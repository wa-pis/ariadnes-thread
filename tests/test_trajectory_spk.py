"""Read-only SPK provenance controls, not a between-epoch error certificate."""

from __future__ import annotations

import ctypes
from collections.abc import Iterator
from fractions import Fraction
from hashlib import file_digest, sha256
import json
from itertools import permutations, product
import math
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter

import numpy as np
import pytest

from space_nav import ephemeris, trajectory


ROOT = Path(__file__).resolve().parents[1]


def test_spk_record_selector_matches_inspected_binary() -> None:
    """Pin the inspected reader instructions, not live dispatch or CPU modes."""
    observation = json.loads((ROOT / "tests/data/m3_spk_selector_observation.json").read_text())
    if (platform.system(), platform.machine()) != (observation["system"], observation["machine"]):
        pytest.skip("No static SPK reader observation for this platform")
    binary_path = Path(sys.prefix) / "lib/libcspice.dylib"
    assert binary_path.stat().st_size == observation["size_bytes"]
    selection_bytes = bytes.fromhex(observation["selection_bytes"])
    assert len(selection_bytes) == 4 * len(observation["selection_instructions"]) == 72
    with binary_path.open("rb") as binary:
        assert file_digest(binary, "sha256").hexdigest() == observation["sha256"], (
            "SPICE build changed; re-audit record selection"
        )
        for reader in observation["readers"]:
            binary.seek(int(reader["selection_file_offset"], 16))
            assert binary.read(len(selection_bytes)) == selection_bytes, reader["symbol"]
        for instruction in observation["evaluation_instructions"]:
            binary.seek(int(instruction["file_offset"], 16))
            assert binary.read(4) == bytes.fromhex(instruction["bytes"]), instruction["instruction"]


def _relative_affine_displacement_upper_m(
    spacecraft_velocity_m_s: np.ndarray, source_slope_m_s: tuple[Fraction, ...],
    duration_s: float, spacecraft_acceleration_m_s2: float,
    source_curvature_m_s2: Fraction, source_coverage_s: float,
) -> Fraction:
    """Bound change of ideal relative position in SI/J2000 within a qualified interval."""
    assert spacecraft_velocity_m_s.shape == (3,) and spacecraft_velocity_m_s.dtype == np.dtype("float64")
    assert np.all(np.isfinite(spacecraft_velocity_m_s))
    assert len(source_slope_m_s) == 3 and all(isinstance(value, Fraction) for value in source_slope_m_s)
    assert all(type(value) is float and math.isfinite(value) and value >= 0
               for value in (duration_s, spacecraft_acceleration_m_s2, source_coverage_s))
    assert duration_s <= source_coverage_s
    assert isinstance(source_curvature_m_s2, Fraction) and source_curvature_m_s2 >= 0
    relative_speed_m_s = sum((abs(Fraction(ship) - source) for ship, source in
                              zip(spacecraft_velocity_m_s, source_slope_m_s, strict=True)), Fraction(0))
    return (relative_speed_m_s * Fraction(duration_s)
            + (Fraction(spacecraft_acceleration_m_s2) + source_curvature_m_s2) * Fraction(duration_s)**2 / 2)


@pytest.mark.parametrize("boost_m_s", [0.0, 1e12])
@pytest.mark.parametrize("duration_s", [0.0, 1 / 64, 0.3])
def test_relative_affine_attains_opposing_acceleration_bound(boost_m_s: float, duration_s: float) -> None:
    ship = np.asarray([boost_m_s + 3.0, -2.0, 1.0])
    source = (Fraction(boost_m_s) + 1, Fraction(-2), Fraction(1))
    bound = _relative_affine_displacement_upper_m(ship, source, duration_s, 2.0, Fraction(1), 1.0)
    t, offset = Fraction(duration_s), Fraction(10**15)
    # Independent exact trajectories: ship acceleration +2, source -1 along x.
    ship_final = offset + Fraction(ship[0])*t + t*t
    source_final = offset + source[0]*t - t*t/2
    assert bound == abs(ship_final - source_final) == 2*t + 3*t*t/2


def test_relative_affine_preserves_three_dimensional_bound() -> None:
    bound = _relative_affine_displacement_upper_m(np.asarray([1.0, 2.0, -2.0]), (Fraction(0),)*3, 0.5, 0.0, Fraction(0), 1.0)
    assert bound == Fraction(5, 2)
    assert Fraction(9, 4) <= bound**2  # Exact squared L2 displacement.


def test_relative_affine_cancels_identical_uniform_motion() -> None:
    velocity = np.asarray([1e12, -1e12, 1.0])
    assert _relative_affine_displacement_upper_m(velocity, tuple(map(Fraction, velocity)), 1.0, 0.0, Fraction(0), 1.0) == 0


@pytest.mark.parametrize("invalid", ["nonfinite", "source", "shape", "duration", "coverage", "boolean",
                                      "negative-ship", "negative-source", "inexact-source"])
def test_relative_affine_rejects_invalid_domains(invalid: str) -> None:
    ship = np.zeros(2 if invalid == "shape" else 3)
    if invalid == "nonfinite":
        ship[0] = math.nan
    with pytest.raises(AssertionError):
        _relative_affine_displacement_upper_m(
            ship, (0.0,)*3 if invalid == "source" else (Fraction(0),)*3,  # type: ignore[arg-type] -- boundary rejection.
            True if invalid == "boolean" else -1.0 if invalid == "duration" else 0.25,
            -1.0 if invalid == "negative-ship" else 0.0,
            0.0 if invalid == "inexact-source" else Fraction(-1 if invalid == "negative-source" else 0),  # type: ignore[arg-type] -- boundary rejection.
            0.125 if invalid == "coverage" else 1.0,
        )


def _spk_position_affine_data(
    budget: trajectory._RefinementBudget, rows_km: tuple[tuple[float, ...], ...],
    midpoint_tdb_s: float, radius_s: float, start_tdb_s: float, duration_s: float,
) -> tuple[tuple[Fraction, ...], tuple[Fraction, ...], Fraction]:
    """Exact record position/slope in SI and an L1 acceleration bound; no join crossing."""
    budget.check()
    assert len(rows_km) == 3 and rows_km[0] and all(len(row) == len(rows_km[0]) for row in rows_km)
    assert all(type(value) is float and math.isfinite(value) for row in rows_km for value in row)
    assert all(type(value) is float and math.isfinite(value) for value in (midpoint_tdb_s, radius_s, start_tdb_s, duration_s))
    assert radius_s > 0 and duration_s >= 0
    radius = Fraction(radius_s)
    x = (Fraction(start_tdb_s) - Fraction(midpoint_tdb_s)) / radius
    assert -1 <= x <= x + Fraction(duration_s) / radius <= 1
    basis, derivative = [Fraction(1), x], [Fraction(0), Fraction(1)]
    for degree in range(2, len(rows_km[0])):
        budget.check()
        derivative.append(2 * basis[-1] + 2 * x * derivative[-1] - derivative[-2])
        basis.append(2 * x * basis[-1] - basis[-2])
    position_m = tuple(1000 * sum((Fraction(c) * basis[n] for n, c in enumerate(row)), Fraction(0)) for row in rows_km)
    slope_m_s = tuple(1000 * sum((Fraction(c) * derivative[n] for n, c in enumerate(row)), Fraction(0)) / radius for row in rows_km)
    # On [-1,1], |T''_n| <= T''_n(1) = n^2*(n^2-1)/3.
    acceleration_m_s2 = 1000 * sum((abs(Fraction(c)) * Fraction(n**2 * (n**2 - 1), 3)
                                   for row in rows_km for n, c in enumerate(row)), Fraction(0)) / radius**2
    budget.check()
    return position_m, slope_m_s, acceleration_m_s2


@pytest.mark.parametrize("midpoint_tdb_s", [0.0, 1e9])
@pytest.mark.parametrize("radius_s", [16.0, 32.0])
@pytest.mark.parametrize("x0", [-0.5, 0.0, 0.5])
def test_spk_affine_matches_expanded_cubic(midpoint_tdb_s: float, radius_s: float, x0: float) -> None:
    rows = ((1e8, 2.0, -0.5, 0.125), (0.0, -1.0, 0.25, -0.5), (1.0, 0.0, 0.0, 0.0))
    start = midpoint_tdb_s + x0 * radius_s
    position, slope, curvature = _spk_position_affine_data(
        trajectory._RefinementBudget("affine-cubic", 300.0), rows, midpoint_tdb_s, radius_s, start, 1.0,
    )
    x, radius = Fraction(x0), Fraction(radius_s)
    for axis, row in enumerate(rows):
        a, b, c, d = map(Fraction, row)
        assert position[axis] == 1000 * (a + b*x + c*(2*x*x-1) + d*(4*x**3-3*x))
        assert slope[axis] == 1000 * (b + 4*c*x + d*(12*x*x-3)) / radius
    assert curvature == 1000 * sum((4*abs(Fraction(row[2])) + 24*abs(Fraction(row[3])) for row in rows), Fraction(0)) / radius**2
    for elapsed in (Fraction(0), Fraction(1, 2), Fraction(1)):
        u = x + elapsed / radius
        exact_final = [1000 * (Fraction(a) + Fraction(b)*u + Fraction(c)*(2*u*u-1) + Fraction(d)*(4*u**3-3*u))
                       for a, b, c, d in rows]
        residual = sum((abs(final - initial - velocity*elapsed) for final, initial, velocity in
                        zip(exact_final, position, slope, strict=True)), Fraction(0))
        assert residual <= curvature * elapsed**2 / 2


@pytest.mark.parametrize("degree", [0, 1, 2, 19, 120])
def test_spk_affine_endpoint_single_mode(degree: int) -> None:
    row = (0.0,) * degree + (1.0,)
    position, slope, curvature = _spk_position_affine_data(
        trajectory._RefinementBudget("affine-mode", 300.0), (row, (0.0,) * len(row), (0.0,) * len(row)),
        0.0, 1.0, 1.0, 0.0,
    )
    assert position == (1000, 0, 0) and slope == (1000 * degree**2, 0, 0)
    # Differentiate T'=n*U and expand U in positive Chebyshev modes.
    endpoint_second = 2 * degree * sum(k*k for k in range(degree - 1, 0, -2))
    assert curvature == 1000 * endpoint_second


@pytest.mark.parametrize("invalid", ["nan", "rows", "radius", "outside", "crossing"])
def test_spk_affine_rejects_invalid_record_interval(invalid: str) -> None:
    rows = ((math.nan if invalid == "nan" else 1.0,), (0.0,), (0.0,))
    if invalid == "rows":
        rows = ((1.0,), (0.0, 0.0), (0.0,))
    with pytest.raises(AssertionError):
        _spk_position_affine_data(
            trajectory._RefinementBudget("affine-invalid", 300.0), rows, 0.0,
            0.0 if invalid == "radius" else 1.0, -2.0 if invalid == "outside" else 0.0,
            2.0 if invalid == "crossing" else 0.25,
        )


def test_spk_affine_rejects_expired_budget() -> None:
    clock = iter([0.0, 301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _spk_position_affine_data(
            trajectory._RefinementBudget("affine-expired", 300.0, lambda: next(clock)),
            ((0.0,),) * 3, 0.0, 1.0, 0.0, 0.25,
        )


def _replay_spk_series(
    coefficients: tuple[float, ...], midpoint_tdb_s: float,
    radius_s: float, epoch_tdb_s: float,
) -> float:
    """Replay the inspected series, retaining coefficient units (km or km/s)."""
    assert coefficients and radius_s > 0
    assert all(math.isfinite(value) for value in (*coefficients, midpoint_tdb_s,
                                                 radius_s, epoch_tdb_s))
    normalized_time = (epoch_tdb_s - midpoint_tdb_s) / radius_s
    twice_time = normalized_time + normalized_time
    current = following = 0.0
    for coefficient in reversed(coefficients[1:]):
        fused = float(Fraction(twice_time) * Fraction(current) - Fraction(following))
        following, current = current, fused + coefficient
        assert math.isfinite(current)
    result = float(Fraction(normalized_time) * Fraction(current) - Fraction(following)) + coefficients[0]
    assert math.isfinite(result)
    return result


def _replay_spk_type2_velocity(
    coefficients_km: tuple[float, ...], midpoint_tdb_s: float,
    radius_s: float, epoch_tdb_s: float,
) -> float:
    """Replay the inspected CHBINT derivative path in km/s, not an error bound."""
    assert coefficients_km and radius_s > 0
    assert all(math.isfinite(value) for value in (*coefficients_km, midpoint_tdb_s,
                                                 radius_s, epoch_tdb_s))
    normalized_time = (epoch_tdb_s - midpoint_tdb_s) / radius_s
    twice_time = normalized_time + normalized_time
    current = following = derivative = next_derivative = 0.0
    for coefficient_km in reversed(coefficients_km[1:]):
        position_km = float(Fraction(twice_time) * Fraction(current) - Fraction(following)) + coefficient_km
        # The derivative first rounds a multiply, then a fused add, then a subtract.
        product_km = twice_time * derivative
        slope_km = float(2 * Fraction(current) + Fraction(product_km)) - next_derivative
        following, current = current, position_km
        next_derivative, derivative = derivative, slope_km
        assert all(math.isfinite(value) for value in (current, derivative))
    slope_km = float(Fraction(normalized_time) * Fraction(derivative) + Fraction(current)) - next_derivative
    return slope_km / radius_s


@pytest.mark.parametrize("degree", [0, 1, 2, 19])
@pytest.mark.parametrize("normalized_time", [-1.0, 0.3, 1.0])
def test_type2_velocity_replay_matches_native_single_modes(
    cspice: ctypes.CDLL, degree: int, normalized_time: float,
) -> None:
    import spiceypy as spice

    coefficients_km = (0.0,) * degree + (0.3,)
    midpoint_tdb_s, radius_s = 978995455.0, 32.0
    epoch_tdb_s = midpoint_tdb_s + radius_s * normalized_time
    replay_km_s = _replay_spk_type2_velocity(coefficients_km, midpoint_tdb_s, radius_s, epoch_tdb_s)
    _, native_km_s = spice.chbint(coefficients_km, degree, [midpoint_tdb_s, radius_s], epoch_tdb_s)
    assert replay_km_s.hex() == native_km_s.hex()
    x = (Fraction(epoch_tdb_s) - Fraction(midpoint_tdb_s)) / Fraction(radius_s)
    previous, current = Fraction(0), Fraction(1)  # U_-1, U_0; T'_n = n U_(n-1).
    for _ in range(1, degree):
        previous, current = current, 2 * x * current - previous
    exact_km_s = Fraction(0.3) * degree * current / Fraction(radius_s)
    assert 1000 * abs(Fraction(native_km_s) - exact_km_s) <= Fraction("0.000001")  # m/s
    assert cspice.failed_c() == 0


def _spk_type2_velocity_roundoff_bound_km_s(
    budget: trajectory._RefinementBudget, coefficients_km: tuple[float, ...],
    radius_s: float, normalized_limit: Fraction,
) -> Fraction:
    """Conditional CHBINT derivative error at fixed rounded normalized time.

    Assume binary64 nearest rounding, gradual underflow and the inspected
    operations. Exclude normalization, source selection and SI conversion.
    """
    budget.check()
    assert coefficients_km and all(type(value) is float and math.isfinite(value)
                                   for value in coefficients_km)
    assert type(radius_s) is float and math.isfinite(radius_s) and radius_s > 0
    assert isinstance(normalized_limit, Fraction) and 1 <= normalized_limit < 2
    u, eta = Fraction(1, 2 ** 53), Fraction(1, 2 ** 1075)
    maximum = Fraction(sys.float_info.max)

    def rounded_bound(magnitude: Fraction) -> tuple[Fraction, Fraction]:
        error = u * magnitude + eta
        assert 0 <= magnitude <= magnitude + error <= maximum
        return magnitude + error, error

    q, radius = normalized_limit, Fraction(radius_s)
    position = following_position = derivative = following_derivative = Fraction(0)
    position_error = following_position_error = derivative_error = following_derivative_error = Fraction(0)
    for coefficient_km in reversed(coefficients_km[1:]):
        budget.check()
        fused_position, fused_position_error = rounded_bound(2 * q * position + following_position)
        new_position, addition_error = rounded_bound(fused_position + abs(Fraction(coefficient_km)))
        new_position_error = 2 * q * position_error + following_position_error + fused_position_error + addition_error
        product, product_error = rounded_bound(2 * q * derivative)
        fused_derivative, fused_derivative_error = rounded_bound(2 * position + product)
        new_derivative, subtraction_error = rounded_bound(fused_derivative + following_derivative)
        new_derivative_error = (2 * q * derivative_error + following_derivative_error
                                + 2 * position_error + product_error + fused_derivative_error + subtraction_error)
        following_position, position = position, new_position
        following_position_error, position_error = position_error, new_position_error
        following_derivative, derivative = derivative, new_derivative
        following_derivative_error, derivative_error = derivative_error, new_derivative_error
    fused, fused_error = rounded_bound(q * derivative + position)
    numerator, subtraction_error = rounded_bound(fused + following_derivative)
    numerator_error = q * derivative_error + position_error + following_derivative_error + fused_error + subtraction_error
    _, division_error = rounded_bound(numerator / radius)
    result_km_s = numerator_error / radius + division_error
    budget.check()
    return result_km_s


@pytest.mark.parametrize("degree", [0, 1, 2, 19])
@pytest.mark.parametrize("limit", [Fraction(1), Fraction(5, 4)])
def test_type2_velocity_bound_contains_single_mode_errors(degree: int, limit: Fraction) -> None:
    budget = trajectory._RefinementBudget("velocity-roundoff-control", 300.0)
    coefficients_km, radius_s = (0.0,) * degree + (0.3,), 32.0
    bound_km_s = _spk_type2_velocity_roundoff_bound_km_s(budget, coefficients_km, radius_s, limit)
    for x in (-limit, -limit / 2, Fraction(0), limit / 2, limit):
        previous, current = Fraction(0), Fraction(1)
        for _ in range(1, degree):
            previous, current = current, 2 * x * current - previous
        exact_km_s = Fraction(0.3) * degree * current / Fraction(radius_s)
        replay_km_s = _replay_spk_type2_velocity(coefficients_km, 0.0, radius_s, float(x * 32))
        assert abs(Fraction(replay_km_s) - exact_km_s) <= bound_km_s
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)


def test_type2_velocity_bound_retains_division_underflow() -> None:
    budget = trajectory._RefinementBudget("velocity-underflow-control", 300.0)
    coefficients_km = (0.0, math.ulp(0.0))
    bound_km_s = _spk_type2_velocity_roundoff_bound_km_s(budget, coefficients_km, 2.0, Fraction(1))
    assert _replay_spk_type2_velocity(coefficients_km, 0.0, 2.0, 0.0) == 0.0
    assert bound_km_s >= Fraction(math.ulp(0.0)) / 2 > 0


@pytest.mark.parametrize("coefficients,radius,limit", [
    ((math.nan,), 1.0, Fraction(1)), ((True,), 1.0, Fraction(1)),
    ((1.0,), 0.0, Fraction(1)), ((1.0,), 1.0, Fraction(2)),
])
def test_type2_velocity_bound_rejects_invalid_domain(
    coefficients: tuple[float, ...], radius: float, limit: Fraction,
) -> None:
    with pytest.raises(AssertionError):
        _spk_type2_velocity_roundoff_bound_km_s(
            trajectory._RefinementBudget("velocity-domain-control", 300.0), coefficients, radius, limit,
        )


def test_type2_velocity_bound_rejects_overflow_and_expired_budget() -> None:
    budget = trajectory._RefinementBudget("velocity-range-control", 300.0)
    for coefficients_km, radius_s in (((0.0, sys.float_info.max), 1.0), ((0.0, 1.0), math.ulp(0.0))):
        with pytest.raises(AssertionError):
            _spk_type2_velocity_roundoff_bound_km_s(budget, coefficients_km, radius_s, Fraction(1))
    clock_s = iter([0.0, 300.0])
    budget = trajectory._RefinementBudget("velocity-deadline-control", 300.0, lambda: next(clock_s))
    with pytest.raises(trajectory.TrajectoryRefinementError, match="deadline"):
        _spk_type2_velocity_roundoff_bound_km_s(budget, (1.0,), 1.0, Fraction(1))


def _spk_series_roundoff_bound(
    budget: trajectory._RefinementBudget, coefficients: tuple[float, ...],
    normalized_limit: Fraction,
) -> Fraction:
    """Conditional RN/gradual-underflow error in coefficient units (km or km/s)."""
    budget.check()
    assert coefficients and all(type(value) is float and math.isfinite(value)
                                for value in coefficients)
    assert isinstance(normalized_limit, Fraction) and 1 <= normalized_limit < 2
    u, eta = Fraction(1, 2 ** 53), Fraction(1, 2 ** 1075)
    maximum = Fraction(sys.float_info.max)
    weights = [Fraction(1), normalized_limit]
    for degree in range(2, len(coefficients)):
        budget.check()
        weights.append(2 * normalized_limit * weights[-1] - weights[-2])
    current = following = error = Fraction(0)
    for degree in reversed(range(len(coefficients))):
        budget.check()
        coefficient = abs(Fraction(coefficients[degree]))
        scale = normalized_limit if degree == 0 else 2 * normalized_limit
        expression = scale * current + following
        fused = (1 + u) * expression + eta
        assert expression <= maximum and fused + coefficient <= maximum
        residual = u * expression + eta + u * (fused + coefficient) + eta
        following, current = current, (1 + u) * (fused + coefficient) + eta
        error += residual * weights[degree]
    budget.check()
    return error


@pytest.mark.parametrize("radius_s", [1.0, 32.0])
@pytest.mark.parametrize("normalized_time", [-1.0, 0.3, 1.0])
def test_type3_velocity_uses_stored_series_not_position_derivative(
    cspice: ctypes.CDLL, radius_s: float, normalized_time: float,
) -> None:
    budget = trajectory._RefinementBudget("stored-velocity-control", 300.0)
    midpoint_tdb_s, coefficient_count = 978995455.0, 3
    epoch_tdb_s = midpoint_tdb_s + radius_s * normalized_time
    velocity_rows_km_s = ((0.1, 0.3, -0.2), (0.4, -0.1, 0.2), (-0.3, 0.2, 0.1))
    size = 2 + 6 * coefficient_count
    # Deliberately inconsistent synthetic channels distinguish the SPK contracts.
    record = (ctypes.c_double * (size + 1))(
        float(size), midpoint_tdb_s, radius_s, *([0.0] * 9),
        *(value for row in velocity_rows_km_s for value in row),
    )
    epoch, state = ctypes.c_double(epoch_tdb_s), (ctypes.c_double * 6)()
    cspice.spke03_(ctypes.byref(epoch), record, state)
    assert cspice.failed_c() == 0 and tuple(state[:3]) == (0.0, 0.0, 0.0)
    x = (epoch_tdb_s - midpoint_tdb_s) / radius_s
    assert Fraction(x) == (Fraction(epoch_tdb_s) - Fraction(midpoint_tdb_s)) / Fraction(radius_s)
    for axis, row in enumerate(velocity_rows_km_s):
        replay_km_s = _replay_spk_series(row, midpoint_tdb_s, radius_s, epoch_tdb_s)
        exact_km_s = Fraction(row[0]) + Fraction(row[1]) * Fraction(x) + Fraction(row[2]) * (2 * Fraction(x)**2 - 1)
        assert state[axis + 3].hex() == replay_km_s.hex()
        assert abs(Fraction(state[axis + 3]) - exact_km_s) <= _spk_series_roundoff_bound(budget, row, Fraction(1))
        assert 1000 * abs(Fraction(state[axis + 3]) - exact_km_s) <= Fraction("0.000001")  # m/s
        assert state[axis + 3] != 0.0  # Not the derivative of the zero position polynomial.


@pytest.mark.parametrize("degree", [0, 1, 2, 19])
@pytest.mark.parametrize("limit", [Fraction(1), Fraction(5, 4)])
def test_spk_fused_bound_contains_exact_single_mode_errors(degree: int, limit: Fraction) -> None:
    budget = trajectory._RefinementBudget("fused-roundoff-control", 300.0)
    coefficients_km = (0.0,) * degree + (0.3,)
    bound_km = _spk_series_roundoff_bound(budget, coefficients_km, limit)
    u, eta = Fraction(1, 2 ** 53), Fraction(1, 2 ** 1075)
    if degree == 0:
        assert bound_km == u * Fraction(0.3) + (2 + u) * eta
    elif degree == 1:
        first_residual = u * Fraction(0.3) + (2 + u) * eta
        first_magnitude = (1 + u) * Fraction(0.3) + (2 + u) * eta
        assert bound_km == limit * first_residual + (2 * u + u ** 2) * limit * first_magnitude + (2 + u) * eta
    for normalized_time in (-limit, -limit / 2, Fraction(0), limit / 2, limit):
        x = float(normalized_time)
        basis = [Fraction(1), normalized_time]
        for k in range(2, degree + 1):
            basis.append(2 * normalized_time * basis[-1] - basis[-2])
        exact_km = Fraction(0.3) * basis[degree]
        replay_km = _replay_spk_series(coefficients_km, 0.0, 1.0, x)
        assert abs(Fraction(replay_km) - exact_km) <= bound_km


def test_spk_fused_bound_retains_gradual_underflow_term() -> None:
    budget = trajectory._RefinementBudget("fused-underflow-control", 300.0)
    smallest_km = math.ulp(0.0)
    coefficients_km = (0.0, smallest_km)
    bound_km = _spk_series_roundoff_bound(budget, coefficients_km, Fraction(1))
    assert _replay_spk_series(coefficients_km, 0.0, 1.0, 0.5) == 0.0
    assert bound_km >= Fraction(smallest_km) / 2 > 0


def test_spk_fused_bound_rejects_overflow_and_expired_budget() -> None:
    budget = trajectory._RefinementBudget("fused-range-control", 300.0)
    with pytest.raises(AssertionError):
        _spk_series_roundoff_bound(budget, (sys.float_info.max,) * 2, Fraction(1))
    now_s = [0.0]
    budget = trajectory._RefinementBudget("fused-deadline-control", 300.0, lambda: now_s[0])
    now_s[0] = 300.0
    with pytest.raises(trajectory.TrajectoryRefinementError, match="deadline"):
        _spk_series_roundoff_bound(budget, (1.0,), Fraction(1))


def test_spk_position_replay_distinguishes_fused_rounding(cspice: ctypes.CDLL) -> None:
    import spiceypy as spice

    coefficients_km = (0.0, 0.1, 0.3)
    epoch_s = 0.3
    replay_km = _replay_spk_series(coefficients_km, 0.0, 1.0, epoch_s)
    unfused_km = epoch_s * ((epoch_s + epoch_s) * 0.3 + 0.1) - 0.3
    assert replay_km.hex() == "-0x1.ba5e353f7ced9p-3"
    assert unfused_km.hex() == "-0x1.ba5e353f7ced8p-3"
    assert replay_km != unfused_km
    assert spice.chbval(coefficients_km, 2, [0.0, 1.0], epoch_s).hex() == replay_km.hex()
    assert spice.chbint(coefficients_km, 2, [0.0, 1.0], epoch_s)[0].hex() == replay_km.hex()
    exact_km = Fraction(0.1) * Fraction(epoch_s) + Fraction(0.3) * (2 * Fraction(epoch_s) ** 2 - 1)
    assert abs(Fraction(replay_km) - exact_km) * 1000 < Fraction("1e-12")  # m
    assert cspice.failed_c() == 0


def _read_native_spk_record(
    native: ctypes.CDLL, data_type: int, handle: int, descriptor: np.ndarray,
    epoch_tdb_s: float, record_size: int,
) -> np.ndarray:
    """Read raw TDB-s/km/type-3-km/s words using the pinned, test-only f2c ABI."""
    assert data_type in (2, 3) and record_size > 2
    native_handle = ctypes.c_int(handle)
    native_epoch = ctypes.c_double(epoch_tdb_s)
    native_descriptor = (ctypes.c_double * 5)(*descriptor)
    raw_record = (ctypes.c_double * (record_size + 2))()
    raw_record[-1] = 1234567.0  # Guard after length and directory-sized data.
    reader = native.spkr02_ if data_type == 2 else native.spkr03_
    reader(ctypes.byref(native_handle), native_descriptor, ctypes.byref(native_epoch), raw_record)
    assert native.failed_c() == 0
    assert raw_record[0] == record_size and raw_record[-1] == 1234567.0
    return np.asarray(raw_record)[1:-1].copy()


@pytest.mark.parametrize("degree", [0, 1, 2, 19])
def test_spk_rate_bound_matches_single_mode_endpoint_oracle(degree: int) -> None:
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0)
    row = tuple(1.0 if index == degree else 0.0 for index in range(degree + 1))
    bound_m_s = trajectory._spk_position_rate_bound(budget, (row, (0.0,) * len(row),
                                                               (0.0,) * len(row)), 17.0)
    exact_m_s = Fraction(1000 * degree ** 2, 17)
    assert Fraction(bound_m_s) >= exact_m_s
    assert bound_m_s == (math.nextafter(float(exact_m_s), math.inf) if degree else 0.0)
    derivative_m_s = np.polynomial.chebyshev.chebval(
        1.0, np.polynomial.chebyshev.chebder(row),
    ) * 1000 / 17
    assert abs(derivative_m_s - float(exact_m_s)) <= 1e-12  # m/s


@pytest.mark.parametrize("degree", [0, 1, 2, 3, 19])
def test_spk_extended_rate_bound_matches_closed_polynomial_oracle(degree: int) -> None:
    budget = trajectory._RefinementBudget("extended-chebyshev-control", 300.0)
    row = (0.0,) * degree + (1.0,)
    rows = (row, (0.0,) * len(row), (0.0,) * len(row))
    q = Fraction(5, 4)
    # Independent finite power formula for U_n, not the implementation recurrence.
    n = degree - 1
    exact_m_s = 1000 * degree * sum(((-1) ** j * math.comb(n - j, j) * (2 * q) ** (n - 2 * j)
                                    for j in range((n // 2) + 1)), Fraction(0)) / 4
    bound_m_s = trajectory._spk_position_rate_bound(budget, rows, 4.0, extension_s=1.0)
    assert Fraction(bound_m_s) >= exact_m_s
    assert bound_m_s == (math.nextafter(float(exact_m_s), math.inf) if degree else 0.0)
    for x in (-float(q), float(q)):
        derivative_m_s = abs(np.polynomial.chebyshev.chebval(x, np.polynomial.chebyshev.chebder(row))) * 250
        assert derivative_m_s == pytest.approx(float(exact_m_s), rel=1e-12, abs=1e-12)  # m/s
    assert trajectory._spk_position_rate_bound(budget, rows, 4.0, extension_s=0.0) == (
        trajectory._spk_position_rate_bound(budget, rows, 4.0)
    )


def test_spk_extended_rate_keeps_sub_ulp_normalized_extension() -> None:
    budget = trajectory._RefinementBudget("extended-chebyshev-control", 300.0)
    rows = ((0.0, 0.0, 1.0), (0.0,) * 3, (0.0,) * 3)
    extension_s = 2.0 ** -53
    assert 1.0 + extension_s == 1.0
    bound_m_s = trajectory._spk_position_rate_bound(budget, rows, 1.0, extension_s=extension_s)
    assert Fraction(bound_m_s) >= 4000 * (1 + Fraction(extension_s))
    assert bound_m_s > trajectory._spk_position_rate_bound(budget, rows, 1.0)


@pytest.mark.parametrize("extension_s", [-1.0, True, float("nan"), float("inf"), 1e308])
def test_spk_extended_rate_rejects_invalid_or_overflowing_extension(extension_s: float) -> None:
    budget = trajectory._RefinementBudget("extended-chebyshev-control", 300.0)
    with pytest.raises(trajectory.TrajectoryRefinementError, match="spk-position-rate-bound") as caught:
        trajectory._spk_position_rate_bound(
            budget, ((0.0, 0.0, 1.0), (0.0,) * 3, (0.0,) * 3), 1e-308, extension_s=extension_s,
        )
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize("extension_s", [0.0, 0.1])
def test_spk_rate_bound_rounds_mixed_axes_outward(extension_s: float) -> None:
    rows = ((1e200, 0.1, -0.3), (-1e200, 0.2, 0.0), (0.0, -0.4, 0.5))
    weights = (Fraction(0), Fraction(1), 4 * (1 + Fraction(extension_s) / Fraction(0.3)))
    exact_m_s = 1000 * sum((abs(Fraction(value)) * weights[degree]
                            for row in rows for degree, value in enumerate(row)), Fraction(0)) / Fraction(0.3)
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0)
    bound_m_s = trajectory._spk_position_rate_bound(budget, rows, 0.3, extension_s=extension_s)
    assert Fraction(bound_m_s) >= exact_m_s
    assert bound_m_s == math.nextafter(float(exact_m_s), math.inf)


def test_spk_rate_bound_preserves_positive_subnormal_bound() -> None:
    smallest = math.nextafter(0.0, math.inf)
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0)
    bound_m_s = trajectory._spk_position_rate_bound(
        budget, ((0.0, smallest), (0.0, 0.0), (0.0, 0.0)), 1e308,
    )
    assert Fraction(bound_m_s) >= 1000 * Fraction(smallest) / Fraction(1e308) > 0


@pytest.mark.parametrize("rows,radius_s", [
    ((), 1.0), (((), (), ()), 1.0), (((1.0,), (1.0, 2.0), (1.0,)), 1.0),
    (((True,), (0.0,), (0.0,)), 1.0), (((float("nan"),), (0.0,), (0.0,)), 1.0),
    (((0.0,), (0.0,), (0.0,)), 0.0), (((0.0,), (0.0,), (0.0,)), True),
    (((0.0,), (0.0,), (0.0,)), float("inf")),
    (((0.0, 1e308), (0.0, 0.0), (0.0, 0.0)), 1e-308),
])
def test_spk_rate_bound_rejects_invalid_coefficients_or_radius(
    rows: tuple[tuple[float, ...], ...], radius_s: float,
) -> None:
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0)
    with pytest.raises(trajectory.TrajectoryRefinementError, match="spk-position-rate-bound") as caught:
        trajectory._spk_position_rate_bound(budget, rows, radius_s)
    assert caught.value.__cause__ is not None


def test_spk_rate_bound_honors_expired_budget() -> None:
    now_s = [0.0]
    budget = trajectory._RefinementBudget("chebyshev-rate-control", 300.0, lambda: now_s[0])
    now_s[0] = 300.0
    with pytest.raises(trajectory.TrajectoryRefinementError, match="deadline"):
        trajectory._spk_position_rate_bound(budget, ((0.0,),) * 3, 1.0)


@pytest.mark.parametrize("native_record_readback", [False, True], ids=["portable", "native-readback"])
def test_loaded_spk_chain_coverage_contains_candidate_interval(
    native_record_readback: bool, request: pytest.FixtureRequest,
) -> None:
    """Qualify conditional source/endpoint bounds, not full-mission safety."""
    import spiceypy as spice
    from spiceypy.utils.support_types import SPICEDOUBLE_CELL

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    start_tdb_s, end_tdb_s = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    native: ctypes.CDLL | None = None
    if native_record_readback:
        native = request.getfixturevalue("cspice")
        assert isinstance(native, ctypes.CDLL)
        budget.check()
    ephemeris._ensure_standard_kernels()
    kernels_before = [spice.kdata(i, "ALL") for i in range(spice.ktotal("ALL"))]
    registrations = [spice.kdata(i, "SPK") for i in range(spice.ktotal("SPK"))]
    # Repeated kernel initialization registers the same physical file again.
    files = list({str(Path(entry[0]).resolve()): entry for entry in registrations}.values())
    assert files
    # Effective targets already qualified against named Tudat states.
    expected_centers = {10: 0, 1: 0, 2: 0, 399: 0, 301: 399,
                        499: 4, 4: 0, 599: 5, 5: 0, 699: 6, 6: 0}
    segment_counts = dict.fromkeys(expected_centers, 0)
    segments: list[tuple[int, int, int, float, float, int, int, np.ndarray]] = []
    total_segments = 0
    # Complete DAF scans before calling other routines that start DAF searches.
    for path, kind, _, handle in files:
        assert kind == "SPK"
        spice.dafbfs(handle)
        while spice.daffna():
            budget.check()
            total_segments += 1
            descriptor = spice.dafgs()[:5]
            target, center, frame, data_type, first, last, begin, end = spice.spkuds(descriptor)
            assert math.isfinite(first) and math.isfinite(last) and first <= last
            assert 0 < begin <= end
            if target in expected_centers and first <= end_tdb_s and last >= start_tdb_s:
                assert center == expected_centers[target], (path, target, center)
                assert frame == 1 and data_type in (2, 3), (path, target, frame, data_type)
                segment_counts[target] += 1
                segments.append((handle, target, data_type, first, last, begin, end, descriptor.copy()))
    assert len(files) == 6 and total_segments == 2028
    assert segment_counts == {target: 2 if target == 699 else 1 for target in expected_centers}

    rates_m_s: dict[int, list[float]] = {target: [] for target in expected_centers}
    position_records: dict[int, list[tuple[float, float, tuple[tuple[float, ...], ...]]]] = {
        target: [] for target in expected_centers
    }
    joins: dict[tuple[int, Fraction], dict[int, tuple[
        tuple[Fraction, ...], tuple[Fraction, ...], float, np.ndarray,
    ]]] = {}
    join_error_terms: dict[tuple[int, Fraction, int], tuple[Fraction, Fraction]] = {}
    max_position_difference_m = max_type2_velocity_difference_m_s = 0.0
    max_join_position_difference_m = 0.0
    native_join_failures: list[tuple[int, float, int, float]] = []
    all_record_checks = dict.fromkeys(expected_centers, 0)
    early_record_choices = dict.fromkeys(expected_centers, 0)
    index_roundoff_margins: list[tuple[int, float, float, float]] = []
    endpoint_record_checks = 0
    evaluation_checks = 0
    type2_velocity_checks = 0
    max_type2_evaluation_error_m_s = 0.0
    type2_uniform_velocity_bounds_m_s: list[float] = []
    type3_uniform_velocity_bounds_m_s: list[float] = []
    type3_velocity_checks = 0
    max_type3_evaluation_error_m_s = 0.0
    max_evaluation_error_m = dict.fromkeys(expected_centers, 0.0)
    uniform_evaluation_bounds_m: dict[int, list[float]] = {target: [] for target in expected_centers}
    native_magnitude_bounds_km: dict[int, list[Fraction]] = {target: [] for target in expected_centers}
    native_velocity_magnitudes_km_s: dict[int, list[Fraction]] = {target: [] for target in expected_centers}
    uniform_velocity_errors_m_s: dict[int, list[Fraction]] = {target: [] for target in expected_centers}
    selection_pieces: dict[int, list[tuple[Fraction, Fraction]]] = {target: [] for target in expected_centers}
    internal_strip_keys: set[tuple[int, Fraction]] = set()
    native_core_checks = native_strip_endpoint_checks = 0
    unit_roundoff = Fraction(1, 2 ** 53)
    switching_records: dict[int, list[tuple[int, np.ndarray, float, float, int, np.ndarray]]] = {
        499: [], 599: [],
    }
    for handle, target, data_type, first, last, begin, end, descriptor in segments:
        budget.check()
        init_s, interval_s, raw_size, raw_count = spice.dafgda(handle, end - 3, end)
        assert all(math.isfinite(value) for value in (init_s, interval_s, raw_size, raw_count))
        assert interval_s > 0 and raw_size == int(raw_size) and raw_count == int(raw_count)
        size, count = int(raw_size), int(raw_count)
        components = 3 if data_type == 2 else 6
        assert size > 2 and count > 0 and (size - 2) % components == 0
        coefficient_count = (size - 2) // components
        assert end - begin + 1 == size * count + 4
        assert Fraction(init_s) == Fraction(first)
        assert Fraction(init_s) + count * Fraction(interval_s) == Fraction(last)
        # Inspected signed 32-bit conversion/add/address path must not overflow.
        assert 0 < size < 2 ** 31 and 0 < count + 1 < 2 ** 31
        assert 0 < begin <= begin + count * size < end < 2 ** 31
        if native is not None:
            for probe_s, selected_index in ((float(first), 0), (float(last), count - 1)):
                budget.check()
                quotient = (probe_s - init_s) / interval_s
                assert quotient == (0 if selected_index == 0 else count)
                assert min(math.trunc(quotient) + 1, count) - 1 == selected_index
                address = begin + selected_index * size
                expected_record = spice.dafgda(handle, address, address + size - 1)
                actual_record = _read_native_spk_record(native, data_type, handle, descriptor, probe_s, size)
                assert actual_record.tobytes() == expected_record.tobytes(), (target, probe_s)
                endpoint_record_checks += 1
        # Conditional two-operation, round-to-nearest binary64 replay over
        # the whole segment; zero offset is exact and handled separately.
        minimum_offset_s = Fraction(math.nextafter(float(init_s), math.inf)) - Fraction(init_s)
        maximum_offset_s = Fraction(last) - Fraction(init_s)
        minimum_normal = Fraction(sys.float_info.min)
        maximum_finite = Fraction(sys.float_info.max)
        assert (float(init_s) - float(init_s)) / float(interval_s) == 0.0
        assert minimum_offset_s * (1 - unit_roundoff) > minimum_normal
        assert minimum_offset_s * (1 - unit_roundoff) ** 2 / Fraction(interval_s) > minimum_normal
        assert maximum_offset_s * (1 + unit_roundoff) < maximum_finite
        assert maximum_offset_s * (1 + unit_roundoff) ** 2 / Fraction(interval_s) < maximum_finite
        margin_s = (2 * unit_roundoff + unit_roundoff ** 2) * maximum_offset_s
        assert count + margin_s / Fraction(interval_s) < count + 1 < 2 ** 31
        assert 0 < margin_s < Fraction(interval_s)
        assert margin_s < 16 * Fraction(min(math.ulp(start_tdb_s), math.ulp(end_tdb_s)))
        reported_margin_s = math.nextafter(float(margin_s), math.inf)
        assert math.isfinite(reported_margin_s) and Fraction(reported_margin_s) >= margin_s
        index_roundoff_margins.append((target, first, last, reported_margin_s))
        # Include both touching records at exact endpoints without rounded index division.
        first_index = max(0, math.ceil((Fraction(start_tdb_s) - Fraction(init_s)) / Fraction(interval_s)) - 1)
        last_index = min(count - 1, math.floor((Fraction(end_tdb_s) - Fraction(init_s)) / Fraction(interval_s)))
        assert 0 <= first_index <= last_index < count
        for index in range(first_index, last_index + 1):
            budget.check()
            address = begin + index * size
            record = spice.dafgda(handle, address, address + size - 1)
            assert np.all(np.isfinite(record))
            record_start_s = Fraction(init_s) + index * Fraction(interval_s)
            assert Fraction(record[0]) == record_start_s + Fraction(interval_s) / 2
            assert Fraction(record[1]) == Fraction(interval_s) / 2
            half_width_s = 16 * Fraction(math.ulp(float(record[0])))
            core_start_s = max(Fraction(start_tdb_s), record_start_s + half_width_s)
            core_end_s = min(Fraction(end_tdb_s), record_start_s + Fraction(interval_s) - half_width_s)
            assert core_start_s < core_end_s
            selection_pieces[target].append((core_start_s, core_end_s))
            if native is not None:
                for exact_probe_s in (core_start_s, core_end_s):
                    budget.check()
                    probe_s = float(exact_probe_s)
                    assert Fraction(probe_s) == exact_probe_s
                    assert min(math.floor((probe_s - init_s) / interval_s), count - 1) == index
                    selected = _read_native_spk_record(native, data_type, handle, descriptor, probe_s, size)
                    assert selected.tobytes() == record.tobytes(), (target, index, probe_s)
                    native_core_checks += 1
            boundary_s = record_start_s + Fraction(interval_s)
            if start_tdb_s < boundary_s < end_tdb_s and boundary_s < Fraction(last):
                assert index + 1 < count
                internal_strip_keys.add((target, boundary_s))
                if native is not None:
                    for direction, selected_index in ((-1, index), (1, index + 1)):
                        budget.check()
                        exact_probe_s = boundary_s + direction * half_width_s
                        probe_s = float(exact_probe_s)
                        assert Fraction(probe_s) == exact_probe_s
                        assert min(math.floor((probe_s - init_s) / interval_s), count - 1) == selected_index
                        selected_address = begin + selected_index * size
                        expected_record = spice.dafgda(handle, selected_address, selected_address + size - 1)
                        selected = _read_native_spk_record(native, data_type, handle, descriptor, probe_s, size)
                        assert selected.tobytes() == expected_record.tobytes(), (target, selected_index, probe_s)
                        native_strip_endpoint_checks += 1
            if native is not None:
                probes_s = [float(record[0])]
                for boundary_s, direction in ((record_start_s, 1), (record_start_s + Fraction(interval_s), -1)):
                    if start_tdb_s < boundary_s < end_tdb_s:
                        probes_s.append(float(boundary_s) + direction * math.ulp(float(boundary_s)))
                for probe_s in probes_s:
                    budget.check()
                    rounded_quotient = (probe_s - init_s) / interval_s
                    exact_quotient = (Fraction(probe_s) - Fraction(init_s)) / Fraction(interval_s)
                    assert abs(Fraction(rounded_quotient) - exact_quotient) * Fraction(interval_s) <= margin_s
                    selected_index = math.floor(rounded_quotient)
                    assert abs(selected_index - math.floor(exact_quotient)) <= 1
                    assert 0 <= selected_index < count
                    assert selected_index in (index, index + 1)
                    if selected_index != index:
                        selected_boundary_s = Fraction(init_s) + selected_index * Fraction(interval_s)
                        assert abs(Fraction(probe_s) - selected_boundary_s) <= margin_s
                    selected_address = begin + selected_index * size
                    expected_record = spice.dafgda(handle, selected_address, selected_address + size - 1)
                    actual_record = _read_native_spk_record(native, data_type, handle, descriptor, probe_s, size)
                    assert actual_record.tobytes() == expected_record.tobytes(), (target, probe_s)
                    all_record_checks[target] += 1
                    early_record_choices[target] += selected_index != index
            if target in switching_records:
                switching_records[target].append((handle, descriptor, init_s, interval_s, index, record))
            coefficients_km = record[2:].reshape(components, coefficient_count)[:3]
            midpoint_s, radius_s = float(record[0]), float(record[1])
            extension_s = 16 * math.ulp(midpoint_s)
            # Every binary64 query in this closed domain has exact Sterbenz subtraction.
            assert Fraction(midpoint_s) / 2 <= Fraction(midpoint_s) - Fraction(radius_s) - Fraction(extension_s)
            assert Fraction(midpoint_s) + Fraction(radius_s) + Fraction(extension_s) <= 2 * Fraction(midpoint_s)
            exact_limit = 1 + Fraction(extension_s) / Fraction(radius_s)
            normalization_error = unit_roundoff * exact_limit + Fraction(1, 2 ** 1075)
            rounded_limit = Fraction(math.nextafter(float(exact_limit + normalization_error), math.inf))
            assert exact_limit + normalization_error <= rounded_limit < 2
            rate_extension_s = math.nextafter(float(Fraction(radius_s) * (rounded_limit - 1)), math.inf)
            assert 1 + Fraction(rate_extension_s) / Fraction(radius_s) >= rounded_limit
            rows_km = tuple(tuple(float(value) for value in row) for row in coefficients_km)
            position_records[target].append((midpoint_s, radius_s, rows_km))
            normalization_rate_m_s = trajectory._spk_position_rate_bound(
                budget, rows_km, radius_s, extension_s=rate_extension_s,
            )
            uniform_error_m = Fraction(normalization_rate_m_s) * Fraction(radius_s) * normalization_error
            uniform_error_m += 1000 * sum((_spk_series_roundoff_bound(budget, row, rounded_limit)
                                          for row in rows_km), Fraction(0))
            reported_uniform_m = math.nextafter(float(uniform_error_m), math.inf)
            assert math.isfinite(reported_uniform_m) and Fraction(reported_uniform_m) >= uniform_error_m
            assert Fraction(reported_uniform_m) <= Fraction("0.001")  # Conditional supplied-record L1 m.
            uniform_evaluation_bounds_m[target].append(reported_uniform_m)
            if data_type == 2:
                # Uniform normalization error in velocity uses the exact second
                # derivative, not the position-rate bound or sampled velocities.
                values = [Fraction(1), rounded_limit]
                first_derivatives = [Fraction(0), Fraction(1)]
                second_derivatives = [Fraction(0), Fraction(0)]
                for degree in range(2, coefficient_count):
                    budget.check()
                    second_derivatives.append(4 * first_derivatives[-1] + 2 * rounded_limit * second_derivatives[-1] - second_derivatives[-2])
                    first_derivatives.append(2 * values[-1] + 2 * rounded_limit * first_derivatives[-1] - first_derivatives[-2])
                    values.append(2 * rounded_limit * values[-1] - values[-2])
                assert all(value >= 0 for value in second_derivatives)
                for degree in range(coefficient_count):
                    # Independent identity from the positive Chebyshev expansion
                    # of U_(n-1): T''_n = 2*n*(T'_(n-1) + T'_(n-3) + ...).
                    assert second_derivatives[degree] == 2 * degree * sum(
                        (first_derivatives[index] for index in range(degree - 1, 0, -2)), Fraction(0),
                    )
                curvature_km = sum((abs(Fraction(value)) * second_derivatives[degree]
                                    for row in rows_km for degree, value in enumerate(row)), Fraction(0))
                velocity_normalization_error_km_s = curvature_km * normalization_error / Fraction(radius_s)
                uniform_velocity_error_m_s = 1000 * (velocity_normalization_error_km_s + sum(
                    (_spk_type2_velocity_roundoff_bound_km_s(budget, row, radius_s, rounded_limit) for row in rows_km), Fraction(0),
                ))
                reported_velocity_m_s = math.nextafter(float(uniform_velocity_error_m_s), math.inf)
                assert math.isfinite(reported_velocity_m_s) and Fraction(reported_velocity_m_s) >= uniform_velocity_error_m_s
                assert reported_velocity_m_s <= 0.000001  # Conditional supplied-record L1 m/s.
                type2_uniform_velocity_bounds_m_s.append(reported_velocity_m_s)
            else:
                velocity_rows_km_s = tuple(tuple(float(value) for value in row)
                                           for row in record[2:].reshape(components, coefficient_count)[3:])
                derivative_weights = [Fraction(0)]
                previous, current = Fraction(0), Fraction(1)  # U_-1(q), U_0(q).
                for degree in range(1, coefficient_count):
                    budget.check()
                    derivative_weights.append(degree * current)
                    previous, current = current, 2 * rounded_limit * current - previous
                normalization_slope_km_s = sum((abs(Fraction(value)) * derivative_weights[degree]
                                                for row in velocity_rows_km_s for degree, value in enumerate(row)), Fraction(0))
                uniform_velocity_error_m_s = 1000 * (normalization_slope_km_s * normalization_error + sum(
                    (_spk_series_roundoff_bound(budget, row, rounded_limit) for row in velocity_rows_km_s), Fraction(0),
                ))
                reported_velocity_m_s = math.nextafter(float(uniform_velocity_error_m_s), math.inf)
                assert math.isfinite(reported_velocity_m_s) and Fraction(reported_velocity_m_s) >= uniform_velocity_error_m_s
                assert reported_velocity_m_s <= 0.000001  # Conditional stored-series L1 m/s.
                type3_uniform_velocity_bounds_m_s.append(reported_velocity_m_s)
            # Uniform L1 magnitude from coefficients, not from sampled states.
            magnitude_weights = [Fraction(1), rounded_limit]
            for degree in range(2, coefficient_count):
                budget.check()
                magnitude_weights.append(2 * rounded_limit * magnitude_weights[-1] - magnitude_weights[-2])
            polynomial_magnitude_km = sum((abs(Fraction(value)) * magnitude_weights[degree]
                                          for row in rows_km for degree, value in enumerate(row)), Fraction(0))
            native_magnitude_km = polynomial_magnitude_km + uniform_error_m / 1000
            native_magnitude_bounds_km[target].append(native_magnitude_km)
            if data_type == 2:
                polynomial_velocity_magnitude_km_s = sum((abs(Fraction(value)) * first_derivatives[degree]
                    for row in rows_km for degree, value in enumerate(row)), Fraction(0)) / Fraction(radius_s)
            else:
                polynomial_velocity_magnitude_km_s = sum((abs(Fraction(value)) * magnitude_weights[degree]
                    for row in velocity_rows_km_s for degree, value in enumerate(row)), Fraction(0))
            native_velocity_magnitude_km_s = polynomial_velocity_magnitude_km_s + uniform_velocity_error_m_s / 1000
            native_velocity_magnitudes_km_s[target].append(native_velocity_magnitude_km_s)
            uniform_velocity_errors_m_s[target].append(uniform_velocity_error_m_s)
            if native is not None:
                # Evaluate the supplied record itself, avoiding record-selection ambiguity.
                native_record = (ctypes.c_double * (size + 1))(float(size), *record)
                evaluator = native.spke02_ if data_type == 2 else native.spke03_
                midpoint_s, radius_s = float(record[0]), float(record[1])
                extension_s = 16 * math.ulp(midpoint_s)
                for probe_s in (midpoint_s - radius_s - extension_s, midpoint_s - radius_s,
                                midpoint_s, midpoint_s + radius_s / 3,
                                midpoint_s + radius_s, midpoint_s + radius_s + extension_s):
                    budget.check()
                    native_epoch = ctypes.c_double(probe_s)
                    state_km = (ctypes.c_double * 6)()
                    evaluator(ctypes.byref(native_epoch), native_record, state_km)
                    assert native.failed_c() == 0 and all(math.isfinite(value) for value in state_km)
                    assert sum((abs(Fraction(value)) for value in state_km[:3]), Fraction(0)) <= native_magnitude_km
                    assert sum((abs(Fraction(value)) for value in state_km[3:]), Fraction(0)) <= native_velocity_magnitude_km_s
                    exact_time = (Fraction(probe_s) - Fraction(midpoint_s)) / Fraction(radius_s)
                    assert Fraction(probe_s - midpoint_s) == Fraction(probe_s) - Fraction(midpoint_s)
                    rounded_time = Fraction((probe_s - midpoint_s) / radius_s)
                    assert abs(rounded_time - exact_time) <= normalization_error
                    assert abs(rounded_time) <= rounded_limit
                    basis = [Fraction(1), exact_time]
                    derivative_basis = [Fraction(0), Fraction(1)]
                    for degree in range(2, coefficient_count):
                        derivative_basis.append(2 * basis[-1] + 2 * exact_time * derivative_basis[-1]
                                                - derivative_basis[-2])
                        basis.append(2 * exact_time * basis[-1] - basis[-2])
                    error_m = Fraction(0)
                    velocity_error_m_s = Fraction(0)
                    exact_magnitude_km = Fraction(0)
                    exact_velocity_magnitude_km_s = Fraction(0)
                    for axis, row in enumerate(coefficients_km):
                        replay_km = _replay_spk_series(tuple(float(value) for value in row),
                                                       midpoint_s, radius_s, probe_s)
                        assert state_km[axis].hex() == replay_km.hex(), (target, index, probe_s, axis)
                        exact_km = sum((Fraction(value) * basis[degree]
                                        for degree, value in enumerate(row)), Fraction(0))
                        exact_magnitude_km += abs(exact_km)
                        error_m += abs(Fraction(state_km[axis]) - exact_km) * 1000
                        if data_type == 2:
                            replay_km_s = _replay_spk_type2_velocity(
                                tuple(float(value) for value in row), midpoint_s, radius_s, probe_s,
                            )
                            assert state_km[axis + 3].hex() == replay_km_s.hex(), (target, index, probe_s, axis)
                            exact_km_s = sum((Fraction(value) * derivative_basis[degree]
                                              for degree, value in enumerate(row)), Fraction(0)) / Fraction(radius_s)
                            velocity_error_m_s += abs(Fraction(state_km[axis + 3]) - exact_km_s) * 1000
                        else:
                            velocity_row_km_s = velocity_rows_km_s[axis]
                            replay_km_s = _replay_spk_series(velocity_row_km_s, midpoint_s, radius_s, probe_s)
                            assert state_km[axis + 3].hex() == replay_km_s.hex(), (target, index, probe_s, axis)
                            exact_km_s = sum((Fraction(value) * basis[degree]
                                              for degree, value in enumerate(velocity_row_km_s)), Fraction(0))
                            velocity_error_m_s += abs(Fraction(state_km[axis + 3]) - exact_km_s) * 1000
                        exact_velocity_magnitude_km_s += abs(exact_km_s)
                    assert exact_velocity_magnitude_km_s <= polynomial_velocity_magnitude_km_s
                    assert error_m <= Fraction("0.001"), (target, index, probe_s)  # L1 m, sampled only.
                    assert error_m <= uniform_error_m, (target, index, probe_s)
                    assert exact_magnitude_km <= polynomial_magnitude_km
                    max_evaluation_error_m[target] = max(max_evaluation_error_m[target], float(error_m))
                    evaluation_checks += 1
                    assert velocity_error_m_s <= Fraction("0.000001"), (target, index, probe_s)
                    assert velocity_error_m_s <= uniform_velocity_error_m_s, (target, index, probe_s)
                    if data_type == 2:
                        max_type2_evaluation_error_m_s = max(max_type2_evaluation_error_m_s, float(velocity_error_m_s))
                        type2_velocity_checks += 1
                    else:
                        max_type3_evaluation_error_m_s = max(max_type3_evaluation_error_m_s, float(velocity_error_m_s))
                        type3_velocity_checks += 1
            bound_m_s = trajectory._spk_position_rate_bound(
                budget, tuple(tuple(float(value) for value in row) for row in coefficients_km),
                float(record[1]),
            )
            rates_m_s[target].append(bound_m_s)
            extension_s = 16 * math.ulp(float(record[0]))
            extended_bound_m_s = trajectory._spk_position_rate_bound(
                budget, tuple(tuple(float(value) for value in row) for row in coefficients_km),
                float(record[1]), extension_s=extension_s,
            )
            assert extended_bound_m_s >= bound_m_s
            exact_q = 1 + Fraction(extension_s) / Fraction(record[1])
            extended_q = float(exact_q)
            if Fraction(extended_q) > exact_q:
                extended_q = math.nextafter(extended_q, 1.0)
            for x in (-extended_q, extended_q):
                derivative_m_s = np.polynomial.chebyshev.chebval(
                    x, np.polynomial.chebyshev.chebder(coefficients_km.T, axis=0),
                ) * (1000 / record[1])
                assert np.linalg.norm(derivative_m_s) <= extended_bound_m_s
            for sign in (-1, 1):
                epoch_s = Fraction(record[0]) + sign * Fraction(record[1])
                if not start_tdb_s < epoch_s < end_tdb_s:
                    continue
                # Store each side explicitly; segment file order need not be chronological.
                sides = joins.setdefault((target, epoch_s), {})
                assert sign not in sides, (target, epoch_s)
                assert math.ulp(float(epoch_s)) == math.ulp(midpoint_s)
                native_si_error_m = uniform_error_m + unit_roundoff * 1000 * native_magnitude_km + 3 * Fraction(1, 2 ** 1075)
                join_error_terms[target, epoch_s, sign] = (Fraction(extended_bound_m_s), native_si_error_m)
                endpoint_m = tuple(1000 * sum((Fraction(value) * sign ** degree
                                              for degree, value in enumerate(row)), Fraction(0))
                                   for row in coefficients_km)
                offset_s = Fraction(math.ulp(float(epoch_s)))
                assert Fraction(float(epoch_s)) == epoch_s and 0 < offset_s < Fraction(record[1])
                normalized_time = sign * (1 - offset_s / Fraction(record[1]))
                basis = [Fraction(1), normalized_time]
                for degree in range(2, coefficient_count):
                    basis.append(2 * normalized_time * basis[-1] - basis[-2])
                near_m = tuple(1000 * sum((Fraction(value) * basis[degree]
                                          for degree, value in enumerate(row)), Fraction(0))
                               for row in coefficients_km)
                query_s = float(epoch_s) - sign * float(offset_s)
                assert Fraction(query_s) == epoch_s - sign * offset_s
                join_frame, join_state_km, join_center = spice.spkpvn(handle, descriptor, query_s)
                assert (join_frame, join_center) == (1, expected_centers[target])
                assert np.all(np.isfinite(join_state_km))
                join_difference_m = float(np.linalg.norm(
                    np.asarray([float(value) for value in near_m]) - join_state_km[:3] * 1000,
                ))
                if join_difference_m > 0.001:
                    native_join_failures.append((target, float(epoch_s), sign, join_difference_m))
                max_join_position_difference_m = max(max_join_position_difference_m, join_difference_m)
                sides[sign] = (endpoint_m, near_m, bound_m_s, join_state_km[:3] * 1000)
            derivative_coefficients = np.polynomial.chebyshev.chebder(coefficients_km.T, axis=0)
            for normalized_time in (-1.0, -0.5, 0.0, 0.5, 1.0):
                derivative_m_s = np.polynomial.chebyshev.chebval(
                    normalized_time, derivative_coefficients,
                ) * (1000 / record[1])
                assert np.all(np.isfinite(derivative_m_s))
                assert np.linalg.norm(derivative_m_s) <= bound_m_s, (target, index)
            frame, state_km, center = spice.spkpvn(handle, descriptor, float(record[0]))
            assert (frame, center) == (1, expected_centers[target])
            assert np.all(np.isfinite(state_km))
            position_difference_m = float(np.linalg.norm(
                (np.polynomial.chebyshev.chebval(0.0, coefficients_km.T) - state_km[:3]) * 1000,
            ))
            assert position_difference_m <= 0.001, (target, index)
            max_position_difference_m = max(max_position_difference_m, position_difference_m)
            if data_type == 2:
                velocity_difference_m_s = float(np.linalg.norm(
                    (np.polynomial.chebyshev.chebval(0.0, derivative_coefficients) / record[1]
                     - state_km[3:]) * 1000,
                ))
                assert velocity_difference_m_s <= 0.000001, (target, index)
                max_type2_velocity_difference_m_s = max(max_type2_velocity_difference_m_s,
                                                       velocity_difference_m_s)

    assert endpoint_record_checks == (24 if native is not None else 0)
    assert evaluation_checks == (3300 if native is not None else 0)
    assert type2_velocity_checks == (1518 if native is not None else 0)
    assert len(type2_uniform_velocity_bounds_m_s) == 253
    assert len(type3_uniform_velocity_bounds_m_s) == 297
    assert type3_velocity_checks == (1782 if native is not None else 0)
    jump_observations: dict[int, list[tuple[float, float, bool]]] = {target: [] for target in expected_centers}
    native_join_envelopes: list[tuple[int, float, float, float]] = []
    native_join_envelope_checks = omitted_jump_failures = 0
    for (target, epoch_s), sides in sorted(joins.items()):
        budget.check()
        assert set(sides) == {-1, 1}, (target, epoch_s)
        left, right = sides[1], sides[-1]
        jump_m = sum((abs(a - b) for a, b in zip(left[0], right[0])), Fraction(0))
        motion_m = sum((abs(a - b) for a, b in zip(left[1], right[1])), Fraction(0))
        local_bound_m = Fraction(math.ulp(float(epoch_s))) * (Fraction(left[2]) + Fraction(right[2]))
        assert motion_m <= local_bound_m + jump_m, (target, epoch_s)
        left_rate, left_error = join_error_terms[target, epoch_s, 1]
        right_rate, right_error = join_error_terms[target, epoch_s, -1]
        half_width_s = 16 * Fraction(math.ulp(float(epoch_s)))
        assert Fraction(start_tdb_s) < epoch_s - half_width_s < epoch_s + half_width_s < Fraction(end_tdb_s)
        selection_pieces[target].append((epoch_s - half_width_s, epoch_s + half_width_s))
        arithmetic_and_motion_m = max(left_error, right_error) + (left_rate + right_rate) * half_width_s
        envelope_m = jump_m + arithmetic_and_motion_m
        reported_m = math.nextafter(float(envelope_m), math.inf)
        assert math.isfinite(reported_m) and Fraction(reported_m) >= envelope_m
        native_join_envelopes.append((target, float(epoch_s), float(half_width_s), reported_m))
        if native is not None:
            for side in (left, right):
                error_m = sum((abs(Fraction(value) - exact) for value, exact in zip(side[3], side[1])), Fraction(0))
                assert error_m <= envelope_m, (target, epoch_s)
                omitted_jump_failures += error_m > arithmetic_and_motion_m
                native_join_envelope_checks += 1
        if target in (499, 599):
            # Counterexample: just before the mathematical join, native values
            # agree with the other side instead. This is not a native-error bound.
            assert np.linalg.norm(left[3] - np.asarray([float(value) for value in right[1]])) <= 0.001
        jump_observations[target].append((float(epoch_s), float(jump_m), motion_m > local_bound_m))
    assert all(len(jump_observations[target]) == len(rates_m_s[target]) - 1 for target in expected_centers)
    assert len(joins) == 539
    assert len(internal_strip_keys) == 538
    assert set(joins) - internal_strip_keys == {(699, Fraction(986817600))}
    assert native_core_checks == (1100 if native is not None else 0)
    assert native_strip_endpoint_checks == (1076 if native is not None else 0)
    junction_s = 986817600.0
    saturn_segments = sorted((segment for segment in segments if segment[1] == 699), key=lambda segment: segment[3])
    left_segment, right_segment = saturn_segments
    assert left_segment[0] == right_segment[0]  # Same loaded file.
    assert left_segment[4] == right_segment[3] == junction_s
    assert left_segment[5] > right_segment[5]  # Left interval is later in DAF order.
    junction_epochs_s = [junction_s + offset * math.ulp(junction_s) for offset in range(-16, 17)]
    assert len(junction_epochs_s) == 33
    assert all(math.nextafter(a, math.inf) == b for a, b in zip(junction_epochs_s, junction_epochs_s[1:]))
    assert Fraction(junction_epochs_s[0]) == Fraction(junction_s) - 16 * Fraction(math.ulp(junction_s))
    assert Fraction(junction_epochs_s[-1]) == Fraction(junction_s) + 16 * Fraction(math.ulp(junction_s))
    native_priority_checks = 0
    for order in (junction_epochs_s, junction_epochs_s[::-1], junction_epochs_s[::2] + junction_epochs_s[1::2]):
        for probe_s in order:
            budget.check()
            eligible = [segment for segment in saturn_segments if segment[3] <= probe_s <= segment[4]]
            assert len(eligible) == (2 if probe_s == junction_s else 1)
            expected_segment = max(eligible, key=lambda segment: segment[5])
            assert expected_segment[5] == (left_segment[5] if probe_s <= junction_s else right_segment[5])
            if native is not None:
                selected_handle, found = ctypes.c_int(), ctypes.c_int()
                selected_descriptor = (ctypes.c_double * 5)()
                identifier = ctypes.create_string_buffer(41)
                native.spksfs_c(699, probe_s, 41, ctypes.byref(selected_handle), selected_descriptor,
                                identifier, ctypes.byref(found))
                assert native.failed_c() == 0 and found.value == 1
                assert selected_handle.value == expected_segment[0]
                assert bytes(selected_descriptor) == expected_segment[7].tobytes()
                handle, _, kind, _, _, begin, end, descriptor = expected_segment
                _, _, raw_size, raw_count = spice.dafgda(handle, end - 3, end)
                size, count = int(raw_size), int(raw_count)
                assert kind == 3 and raw_size == size == 122 and raw_count == count == 100
                selected_index = count - 1 if probe_s <= junction_s else 0
                address = begin + selected_index * size
                expected_record = spice.dafgda(handle, address, address + size - 1)
                selected_record = _read_native_spk_record(native, kind, handle, descriptor, probe_s, size)
                assert selected_record.tobytes() == expected_record.tobytes(), probe_s
                native_priority_checks += 1
    assert native_priority_checks == (99 if native is not None else 0)
    for target, pieces in selection_pieces.items():
        budget.check()
        assert len(pieces) == 2 * len(rates_m_s[target]) - 1
        covered_to_s = Fraction(start_tdb_s)
        for first_s, last_s in sorted(pieces):
            assert Fraction(start_tdb_s) <= first_s <= covered_to_s
            assert first_s < last_s <= Fraction(end_tdb_s)
            covered_to_s = max(covered_to_s, last_s)
        assert covered_to_s == Fraction(end_tdb_s)
    assert len(native_join_envelopes) == 539
    assert native_join_envelope_checks == (1078 if native is not None else 0)
    assert omitted_jump_failures >= (221 if native is not None else 0)
    assert len(native_join_failures) == 221
    assert {(target, epoch_s) for target, epoch_s, _, _ in native_join_failures} == {
        (target, float(epoch_s)) for target, epoch_s in joins if target in (499, 599)
    }
    assert all(sign == 1 for _, _, sign, _ in native_join_failures)

    switching_probes: list[tuple[int, float, int, float]] = []
    ambiguity_bounds: list[tuple[int, float, float]] = []
    exact_ambiguity_checks = 0
    native_record_checks = 0
    for target, records in switching_records.items():
        for left, right in zip(records, records[1:]):
            handle, descriptor, init_s, interval_s, index, left_record = left
            assert right[4] == index + 1
            right_record = right[5]
            if native is not None:
                # Both directories were checked before calling the raw record reader.
                assert len(left_record) == len(right_record) == 122
                assert spice.spkuds(descriptor)[3] == 3
            epoch_s = float(left_record[0] + left_record[1])
            assert epoch_s == right_record[0] - right_record[1]
            extension_s = 16 * math.ulp(epoch_s)
            rate_sum_m_s = sum((Fraction(trajectory._spk_position_rate_bound(
                budget, tuple(tuple(float(value) for value in row)
                              for row in record[2:].reshape(6, -1)[:3]),
                float(record[1]), extension_s=extension_s,
            )) for record in (left_record, right_record)), Fraction(0))
            endpoints = joins[(target, Fraction(epoch_s))]
            jump_m = sum((abs(a - b) for a, b in zip(endpoints[1][0], endpoints[-1][0])), Fraction(0))
            uniform_bound_m = jump_m + rate_sum_m_s * Fraction(extension_s)
            reported_bound_m = math.nextafter(float(uniform_bound_m), math.inf)
            assert math.isfinite(reported_bound_m) and Fraction(reported_bound_m) >= uniform_bound_m
            ambiguity_bounds.append((target, epoch_s, reported_bound_m))
            selected_offsets: list[int] = []
            max_error_m = 0.0
            for offset in range(-16, 17):
                budget.check()
                query_s = epoch_s + offset * math.ulp(epoch_s)
                if offset in (-16, -5, -4, -1, 0, 1, 16):
                    exact_positions_m: list[tuple[Fraction, ...]] = []
                    for record in (left_record, right_record):
                        rows = record[2:].reshape(6, -1)[:3]
                        x_exact = (Fraction(query_s) - Fraction(record[0])) / Fraction(record[1])
                        assert abs(x_exact) <= 1 + Fraction(extension_s) / Fraction(record[1])
                        basis = [Fraction(1), x_exact]
                        for degree in range(2, rows.shape[1]):
                            basis.append(2 * x_exact * basis[-1] - basis[-2])
                        exact_positions_m.append(tuple(
                            1000 * sum((Fraction(value) * basis[degree]
                                        for degree, value in enumerate(row)), Fraction(0)) for row in rows
                        ))
                    difference_m = sum((abs(a - b) for a, b in zip(*exact_positions_m)), Fraction(0))
                    motion_only_m = rate_sum_m_s * abs(Fraction(query_s) - Fraction(epoch_s))
                    assert difference_m <= jump_m + motion_only_m <= uniform_bound_m
                    assert difference_m > motion_only_m  # Omitting the source jump is unsafe.
                    exact_ambiguity_checks += 1
                if -4 <= offset < 0:
                    assert Fraction(query_s) - Fraction(init_s) < Fraction(epoch_s) - Fraction(init_s)
                    assert query_s - init_s == epoch_s - init_s
                # Candidate arithmetic replay, qualified against native values below.
                selected_index = math.floor((query_s - init_s) / interval_s)
                assert selected_index in (index, index + 1)
                selected_record = left_record if selected_index == index else right_record
                if native is not None:
                    actual_record = _read_native_spk_record(native, 3, handle, descriptor, query_s, 122)
                    assert actual_record.tobytes() == selected_record.tobytes()
                    native_record_checks += 1
                x = (query_s - selected_record[0]) / selected_record[1]
                predicted_m = np.polynomial.chebyshev.chebval(
                    x, selected_record[2:].reshape(6, -1)[:3].T,
                ) * 1000
                frame, state_km, center = spice.spkpvn(handle, descriptor, query_s)
                assert (frame, center) == (1, expected_centers[target])
                assert np.all(np.isfinite(state_km)) and np.all(np.isfinite(predicted_m))
                error_m = float(np.linalg.norm(predicted_m - state_km[:3] * 1000))
                assert error_m <= 0.001, (target, epoch_s, offset)
                other_record = right_record if selected_index == index else left_record
                other_m = np.polynomial.chebyshev.chebval(
                    (query_s - other_record[0]) / other_record[1],
                    other_record[2:].reshape(6, -1)[:3].T,
                ) * 1000
                assert np.linalg.norm(other_m - state_km[:3] * 1000) > 0.001
                max_error_m = max(max_error_m, error_m)
                if selected_index == index + 1:
                    selected_offsets.append(offset)
            assert selected_offsets == list(range(selected_offsets[0], 17))
            assert selected_offsets[0] == -4
            switching_probes.append((target, epoch_s, selected_offsets[0], max_error_m))
    assert len(switching_probes) == 221
    assert exact_ambiguity_checks == 1547
    assert native_record_checks == (7293 if native_record_readback else 0)
    assert sum(all_record_checks.values()) == (1628 if native_record_readback else 0)
    assert early_record_choices == {
        target: len(rates_m_s[target]) - 1 if native_record_readback and target != 699 else 0
        for target in expected_centers
    }

    chain_position_bounds_m: dict[int, float] = {}
    chain_add_scale_bounds_m: dict[int, float] = {}
    chain_velocity_bounds_m_s: dict[int, float] = {}
    chain_speed_bounds_m_s: dict[int, float] = {}
    velocity_arithmetic_controls = 0
    eta = Fraction(1, 2 ** 1075)
    for target in (10, 1, 2, 399, 301, 499, 599, 699):
        budget.check()
        center = expected_centers[target]
        chain = [target] if center == 0 else [target, center]
        assert expected_centers[chain[-1]] == 0
        magnitude_km = sum((max(native_magnitude_bounds_km[link]) for link in chain), Fraction(0))
        source_error_m = sum((Fraction(max(uniform_evaluation_bounds_m[link])) for link in chain), Fraction(0))
        addition_km = unit_roundoff * magnitude_km + 3 * eta if len(chain) == 2 else Fraction(0)
        assert magnitude_km <= Fraction(sys.float_info.max)
        assert 1000 * (magnitude_km + addition_km) <= Fraction(sys.float_info.max)
        conversion_m = unit_roundoff * 1000 * (magnitude_km + addition_km) + 3 * eta
        combined_m = source_error_m + 1000 * addition_km + conversion_m
        reported_m = math.nextafter(float(combined_m), math.inf)
        assert Fraction(reported_m) >= combined_m > source_error_m
        assert Fraction(reported_m) <= Fraction("0.001")  # Conditional position L1 m, not selection error.
        chain_position_bounds_m[target] = reported_m
        chain_add_scale_bounds_m[target] = math.nextafter(float(1000 * addition_km + conversion_m), math.inf)
        # Independent arithmetic controls at magnitude limits, not mission states.
        control_values_km: list[float] = []
        for link in chain:
            limit_km = max(native_magnitude_bounds_km[link]) / 3
            value_km = float(limit_km)
            if Fraction(value_km) > limit_km:
                value_km = math.nextafter(value_km, 0.0)
            assert 3 * abs(Fraction(value_km)) <= max(native_magnitude_bounds_km[link])
            control_values_km.append(value_km)
        for sign in (-1, 1):
            values_km = [control_values_km[0]] + [sign * value for value in control_values_km[1:]]
            exact_sum_km = sum((Fraction(value) for value in values_km), Fraction(0))
            actual_m = sum(values_km) * 1000
            assert 3 * abs(Fraction(actual_m) - 1000 * exact_sum_km) <= 1000 * addition_km + conversion_m

        # Same inspected add-then-scale path, with native km/s magnitudes.
        magnitude_km_s = sum((max(native_velocity_magnitudes_km_s[link]) for link in chain), Fraction(0))
        source_error_m_s = sum((max(uniform_velocity_errors_m_s[link]) for link in chain), Fraction(0))
        addition_km_s = unit_roundoff * magnitude_km_s + 3 * eta if len(chain) == 2 else Fraction(0)
        assert magnitude_km_s <= Fraction(sys.float_info.max)
        assert 1000 * (magnitude_km_s + addition_km_s) <= Fraction(sys.float_info.max)
        conversion_m_s = unit_roundoff * 1000 * (magnitude_km_s + addition_km_s) + 3 * eta
        combined_m_s = source_error_m_s + 1000 * addition_km_s + conversion_m_s
        reported_m_s = math.nextafter(float(combined_m_s), math.inf)
        assert Fraction(reported_m_s) >= combined_m_s > source_error_m_s
        assert Fraction(reported_m_s) <= Fraction("0.000001")  # Conditional SSB/J2000 L1 m/s.
        chain_velocity_bounds_m_s[target] = reported_m_s
        speed_m_s = 1000 * (magnitude_km_s + addition_km_s) + conversion_m_s
        reported_speed_m_s = math.nextafter(float(speed_m_s), math.inf)
        assert math.isfinite(reported_speed_m_s) and Fraction(reported_speed_m_s) >= speed_m_s
        chain_speed_bounds_m_s[target] = reported_speed_m_s
        control_values_km_s: list[float] = []
        for link in chain:
            limit_km_s = max(native_velocity_magnitudes_km_s[link]) / 3
            value_km_s = float(limit_km_s)
            if Fraction(value_km_s) > limit_km_s:
                value_km_s = math.nextafter(value_km_s, 0.0)
            assert 3 * abs(Fraction(value_km_s)) <= max(native_velocity_magnitudes_km_s[link])
            control_values_km_s.append(value_km_s)
        for sign in (-1, 1):
            values_km_s = [control_values_km_s[0]] + [sign * value for value in control_values_km_s[1:]]
            exact_sum_km_s = sum((Fraction(value) for value in values_km_s), Fraction(0))
            actual_m_s = sum(values_km_s) * 1000
            assert 3 * abs(Fraction(actual_m_s) - 1000 * exact_sum_km_s) <= 1000 * addition_km_s + conversion_m_s
            assert 3 * abs(Fraction(actual_m_s)) <= Fraction(reported_speed_m_s)
            velocity_arithmetic_controls += 1
    assert velocity_arithmetic_controls == 16
    assert set(chain_velocity_bounds_m_s) == set(chain_speed_bounds_m_s) == set(chain_position_bounds_m)

    # Moon/Earth joins coincide: neither link's representation error may be omitted.
    moon_epochs_s = {epoch for target, epoch in joins if target == 301}
    earth_epochs_s = {epoch for target, epoch in joins if target == 399}
    assert moon_epochs_s == earth_epochs_s and len(moon_epochs_s) == 73
    moon_chain_join_bounds_m: list[tuple[float, float]] = []
    moon_chain_join_checks = 0
    for epoch_s in sorted(moon_epochs_s):
        budget.check()
        half_width_s = 16 * Fraction(math.ulp(float(epoch_s)))
        jump_sum_m = sum((abs(a - b) for link in (301, 399)
                          for a, b in zip(joins[link, epoch_s][1][0], joins[link, epoch_s][-1][0])), Fraction(0))
        rate_sum_m_s = sum((join_error_terms[link, epoch_s, sign][0]
                            for link in (301, 399) for sign in (-1, 1)), Fraction(0))
        envelope_m = jump_sum_m + rate_sum_m_s * half_width_s + Fraction(chain_position_bounds_m[301])
        reported_m = math.nextafter(float(envelope_m), math.inf)
        assert math.isfinite(reported_m) and Fraction(reported_m) >= envelope_m
        moon_chain_join_bounds_m.append((float(epoch_s), reported_m))
        # Exact rational sums retain cancellation; the bound assumes none.
        endpoint_branches_m = [tuple(a + b for a, b in zip(
            joins[301, epoch_s][moon_sign][0], joins[399, epoch_s][earth_sign][0],
        )) for moon_sign in (-1, 1) for earth_sign in (-1, 1)]
        for left in endpoint_branches_m:
            for right in endpoint_branches_m:
                assert sum((abs(a - b) for a, b in zip(left, right)), Fraction(0)) <= jump_sum_m
        for sign in (-1, 1):
            query_s = float(epoch_s) - sign * math.ulp(float(epoch_s))
            exact_m = tuple(a + b for a, b in zip(
                joins[301, epoch_s][sign][1], joins[399, epoch_s][sign][1],
            ))
            state_m = spice.spkssb(301, query_s, "J2000")[:3] * 1000
            assert np.all(np.isfinite(state_m))
            error_m = sum((abs(Fraction(value) - exact) for value, exact in zip(state_m, exact_m)), Fraction(0))
            assert error_m <= envelope_m, (epoch_s, sign, float(error_m), reported_m)
            moon_chain_join_checks += 1
    assert moon_chain_join_checks == 146

    chain_join_bounds_m: dict[int, list[tuple[float, float, int]]] = {}
    motion_samples: dict[int, list[tuple[float, np.ndarray, Fraction]]] = {}
    chain_join_checks = 0
    for target in chain_position_bounds_m:
        center = expected_centers[target]
        chain = [target] if center == 0 else [target, center]
        epochs_s = sorted({epoch for link, epoch in joins if link in chain})
        # Distinct strips do not overlap; simultaneous joins are grouped once.
        assert all(b - a > 16 * (Fraction(math.ulp(float(a))) + Fraction(math.ulp(float(b))))
                   for a, b in zip(epochs_s, epochs_s[1:]))
        chain_join_bounds_m[target] = []
        motion_samples[target] = []
        for epoch_s in epochs_s:
            budget.check()
            half_width_s = 16 * Fraction(math.ulp(float(epoch_s)))
            active_links = [link for link in chain if (link, epoch_s) in joins]
            assert active_links
            jump_m = sum((abs(a - b) for link in active_links
                          for a, b in zip(joins[link, epoch_s][1][0], joins[link, epoch_s][-1][0])), Fraction(0))
            rates_m_s_sum = sum((join_error_terms[link, epoch_s, sign][0]
                                for link in active_links for sign in (-1, 1)), Fraction(0))
            envelope_m = jump_m + rates_m_s_sum * half_width_s + Fraction(chain_position_bounds_m[target])
            reported_m = math.nextafter(float(envelope_m), math.inf)
            assert math.isfinite(reported_m) and Fraction(reported_m) >= envelope_m
            chain_join_bounds_m[target].append((float(epoch_s), reported_m, len(active_links)))
            for sign in (-1, 1):
                query_s = float(epoch_s) - sign * math.ulp(float(epoch_s))
                exact_links_m: list[tuple[Fraction, ...]] = []
                for link in chain:
                    if link in active_links:
                        exact_links_m.append(joins[link, epoch_s][sign][1])
                        continue
                    # The entire event strip must fit one qualified record core.
                    records = [(mid, radius, rows) for mid, radius, rows in position_records[link]
                               if Fraction(mid) - Fraction(radius) + 16 * Fraction(math.ulp(mid))
                               <= epoch_s - half_width_s
                               and epoch_s + half_width_s
                               <= Fraction(mid) + Fraction(radius) - 16 * Fraction(math.ulp(mid))]
                    assert len(records) == 1, (target, link, epoch_s)
                    midpoint_s, radius_s, rows_km = records[0]
                    x = (Fraction(query_s) - Fraction(midpoint_s)) / Fraction(radius_s)
                    assert abs(x) < 1
                    basis = [Fraction(1), x]
                    for degree in range(2, len(rows_km[0])):
                        basis.append(2 * x * basis[-1] - basis[-2])
                    exact_links_m.append(tuple(1000 * sum((Fraction(value) * basis[degree]
                        for degree, value in enumerate(row)), Fraction(0)) for row in rows_km))
                exact_m = tuple(sum(axis_values, Fraction(0)) for axis_values in zip(*exact_links_m))
                state_m = spice.spkssb(target, query_s, "J2000")[:3] * 1000
                assert np.all(np.isfinite(state_m))
                error_m = sum((abs(Fraction(value) - exact) for value, exact in zip(state_m, exact_m)), Fraction(0))
                assert error_m <= envelope_m, (target, epoch_s, sign, float(error_m), reported_m)
                motion_samples[target].append((query_s, state_m.copy(), Fraction(reported_m)))
                chain_join_checks += 1
    assert chain_join_checks == 2 * sum(len(values) for values in chain_join_bounds_m.values())
    assert [(epoch, bound) for epoch, bound, count in chain_join_bounds_m[301] if count == 2] == moon_chain_join_bounds_m

    motion_checks = 0
    body_reach_checks = 0
    full_interval_motion_bounds_m: dict[int, float] = {}
    full_interval_body_reach_m: dict[int, float] = {}
    for target, samples in motion_samples.items():
        center = expected_centers[target]
        chain = [target] if center == 0 else [target, center]
        rate_m_s = sum((Fraction(max(rates_m_s[link])) for link in chain), Fraction(0))
        source_jumps = [(epoch, sum((abs(a - b) for a, b in zip(sides[1][0], sides[-1][0])), Fraction(0)))
                        for (link, epoch), sides in joins.items() if link in chain]
        for query_s in (start_tdb_s, end_tdb_s):
            budget.check()
            # At candidate endpoints, every source link is in a qualified core.
            for link in chain:
                assert sum(Fraction(mid) - Fraction(radius) + 16 * Fraction(math.ulp(mid)) <= Fraction(query_s)
                           <= Fraction(mid) + Fraction(radius) - 16 * Fraction(math.ulp(mid))
                           for mid, radius, _ in position_records[link]) == 1
            state_m = spice.spkssb(target, query_s, "J2000")[:3] * 1000
            assert np.all(np.isfinite(state_m))
            samples.append((query_s, state_m, Fraction(chain_position_bounds_m[target])))
        samples.sort(key=lambda sample: sample[0])
        assert len(samples) == 2 * len(chain_join_bounds_m[target]) + 2
        for first, last in [*zip(samples, samples[1:]), (samples[0], samples[-1])]:
            budget.check()
            a_s, b_s = Fraction(first[0]), Fraction(last[0])
            assert a_s < b_s
            jumps_m = sum((jump for epoch, jump in source_jumps if a_s <= epoch <= b_s), Fraction(0))
            # Piecewise exact motion plus both native endpoint errors; no continuity assumption.
            bound_m = rate_m_s * (b_s - a_s) + jumps_m + first[2] + last[2]
            displacement_m = sum((abs(Fraction(b) - Fraction(a)) for a, b in zip(first[1], last[1])), Fraction(0))
            assert displacement_m <= bound_m, (target, first[0], last[0])
            motion_checks += 1
            # Enclose every intermediate epoch, including error strips not at the endpoints.
            overlapping_errors_m = [Fraction(error) for epoch, error, _ in chain_join_bounds_m[target]
                                    if Fraction(epoch) - 16 * Fraction(math.ulp(epoch)) <= b_s
                                    and Fraction(epoch) + 16 * Fraction(math.ulp(epoch)) >= a_s]
            interval_error_m = max([Fraction(chain_position_bounds_m[target]), *overlapping_errors_m])
            assert interval_error_m >= first[2] and interval_error_m >= last[2]
            radius_m = rate_m_s * (b_s - a_s) + jumps_m + first[2] + interval_error_m
            assert radius_m >= bound_m
            for query_s, state_m, _ in samples:
                if first[0] <= query_s <= last[0]:
                    budget.check()
                    offset_m = sum((abs(Fraction(b) - Fraction(a)) for a, b in zip(first[1], state_m)), Fraction(0))
                    assert offset_m <= radius_m, (target, first[0], last[0], query_s)
                    body_reach_checks += 1
            if first[0] == start_tdb_s and last[0] == end_tdb_s:
                reported_m = math.nextafter(float(bound_m), math.inf)
                assert math.isfinite(reported_m) and Fraction(reported_m) >= bound_m
                full_interval_motion_bounds_m[target] = reported_m
                assert interval_error_m > max(first[2], last[2])  # Endpoint errors alone miss interior strips.
                reported_radius_m = math.nextafter(float(radius_m), math.inf)
                assert math.isfinite(reported_radius_m) and Fraction(reported_radius_m) >= radius_m
                full_interval_body_reach_m[target] = reported_radius_m
    assert motion_checks == chain_join_checks + 16
    assert set(full_interval_motion_bounds_m) == set(chain_position_bounds_m)
    assert body_reach_checks == 3 * chain_join_checks + 32
    assert set(full_interval_body_reach_m) == set(chain_position_bounds_m)

    coast_durations_s = (1 / 64, 1 / 32, 1 / 16, 1 / 8, 1.0)
    coast_body_reaches_m: dict[float, dict[str, float]] = {}
    body_ids = dict(zip(trajectory.PHYSICAL_BODY_NAMES, (10, 1, 2, 399, 301, 499, 599, 699), strict=True))
    affine_links: dict[int, tuple[tuple[Fraction, ...], tuple[Fraction, ...], Fraction]] = {}
    for link, records in position_records.items():
        selected = [(mid, radius, rows) for mid, radius, rows in records
                    if Fraction(mid) - Fraction(radius) + 16 * Fraction(math.ulp(mid)) <= Fraction(start_tdb_s)
                    and Fraction(start_tdb_s) + 1 <= Fraction(mid) + Fraction(radius) - 16 * Fraction(math.ulp(mid))]
        assert len(selected) == 1, (link, "affine interval must fit one qualified core")
        mid, radius, rows = selected[0]
        affine_links[link] = _spk_position_affine_data(budget, rows, mid, radius, start_tdb_s, 1.0)
    affine_curvature_bounds_m_s2: dict[str, float] = {}
    source_affine_motion: dict[str, tuple[tuple[Fraction, ...], Fraction]] = {}
    source_affine_positions_m: dict[str, tuple[Fraction, ...]] = {}
    affine_native_checks = 0
    for body, target in body_ids.items():
        center = expected_centers[target]
        chain = [target] if center == 0 else [target, center]
        position = tuple(sum((affine_links[link][0][axis] for link in chain), Fraction(0)) for axis in range(3))
        slope = tuple(sum((affine_links[link][1][axis] for link in chain), Fraction(0)) for axis in range(3))
        curvature = sum((affine_links[link][2] for link in chain), Fraction(0))
        source_affine_motion[body] = (slope, curvature)
        source_affine_positions_m[body] = position
        reported_curvature = math.nextafter(float(curvature), math.inf)
        assert math.isfinite(reported_curvature) and Fraction(reported_curvature) >= curvature
        affine_curvature_bounds_m_s2[body] = reported_curvature
        for duration_s in coast_durations_s:
            budget.check()
            native_position = spice.spkssb(target, start_tdb_s + duration_s, "J2000")[:3] * 1000
            assert np.all(np.isfinite(native_position))
            residual = sum((abs(Fraction(observed) - initial - velocity * Fraction(duration_s))
                            for observed, initial, velocity in zip(native_position, position, slope, strict=True)), Fraction(0))
            assert residual <= curvature * Fraction(duration_s)**2 / 2 + Fraction(chain_position_bounds_m[target]), body
            affine_native_checks += 1
    assert len(affine_links) == 11 and affine_native_checks == 40
    print(json.dumps({"position_polynomial_acceleration_l1_bound_m_s2": affine_curvature_bounds_m_s2,
                      "affine_native_position_checks": affine_native_checks}, sort_keys=True, allow_nan=False))
    for duration_s in coast_durations_s:
        assert start_tdb_s + duration_s <= end_tdb_s
        assert Fraction(start_tdb_s + duration_s) - Fraction(start_tdb_s) == Fraction(duration_s)
        coast_body_reaches_m[duration_s] = {}
        for body, target in body_ids.items():
            budget.check()
            center = expected_centers[target]
            chain = [target] if center == 0 else [target, center]
            rate_m_s = sum((Fraction(max(rates_m_s[link])) for link in chain), Fraction(0))
            # Deliberately overcount every candidate-window jump, not only local joins.
            jumps_m = sum((abs(a - b) for (link, _), sides in joins.items() if link in chain
                           for a, b in zip(sides[1][0], sides[-1][0])), Fraction(0))
            interval_error_m = max([Fraction(chain_position_bounds_m[target]),
                                    *(Fraction(error) for _, error, _ in chain_join_bounds_m[target])])
            reach_m = rate_m_s * Fraction(duration_s) + jumps_m + Fraction(chain_position_bounds_m[target]) + interval_error_m
            reported_reach_m = math.nextafter(float(reach_m), math.inf)
            assert math.isfinite(reported_reach_m) and Fraction(reported_reach_m) >= reach_m
            coast_body_reaches_m[duration_s][body] = reported_reach_m
    assert all(motion_samples[target][0][0] == start_tdb_s for target in body_ids.values())
    coast_domains = _check_conditional_full_force_coast_domains(
        budget, start_tdb_s, end_tdb_s, coast_body_reaches_m, chain_speed_bounds_m_s[10],
        {body: motion_samples[target][0][1] for body, target in body_ids.items()},
        {body: float(motion_samples[target][0][2]) for body, target in body_ids.items()},
        chain_velocity_bounds_m_s[10],
        source_affine_motion=source_affine_motion, source_affine_coverage_s=1.0,
        source_affine_positions_m=source_affine_positions_m,
        run_native_controls=native_record_readback,
    )

    common = SPICEDOUBLE_CELL(2)
    spice.wninsd(start_tdb_s, end_tdb_s, common)
    observations: dict[int, list[tuple[float, float]]] = {}
    for target in expected_centers:
        # spkcov merges into its supplied window across all loaded files.
        coverage = SPICEDOUBLE_CELL(10000)
        for path, _, _, _ in files:
            budget.check()
            spice.spkcov(path, target, coverage)
        intervals = [spice.wnfetd(coverage, i) for i in range(spice.wncard(coverage))]
        assert intervals and all(math.isfinite(value) for pair in intervals for value in pair)
        assert spice.wnincd(start_tdb_s, end_tdb_s, coverage), (target, intervals)
        common = spice.wnintd(common, coverage)
        observations[target] = intervals
    assert spice.wncard(common) == 1
    assert spice.wnfetd(common, 0) == (start_tdb_s, end_tdb_s)

    # Endpoint membership alone must not accept an interior gap.
    gap = SPICEDOUBLE_CELL(4)
    midpoint_tdb_s = (start_tdb_s + end_tdb_s) / 2
    spice.wninsd(start_tdb_s, midpoint_tdb_s - 1.0, gap)
    spice.wninsd(midpoint_tdb_s + 1.0, end_tdb_s, gap)
    assert spice.wnincd(start_tdb_s, start_tdb_s, gap)
    assert spice.wnincd(end_tdb_s, end_tdb_s, gap)
    assert not spice.wnincd(start_tdb_s, end_tdb_s, gap)
    missing = SPICEDOUBLE_CELL(10000)
    for path, _, _, _ in files:
        spice.spkcov(path, -2147483647, missing)
    assert spice.wncard(missing) == 0
    assert not spice.wnincd(start_tdb_s, end_tdb_s, missing)
    assert not spice.failed()
    assert kernels_before == [spice.kdata(i, "ALL") for i in range(spice.ktotal("ALL"))]
    budget.check()
    assert budget.native_arc_propagations == (7 if native_record_readback else 0)
    # Hypothetical uniform reuse, not proof these controls apply elsewhere.
    control_duration = Fraction(1, 64)
    assert len(coast_domains) == 12
    assert {(domain["center"], Fraction(domain["duration_s"]),
             domain["position_domain_radius_m"], domain["velocity_domain_radius_m_s"])
            for domain in coast_domains if domain["conditional_domain_closed"]} == {
        ("Moon", control_duration, 1000.0, 0.1),
        ("Mars", control_duration, 1000.0, 0.1),
        ("Mars", 2 * control_duration, 1000.0, 0.1),
        ("Mars", 4 * control_duration, 2000.0, 0.25),
        ("Mars", 8 * control_duration, 4000.0, 0.5),
    }
    interval_duration = Fraction(end_tdb_s) - Fraction(start_tdb_s)
    uniform_arc_count = math.ceil(interval_duration / control_duration)
    assert (uniform_arc_count - 1) * control_duration < interval_duration <= uniform_arc_count * control_duration
    assert uniform_arc_count == 1611124364 > 228
    assert 228 * control_duration == Fraction(57, 16)  # Even granting all operation arcs to one coast.
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "time": "TDB seconds since J2000",
        "candidate_interval_tdb_s": [start_tdb_s, end_tdb_s],
        "hypothetical_uniform_control_tiling": {
            "scope": "One native arc per equal short coast; not a safety certificate or adaptive-method lower bound",
            "control_duration_s": float(control_duration),
            "minimum_native_arcs_for_this_uniform_strategy": uniform_arc_count,
            "production_operation_native_arc_limit": 228,
            "covered_duration_at_operation_limit_s": float(228 * control_duration),
            "fits_operation_arc_limit": False,
            "excludes": ["retries", "discarded_parents", "burns", "targeting", "independent_diagnostics"],
        },
        "spk_files": [Path(entry[0]).name for entry in files],
        "spk_registration_count": len(registrations),
        "total_segments": total_segments, "overlapping_chain_segments": segment_counts,
        "coverage_intervals_tdb_s": observations, "chain_centers": expected_centers,
        "position_rate_bounds_by_target": {
            target: {"record_count": len(values), "min_m_s": min(values), "max_m_s": max(values)}
            for target, values in rates_m_s.items()
        },
        "record_midpoint_max_position_difference_m": max_position_difference_m,
        "native_record_evaluation_checks": evaluation_checks,
        "native_record_evaluation_max_l1_error_m": max_evaluation_error_m if native is not None else None,
        "conditional_uniform_evaluation_bound_m": {
            target: {"record_count": len(values), "minimum": min(values), "maximum": max(values)}
            for target, values in uniform_evaluation_bounds_m.items()
        },
        "conditional_chain_position_bound_m": chain_position_bounds_m,
        "conditional_chain_add_scale_bound_m": chain_add_scale_bounds_m,
        "conditional_chain_velocity_bound_m_s": chain_velocity_bounds_m_s,
        "conditional_chain_speed_bound_m_s": chain_speed_bounds_m_s,
        "conditional_full_force_coast_domains": coast_domains,
        "velocity_arithmetic_controls": velocity_arithmetic_controls,
        "moon_chain_join_fields": ["epoch_tdb_s", "conditional_l1_bound_m"],
        "moon_chain_join_bounds": moon_chain_join_bounds_m,
        "moon_chain_join_checks": moon_chain_join_checks,
        "chain_join_fields": ["epoch_tdb_s", "conditional_l1_bound_m", "joining_link_count"],
        "chain_join_bounds": chain_join_bounds_m,
        "chain_join_checks": chain_join_checks,
        "two_epoch_motion_checks": motion_checks,
        "conditional_full_interval_displacement_bound_m": full_interval_motion_bounds_m,
        "body_reach_checks": body_reach_checks,
        "conditional_full_interval_body_reach_m": full_interval_body_reach_m,
        "record_join_fields": ["epoch_tdb_s", "exact_position_jump_l1_m", "jump_omission_fails"],
        "record_joins_by_target": jump_observations,
        "record_join_max_position_difference_m": max_join_position_difference_m,
        "native_join_envelope_fields": ["target", "epoch_tdb_s", "half_width_s", "conditional_l1_bound_m"],
        "native_join_envelopes": native_join_envelopes,
        "native_join_envelope_checks": native_join_envelope_checks,
        "native_selection_core_endpoint_checks": native_core_checks,
        "native_selection_strip_endpoint_checks": native_strip_endpoint_checks,
        "internal_record_strip_count": len(internal_strip_keys),
        "segment_priority_strip_target_epoch": [699, 986817600.0],
        "segment_priority_distinct_epoch_count": len(junction_epochs_s),
        "native_segment_priority_and_record_checks": native_priority_checks,
        "native_join_envelope_omitted_jump_failures": omitted_jump_failures,
        "native_join_parity_failure_fields": ["target", "epoch_tdb_s", "record_endpoint_sign", "error_m"],
        "native_join_parity_failures": native_join_failures,
        "native_join_parity_tolerance_m": 0.001,
        "record_switch_fields": ["target", "boundary_tdb_s", "first_right_record_offset_ulp", "max_replay_error_m"],
        "record_switch_probes": switching_probes,
        "exact_branch_ambiguity_fields": ["target", "boundary_tdb_s", "position_l1_bound_m"],
        "exact_branch_ambiguity_bounds": ambiguity_bounds,
        "exact_branch_ambiguity_checks": exact_ambiguity_checks,
        "native_selected_record_bitwise_checks": native_record_checks,
        "all_chain_native_record_checks": all_record_checks,
        "all_chain_early_record_choices": early_record_choices,
        "conditional_index_margin_fields": ["target", "segment_start_tdb_s", "segment_end_tdb_s", "time_margin_s"],
        "conditional_index_margins": index_roundoff_margins,
        "type2_midpoint_max_velocity_difference_m_s": max_type2_velocity_difference_m_s,
        "type2_supplied_record_velocity_checks": type2_velocity_checks,
        "type2_conditional_max_uniform_velocity_bound_m_s": max(type2_uniform_velocity_bounds_m_s),
        "type2_supplied_record_max_velocity_error_m_s": max_type2_evaluation_error_m_s,
        "type3_conditional_max_uniform_velocity_bound_m_s": max(type3_uniform_velocity_bounds_m_s),
        "type3_supplied_record_velocity_checks": type3_velocity_checks,
        "type3_supplied_record_max_velocity_error_m_s": max_type3_evaluation_error_m_s,
        "frame": "J2000, each target relative to its listed center; chains end at SSB",
        "scope": "Coverage and exact per-record position-rate bounds, not composed motion or safety",
    }, sort_keys=True, allow_nan=False))


def _ballistic_endpoint_error_bound_m(
    initial_state: np.ndarray, final_position_m: np.ndarray,
    duration_s: float, acceleration_bound_m_s2: float,
) -> Fraction:
    """Bound endpoint error in SI/SSB/J2000, conditional on an ideal force bound."""
    assert initial_state.shape == (6,) and final_position_m.shape == (3,)
    assert initial_state.dtype == final_position_m.dtype == np.dtype("float64")
    assert np.all(np.isfinite(initial_state)) and np.all(np.isfinite(final_position_m))
    assert all(type(value) is float and math.isfinite(value) and value >= 0
               for value in (duration_s, acceleration_bound_m_s2))
    residual_m = sum((abs(Fraction(final_position_m[axis]) - Fraction(initial_state[axis])
                         - Fraction(initial_state[axis + 3]) * Fraction(duration_s)) for axis in range(3)), Fraction(0))
    return residual_m + Fraction(acceleration_bound_m_s2) * Fraction(duration_s)**2 / 2


@pytest.mark.parametrize("duration_s", [1 / 64, 0.3, 0.5])
def test_ballistic_residual_certificate_attains_constant_acceleration_error(duration_s: float) -> None:
    # Exact SI control x(t)=x0+64*t+t^2, with A=2 m/s^2 and a 0.5 m
    # deliberately wrong numerical displacement opposite to acceleration.
    initial_m, speed_m_s = 1e12, 64.0
    approximate_m = initial_m + speed_m_s * duration_s - 0.5
    true_m = Fraction(initial_m) + 64 * Fraction(duration_s) + Fraction(duration_s)**2
    certificate_m = _ballistic_endpoint_error_bound_m(
        np.asarray([initial_m, 0.0, 0.0, speed_m_s, 0.0, 0.0]),
        np.asarray([approximate_m, 0.0, 0.0]), duration_s, 2.0,
    )
    assert abs(Fraction(approximate_m) - true_m) == certificate_m
    assert certificate_m > Fraction("0.001")  # Cannot accept this corrupted endpoint.


def _coast_endpoint_velocity_error_bound_m_s(
    initial_velocity_m_s: np.ndarray, final_velocity_m_s: np.ndarray,
    duration_s: float, acceleration_bound_m_s2: float,
) -> Fraction:
    """Bound SI/SSB/J2000 endpoint velocity error using a conditional force norm."""
    assert initial_velocity_m_s.shape == final_velocity_m_s.shape == (3,)
    assert initial_velocity_m_s.dtype == final_velocity_m_s.dtype == np.dtype("float64")
    assert np.all(np.isfinite(initial_velocity_m_s)) and np.all(np.isfinite(final_velocity_m_s))
    assert all(type(value) is float and math.isfinite(value) and value >= 0
               for value in (duration_s, acceleration_bound_m_s2))
    residual_m_s = sum((abs(Fraction(final) - Fraction(initial))
                        for initial, final in zip(initial_velocity_m_s, final_velocity_m_s, strict=True)), Fraction(0))
    return residual_m_s + Fraction(acceleration_bound_m_s2) * Fraction(duration_s)


@pytest.mark.parametrize(("duration_s", "acceleration_m_s2"), [(0.0, 2.0), (0.25, 0.0), (1 / 64, 2.0), (0.3, 2.0)])
def test_coast_velocity_certificate_attains_constant_acceleration_error(
    duration_s: float, acceleration_m_s2: float,
) -> None:
    # Exact v(t)=64+A*t; the corrupted endpoint is 0.5 m/s below v(0).
    bound_m_s = _coast_endpoint_velocity_error_bound_m_s(
        np.asarray([64.0, 0.0, 0.0]), np.asarray([63.5, 0.0, 0.0]), duration_s, acceleration_m_s2,
    )
    true_m_s = Fraction(64) + Fraction(acceleration_m_s2) * Fraction(duration_s)
    assert abs(Fraction(63.5) - true_m_s) == bound_m_s
    assert bound_m_s > Fraction("0.000001")


def test_coast_velocity_certificate_can_be_unresolved_for_exact_endpoint() -> None:
    duration_s = 1 / 64
    exact_final_m_s = 64.0 + 2.0 * duration_s
    assert Fraction(exact_final_m_s) == Fraction(64) + 2 * Fraction(duration_s)
    bound_m_s = _coast_endpoint_velocity_error_bound_m_s(
        np.asarray([64.0, 0.0, 0.0]), np.asarray([exact_final_m_s, 0.0, 0.0]), duration_s, 2.0,
    )
    assert bound_m_s == 4 * Fraction(duration_s) > Fraction("0.000001")
    # An upper bound exceeding a gate is not evidence of actual error.


def _anchored_coast_velocity_error_bound_m_s(
    initial_velocity_m_s: np.ndarray, final_velocity_m_s: np.ndarray,
    anchor_acceleration_m_s2: np.ndarray, duration_s: float,
    anchor_error_m_s2: Fraction, force_variation_m_s2: Fraction,
) -> Fraction:
    """Bound SI/SSB/J2000 velocity error, conditional on initial/interval force bounds."""
    for vector in (initial_velocity_m_s, final_velocity_m_s, anchor_acceleration_m_s2):
        assert vector.shape == (3,) and vector.dtype == np.dtype("float64") and np.all(np.isfinite(vector))
    assert type(duration_s) is float and math.isfinite(duration_s) and duration_s >= 0
    assert all(isinstance(value, Fraction) and value >= 0 for value in (anchor_error_m_s2, force_variation_m_s2))
    duration = Fraction(duration_s)
    residual_m_s = sum((abs(Fraction(final) - Fraction(initial) - Fraction(acceleration) * duration)
                        for initial, final, acceleration in zip(initial_velocity_m_s, final_velocity_m_s,
                                                                anchor_acceleration_m_s2, strict=True)), Fraction(0))
    return residual_m_s + (anchor_error_m_s2 + force_variation_m_s2) * duration


@pytest.mark.parametrize("duration_s", [0.0, 1 / 64, 0.3])
@pytest.mark.parametrize("anchor_error_m_s2", [Fraction(0), Fraction(1, 8)])
def test_anchored_velocity_attains_constant_acceleration_error(
    duration_s: float, anchor_error_m_s2: Fraction,
) -> None:
    initial = np.asarray([1e12, 0.0, 0.0])
    final = np.asarray([1e12 + 2 * duration_s - 0.5, 0.0, 0.0])
    bound = _anchored_coast_velocity_error_bound_m_s(
        initial, final, np.asarray([2.0, 0.0, 0.0]), duration_s, anchor_error_m_s2, Fraction(0),
    )
    true_final = Fraction(initial[0]) + (2 + anchor_error_m_s2) * Fraction(duration_s)
    assert bound == abs(Fraction(final[0]) - true_final)


@pytest.mark.parametrize("duration_s", [0.25, 0.5])
@pytest.mark.parametrize("jerk_m_s3", [-2, 2])
def test_anchored_velocity_encloses_linear_acceleration(duration_s: float, jerk_m_s3: int) -> None:
    initial = np.asarray([64.0, 0.0, 0.0])
    final = np.asarray([64.0 + 2 * duration_s - math.copysign(0.125, jerk_m_s3), 0.0, 0.0])
    variation = abs(jerk_m_s3) * Fraction(duration_s)
    bound = _anchored_coast_velocity_error_bound_m_s(
        initial, final, np.asarray([2.0, 0.0, 0.0]), duration_s, Fraction(0), variation,
    )
    # Exact integral of a(t)=2+j*t, independent of the bound construction.
    true_final = 64 + 2 * Fraction(duration_s) + jerk_m_s3 * Fraction(duration_s)**2 / 2
    assert Fraction(1, 8) < abs(Fraction(final[0]) - true_final) <= bound


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_anchored_velocity_preserves_vector_residual(axis: int) -> None:
    initial = np.full(3, 1e12)
    acceleration = np.asarray([2.0, -4.0, 8.0])
    final = initial + acceleration / 4
    final[axis] += 0.125
    assert _anchored_coast_velocity_error_bound_m_s(
        initial, final, acceleration, 0.25, Fraction(0), Fraction(0),
    ) == Fraction(1, 8)


def test_anchored_velocity_can_resolve_exact_constant_acceleration() -> None:
    initial, final, acceleration = np.asarray([64.0, 0.0, 0.0]), np.asarray([64.5, 0.0, 0.0]), np.asarray([2.0, 0.0, 0.0])
    assert _anchored_coast_velocity_error_bound_m_s(initial, final, acceleration, 0.25, Fraction(0), Fraction(0)) == 0
    assert _coast_endpoint_velocity_error_bound_m_s(initial, final, 0.25, 2.0) > Fraction("0.000001")


@pytest.mark.parametrize("invalid", ["nan", "infinity", "shape", "dtype", "duration", "boolean-duration",
                                      "negative-error", "inexact-error", "negative-variation"])
def test_anchored_velocity_rejects_invalid_inputs(invalid: str) -> None:
    acceleration = np.zeros(3)
    if invalid in {"nan", "infinity"}:
        acceleration[0] = math.nan if invalid == "nan" else math.inf
    elif invalid == "shape":
        acceleration = np.zeros(2)
    elif invalid == "dtype":
        acceleration = np.zeros(3, dtype=bool)
    with pytest.raises(AssertionError):
        _anchored_coast_velocity_error_bound_m_s(
            np.zeros(3), np.zeros(3), acceleration,
            True if invalid == "boolean-duration" else -1.0 if invalid == "duration" else 0.25,
            0.0 if invalid == "inexact-error" else Fraction(-1 if invalid == "negative-error" else 0),  # type: ignore[arg-type] -- rejection boundary.
            Fraction(-1 if invalid == "negative-variation" else 0),
        )


def _anchored_coast_position_error_bound_m(
    initial_state: np.ndarray, final_position_m: np.ndarray,
    anchor_acceleration_m_s2: np.ndarray, duration_s: float,
    anchor_error_m_s2: Fraction, force_variation_m_s2: Fraction,
) -> Fraction:
    """Bound SI/SSB/J2000 position error given exact initial state and force bounds."""
    assert initial_state.shape == (6,) and initial_state.dtype == np.dtype("float64")
    assert np.all(np.isfinite(initial_state))
    for vector in (final_position_m, anchor_acceleration_m_s2):
        assert vector.shape == (3,) and vector.dtype == np.dtype("float64") and np.all(np.isfinite(vector))
    assert type(duration_s) is float and math.isfinite(duration_s) and duration_s >= 0
    assert all(isinstance(value, Fraction) and value >= 0 for value in (anchor_error_m_s2, force_variation_m_s2))
    duration = Fraction(duration_s)
    residual_m = sum((abs(Fraction(final_position_m[axis]) - Fraction(initial_state[axis])
                         - Fraction(initial_state[axis + 3]) * duration
                         - Fraction(anchor_acceleration_m_s2[axis]) * duration**2 / 2)
                      for axis in range(3)), Fraction(0))
    return residual_m + (anchor_error_m_s2 + force_variation_m_s2) * duration**2 / 2


@pytest.mark.parametrize("duration_s", [0.0, 1 / 64, 0.3])
@pytest.mark.parametrize("anchor_error_m_s2", [Fraction(0), Fraction(1, 8)])
def test_anchored_position_attains_constant_acceleration_error(
    duration_s: float, anchor_error_m_s2: Fraction,
) -> None:
    initial = np.asarray([1e12, 0.0, 0.0, 64.0, 0.0, 0.0])
    final = np.asarray([1e12 + 64 * duration_s + duration_s**2 - 0.5, 0.0, 0.0])
    bound = _anchored_coast_position_error_bound_m(
        initial, final, np.asarray([2.0, 0.0, 0.0]), duration_s, anchor_error_m_s2, Fraction(0),
    )
    true_final = Fraction(initial[0]) + 64 * Fraction(duration_s) + (2 + anchor_error_m_s2) * Fraction(duration_s)**2 / 2
    assert bound == abs(Fraction(final[0]) - true_final)
    assert bound > Fraction("0.001")  # Corrupted endpoint must not pass.


@pytest.mark.parametrize("duration_s", [0.25, 0.5])
@pytest.mark.parametrize("jerk_m_s3", [-2, 2])
def test_anchored_position_encloses_linear_acceleration(duration_s: float, jerk_m_s3: int) -> None:
    initial = np.asarray([128.0, 0.0, 0.0, 64.0, 0.0, 0.0])
    final = np.asarray([128 + 64 * duration_s + duration_s**2 - math.copysign(0.125, jerk_m_s3), 0.0, 0.0])
    bound = _anchored_coast_position_error_bound_m(
        initial, final, np.asarray([2.0, 0.0, 0.0]), duration_s,
        Fraction(0), abs(jerk_m_s3) * Fraction(duration_s),
    )
    # Twice integrate a(t)=2+j*t: x(t)=128+64*t+t^2+j*t^3/6.
    time = Fraction(duration_s)
    true_final = 128 + 64 * time + time**2 + jerk_m_s3 * time**3 / 6
    assert Fraction(1, 8) < abs(Fraction(final[0]) - true_final) <= bound


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_anchored_position_preserves_vector_residual(axis: int) -> None:
    initial = np.asarray([1e12, 1e12, 1e12, 64.0, -32.0, 16.0])
    acceleration = np.asarray([2.0, -4.0, 8.0])
    final = initial[:3] + initial[3:] / 4 + acceleration / 32
    final[axis] += 0.125
    assert _anchored_coast_position_error_bound_m(
        initial, final, acceleration, 0.25, Fraction(0), Fraction(0),
    ) == Fraction(1, 8)


def test_anchored_position_can_resolve_exact_constant_acceleration() -> None:
    initial = np.asarray([128.0, 0.0, 0.0, 64.0, 0.0, 0.0])
    final, acceleration = np.asarray([144.0625, 0.0, 0.0]), np.asarray([2.0, 0.0, 0.0])
    assert _anchored_coast_position_error_bound_m(initial, final, acceleration, 0.25, Fraction(0), Fraction(0)) == 0
    assert _ballistic_endpoint_error_bound_m(initial, final, 0.25, 2.0) > Fraction("0.001")


@pytest.mark.parametrize("invalid", ["nan", "infinity", "shape", "dtype", "duration", "boolean-duration",
                                      "negative-error", "inexact-error", "negative-variation"])
def test_anchored_position_rejects_invalid_inputs(invalid: str) -> None:
    initial = np.zeros(6)
    if invalid in {"nan", "infinity"}:
        initial[0] = math.nan if invalid == "nan" else math.inf
    elif invalid == "shape":
        initial = np.zeros(3)
    elif invalid == "dtype":
        initial = np.zeros(6, dtype=bool)
    with pytest.raises(AssertionError):
        _anchored_coast_position_error_bound_m(
            initial, np.zeros(3), np.zeros(3),
            True if invalid == "boolean-duration" else -1.0 if invalid == "duration" else 0.25,
            0.0 if invalid == "inexact-error" else Fraction(-1 if invalid == "negative-error" else 0),  # type: ignore[arg-type] -- rejection boundary.
            Fraction(-1 if invalid == "negative-variation" else 0),
        )


def _dyadic_sqrt_bounds(value: Fraction) -> tuple[Fraction, Fraction]:
    """Enclose a positive rational root with 100 relative binary guard bits."""
    assert isinstance(value, Fraction) and value > 0
    exponent = (value.numerator.bit_length() - value.denominator.bit_length()) // 2
    step = Fraction(2) ** (exponent - 100)
    scaled = value / step**2
    root = math.isqrt(scaled.numerator // scaled.denominator)
    lower = root * step
    upper = lower if lower**2 == value else (root + 1) * step
    assert 0 < lower and lower**2 <= value <= upper**2
    return lower, upper


def _point_gravity_anchor_error_bound_m_s2(
    gm_m3_s2: float, body_position_m: np.ndarray,
    spacecraft_position_m: np.ndarray, observed_acceleration_m_s2: np.ndarray,
) -> Fraction:
    """Enclose L1 point-force error at exact stored SSB/J2000 inputs, in m/s^2."""
    assert type(gm_m3_s2) is float and math.isfinite(gm_m3_s2) and gm_m3_s2 > 0
    for vector in (body_position_m, spacecraft_position_m, observed_acceleration_m_s2):
        assert vector.shape == (3,) and vector.dtype == np.float64
        assert np.all(np.isfinite(vector))
    relative_m = [Fraction(body) - Fraction(ship) for body, ship in
                  zip(body_position_m, spacecraft_position_m, strict=True)]
    squared_m2 = sum((value**2 for value in relative_m), Fraction(0))
    assert squared_m2 > 0
    lower_m, upper_m = _dyadic_sqrt_bounds(squared_m2)
    error_m_s2 = Fraction(0)
    for relative, observed in zip(relative_m, observed_acceleration_m_s2, strict=True):
        endpoints = [Fraction(gm_m3_s2) * relative / (squared_m2 * radius)
                     for radius in (lower_m, upper_m)]
        error_m_s2 += max(abs(Fraction(observed) - endpoint) for endpoint in endpoints)
    return error_m_s2


@pytest.mark.parametrize("offset_m", [0.0, 1e12])
@pytest.mark.parametrize("error_m_s2", [0.0, 0.125])
def test_point_gravity_anchor_exact_geometry(offset_m: float, error_m_s2: float) -> None:
    ship_m = np.full(3, offset_m)
    bound_m_s2 = _point_gravity_anchor_error_bound_m_s2(
        125.0, ship_m + np.asarray([3.0, 4.0, 0.0]), ship_m,
        np.asarray([3.0 + error_m_s2, 4.0, 0.0]),
    )
    assert bound_m_s2 == Fraction(error_m_s2)  # r=5, GM/r^3=1 exactly.


def test_point_gravity_anchor_irrational_radius() -> None:
    bound_m_s2 = _point_gravity_anchor_error_bound_m_s2(
        2.0, np.asarray([1.0, -1.0, 0.0]), np.zeros(3), np.zeros(3),
    )
    # The exact L1 force is sqrt(2); verify enclosure without a float sqrt.
    assert 2 <= bound_m_s2**2 < 2 + Fraction(2)**-90


@pytest.mark.parametrize("distance_m", [1e-200, 1e100])
def test_point_gravity_anchor_extreme_scale(distance_m: float) -> None:
    exact_m_s2 = Fraction(1e-300) / Fraction(distance_m)**2
    observed_m_s2 = float(exact_m_s2)
    bound_m_s2 = _point_gravity_anchor_error_bound_m_s2(
        1e-300, np.asarray([distance_m, 0.0, 0.0]), np.zeros(3),
        np.asarray([observed_m_s2, 0.0, 0.0]),
    )
    assert bound_m_s2 == abs(Fraction(observed_m_s2) - exact_m_s2) > 0


def test_point_gravity_anchor_rejects_singularity() -> None:
    with pytest.raises(AssertionError):
        _point_gravity_anchor_error_bound_m_s2(1.0, np.zeros(3), np.zeros(3), np.zeros(3))


def _schwarzschild_anchor_error_bound_m_s2(
    gm_m3_s2: float, sun_state: np.ndarray, spacecraft_state: np.ndarray,
    observed_acceleration_m_s2: np.ndarray,
) -> Fraction:
    """Enclose PPN=1 Schwarzschild L1 error at exact stored SI SSB/J2000 states."""
    assert type(gm_m3_s2) is float and math.isfinite(gm_m3_s2) and gm_m3_s2 > 0
    for vector, size in ((sun_state, 6), (spacecraft_state, 6), (observed_acceleration_m_s2, 3)):
        assert vector.shape == (size,) and vector.dtype == np.float64
        assert np.all(np.isfinite(vector))
    relative = [Fraction(ship) - Fraction(sun) for ship, sun in
                zip(spacecraft_state, sun_state, strict=True)]
    position_m, velocity_m_s = relative[:3], relative[3:]
    squared_m2 = sum((value**2 for value in position_m), Fraction(0))
    lower_m, upper_m = _dyadic_sqrt_bounds(squared_m2)
    speed_squared_m2_s2 = sum((value**2 for value in velocity_m_s), Fraction(0))
    radial_m2_s = sum((r * v for r, v in zip(position_m, velocity_m_s, strict=True)), Fraction(0))
    gm = Fraction(gm_m3_s2)
    error_m_s2 = Fraction(0)
    for r, v, observed in zip(position_m, velocity_m_s, observed_acceleration_m_s2, strict=True):
        # Separate the rational potential term; only the velocity term needs sqrt.
        potential_m_s2 = 4 * gm**2 * r / (299792458**2 * squared_m2**2)
        velocity_term = gm * (-speed_squared_m2_s2 * r + 4 * radial_m2_s * v)
        endpoints = [potential_m_s2 + velocity_term / (299792458**2 * squared_m2 * radius)
                     for radius in (lower_m, upper_m)]
        error_m_s2 += max(abs(Fraction(observed) - endpoint) for endpoint in endpoints)
    return error_m_s2


@pytest.mark.parametrize("offset", [0.0, 1e12])
@pytest.mark.parametrize(("velocity", "scaled_force"), [
    ((0.0, 0.0, 0.0), (300, 400, 0)),
    ((3.0, 4.0, 0.0), (525, 700, 0)),
    ((-4.0, 3.0, 0.0), (225, 300, 0)),
    ((1.0, -2.0, 3.0), (238, 384, -60)),
])
def test_schwarzschild_anchor_exact_geometry(
    offset: float, velocity: tuple[float, float, float], scaled_force: tuple[int, int, int],
) -> None:
    # r=(3,4,0), GM=125: potential term*c^2=100*r, velocity factor*c^2=1.
    exact_m_s2 = [Fraction(value, 299792458**2) for value in scaled_force]
    observed_m_s2 = np.asarray([float(value) for value in exact_m_s2])
    observed_m_s2[2] += 0.125  # Deliberately corrupt a component, including negative force.
    sun_state = np.full(6, offset)
    bound_m_s2 = _schwarzschild_anchor_error_bound_m_s2(
        125.0, sun_state, sun_state + np.asarray([3.0, 4.0, 0.0, *velocity]), observed_m_s2,
    )
    assert bound_m_s2 == sum((abs(Fraction(value) - exact) for value, exact in
                             zip(observed_m_s2, exact_m_s2, strict=True)), Fraction(0))


def test_schwarzschild_anchor_irrational_radius() -> None:
    bound_m_s2 = _schwarzschild_anchor_error_bound_m_s2(
        2.0, np.zeros(6), np.asarray([1.0, -1.0, 0.0, 0.0, 0.0, 1.0]), np.zeros(3),
    )
    # Exact L1 force*c^2 = 8-sqrt(2); both signs and cancellation are exercised.
    remainder = 8 - bound_m_s2 * 299792458**2
    assert remainder > 0 and 2 - Fraction(2)**-90 < remainder**2 <= 2


@pytest.mark.parametrize("invalid_state", [(0.0,) * 6, (1.0, 0.0, 0.0, math.nan, 0.0, 0.0)])
def test_schwarzschild_anchor_rejects_invalid_state(invalid_state: tuple[float, ...]) -> None:
    with pytest.raises(AssertionError):
        _schwarzschild_anchor_error_bound_m_s2(1.0, np.zeros(6), np.asarray(invalid_state), np.zeros(3))


def _schwarzschild_state_jacobian_bounds(
    gm_m3_s2: float, distance_floor_m: float, speed_upper_m_s: Fraction,
) -> tuple[Fraction, Fraction]:
    """Bound PPN=1 position/velocity operators in s^-2/s^-1 for r>=d, |v|<=V."""
    assert all(type(value) is float and math.isfinite(value) and value > 0
               for value in (gm_m3_s2, distance_floor_m))
    assert isinstance(speed_upper_m_s, Fraction) and speed_upper_m_s >= 0
    gm, d, v = Fraction(gm_m3_s2), Fraction(distance_floor_m), speed_upper_m_s
    # Position derivative norms: 12*GM^2/r^4 + (2+4+12)*GM*|v|^2/r^3.
    position_jacobian_s_inv2 = (12 * gm**2 / d**4 + 18 * gm * v**2 / d**3) / 299792458**2
    # Velocity derivatives of -|v|^2*r + 4*(r.v)*v contribute 2+4+4.
    velocity_jacobian_s_inv = 10 * gm * v / (299792458**2 * d**2)
    return position_jacobian_s_inv2, velocity_jacobian_s_inv


def _schwarzschild_state_variation_bound_m_s2(
    gm_m3_s2: float, distance_floor_m: float, speed_upper_m_s: Fraction,
    position_error_m: Fraction, velocity_error_m_s: Fraction,
) -> Fraction:
    """Bound PPN=1 source-state effects on a chord with r>=d and |v|<=V."""
    assert all(isinstance(value, Fraction) and value >= 0 for value in (position_error_m, velocity_error_m_s))
    position_jacobian_s_inv2, velocity_jacobian_s_inv = _schwarzschild_state_jacobian_bounds(
        gm_m3_s2, distance_floor_m, speed_upper_m_s,
    )
    return position_jacobian_s_inv2 * position_error_m + velocity_jacobian_s_inv * velocity_error_m_s


@pytest.mark.parametrize("position,radius", [((3, 4, 0), 5), ((0, 0, 2), 2)])
@pytest.mark.parametrize("velocity,speed", [((0, 0, 0), 0), ((2, 0, 0), 2), ((1, -2, 2), 3)])
@pytest.mark.parametrize("kind", ["position", "velocity"])
@pytest.mark.parametrize("direction", [(1, 0, 0), (0, 1, 0), (0, 0, 1), (Fraction(3, 5), Fraction(4, 5), 0)])
def test_schwarzschild_jacobians_enclose_exact_directional_derivatives(
    position: tuple[int, int, int], radius: int, velocity: tuple[int, int, int], speed: int,
    kind: str, direction: tuple[int | Fraction, int | Fraction, int | Fraction],
) -> None:
    r, v, u = tuple(map(Fraction, position)), tuple(map(Fraction, velocity)), tuple(map(Fraction, direction))
    d = Fraction(radius)
    assert sum(value**2 for value in r) == d**2
    assert sum(value**2 for value in v) == speed**2
    assert sum(value**2 for value in u) == 1
    rv, ru, vu = (sum((a * b for a, b in zip(left, right, strict=True)), Fraction(0))
                  for left, right in ((r, v), (r, u), (v, u)))
    # Direct Cartesian differentiation at GM=1, without finite differences.
    # a*c^2 = 4*r/|r|^4 - |v|^2*r/|r|^3 + 4*(r.v)*v/|r|^3.
    if kind == "position":
        derivative = tuple((
            4 * (u[i] / d**4 - 4 * r[i] * ru / d**6)
            - speed**2 * (u[i] / d**3 - 3 * r[i] * ru / d**5)
            + 4 * (vu * v[i] / d**3 - 3 * rv * v[i] * ru / d**5)
        ) / 299792458**2 for i in range(3))
    else:
        derivative = tuple((-2 * vu * r[i] + 4 * ru * v[i] + 4 * rv * u[i])
                           / (299792458**2 * d**3) for i in range(3))
    position_bound, velocity_bound = _schwarzschild_state_jacobian_bounds(1.0, float(radius), Fraction(speed))
    bound = position_bound if kind == "position" else velocity_bound
    assert sum(value**2 for value in derivative) <= bound**2
    assert position_bound > 0 and (velocity_bound == 0) == (speed == 0)


@pytest.mark.parametrize("speed_m_s", [0, 2])
@pytest.mark.parametrize("delta_m", [-0.125, 0.0, 0.125])
def test_schwarzschild_state_variation_radial_position(speed_m_s: int, delta_m: float) -> None:
    bound_m_s2 = _schwarzschild_state_variation_bound_m_s2(
        1.0, 10.0 - abs(delta_m), Fraction(speed_m_s), Fraction(abs(delta_m)), Fraction(0),
    )
    r0, r1 = Fraction(10), 10 + Fraction(delta_m)
    # GM=1, radial fixed velocity: a*c^2=4/r^3+3*v^2/r^2.
    exact_times_c2 = abs(4 / r0**3 + 3 * speed_m_s**2 / r0**2 - 4 / r1**3 - 3 * speed_m_s**2 / r1**2)
    assert exact_times_c2 <= bound_m_s2 * 299792458**2
    assert (bound_m_s2 == 0) == (delta_m == 0)


@pytest.mark.parametrize("radial", [False, True])
@pytest.mark.parametrize("delta_m_s", [-0.125, 0.0, 0.125])
def test_schwarzschild_state_variation_velocity(radial: bool, delta_m_s: float) -> None:
    bound_m_s2 = _schwarzschild_state_variation_bound_m_s2(
        1.0, 10.0, 2 + Fraction(abs(delta_m_s)), Fraction(0), Fraction(abs(delta_m_s)),
    )
    # At r=(10,0,0), changing a purely radial/transverse speed changes only a_x;
    # the velocity coefficient is +3/-1 times v^2/(100*c^2).
    exact_times_c2 = Fraction(3 if radial else 1, 100) * abs((2 + Fraction(delta_m_s))**2 - 4)
    assert exact_times_c2 <= bound_m_s2 * 299792458**2
    assert (bound_m_s2 == 0) == (delta_m_s == 0)


@pytest.mark.parametrize("invalid", ["gm", "floor", "speed", "position", "velocity", "inexact"])
def test_schwarzschild_state_variation_rejects_invalid_domain(invalid: str) -> None:
    with pytest.raises(AssertionError):
        _schwarzschild_state_variation_bound_m_s2(
            math.nan if invalid == "gm" else 1.0, 0.0 if invalid == "floor" else 1.0,
            Fraction(-1 if invalid == "speed" else 1), Fraction(-1 if invalid == "position" else 0),
            0.0 if invalid == "inexact" else Fraction(-1 if invalid == "velocity" else 0),  # type: ignore[arg-type] -- boundary rejection.
        )


def _degree_two_anchor_error_bound_m_s2(
    gm_m3_s2: float, reference_radius_m: float, cosine: float, sine: float, order: int,
    body_position_m: np.ndarray, spacecraft_position_m: np.ndarray,
    inertial_to_fixed: np.ndarray, observed_acceleration_m_s2: np.ndarray,
) -> Fraction:
    """Bound one degree-two order at exact stored SI inputs/matrix, not ideal PCK orientation."""
    assert all(type(value) is float and math.isfinite(value) and value > 0
               for value in (gm_m3_s2, reference_radius_m))
    assert type(order) is int and order in (0, 1, 2)
    assert all(type(value) is float and math.isfinite(value) for value in (cosine, sine))
    assert order != 0 or sine == 0.0
    for array, shape in ((body_position_m, (3,)), (spacecraft_position_m, (3,)),
                         (inertial_to_fixed, (3, 3)), (observed_acceleration_m_s2, (3,))):
        assert array.shape == shape and array.dtype == np.float64 and np.all(np.isfinite(array))
    relative_m = [Fraction(ship) - Fraction(body) for ship, body in
                  zip(spacecraft_position_m, body_position_m, strict=True)]
    matrix = [[Fraction(value) for value in row] for row in inertial_to_fixed]
    fixed_m = [sum((entry * coordinate for entry, coordinate in
                    zip(row, relative_m, strict=True)), Fraction(0)) for row in matrix]
    q_m2 = sum((value**2 for value in fixed_m), Fraction(0))
    root_lower_m, root_upper_m = _dyadic_sqrt_bounds(q_m2)
    normalization_lower, normalization_upper = _dyadic_sqrt_bounds(Fraction(5 if order == 0 else 15))
    x, y, z = fixed_m
    c, s = Fraction(cosine), Fraction(sine)
    if order == 0:
        harmonic = c * (3 * z**2 - q_m2) / 2
        gradient = (-c * x, -c * y, 2 * c * z)
    elif order == 1:
        harmonic = c * x * z + s * y * z
        gradient = (c * z, s * z, c * x + s * y)
    else:
        harmonic = c * (x**2 - y**2) / 2 + s * x * y
        gradient = (c * x + s * y, -c * y + s * x, Fraction(0))
    factor = Fraction(gm_m3_s2) * Fraction(reference_radius_m)**2 / q_m2**3
    # Gradient of GM*R^2*normalization*H(x,y,z)/q^(5/2).
    polynomial = [factor * (q_m2 * derivative - 5 * harmonic * coordinate)
                  for coordinate, derivative in zip(fixed_m, gradient, strict=True)]
    error_m_s2 = Fraction(0)
    for axis, observed in enumerate(observed_acceleration_m_s2):
        projected = sum((matrix[row][axis] * polynomial[row] for row in range(3)), Fraction(0))
        endpoints = (projected * normalization_lower / root_upper_m, projected * normalization_upper / root_lower_m)
        error_m_s2 += max(abs(Fraction(observed) - endpoint) for endpoint in endpoints)
    return error_m_s2


@pytest.mark.parametrize("pole", [False, True])
@pytest.mark.parametrize("rotated", [False, True])
@pytest.mark.parametrize("c20", [-0.125, 0.125])
def test_c20_anchor_exact_axis_oracle(pole: bool, rotated: bool, c20: float) -> None:
    matrix = np.asarray([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]) if rotated else np.eye(3)
    direction = matrix.T @ np.asarray([0.0, 0.0, 1.0] if pole else [1.0, 0.0, 0.0])
    coefficient = Fraction(c20) * (Fraction(-3) if pole else Fraction(3, 2))
    observed = -math.copysign(0.5, coefficient) * direction
    body_m = np.full(3, 1e12)
    bound_m_s2 = _degree_two_anchor_error_bound_m_s2(1.0, 1.0, c20, 0.0, 0, body_m, body_m + direction, matrix, observed)
    # Exact acceleration is coefficient*sqrt(5)*direction; observation points backwards.
    residual = bound_m_s2 - Fraction(1, 2)
    assert residual > 0 and 5 * coefficient**2 <= residual**2 < 5 * coefficient**2 * (1 + Fraction(2)**-90)


def test_c20_anchor_irrational_radius_and_zero_coefficient() -> None:
    c20 = 0.125
    bound_m_s2 = _degree_two_anchor_error_bound_m_s2(1.0, 1.0, c20, 0.0, 0, np.zeros(3), np.ones(3), np.eye(3), np.zeros(3))
    # At (1,1,1), force = C20/9 * sqrt(5/3) * (-1,-1,2).
    exact_squared = Fraction(80, 243) * Fraction(c20)**2
    assert exact_squared <= bound_m_s2**2 < exact_squared * (1 + Fraction(2)**-90)
    assert _degree_two_anchor_error_bound_m_s2(
        1.0, 1.0, 0.0, 0.0, 0, np.zeros(3), np.ones(3), np.eye(3), np.asarray([0.5, 0.0, 0.0]),
    ) == Fraction(1, 2)


@pytest.mark.parametrize("invalid_matrix", [np.zeros((3, 3)), np.full((3, 3), math.nan)])
def test_c20_anchor_rejects_invalid_geometry(invalid_matrix: np.ndarray) -> None:
    with pytest.raises(AssertionError):
        _degree_two_anchor_error_bound_m_s2(1.0, 1.0, 0.125, 0.0, 0, np.zeros(3), np.ones(3), invalid_matrix, np.zeros(3))


@pytest.mark.parametrize("sign", [-1.0, 1.0])
@pytest.mark.parametrize("rotated", [False, True])
@pytest.mark.parametrize(("order", "sine_term", "direction", "coefficient"), [
    (1, False, (0.0, 0.0, 1.0), 1.0),
    (1, True, (0.0, 1.0, 0.0), 1.0),
    (2, False, (-1.0, 0.0, 0.0), 1.5),
    (2, True, (0.0, 1.0, 0.0), 1.0),
])
def test_degree_two_tesseral_axis_oracles(
    sign: float, rotated: bool, order: int, sine_term: bool,
    direction: tuple[float, float, float], coefficient: float,
) -> None:
    matrix = np.asarray([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]) if rotated else np.eye(3)
    # C21 at x=1 accelerates along z; S21 at z=1 along y; C22/S22 use x=1.
    fixed_position = np.asarray([0.0, 0.0, 1.0] if order == 1 and sine_term else [1.0, 0.0, 0.0])
    force_direction = sign * (matrix.T @ np.asarray(direction))
    body_m = np.full(3, 1e12)
    bound_m_s2 = _degree_two_anchor_error_bound_m_s2(
        1.0, 1.0, 0.0 if sine_term else sign, sign if sine_term else 0.0, order,
        body_m, body_m + matrix.T @ fixed_position, matrix, -0.5 * force_direction,
    )
    exact_squared = 15 * Fraction(coefficient)**2
    residual = bound_m_s2 - Fraction(1, 2)
    assert residual > 0 and exact_squared <= residual**2 < exact_squared * (1 + Fraction(2)**-90)


@pytest.mark.parametrize(("order", "scaled_l1"), [(1, Fraction(11, 8)), (2, Fraction(9, 4))])
def test_degree_two_tesseral_mixed_coefficients(order: int, scaled_l1: Fraction) -> None:
    bound_m_s2 = _degree_two_anchor_error_bound_m_s2(
        1.0, 1.0, 0.125, -0.25, order, np.zeros(3), np.ones(3), np.eye(3), np.zeros(3),
    )
    # At (1,1,1), force/sqrt(5) is (1,-1/8,1/4)/27 or (7/8,1/8,5/4)/27.
    exact_squared = 5 * (scaled_l1 / 27)**2
    assert exact_squared <= bound_m_s2**2 < exact_squared * (1 + Fraction(2)**-90)


@pytest.mark.parametrize(("order", "sine"), [(-1, 0.0), (3, 0.0), (True, 0.0), (0, 1.0)])
def test_degree_two_rejects_invalid_order_or_sine(order: int, sine: float) -> None:
    with pytest.raises(AssertionError):
        _degree_two_anchor_error_bound_m_s2(1.0, 1.0, 1.0, sine, order, np.zeros(3), np.ones(3), np.eye(3), np.zeros(3))


def _pi_rational_bounds() -> tuple[Fraction, Fraction]:
    """Enclose pi using Machin's identity and exact alternating-series tails."""
    bounds: list[tuple[Fraction, Fraction]] = []
    for denominator in (5, 239):
        # 24 terms end with a negative term; the next positive term bounds the tail.
        lower = sum((Fraction((-1)**k, (2 * k + 1) * denominator**(2 * k + 1))
                     for k in range(24)), Fraction(0))
        bounds.append((lower, lower + Fraction(1, 49 * denominator**49)))
    return 16 * bounds[0][0] - 4 * bounds[1][1], 16 * bounds[0][1] - 4 * bounds[1][0]


def test_pi_enclosure_machin_identity_and_width() -> None:
    tangent = Fraction(1, 5)
    for _ in range(2):
        tangent = 2 * tangent / (1 - tangent**2)
    assert (tangent - Fraction(1, 239)) / (1 + tangent / 239) == 1
    # 0 < 4*atan(1/5)-atan(1/239) < 4/5 < pi/2 fixes the tangent branch.
    lower, upper = _pi_rational_bounds()
    assert Fraction(333, 106) < lower < upper < Fraction(355, 113)
    assert upper - lower < Fraction(2)**-100
    assert float(lower) == float(upper) == math.pi  # Binary64 parity, not the proof.


def _sin_cos_degrees_bounds(angle_deg: Fraction) -> tuple[tuple[Fraction, Fraction], ...]:
    """Enclose sine/cosine with exact degree reduction and Taylor remainder bounds."""
    assert isinstance(angle_deg, Fraction)
    reduced_deg = (angle_deg + 180) % 360 - 180
    radians = sorted(reduced_deg * pi / 180 for pi in _pi_rational_bounds())
    midpoint = (radians[0] + radians[1]) / 2
    assert abs(midpoint) < 4
    # Degree-47 Taylor polynomials; every 48th derivative has magnitude <=1.
    remainder = abs(midpoint)**48 / math.factorial(48) + (radians[1] - radians[0]) / 2
    results: list[tuple[Fraction, Fraction]] = []
    for parity in (1, 0):
        value = sum((Fraction((-1)**k, math.factorial(2 * k + parity)) * midpoint**(2 * k + parity)
                     for k in range(24)), Fraction(0))
        results.append((value - remainder, value + remainder))
    return tuple(results)


@pytest.mark.parametrize(("angle_deg", "sine", "cosine"), [
    (0, 0, 1), (90, 1, 0), (180, 0, -1), (270, -1, 0), (-90, -1, 0), (360, 0, 1),
])
def test_trig_enclosure_exact_quadrants(angle_deg: int, sine: int, cosine: int) -> None:
    bounds = _sin_cos_degrees_bounds(Fraction(angle_deg))
    for (lower, upper), exact in zip(bounds, (sine, cosine), strict=True):
        assert lower <= exact <= upper and upper - lower < Fraction(2)**-100


def test_trig_enclosure_diagonal_and_large_exact_turns() -> None:
    for lower, upper in _sin_cos_degrees_bounds(Fraction(45)):
        assert 0 < lower and lower**2 <= Fraction(1, 2) <= upper**2
        assert upper - lower < Fraction(2)**-100
    for angle_deg in (Fraction(1, 3), Fraction(-45)):
        assert _sin_cos_degrees_bounds(angle_deg + 360 * 10**18) == _sin_cos_degrees_bounds(angle_deg)


def test_trig_enclosure_rejects_inexact_input() -> None:
    with pytest.raises(AssertionError):
        _sin_cos_degrees_bounds(0.5)  # type: ignore[arg-type] -- explicit boundary rejection.


def _pck_matrix_error_bound(
    angles_deg: tuple[tuple[Fraction, Fraction], ...], observed: np.ndarray,
) -> Fraction:
    """Bound matrix-entry L1 (hence operator) error against ideal RA/DEC/PM intervals."""
    assert len(angles_deg) == 3
    assert all(len(pair) == 2 and all(isinstance(value, Fraction) for value in pair)
               and pair[0] <= pair[1] for pair in angles_deg)
    assert observed.shape == (3, 3) and observed.dtype == np.float64 and np.all(np.isfinite(observed))
    ra, dec, pm = angles_deg
    euler_deg = (pm, (90 - dec[1], 90 - dec[0]), (90 + ra[0], 90 + ra[1]))
    trig: list[tuple[Fraction, Fraction]] = []
    for lower, upper in euler_deg:
        turns = ((lower + upper) / 2 + 180) // 360
        lower, upper = lower - 360 * turns, upper - 360 * turns
        # Use a small binary64 midpoint to avoid huge nested rational denominators;
        # its complete rounding error is retained in the Lipschitz expansion.
        midpoint = Fraction(float((lower + upper) / 2))
        error_rad = max(abs(midpoint - lower), abs(midpoint - upper)) * _pi_rational_bounds()[1] / 180
        # Outward dyadic rounding keeps the corner products cheap; 120 bits is
        # computational precision, not a new physical tolerance.
        step = Fraction(2)**-120
        for lo, hi in _sin_cos_degrees_bounds(midpoint):
            lower_trig, upper_trig = lo - error_rad, hi + error_rad
            enclosed = ((lower_trig // step) * step, -((-upper_trig) // step) * step)
            assert enclosed[0] <= lower_trig <= upper_trig <= enclosed[1]
            trig.append(enclosed)
    errors = [Fraction(0)] * 9
    # Each matrix entry is multi-affine in the six enclosed trig values, so
    # its extrema over this box occur at the 64 corners. Correlation is not assumed.
    for sw, cw, sb, cb, sa, ca in product(*trig):
        matrix = (cw * ca - sw * cb * sa, cw * sa + sw * cb * ca, sw * sb,
                  -sw * ca - cw * cb * sa, -sw * sa + cw * cb * ca, cw * sb,
                  sb * sa, -sb * ca, cb)
        for index, (value, native) in enumerate(zip(matrix, observed.flat, strict=True)):
            errors[index] = max(errors[index], abs(value - Fraction(native)))
    return sum(errors, Fraction(0))


@pytest.mark.parametrize("error", [0.0, 0.125])
@pytest.mark.parametrize(("angles", "expected"), [
    ((-90, 90, 0), ((1, 0, 0), (0, 1, 0), (0, 0, 1))),
    ((-90, 90, 90), ((0, 1, 0), (-1, 0, 0), (0, 0, 1))),
    ((-90, 0, 0), ((1, 0, 0), (0, 0, 1), (0, -1, 0))),
    ((0, 0, 90), ((0, 0, 1), (0, -1, 0), (1, 0, 0))),
])
def test_pck_matrix_exact_axis_rotations(
    error: float, angles: tuple[int, int, int], expected: tuple[tuple[int, ...], ...],
) -> None:
    observed = np.asarray(expected, dtype=float)
    observed[0, 0] += error
    bound = _pck_matrix_error_bound(tuple((Fraction(a), Fraction(a)) for a in angles), observed)
    assert Fraction(error) <= bound < Fraction(error) + Fraction(2)**-90


def test_pck_matrix_diagonal_and_nonzero_angle_width() -> None:
    diagonal = _pck_matrix_error_bound(
        ((Fraction(-45), Fraction(-45)), (Fraction(90), Fraction(90)), (Fraction(0), Fraction(0))), np.zeros((3, 3)),
    )
    # Entry L1 norm of R3(45 degrees) is 1+2*sqrt(2).
    assert diagonal > 1 and 8 <= (diagonal - 1)**2 < 8 + Fraction(2)**-80
    uncertain = _pck_matrix_error_bound(
        ((Fraction(-90), Fraction(-90)), (Fraction(90), Fraction(90)), (Fraction(-45), Fraction(45))), np.eye(3),
    )
    assert uncertain >= 2  # Exact entry-L1 error at either 45-degree endpoint.


def test_pck_matrix_rejects_reversed_interval() -> None:
    with pytest.raises(AssertionError):
        _pck_matrix_error_bound(((Fraction(1), Fraction(0)),) * 3, np.eye(3))


def _fully_lit_srp_anchor_error_bound_m_s2(
    sun_position_m: np.ndarray, spacecraft_position_m: np.ndarray,
    luminosity_w: float, area_m2: float, cr: float, mass_kg: float,
    observed_acceleration_m_s2: np.ndarray,
) -> Fraction:
    """Enclose cannonball SRP L1 error at exact SI inputs; requires proven full light."""
    assert all(type(value) is float and math.isfinite(value) and value > 0
               for value in (luminosity_w, area_m2, cr, mass_kg))
    for vector in (sun_position_m, spacecraft_position_m, observed_acceleration_m_s2):
        assert vector.shape == (3,) and vector.dtype == np.float64
        assert np.all(np.isfinite(vector))
    relative_m = [Fraction(ship) - Fraction(sun) for ship, sun in
                  zip(spacecraft_position_m, sun_position_m, strict=True)]
    squared_m2 = sum((value**2 for value in relative_m), Fraction(0))
    lower_m, upper_m = _dyadic_sqrt_bounds(squared_m2)
    pi_lower, pi_upper = _pi_rational_bounds()
    coefficient = (Fraction(luminosity_w) * Fraction(area_m2) * Fraction(cr)
                   / (4 * 299792458 * Fraction(mass_kg) * squared_m2))
    error_m_s2 = Fraction(0)
    for relative, observed in zip(relative_m, observed_acceleration_m_s2, strict=True):
        endpoints = [coefficient * relative / (pi * radius) for pi, radius in
                     ((pi_lower, lower_m), (pi_upper, upper_m))]
        error_m_s2 += max(abs(Fraction(observed) - endpoint) for endpoint in endpoints)
    return error_m_s2


@pytest.mark.parametrize("offset_m", [0.0, 1e12])
def test_fully_lit_srp_anchor_signed_geometry(offset_m: float) -> None:
    sun_m = np.full(3, offset_m)
    ship_m = sun_m + np.asarray([3.0, -4.0, 0.0])
    # L=4*c*125, A=Cr=m=1 gives exact acceleration (3,-4,0)/pi m/s^2.
    zero_bound = _fully_lit_srp_anchor_error_bound_m_s2(
        sun_m, ship_m, float(4 * 299792458 * 125), 1.0, 1.0, 1.0, np.zeros(3),
    )
    assert Fraction(7 * 113, 355) < zero_bound < Fraction(7 * 106, 333)
    observed = np.asarray([0.9, -1.2, 0.0])
    directed_bound = _fully_lit_srp_anchor_error_bound_m_s2(
        sun_m, ship_m, float(4 * 299792458 * 125), 1.0, 1.0, 1.0, observed,
    )
    assert directed_bound == zero_bound - Fraction(0.9) - Fraction(1.2)
    assert Fraction("0.12") < directed_bound < Fraction("0.14")


@pytest.mark.parametrize(("area_m2", "cr", "mass_kg"), [(2.0, 1.0, 1.0), (1.0, 2.0, 1.0), (1.0, 1.0, 0.5)])
def test_fully_lit_srp_anchor_exact_scaling(area_m2: float, cr: float, mass_kg: float) -> None:
    # Irrational radius exercises the second enclosure; zero observation makes scaling exact.
    source_m, ship_m = np.zeros(3), np.asarray([1.0, -1.0, 0.0])
    baseline = _fully_lit_srp_anchor_error_bound_m_s2(source_m, ship_m, 1.0, 1.0, 1.0, 1.0, np.zeros(3))
    scaled = _fully_lit_srp_anchor_error_bound_m_s2(source_m, ship_m, 1.0, area_m2, cr, mass_kg, np.zeros(3))
    assert scaled == 2 * baseline > 0


@pytest.mark.parametrize("mass_kg", [0.0, -1.0, math.nan])
def test_fully_lit_srp_anchor_rejects_invalid_mass(mass_kg: float) -> None:
    with pytest.raises(AssertionError):
        _fully_lit_srp_anchor_error_bound_m_s2(
            np.zeros(3), np.ones(3), 1.0, 1.0, 1.0, mass_kg, np.zeros(3),
        )


def _fully_lit_srp_position_jacobian_bound_s_inv2(
    luminosity_w: float, area_m2: float, cr: float, mass_kg: float,
    distance_floor_m: float,
) -> Fraction:
    """Bound the fully lit, fixed-mass SRP position operator in s^-2."""
    assert all(type(value) is float and math.isfinite(value) and value > 0
               for value in (luminosity_w, area_m2, cr, mass_kg))
    coefficient_upper_m3_s2 = (Fraction(luminosity_w) * Fraction(area_m2) * Fraction(cr)
                              / (4 * 299792458 * Fraction(mass_kg) * _pi_rational_bounds()[0]))
    # Fully lit SRP has the same inverse-square Jacobian norm as point gravity.
    return coefficient_upper_m3_s2 * _point_mass_variation_bound_m_s2(1.0, distance_floor_m, Fraction(1))


def _fully_lit_srp_position_variation_bound_m_s2(
    luminosity_w: float, area_m2: float, cr: float, mass_kg: float,
    distance_floor_m: float, displacement_m: Fraction,
) -> Fraction:
    """Bound SRP source-position effect; caller proves full light and chord floor."""
    assert isinstance(displacement_m, Fraction) and displacement_m >= 0
    return _fully_lit_srp_position_jacobian_bound_s_inv2(
        luminosity_w, area_m2, cr, mass_kg, distance_floor_m,
    ) * displacement_m


@pytest.mark.parametrize("position,radius", [((3, 4, 0), 5), ((0, 0, 2), 2)])
@pytest.mark.parametrize("area_m2,cr,mass_kg", [(1.0, 1.0, 1.0), (2.0, 1.0, 1.0), (1.0, 2.0, 0.5)])
@pytest.mark.parametrize("direction", [(1, 0, 0), (0, 1, 0), (0, 0, 1), (Fraction(3, 5), Fraction(4, 5), 0)])
def test_fully_lit_srp_jacobian_encloses_exact_directional_derivative(
    position: tuple[int, int, int], radius: int, area_m2: float, cr: float, mass_kg: float,
    direction: tuple[int | Fraction, int | Fraction, int | Fraction],
) -> None:
    r, u, d = tuple(map(Fraction, position)), tuple(map(Fraction, direction)), Fraction(radius)
    assert sum(value**2 for value in r) == d**2 and sum(value**2 for value in u) == 1
    dot = sum((a * b for a, b in zip(r, u, strict=True)), Fraction(0))
    scale = Fraction(area_m2) * Fraction(cr) / Fraction(mass_kg)
    # L=4*c gives a*pi=(A*Cr/m)*r/|r|^3; differentiate exactly.
    derivative_times_pi = tuple(scale * (u[i] / d**3 - 3 * r[i] * dot / d**5) for i in range(3))
    bound = _fully_lit_srp_position_jacobian_bound_s_inv2(
        float(4 * 299792458), area_m2, cr, mass_kg, float(radius),
    )
    assert sum(value**2 for value in derivative_times_pi) <= (bound * _pi_rational_bounds()[0])**2


@pytest.mark.parametrize("area_m2", [1.0, 2.0])
@pytest.mark.parametrize("delta_m", [-0.125, 0.0, 0.125])
def test_fully_lit_srp_position_variation_radial_oracle(area_m2: float, delta_m: float) -> None:
    bound_m_s2 = _fully_lit_srp_position_variation_bound_m_s2(
        float(4 * 299792458 * 125), area_m2, 1.0, 1.0,
        5.0 - abs(delta_m), Fraction(abs(delta_m)),
    )
    # Exact radial acceleration is 125*A/(pi*r^2); only the source moves.
    exact_times_pi_m_s2 = 125 * Fraction(area_m2) * abs(Fraction(1, 25) - (5 + Fraction(delta_m))**-2)
    pi_lower, pi_upper = _pi_rational_bounds()
    assert bound_m_s2 * pi_lower >= exact_times_pi_m_s2
    if delta_m:
        assert bound_m_s2 * pi_upper < 2 * exact_times_pi_m_s2
    else:
        assert bound_m_s2 == 0


@pytest.mark.parametrize(("mass_kg", "error_m"), [
    (0.0, Fraction(0)), (math.nan, Fraction(0)), (1.0, Fraction(-1)),
])
def test_fully_lit_srp_position_variation_rejects_invalid_input(mass_kg: float, error_m: Fraction) -> None:
    with pytest.raises(AssertionError):
        _fully_lit_srp_position_variation_bound_m_s2(1.0, 1.0, 1.0, mass_kg, 1.0, error_m)


def _apparent_spheres_strictly_disjoint(
    source_position_m: np.ndarray, source_radius_m: float,
    occultor_position_m: np.ndarray, occultor_radius_m: float,
    observer_position_m: np.ndarray,
    *, source_position_error_m: float = 0.0, occultor_position_error_m: float = 0.0,
    observer_position_error_m: float = 0.0,
) -> bool:
    """Prove clear discs for SI/J2000 position balls; false means unresolved."""
    assert all(type(radius) is float and math.isfinite(radius) and radius > 0
               for radius in (source_radius_m, occultor_radius_m))
    assert all(type(error) is float and math.isfinite(error) and error >= 0
               for error in (source_position_error_m, occultor_position_error_m, observer_position_error_m))
    for vector in (source_position_m, occultor_position_m, observer_position_m):
        assert vector.shape == (3,) and vector.dtype == np.float64
        assert np.all(np.isfinite(vector))
    source, occultor = ([Fraction(body) - Fraction(observer) for body, observer in
                        zip(position, observer_position_m, strict=True)]
                       for position in (source_position_m, occultor_position_m))
    source_squared_m2 = sum((value**2 for value in source), Fraction(0))
    occultor_squared_m2 = sum((value**2 for value in occultor), Fraction(0))
    source_radius, occultor_radius = Fraction(source_radius_m), Fraction(occultor_radius_m)
    assert source_squared_m2 > source_radius**2 and occultor_squared_m2 > occultor_radius**2
    # Every uncertain physical sphere is contained in the concentric sphere
    # enlarged by its centre-error radius (triangle inequality). Sum exactly.
    # Relative centre uncertainty includes observer motion. Enclose both cones
    # separately; ignoring their shared observer correlation is conservative.
    source_radius += Fraction(source_position_error_m) + Fraction(observer_position_error_m)
    occultor_radius += Fraction(occultor_position_error_m) + Fraction(observer_position_error_m)
    if source_squared_m2 <= source_radius**2 or occultor_squared_m2 <= occultor_radius**2:
        return False  # Cannot prove an external viewpoint for the enlarged sphere.
    dot_m2 = sum((s * o for s, o in zip(source, occultor, strict=True)), Fraction(0))
    left_m2 = dot_m2 + source_radius * occultor_radius
    right_squared_m4 = ((source_squared_m2 - source_radius**2)
                        * (occultor_squared_m2 - occultor_radius**2))
    # cos(separation) < cos(source angular radius + occultor angular radius).
    # Avoid squaring a negative left side: it already lies below the positive root.
    return left_m2 < 0 or left_m2**2 < right_squared_m4


@pytest.mark.parametrize("offset_m", [0.0, 1e12])
@pytest.mark.parametrize(("occultor", "radius_m", "clear"), [
    ((15.0, 20.0, 0.0), 6.0, True),
    ((15.0, 20.0, 0.0), 7.0, False),  # Exact apparent tangency: 480^2=400*576.
    ((15.0, 20.0, 0.0), 8.0, False),
    ((-25.0, 0.0, 0.0), 15.0, True),  # Opposite hemispheres; left side is negative.
    ((25.0, 0.0, 0.0), 15.0, False),
])
def test_apparent_spheres_exact_geometry(
    offset_m: float, occultor: tuple[float, float, float], radius_m: float, clear: bool,
) -> None:
    observer_m = np.full(3, offset_m)
    assert _apparent_spheres_strictly_disjoint(
        observer_m + np.asarray([25.0, 0.0, 0.0]), 15.0,
        observer_m + np.asarray(occultor), radius_m, observer_m,
    ) is clear


@pytest.mark.parametrize("source_radius_m", [25.0, 26.0, math.nan, -1.0])
def test_apparent_spheres_rejects_invalid_geometry(source_radius_m: float) -> None:
    with pytest.raises(AssertionError):
        _apparent_spheres_strictly_disjoint(
            np.asarray([25.0, 0.0, 0.0]), source_radius_m,
            np.asarray([0.0, 25.0, 0.0]), 1.0, np.zeros(3),
        )


@pytest.mark.parametrize("offset_m", [0.0, 1e12])
@pytest.mark.parametrize(("source_error_m", "occultor_error_m", "clear"), [
    (0.0, 0.0, True), (0.25, 0.25, True), (0.0, 1.0, False),
    (10.0, 0.0, False),  # Enlarged source reaches observer: unresolved, not an impact.
])
def test_apparent_spheres_position_balls(
    offset_m: float, source_error_m: float, occultor_error_m: float, clear: bool,
) -> None:
    observer_m = np.full(3, offset_m)
    assert _apparent_spheres_strictly_disjoint(
        observer_m + np.asarray([25.0, 0.0, 0.0]), 15.0,
        observer_m + np.asarray([15.0, 20.0, 0.0]), 6.0, observer_m,
        source_position_error_m=source_error_m, occultor_position_error_m=occultor_error_m,
    ) is clear
    # With zero source error and occultor error 1, enlarged apparent discs
    # are exactly tangent (480^2=400*576); no small-epsilon "clear" is allowed.


@pytest.mark.parametrize("error_m", [-1.0, math.nan, True])
def test_apparent_spheres_rejects_invalid_position_error(error_m: float) -> None:
    with pytest.raises(AssertionError):
        _apparent_spheres_strictly_disjoint(
            np.asarray([25.0, 0.0, 0.0]), 15.0, np.asarray([0.0, 25.0, 0.0]),
            6.0, np.zeros(3), source_position_error_m=error_m,
        )


@pytest.mark.parametrize("offset_m", [0.0, 1e12])
@pytest.mark.parametrize("observer_error_m,clear", [(0.0, True), (0.5, True), (1.0, False), (2.0, False), (11.0, False)])
def test_apparent_spheres_shared_observer_ball(offset_m: float, observer_error_m: float, clear: bool) -> None:
    observer = np.full(3, offset_m)
    assert _apparent_spheres_strictly_disjoint(
        observer + np.asarray([25.0, 0.0, 0.0]), 14.0,
        observer + np.asarray([15.0, 20.0, 0.0]), 6.0, observer,
        observer_position_error_m=observer_error_m,
    ) is clear
    # At observer error 1 m, enlarged radii are exactly 15 and 7 m:
    # dot+R1*R2=375+105=480 and (625-225)*(625-49)=480^2.
    # Tangency is unresolved; 11 m also loses the external-viewpoint proof.


@pytest.mark.parametrize("observer_error_m", [-1.0, math.nan, math.inf, True])
def test_apparent_spheres_rejects_invalid_observer_ball(observer_error_m: float) -> None:
    with pytest.raises(AssertionError):
        _apparent_spheres_strictly_disjoint(
            np.asarray([25.0, 0.0, 0.0]), 14.0,
            np.asarray([15.0, 20.0, 0.0]), 6.0, np.zeros(3),
            observer_position_error_m=observer_error_m,
        )


def _point_mass_jerk_interval_m_s3(
    gm_m3_s2: float, relative_position_m: tuple[Fraction, ...], relative_velocity_m_s: tuple[Fraction, ...],
) -> tuple[tuple[Fraction, Fraction], ...]:
    """Enclose ideal point-mass acceleration's first time derivative in SI/J2000."""
    assert type(gm_m3_s2) is float and math.isfinite(gm_m3_s2) and gm_m3_s2 > 0
    assert all(len(vector) == 3 and all(isinstance(value, Fraction) for value in vector)
               for vector in (relative_position_m, relative_velocity_m_s))
    squared_m2 = sum((value**2 for value in relative_position_m), Fraction(0))
    assert squared_m2 > 0, "singular point-mass jerk position"
    radius_lower_m, radius_upper_m = _dyadic_sqrt_bounds(squared_m2)
    dot_m2_s = sum((r*v for r, v in zip(relative_position_m, relative_velocity_m_s, strict=True)), Fraction(0))
    intervals: list[tuple[Fraction, Fraction]] = []
    for r, v in zip(relative_position_m, relative_velocity_m_s, strict=True):
        numerator = Fraction(gm_m3_s2) * (3*r*dot_m2_s - squared_m2*v)
        endpoints = (numerator / (squared_m2**2 * radius_lower_m), numerator / (squared_m2**2 * radius_upper_m))
        intervals.append((min(endpoints), max(endpoints)))
    return tuple(intervals)


@pytest.mark.parametrize("gm_m3_s2", [1.0, 7.0])
@pytest.mark.parametrize("position,radius", [((3, 4, 0), 5), ((0, 0, 5), 5), ((0, 0, 10), 10)])
@pytest.mark.parametrize("velocity", [(0, 0, 0), (1, 0, 0), (0, 0, 2), (-1, 2, -2)])
def test_point_mass_jerk_exact_rational_radius(
    gm_m3_s2: float, position: tuple[int, ...], radius: int, velocity: tuple[int, ...],
) -> None:
    intervals = _point_mass_jerk_interval_m_s3(gm_m3_s2, tuple(map(Fraction, position)), tuple(map(Fraction, velocity)))
    dot = sum(r*v for r, v in zip(position, velocity, strict=True))
    # Differentiate -mu*r(t)/R(t)^3 by the scalar product rule at t=0.
    for r, v, (lower, upper) in zip(position, velocity, intervals, strict=True):
        exact = -Fraction(gm_m3_s2)*v / radius**3 + 3*Fraction(gm_m3_s2)*r*dot / radius**5
        assert lower == exact == upper  # m/s³, exactly representable rational root.


@pytest.mark.parametrize("direction", [-1, 1])
def test_point_mass_jerk_encloses_irrational_radius(direction: int) -> None:
    intervals = _point_mass_jerk_interval_m_s3(
        1.0, (Fraction(1), Fraction(1), Fraction(0)), (Fraction(direction), Fraction(0), Fraction(0)),
    )
    # Exact components are sign*(1,3,0)/(4*sqrt(2)). Compare squares,
    # independently of the dyadic-root implementation, including both signs.
    for numerator, (lower, upper) in zip((1, 3), intervals[:2], strict=True):
        abs_lower, abs_upper = (lower, upper) if direction > 0 else (-upper, -lower)
        assert 0 < abs_lower < abs_upper
        assert abs_lower**2 <= Fraction(numerator**2, 32) <= abs_upper**2
    assert intervals[2] == (Fraction(0), Fraction(0))


@pytest.mark.parametrize("case", ["zero", "gm-zero", "gm-negative", "gm-boolean", "gm-nan", "gm-inf",
                                  "position-length", "velocity-length", "position-float", "velocity-boolean"])
def test_point_mass_jerk_rejects_invalid_inputs(case: str) -> None:
    gm = {"gm-zero": 0.0, "gm-negative": -1.0, "gm-boolean": True, "gm-nan": math.nan, "gm-inf": math.inf}.get(case, 1.0)
    position = (Fraction(0 if case == "zero" else 1), Fraction(0), Fraction(0))
    velocity = (Fraction(1), Fraction(0), Fraction(0))
    if case == "position-length":
        position = position[:2]
    elif case == "velocity-length":
        velocity = velocity[:2]
    elif case == "position-float":
        position = (1.0, 0.0, 0.0)  # type: ignore[assignment] -- boundary rejection.
    elif case == "velocity-boolean":
        velocity = (True, Fraction(0), Fraction(0))  # type: ignore[assignment] -- boundary rejection.
    with pytest.raises(AssertionError):
        _point_mass_jerk_interval_m_s3(gm, position, velocity)


def _point_mass_variation_bound_m_s2(
    gm_m3_s2: float, distance_floor_m: float, displacement_m: Fraction,
) -> Fraction:
    """Bound ideal force change when the entire comparison chord stays above d."""
    assert all(type(value) is float and math.isfinite(value) and value > 0
               for value in (gm_m3_s2, distance_floor_m))
    assert isinstance(displacement_m, Fraction) and displacement_m >= 0
    return 2 * Fraction(gm_m3_s2) * displacement_m / Fraction(distance_floor_m)**3


@pytest.mark.parametrize("gm_m3_s2", [1.0, 1000.0])
@pytest.mark.parametrize("delta_m", [-0.125, 0.0, 0.125])
def test_point_mass_variation_encloses_exact_radial_force(
    gm_m3_s2: float, delta_m: float,
) -> None:
    initial_m, final_m = Fraction(10), Fraction(10) + Fraction(delta_m)
    # The complete symmetric displacement ball has this exact distance floor.
    floor_m = float(initial_m - abs(Fraction(delta_m)))
    bound_m_s2 = _point_mass_variation_bound_m_s2(
        gm_m3_s2, floor_m, abs(Fraction(delta_m)),
    )
    exact_change_m_s2 = abs(Fraction(gm_m3_s2) / initial_m**2
                            - Fraction(gm_m3_s2) / final_m**2)
    assert exact_change_m_s2 <= bound_m_s2
    if delta_m:
        assert exact_change_m_s2 > bound_m_s2 / 2  # A missing factor 2 fails.
    else:
        assert exact_change_m_s2 == bound_m_s2 == 0


def test_point_mass_variation_encloses_exact_transverse_force() -> None:
    # A rational rotation preserves radius exactly and changes force direction.
    initial_m = (Fraction(10), Fraction(0), Fraction(0))
    final_m = (Fraction(99990, 10001), Fraction(2000, 10001), Fraction(0))
    assert sum(value**2 for value in final_m) == 100
    displacement_m = sum(map(abs, (b - a for a, b in zip(initial_m, final_m, strict=True))))
    assert displacement_m < Fraction("0.5")  # Whole chord is outside 9.5 m.
    bound_m_s2 = _point_mass_variation_bound_m_s2(1000.0, 9.5, displacement_m)
    # With GM=1000 and r=10, a=-r exactly, so no numerical force oracle is used.
    exact_change_squared = sum((b - a)**2 for a, b in zip(initial_m, final_m, strict=True))
    assert 0 < exact_change_squared <= bound_m_s2**2


def test_point_mass_variation_rejects_singular_chord_floor() -> None:
    with pytest.raises(AssertionError):
        _point_mass_variation_bound_m_s2(1.0, 0.0, Fraction(2))


def _harmonic_spatial_jacobian_bound_s_inv2(
    budget: trajectory._RefinementBudget, gm_m3_s2: float,
    radius_m: float, distance_m: float, cosine: np.ndarray, sine: np.ndarray,
) -> Fraction:
    """Bound the ideal spatial Jacobian in s^-2, at a fixed field orientation."""
    scaled: list[list[list[float]]] = []
    for matrix in (cosine, sine):
        assert matrix.ndim == 2 and matrix.dtype == np.dtype("float64")
        assert np.all(np.isfinite(matrix))
        rows: list[list[float]] = []
        for degree, row in enumerate(matrix):
            budget.check()
            squared_weight = (degree + 2) * (2 * degree + 3)
            weight = math.isqrt(squared_weight)
            weight += int(weight**2 < squared_weight)
            values: list[float] = []
            for coefficient in row:
                magnitude = abs(float(coefficient))
                value = math.nextafter(magnitude * weight, math.inf) if magnitude else 0.0
                assert math.isfinite(value)
                assert Fraction(value) >= Fraction(magnitude) * weight
                values.append(value)
            rows.append(values)
        scaled.append(rows)
    # Only the norm-bound calculation sees these weights, never native dynamics.
    acceleration_bound = trajectory._harmonic_acceleration_upper_bound(
        budget.candidate_id, gm_m3_s2, radius_m, distance_m, *scaled,
    )
    budget.check()
    return Fraction(acceleration_bound) / Fraction(distance_m)


@pytest.mark.parametrize("degree", [0, 1, 2])
def test_harmonic_hessian_addition_identity_at_north_pole(degree: int) -> None:
    # Independent Cartesian Hessians of the real 4pi solid harmonics at (0,0,1).
    # Each pair is a squared normalization and an unnormalized Hessian's
    # squared Frobenius norm, obtained from 1/r, {x,y,z}/r^3 and quadratics/r^5.
    terms = (
        ((1, 1 + 1 + 4),),
        ((3, 2 * 9), (3, 2 * 9), (3, 9 + 9 + 36)),
        ((5, 36 + 36 + 144), (15, 2 * 16), (15, 2 * 16), (15, 2), (15, 2)),
    )
    exact_squared_norm = sum(normalization * norm for normalization, norm in terms[degree])
    assert exact_squared_norm == (2 * degree + 1)**2 * (degree + 1) * (degree + 2) * (2 * degree + 3)


@pytest.mark.parametrize("degree", [0, 1, 2, 19, 120, 200])
def test_harmonic_spatial_jacobian_encloses_single_degree(degree: int) -> None:
    cosine = np.zeros((degree + 1, degree + 1))
    cosine[degree, 0] = (-1.0)**degree
    bound_s_inv2 = _harmonic_spatial_jacobian_bound_s_inv2(
        trajectory._RefinementBudget("jacobian-bound", 300.0),
        1.0, 1.0, 1.0, cosine, np.zeros_like(cosine),
    )
    # At the north pole, the independent radial second derivative of
    # sqrt(2n+1)*r^(-n-1) has this squared magnitude (GM=R=r=1 SI).
    radial_squared = Fraction((2 * degree + 1) * ((degree + 1) * (degree + 2))**2)
    frobenius_squared = Fraction((2 * degree + 1)**2 * (degree + 1) * (degree + 2) * (2 * degree + 3))
    assert radial_squared <= frobenius_squared <= bound_s_inv2**2
    # Integer ceiling weights cost at most 23% for these degrees, not an
    # unexplained numerical tolerance on the underlying scientific dynamics.
    assert bound_s_inv2**2 < frobenius_squared * Fraction(123, 100)**2


def test_harmonic_spatial_jacobian_zero_and_expired_budget() -> None:
    zeros = np.zeros((1, 1))
    assert _harmonic_spatial_jacobian_bound_s_inv2(
        trajectory._RefinementBudget("zero-jacobian", 300.0), 1.0, 1.0, 1.0, zeros, zeros,
    ) == 0
    clock = iter([0.0, 301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _harmonic_spatial_jacobian_bound_s_inv2(
            trajectory._RefinementBudget("expired-jacobian", 300.0, lambda: next(clock)),
            1.0, 1.0, 1.0, zeros, zeros,
        )


@pytest.mark.parametrize("offset_m", [0.0, 1e12])
@pytest.mark.parametrize("delta_m", [-0.125, 0.0, 0.125])
@pytest.mark.parametrize("coefficient", [-0.125, 0.125])
def test_ephemeris_position_error_encloses_radial_quadrupole(
    offset_m: float, delta_m: float, coefficient: float,
) -> None:
    budget = trajectory._RefinementBudget("source-error-quadrupole", 300.0)
    body = (offset_m, offset_m, offset_m)
    ship = (offset_m, offset_m, offset_m + 2.0)
    floor_m = trajectory._relative_distance_lower_bound(budget, ship, body, 0.0, abs(delta_m))
    assert 0 < Fraction(floor_m) <= 2 - abs(Fraction(delta_m))
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[2, 0] = coefficient
    bound = _harmonic_spatial_jacobian_bound_s_inv2(budget, 1.0, 1.0, floor_m, cosine, sine) * Fraction(abs(delta_m))
    # At the pole, g_z=-3*sqrt(5)*C20/r^4. Move only the source, not the ship.
    exact_squared = 45 * Fraction(coefficient)**2 * (Fraction(2)**-4 - (2 + Fraction(delta_m))**-4)**2
    assert exact_squared <= bound**2
    assert (bound == 0) == (delta_m == 0)


def _monopole_split_jacobian_bound_s_inv2(
    gm_m3_s2: float, distance_floor_m: float, nonmonopole_bound_s_inv2: Fraction,
) -> Fraction:
    """Combine the C00=1 monopole operator norm with a qualified nonmonopole bound."""
    assert all(type(value) is float and math.isfinite(value) and value > 0 for value in (gm_m3_s2, distance_floor_m))
    assert isinstance(nonmonopole_bound_s_inv2, Fraction) and nonmonopole_bound_s_inv2 >= 0
    return 2 * Fraction(gm_m3_s2) / Fraction(distance_floor_m)**3 + nonmonopole_bound_s_inv2


@pytest.mark.parametrize("gm_m3_s2", [1.0, 1000.0])
@pytest.mark.parametrize("radius_m", [1.0, 2.0])
def test_monopole_split_matches_exact_operator_norm(gm_m3_s2: float, radius_m: float) -> None:
    unit = Fraction(gm_m3_s2) / Fraction(radius_m)**3
    # At the pole the Cartesian Jacobian is diag(-unit,-unit,2*unit).
    eigenvalues = (-unit, -unit, 2*unit)
    bound = _monopole_split_jacobian_bound_s_inv2(gm_m3_s2, radius_m, Fraction(0))
    assert bound == max(map(abs, eigenvalues))
    assert bound * Fraction(1, 8) == _point_mass_variation_bound_m_s2(gm_m3_s2, radius_m, Fraction(1, 8))


@pytest.mark.parametrize("degree", [4, 12])
@pytest.mark.parametrize("radius_m", [1.0, 2.0])
@pytest.mark.parametrize("coefficient", [-0.125, 0.125])
def test_monopole_split_encloses_mixed_radial_derivative(degree: int, radius_m: float, coefficient: float) -> None:
    budget = trajectory._RefinementBudget("split-jacobian", 300.0)
    cosine, sine = np.zeros((degree+1, degree+1)), np.zeros((degree+1, degree+1))
    cosine[degree, 0] = coefficient
    tail_bound = _harmonic_spatial_jacobian_bound_s_inv2(budget, 1.0, 1.0, radius_m, cosine, sine)
    bound = _monopole_split_jacobian_bound_s_inv2(1.0, radius_m, tail_bound)
    radius, normalization = Fraction(radius_m), math.isqrt(2*degree+1)
    assert normalization**2 == 2*degree+1
    # Differentiate -1/r^2-(n+1)*sqrt(2n+1)*C/r^(n+2) at the pole.
    radial_derivative = 2/radius**3 + (degree+1)*(degree+2)*normalization*Fraction(coefficient)/radius**(degree+3)
    assert abs(radial_derivative) <= bound
    cosine[0, 0] = 1.0
    assert bound < _harmonic_spatial_jacobian_bound_s_inv2(budget, 1.0, 1.0, radius_m, cosine, sine)


@pytest.mark.parametrize("invalid", ["gm", "radius", "boolean", "negative-tail", "inexact-tail"])
def test_monopole_split_rejects_invalid_domain(invalid: str) -> None:
    with pytest.raises(AssertionError):
        _monopole_split_jacobian_bound_s_inv2(
            True if invalid == "boolean" else 0.0 if invalid == "gm" else 1.0,
            0.0 if invalid == "radius" else 1.0,
            0.0 if invalid == "inexact-tail" else Fraction(-1 if invalid == "negative-tail" else 0),  # type: ignore[arg-type] -- rejection boundary.
        )


def _harmonic_arbitrary_rotation_bound_m_s2(
    budget: trajectory._RefinementBudget, gm_m3_s2: float,
    radius_m: float, distance_m: float, cosine: np.ndarray, sine: np.ndarray,
) -> Fraction:
    """Bound ideal force change at one position under any two field rotations."""
    budget.check()
    assert cosine.ndim == 2 and cosine.size > 0
    assert cosine.dtype == np.dtype("float64") and np.all(np.isfinite(cosine))
    nonmonopole_cosine = cosine.copy()
    nonmonopole_cosine[0, 0] = 0.0  # Degree zero is exactly rotation invariant.
    bound_m_s2 = trajectory._harmonic_acceleration_upper_bound(
        budget.candidate_id, gm_m3_s2, radius_m, distance_m,
        nonmonopole_cosine, sine,
    )
    budget.check()
    return 2 * Fraction(bound_m_s2)


@pytest.mark.parametrize("monopole", [0.0, 1.0, 100.0])
def test_harmonic_arbitrary_rotation_preserves_monopole(monopole: float) -> None:
    cosine, sine = np.asarray([[monopole]]), np.zeros((1, 1))
    assert _harmonic_arbitrary_rotation_bound_m_s2(
        trajectory._RefinementBudget("monopole-rotation", 300.0),
        1.0, 1.0, 1.0, cosine, sine,
    ) == 0
    assert cosine[0, 0] == monopole and sine[0, 0] == 0.0


@pytest.mark.parametrize("coefficient", [-0.125, 0.125])
def test_harmonic_arbitrary_rotation_encloses_quadrupole(coefficient: float) -> None:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[0, 0], cosine[2, 0] = 1.0, coefficient
    original = cosine.copy()
    bound_m_s2 = _harmonic_arbitrary_rotation_bound_m_s2(
        trajectory._RefinementBudget("quadrupole-rotation", 300.0),
        1.0, 1.0, 1.0, cosine, sine,
    )
    assert np.array_equal(cosine, original)
    # At inertial (0,0,1), turn the symmetry axis from z to x. For the
    # potential c*sqrt(5)/2*(3*(n.r)^2-r^2)/r^5, accelerations along z
    # change from -3*c*sqrt(5) to 3*c*sqrt(5)/2 (GM=R=r=1 SI).
    exact_change_squared = 5 * (Fraction(9, 2) * Fraction(coefficient))**2
    assert 0 < exact_change_squared <= bound_m_s2**2
    # Independent degree-2 addition norm: (2*5*sqrt(3)*|c|)^2.
    expected_bound_squared = 300 * Fraction(coefficient)**2
    assert expected_bound_squared <= bound_m_s2**2
    assert math.isclose(float(bound_m_s2), math.sqrt(float(expected_bound_squared)), rel_tol=1e-15)


def test_harmonic_arbitrary_rotation_rejects_expired_budget() -> None:
    clock = iter([0.0, 301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _harmonic_arbitrary_rotation_bound_m_s2(
            trajectory._RefinementBudget("expired-rotation", 300.0, lambda: next(clock)),
            1.0, 1.0, 1.0, np.ones((1, 1)), np.zeros((1, 1)),
        )


def _pck_euler_rate_upper_rad_s(
    polynomial_deg: tuple[float, ...], time_unit_s: int,
    epoch_magnitude_s: Fraction, amplitudes_deg: tuple[float, ...],
    phase_rates_deg_s: tuple[Fraction, ...],
) -> Fraction:
    """Bound an ideal text-PCK Euler-angle derivative over |t| <= epoch_magnitude_s."""
    assert len(polynomial_deg) == 3 and len(amplitudes_deg) == len(phase_rates_deg_s)
    assert all(type(value) is float and math.isfinite(value)
               for value in (*polynomial_deg, *amplitudes_deg))
    assert type(time_unit_s) is int and time_unit_s > 0
    assert isinstance(epoch_magnitude_s, Fraction) and epoch_magnitude_s >= 0
    assert all(isinstance(value, Fraction) for value in phase_rates_deg_s)
    radians_per_degree_upper = Fraction(22, 7 * 180)  # Exact pi < 22/7 enclosure.
    polynomial_rate = (abs(Fraction(polynomial_deg[1])) / time_unit_s
                       + 2 * abs(Fraction(polynomial_deg[2])) * epoch_magnitude_s / time_unit_s**2)
    periodic_rate = sum((abs(Fraction(amplitude) * rate) for amplitude, rate in
                         zip(amplitudes_deg, phase_rates_deg_s, strict=True)), Fraction(0))
    return radians_per_degree_upper * (polynomial_rate + radians_per_degree_upper * periodic_rate)


def test_pck_euler_rate_bounds_signed_quadratic_and_periodic_terms() -> None:
    day_s = 86400
    bound = _pck_euler_rate_upper_rad_s((2.0, 3.0, -0.25), day_s, Fraction(2 * day_s), (), ())
    for epoch_s in (-2 * day_s, 0, 2 * day_s):
        exact_derivative_deg_s = Fraction(3, day_s) - Fraction(epoch_s, 2 * day_s**2)
        assert abs(float(exact_derivative_deg_s)) * math.pi / 180 <= float(bound)
    assert bound == Fraction(4, day_s) * Fraction(22, 1260)
    # One-degree sine oscillation with one revolution/day: derivative at zero
    # is pi^2/(90*day) rad/s. The two degree-to-radian factors are essential.
    periodic = _pck_euler_rate_upper_rad_s(
        (0.0, 0.0, 0.0), day_s, Fraction(0), (-1.0,), (Fraction(360, day_s),),
    )
    analytic_rad_s = math.pi**2 / (90 * day_s)
    assert analytic_rad_s <= float(periodic) < 1.001 * analytic_rad_s
    assert _pck_euler_rate_upper_rad_s((1.0, 0.0, 0.0), day_s, Fraction(0), (), ()) == 0


@pytest.mark.parametrize("time_unit_s", [0, -1, True])
def test_pck_euler_rate_rejects_invalid_time_unit(time_unit_s: int) -> None:
    with pytest.raises(AssertionError):
        _pck_euler_rate_upper_rad_s((0.0, 0.0, 0.0), time_unit_s, Fraction(0), (), ())


def _check_pinned_pck_rotation_rates(
    budget: trajectory._RefinementBudget, start_tdb_s: float, end_tdb_s: float,
) -> tuple[dict[str, Fraction], dict[str, tuple[tuple[Fraction, Fraction], ...]]]:
    """Qualify ideal text-PCK rates; sampled native readbacks are not error bounds."""
    import spiceypy as spice

    budget.check()
    assert spice.ktotal("PCK") == 0  # No binary orientation model may override text.
    keys = [f"BODY{body}_{name}" for body in (301, 499) for name in ("POLE_RA", "POLE_DEC", "PM")]
    keys += [f"BODY301_NUT_PREC_{name}" for name in ("RA", "DEC", "PM")]
    keys += ["BODY3_NUT_PREC_ANGLES"]
    inputs = {key: spice.gdpool(key, 0, 100).tolist() for key in keys}
    assert sha256(json.dumps(inputs, sort_keys=True, allow_nan=False).encode()).hexdigest() == (
        "75435fa077261f1e6392eb362d8f02dde5f621d5dd02fefb99ca773d5966b9a0"
    )
    for body in (3, 4, 301, 499):
        for suffix in ("MAX_PHASE_DEGREE", "CONSTANTS_JED", "CONSTANTS_REF_FRAME"):
            assert not spice.expool(f"BODY{body}_{suffix}")
    for suffix in ("RA", "DEC", "PM"):
        assert not spice.expool(f"BODY499_NUT_PREC_{suffix}")
    century_s = 36525 * 86400
    phases = inputs["BODY3_NUT_PREC_ANGLES"]
    assert len(phases) == 26
    phase_rates = tuple(Fraction(value) / century_s for value in phases[1::2])
    epoch_magnitude_s = max(abs(Fraction(start_tdb_s)), abs(Fraction(end_tdb_s)))
    bounds: dict[str, Fraction] = {}
    angle_error_upper_rad: dict[str, dict[str, float]] = {}
    angle_intervals_deg: dict[str, tuple[tuple[Fraction, Fraction], ...]] = {}
    phase_bounds = [_sin_cos_degrees_bounds(Fraction(offset) + Fraction(rate) * Fraction(start_tdb_s) / century_s)
                    for offset, rate in zip(phases[::2], phases[1::2], strict=True)]
    pi_bounds = _pi_rational_bounds()
    for body, name, frame_id in ((301, "Moon", 10020), (499, "Mars", 10014)):
        budget.check()
        frame = f"IAU_{name.upper()}"
        assert spice.namfrm(frame) == frame_id and spice.frinfo(frame_id) == (body, 2, body)
        components = []
        initial_angles_deg: list[tuple[Fraction, Fraction]] = []
        native_angles = spice.bodeul(body, start_tdb_s)
        assert len(native_angles) == 4 and all(math.isfinite(value) for value in native_angles)
        assert native_angles[3] == 0.0  # No long-axis offset in the pinned model.
        angle_error_upper_rad[name] = {}
        for polynomial, periodic, time_unit_s in (("POLE_RA", "RA", century_s),
                                                 ("POLE_DEC", "DEC", century_s), ("PM", "PM", 86400)):
            amplitudes = tuple(inputs[f"BODY301_NUT_PREC_{periodic}"]) if body == 301 else ()
            assert len(amplitudes) == (13 if body == 301 else 0)
            components.append(_pck_euler_rate_upper_rad_s(
                tuple(inputs[f"BODY{body}_{polynomial}"]), time_unit_s,
                epoch_magnitude_s, amplitudes, phase_rates if body == 301 else (),
            ))
            time = Fraction(start_tdb_s) / time_unit_s
            angle_deg = sum((Fraction(value) * time**power for power, value in
                            enumerate(inputs[f"BODY{body}_{polynomial}"])), Fraction(0))
            lower_deg = upper_deg = angle_deg
            for amplitude, phase in zip(amplitudes, phase_bounds if body == 301 else (), strict=True):
                term = [Fraction(amplitude) * endpoint for endpoint in phase[int(periodic == "DEC")]]
                lower_deg += min(term)
                upper_deg += max(term)
            # BODEUL returns the prime meridian modulo one revolution.
            if periodic == "PM":
                turns = lower_deg // 360
                assert upper_deg // 360 == turns  # Reject a wrap-crossing enclosure.
                lower_deg -= 360 * turns
                upper_deg -= 360 * turns
            initial_angles_deg.append((lower_deg, upper_deg))
            angle_rad = [degree * pi / 180 for degree in (lower_deg, upper_deg) for pi in pi_bounds]
            observed_rad = Fraction(native_angles[len(components) - 1])
            error_rad = max(abs(observed_rad - endpoint) for endpoint in angle_rad)
            reported_error_rad = math.nextafter(float(error_rad), math.inf)
            assert math.isfinite(reported_error_rad) and Fraction(reported_error_rad) >= error_rad
            angle_error_upper_rad[name][periodic] = reported_error_rad
        bounds[name] = sum(components, Fraction(0))
        angle_intervals_deg[name] = tuple(initial_angles_deg)
        # Euler generators have unit operator norm: |omega| <= sum |angle'|.
        for epoch_tdb_s in np.linspace(start_tdb_s, end_tdb_s, 13):
            budget.check()
            rotation, angular_velocity = spice.xf2rav(spice.sxform("J2000", frame, float(epoch_tdb_s)))
            assert np.max(np.abs(rotation @ rotation.T - np.eye(3))) <= 1e-14
            assert float(np.linalg.norm(angular_velocity)) <= float(bounds[name])
    budget.check()
    print(json.dumps({"pck_anchor_epoch_tdb_s": start_tdb_s,
                      "pck_anchor_angle_error_upper_rad": angle_error_upper_rad}, sort_keys=True, allow_nan=False))
    return bounds, angle_intervals_deg


@pytest.mark.parametrize("changed_source", ["binary", "coefficients", "phase", "frame", "mars-periodic"])
def test_pck_rotation_rates_reject_changed_source(
    monkeypatch: pytest.MonkeyPatch, changed_source: str,
) -> None:
    import spiceypy as spice

    ephemeris._ensure_standard_kernels()
    if changed_source == "binary":
        monkeypatch.setattr(spice, "ktotal", lambda kind: 1)
    elif changed_source == "coefficients":
        original_pool = spice.gdpool
        monkeypatch.setattr(spice, "gdpool", lambda key, start, room:
                            np.zeros(3) if key == "BODY301_POLE_RA" else original_pool(key, start, room))
    elif changed_source == "frame":
        monkeypatch.setattr(spice, "frinfo", lambda frame_id: (301, 4, 301))
    else:
        override = "BODY3_MAX_PHASE_DEGREE" if changed_source == "phase" else "BODY499_NUT_PREC_RA"
        original_exists = spice.expool
        monkeypatch.setattr(spice, "expool", lambda key: key == override or original_exists(key))
    budget = trajectory._RefinementBudget("changed-pck", 300.0)
    with pytest.raises(AssertionError):
        _check_pinned_pck_rotation_rates(budget, 100.0, 200.0)
    assert budget.native_arc_propagations == 0


def _regular_solid_harmonic_jets(
    budget: trajectory._RefinementBudget, coordinates: tuple[Fraction, ...], maximum_degree: int,
) -> Iterator[tuple[int, int, tuple[Fraction, ...], tuple[Fraction, ...]]]:
    """Yield unnormalized real/imaginary (value, dx, dy, dz), with no Condon-Shortley phase.

    Coordinates are dimensionless exact rationals; only two preceding degree
    rows are retained. This polynomial kernel does not yet evaluate a force.
    """
    budget.check()
    assert type(maximum_degree) is int and maximum_degree >= 0
    assert len(coordinates) == 3 and all(isinstance(value, Fraction) for value in coordinates)
    x, y, z = coordinates
    q = sum((value**2 for value in coordinates), Fraction(0))
    zero = (Fraction(0),) * 4
    previous: dict[int, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]] = {}
    older: dict[int, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]] = {}
    for degree in range(maximum_degree + 1):
        budget.check()
        current: dict[int, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]] = {}
        for order in range(degree + 1):
            budget.check()
            if degree == 0:
                real, imaginary = (Fraction(1), *zero[1:]), zero
            elif order == degree:
                re, im = previous[order - 1]
                # Q_nn=(2n-1)*(x+i*y)*Q_(n-1,n-1), including product-rule gradients.
                real = tuple((2 * degree - 1) * (x * re[j] - y * im[j]
                             + (re[0] if j == 1 else 0) - (im[0] if j == 2 else 0)) for j in range(4))
                imaginary = tuple((2 * degree - 1) * (x * im[j] + y * re[j]
                                  + (im[0] if j == 1 else 0) + (re[0] if j == 2 else 0)) for j in range(4))
            else:
                parts = []
                for first, second in zip(previous[order], older.get(order, (zero, zero)), strict=True):
                    parts.append(tuple(((2 * degree - 1) * (z * first[j] + (first[0] if j == 3 else 0))
                                        - (degree + order - 1) * (q * second[j]
                                        + (2 * coordinates[j - 1] * second[0] if j else 0))) / (degree - order)
                                       for j in range(4)))
                real, imaginary = parts
            current[order] = (real, imaginary)
            yield degree, order, real, imaginary
        older, previous = previous, current


@pytest.mark.parametrize("coordinates", [
    (Fraction(1, 3), Fraction(-2, 5), Fraction(7, 11)),
    (Fraction(1), Fraction(2), Fraction(-3)), (Fraction(0),) * 3,
])
def test_regular_solid_harmonics_match_expanded_rodrigues(coordinates: tuple[Fraction, ...]) -> None:
    q = sum((value**2 for value in coordinates), Fraction(0))
    count = 0
    for degree, order, real, imaginary in _regular_solid_harmonic_jets(
        trajectory._RefinementBudget("solid-rodrigues", 300.0), coordinates, 8,
    ):
        expected = [[Fraction(0)] * 4 for _ in range(2)]
        # Direct factorial/binomial expansion, independent of the recurrence:
        # Q_nm=(x+i*y)^m * sum_k a_nmk*z^(n-m-2k)*q^k.
        for k in range((degree - order) // 2 + 1):
            for j in range(order + 1):
                coefficient = Fraction((-1)**(k + j // 2) * math.factorial(2 * degree - 2 * k) * math.comb(order, j),
                                       2**degree * math.factorial(k) * math.factorial(degree - k)
                                       * math.factorial(degree - order - 2 * k))
                powers = (order - j, j, degree - order - 2 * k)
                monomial = math.prod((value**power for value, power in zip(coordinates, powers, strict=True)), start=Fraction(1))
                expected[j % 2][0] += coefficient * monomial * q**k
                for axis in range(3):
                    derivative = powers[axis] * math.prod((value**(power - int(index == axis))
                        for index, (value, power) in enumerate(zip(coordinates, powers, strict=True))), start=Fraction(1)) if powers[axis] else Fraction(0)
                    expected[j % 2][axis + 1] += coefficient * (derivative * q**k
                        + (2 * k * coordinates[axis] * monomial * q**(k - 1) if k else 0))
        assert (real, imaginary) == tuple(map(tuple, expected)), (degree, order)
        for jet in (real, imaginary):
            assert sum((u * derivative for u, derivative in zip(coordinates, jet[1:], strict=True)), Fraction(0)) == degree * jet[0]
        count += 1
    assert count == 45


@pytest.mark.parametrize("pole", [Fraction(-1), Fraction(1)])
def test_regular_solid_harmonics_degree_200_poles(pole: Fraction) -> None:
    count = 0
    for degree, order, real, imaginary in _regular_solid_harmonic_jets(
        trajectory._RefinementBudget("solid-pole-200", 300.0), (Fraction(0), Fraction(0), pole), 200,
    ):
        zero = (Fraction(0),) * 4
        if order == 0:
            assert real == (pole**degree, 0, 0, degree * pole**(degree - 1)) and imaginary == zero
        elif order == 1:
            slope = Fraction(degree * (degree + 1), 2) * pole**(degree - 1)
            assert real == (0, slope, 0, 0) and imaginary == (0, 0, slope, 0)
        else:
            assert real == imaginary == zero
        count += 1
    assert count == 20301


def test_regular_solid_harmonics_degree_200_nonpolar() -> None:
    coordinates = tuple(map(Fraction, (0.31, -0.47, 0.83)))
    budget = trajectory._RefinementBudget("solid-nonpolar-200", 300.0)
    started_s, count, largest_bits = perf_counter(), 0, 0
    for degree, _, real, imaginary in _regular_solid_harmonic_jets(budget, coordinates, 200):
        for jet in (real, imaginary):
            assert sum((u * derivative for u, derivative in zip(coordinates, jet[1:], strict=True)), Fraction(0)) == degree * jet[0]
            largest_bits = max(largest_bits, *(max(value.numerator.bit_length(), value.denominator.bit_length()) for value in jet))
        count += 1
    budget.check()
    assert count == 20301
    assert budget.native_arc_propagations == 0
    print(json.dumps({"solid_nonpolar_degree_200_seconds": perf_counter() - started_s,
                      "solid_nonpolar_largest_integer_bits": largest_bits}, sort_keys=True))


@pytest.mark.parametrize("invalid", ["degree", "boolean", "coordinate"])
def test_regular_solid_harmonics_rejects_invalid_input(invalid: str) -> None:
    with pytest.raises(AssertionError):
        list(_regular_solid_harmonic_jets(
            trajectory._RefinementBudget("solid-invalid", 300.0),
            (0.0 if invalid == "coordinate" else Fraction(0), Fraction(0), Fraction(0)),  # type: ignore[arg-type] -- boundary rejection.
            -1 if invalid == "degree" else True if invalid == "boolean" else 0,
        ))


def test_regular_solid_harmonics_checks_deadline_between_rows() -> None:
    clock = iter([0.0, 0.0, 0.0, 0.0, 301.0])
    stream = _regular_solid_harmonic_jets(
        trajectory._RefinementBudget("solid-expired", 300.0, lambda: next(clock)), (Fraction(1),) * 3, 2,
    )
    assert next(stream)[:2] == (0, 0)
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        next(stream)


def _generic_harmonic_term_errors_m_s2(
    budget: trajectory._RefinementBudget, gm_m3_s2: float, reference_radius_m: float,
    cosine: np.ndarray, sine: np.ndarray, body_position_m: np.ndarray, spacecraft_position_m: np.ndarray,
    inertial_to_fixed: np.ndarray, observed_terms_m_s2: np.ndarray,
) -> dict[tuple[int, int], Fraction]:
    """Enclose each normalized term's L1 error at exact stored SI states/matrix."""
    budget.check()
    assert all(type(value) is float and math.isfinite(value) and value > 0 for value in (gm_m3_s2, reference_radius_m))
    assert cosine.ndim == 2 and cosine.shape == sine.shape and cosine.shape[0] == cosine.shape[1] > 0
    assert all(matrix.dtype == np.float64 and np.all(np.isfinite(matrix)) and not np.any(np.triu(matrix, 1))
               for matrix in (cosine, sine))
    assert not np.any(sine[:, 0])
    maximum_degree = len(cosine) - 1
    term_count = (maximum_degree + 1) * (maximum_degree + 2) // 2
    for array, shape in ((body_position_m, (3,)), (spacecraft_position_m, (3,)),
                         (inertial_to_fixed, (3, 3)), (observed_terms_m_s2, (term_count, 3))):
        assert array.shape == shape and array.dtype == np.float64 and np.all(np.isfinite(array))
    relative_m = [Fraction(ship) - Fraction(body) for ship, body in zip(spacecraft_position_m, body_position_m, strict=True)]
    matrix = [tuple(map(Fraction, row)) for row in inertial_to_fixed]
    fixed_m = [sum((a * r for a, r in zip(row, relative_m, strict=True)), Fraction(0)) for row in matrix]
    magnitude_m = max(map(abs, fixed_m))
    assert magnitude_m > 0
    # Any exact positive scale is valid; a power of two keeps coordinates near unity.
    scale_m = Fraction(2)**(magnitude_m.numerator.bit_length() - magnitude_m.denominator.bit_length())
    coordinates = tuple(value / scale_m for value in fixed_m)
    q = sum((value**2 for value in coordinates), Fraction(0))
    root_lower, root_upper = _dyadic_sqrt_bounds(q)
    radial_factor_m_s2 = Fraction(gm_m3_s2) / (scale_m**2 * q)
    radial_ratio = Fraction(reference_radius_m) / (scale_m * q)
    errors: dict[tuple[int, int], Fraction] = {}
    for index, (degree, order, real, imaginary) in enumerate(_regular_solid_harmonic_jets(budget, coordinates, maximum_degree)):
        if degree and order == 0:
            radial_factor_m_s2 *= radial_ratio
        c, s = Fraction(cosine[degree, order]), Fraction(sine[degree, order])
        jet = tuple(c * re + s * im for re, im in zip(real, imaginary, strict=True))
        normalization_squared = Fraction((2 if order else 1) * (2 * degree + 1) * math.factorial(degree - order),
                                         math.factorial(degree + order))
        norm_lower, norm_upper = _dyadic_sqrt_bounds(normalization_squared)
        polynomial_m_s2 = [radial_factor_m_s2 * (q * derivative - (2 * degree + 1) * jet[0] * u)
                           for derivative, u in zip(jet[1:], coordinates, strict=True)]
        error_m_s2 = Fraction(0)
        for axis, observed in enumerate(observed_terms_m_s2[index]):
            projected_m_s2 = sum((matrix[row][axis] * polynomial_m_s2[row] for row in range(3)), Fraction(0))
            endpoints_m_s2 = (projected_m_s2 * norm_lower / root_upper, projected_m_s2 * norm_upper / root_lower)
            error_m_s2 += max(abs(Fraction(observed) - value) for value in endpoints_m_s2)
        errors[degree, order] = error_m_s2
    budget.check()
    assert len(errors) == term_count
    return errors


@pytest.mark.parametrize("error_m_s2", [0.0, 0.125])
def test_generic_harmonic_monopole_matches_point_oracle(error_m_s2: float) -> None:
    body_m = np.full(3, 1e12)
    observed_m_s2 = np.asarray([[-3.0, 4.0, error_m_s2]])
    errors = _generic_harmonic_term_errors_m_s2(
        trajectory._RefinementBudget("generic-monopole", 300.0), 125.0, 1.0, np.ones((1, 1)), np.zeros((1, 1)),
        body_m, body_m + np.asarray([3.0, -4.0, 0.0]), np.eye(3), observed_m_s2,
    )
    assert errors == {(0, 0): Fraction(error_m_s2)}


@pytest.mark.parametrize("order", [0, 1, 2])
@pytest.mark.parametrize("distorted", [False, True])
def test_generic_harmonic_degree_two_matches_cartesian_oracle(order: int, distorted: bool) -> None:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[2, order], sine[2, order] = 0.125, -0.25 if order else 0.0
    matrix = np.diag([1.125, 0.875, 1.0]) if distorted else np.eye(3)
    body_m, ship_m = np.full(3, 1e12), np.full(3, 1e12) + np.asarray([1.0, -2.0, 3.0])
    general = _generic_harmonic_term_errors_m_s2(
        trajectory._RefinementBudget("generic-degree-two", 300.0), 1.0, 1.0, cosine, sine,
        body_m, ship_m, matrix, np.zeros((6, 3)),
    )[2, order]
    cartesian = _degree_two_anchor_error_bound_m_s2(
        1.0, 1.0, float(cosine[2, order]), float(sine[2, order]), order, body_m, ship_m, matrix, np.zeros(3),
    )
    assert abs(general - cartesian) <= max(Fraction(1), cartesian) * Fraction(2)**-90


@pytest.mark.parametrize("radius_m", [1.0, 2.0])
@pytest.mark.parametrize("kind", ["zonal", "cosine", "sine", "mixed"])
def test_generic_harmonic_degree_three_axis_oracles(radius_m: float, kind: str) -> None:
    cosine, sine = np.zeros((4, 4)), np.zeros((4, 4))
    order = 0 if kind == "zonal" else 3
    cosine[3, order] = 0.0 if kind == "sine" else 0.125
    sine[3, order] = -0.25 if kind in {"sine", "mixed"} else 0.0
    position_m = np.asarray([0.0, 0.0, radius_m]) if order == 0 else np.asarray([radius_m, 0.0, 0.0])
    bound_m_s2 = _generic_harmonic_term_errors_m_s2(
        trajectory._RefinementBudget("generic-degree-three", 300.0), 1.0, 1.0, cosine, sine,
        np.zeros(3), position_m, np.eye(3), np.zeros((10, 3)),
    )[3, order]
    # C30 at the pole: -4*sqrt(7)*C/r^5. At x-axis, C33/S33 give
    # (-sqrt(70)*C, 3*sqrt(70)*S/4, 0)/r^5.
    expected_squared = (112 * Fraction(0.125)**2 if order == 0 else
                        70 * (abs(Fraction(cosine[3, 3])) + Fraction(3, 4) * abs(Fraction(sine[3, 3])))**2) / Fraction(radius_m)**10
    assert expected_squared <= bound_m_s2**2 < expected_squared * (1 + Fraction(2)**-90)


@pytest.mark.parametrize("invalid", ["gm", "singularity", "sine"])
def test_generic_harmonic_rejects_invalid_input(invalid: str) -> None:
    with pytest.raises(AssertionError):
        _generic_harmonic_term_errors_m_s2(
            trajectory._RefinementBudget("generic-invalid", 300.0), math.nan if invalid == "gm" else 1.0, 1.0,
            np.ones((1, 1)), np.asarray([[1.0 if invalid == "sine" else 0.0]]), np.zeros(3),
            np.zeros(3) if invalid == "singularity" else np.ones(3), np.eye(3), np.zeros((1, 3)),
        )


def test_generic_harmonic_rejects_expired_budget() -> None:
    clock = iter([0.0, 301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _generic_harmonic_term_errors_m_s2(
            trajectory._RefinementBudget("generic-expired", 300.0, lambda: next(clock)), 1.0, 1.0,
            np.ones((1, 1)), np.zeros((1, 1)), np.zeros(3), np.ones(3), np.eye(3), np.zeros((1, 3)),
        )


def _harmonic_remainder_anchor_error_bound_m_s2(
    budget: trajectory._RefinementBudget, gm_m3_s2: float, reference_radius_m: float,
    distance_floor_m: float, cosine: np.ndarray, sine: np.ndarray,
    observed_remainder_m_s2: tuple[Fraction, ...],
    *, excluded_through_degree: int | None = None,
) -> Fraction:
    """Bound a remainder; optional prefix exclusion is diagnostic, not qualification."""
    budget.check()
    assert len(observed_remainder_m_s2) == 3 and all(isinstance(value, Fraction) for value in observed_remainder_m_s2)
    assert cosine.shape == sine.shape and cosine.ndim == 2 and len(cosine) >= 3
    assert all(matrix.dtype == np.float64 and np.all(np.isfinite(matrix)) for matrix in (cosine, sine))
    remainder_cosine, remainder_sine = cosine.copy(), sine.copy()
    remainder_cosine[0, 0] = 0.0
    remainder_cosine[2, :3] = remainder_sine[2, :3] = 0.0
    if excluded_through_degree is not None:
        assert type(excluded_through_degree) is int and 2 <= excluded_through_degree < len(cosine)
        remainder_cosine[:excluded_through_degree + 1] = remainder_sine[:excluded_through_degree + 1] = 0.0
    # ponytail: triangle bound is intentionally loose; qualify individual
    # remaining orders before treating this as a useful trajectory allocation.
    ideal_norm_m_s2 = trajectory._harmonic_acceleration_upper_bound(
        budget.candidate_id, gm_m3_s2, reference_radius_m, distance_floor_m, remainder_cosine, remainder_sine,
    )
    budget.check()
    return sum(map(abs, observed_remainder_m_s2), Fraction(ideal_norm_m_s2))


@pytest.mark.parametrize("degree", [1, 3])
@pytest.mark.parametrize("observed_m_s2", [Fraction(-1, 8), Fraction(0), Fraction(1, 8)])
def test_harmonic_remainder_preserves_unqualified_degrees(degree: int, observed_m_s2: Fraction) -> None:
    cosine, sine = np.zeros((4, 4)), np.zeros((4, 4))
    cosine[0, 0], cosine[2, 0], cosine[degree, 0] = 1000.0, 1000.0, 0.125
    original = cosine.copy()
    bound_m_s2 = _harmonic_remainder_anchor_error_bound_m_s2(
        trajectory._RefinementBudget("remainder-pole", 300.0), 1.0, 1.0, 1.0, cosine, sine,
        (Fraction(0), Fraction(0), observed_m_s2),
    )
    assert np.array_equal(cosine, original)
    # At the pole, an isolated zonal force is -(n+1)*sqrt(2n+1)*C_n0.
    # The bound must enclose either observation sign without using native gravity.
    assert (bound_m_s2 - abs(observed_m_s2))**2 >= (degree + 1)**2 * (2 * degree + 1) * Fraction(0.125)**2
    assert bound_m_s2 < 3  # The already qualified, large n=0,2 fields were excluded.


def test_harmonic_remainder_excludes_all_degree_two_orders() -> None:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[0, 0], cosine[2], sine[2] = 1000.0, (3.0, 4.0, 5.0), (0.0, 6.0, 7.0)
    original_cosine, original_sine = cosine.copy(), sine.copy()
    bound_m_s2 = _harmonic_remainder_anchor_error_bound_m_s2(
        trajectory._RefinementBudget("remainder-zero", 300.0), 1.0, 1.0, 1.0, cosine, sine,
        (Fraction(1), Fraction(-2), Fraction(3)),
    )
    assert bound_m_s2 == 6
    assert np.array_equal(cosine, original_cosine) and np.array_equal(sine, original_sine)


def test_harmonic_remainder_rejects_expired_budget() -> None:
    clock = iter([0.0, 301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _harmonic_remainder_anchor_error_bound_m_s2(
            trajectory._RefinementBudget("remainder-expired", 300.0, lambda: next(clock)),
            1.0, 1.0, 1.0, np.zeros((3, 3)), np.zeros((3, 3)), (Fraction(0),) * 3,
        )


@pytest.mark.parametrize("cutoff", [2, 3, 4])
def test_harmonic_remainder_diagnostic_prefix(cutoff: int) -> None:
    cosine, sine = np.zeros((5, 5)), np.zeros((5, 5))
    cosine[0, 0], cosine[1, 0], cosine[2, 0], cosine[3, 0] = 1000.0, 1000.0, 1000.0, 0.125
    original = cosine.copy()
    bound_m_s2 = _harmonic_remainder_anchor_error_bound_m_s2(
        trajectory._RefinementBudget("tail-prefix", 300.0), 1.0, 1.0, 1.0, cosine, sine,
        (Fraction(0),) * 3, excluded_through_degree=cutoff,
    )
    assert np.array_equal(cosine, original)
    if cutoff == 2:
        # Only C30 remains: norm bound (2n+1)*sqrt(n+1)*|C30|=7/4.
        assert Fraction(7, 4) <= bound_m_s2 < Fraction(7, 4) + Fraction(2)**-45
    else:
        assert bound_m_s2 == 0


@pytest.mark.parametrize("cutoff", [1, 5, True])
def test_harmonic_remainder_rejects_invalid_prefix(cutoff: int) -> None:
    with pytest.raises(AssertionError):
        _harmonic_remainder_anchor_error_bound_m_s2(
            trajectory._RefinementBudget("tail-prefix-invalid", 300.0), 1.0, 1.0, 1.0,
            np.zeros((5, 5)), np.zeros((5, 5)), (Fraction(0),) * 3, excluded_through_degree=cutoff,
        )


def _stored_matrix_force_error_bound_m_s2(
    budget: trajectory._RefinementBudget, gm_m3_s2: float, reference_radius_m: float,
    radius_squared_m2: Fraction, matrix_error: Fraction,
    cosine: np.ndarray, sine: np.ndarray,
) -> Fraction:
    """Bound |A.T g(A r) - Q.T g(Q r)|_2 for orthogonal Q and |A-Q|_2 <= e < 1."""
    budget.check()
    assert isinstance(radius_squared_m2, Fraction) and radius_squared_m2 > 0
    assert isinstance(matrix_error, Fraction) and 0 <= matrix_error < 1
    lower_m, upper_m = _dyadic_sqrt_bounds(radius_squared_m2)
    # The entire straight chord from Qr to Ar stays outside (1-e)*|r|.
    exact_floor_m = (1 - matrix_error) * lower_m
    floor_m = math.nextafter(float(exact_floor_m), -math.inf)
    assert math.isfinite(floor_m) and 0 < Fraction(floor_m) <= exact_floor_m
    acceleration_m_s2 = trajectory._harmonic_acceleration_upper_bound(
        budget.candidate_id, gm_m3_s2, reference_radius_m, floor_m, cosine, sine,
    )
    jacobian_s_inv2 = _harmonic_spatial_jacobian_bound_s_inv2(
        budget, gm_m3_s2, reference_radius_m, floor_m, cosine, sine,
    )
    budget.check()
    # (A-Q).T g(Ar) + Q.T [g(Ar)-g(Qr)]; A need not be orthogonal.
    # Unlike rotation-only bounds, do not discard C00 or cap by 2*|g|.
    return matrix_error * (Fraction(acceleration_m_s2) + jacobian_s_inv2 * upper_m)


@pytest.mark.parametrize("radius_m", [1, 2])
@pytest.mark.parametrize("scale", [Fraction(7, 8), Fraction(1), Fraction(9, 8)])
@pytest.mark.parametrize("coefficient", [-0.125, 0.125])
def test_stored_matrix_force_encloses_nonorthogonal_dilation(
    radius_m: int, scale: Fraction, coefficient: float,
) -> None:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[2, 0] = coefficient
    bound = _stored_matrix_force_error_bound_m_s2(
        trajectory._RefinementBudget("matrix-dilation", 300.0),
        1.0, 1.0, Fraction(radius_m**2), abs(scale - 1), cosine, sine,
    )
    # Q=I, A=scale*I, r=(0,0,radius). Homogeneity gives A.T*g(Ar)=scale^-3*g(r).
    exact_error_squared = 45 * Fraction(coefficient)**2 * (scale**-3 - 1)**2 / radius_m**8
    assert exact_error_squared <= bound**2
    assert (bound == 0) == (scale == 1)


def test_stored_matrix_force_encloses_proper_rotation_and_monopole_scaling() -> None:
    budget = trajectory._RefinementBudget("matrix-rotation", 300.0)
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[2, 0] = 0.125
    u = Fraction(1, 1000)  # tan(theta/2); |A-I|_2 <= 2*u.
    sin_squared = (2 * u / (1 + u**2))**2
    exact_squared = Fraction(5, 4) * Fraction(0.125)**2 * (36 * sin_squared + 45 * sin_squared**2)
    bound = _stored_matrix_force_error_bound_m_s2(budget, 1.0, 1.0, Fraction(1), 2 * u, cosine, sine)
    assert 0 < exact_squared <= bound**2
    # C00 is invariant under proper rotations, not under a rounded nonorthogonal matrix.
    bound = _stored_matrix_force_error_bound_m_s2(
        budget, 1.0, 1.0, Fraction(1), Fraction(1, 8), np.ones((1, 1)), np.zeros((1, 1)),
    )
    assert 0 < 1 - Fraction(9, 8)**-1 <= bound  # A=(9/8)*I, g(r)=-r/|r|^3.


@pytest.mark.parametrize(("squared", "error"), [
    (Fraction(0), Fraction(0)), (Fraction(1), Fraction(-1)),
    (Fraction(1), Fraction(1)), (Fraction(1), 0.125),
])
def test_stored_matrix_force_rejects_invalid_domain(squared: Fraction, error: Fraction | float) -> None:
    with pytest.raises(AssertionError):
        _stored_matrix_force_error_bound_m_s2(
            trajectory._RefinementBudget("matrix-domain", 300.0), 1.0, 1.0,
            squared, error, np.ones((1, 1)), np.zeros((1, 1)),  # type: ignore[arg-type] -- boundary rejection.
        )


def test_stored_matrix_force_rejects_expired_budget() -> None:
    clock = iter([0.0, 301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _stored_matrix_force_error_bound_m_s2(
            trajectory._RefinementBudget("matrix-expired", 300.0, lambda: next(clock)),
            1.0, 1.0, Fraction(1), Fraction(0), np.ones((1, 1)), np.zeros((1, 1)),
        )


@pytest.mark.parametrize("degree", [3, 8, 20, 50, 100, 120, 150])
@pytest.mark.parametrize("scale", [Fraction(127, 128), Fraction(1), Fraction(129, 128)])
@pytest.mark.parametrize("source_shift_m", [Fraction(-1, 128), Fraction(0), Fraction(1, 128)])
def test_harmonic_prefix_matrix_and_source_error_composition(
    degree: int, scale: Fraction, source_shift_m: Fraction,
) -> None:
    budget = trajectory._RefinementBudget("prefix-composition", 300.0)
    cosine, sine = np.zeros((degree + 1, degree + 1)), np.zeros((degree + 1, degree + 1))
    cosine[degree, 0] = 0.125
    orientation_error_m_s2 = _stored_matrix_force_error_bound_m_s2(
        budget, 1.0, 1.0, Fraction(1), abs(scale - 1), cosine, sine,
    )
    source_error_m_s2 = _harmonic_spatial_jacobian_bound_s_inv2(
        budget, 1.0, 1.0, float(1 - abs(source_shift_m)), cosine, sine,
    ) * abs(source_shift_m)
    # At the north pole, g_n=-(n+1)*sqrt(2*n+1)*C/r^(n+2).
    # A=scale*I gives A.T*g_n(A*r)=scale^(-n-1)*g_n(r).
    exact_error_squared = (degree + 1)**2 * (2 * degree + 1) * Fraction(0.125)**2 * (
        scale**(-degree - 1) - (1 - source_shift_m)**(-degree - 2)
    )**2
    assert exact_error_squared <= (orientation_error_m_s2 + source_error_m_s2)**2
    assert (orientation_error_m_s2 + source_error_m_s2 == 0) == (scale == 1 and source_shift_m == 0)


def _angle_limited_rotation_bound_m_s2(
    angle_rad: Fraction, acceleration_m_s2: Fraction,
    jacobian_s_inv2: Fraction, radius_upper_m: Fraction,
) -> Fraction:
    """Bound ideal rotation-only force change using nonmonopole norm bounds."""
    assert all(isinstance(value, Fraction) and value >= 0
               for value in (angle_rad, acceleration_m_s2, jacobian_s_inv2, radius_upper_m))
    assert radius_upper_m > 0
    return min(2 * acceleration_m_s2,
               angle_rad * (acceleration_m_s2 + jacobian_s_inv2 * radius_upper_m))


@pytest.mark.parametrize("half_angle_tangent", [Fraction(0), Fraction(1, 1000), Fraction(1)])
def test_angle_limited_rotation_encloses_exact_quadrupole(
    half_angle_tangent: Fraction,
) -> None:
    budget = trajectory._RefinementBudget("angle-control", 300.0)
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[2, 0] = 0.125
    norm = _harmonic_arbitrary_rotation_bound_m_s2(budget, 1.0, 1.0, 1.0, cosine, sine) / 2
    jacobian = _harmonic_spatial_jacobian_bound_s_inv2(budget, 1.0, 1.0, 1.0, cosine, sine)
    # theta=2*atan(u) <= 2*u and sin(theta)=2*u/(1+u^2), all exact here.
    u = half_angle_tangent
    angle_upper_rad = 2 * u
    sin_squared = (2 * u / (1 + u**2))**2
    # At inertial r=(0,0,1), rotate the quadrupole axis about y. Direct
    # differentiation gives delta-a squared = (5*c^2/4)*(36*sin^2+45*sin^4).
    exact_change_squared = Fraction(5, 4) * Fraction(0.125)**2 * (36 * sin_squared + 45 * sin_squared**2)
    bound = _angle_limited_rotation_bound_m_s2(angle_upper_rad, norm, jacobian, Fraction(1))
    assert exact_change_squared <= bound**2
    if u == 0:
        assert bound == 0
    elif u < 1:
        assert 0 < bound < 2 * norm
    else:
        assert bound == 2 * norm


def test_angle_limited_rotation_preserves_monopole_and_rejects_invalid_bounds() -> None:
    assert _angle_limited_rotation_bound_m_s2(Fraction(10), Fraction(0), Fraction(0), Fraction(1)) == 0
    with pytest.raises(AssertionError):
        _angle_limited_rotation_bound_m_s2(Fraction(-1), Fraction(1), Fraction(1), Fraction(1))
    with pytest.raises(AssertionError):
        _angle_limited_rotation_bound_m_s2(Fraction(1), Fraction(1), Fraction(1), Fraction(0))


def _coast_force_variation_bound_m_s2(
    point_m_s2: dict[str, float], spatial_m_s2: dict[str, float],
    rotation_m_s2: dict[str, float], srp_norm_m_s2: float, relativity_norm_m_s2: float,
) -> Fraction:
    """Sum conditional ideal force changes for coast, excluding native roundoff."""
    assert set(point_m_s2) == set(trajectory.PHYSICAL_BODY_NAMES) - {"Moon", "Mars"}
    assert set(spatial_m_s2) == set(rotation_m_s2) == {"Moon", "Mars"}
    gravity_values = (*point_m_s2.values(), *spatial_m_s2.values(), *rotation_m_s2.values())
    assert all(type(value) is float and math.isfinite(value) and value >= 0
               for value in (*gravity_values, srp_norm_m_s2, relativity_norm_m_s2))
    return (sum(map(Fraction, gravity_values), Fraction(0))
            + 2 * (Fraction(srp_norm_m_s2) + Fraction(relativity_norm_m_s2)))


@pytest.mark.parametrize("component_m_s2", [0.0, 0.1, 1.0])
def test_coast_force_variation_attains_aligned_component_changes(component_m_s2: float) -> None:
    point = {body: component_m_s2 for body in trajectory.PHYSICAL_BODY_NAMES if body not in {"Moon", "Mars"}}
    harmonic = dict.fromkeys(("Moon", "Mars"), component_m_s2)
    bound = _coast_force_variation_bound_m_s2(point, harmonic, harmonic, component_m_s2, component_m_s2)
    # Abstract collinear vector oracle, not a physical trajectory: ten gravity
    # change terms increase from zero by c each. The two norm-only terms
    # reverse from -c to +c, so the exact total change is 14*c along one axis.
    before = -2 * Fraction(component_m_s2)
    after = 12 * Fraction(component_m_s2)
    assert bound == abs(after - before)


@pytest.mark.parametrize("case", ["missing-point", "extra-rotation", "negative-norm"])
def test_coast_force_variation_rejects_invalid_components(case: str) -> None:
    point = {body: 1.0 for body in trajectory.PHYSICAL_BODY_NAMES if body not in {"Moon", "Mars"}}
    spatial, rotation = dict.fromkeys(("Moon", "Mars"), 1.0), dict.fromkeys(("Moon", "Mars"), 1.0)
    srp = 1.0
    if case == "missing-point":
        point.pop("Sun")
    elif case == "extra-rotation":
        rotation["Sun"] = 1.0
    else:
        srp = -1.0
    with pytest.raises(AssertionError):
        _coast_force_variation_bound_m_s2(point, spatial, rotation, srp, 1.0)


def _check_conditional_full_force_coast_domains(
    budget: trajectory._RefinementBudget, start_tdb_s: float, end_tdb_s: float,
    body_reaches_m: dict[float, dict[str, float]], sun_speed_upper_m_s: float,
    position_anchors_m: dict[str, np.ndarray],
    source_position_errors_m: dict[str, float],
    sun_velocity_error_m_s: float,
    *, source_affine_motion: dict[str, tuple[tuple[Fraction, ...], Fraction]],
    source_affine_positions_m: dict[str, tuple[Fraction, ...]],
    source_affine_coverage_s: float, run_native_controls: bool,
) -> list[dict[str, object]]:
    """Check conditional ideal domains and optional native endpoint residuals."""
    from test_trajectory_error_transport import _coast_error_envelope, _cubic_reference_endpoint
    from test_trajectory_force_derivatives import _point_mass_force_curvature_bound_m_s4
    from test_trajectory_gravity import _candidate, _spacecraft

    candidate = _candidate(
        departure_epoch_utc=ephemeris.tdb_to_utc(start_tdb_s),
        arrival_epoch_utc=ephemeris.tdb_to_utc(end_tdb_s),
        departure_epoch_tdb_s=start_tdb_s, arrival_epoch_tdb_s=end_tdb_s,
        flight_time_s=end_tdb_s - start_tdb_s,
    )
    spacecraft = _spacecraft()
    rotation_rates_rad_s, pck_angles_deg = _check_pinned_pck_rotation_rates(budget, start_tdb_s, end_tdb_s)
    environment = trajectory._build_physical_environment(candidate, spacecraft, budget=budget)
    bodies = environment.bodies
    states = {body: np.asarray(bodies.get(body).ephemeris.cartesian_state(start_tdb_s)).reshape(6)
              for body in trajectory.PHYSICAL_BODY_NAMES}
    assert set(source_affine_motion) == set(states)
    assert set(source_affine_positions_m) == set(states)
    assert all(np.all(np.isfinite(state)) for state in states.values())
    for body, state in states.items():
        assert np.array_equal(state[:3], position_anchors_m[body]), body
    assert set(source_position_errors_m) == set(states)
    assert all(type(error) is float and math.isfinite(error) and 0 <= error <= 0.001
               for error in source_position_errors_m.values())
    for body, position in source_affine_positions_m.items():
        assert len(position) == 3 and all(isinstance(value, Fraction) for value in position)
        assert sum((abs(Fraction(stored) - ideal) for stored, ideal in
                    zip(states[body][:3], position, strict=True)), Fraction(0)) <= Fraction(source_position_errors_m[body]), body
    assert type(sun_velocity_error_m_s) is float and math.isfinite(sun_velocity_error_m_s)
    assert 0 <= sun_velocity_error_m_s <= 1e-6
    assert sum((abs(Fraction(value)) for value in states["Sun"][3:]), Fraction(0)) <= Fraction(sun_speed_upper_m_s)
    guards_m = {surface.body: surface.guard_radius_m for surface in environment.collision_resource.surfaces}
    results: list[dict[str, object]] = []
    for center, radius_m in (("Moon", 1_837_400.0), ("Mars", 3_689_500.0)):
        # The stored SI state defines the exact initial condition of this control.
        state = states[center] + np.asarray([radius_m, 0.0, 0.0, 0.0, 1500.0, 0.0])
        source_error_floors_m = {
            body: trajectory._relative_distance_lower_bound(
                budget, tuple(state[:3]), tuple(states[body][:3]), 0.0, source_position_errors_m[body],
            ) for body in states
        }
        assert all(floor > 0 for floor in source_error_floors_m.values())
        point_jerk_intervals_m_s3: dict[str, list[list[float]]] = {}
        harmonic_monopole_jerks_m_s3: dict[str, list[list[float]]] = {}
        exact_monopole_jerks_m_s3: dict[str, tuple[tuple[Fraction, Fraction], ...]] = {}
        for source in trajectory.PHYSICAL_BODY_NAMES:
            if source in {"Moon", "Mars"}:
                field = bodies.get(source).gravity_field_model
                assert field.cosine_coefficients[0, 0] == 1.0 and field.sine_coefficients[0, 0] == 0.0
            budget.check()
            relative_position_m = tuple(Fraction(ship) - ideal for ship, ideal in
                                        zip(state[:3], source_affine_positions_m[source], strict=True))
            relative_velocity_m_s = tuple(Fraction(ship) - slope for ship, slope in
                                          zip(state[3:], source_affine_motion[source][0], strict=True))
            intervals = _point_mass_jerk_interval_m_s3(
                bodies.get(source).gravity_field_model.gravitational_parameter, relative_position_m, relative_velocity_m_s,
            )
            reported = [[math.nextafter(float(lower), -math.inf) if lower else 0.0,
                         math.nextafter(float(upper), math.inf) if upper else 0.0] for lower, upper in intervals]
            assert all(math.isfinite(a) and math.isfinite(b) and Fraction(a) <= lower <= upper <= Fraction(b)
                       for (a, b), (lower, upper) in zip(reported, intervals, strict=True))
            exact_monopole_jerks_m_s3[source] = intervals
            if source in {"Moon", "Mars"}:
                harmonic_monopole_jerks_m_s3[source] = reported
            else:
                point_jerk_intervals_m_s3[source] = reported
        assert set(point_jerk_intervals_m_s3) == set(trajectory.PHYSICAL_BODY_NAMES) - {"Moon", "Mars"}
        assert set(harmonic_monopole_jerks_m_s3) == {"Moon", "Mars"}
        assert set(exact_monopole_jerks_m_s3) == set(trajectory.PHYSICAL_BODY_NAMES)
        reference_jerk_m_s3 = tuple(sum((intervals[axis][0] + intervals[axis][1]
                                       for intervals in exact_monopole_jerks_m_s3.values()), Fraction(0)) / 2 for axis in range(3))
        reference_jerk_error_m_s3 = sum((upper - lower for intervals in exact_monopole_jerks_m_s3.values()
                                       for lower, upper in intervals), Fraction(0)) / 2
        initial_speed_m_s = sum((abs(Fraction(value)) for value in state[3:]), Fraction(0))
        initial_speed_upper_m_s = math.nextafter(float(initial_speed_m_s), math.inf)
        assert Fraction(initial_speed_upper_m_s) >= initial_speed_m_s
        domain_cases = [(duration_s, 1000.0, 0.1) for duration_s in body_reaches_m]
        if center == "Mars":
            domain_cases.extend(((1 / 16, 2000.0, 0.25), (1 / 8, 4000.0, 0.5)))
        for duration_s, position_radius_m, velocity_radius_m_s in domain_cases:
            reaches_m = body_reaches_m[duration_s]
            relative_speed_m_s = initial_speed_m_s + Fraction(velocity_radius_m_s) + Fraction(sun_speed_upper_m_s)
            relative_speed_upper_m_s = math.nextafter(float(relative_speed_m_s), math.inf)
            assert Fraction(relative_speed_upper_m_s) >= relative_speed_m_s
            budget.check()
            short_control = duration_s == 1 / 64
            floors_m: dict[str, float] = {}
            gravity_m_s2: dict[str, float] = {}
            point_mass_variation_m_s2: dict[str, float] = {}
            frozen_harmonic_variation_m_s2: dict[str, float] = {}
            arbitrary_rotation_variation_m_s2: dict[str, float] = {}
            angle_limited_rotation_variation_m_s2: dict[str, float] = {}
            harmonic_jacobians_s_inv2: dict[str, Fraction] = {}
            split_harmonic_jacobians_s_inv2: dict[str, Fraction] = {}
            for body in trajectory.PHYSICAL_BODY_NAMES:
                floor_m = trajectory._relative_distance_lower_bound(
                    budget, tuple(state[:3]), tuple(states[body][:3]), position_radius_m, reaches_m[body],
                )
                assert floor_m > guards_m[body]  # Only a declared position-domain property.
                floors_m[body] = floor_m
                field = bodies.get(body).gravity_field_model
                harmonic = body in {"Moon", "Mars"}
                if not harmonic:
                    variation_m_s2 = _point_mass_variation_bound_m_s2(
                        field.gravitational_parameter, floor_m,
                        Fraction(position_radius_m) + Fraction(reaches_m[body]),
                    )
                    reported_variation_m_s2 = math.nextafter(float(variation_m_s2), math.inf)
                    assert math.isfinite(reported_variation_m_s2)
                    assert Fraction(reported_variation_m_s2) >= variation_m_s2
                    point_mass_variation_m_s2[body] = reported_variation_m_s2
                else:
                    jacobian_s_inv2 = _harmonic_spatial_jacobian_bound_s_inv2(
                        budget, field.gravitational_parameter, field.reference_radius,
                        floor_m, field.cosine_coefficients, field.sine_coefficients,
                    )
                    harmonic_jacobians_s_inv2[body] = jacobian_s_inv2
                    variation_m_s2 = jacobian_s_inv2 * (Fraction(position_radius_m) + Fraction(reaches_m[body]))
                    reported_variation_m_s2 = math.nextafter(float(variation_m_s2), math.inf)
                    assert math.isfinite(reported_variation_m_s2)
                    assert Fraction(reported_variation_m_s2) >= variation_m_s2
                    frozen_harmonic_variation_m_s2[body] = reported_variation_m_s2
                    rotation_m_s2 = _harmonic_arbitrary_rotation_bound_m_s2(
                        budget, field.gravitational_parameter, field.reference_radius,
                        floor_m, field.cosine_coefficients, field.sine_coefficients,
                    )
                    reported_rotation_m_s2 = math.nextafter(float(rotation_m_s2), math.inf)
                    assert math.isfinite(reported_rotation_m_s2)
                    assert Fraction(reported_rotation_m_s2) >= rotation_m_s2
                    arbitrary_rotation_variation_m_s2[body] = reported_rotation_m_s2
                    nonmonopole_cosine = field.cosine_coefficients.copy()
                    nonmonopole_cosine[0, 0] = 0.0
                    tail_jacobian_s_inv2 = _harmonic_spatial_jacobian_bound_s_inv2(
                        budget, field.gravitational_parameter, field.reference_radius,
                        floor_m, nonmonopole_cosine, field.sine_coefficients,
                    )
                    assert field.cosine_coefficients[0, 0] == 1.0 and field.sine_coefficients[0, 0] == 0.0
                    split_harmonic_jacobians_s_inv2[body] = _monopole_split_jacobian_bound_s_inv2(
                        field.gravitational_parameter, floor_m, tail_jacobian_s_inv2,
                    )
                    assert split_harmonic_jacobians_s_inv2[body] < jacobian_s_inv2
                    radius_upper_m = sum((abs(Fraction(x) - Fraction(b)) for x, b in
                                          zip(state[:3], states[body][:3], strict=True)), Fraction(0))
                    radius_upper_m += Fraction(position_radius_m) + Fraction(reaches_m[body])
                    angle_limited_m_s2 = _angle_limited_rotation_bound_m_s2(
                        rotation_rates_rad_s[body] * Fraction(duration_s), rotation_m_s2 / 2,
                        tail_jacobian_s_inv2, radius_upper_m,
                    )
                    assert 0 < angle_limited_m_s2 < rotation_m_s2
                    # The linear branch, not the capped 2*norm branch, permits t/h scaling.
                    assert angle_limited_m_s2 == rotation_rates_rad_s[body] * Fraction(duration_s) * (
                        rotation_m_s2 / 2 + tail_jacobian_s_inv2 * radius_upper_m
                    )
                    reported_angle_limited_m_s2 = math.nextafter(float(angle_limited_m_s2), math.inf)
                    assert math.isfinite(reported_angle_limited_m_s2)
                    assert Fraction(reported_angle_limited_m_s2) >= angle_limited_m_s2
                    angle_limited_rotation_variation_m_s2[body] = reported_angle_limited_m_s2
                gravity_m_s2[body] = trajectory._harmonic_acceleration_upper_bound(
                    budget.candidate_id, field.gravitational_parameter,
                    field.reference_radius if harmonic else floor_m, floor_m,
                    field.cosine_coefficients if harmonic else ((1.0,),),
                    field.sine_coefficients if harmonic else ((0.0,),),
                )
            assert set(point_mass_variation_m_s2) == set(trajectory.PHYSICAL_BODY_NAMES) - {"Moon", "Mars"}
            assert set(frozen_harmonic_variation_m_s2) == {"Moon", "Mars"}
            assert set(arbitrary_rotation_variation_m_s2) == {"Moon", "Mars"}
            assert set(angle_limited_rotation_variation_m_s2) == {"Moon", "Mars"}
            domain_clear_by_body = {
                occultor: _apparent_spheres_strictly_disjoint(
                    states["Sun"][:3], bodies.get("Sun").shape_model.average_radius,
                    states[occultor][:3], bodies.get(occultor).shape_model.average_radius,
                    state[:3], source_position_error_m=reaches_m["Sun"],
                    occultor_position_error_m=reaches_m[occultor], observer_position_error_m=position_radius_m,
                ) for occultor in trajectory.SOLAR_RADIATION_OCCULTING_BODY_NAMES
            }
            assert set(domain_clear_by_body) == {"Moon", "Earth", "Mars"}
            assert all(domain_clear_by_body.values()), (center, duration_s, domain_clear_by_body)
            thrust, srp = trajectory._thrust_and_srp_upper_bounds(
                budget.candidate_id, spacecraft, floors_m["Sun"], thrust_enabled=False,
            )
            relativity = trajectory._schwarzschild_acceleration_upper_bound(
                budget.candidate_id, bodies.get("Sun").gravity_field_model.gravitational_parameter,
                floors_m["Sun"], relative_speed_upper_m_s,
            )
            relativity_sensitivities = _schwarzschild_state_jacobian_bounds(
                bodies.get("Sun").gravity_field_model.gravitational_parameter,
                floors_m["Sun"], Fraction(relative_speed_upper_m_s),
            )
            reported_relativity_sensitivities = tuple(math.nextafter(float(value), math.inf)
                                                      for value in relativity_sensitivities)
            assert all(math.isfinite(reported) and Fraction(reported) >= exact > 0 for reported, exact in
                       zip(reported_relativity_sensitivities, relativity_sensitivities, strict=True))
            # Fixed epoch and coast mass; the entire position domain is lit.
            position_sensitivities = dict(split_harmonic_jacobians_s_inv2)
            for body in point_mass_variation_m_s2:
                position_sensitivities[body] = _monopole_split_jacobian_bound_s_inv2(
                    bodies.get(body).gravity_field_model.gravitational_parameter, floors_m[body], Fraction(0),
                )
            position_sensitivities["Sun/SRP"] = _fully_lit_srp_position_jacobian_bound_s_inv2(
                trajectory.SUN_LUMINOSITY_W, spacecraft.srp_area_m2,
                spacecraft.reflectivity_coefficient, spacecraft.initial_mass_kg, floors_m["Sun"],
            )
            position_sensitivities["Sun/Schwarzschild"] = relativity_sensitivities[0]
            assert set(position_sensitivities) == set(trajectory.PHYSICAL_BODY_NAMES) | {"Sun/SRP", "Sun/Schwarzschild"}
            reported_position_sensitivities = {body: math.nextafter(float(value), math.inf)
                                              for body, value in position_sensitivities.items()}
            assert all(math.isfinite(value) and Fraction(value) >= position_sensitivities[body] > 0
                       for body, value in reported_position_sensitivities.items())
            full_position_sensitivity = sum(map(Fraction, reported_position_sensitivities.values()), Fraction(0))
            reported_full_position_sensitivity = math.nextafter(float(full_position_sensitivity), math.inf)
            assert math.isfinite(reported_full_position_sensitivity)
            assert Fraction(reported_full_position_sensitivity) >= full_position_sensitivity
            # Gravity and fully lit fixed-mass cannonball SRP do not depend on velocity.
            feedback = (Fraction(reported_full_position_sensitivity) * Fraction(duration_s)**2 / 2
                        + Fraction(reported_relativity_sensitivities[1]) * Fraction(duration_s))
            reported_feedback = math.nextafter(float(feedback), math.inf)
            assert math.isfinite(reported_feedback) and Fraction(reported_feedback) >= feedback > 0
            assert reported_feedback < 1  # Necessary lemma condition, not domain closure.
            acceleration_m_s2 = trajectory._sum_force_acceleration_bounds(
                budget, gravity_m_s2, thrust, srp, relativity, thrust_enabled=False,
            )
            assert Fraction(acceleration_m_s2) >= sum(map(Fraction, (*gravity_m_s2.values(), thrust, srp, relativity)))
            assert thrust == 0.0
            force_variation_m_s2 = _coast_force_variation_bound_m_s2(
                point_mass_variation_m_s2, frozen_harmonic_variation_m_s2,
                angle_limited_rotation_variation_m_s2, srp, relativity,
            )
            assert 0 < force_variation_m_s2 < 2 * Fraction(acceleration_m_s2)
            reported_force_variation_m_s2 = math.nextafter(float(force_variation_m_s2), math.inf)
            assert math.isfinite(reported_force_variation_m_s2)
            assert Fraction(reported_force_variation_m_s2) >= force_variation_m_s2
            budget.check()
            reach_m = trajectory._position_reach_upper_bound(
                budget, duration_s, 0.0, initial_speed_upper_m_s, acceleration_m_s2,
            )
            velocity_reach_m_s = Fraction(acceleration_m_s2) * Fraction(duration_s)
            mass_floor_kg = trajectory._mass_lower_bound(budget, spacecraft.initial_mass_kg, 0.0, 0.0, duration_s)
            assert mass_floor_kg == spacecraft.initial_mass_kg > spacecraft.dry_mass_kg
            closed = reach_m < position_radius_m and velocity_reach_m_s < Fraction(velocity_radius_m_s)
            assert closed is (short_control or (center == "Mars" and (
                duration_s == 1 / 32 or (duration_s == 1 / 16 and position_radius_m == 2000.0)
                or (duration_s == 1 / 8 and position_radius_m == 4000.0)
            ))), (
                center, duration_s, position_radius_m, velocity_radius_m_s, reach_m, float(velocity_reach_m_s),
            )
            relative_reaches_m: dict[str, float] = {}
            reported_relative_variation_m_s2: float | None = None
            reported_split_relative_variation_m_s2: float | None = None
            if closed:
                # First close the original domain; only then use its acceleration
                # bound to tighten relative displacement, avoiding circular proof.
                relative_point_m_s2: dict[str, float] = {}
                relative_harmonic_m_s2: dict[str, float] = {}
                split_relative_harmonic_m_s2: dict[str, float] = {}
                for body, (slope, curvature) in source_affine_motion.items():
                    budget.check()
                    displacement_m = _relative_affine_displacement_upper_m(
                        state[3:], slope, duration_s, acceleration_m_s2, curvature, source_affine_coverage_s,
                    )
                    assert displacement_m < Fraction(position_radius_m) + Fraction(reaches_m[body])
                    reported_displacement_m = math.nextafter(float(displacement_m), math.inf)
                    assert math.isfinite(reported_displacement_m) and Fraction(reported_displacement_m) >= displacement_m
                    relative_reaches_m[body] = reported_displacement_m
                    if body in harmonic_jacobians_s_inv2:
                        change_m_s2 = harmonic_jacobians_s_inv2[body] * displacement_m
                        destination = relative_harmonic_m_s2
                        split_change_m_s2 = split_harmonic_jacobians_s_inv2[body] * displacement_m
                        reported_split_change_m_s2 = math.nextafter(float(split_change_m_s2), math.inf)
                        assert math.isfinite(reported_split_change_m_s2) and Fraction(reported_split_change_m_s2) >= split_change_m_s2
                        split_relative_harmonic_m_s2[body] = reported_split_change_m_s2
                    else:
                        change_m_s2 = _point_mass_variation_bound_m_s2(
                            bodies.get(body).gravity_field_model.gravitational_parameter, floors_m[body], displacement_m,
                        )
                        destination = relative_point_m_s2
                    reported_change_m_s2 = math.nextafter(float(change_m_s2), math.inf)
                    assert math.isfinite(reported_change_m_s2) and Fraction(reported_change_m_s2) >= change_m_s2
                    destination[body] = reported_change_m_s2
                relative_variation_m_s2 = _coast_force_variation_bound_m_s2(
                    relative_point_m_s2, relative_harmonic_m_s2, angle_limited_rotation_variation_m_s2, srp, relativity,
                )
                assert 0 < relative_variation_m_s2 < force_variation_m_s2
                reported_relative_variation_m_s2 = math.nextafter(float(relative_variation_m_s2), math.inf)
                assert math.isfinite(reported_relative_variation_m_s2) and Fraction(reported_relative_variation_m_s2) >= relative_variation_m_s2
                split_relative_variation_m_s2 = _coast_force_variation_bound_m_s2(
                    relative_point_m_s2, split_relative_harmonic_m_s2, angle_limited_rotation_variation_m_s2, srp, relativity,
                )
                assert 0 < split_relative_variation_m_s2 < relative_variation_m_s2
                reported_split_relative_variation_m_s2 = math.nextafter(float(split_relative_variation_m_s2), math.inf)
                assert math.isfinite(reported_split_relative_variation_m_s2)
                assert Fraction(reported_split_relative_variation_m_s2) >= split_relative_variation_m_s2
            endpoint_controls: list[dict[str, object]] = []
            first_acceleration_m_s2: np.ndarray | None = None
            if run_native_controls and closed:
                from tudatpy.astro.time_representation import Time
                from tudatpy.astro import fundamentals
                from tudatpy.dynamics import propagation_setup

                for tighter in ((False, True) if short_control else (False,)):
                    control_started_s = perf_counter()
                    budget.begin_control()
                    models = trajectory._build_arc_force_models(budget.candidate_id, environment)
                    final_tdb_s = start_tdb_s + duration_s
                    settings = trajectory._build_coupled_arc_settings(
                        budget.candidate_id, bodies, models, state, spacecraft.initial_mass_kg, start_tdb_s,
                        trajectory._build_arc_integrator(budget.candidate_id, "coast", tighter=tighter),
                        propagation_setup.propagator.time_termination(final_tdb_s, terminate_exactly_on_final_condition=True),
                        thrust_enabled=False,
                    )
                    acceleration = propagation_setup.acceleration
                    output_variables = [propagation_setup.dependent_variable.total_acceleration("Spacecraft")]
                    for source in trajectory.PHYSICAL_BODY_NAMES:
                        kind = (acceleration.spherical_harmonic_gravity_type if source in {"Moon", "Mars"}
                                else acceleration.point_mass_gravity_type)
                        output_variables.append(propagation_setup.dependent_variable.single_acceleration(
                            kind, "Spacecraft", source,
                        ))
                    output_variables.extend(propagation_setup.dependent_variable.single_acceleration(
                        kind, "Spacecraft", "Sun",
                    ) for kind in (acceleration.radiation_pressure_type, acceleration.relativistic_correction_acceleration_type))
                    output_variables.append(propagation_setup.dependent_variable.received_irradiance_shadow_function(
                        "Spacecraft", "Sun",
                    ))
                    output_variables.extend(propagation_setup.dependent_variable.spherical_harmonic_terms_acceleration(
                        "Spacecraft", source, [(0, 0)],
                    ) for source in ("Moon", "Mars"))
                    output_variables.extend(propagation_setup.dependent_variable.spherical_harmonic_terms_acceleration(
                        "Spacecraft", source, [(2, 0)],
                    ) for source in ("Moon", "Mars"))
                    output_variables.extend(propagation_setup.dependent_variable.inertial_to_body_fixed_rotation_frame(
                        source,
                    ) for source in ("Moon", "Mars"))
                    output_variables.extend(propagation_setup.dependent_variable.spherical_harmonic_terms_acceleration(
                        "Spacecraft", source, [(2, 1), (2, 2)],
                    ) for source in ("Moon", "Mars"))
                    harmonic_indices = {source: [(degree, order) for degree in range(limit + 1)
                                                for order in range(degree + 1)]
                                        for source, limit in (("Moon", 200), ("Mars", 120))}
                    assert {source: len(indices) for source, indices in harmonic_indices.items()} == {"Moon": 20301, "Mars": 7381}
                    output_variables.extend(propagation_setup.dependent_variable.spherical_harmonic_terms_acceleration(
                        "Spacecraft", source, indices,
                    ) for source, indices in harmonic_indices.items())
                    # Pinned binding accepts double time, not these native-Time
                    # settings. Retain the incompatibility as a regression check.
                    with pytest.raises(TypeError, match="SingleArcPropagatorSettings<double, double>"):
                        propagation_setup.propagator.add_dependent_variable_settings(output_variables, settings)
                    original_settings = settings
                    children = [child for group in settings.propagator_settings_per_type.values() for child in group]
                    assert len(children) == 2
                    settings = propagation_setup.propagator.multitype(
                        children, original_settings.integrator_settings, start_tdb_s,
                        original_settings.termination_settings, output_variables=output_variables,
                        processing_settings=original_settings.processing_settings,
                    )
                    assert np.array_equal(settings.initial_states, original_settings.initial_states)
                    native_started_s = perf_counter()
                    simulator = trajectory._run_native_arc(budget, bodies, settings, first_in_evaluation=True)
                    native_elapsed_s = perf_counter() - native_started_s
                    assert math.isfinite(native_elapsed_s) and native_elapsed_s > 0
                    assert simulator.integration_completed_successfully
                    history = simulator.state_history_time_object
                    first_epoch, last_epoch = min(history), max(history)
                    assert (first_epoch - Time(start_tdb_s)).to_float() == 0.0
                    assert (last_epoch - Time(final_tdb_s)).to_float() == 0.0
                    assert np.array_equal(np.asarray(history[first_epoch]).reshape(7)[:6], state)
                    force_history = simulator.dependent_variable_history_time_object
                    force_epoch = min(force_history)
                    assert (force_epoch - first_epoch).to_float() == 0.0
                    force_values = np.asarray(force_history[force_epoch]).reshape(-1)
                    assert force_values.shape == (83122,) and np.all(np.isfinite(force_values))
                    anchor_m_s2, components_m_s2 = force_values[:3], force_values[3:33].reshape(10, 3)
                    shadow = float(force_values[33])
                    source_radius_m = bodies.get("Sun").shape_model.average_radius
                    clear_by_body: dict[str, bool] = {}
                    conditional_clear_by_body: dict[str, bool] = {}
                    for occultor in trajectory.SOLAR_RADIATION_OCCULTING_BODY_NAMES:
                        occultor_radius_m = bodies.get(occultor).shape_model.average_radius
                        clear_by_body[occultor] = _apparent_spheres_strictly_disjoint(
                            states["Sun"][:3], source_radius_m, states[occultor][:3],
                            occultor_radius_m, state[:3],
                        )
                        assert clear_by_body[occultor], (center, occultor)
                        conditional_clear_by_body[occultor] = _apparent_spheres_strictly_disjoint(
                            states["Sun"][:3], source_radius_m, states[occultor][:3], occultor_radius_m, state[:3],
                            source_position_error_m=source_position_errors_m["Sun"],
                            occultor_position_error_m=source_position_errors_m[occultor],
                        )
                        assert conditional_clear_by_body[occultor], (center, occultor, "source-position balls")
                        direct_shadow = fundamentals.compute_shadow_function(
                            states["Sun"][:3], source_radius_m, states[occultor][:3],
                            occultor_radius_m, state[:3],
                        )
                        assert abs(direct_shadow - 1.0) <= 1e-12
                    assert set(clear_by_body) == {"Moon", "Earth", "Mars"}
                    assert shadow == 1.0  # Exact full illumination at this observed anchor only.
                    srp_anchor_error_m_s2 = _fully_lit_srp_anchor_error_bound_m_s2(
                        states["Sun"][:3], state[:3], trajectory.SUN_LUMINOSITY_W,
                        spacecraft.srp_area_m2, spacecraft.reflectivity_coefficient,
                        spacecraft.initial_mass_kg, components_m_s2[8],
                    )
                    assert srp_anchor_error_m_s2 <= Fraction(1e-15)
                    reported_srp_error_m_s2 = math.nextafter(float(srp_anchor_error_m_s2), math.inf)
                    assert math.isfinite(reported_srp_error_m_s2)
                    assert Fraction(reported_srp_error_m_s2) >= srp_anchor_error_m_s2
                    conditional_srp_error_m_s2 = srp_anchor_error_m_s2 + _fully_lit_srp_position_variation_bound_m_s2(
                        trajectory.SUN_LUMINOSITY_W, spacecraft.srp_area_m2, spacecraft.reflectivity_coefficient,
                        spacecraft.initial_mass_kg, source_error_floors_m["Sun"], Fraction(source_position_errors_m["Sun"]),
                    )
                    reported_conditional_srp_error_m_s2 = math.nextafter(float(conditional_srp_error_m_s2), math.inf)
                    assert math.isfinite(reported_conditional_srp_error_m_s2)
                    assert Fraction(reported_conditional_srp_error_m_s2) >= conditional_srp_error_m_s2
                    exact_sum = [sum(map(Fraction, components_m_s2[:, axis]), Fraction(0)) for axis in range(3)]
                    sum_residual = [Fraction(anchor_m_s2[axis]) - exact_sum[axis] for axis in range(3)]
                    component_norm_sum = float(np.linalg.norm(components_m_s2, axis=1).sum())
                    force_tolerance_m_s2 = max(1e-15, 1e-12 * component_norm_sum)
                    assert sum(value**2 for value in sum_residual) <= Fraction(force_tolerance_m_s2)**2
                    point_anchor_error_upper_m_s2: dict[str, float] = {}
                    conditional_point_spk_error_upper_m_s2: dict[str, float] = {}
                    for source, component in zip(trajectory.PHYSICAL_BODY_NAMES, components_m_s2[:8], strict=True):
                        if source not in {"Moon", "Mars"}:
                            relative_m = states[source][:3] - state[:3]
                            direct_m_s2 = bodies.get(source).gravity_field_model.gravitational_parameter * relative_m / np.linalg.norm(relative_m)**3
                            assert np.linalg.norm(component - direct_m_s2) <= max(1e-15, 1e-12 * np.linalg.norm(direct_m_s2))
                            point_error_m_s2 = _point_gravity_anchor_error_bound_m_s2(
                                bodies.get(source).gravity_field_model.gravitational_parameter,
                                states[source][:3], state[:3], component,
                            )
                            assert point_error_m_s2 <= Fraction(float(max(1e-15, 1e-12 * np.linalg.norm(direct_m_s2))))
                            reported_point_error_m_s2 = math.nextafter(float(point_error_m_s2), math.inf)
                            assert math.isfinite(reported_point_error_m_s2)
                            assert Fraction(reported_point_error_m_s2) >= point_error_m_s2
                            point_anchor_error_upper_m_s2[source] = reported_point_error_m_s2
                            combined_error = point_error_m_s2 + _point_mass_variation_bound_m_s2(
                                bodies.get(source).gravity_field_model.gravitational_parameter,
                                source_error_floors_m[source], Fraction(source_position_errors_m[source]),
                            )
                            reported_combined = math.nextafter(float(combined_error), math.inf)
                            assert math.isfinite(reported_combined) and Fraction(reported_combined) >= combined_error
                            conditional_point_spk_error_upper_m_s2[source] = reported_combined
                    assert set(point_anchor_error_upper_m_s2) == set(trajectory.PHYSICAL_BODY_NAMES) - {"Moon", "Mars"}
                    harmonic_monopole_error_upper_m_s2: dict[str, float] = {}
                    harmonic_monopoles_m_s2 = force_values[34:40].reshape(2, 3)
                    for source, observed in zip(("Moon", "Mars"), harmonic_monopoles_m_s2, strict=True):
                        field = bodies.get(source).gravity_field_model
                        assert field.cosine_coefficients[0, 0] == 1.0
                        assert field.sine_coefficients[0, 0] == 0.0
                        monopole_error_m_s2 = _point_gravity_anchor_error_bound_m_s2(
                            field.gravitational_parameter, states[source][:3], state[:3], observed,
                        )
                        tolerance_m_s2 = max(1e-15, 1e-12 * float(np.linalg.norm(observed)))
                        assert monopole_error_m_s2 <= Fraction(tolerance_m_s2), (center, source)
                        reported_monopole_error_m_s2 = math.nextafter(float(monopole_error_m_s2), math.inf)
                        assert math.isfinite(reported_monopole_error_m_s2)
                        assert Fraction(reported_monopole_error_m_s2) >= monopole_error_m_s2
                        harmonic_monopole_error_upper_m_s2[source] = reported_monopole_error_m_s2
                        combined_error = monopole_error_m_s2 + _point_mass_variation_bound_m_s2(
                            field.gravitational_parameter, source_error_floors_m[source], Fraction(source_position_errors_m[source]),
                        )
                        reported_combined = math.nextafter(float(combined_error), math.inf)
                        assert math.isfinite(reported_combined) and Fraction(reported_combined) >= combined_error
                        conditional_point_spk_error_upper_m_s2[source] = reported_combined
                    assert set(harmonic_monopole_error_upper_m_s2) == {"Moon", "Mars"}
                    assert set(conditional_point_spk_error_upper_m_s2) == set(states)
                    import spiceypy as spice

                    c20_error_upper_m_s2: dict[str, float] = {}
                    degree_two_error_upper_m_s2: dict[str, dict[str, float]] = {}
                    pck_matrix_error_upper: dict[str, float] = {}
                    degree_two_ideal_pck_error_upper_m_s2: dict[str, float] = {}
                    conditional_degree_two_spk_pck_error_upper_m_s2: dict[str, float] = {}
                    for index, source in enumerate(("Moon", "Mars")):
                        field = bodies.get(source).gravity_field_model
                        observed_c20_m_s2 = force_values[40:46].reshape(2, 3)[index]
                        rotation = force_values[46:64].reshape(2, 3, 3)[index]
                        assert np.max(np.abs(rotation - spice.pxform("J2000", f"IAU_{source.upper()}", start_tdb_s))) <= 1e-14
                        budget.check()
                        matrix_error = _pck_matrix_error_bound(pck_angles_deg[source], rotation)
                        reported_matrix_error = math.nextafter(float(matrix_error), math.inf)
                        assert math.isfinite(reported_matrix_error) and Fraction(reported_matrix_error) >= matrix_error
                        pck_matrix_error_upper[source] = reported_matrix_error
                        budget.check()
                        assert field.sine_coefficients[2, 0] == 0.0
                        c20_error_m_s2 = _degree_two_anchor_error_bound_m_s2(
                            field.gravitational_parameter, field.reference_radius, float(field.cosine_coefficients[2, 0]),
                            0.0, 0,
                            states[source][:3], state[:3], rotation, observed_c20_m_s2,
                        )
                        assert c20_error_m_s2 <= Fraction(1e-15), (center, source)
                        reported_c20_error_m_s2 = math.nextafter(float(c20_error_m_s2), math.inf)
                        assert math.isfinite(reported_c20_error_m_s2) and Fraction(reported_c20_error_m_s2) >= c20_error_m_s2
                        c20_error_upper_m_s2[source] = reported_c20_error_m_s2
                        degree_two_error_upper_m_s2[source] = {"0": reported_c20_error_m_s2}
                        stored_error_m_s2 = c20_error_m_s2
                        for order in (1, 2):
                            observed_term = force_values[64:76].reshape(2, 2, 3)[index, order - 1]
                            term_error_m_s2 = _degree_two_anchor_error_bound_m_s2(
                                field.gravitational_parameter, field.reference_radius,
                                float(field.cosine_coefficients[2, order]), float(field.sine_coefficients[2, order]), order,
                                states[source][:3], state[:3], rotation, observed_term,
                            )
                            assert term_error_m_s2 <= Fraction(1e-15), (center, source, order)
                            reported_term_error_m_s2 = math.nextafter(float(term_error_m_s2), math.inf)
                            assert math.isfinite(reported_term_error_m_s2) and Fraction(reported_term_error_m_s2) >= term_error_m_s2
                            degree_two_error_upper_m_s2[source][str(order)] = reported_term_error_m_s2
                            stored_error_m_s2 += term_error_m_s2
                        degree_two_cosine, degree_two_sine = np.zeros((3, 3)), np.zeros((3, 3))
                        degree_two_cosine[2] = field.cosine_coefficients[2, :3]
                        degree_two_sine[2] = field.sine_coefficients[2, :3]
                        squared_radius_m2 = sum(((Fraction(ship) - Fraction(body))**2 for ship, body in
                                                 zip(state[:3], states[source][:3], strict=True)), Fraction(0))
                        orientation_error_m_s2 = _stored_matrix_force_error_bound_m_s2(
                            budget, field.gravitational_parameter, field.reference_radius,
                            squared_radius_m2, matrix_error, degree_two_cosine, degree_two_sine,
                        )
                        # Exact sum of the three saved vectors: no extra float summation is claimed.
                        ideal_error_m_s2 = stored_error_m_s2 + orientation_error_m_s2
                        reported_ideal_error_m_s2 = math.nextafter(float(ideal_error_m_s2), math.inf)
                        assert math.isfinite(reported_ideal_error_m_s2) and Fraction(reported_ideal_error_m_s2) >= ideal_error_m_s2
                        degree_two_ideal_pck_error_upper_m_s2[source] = reported_ideal_error_m_s2
                        source_force_error_m_s2 = _harmonic_spatial_jacobian_bound_s_inv2(
                            budget, field.gravitational_parameter, field.reference_radius,
                            source_error_floors_m[source], degree_two_cosine, degree_two_sine,
                        ) * Fraction(source_position_errors_m[source])
                        combined_error = ideal_error_m_s2 + source_force_error_m_s2
                        reported_combined = math.nextafter(float(combined_error), math.inf)
                        assert math.isfinite(reported_combined) and Fraction(reported_combined) >= combined_error
                        conditional_degree_two_spk_pck_error_upper_m_s2[source] = reported_combined
                    harmonic_sum_residual_upper_m_s2: dict[str, float] = {}
                    conditional_remainder_error_upper_m_s2: dict[str, float] = {}
                    diagnostic_tail_profiles_m_s2: dict[str, dict[str, float]] = {}
                    generic_degree_three_errors_m_s2: dict[str, dict[str, float]] = {}
                    conditional_additional_prefix_errors_m_s2: dict[str, Fraction] = {}
                    generic_prefix_elapsed_s: dict[str, float] = {}
                    # Test-only allocation: distant high-degree terms remain
                    # enclosed by the tail bound, never omitted from dynamics.
                    prefix_degrees = {
                        "Moon": 150 if center == "Moon" else 20,
                        "Mars": 120 if center == "Mars" else 20,
                    }
                    harmonic_offset = 76
                    for index, (source, indices) in enumerate(harmonic_indices.items()):
                        budget.check()
                        terms = force_values[harmonic_offset:harmonic_offset + 3 * len(indices)].reshape(-1, 3)
                        harmonic_offset += 3 * len(indices)
                        # Check degree/order mapping against the earlier individually requested terms.
                        assert np.array_equal(terms[0], harmonic_monopoles_m_s2[index])
                        assert np.array_equal(terms[3], force_values[40:46].reshape(2, 3)[index])
                        assert np.array_equal(terms[4:6], force_values[64:76].reshape(2, 2, 3)[index])
                        exact_term_sum = [sum(map(Fraction, terms[:, axis]), Fraction(0)) for axis in range(3)]
                        observed_total = components_m_s2[trajectory.PHYSICAL_BODY_NAMES.index(source)]
                        residual_m_s2 = sum((abs(Fraction(value) - exact) for value, exact in
                                            zip(observed_total, exact_term_sum, strict=True)), Fraction(0))
                        tolerance_m_s2 = max(1e-15, 1e-12 * float(np.linalg.norm(terms, axis=1).sum()))
                        assert residual_m_s2 <= Fraction(tolerance_m_s2), (center, source)
                        reported_residual_m_s2 = math.nextafter(float(residual_m_s2), math.inf)
                        assert math.isfinite(reported_residual_m_s2) and Fraction(reported_residual_m_s2) >= residual_m_s2
                        harmonic_sum_residual_upper_m_s2[source] = reported_residual_m_s2
                        observed_remainder_m_s2 = tuple(exact_term_sum[axis] - sum(
                            (Fraction(terms[term, axis]) for term in (0, 3, 4, 5)), Fraction(0),
                        ) for axis in range(3))
                        field = bodies.get(source).gravity_field_model
                        prefix_degree = prefix_degrees[source]
                        prefix_count = (prefix_degree + 1) * (prefix_degree + 2) // 2
                        prefix_cosine = field.cosine_coefficients[:prefix_degree + 1, :prefix_degree + 1].copy()
                        prefix_sine = field.sine_coefficients[:prefix_degree + 1, :prefix_degree + 1].copy()
                        prefix_started_s = perf_counter()
                        generic_errors = _generic_harmonic_term_errors_m_s2(
                            budget, field.gravitational_parameter, field.reference_radius,
                            prefix_cosine, prefix_sine,
                            states[source][:3], state[:3], force_values[46:64].reshape(2, 3, 3)[index], terms[:prefix_count],
                        )
                        generic_prefix_elapsed_s[source] = perf_counter() - prefix_started_s
                        assert list(generic_errors) == indices[:prefix_count]
                        for term_index, ((degree, order), error_m_s2) in enumerate(generic_errors.items()):
                            gate_m_s2 = max(1e-15, 1e-12 * float(np.linalg.norm(terms[term_index])))
                            assert error_m_s2 <= Fraction(gate_m_s2), (center, source, degree, order, float(error_m_s2))
                        generic_degree_three_errors_m_s2[source] = {}
                        for order in range(4):
                            error_m_s2 = generic_errors[3, order]
                            reported_generic_m_s2 = math.nextafter(float(error_m_s2), math.inf) if error_m_s2 else 0.0
                            assert math.isfinite(reported_generic_m_s2) and Fraction(reported_generic_m_s2) >= error_m_s2
                            generic_degree_three_errors_m_s2[source][str(order)] = reported_generic_m_s2
                        # Degrees zero and two already have separate SPK/PCK bounds.
                        # Compose only the newly qualified, disjoint prefix terms.
                        for matrix in (prefix_cosine, prefix_sine):
                            matrix[0] = 0.0
                            matrix[2] = 0.0
                        additional_stored_error_m_s2 = sum((error for (degree, _), error in generic_errors.items()
                                                          if degree not in (0, 2)), Fraction(0))
                        squared_radius_m2 = sum(((Fraction(ship) - Fraction(body))**2 for ship, body in
                                                 zip(state[:3], states[source][:3], strict=True)), Fraction(0))
                        additional_orientation_error_m_s2 = _stored_matrix_force_error_bound_m_s2(
                            budget, field.gravitational_parameter, field.reference_radius, squared_radius_m2,
                            Fraction(pck_matrix_error_upper[source]), prefix_cosine, prefix_sine,
                        )
                        additional_source_error_m_s2 = _harmonic_spatial_jacobian_bound_s_inv2(
                            budget, field.gravitational_parameter, field.reference_radius, source_error_floors_m[source],
                            prefix_cosine, prefix_sine,
                        ) * Fraction(source_position_errors_m[source])
                        conditional_additional_prefix_errors_m_s2[source] = (
                            additional_stored_error_m_s2 + additional_orientation_error_m_s2 + additional_source_error_m_s2
                        )
                        remainder_error_m_s2 = _harmonic_remainder_anchor_error_bound_m_s2(
                            budget, field.gravitational_parameter, field.reference_radius, source_error_floors_m[source],
                            field.cosine_coefficients, field.sine_coefficients, observed_remainder_m_s2,
                        )
                        reported_remainder_m_s2 = math.nextafter(float(remainder_error_m_s2), math.inf)
                        assert math.isfinite(reported_remainder_m_s2) and Fraction(reported_remainder_m_s2) >= remainder_error_m_s2
                        conditional_remainder_error_upper_m_s2[source] = reported_remainder_m_s2
                        # Hypothetically exclude successive degree prefixes; this
                        # never substitutes for qualifying their native arithmetic.
                        tail_sum_m_s2, cursor = list(exact_term_sum), 0
                        diagnostic_tail_profiles_m_s2[source] = {}
                        maximum_degree = len(field.cosine_coefficients) - 1
                        for cutoff in sorted({degree for degree in (2, 5, 10, 20, 50, 100, 120, 150, maximum_degree)
                                              if degree <= maximum_degree}):
                            budget.check()
                            stop = (cutoff + 1) * (cutoff + 2) // 2
                            assert indices[stop - 1] == (cutoff, cutoff)
                            for axis in range(3):
                                tail_sum_m_s2[axis] -= sum(map(Fraction, terms[cursor:stop, axis]), Fraction(0))
                            cursor = stop
                            tail_error_m_s2 = _harmonic_remainder_anchor_error_bound_m_s2(
                                budget, field.gravitational_parameter, field.reference_radius, source_error_floors_m[source],
                                field.cosine_coefficients, field.sine_coefficients, tuple(tail_sum_m_s2),
                                excluded_through_degree=cutoff,
                            )
                            reported_tail_m_s2 = math.nextafter(float(tail_error_m_s2), math.inf) if tail_error_m_s2 else 0.0
                            assert math.isfinite(reported_tail_m_s2) and Fraction(reported_tail_m_s2) >= tail_error_m_s2
                            diagnostic_tail_profiles_m_s2[source][str(cutoff)] = reported_tail_m_s2
                        assert cursor == len(indices) and tail_sum_m_s2 == [Fraction(0)] * 3
                        assert diagnostic_tail_profiles_m_s2[source][str(maximum_degree)] == 0.0
                    assert harmonic_offset == len(force_values)
                    budget.check()
                    relativity_anchor_error_m_s2 = _schwarzschild_anchor_error_bound_m_s2(
                        bodies.get("Sun").gravity_field_model.gravitational_parameter,
                        states["Sun"], state, components_m_s2[9],
                    )
                    # The existing force gate is at least 1e-15 m/s^2; require its floor.
                    assert relativity_anchor_error_m_s2 <= Fraction(1e-15)
                    reported_relativity_error_m_s2 = math.nextafter(float(relativity_anchor_error_m_s2), math.inf)
                    assert math.isfinite(reported_relativity_error_m_s2)
                    assert Fraction(reported_relativity_error_m_s2) >= relativity_anchor_error_m_s2
                    relative_speed_bound_m_s = sum((abs(Fraction(ship) - Fraction(sun)) for ship, sun in
                                                   zip(state[3:], states["Sun"][3:], strict=True)), Fraction(sun_velocity_error_m_s))
                    conditional_relativity_error_m_s2 = relativity_anchor_error_m_s2 + _schwarzschild_state_variation_bound_m_s2(
                        bodies.get("Sun").gravity_field_model.gravitational_parameter, source_error_floors_m["Sun"],
                        relative_speed_bound_m_s, Fraction(source_position_errors_m["Sun"]), Fraction(sun_velocity_error_m_s),
                    )
                    reported_conditional_relativity_error_m_s2 = math.nextafter(float(conditional_relativity_error_m_s2), math.inf)
                    assert math.isfinite(reported_conditional_relativity_error_m_s2)
                    assert Fraction(reported_conditional_relativity_error_m_s2) >= conditional_relativity_error_m_s2
                    # Disjoint n=0 / n=2 / remainder partition, both assembly levels,
                    # and the SRP/relativistic components: each is counted once.
                    full_anchor_error_m_s2 = sum((Fraction(error) for bounds in (
                        conditional_point_spk_error_upper_m_s2, conditional_degree_two_spk_pck_error_upper_m_s2,
                        conditional_remainder_error_upper_m_s2, harmonic_sum_residual_upper_m_s2,
                    ) for error in bounds.values()), conditional_srp_error_m_s2 + conditional_relativity_error_m_s2)
                    full_anchor_error_m_s2 += sum(map(abs, sum_residual), Fraction(0))
                    reported_full_anchor_error_m_s2 = math.nextafter(float(full_anchor_error_m_s2), math.inf)
                    assert math.isfinite(reported_full_anchor_error_m_s2) and Fraction(reported_full_anchor_error_m_s2) >= full_anchor_error_m_s2
                    # Preserve the old envelope as a regression; replace only its
                    # remainder partition in the new, conditional prefix bound.
                    prefix_full_error_m_s2 = full_anchor_error_m_s2
                    reported_additional_prefix_errors_m_s2: dict[str, float] = {}
                    for source, prefix_error_m_s2 in conditional_additional_prefix_errors_m_s2.items():
                        prefix_full_error_m_s2 -= Fraction(conditional_remainder_error_upper_m_s2[source])
                        prefix_full_error_m_s2 += prefix_error_m_s2 + Fraction(
                            diagnostic_tail_profiles_m_s2[source][str(prefix_degrees[source])],
                        )
                        reported_prefix_error_m_s2 = math.nextafter(float(prefix_error_m_s2), math.inf)
                        assert math.isfinite(reported_prefix_error_m_s2) and Fraction(reported_prefix_error_m_s2) >= prefix_error_m_s2
                        reported_additional_prefix_errors_m_s2[source] = reported_prefix_error_m_s2
                    reported_prefix_full_error_m_s2 = math.nextafter(float(prefix_full_error_m_s2), math.inf)
                    assert math.isfinite(reported_prefix_full_error_m_s2)
                    assert 0 < prefix_full_error_m_s2 <= Fraction(reported_prefix_full_error_m_s2) < full_anchor_error_m_s2
                    budget.check()
                    if first_acceleration_m_s2 is None:
                        first_acceleration_m_s2 = anchor_m_s2.copy()
                    else:
                        assert np.array_equal(anchor_m_s2, first_acceleration_m_s2)
                    final_state = np.asarray(history[last_epoch]).reshape(7)
                    assert np.all(np.isfinite(final_state)) and final_state[6] == spacecraft.initial_mass_kg
                    curvature_m = Fraction(acceleration_m_s2) * Fraction(duration_s)**2 / 2
                    error_bound_m = _ballistic_endpoint_error_bound_m(state, final_state[:3], duration_s, acceleration_m_s2)
                    assert (error_bound_m <= Fraction("0.001")) is short_control, (center, tighter, float(error_bound_m))
                    reported_error_m = math.nextafter(float(error_bound_m), math.inf)
                    assert Fraction(reported_error_m) >= error_bound_m
                    velocity_error_m_s = _coast_endpoint_velocity_error_bound_m_s(
                        state[3:], final_state[3:6], duration_s, acceleration_m_s2,
                    )
                    assert velocity_error_m_s >= velocity_reach_m_s > Fraction("0.000001")
                    reported_velocity_error_m_s = math.nextafter(float(velocity_error_m_s), math.inf)
                    assert Fraction(reported_velocity_error_m_s) >= velocity_error_m_s
                    anchored_velocity_error_m_s = _anchored_coast_velocity_error_bound_m_s(
                        state[3:], final_state[3:6], anchor_m_s2, duration_s,
                        prefix_full_error_m_s2, force_variation_m_s2,
                    )
                    assert Fraction("0.000001") < anchored_velocity_error_m_s < velocity_error_m_s
                    reported_anchored_velocity_m_s = math.nextafter(float(anchored_velocity_error_m_s), math.inf)
                    assert math.isfinite(reported_anchored_velocity_m_s)
                    assert Fraction(reported_anchored_velocity_m_s) >= anchored_velocity_error_m_s
                    assert reported_relative_variation_m_s2 is not None
                    relative_velocity_error_m_s = _anchored_coast_velocity_error_bound_m_s(
                        state[3:], final_state[3:6], anchor_m_s2, duration_s,
                        prefix_full_error_m_s2, Fraction(reported_relative_variation_m_s2),
                    )
                    assert 0 < relative_velocity_error_m_s < anchored_velocity_error_m_s
                    reported_relative_velocity_m_s = math.nextafter(float(relative_velocity_error_m_s), math.inf)
                    assert math.isfinite(reported_relative_velocity_m_s) and Fraction(reported_relative_velocity_m_s) >= relative_velocity_error_m_s
                    assert reported_split_relative_variation_m_s2 is not None
                    split_velocity_error_m_s = _anchored_coast_velocity_error_bound_m_s(
                        state[3:], final_state[3:6], anchor_m_s2, duration_s,
                        prefix_full_error_m_s2, Fraction(reported_split_relative_variation_m_s2),
                    )
                    assert 0 < split_velocity_error_m_s < relative_velocity_error_m_s
                    assert (split_velocity_error_m_s <= Fraction("0.000001")) is short_control
                    anchored_position_error_m = _anchored_coast_position_error_bound_m(
                        state, final_state[:3], anchor_m_s2, duration_s,
                        prefix_full_error_m_s2, Fraction(reported_split_relative_variation_m_s2),
                    )
                    assert 0 < anchored_position_error_m < error_bound_m
                    assert anchored_position_error_m <= Fraction("0.001")
                    reported_anchored_position_m = math.nextafter(float(anchored_position_error_m), math.inf)
                    assert math.isfinite(reported_anchored_position_m)
                    assert Fraction(reported_anchored_position_m) >= anchored_position_error_m
                    reported_split_velocity_m_s = math.nextafter(float(split_velocity_error_m_s), math.inf)
                    assert math.isfinite(reported_split_velocity_m_s) and Fraction(reported_split_velocity_m_s) >= split_velocity_error_m_s
                    anchor_residual_m_s = _anchored_coast_velocity_error_bound_m_s(
                        state[3:], final_state[3:6], anchor_m_s2, duration_s, Fraction(0), Fraction(0),
                    )
                    reported_anchor_residual_m_s = math.nextafter(float(anchor_residual_m_s), math.inf)
                    assert math.isfinite(reported_anchor_residual_m_s) and Fraction(reported_anchor_residual_m_s) >= anchor_residual_m_s
                    # q(t)=x0+v0*t+a_hat*t^2/2, q'=v0+a_hat*t exactly.
                    # The same acceleration/reach bounds contain q and its velocity;
                    # hence the existing relative-motion force variation also covers q.
                    assert closed and reach_m < position_radius_m
                    assert velocity_reach_m_s < Fraction(velocity_radius_m_s)
                    assert sum((Fraction(value)**2 for value in anchor_m_s2), Fraction(0)) <= Fraction(acceleration_m_s2)**2
                    reference_defect_m_s2 = prefix_full_error_m_s2 + Fraction(reported_split_relative_variation_m_s2)
                    reference_position_error_m, reference_velocity_error_m_s = _coast_error_envelope(
                        duration_s, Fraction(0), Fraction(0), Fraction(reported_full_position_sensitivity),
                        Fraction(reported_relativity_sensitivities[1]), reference_defect_m_s2,
                    )
                    reference_position_residual_m = _anchored_coast_position_error_bound_m(
                        state, final_state[:3], anchor_m_s2, duration_s, Fraction(0), Fraction(0),
                    )
                    transported_position_error_m = reference_position_residual_m + reference_position_error_m
                    transported_velocity_error_m_s = anchor_residual_m_s + reference_velocity_error_m_s
                    assert anchored_position_error_m < transported_position_error_m <= Fraction("0.001")
                    assert split_velocity_error_m_s < transported_velocity_error_m_s
                    assert (transported_velocity_error_m_s <= Fraction("0.000001")) is short_control
                    # Relative reaches are a*t+b*t^2, a,b>=0, hence <=t/h times
                    # their endpoint bounds. Rotation uses the verified linear branch.
                    gravity_variation_m_s2 = sum((Fraction(value) for partition in (
                        relative_point_m_s2, split_relative_harmonic_m_s2,
                        angle_limited_rotation_variation_m_s2,
                    ) for value in partition.values()), Fraction(0))
                    defect_rate_m_s3 = gravity_variation_m_s2 / Fraction(duration_s)
                    constant_defect_m_s2 = prefix_full_error_m_s2 + 2 * (Fraction(srp) + Fraction(relativity))
                    assert constant_defect_m_s2 + defect_rate_m_s3 * Fraction(duration_s) <= reference_defect_m_s2
                    weighted_reference_position_error_m, weighted_reference_velocity_error_m_s = _coast_error_envelope(
                        duration_s, Fraction(0), Fraction(0), Fraction(reported_full_position_sensitivity),
                        Fraction(reported_relativity_sensitivities[1]), constant_defect_m_s2,
                        acceleration_defect_rate_m_s3=defect_rate_m_s3,
                    )
                    weighted_position_error_m = weighted_reference_position_error_m + reference_position_residual_m
                    weighted_velocity_error_m_s = weighted_reference_velocity_error_m_s + anchor_residual_m_s
                    # A fixed reference enclosure can exceed the gate before the
                    # nonnegative native-to-reference residual is even added.
                    assert (weighted_reference_velocity_error_m_s <= Fraction("0.000001")) is short_control
                    assert 0 < weighted_position_error_m < transported_position_error_m <= Fraction("0.001")
                    assert 0 < weighted_velocity_error_m_s < transported_velocity_error_m_s
                    assert (weighted_velocity_error_m_s <= Fraction("0.000001")) is short_control
                    # Selected monopole jerk only; bound every other force's variation.
                    h = Fraction(duration_s)
                    reference_acceleration_m_s2 = (sum(map(abs, map(Fraction, anchor_m_s2)), Fraction(0))
                                                  + h * sum(map(abs, reference_jerk_m_s3), Fraction(0)))
                    assert reference_acceleration_m_s2 <= Fraction(acceleration_m_s2)
                    monopole_curvature_m_s4 = Fraction(0)
                    for source, (slope, source_curvature) in source_affine_motion.items():
                        budget.check()
                        relative_acceleration_m_s2 = Fraction(acceleration_m_s2) + source_curvature
                        relative_speed_m_s = sum((abs(Fraction(ship) - v) for ship, v in
                                                  zip(state[3:], slope, strict=True)), Fraction(0)) + relative_acceleration_m_s2*h
                        monopole_curvature_m_s4 += _point_mass_force_curvature_bound_m_s4(
                            bodies.get(source).gravity_field_model.gravitational_parameter, floors_m[source],
                            relative_speed_m_s, relative_acceleration_m_s2,
                        )
                    remaining_variation_rate_m_s3 = sum(map(Fraction, angle_limited_rotation_variation_m_s2.values()), Fraction(0)) / h
                    for source in ("Moon", "Mars"):
                        monopole_jacobian = 2 * Fraction(bodies.get(source).gravity_field_model.gravitational_parameter) / Fraction(floors_m[source])**3
                        nonmonopole_jacobian = split_harmonic_jacobians_s_inv2[source] - monopole_jacobian
                        assert nonmonopole_jacobian >= 0
                        remaining_variation_rate_m_s3 += nonmonopole_jacobian * Fraction(relative_reaches_m[source]) / h
                    cubic_defect_rate_m_s3 = reference_jerk_error_m_s3 + remaining_variation_rate_m_s3 + monopole_curvature_m_s4*h/2
                    cubic_reference_position_m, cubic_reference_velocity_m_s = _coast_error_envelope(
                        duration_s, Fraction(0), Fraction(0), Fraction(reported_full_position_sensitivity),
                        Fraction(reported_relativity_sensitivities[1]), constant_defect_m_s2,
                        acceleration_defect_rate_m_s3=cubic_defect_rate_m_s3,
                    )
                    cubic_endpoint = _cubic_reference_endpoint(
                        tuple(map(Fraction, state)), tuple(map(Fraction, anchor_m_s2)), reference_jerk_m_s3, duration_s,
                    )
                    cubic_position_residual_m = sum((abs(Fraction(native) - reference) for native, reference in
                                                    zip(final_state[:3], cubic_endpoint[:3], strict=True)), Fraction(0))
                    cubic_velocity_residual_m_s = sum((abs(Fraction(native) - reference) for native, reference in
                                                      zip(final_state[3:6], cubic_endpoint[3:], strict=True)), Fraction(0))
                    cubic_position_error_m = cubic_reference_position_m + cubic_position_residual_m
                    cubic_velocity_error_m_s = cubic_reference_velocity_m_s + cubic_velocity_residual_m_s
                    assert cubic_reference_position_m < weighted_reference_position_error_m
                    assert cubic_reference_velocity_m_s < weighted_reference_velocity_error_m_s
                    assert cubic_position_error_m <= Fraction("0.001")
                    assert cubic_velocity_error_m_s < weighted_velocity_error_m_s
                    # At 1/8 s this fixed reference bound alone exceeds the
                    # gate; reducing only its endpoint residual cannot resolve it.
                    assert (cubic_reference_velocity_m_s <= Fraction("0.000001")) is (duration_s < 1 / 8)
                    assert (cubic_velocity_error_m_s <= Fraction("0.000001")) is (duration_s < 1 / 8)
                    cubic_values = {
                        "reference_acceleration_upper_m_s2": reference_acceleration_m_s2,
                        "monopole_jerk_error_m_s3": reference_jerk_error_m_s3,
                        "monopole_force_curvature_m_s4": monopole_curvature_m_s4,
                        "remaining_variation_rate_m_s3": remaining_variation_rate_m_s3,
                        "reference_defect_rate_m_s3": cubic_defect_rate_m_s3,
                        "reference_position_error_m": cubic_reference_position_m,
                        "reference_velocity_error_m_s": cubic_reference_velocity_m_s,
                        "endpoint_position_residual_m": cubic_position_residual_m,
                        "endpoint_velocity_residual_m_s": cubic_velocity_residual_m_s,
                        "endpoint_position_error_m": cubic_position_error_m,
                        "endpoint_velocity_error_m_s": cubic_velocity_error_m_s,
                    }
                    reported_cubic = {key: math.nextafter(float(value), math.inf) if value else 0.0 for key, value in cubic_values.items()}
                    assert all(math.isfinite(value) and Fraction(value) >= cubic_values[key] >= 0 for key, value in reported_cubic.items())
                    transport_bounds = {
                        "conditional_weighted_reference_position_error_m": weighted_reference_position_error_m,
                        "conditional_weighted_reference_velocity_error_m_s": weighted_reference_velocity_error_m_s,
                        "conditional_reference_endpoint_position_residual_m": reference_position_residual_m,
                        "conditional_linear_reference_defect_constant_m_s2": constant_defect_m_s2,
                        "conditional_linear_reference_defect_rate_m_s3": defect_rate_m_s3,
                        "conditional_weighted_endpoint_position_error_m": weighted_position_error_m,
                        "conditional_weighted_endpoint_velocity_error_m_s": weighted_velocity_error_m_s,
                        "conditional_quadratic_reference_defect_m_s2": reference_defect_m_s2,
                        "conditional_quadratic_reference_position_error_m": reference_position_error_m,
                        "conditional_quadratic_reference_velocity_error_m_s": reference_velocity_error_m_s,
                        "conditional_transport_endpoint_position_error_m": transported_position_error_m,
                        "conditional_transport_endpoint_velocity_error_m_s": transported_velocity_error_m_s,
                    }
                    reported_transport_bounds = {key: math.nextafter(float(value), math.inf)
                                                 for key, value in transport_bounds.items()}
                    assert all(math.isfinite(value) and Fraction(value) >= transport_bounds[key] > 0
                               for key, value in reported_transport_bounds.items())
                    initial_ball_controls: list[dict[str, object]] = []
                    for initial_velocity_radius_m_s in ((0.0, 5e-8, 1e-7) if short_control else ()):
                        budget.check()
                        initial_position_radius_m = 0.0001  # Explicit fixture, not a mission default/allocation.
                        p, v, h = Fraction(initial_position_radius_m), Fraction(initial_velocity_radius_m_s), Fraction(duration_s)
                        # First-exit closure around nominal x0/v0, for the whole
                        # initial-state family. The reference and its defect stay fixed.
                        family_position_reach_m = p + (initial_speed_m_s + v) * h + Fraction(acceleration_m_s2) * h**2 / 2
                        family_velocity_reach_m_s = v + Fraction(acceleration_m_s2) * h
                        assert family_position_reach_m < Fraction(position_radius_m)
                        assert family_velocity_reach_m_s < Fraction(velocity_radius_m_s)
                        family_position_error_m, family_velocity_error_m_s = _coast_error_envelope(
                            duration_s, p, v, Fraction(reported_full_position_sensitivity),
                            Fraction(reported_relativity_sensitivities[1]), reference_defect_m_s2,
                        )
                        family_position_error_m += reference_position_residual_m
                        family_velocity_error_m_s += anchor_residual_m_s
                        assert transported_position_error_m < family_position_error_m <= Fraction("0.001")
                        assert transported_velocity_error_m_s < family_velocity_error_m_s
                        family_values = {
                            "position_reach_m": family_position_reach_m,
                            "velocity_reach_m_s": family_velocity_reach_m_s,
                            "endpoint_position_error_m": family_position_error_m,
                            "endpoint_velocity_error_m_s": family_velocity_error_m_s,
                        }
                        reported_family = {key: math.nextafter(float(value), math.inf) for key, value in family_values.items()}
                        assert all(math.isfinite(value) and Fraction(value) >= family_values[key] > 0
                                   for key, value in reported_family.items())
                        resolves_velocity = family_velocity_error_m_s <= Fraction("0.000001")
                        assert resolves_velocity == (center != "Moon" or initial_velocity_radius_m_s < 1e-7)
                        initial_ball_controls.append({
                            "initial_position_radius_m": initial_position_radius_m,
                            "initial_velocity_radius_m_s": initial_velocity_radius_m_s,
                            "conditional_domain_closed": True,
                            "within_position_gate": family_position_error_m <= Fraction("0.001"),
                            "within_velocity_gate": resolves_velocity,
                            **reported_family,
                        })
                    control_elapsed_s = perf_counter() - control_started_s
                    assert math.isfinite(control_elapsed_s) and control_elapsed_s >= native_elapsed_s
                    budget.check()
                    endpoint_controls.append({"tighter": tighter,
                        **reported_transport_bounds,
                        "conditional_partial_cubic_control": {
                            **reported_cubic,
                            "reference_within_velocity_gate": cubic_reference_velocity_m_s <= Fraction("0.000001"),
                            "within_position_gate": cubic_position_error_m <= Fraction("0.001"),
                            "within_velocity_gate": cubic_velocity_error_m_s <= Fraction("0.000001"),
                        },
                        "weighted_position_bound_resolves_1mm": weighted_position_error_m <= Fraction("0.001"),
                        "reference_only_velocity_bound_resolves_1um_s": weighted_reference_velocity_error_m_s <= Fraction("0.000001"),
                        "weighted_velocity_bound_resolves_1um_s": weighted_velocity_error_m_s <= Fraction("0.000001"),
                        "conditional_initial_state_ball_controls": initial_ball_controls,
                        "native_arc_elapsed_s": native_elapsed_s,
                        "control_verification_elapsed_s": control_elapsed_s,
                        "observed_initial_acceleration_m_s2": anchor_m_s2.tolist(),
                        "initial_shadow_function": shadow,
                        "fully_lit_srp_anchor_error_upper_m_s2": reported_srp_error_m_s2,
                        "conditional_fully_lit_srp_spk_anchor_l2_error_upper_m_s2": reported_conditional_srp_error_m_s2,
                        "conditional_apparent_discs_clear_for_position_balls": conditional_clear_by_body,
                        "initial_apparent_discs_strictly_disjoint": clear_by_body,
                        "point_anchor_error_upper_m_s2": point_anchor_error_upper_m_s2,
                        "harmonic_monopole_anchor_error_upper_m_s2": harmonic_monopole_error_upper_m_s2,
                        "c20_stored_matrix_anchor_error_upper_m_s2": c20_error_upper_m_s2,
                        "degree_two_stored_matrix_anchor_error_upper_m_s2": degree_two_error_upper_m_s2,
                        "pck_anchor_matrix_entry_l1_error_upper": pck_matrix_error_upper,
                        "degree_two_ideal_pck_anchor_l2_error_upper_m_s2": degree_two_ideal_pck_error_upper_m_s2,
                        "conditional_source_position_error_upper_m": source_position_errors_m,
                        "conditional_point_spk_anchor_l2_error_upper_m_s2": conditional_point_spk_error_upper_m_s2,
                        "conditional_degree_two_spk_pck_anchor_l2_error_upper_m_s2": conditional_degree_two_spk_pck_error_upper_m_s2,
                        "observed_harmonic_sum_residual_l1_upper_m_s2": harmonic_sum_residual_upper_m_s2,
                        "observed_harmonic_term_counts": {source: len(indices) for source, indices in harmonic_indices.items()},
                        "schwarzschild_anchor_error_upper_m_s2": reported_relativity_error_m_s2,
                        "conditional_sun_velocity_error_upper_m_s": sun_velocity_error_m_s,
                        "conditional_schwarzschild_spk_anchor_l2_error_upper_m_s2": reported_conditional_relativity_error_m_s2,
                        "conditional_harmonic_remainder_anchor_l2_error_upper_m_s2": conditional_remainder_error_upper_m_s2,
                        "conditional_full_force_anchor_l2_error_upper_m_s2": reported_full_anchor_error_m_s2,
                        "diagnostic_unqualified_prefix_tail_error_upper_m_s2": diagnostic_tail_profiles_m_s2,
                        "generic_degree_three_stored_matrix_term_l1_error_upper_m_s2": generic_degree_three_errors_m_s2,
                        "qualified_prefix_degrees": prefix_degrees,
                        "generic_prefix_evaluation_seconds": generic_prefix_elapsed_s,
                        "conditional_additional_prefix_anchor_l2_error_upper_m_s2": reported_additional_prefix_errors_m_s2,
                        "conditional_prefix_full_force_anchor_l2_error_upper_m_s2": reported_prefix_full_error_m_s2,
                        "observed_acceleration_sum_residual_l1_m_s2": float(sum(map(abs, sum_residual), Fraction(0))),
                        "conditional_endpoint_position_error_m": reported_error_m,
                        "conditional_anchored_endpoint_position_error_m": reported_anchored_position_m,
                        "conditional_endpoint_velocity_error_m_s": reported_velocity_error_m_s,
                        "conditional_anchored_endpoint_velocity_error_m_s": reported_anchored_velocity_m_s,
                        "conditional_relative_endpoint_velocity_error_m_s": reported_relative_velocity_m_s,
                        "conditional_split_endpoint_velocity_error_m_s": reported_split_velocity_m_s,
                        "split_velocity_bound_resolves_1um_s": split_velocity_error_m_s <= Fraction("0.000001"),
                        "relative_velocity_bound_resolves_1um_s": relative_velocity_error_m_s <= Fraction("0.000001"),
                        "anchor_velocity_residual_l1_m_s": reported_anchor_residual_m_s,
                        "anchored_velocity_bound_resolves_1um_s": anchored_velocity_error_m_s <= Fraction("0.000001"),
                        "velocity_bound_resolves_1um_s": velocity_error_m_s <= Fraction("0.000001"),
                        "ballistic_residual_l1_m": float(error_bound_m - curvature_m)})
            results.append({"center": center, "duration_s": duration_s,
                "position_domain_radius_m": position_radius_m,
                "velocity_domain_radius_m_s": velocity_radius_m_s,
                "conditional_point_mass_initial_jerk_intervals_m_s3": point_jerk_intervals_m_s3,
                "conditional_harmonic_monopole_initial_jerk_intervals_m_s3": harmonic_monopole_jerks_m_s3,
                "conditional_domain_fully_lit_by_occultor": domain_clear_by_body,
                "conditional_position_sensitivities_by_force_s_inv2": reported_position_sensitivities,
                "conditional_full_force_position_sensitivity_s_inv2": reported_full_position_sensitivity,
                "conditional_full_force_velocity_sensitivity_s_inv": reported_relativity_sensitivities[1],
                "conditional_error_transport_feedback_upper": reported_feedback,
                "conditional_schwarzschild_position_sensitivity_s_inv2": reported_relativity_sensitivities[0],
                "conditional_schwarzschild_velocity_sensitivity_s_inv": reported_relativity_sensitivities[1],
                "conditional_pck_rotation_path_rad": {
                    body: math.nextafter(float(rate * Fraction(duration_s)), math.inf)
                    for body, rate in rotation_rates_rad_s.items()},
                "acceleration_bound_m_s2": acceleration_m_s2, "position_reach_m": reach_m,
                "conditional_point_mass_variation_m_s2": point_mass_variation_m_s2,
                "conditional_frozen_harmonic_variation_m_s2": frozen_harmonic_variation_m_s2,
                "conditional_arbitrary_rotation_variation_m_s2": arbitrary_rotation_variation_m_s2,
                "conditional_angle_limited_rotation_variation_m_s2": angle_limited_rotation_variation_m_s2,
                "conditional_total_coast_force_variation_m_s2": reported_force_variation_m_s2,
                "conditional_relative_displacement_upper_m": relative_reaches_m or None,
                "conditional_relative_force_variation_m_s2": reported_relative_variation_m_s2,
                "conditional_split_relative_force_variation_m_s2": reported_split_relative_variation_m_s2,
                "velocity_reach_upper_m_s": math.nextafter(float(velocity_reach_m_s), math.inf),
                "conditional_domain_closed": closed, "endpoint_controls": endpoint_controls})
    expected_arcs = 7 if run_native_controls else 0
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (expected_arcs,) * 3
    return results


def test_direct_and_tabulated_ephemeris_lookup_cost() -> None:
    """Measure warm Python-boundary lookup cost, not full-force propagation."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    epochs_tdb_s = evidence["epoch_tdb_s"]
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    spice = ephemeris._ensure_standard_kernels()
    started_s = perf_counter()
    settings = trajectory._create_time_limited_body_settings(
        environment_setup, epochs_tdb_s[0], epochs_tdb_s[-1],
    )
    settings_elapsed_s = perf_counter() - started_s
    repeats, batches = 100, 6
    observations: list[dict[str, object]] = []
    for body in trajectory.PHYSICAL_BODY_NAMES:
        budget.check()
        started_s = perf_counter()
        table = environment_setup.create_body_ephemeris(
            settings.get(body).ephemeris_settings, body,
        )
        table_setup_s = perf_counter() - started_s
        started_s = perf_counter()
        direct = environment_setup.create_body_ephemeris(
            environment_setup.ephemeris.direct_spice("SSB", "J2000", body), body,
        )
        direct_setup_s = perf_counter() - started_s
        # Validate and warm both paths outside the timed loops.
        for model in (table, direct):
            assert (model.frame_origin, model.frame_orientation) == ("SSB", "J2000")
            for epoch_tdb_s in epochs_tdb_s:
                state_si = model.cartesian_state(epoch_tdb_s)
                reference_si = spice.get_body_cartesian_state_at_epoch(
                    body, "SSB", "J2000", "NONE", epoch_tdb_s,
                )
                assert np.all(np.isfinite(state_si))
                difference_si = state_si - reference_si
                position_limit_m = 0.001 if model is direct else 0.025
                velocity_limit_m_s = 0.000001 if model is direct else 0.0000025
                assert np.linalg.norm(difference_si[:3]) <= position_limit_m
                assert np.linalg.norm(difference_si[3:]) <= velocity_limit_m_s
        elapsed_s: dict[str, list[float]] = {"table": [], "direct": []}
        paths = (("table", table), ("direct", direct))
        for batch in range(batches):
            for name, model in paths if batch % 2 == 0 else paths[::-1]:
                budget.check()
                query = model.cartesian_state
                started_s = perf_counter()
                for _ in range(repeats):
                    for epoch_tdb_s in epochs_tdb_s:
                        query(epoch_tdb_s)
                duration_s = perf_counter() - started_s
                assert math.isfinite(duration_s) and duration_s > 0
                elapsed_s[name].append(duration_s)
                budget.check()
        observations.append({
            "body": body, "table_setup_s": table_setup_s,
            "direct_setup_s": direct_setup_s, "batch_elapsed_s": elapsed_s,
            "median_query_s": {
                name: median(values) / (repeats * len(epochs_tdb_s))
                for name, values in elapsed_s.items()
            },
        })
    budget.check()
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "platform": platform.platform(),
        "python": platform.python_version(), "settings_elapsed_s": settings_elapsed_s,
        "epoch_count": len(epochs_tdb_s), "batches_per_path": batches,
        "queries_per_batch": repeats * len(epochs_tdb_s),
        "time": "TDB seconds since J2000", "frame": "SSB/J2000",
        "state_units": ["m", "m/s"], "observations": observations,
        "scope": "Warm Python-boundary lookup timings; no speed gate or mission estimate",
    }, sort_keys=True, allow_nan=False))


@pytest.fixture
def cspice() -> ctypes.CDLL:
    """Use the installed Darwin ABI and Tudat-loaded pool without changing it."""
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        pytest.skip("Only the installed Darwin/arm64 CSPICE ABI was inspected")
    ephemeris._ensure_standard_kernels()
    native = ctypes.CDLL(str(Path(sys.prefix) / "lib/libcspice.dylib"))
    integer, double, pointer = ctypes.c_int, ctypes.c_double, ctypes.POINTER
    assert ctypes.sizeof(integer) == 4 and ctypes.sizeof(double) == 8
    native.spksfs_c.argtypes = [
        integer, double, integer, pointer(integer), pointer(double),
        pointer(ctypes.c_char), pointer(integer),
    ]
    native.spksfs_c.restype = None
    native.spkuds_c.argtypes = [
        pointer(double), *([pointer(integer)] * 4),
        pointer(double), pointer(double), pointer(integer), pointer(integer),
    ]
    native.spkuds_c.restype = None
    native.spkssb_c.argtypes = [integer, double, ctypes.c_char_p, pointer(double)]
    native.spkssb_c.restype = None
    native.spkpvn_c.argtypes = [
        integer, pointer(double), double, pointer(integer), pointer(double), pointer(integer),
    ]
    native.spkpvn_c.restype = None
    # Pinned f2c ABI: by-reference handle/descriptor/epoch and caller-owned record.
    for reader in (native.spkr02_, native.spkr03_):
        reader.argtypes = [pointer(integer), pointer(double), pointer(double), pointer(double)]
        reader.restype = None
    for evaluator in (native.spke02_, native.spke03_):
        evaluator.argtypes = [pointer(double), pointer(double), pointer(double)]
        evaluator.restype = None
    native.dafbfs_c.argtypes = [integer]
    native.dafbfs_c.restype = None
    native.daffna_c.argtypes = [pointer(integer)]
    native.daffna_c.restype = None
    native.dafgs_c.argtypes = [pointer(double)]
    native.dafgs_c.restype = None
    native.dafgda_c.argtypes = [integer, integer, integer, pointer(double)]
    native.dafgda_c.restype = None
    native.failed_c.argtypes = []
    native.failed_c.restype = integer
    assert native.failed_c() == 0
    return native


@pytest.mark.parametrize("body,target_id,expected_chain", [
    ("Sun", 10, [(10, 0, 2)]),
    ("Mercury", 1, [(1, 0, 2)]),
    ("Venus", 2, [(2, 0, 2)]),
    ("Earth", 399, [(399, 0, 2)]),
    ("Moon", 301, [(301, 399, 2), (399, 0, 2)]),
    ("Mars", 499, [(499, 4, 3), (4, 0, 2)]),
    ("Jupiter", 599, [(599, 5, 3), (5, 0, 2)]),
    ("Saturn", 699, [(699, 6, 3), (6, 0, 2)]),
])
def test_sampled_spk_chains_match_tudat_states(
    cspice: ctypes.CDLL, body: str, target_id: int,
    expected_chain: list[tuple[int, int, int]],
) -> None:
    """Qualify IDs and segment types at the existing 38 TDB epochs in SSB/J2000."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    spice = ephemeris._ensure_standard_kernels()
    direct_native = environment_setup.create_body_ephemeris(
        environment_setup.ephemeris.direct_spice("SSB", "J2000", body), body,
    )
    assert (direct_native.frame_origin, direct_native.frame_orientation) == ("SSB", "J2000")
    direct_errors_si: list[tuple[float, float]] = []
    accumulation_errors_si: list[tuple[float, float]] = []
    accumulation_bounds_si: list[tuple[float, float]] = []
    reordered_conversion_failures = 0
    u, eta = Fraction(1, 2 ** 53), Fraction(1, 2 ** 1075)
    assert 1 <= len(expected_chain) <= 2
    observations: set[tuple[int, int, int, float, float, str]] = set()
    for epoch_tdb_s in evidence["epoch_tdb_s"]:
        budget.check()
        current_id = target_id
        link_states: list[tuple[float, ...]] = []
        for expected_body, expected_center, expected_type in expected_chain:
            assert current_id == expected_body
            handle, found = ctypes.c_int(), ctypes.c_int()
            descriptor = (ctypes.c_double * 5)()
            identifier = ctypes.create_string_buffer(41)
            cspice.spksfs_c(current_id, epoch_tdb_s, 41, ctypes.byref(handle),
                            descriptor, identifier, ctypes.byref(found))
            assert cspice.failed_c() == 0 and found.value == 1, (body, epoch_tdb_s)
            integers = [ctypes.c_int() for _ in range(6)]
            first, last = ctypes.c_double(), ctypes.c_double()
            cspice.spkuds_c(
                descriptor, *[ctypes.byref(value) for value in integers[:4]],
                ctypes.byref(first), ctypes.byref(last),
                *[ctypes.byref(value) for value in integers[4:]],
            )
            assert cspice.failed_c() == 0
            segment_body, center, frame, kind, begin, end = [value.value for value in integers]
            assert (segment_body, center, frame, kind) == (
                expected_body, expected_center, 1, expected_type,
            )
            assert first.value <= epoch_tdb_s <= last.value and 0 < begin <= end
            observations.add((segment_body, center, kind, first.value, last.value,
                              identifier.value.decode("ascii")))
            link_frame, link_center = ctypes.c_int(), ctypes.c_int()
            link_state = (ctypes.c_double * 6)()
            cspice.spkpvn_c(handle, descriptor, epoch_tdb_s, ctypes.byref(link_frame),
                           link_state, ctypes.byref(link_center))
            assert cspice.failed_c() == 0
            assert (link_frame.value, link_center.value) == (1, expected_center)
            assert all(math.isfinite(value) for value in link_state)
            link_states.append(tuple(link_state))  # J2000, target relative to center, km and km/s.
            current_id = center
        assert current_id == 0
        raw_state_km = (ctypes.c_double * 6)()
        cspice.spkssb_c(target_id, epoch_tdb_s, b"J2000", raw_state_km)
        assert cspice.failed_c() == 0
        replay_km = tuple(link_states[0][axis] + link_states[1][axis]
                          if len(link_states) == 2 else link_states[0][axis] for axis in range(6))
        assert bytes(raw_state_km) == bytes((ctypes.c_double * 6)(*replay_km)), (body, epoch_tdb_s)
        native_state_si = np.asarray(raw_state_km) * 1000.0
        tudat_state_si = spice.get_body_cartesian_state_at_epoch(
            body, "SSB", "J2000", "NONE", epoch_tdb_s,
        )
        difference_si = native_state_si - tudat_state_si
        assert np.all(np.isfinite(difference_si))
        assert np.linalg.norm(difference_si[:3]) <= 0.001  # m
        assert np.linalg.norm(difference_si[3:]) <= 0.000001  # m/s
        direct_state_si = np.asarray(direct_native.cartesian_state(epoch_tdb_s)).reshape(6)
        assert native_state_si.tobytes() == np.asarray(tudat_state_si).reshape(6).tobytes()
        assert native_state_si.tobytes() == direct_state_si.tobytes()
        errors_si: list[Fraction] = []
        bounds_si: list[Fraction] = []
        for axis in range(6):
            exact_sum_km = sum((Fraction(link[axis]) for link in link_states), Fraction(0))
            sum_bound_km = u * abs(exact_sum_km) + eta if len(link_states) == 2 else Fraction(0)
            assert abs(exact_sum_km) <= Fraction(sys.float_info.max)
            assert abs(Fraction(raw_state_km[axis]) - exact_sum_km) <= sum_bound_km
            exact_conversion_si = 1000 * Fraction(raw_state_km[axis])
            assert abs(exact_conversion_si) <= Fraction(sys.float_info.max)
            conversion_bound_si = u * abs(exact_conversion_si) + eta
            assert abs(Fraction(native_state_si[axis]) - exact_conversion_si) <= conversion_bound_si
            errors_si.append(abs(Fraction(native_state_si[axis]) - 1000 * exact_sum_km))
            bounds_si.append(1000 * sum_bound_km + conversion_bound_si)
            assert errors_si[-1] <= bounds_si[-1]
        position_bound_m, velocity_bound_m_s = sum(bounds_si[:3]), sum(bounds_si[3:])
        assert position_bound_m <= Fraction("0.001") and velocity_bound_m_s <= Fraction("0.000001")
        accumulation_errors_si.append((float(sum(errors_si[:3])), float(sum(errors_si[3:]))))
        accumulation_bounds_si.append((math.nextafter(float(position_bound_m), math.inf),
                                       math.nextafter(float(velocity_bound_m_s), math.inf)))
        if len(link_states) == 2:
            # Scale-then-add is mathematically equivalent, but need not round identically.
            reordered_si = np.asarray(link_states[0]) * 1000.0 + np.asarray(link_states[1]) * 1000.0
            reordered_conversion_failures += reordered_si.tobytes() != native_state_si.tobytes()
        difference_si = direct_state_si - native_state_si
        assert np.all(np.isfinite(difference_si))
        error_m = float(np.linalg.norm(difference_si[:3]))
        error_m_s = float(np.linalg.norm(difference_si[3:]))
        assert error_m <= 0.001 and error_m_s <= 0.000001
        direct_errors_si.append((error_m, error_m_s))
        budget.check()
    assert budget.native_arc_propagations == 0
    assert reordered_conversion_failures > 0 if len(expected_chain) == 2 else reordered_conversion_failures == 0
    print(json.dumps({
        "body": body, "effective_spk_target_id": target_id,
        "epoch_count": len(evidence["epoch_tdb_s"]),
        "time": "TDB seconds since J2000", "frame": "SSB/J2000",
        "segments": sorted(observations),
        "experimental_direct_native_max_position_error_m": max(value[0] for value in direct_errors_si),
        "experimental_direct_native_max_velocity_error_m_s": max(value[1] for value in direct_errors_si),
        "chain_and_conversion_max_l1_error_m": max(value[0] for value in accumulation_errors_si),
        "chain_and_conversion_max_l1_error_m_s": max(value[1] for value in accumulation_errors_si),
        "chain_and_conversion_max_sampled_bound_m": max(value[0] for value in accumulation_bounds_si),
        "chain_and_conversion_max_sampled_bound_m_s": max(value[1] for value in accumulation_bounds_si),
        "scale_before_add_different_epoch_count": reordered_conversion_failures,
        "scope": "Sampled chain metadata, bit-exact arithmetic replay and local rounding bounds; excludes source-polynomial errors and uniform interval certification",
    }, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("step_s", [300.0, 150.0, 75.0])
def test_saturn_spk_segment_junction(cspice: ctypes.CDLL, step_s: float) -> None:
    """Reproduce a failed allocation, not a passing interpolation qualification."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    spice = ephemeris._ensure_standard_kernels()
    junction_tdb_s = 986817600.0
    epochs_tdb_s = [math.nextafter(junction_tdb_s, -math.inf), junction_tdb_s,
                    math.nextafter(junction_tdb_s, math.inf)]
    junction_states_si: list[np.ndarray] = []
    descriptors: list[bytes] = []
    for epoch_tdb_s in epochs_tdb_s:
        budget.check()
        handle, found = ctypes.c_int(), ctypes.c_int()
        descriptor = (ctypes.c_double * 5)()
        identifier = ctypes.create_string_buffer(41)
        cspice.spksfs_c(699, epoch_tdb_s, 41, ctypes.byref(handle), descriptor,
                        identifier, ctypes.byref(found))
        assert cspice.failed_c() == 0 and found.value == 1
        descriptors.append(bytes(descriptor))
        # The first two descriptor doubles are coverage endpoints (SPK ND=2).
        assert descriptor[0] <= junction_tdb_s <= descriptor[1]
        frame, center = ctypes.c_int(), ctypes.c_int()
        state_km = (ctypes.c_double * 6)()
        cspice.spkpvn_c(handle, descriptor, junction_tdb_s, ctypes.byref(frame),
                        state_km, ctypes.byref(center))
        assert cspice.failed_c() == 0 and (frame.value, center.value) == (1, 6)
        state_si = np.asarray(state_km).copy() * 1000.0
        assert np.all(np.isfinite(state_si))
        junction_states_si.append(state_si)
    assert descriptors[0] != descriptors[2]
    assert descriptors[1] in (descriptors[0], descriptors[2])
    difference_si = junction_states_si[2] - junction_states_si[0]
    jump_m = float(np.linalg.norm(difference_si[:3]))
    jump_m_s = float(np.linalg.norm(difference_si[3:]))
    # Counterexample: one value cannot be within 0.025 m of both segment values.
    assert jump_m > 2 * 0.025

    start_s, end_s = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    if step_s == 300.0:
        settings = trajectory._create_time_limited_body_settings(environment_setup, start_s, end_s)
    else:
        settings = environment_setup.get_default_body_settings_time_limited(
            trajectory.PHYSICAL_BODY_NAMES, start_s, end_s, "SSB", "J2000", step_s,
        )
    assert settings.get("Saturn").ephemeris_settings.time_step == step_s
    budget.check()
    native = environment_setup.create_body_ephemeris(settings.get("Saturn").ephemeris_settings,
                                                    "Saturn")
    safe_start_s, safe_end_s = environment_setup.get_safe_interpolation_interval(native)
    assert safe_start_s <= start_s < end_s <= safe_end_s
    assert (native.frame_origin, native.frame_orientation) == ("SSB", "J2000")
    budget.check()
    errors_si: list[tuple[float, float]] = []
    for epoch_tdb_s in epochs_tdb_s:
        direct_si = spice.get_body_cartesian_state_at_epoch(
            "Saturn", "SSB", "J2000", "NONE", epoch_tdb_s,
        )
        difference_si = native.cartesian_state(epoch_tdb_s) - direct_si
        assert np.all(np.isfinite(difference_si))
        error_m = float(np.linalg.norm(difference_si[:3]))
        error_m_s = float(np.linalg.norm(difference_si[3:]))
        errors_si.append((error_m, error_m_s))
        budget.check()
    assert max(value[0] for value in errors_si) > 0.025
    assert max(value[1] for value in errors_si) > 2.5e-6
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "junction_tdb_s": junction_tdb_s, "time": "TDB seconds since J2000",
        "table_step_s": step_s,
        "segment_state_frame": "Saturn barycenter/J2000", "units": ["m", "m/s"],
        "same_epoch_segment_difference": [jump_m, jump_m_s],
        "junction_selection_after_left_query": "left" if descriptors[1] == descriptors[0] else "right",
        "query_epochs_tdb_s": epochs_tdb_s, "interpolation_state_frame": "SSB/J2000",
        "interpolation_errors": errors_si,
        "qualification_status": "failed-existing-interpolation-allocation",
        "scope": "Regression of a counterexample, not a passing safety qualification",
    }, sort_keys=True, allow_nan=False))


def test_saturn_junction_query_order_is_repeatable(cspice: ctypes.CDLL) -> None:
    """Qualify all six local query orders without resetting the loaded kernel pool."""
    spice = ephemeris._ensure_standard_kernels()
    budget = trajectory._RefinementBudget("d0001-t0035", 300.0)
    junction_tdb_s = 986817600.0
    epochs_tdb_s = (math.nextafter(junction_tdb_s, -math.inf), junction_tdb_s,
                    math.nextafter(junction_tdb_s, math.inf))
    reference_bits: dict[float, np.ndarray] = {}
    selection_coverage: set[tuple[float, float]] = set()
    for order in permutations(epochs_tdb_s):
        for epoch_tdb_s in order:
            budget.check()
            for _ in range(2):
                state_si = spice.get_body_cartesian_state_at_epoch(
                    "Saturn", "SSB", "J2000", "NONE", epoch_tdb_s,
                )
                assert np.all(np.isfinite(state_si))
                bits = state_si.view(np.uint64)
                if epoch_tdb_s not in reference_bits:
                    reference_bits[epoch_tdb_s] = bits.copy()
                np.testing.assert_array_equal(bits, reference_bits[epoch_tdb_s])
            raw_state_km = (ctypes.c_double * 6)()
            cspice.spkssb_c(699, epoch_tdb_s, b"J2000", raw_state_km)
            assert cspice.failed_c() == 0
            raw_state_si = np.asarray(raw_state_km) * 1000.0
            np.testing.assert_array_equal(raw_state_si.view(np.uint64),
                                          reference_bits[epoch_tdb_s])
            if epoch_tdb_s == junction_tdb_s:
                handle, found = ctypes.c_int(), ctypes.c_int()
                descriptor = (ctypes.c_double * 5)()
                identifier = ctypes.create_string_buffer(41)
                cspice.spksfs_c(699, epoch_tdb_s, 41, ctypes.byref(handle), descriptor,
                                identifier, ctypes.byref(found))
                assert cspice.failed_c() == 0 and found.value == 1
                selection_coverage.add((descriptor[0], descriptor[1]))
            budget.check()
    assert selection_coverage == {(952430400.0, junction_tdb_s)}
    assert len(reference_bits) == 3 and budget.native_arc_propagations == 0
    print(json.dumps({
        "junction_tdb_s": junction_tdb_s, "time": "TDB seconds since J2000",
        "state_frame": "SSB/J2000", "state_units": ["m", "m/s"],
        "orders": 6, "named_queries": 36, "raw_cspice_queries": 18,
        "comparison": "Exact binary64 component bit patterns",
        "exact_junction_selected_coverage_tdb_s": sorted(selection_coverage),
        "scope": "Local query-order repeatability, not continuity or interpolation accuracy",
    }, sort_keys=True, allow_nan=False))


def test_saturn_source_file_segment_inventory(cspice: ctypes.CDLL) -> None:
    """Exhaust one file and its two relevant Saturn record directories, not all sources."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    start_s, end_s = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    handle, found = ctypes.c_int(), ctypes.c_int()
    # DAF's maximum packed-summary size; SPK consumes its first five doubles.
    summary = (ctypes.c_double * 125)()
    identifier = ctypes.create_string_buffer(41)
    cspice.spksfs_c(699, start_s, 41, ctypes.byref(handle), summary,
                    identifier, ctypes.byref(found))
    assert cspice.failed_c() == 0 and found.value == 1
    cspice.dafbfs_c(handle)
    assert cspice.failed_c() == 0
    count = saturn_count = 0
    overlaps: list[tuple[float, float, int, int]] = []
    while True:
        budget.check()
        cspice.daffna_c(ctypes.byref(found))
        assert cspice.failed_c() == 0 and found.value in (0, 1)
        if not found.value:
            break
        count += 1
        cspice.dafgs_c(summary)
        assert cspice.failed_c() == 0
        integers = [ctypes.c_int() for _ in range(6)]
        first, last = ctypes.c_double(), ctypes.c_double()
        cspice.spkuds_c(summary, *[ctypes.byref(value) for value in integers[:4]],
                        ctypes.byref(first), ctypes.byref(last),
                        *[ctypes.byref(value) for value in integers[4:]])
        assert cspice.failed_c() == 0
        body, center, frame, kind, begin, end = [value.value for value in integers]
        if body == 699:
            saturn_count += 1
            assert (center, frame, kind) == (6, 1, 3)
            assert math.isfinite(first.value) and math.isfinite(last.value)
            assert first.value < last.value and 0 < begin <= end
            if first.value <= end_s and last.value >= start_s:
                overlaps.append((first.value, last.value, begin, end))
    # Keep file order: the left interval is stored after the right interval.
    assert (count, saturn_count) == (1223, 171)
    assert overlaps == [
        (986817600.0, 1021204800.0, 25956465, 25968668),
        (952430400.0, 986817600.0, 25969025, 25981228),
    ]
    assert overlaps[1][0] <= start_s < overlaps[1][1] == overlaps[0][0] < end_s <= overlaps[0][1]
    record_boundaries_tdb_s: set[float] = set()
    record_endpoints_si: dict[float, list[tuple[Fraction, ...]]] = {}
    near_endpoints_m: dict[float, list[tuple[tuple[Fraction, ...], float]]] = {}
    record_rate_bounds_m_s: list[float] = []
    join_offset_s = Fraction(1, 8388608)  # One binary64 epoch ULP in this interval.
    overlapping_record_count = 0
    for segment_start_s, segment_end_s, begin, end in overlaps:
        directory = (ctypes.c_double * 4)()
        cspice.dafgda_c(handle, end - 3, end, directory)
        assert cspice.failed_c() == 0
        # Type 3: INIT, INTLEN, RSIZE, N; six polynomial coefficient sets.
        assert list(directory) == [segment_start_s, 343872.0, 122.0, 100.0]
        assert (122 - 2) // 6 - 1 == 19
        assert end - begin + 1 == 100 * 122 + 4
        assert segment_start_s + 100 * 343872 == segment_end_s
        for index in range(100):
            budget.check()
            address = begin + index * 122
            record = (ctypes.c_double * 122)()
            cspice.dafgda_c(handle, address, address + 121, record)
            assert cspice.failed_c() == 0
            record_start_s = segment_start_s + index * 343872
            record_end_s = record_start_s + 343872
            assert list(record[:2]) == [record_start_s + 171936, 171936.0]
            assert all(math.isfinite(value) for value in record)
            if record_start_s <= end_s and record_end_s >= start_s:
                overlapping_record_count += 1
                coefficients_km = tuple(tuple(record[2 + axis * 20 + degree]
                                              for degree in range(20)) for axis in range(3))
                rate_bound_m_s = trajectory._spk_position_rate_bound(budget, coefficients_km, record[1])
                record_rate_bounds_m_s.append(rate_bound_m_s)
                derivative_coefficients = np.polynomial.chebyshev.chebder(
                    np.asarray(coefficients_km).T, axis=0,
                ) * (1000 / record[1])
                for normalized_time in (-1.0, -0.5, 0.0, 0.5, 1.0):
                    derivative_m_s = np.polynomial.chebyshev.chebval(
                        normalized_time, derivative_coefficients,
                    )
                    assert np.linalg.norm(derivative_m_s) <= rate_bound_m_s
                record_boundaries_tdb_s.update(
                    epoch_s for epoch_s in (record_start_s, record_end_s)
                    if start_s < epoch_s < end_s
                )
                for epoch_s, sign in ((record_start_s, -1), (record_end_s, 1)):
                    if start_s < epoch_s < end_s:
                        # T_k(+1)=1 and T_k(-1)=(-1)^k, evaluated exactly.
                        endpoint_si = tuple(
                            1000 * sum((Fraction(record[2 + component * 20 + degree]) * sign ** degree
                                        for degree in range(20)), Fraction(0))
                            for component in range(6)
                        )
                        coefficients = np.asarray(record)[2:].reshape(6, 20)
                        clenshaw_si = np.polynomial.chebyshev.chebval(sign, coefficients.T) * 1000
                        oracle_difference_si = clenshaw_si - np.asarray([float(value) for value in endpoint_si])
                        assert np.linalg.norm(oracle_difference_si[:3]) <= 1e-8  # m
                        assert np.linalg.norm(oracle_difference_si[3:]) <= 1e-12  # m/s
                        record_endpoints_si.setdefault(epoch_s, []).append(endpoint_si)
                        # Exact recurrence at one epoch ULP inside this record.
                        normalized_time = sign * (1 - join_offset_s / Fraction(record[1]))
                        basis = [Fraction(1), normalized_time]
                        for degree in range(2, 20):
                            basis.append(2 * normalized_time * basis[-1] - basis[-2])
                        near_m = tuple(1000 * sum((Fraction(row[degree]) * basis[degree]
                                                 for degree in range(20)), Fraction(0))
                                       for row in coefficients_km)
                        near_endpoints_m.setdefault(epoch_s, []).append((near_m, rate_bound_m_s))
    assert overlapping_record_count == 74 and len(record_boundaries_tdb_s) == 73
    assert 986817600.0 in record_boundaries_tdb_s
    assert set(record_endpoints_si) == record_boundaries_tdb_s
    coefficient_jumps_si: list[tuple[float, float, float]] = []
    incompatible_position_joins = incompatible_velocity_joins = 0
    for epoch_s, endpoints in sorted(record_endpoints_si.items()):
        assert len(endpoints) == 2
        difference_si = tuple(a - b for a, b in zip(*endpoints))
        near_left, near_right = near_endpoints_m[epoch_s]
        motion_m = sum((abs(a - b) for a, b in zip(near_left[0], near_right[0])), Fraction(0))
        within_records_m = join_offset_s * (Fraction(near_left[1]) + Fraction(near_right[1]))
        jump_m = sum((abs(value) for value in difference_si[:3]), Fraction(0))
        assert motion_m <= within_records_m + jump_m
        assert motion_m > within_records_m  # Omitting the source jump is invalid.
        # Exact squared SI norms decide allocation exceedance; floats are reporting only.
        position_squared_m2 = sum((value * value for value in difference_si[:3]), Fraction(0))
        velocity_squared_m2_s2 = sum((value * value for value in difference_si[3:]), Fraction(0))
        assert position_squared_m2 > 0 and velocity_squared_m2_s2 > 0
        incompatible_position_joins += position_squared_m2 > (2 * Fraction("0.025")) ** 2
        incompatible_velocity_joins += velocity_squared_m2_s2 > (2 * Fraction("0.0000025")) ** 2
        coefficient_jumps_si.append((epoch_s, math.sqrt(float(position_squared_m2)),
                                     math.sqrt(float(velocity_squared_m2_s2))))
    assert (incompatible_position_joins, incompatible_velocity_joins) == (70, 68)
    settings = trajectory._create_time_limited_body_settings(environment_setup, start_s, end_s)
    budget.check()
    native = environment_setup.create_body_ephemeris(settings.get("Saturn").ephemeris_settings,
                                                    "Saturn")
    budget.check()
    spice = ephemeris._ensure_standard_kernels()
    boundary_errors_si: list[tuple[float, float, float]] = []
    direct_settings = environment_setup.ephemeris.direct_spice("SSB", "J2000", "Saturn")
    direct_native = environment_setup.create_body_ephemeris(direct_settings, "Saturn")
    assert (direct_native.frame_origin, direct_native.frame_orientation) == ("SSB", "J2000")
    budget.check()
    direct_native_errors_si: list[tuple[float, float]] = []
    for boundary_s in sorted(record_boundaries_tdb_s):
        errors_si: list[tuple[float, float]] = []
        for epoch_s in (math.nextafter(boundary_s, -math.inf), boundary_s,
                        math.nextafter(boundary_s, math.inf)):
            budget.check()
            direct_si = spice.get_body_cartesian_state_at_epoch("Saturn", "SSB", "J2000", "NONE",
                                                               epoch_s)
            native_difference_si = direct_native.cartesian_state(epoch_s) - direct_si
            assert np.all(np.isfinite(native_difference_si))
            native_error_m = float(np.linalg.norm(native_difference_si[:3]))
            native_error_m_s = float(np.linalg.norm(native_difference_si[3:]))
            assert native_error_m <= 0.001 and native_error_m_s <= 0.000001
            direct_native_errors_si.append((native_error_m, native_error_m_s))
            difference_si = native.cartesian_state(epoch_s) - direct_si
            assert np.all(np.isfinite(difference_si))
            errors_si.append((float(np.linalg.norm(difference_si[:3])),
                              float(np.linalg.norm(difference_si[3:]))))
        boundary_errors_si.append((boundary_s, max(value[0] for value in errors_si),
                                   max(value[1] for value in errors_si)))
    position_failures = sum(value[1] > 0.025 for value in boundary_errors_si)
    velocity_failures = sum(value[2] > 2.5e-6 for value in boundary_errors_si)
    # Preserve the observed failure population, not a relaxed acceptance limit.
    assert (position_failures, velocity_failures) == (73, 71)
    budget.check()
    assert budget.native_arc_propagations == 0
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "file_segment_count": count,
        "saturn_segment_count": saturn_count, "overlaps_in_file_order": overlaps,
        "overlap_fields": ["start_tdb_s", "end_tdb_s", "first_daf_word", "last_daf_word"],
        "record_duration_s": 343872, "polynomial_degree": 19,
        "record_headers_checked": 200, "candidate_overlapping_records": overlapping_record_count,
        "candidate_interior_record_boundaries_tdb_s": sorted(record_boundaries_tdb_s),
        "boundary_error_fields": ["boundary_tdb_s", "max_position_error_m", "max_velocity_error_m_s"],
        "boundary_errors": boundary_errors_si,
        "coefficient_jump_fields": ["boundary_tdb_s", "position_jump_m", "velocity_jump_m_s"],
        "coefficient_jumps": coefficient_jumps_si,
        "joins_exceeding_twice_position_allocation": incompatible_position_joins,
        "joins_exceeding_twice_velocity_allocation": incompatible_velocity_joins,
        "coefficient_frame": "Saturn barycenter/J2000",
        "record_position_rate_bound_min_m_s": min(record_rate_bounds_m_s),
        "record_position_rate_bound_max_m_s": max(record_rate_bounds_m_s),
        "exact_jump_inclusive_motion_controls": len(near_endpoints_m),
        "position_failed_boundaries": position_failures, "velocity_failed_boundaries": velocity_failures,
        "position_worst_boundary": max(boundary_errors_si, key=lambda row: row[1]),
        "velocity_worst_boundary": max(boundary_errors_si, key=lambda row: row[2]),
        "comparison_frame": "SSB/J2000", "comparison_query_count": 219,
        "experimental_direct_native_query_count": len(direct_native_errors_si),
        "experimental_direct_native_max_position_error_m": max(value[0] for value in direct_native_errors_si),
        "experimental_direct_native_max_velocity_error_m_s": max(value[1] for value in direct_native_errors_si),
        "qualification_status": "failed-existing-interpolation-allocation",
        "time": "TDB seconds since J2000", "target": 699, "center": 6, "frame": "J2000",
        "scope": "One file and two Saturn record directories; not all sources or coefficient error bounds",
    }, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("body,epoch_tdb_s,error_code", [
    ("ARIADNA_UNKNOWN_BODY", 986817600.0, r"SPICE\(IDCODENOTFOUND\)"),
    ("Saturn", -1e12, r"SPICE\(SPKINSUFFDATA\)"),
    ("Saturn", 1e12, r"SPICE\(SPKINSUFFDATA\)"),
])
def test_direct_spice_errors_do_not_poison_valid_queries(
    body: str, epoch_tdb_s: float, error_code: str,
) -> None:
    """Native errors must raise and leave valid direct queries repeatable without reset."""
    import spiceypy
    from tudatpy.dynamics import environment_setup

    budget = trajectory._RefinementBudget("d0001-t0035", 300.0)
    spice = ephemeris._ensure_standard_kernels()
    kernel_count = spice.get_total_count_of_kernels_loaded()
    valid = environment_setup.create_body_ephemeris(
        environment_setup.ephemeris.direct_spice("SSB", "J2000", "Saturn"), "Saturn",
    )
    baseline_si = valid.cartesian_state(986817600.0)
    assert np.all(np.isfinite(baseline_si))
    budget.check()
    with pytest.raises(RuntimeError, match=error_code) as error:
        invalid = environment_setup.create_body_ephemeris(
            environment_setup.ephemeris.direct_spice("SSB", "J2000", body), body,
        )
        invalid.cartesian_state(epoch_tdb_s)
    assert body.upper() in str(error.value).upper()
    assert not spiceypy.failed()
    recovered_si = valid.cartesian_state(986817600.0)
    np.testing.assert_array_equal(recovered_si.view(np.uint64), baseline_si.view(np.uint64))
    assert spice.get_total_count_of_kernels_loaded() == kernel_count
    budget.check()
    assert budget.native_arc_propagations == 0


def test_unknown_spk_body_has_no_descriptor(cspice: ctypes.CDLL) -> None:
    """An unknown ID must not produce a fabricated usable segment."""
    handle, found = ctypes.c_int(), ctypes.c_int()
    descriptor = (ctypes.c_double * 5)()
    identifier = ctypes.create_string_buffer(41)
    cspice.spksfs_c(-2147483647, 978995455.2304223, 41, ctypes.byref(handle),
                    descriptor, identifier, ctypes.byref(found))
    assert cspice.failed_c() == 0 and found.value == 0
