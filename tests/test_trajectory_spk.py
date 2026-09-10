"""Read-only SPK provenance controls, not a between-epoch error certificate."""

from __future__ import annotations

import ctypes
from fractions import Fraction
from hashlib import file_digest, sha256
import json
from itertools import permutations
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

    coast_durations_s = (1 / 64, 1.0)
    coast_body_reaches_m: dict[float, dict[str, float]] = {}
    body_ids = dict(zip(trajectory.PHYSICAL_BODY_NAMES, (10, 1, 2, 399, 301, 499, 599, 699), strict=True))
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
    coast_domains = _check_conditional_full_force_coast_domains(
        budget, start_tdb_s, end_tdb_s, coast_body_reaches_m, chain_speed_bounds_m_s[10],
        {body: motion_samples[target][0][1] for body, target in body_ids.items()},
        run_native_controls=native_record_readback,
    )
    assert all(motion_samples[target][0][0] == start_tdb_s for target in body_ids.values())

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
    assert budget.native_arc_propagations == (4 if native_record_readback else 0)
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "time": "TDB seconds since J2000",
        "candidate_interval_tdb_s": [start_tdb_s, end_tdb_s],
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
) -> dict[str, Fraction]:
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
    for body, name, frame_id in ((301, "Moon", 10020), (499, "Mars", 10014)):
        budget.check()
        frame = f"IAU_{name.upper()}"
        assert spice.namfrm(frame) == frame_id and spice.frinfo(frame_id) == (body, 2, body)
        components = []
        for polynomial, periodic, time_unit_s in (("POLE_RA", "RA", century_s),
                                                 ("POLE_DEC", "DEC", century_s), ("PM", "PM", 86400)):
            amplitudes = tuple(inputs[f"BODY301_NUT_PREC_{periodic}"]) if body == 301 else ()
            assert len(amplitudes) == (13 if body == 301 else 0)
            components.append(_pck_euler_rate_upper_rad_s(
                tuple(inputs[f"BODY{body}_{polynomial}"]), time_unit_s,
                epoch_magnitude_s, amplitudes, phase_rates if body == 301 else (),
            ))
        bounds[name] = sum(components, Fraction(0))
        # Euler generators have unit operator norm: |omega| <= sum |angle'|.
        for epoch_tdb_s in np.linspace(start_tdb_s, end_tdb_s, 13):
            budget.check()
            rotation, angular_velocity = spice.xf2rav(spice.sxform("J2000", frame, float(epoch_tdb_s)))
            assert np.max(np.abs(rotation @ rotation.T - np.eye(3))) <= 1e-14
            assert float(np.linalg.norm(angular_velocity)) <= float(bounds[name])
    budget.check()
    return bounds


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


def _check_conditional_full_force_coast_domains(
    budget: trajectory._RefinementBudget, start_tdb_s: float, end_tdb_s: float,
    body_reaches_m: dict[float, dict[str, float]], sun_speed_upper_m_s: float,
    position_anchors_m: dict[str, np.ndarray],
    *, run_native_controls: bool,
) -> list[dict[str, object]]:
    """Check conditional ideal domains and optional native endpoint residuals."""
    from test_trajectory_gravity import _candidate, _spacecraft

    candidate = _candidate(
        departure_epoch_utc=ephemeris.tdb_to_utc(start_tdb_s),
        arrival_epoch_utc=ephemeris.tdb_to_utc(end_tdb_s),
        departure_epoch_tdb_s=start_tdb_s, arrival_epoch_tdb_s=end_tdb_s,
        flight_time_s=end_tdb_s - start_tdb_s,
    )
    spacecraft = _spacecraft()
    rotation_rates_rad_s = _check_pinned_pck_rotation_rates(budget, start_tdb_s, end_tdb_s)
    environment = trajectory._build_physical_environment(candidate, spacecraft, budget=budget)
    bodies = environment.bodies
    states = {body: np.asarray(bodies.get(body).ephemeris.cartesian_state(start_tdb_s)).reshape(6)
              for body in trajectory.PHYSICAL_BODY_NAMES}
    assert all(np.all(np.isfinite(state)) for state in states.values())
    for body, state in states.items():
        assert np.array_equal(state[:3], position_anchors_m[body]), body
    assert sum((abs(Fraction(value)) for value in states["Sun"][3:]), Fraction(0)) <= Fraction(sun_speed_upper_m_s)
    guards_m = {surface.body: surface.guard_radius_m for surface in environment.collision_resource.surfaces}
    position_radius_m, velocity_radius_m_s = 1000.0, 0.1
    results: list[dict[str, object]] = []
    for center, radius_m in (("Moon", 1_837_400.0), ("Mars", 3_689_500.0)):
        # The stored SI state defines the exact initial condition of this control.
        state = states[center] + np.asarray([radius_m, 0.0, 0.0, 0.0, 1500.0, 0.0])
        initial_speed_m_s = sum((abs(Fraction(value)) for value in state[3:]), Fraction(0))
        initial_speed_upper_m_s = math.nextafter(float(initial_speed_m_s), math.inf)
        assert Fraction(initial_speed_upper_m_s) >= initial_speed_m_s
        relative_speed_m_s = initial_speed_m_s + Fraction(velocity_radius_m_s) + Fraction(sun_speed_upper_m_s)
        relative_speed_upper_m_s = math.nextafter(float(relative_speed_m_s), math.inf)
        assert Fraction(relative_speed_upper_m_s) >= relative_speed_m_s
        for duration_s, reaches_m in body_reaches_m.items():
            budget.check()
            floors_m: dict[str, float] = {}
            gravity_m_s2: dict[str, float] = {}
            point_mass_variation_m_s2: dict[str, float] = {}
            frozen_harmonic_variation_m_s2: dict[str, float] = {}
            arbitrary_rotation_variation_m_s2: dict[str, float] = {}
            angle_limited_rotation_variation_m_s2: dict[str, float] = {}
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
                    radius_upper_m = sum((abs(Fraction(x) - Fraction(b)) for x, b in
                                          zip(state[:3], states[body][:3], strict=True)), Fraction(0))
                    radius_upper_m += Fraction(position_radius_m) + Fraction(reaches_m[body])
                    angle_limited_m_s2 = _angle_limited_rotation_bound_m_s2(
                        rotation_rates_rad_s[body] * Fraction(duration_s), rotation_m_s2 / 2,
                        tail_jacobian_s_inv2, radius_upper_m,
                    )
                    assert 0 < angle_limited_m_s2 < rotation_m_s2
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
            thrust, srp = trajectory._thrust_and_srp_upper_bounds(
                budget.candidate_id, spacecraft, floors_m["Sun"], thrust_enabled=False,
            )
            relativity = trajectory._schwarzschild_acceleration_upper_bound(
                budget.candidate_id, bodies.get("Sun").gravity_field_model.gravitational_parameter,
                floors_m["Sun"], relative_speed_upper_m_s,
            )
            acceleration_m_s2 = trajectory._sum_force_acceleration_bounds(
                budget, gravity_m_s2, thrust, srp, relativity, thrust_enabled=False,
            )
            assert Fraction(acceleration_m_s2) >= sum(map(Fraction, (*gravity_m_s2.values(), thrust, srp, relativity)))
            reach_m = trajectory._position_reach_upper_bound(
                budget, duration_s, 0.0, initial_speed_upper_m_s, acceleration_m_s2,
            )
            velocity_reach_m_s = Fraction(acceleration_m_s2) * Fraction(duration_s)
            mass_floor_kg = trajectory._mass_lower_bound(budget, spacecraft.initial_mass_kg, 0.0, 0.0, duration_s)
            assert mass_floor_kg == spacecraft.initial_mass_kg > spacecraft.dry_mass_kg
            closed = reach_m < position_radius_m and velocity_reach_m_s < Fraction(velocity_radius_m_s)
            assert closed is (duration_s == 1 / 64), (center, duration_s, reach_m, float(velocity_reach_m_s))
            endpoint_controls: list[dict[str, object]] = []
            if run_native_controls and closed:
                from tudatpy.astro.time_representation import Time
                from tudatpy.dynamics import propagation_setup

                for tighter in (False, True):
                    budget.begin_control()
                    models = trajectory._build_arc_force_models(budget.candidate_id, environment)
                    final_tdb_s = start_tdb_s + duration_s
                    settings = trajectory._build_coupled_arc_settings(
                        budget.candidate_id, bodies, models, state, spacecraft.initial_mass_kg, start_tdb_s,
                        trajectory._build_arc_integrator(budget.candidate_id, "coast", tighter=tighter),
                        propagation_setup.propagator.time_termination(final_tdb_s, terminate_exactly_on_final_condition=True),
                        thrust_enabled=False,
                    )
                    simulator = trajectory._run_native_arc(budget, bodies, settings, first_in_evaluation=True)
                    assert simulator.integration_completed_successfully
                    history = simulator.state_history_time_object
                    first_epoch, last_epoch = min(history), max(history)
                    assert (first_epoch - Time(start_tdb_s)).to_float() == 0.0
                    assert (last_epoch - Time(final_tdb_s)).to_float() == 0.0
                    assert np.array_equal(np.asarray(history[first_epoch]).reshape(7)[:6], state)
                    final_state = np.asarray(history[last_epoch]).reshape(7)
                    assert np.all(np.isfinite(final_state)) and final_state[6] == spacecraft.initial_mass_kg
                    curvature_m = Fraction(acceleration_m_s2) * Fraction(duration_s)**2 / 2
                    error_bound_m = _ballistic_endpoint_error_bound_m(state, final_state[:3], duration_s, acceleration_m_s2)
                    assert error_bound_m <= Fraction("0.001"), (center, tighter, float(error_bound_m))
                    reported_error_m = math.nextafter(float(error_bound_m), math.inf)
                    assert Fraction(reported_error_m) >= error_bound_m
                    velocity_error_m_s = _coast_endpoint_velocity_error_bound_m_s(
                        state[3:], final_state[3:6], duration_s, acceleration_m_s2,
                    )
                    assert velocity_error_m_s >= velocity_reach_m_s > Fraction("0.000001")
                    reported_velocity_error_m_s = math.nextafter(float(velocity_error_m_s), math.inf)
                    assert Fraction(reported_velocity_error_m_s) >= velocity_error_m_s
                    endpoint_controls.append({"tighter": tighter,
                        "conditional_endpoint_position_error_m": reported_error_m,
                        "conditional_endpoint_velocity_error_m_s": reported_velocity_error_m_s,
                        "velocity_bound_resolves_1um_s": velocity_error_m_s <= Fraction("0.000001"),
                        "ballistic_residual_l1_m": float(error_bound_m - curvature_m)})
            results.append({"center": center, "duration_s": duration_s,
                "conditional_pck_rotation_path_rad": {
                    body: math.nextafter(float(rate * Fraction(duration_s)), math.inf)
                    for body, rate in rotation_rates_rad_s.items()},
                "acceleration_bound_m_s2": acceleration_m_s2, "position_reach_m": reach_m,
                "conditional_point_mass_variation_m_s2": point_mass_variation_m_s2,
                "conditional_frozen_harmonic_variation_m_s2": frozen_harmonic_variation_m_s2,
                "conditional_arbitrary_rotation_variation_m_s2": arbitrary_rotation_variation_m_s2,
                "conditional_angle_limited_rotation_variation_m_s2": angle_limited_rotation_variation_m_s2,
                "velocity_reach_upper_m_s": math.nextafter(float(velocity_reach_m_s), math.inf),
                "conditional_domain_closed": closed, "endpoint_controls": endpoint_controls})
    expected_arcs = 4 if run_native_controls else 0
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
