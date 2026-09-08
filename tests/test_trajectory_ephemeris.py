from __future__ import annotations

import json
from fractions import Fraction
from importlib.metadata import version
from itertools import permutations
import math
from pathlib import Path
import platform
import sys
import time

import numpy as np
import pytest

from space_nav import ephemeris, trajectory
from space_nav.scenario import load_scenario
from space_nav.transfer import search_impulsive_transfers


ROOT = Path(__file__).resolve().parents[1]


def test_pinned_grid_binary64_arithmetic_matches_exact_rationals() -> None:
    """Replay source arithmetic premises, not compiled native evaluation error."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    ephemeris._ensure_standard_kernels()
    settings = trajectory._create_time_limited_body_settings(
        environment_setup, evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1],
    )
    first = settings.get("Sun").ephemeris_settings
    start_s, end_s, step_s = first.initial_time, first.final_time, first.time_step
    assert sys.float_info.radix == 2 and sys.float_info.mant_dig == 53
    assert step_s == 300.0
    assert 0 < start_s < end_s <= 2 * start_s  # Sterbenz domain for represented epochs.
    for body in trajectory.PHYSICAL_BODY_NAMES:
        body_settings = settings.get(body).ephemeris_settings
        assert (body_settings.initial_time, body_settings.final_time, body_settings.time_step) == (
            start_s, end_s, step_s,
        )
    exact_start_s, exact_step_s = Fraction(start_s), Fraction(step_s)
    count = math.ceil((Fraction(end_s) - exact_start_s) / exact_step_s)
    epoch_s = start_s
    # Source createStateInterpolatorFromSpice uses repeated addition, not multiplication.
    for index in range(count):
        budget.check()
        assert epoch_s < end_s
        assert Fraction(epoch_s) == exact_start_s + index * exact_step_s
        epoch_s += step_s
    assert epoch_s >= end_s
    largest_denominator_s5 = 0
    for first_index in (0, count // 2, count - 6):
        nodes_s = [start_s + index * step_s for index in range(first_index, first_index + 6)]
        for selected, node_s in enumerate(nodes_s):
            denominator_s5 = 1.0
            exact_product = Fraction(1)
            for other_index, other_s in enumerate(nodes_s):
                if selected != other_index:
                    difference_s = node_s - other_s
                    assert Fraction(difference_s) == Fraction(node_s) - Fraction(other_s)
                    denominator_s5 *= difference_s
                    exact_product *= Fraction(node_s) - Fraction(other_s)
                    assert Fraction(denominator_s5) == exact_product
            factorial_denominator = (-1) ** (5 - selected) * math.factorial(selected) * math.factorial(5 - selected) * 300 ** 5
            assert exact_product == factorial_denominator
            largest_denominator_s5 = max(largest_denominator_s5, abs(factorial_denominator))
        for query_s in (nodes_s[2], math.nextafter(nodes_s[2], nodes_s[3]),
                        (nodes_s[2] + nodes_s[3]) / 2,
                        math.nextafter(nodes_s[3], nodes_s[2]), nodes_s[3]):
            for node_s in nodes_s:
                assert Fraction(query_s - node_s) == Fraction(query_s) - Fraction(node_s)
    assert largest_denominator_s5 < 2 ** 53
    # All non-knot represented queries in a middle cell: delta <= |t-node| <= 3h.
    # Spacing is nondecreasing on this positive epoch interval. Exact differences
    # and cached denominators were established above; do not assume state ranges.
    unit = Fraction(1, 2 ** 53)
    delta_s = Fraction(math.ulp(start_s))
    max_difference_s = 3 * exact_step_s
    normal_min, finite_max = Fraction(sys.float_info.min), Fraction(sys.float_info.max)
    numerator_lower = numerator_upper = Fraction(1)
    for _ in range(6):
        exact_lower = numerator_lower * delta_s
        exact_upper = numerator_upper * max_difference_s
        assert normal_min < exact_lower <= exact_upper < finite_max
        numerator_lower = exact_lower * (1 - unit)
        numerator_upper = exact_upper * (1 + unit)
        assert normal_min < numerator_lower <= numerator_upper < finite_max
    denominator_lower = delta_s * (math.factorial(2) * math.factorial(3) * exact_step_s ** 5)
    denominator_upper = max_difference_s * largest_denominator_s5
    assert normal_min < denominator_lower <= denominator_upper < finite_max
    denominator_lower *= 1 - unit
    denominator_upper *= 1 + unit
    assert normal_min < denominator_lower <= denominator_upper < finite_max
    weight_lower = numerator_lower / denominator_upper
    weight_upper = numerator_upper / denominator_lower
    assert normal_min < weight_lower <= weight_upper < finite_max
    weight_lower *= 1 - unit
    weight_upper *= 1 + unit
    assert normal_min < weight_lower <= weight_upper < finite_max
    # Coarse powers of two used by the separate state-range qualification.
    assert Fraction(2) ** -200 < weight_lower <= weight_upper < 2 ** 40
    # Exercise the nearest represented interior queries as well as the knot shortcut.
    control_states_si = np.asarray([[float((i - 2) * (j + 1)) for j in range(6)] for i in range(6)])
    for first_index in (0, count // 2, count - 6):
        nodes_s = [start_s + index * step_s for index in range(first_index, first_index + 6)]
        for query_s in (nodes_s[2], math.nextafter(nodes_s[2], nodes_s[3]),
                        math.nextafter(nodes_s[3], nodes_s[2]), nodes_s[3]):
            np.testing.assert_allclose(
                _replay_lagrange_state(nodes_s, control_states_si, query_s),
                _rational_lagrange_state(nodes_s, control_states_si, query_s),
                rtol=0.0, atol=1e-12,
            )
    # Counterexamples keep exactness conditional on the checked grid/domain.
    assert Fraction(start_s + 0.1) != Fraction(start_s) + Fraction(0.1)
    assert Fraction(float(2 ** 54) - 1.0) != Fraction(2 ** 54) - 1
    budget.check()
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({
        "scope": "Python binary64 replay of pinned source arithmetic; not native roundoff bound",
        "candidate_id": evidence["candidate_id"], "grid_node_count": count,
        "initial_tdb_s": start_s, "final_tdb_s": end_s, "step_s": step_s,
        "largest_exact_denominator_s5": largest_denominator_s5,
        "weight_range_scope": "interior binary64 non-knot queries; excludes state arithmetic and compiled paths",
        "minimum_epoch_spacing_s": float(delta_s),
        "weight_magnitude_lower_exact": str(weight_lower),
        "weight_magnitude_upper_exact": str(weight_upper),
        "time_scale": "TDB seconds since J2000",
    }, sort_keys=True, allow_nan=False))


def _assert_pinned_state_range(states_si: np.ndarray) -> None:
    """Test-only range premise in m and m/s, not a production scientific limit."""
    assert np.all(np.isfinite(states_si))
    magnitudes_si = np.abs(states_si)
    assert np.all((magnitudes_si == 0.0) | ((magnitudes_si >= 2.0 ** -100) & (magnitudes_si <= 2.0 ** 100)))


@pytest.mark.parametrize("value", [math.nan, math.inf, 2.0 ** -101, 2.0 ** 101])
def test_pinned_state_range_rejects_unqualified_values(value: float) -> None:
    with pytest.raises(AssertionError):
        _assert_pinned_state_range(np.full((6, 6), value))


def test_state_accumulation_range_handles_cancellation() -> None:
    """Exact dyadic lattice prevents subnormal nonzero cancellation results."""
    _assert_pinned_state_range(np.asarray([0.0, 2.0 ** -100, -(2.0 ** -100), 2.0 ** 100, -(2.0 ** 100)]))
    unit = Fraction(1, 2 ** 53)
    normal_min, finite_max = Fraction(sys.float_info.min), Fraction(sys.float_info.max)
    exact_product_min = Fraction(2) ** (-200 - 100)
    exact_product_max = Fraction(2) ** (40 + 100)
    term_min, term_max = Fraction(2) ** -301, Fraction(2) ** 141
    assert normal_min < exact_product_min <= exact_product_max < finite_max
    assert term_min < exact_product_min * (1 - unit)
    assert exact_product_max * (1 + unit) < term_max
    lattice = term_min / 2 ** 52
    assert lattice == Fraction(2) ** -353 > normal_min
    upper = Fraction(0)
    for _ in range(6):
        exact_upper = upper + term_max
        assert exact_upper < finite_max
        upper = exact_upper * (1 + unit)
        assert upper < finite_max
    assert upper < 2 ** 145
    # A smallest-binade ulp, exact zero, and loss of tiny terms beside a large
    # term are exercised in every order. The range proof does not rely on this sample.
    small = float(term_min)
    neighbor = math.nextafter(small, math.inf)
    seen_zero = seen_lattice = False
    for terms in permutations((small, neighbor, -small, -neighbor, 0.0, 2.0 ** 140)):
        total = 0.0
        for term in terms:
            exact_sum = Fraction(total) + Fraction(term)
            assert (exact_sum / lattice).denominator == 1
            assert exact_sum == 0 or abs(exact_sum) >= lattice
            total += term
            _assert_unit_roundoff(total, exact_sum)
            assert (Fraction(total) / lattice).denominator == 1
            seen_zero |= exact_sum == 0
            seen_lattice |= abs(exact_sum) == lattice
    assert seen_zero and seen_lattice


def _rational_lagrange_state(
    epochs_tdb_s: list[float], states_si: np.ndarray, epoch_tdb_s: float,
) -> np.ndarray:
    """Exact polynomial of supplied binary SI states; not a SPICE error bound."""
    nodes = [Fraction(epoch) for epoch in epochs_tdb_s]
    target = Fraction(epoch_tdb_s)
    weights = [
        math.prod((target - other) / (node - other)
                  for index, other in enumerate(nodes) if index != selected)
        for selected, node in enumerate(nodes)
    ]
    exact_components = [
        sum((weight * Fraction(float(value)) for weight, value in zip(weights, column)), Fraction(0))
        for column in states_si.T
    ]
    rounded_si = np.asarray([float(value) for value in exact_components])
    for rounded, exact in zip(rounded_si, exact_components):
        _assert_unit_roundoff(float(rounded), exact)
    return rounded_si


def _assert_unit_roundoff(actual: float, exact: Fraction) -> None:
    """Check the relative IEEE model at one operation, including an exact zero."""
    assert math.isfinite(actual)
    assert abs(Fraction(actual) - exact) <= Fraction(1, 2 ** 53) * abs(exact)


@pytest.mark.parametrize("case", ["underflow", "nonfinite", "excess_error"])
def test_unit_roundoff_check_rejects_invalid_model_premises(case: str) -> None:
    actual, exact = {
        "underflow": (0.0, Fraction(math.ulp(0.0)) / 2),
        "nonfinite": (math.inf, Fraction(10) ** 400),
        "excess_error": (math.nextafter(1.0, math.inf), Fraction(1)),
    }[case]
    with pytest.raises(AssertionError):
        _assert_unit_roundoff(actual, exact)


@pytest.mark.parametrize("count", [15, 16])
def test_roundoff_factor_products_fit_exact_gamma_envelope(count: int) -> None:
    unit = Fraction(1, 2 ** 53)
    gamma = count * unit / (1 - count * unit)
    assert (1 - unit) ** (-count) - 1 <= gamma
    assert (1 + unit) ** count - 1 <= gamma
    assert 1 - (1 - unit) ** count <= gamma
    assert 15 * unit / (1 - 15 * unit) + unit <= 16 * unit / (1 - 16 * unit)


def _replay_lagrange_state(
    epochs_tdb_s: list[float], states_si: np.ndarray, epoch_tdb_s: float,
) -> np.ndarray:
    """Replay inspected scalar multiply/add order, not compiler or error certification."""
    if epoch_tdb_s in epochs_tdb_s:
        return states_si[epochs_tdb_s.index(epoch_tdb_s)].copy()
    differences_s = [epoch_tdb_s - node for node in epochs_tdb_s]
    assert all(Fraction(value) == Fraction(epoch_tdb_s) - Fraction(node)
               for value, node in zip(differences_s, epochs_tdb_s))
    numerator_s6 = 1.0
    for difference_s in differences_s:
        exact_product = Fraction(numerator_s6) * Fraction(difference_s)
        numerator_s6 *= difference_s
        _assert_unit_roundoff(numerator_s6, exact_product)
    result_si = [0.0] * 6
    for index, node in enumerate(epochs_tdb_s):
        denominator_s5 = 1.0
        for other_index, other in enumerate(epochs_tdb_s):
            if other_index != index:
                exact_product = Fraction(denominator_s5) * (Fraction(node) - Fraction(other))
                denominator_s5 *= node - other
                assert Fraction(denominator_s5) == exact_product
        denominator_s6 = differences_s[index] * denominator_s5
        _assert_unit_roundoff(denominator_s6, Fraction(differences_s[index]) * Fraction(denominator_s5))
        weight = numerator_s6 / denominator_s6
        _assert_unit_roundoff(weight, Fraction(numerator_s6) / Fraction(denominator_s6))
        for component in range(6):
            product_si = float(states_si[index, component]) * weight
            _assert_unit_roundoff(product_si, Fraction(float(states_si[index, component])) * Fraction(weight))
            exact_sum = Fraction(result_si[component]) + Fraction(product_si)
            result_si[component] += product_si
            _assert_unit_roundoff(result_si[component], exact_sum)
    return np.asarray(result_si)


@pytest.mark.parametrize("case", ["affine", "cancellation"])
def test_lagrange_arithmetic_replay_matches_exact_controls(case: str) -> None:
    nodes_s = [-600.0, -300.0, 0.0, 300.0, 600.0, 900.0]
    states_si = np.asarray([
        [(axis + 1) * (index - 2) if case == "affine" else (-1) ** index * (axis + 1)
         for axis in range(6)] for index in range(6)
    ], dtype=float)
    for epoch_s in (0.0, 37.5, 150.0, 262.5, 300.0):
        replay_si = _replay_lagrange_state(nodes_s, states_si, epoch_s)
        exact_si = _rational_lagrange_state(nodes_s, states_si, epoch_s)
        np.testing.assert_allclose(replay_si, exact_si, rtol=0.0, atol=1e-12)
        if epoch_s in nodes_s:
            np.testing.assert_array_equal(replay_si, states_si[nodes_s.index(epoch_s)])
        if case == "cancellation" and epoch_s == 150.0:
            np.testing.assert_array_equal(exact_si, np.zeros(6))


def test_six_node_amplification_identity_is_sharp() -> None:
    nodes = tuple(Fraction(index) for index in range(-2, 4))
    signs = (1, -1, 1, 1, -1, 1)
    for index in range(33):
        u = Fraction(index, 32)
        weights = [math.prod((u - other) / (node - other)
                             for j, other in enumerate(nodes) if i != j)
                   for i, node in enumerate(nodes)]
        assert sum(weights) == 1
        assert all(sign * weight >= 0 for sign, weight in zip(signs, weights))
        w = u * (1 - u)
        amplification = sum(abs(weight) for weight in weights)
        assert weights[1] + weights[4] == -w * (6 + w) / 8
        assert amplification == 1 + w * (6 + w) / 4
        assert amplification <= Fraction(89, 64)
        if u == Fraction(1, 2):
            assert amplification == Fraction(89, 64) > 1


@pytest.mark.parametrize("step_s", [1.0, 300.0])
@pytest.mark.parametrize("worst_signs", [False, True])
def test_native_six_node_amplification_matches_exact_control(step_s: float, worst_signs: bool) -> None:
    """Attaining nodal perturbations are synthetic controls, not SPICE errors."""
    from tudatpy.dynamics import environment_setup

    node_error_m = 0.125  # Exactly representable; perturbation along the X axis.
    signs = dict(zip(range(-2, 4), (1, -1, 1, 1, -1, 1))) if worst_signs else {}
    table = environment_setup.create_body_ephemeris(environment_setup.ephemeris.tabulated({
        index * step_s: np.asarray([signs.get(index, 1) * node_error_m, 0.0, 0.0, 0.0, 0.0, 0.0])
        for index in range(-8, 10)
    }, "SSB", "J2000"), "AmplificationControl")
    assert table.frame_origin == "SSB" and table.frame_orientation == "J2000"
    for offset in (0.0, 0.125, 0.25, 0.5, 0.75, 0.875, 1.0):
        u = Fraction(offset)
        w = u * (1 - u)
        expected_factor = 1 + w * (6 + w) / 4 if worst_signs else Fraction(1)
        expected_m = float(Fraction(node_error_m) * expected_factor)
        native_si = np.asarray(table.cartesian_state(offset * step_s)).reshape(6)
        np.testing.assert_allclose(native_si, [expected_m, 0.0, 0.0, 0.0, 0.0, 0.0],
                                   rtol=0.0, atol=1e-12)
    midpoint_error_m = float(table.cartesian_position(0.5 * step_s)[0])
    if worst_signs:
        assert midpoint_error_m > node_error_m
    print(json.dumps({
        "scope": "Synthetic nodal-error amplification, not native/SPICE error bound",
        "step_s": step_s, "worst_signs": worst_signs, "node_error_m": node_error_m,
        "native_midpoint_error_m": midpoint_error_m,
        "exact_midpoint_amplification": 89 / 64 if worst_signs else 1.0,
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB seconds since J2000",
    }, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("degree", range(6))
def test_rational_ephemeris_oracle_reproduces_polynomials(degree: int) -> None:
    origin_tdb_s = 978995455.2304223
    offsets_s = [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    nodes_tdb_s = [origin_tdb_s + offset for offset in offsets_s]
    states_si = np.asarray([
        [(component + 1) * offset ** degree for component in range(6)]
        for offset in offsets_s
    ])
    # Include knots and off-grid evaluations; each SI component is independent.
    for offset_s in (0.0, 0.125, 0.5, 0.875, 1.0):
        actual = _rational_lagrange_state(nodes_tdb_s, states_si, origin_tdb_s + offset_s)
        expected = np.asarray([(component + 1) * offset_s ** degree for component in range(6)])
        np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-12)


@pytest.mark.parametrize("degree", [5, 6])
@pytest.mark.parametrize("step_s", [1.0, 300.0])
def test_native_ephemeris_grid_switch_does_not_guarantee_smooth_position(
    degree: int, step_s: float,
) -> None:
    """Analytic control, not a replacement ephemeris or a mission jump bound."""
    from tudatpy.dynamics import environment_setup

    # x = u**degree metres, u = t/step; sampled vx is its exact derivative.
    history = {
        index * step_s: np.asarray([
            float(index ** degree), 0.0, 0.0,
            degree * index ** (degree - 1) / step_s, 0.0, 0.0,
        ])
        for index in range(-8, 10)
    }
    table = environment_setup.create_body_ephemeris(
        environment_setup.ephemeris.tabulated(history, "SSB", "J2000"), "Control",
    )
    assert table.frame_origin == "SSB" and table.frame_orientation == "J2000"
    knot_tdb_s = step_s
    knot_state_si = np.asarray(table.cartesian_state(knot_tdb_s)).reshape(6)
    np.testing.assert_allclose(knot_state_si, [1.0, 0.0, 0.0, degree / step_s, 0.0, 0.0],
                               rtol=0.0, atol=1e-10)
    slopes_m_s: dict[str, float] = {}
    for side, nodes, sign in (("left", range(-2, 4), -1), ("right", range(-1, 5), 1)):
        # For degree six the interpolation remainder is the monic node product;
        # for degree five interpolation is exact. No fitted or sampled oracle.
        product_derivative_at_knot = math.prod(1 - node for node in nodes if node != 1)
        expected_derivative_m_s = (
            degree - (product_derivative_at_knot if degree == 6 else 0)
        ) / step_s
        for denominator in (4096, 8192):
            delta_s = sign * step_s / denominator
            epoch_tdb_s = knot_tdb_s + delta_s
            u = Fraction(epoch_tdb_s) / Fraction(step_s)
            expected_position_m = u ** degree
            if degree == 6:
                expected_position_m -= math.prod(u - node for node in nodes)
            expected_velocity_m_s = degree * u ** (degree - 1) / Fraction(step_s)
            state_si = np.asarray(table.cartesian_state(epoch_tdb_s)).reshape(6)
            np.testing.assert_allclose(state_si[:3], [float(expected_position_m), 0.0, 0.0],
                                       rtol=0.0, atol=1e-10)
            np.testing.assert_allclose(state_si[3:], [float(expected_velocity_m_s), 0.0, 0.0],
                                       rtol=0.0, atol=1e-10)
            secant_m_s = (state_si[0] - knot_state_si[0]) / delta_s
            rational_secant_m_s = float((expected_position_m - 1) / Fraction(delta_s))
            assert abs(secant_m_s - rational_secant_m_s) <= 1e-6
            # This is a finite-secant approximation allowance, not a native or
            # mission velocity tolerance; the limiting derivatives are analytic.
            assert abs(secant_m_s - expected_derivative_m_s) <= 0.05 / step_s
        slopes_m_s[side] = expected_derivative_m_s
    if degree == 5:
        assert slopes_m_s["left"] == slopes_m_s["right"] == knot_state_si[3]
    else:
        assert slopes_m_s["left"] == -6.0 / step_s
        assert slopes_m_s["right"] == 18.0 / step_s
        assert slopes_m_s["left"] != knot_state_si[3] != slopes_m_s["right"]
    print(json.dumps({
        "scope": "Analytic native interpolation control; not mission derivative jumps",
        "degree": degree, "step_s": step_s, "knot_tdb_s": knot_tdb_s,
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB seconds since J2000",
        "position_m": knot_state_si[0], "returned_velocity_m_s": knot_state_si[3],
        "position_derivative_limits_m_s": slopes_m_s,
    }, sort_keys=True, allow_nan=False))


@pytest.mark.parametrize("phase", ["departure", "cruise", "arrival"])
@pytest.mark.parametrize("duration_s", [30.0, 300.0, 1800.0, 86400.0])
def test_moving_body_chord_deviation_is_not_interpolation_error(
    phase: str, duration_s: float,
) -> None:
    """Measure required motion allowances; sampled maxima are not upper bounds."""
    from tudatpy.dynamics import environment_setup

    evidence = json.loads((ROOT / "tests/data/m3_ephemeris_qualification.json").read_text())
    bound_budget = trajectory._RefinementBudget(evidence["candidate_id"], 300.0)
    departure_s, arrival_s = evidence["epoch_tdb_s"][0], evidence["epoch_tdb_s"][-1]
    fraction = {"departure": 0.0, "cruise": 0.5, "arrival": 1.0}[phase]
    start_s = departure_s + fraction * (arrival_s - departure_s - duration_s)
    end_s = start_s + duration_s
    spice = ephemeris._ensure_standard_kernels()
    settings = trajectory._create_time_limited_body_settings(
        environment_setup, start_s, end_s,
    )
    trajectory._validate_time_limited_body_settings(settings, start_s, end_s)
    # Include the midpoint and off-grid samples even for a whole-day interval.
    fractions = np.unique(np.append(np.linspace(0.0, 1.0, 34), 0.5))
    epochs_s = start_s + fractions * duration_s
    measurements: dict[str, dict[str, float]] = {}
    for body in trajectory.PHYSICAL_BODY_NAMES:
        bound_budget.check()
        table = environment_setup.create_body_ephemeris(
            settings.get(body).ephemeris_settings, body,
        )
        safe_start_s, safe_end_s = environment_setup.get_safe_interpolation_interval(table)
        assert safe_start_s <= start_s < end_s <= safe_end_s
        assert table.frame_origin == "SSB" and table.frame_orientation == "J2000"
        direct = np.asarray([
            spice.get_body_cartesian_state_at_epoch(body, "SSB", "J2000", "NONE", epoch)
            for epoch in epochs_s
        ]).reshape(-1, 6)
        native = np.asarray([table.cartesian_state(epoch) for epoch in epochs_s]).reshape(-1, 6)
        assert np.all(np.isfinite(direct)) and np.all(np.isfinite(native))
        errors = native - direct
        position_error_m = float(np.max(np.linalg.norm(errors[:, :3], axis=1)))
        velocity_error_m_s = float(np.max(np.linalg.norm(errors[:, 3:], axis=1)))
        assert position_error_m <= 0.025, (phase, duration_s, body, position_error_m)
        assert velocity_error_m_s <= 2.5e-6, (phase, duration_s, body, velocity_error_m_s)
        # Subtract the first position before forming the chord to reduce SSB cancellation.
        direct_offsets = direct[:, :3] - direct[0, :3]
        native_offsets = native[:, :3] - native[0, :3]
        direct_defect = direct_offsets - fractions[:, None] * direct_offsets[-1]
        native_defect = native_offsets - fractions[:, None] * native_offsets[-1]
        # Each chord is a convex combination of its two endpoints. The difference
        # in the two defects is therefore <= twice the input position allowance.
        assert np.max(np.linalg.norm(native_defect - direct_defect, axis=1)) <= 2 * 0.025
        direct_deviation_m = float(np.max(np.linalg.norm(direct_defect, axis=1)))
        if body in {"Earth", "Moon", "Mars"} and duration_s >= 300.0:
            assert direct_deviation_m > 1.0
        measurements[body] = {
            "sampled_direct_chord_deviation_m": direct_deviation_m,
            "sampled_native_chord_deviation_m": float(np.max(
                np.linalg.norm(native_defect, axis=1),
            )),
            "sampled_position_error_m": position_error_m,
            "sampled_velocity_error_m_s": velocity_error_m_s,
        }
        if body in {"Moon", "Mars"} and duration_s >= 1800.0:
            cell_count = int(duration_s / trajectory.EPHEMERIS_TIME_STEP_S)
            assert cell_count in {6, 288}
            nodes_s = [start_s + index * trajectory.EPHEMERIS_TIME_STEP_S
                       for index in range(-2, cell_count + 3)]
            node_states_si = np.asarray([
                spice.get_body_cartesian_state_at_epoch(body, "SSB", "J2000", "NONE", epoch)
                for epoch in nodes_s
            ]).reshape(-1, 6)
            node_positions_m = tuple((float(row[0]), float(row[1]), float(row[2]))
                                     for row in node_states_si)
            helper_started_s = time.perf_counter()
            local_bounds_m = tuple(trajectory._ephemeris_cell_chord_bound(
                bound_budget, tuple(nodes_s[index:index + 6]), node_positions_m[index:index + 6],
                nodes_s[index + 2], nodes_s[index + 3],
            ) for index in range(cell_count))
            composed_bound_m = trajectory._compose_ephemeris_chord_bounds(
                bound_budget, tuple(nodes_s[2:cell_count + 3]),
                node_positions_m[2:cell_count + 3], local_bounds_m,
            )
            helper_elapsed_s = time.perf_counter() - helper_started_s
            polynomial_states_si = []
            for epoch in epochs_s:
                index = min(cell_count - 1, int((epoch - start_s) / trajectory.EPHEMERIS_TIME_STEP_S))
                polynomial_states_si.append(_rational_lagrange_state(
                    nodes_s[index:index + 6], node_states_si[index:index + 6], float(epoch),
                ))
            polynomial_errors_si = native - np.asarray(polynomial_states_si)
            polynomial_position_error_m = float(np.max(np.linalg.norm(polynomial_errors_si[:, :3], axis=1)))
            polynomial_velocity_error_m_s = float(np.max(np.linalg.norm(polynomial_errors_si[:, 3:], axis=1)))
            assert polynomial_position_error_m <= 0.025, (phase, body, polynomial_position_error_m)
            assert polynomial_velocity_error_m_s <= 2.5e-6, (phase, body, polynomial_velocity_error_m_s)
            native_deviation_m = float(np.max(np.linalg.norm(native_defect, axis=1)))
            assert native_deviation_m <= composed_bound_m + 2 * 0.025
            measurements[body].update({
                "cell_count": cell_count, "bound_helper_calls": cell_count + 1,
                "composed_polynomial_chord_bound_m": composed_bound_m,
                "sampled_polynomial_position_error_m": polynomial_position_error_m,
                "sampled_polynomial_velocity_error_m_s": polynomial_velocity_error_m_s,
                "bound_helpers_only_elapsed_s": helper_elapsed_s,
            })
    bound_budget.check()
    assert (bound_budget.control_attempts, bound_budget.propagation_evaluations,
            bound_budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({
        "candidate_id": evidence["candidate_id"], "phase": phase,
        "start_tdb_s": start_s, "duration_s": duration_s, "sample_count": len(fractions),
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB seconds since J2000",
        "scope": "Sampled motion and conditional exact-polynomial enclosures; "
                 "not uniform native/SPICE error or trajectory safety bounds",
        "measurements": measurements,
    }, sort_keys=True, allow_nan=False))


def test_full_candidate_interpolation_against_direct_spice() -> None:
    """Qualify SI/SSB/J2000 states, not propagated trajectory accuracy."""
    import tudatpy
    from tudatpy.dynamics import environment_setup

    scenario = load_scenario(ROOT / "examples/m3_feasible_mission.toml")
    candidate = next(
        item
        for item in search_impulsive_transfers(scenario).pareto_front
        if item.candidate_id == "d0001-t0035"
    )
    start = candidate.departure_epoch_tdb_s
    end = candidate.arrival_epoch_tdb_s
    cell_budget = trajectory._RefinementBudget(candidate.candidate_id, 300.0)
    cell_measurements: dict[str, dict[str, float | int]] = {}
    # Offset interior samples from both 300 s and 150 s grids; include arc edges.
    epochs = sorted(
        {start, start + 0.125, start + 75.25, end - 75.25, end - 0.125, end}
        | {
            start + ((end - start) * index / 33 // 300) * 300 + 37.125
            for index in range(1, 33)
        }
    )
    settings = trajectory._create_time_limited_body_settings(
        environment_setup, start, end
    )
    trajectory._validate_time_limited_body_settings(settings, start, end)
    with pytest.raises(ValueError, match="do not cover"):
        trajectory._validate_time_limited_body_settings(settings, start - 86400.0, end)
    with pytest.raises(ValueError, match="do not cover"):
        trajectory._validate_time_limited_body_settings(settings, start, end + 86400.0)
    dense_settings = environment_setup.get_default_body_settings_time_limited(
        trajectory.PHYSICAL_BODY_NAMES,
        start,
        end,
        "SSB",
        "J2000",
        150.0,
    )
    spice = ephemeris._ensure_standard_kernels()
    errors: dict[str, dict[str, list[float]]] = {}
    for body in trajectory.PHYSICAL_BODY_NAMES:
        cell_budget.check()
        nominal = environment_setup.create_body_ephemeris(
            settings.get(body).ephemeris_settings, body
        )
        dense = environment_setup.create_body_ephemeris(
            dense_settings.get(body).ephemeris_settings, body
        )
        for table in (nominal, dense):
            safe_start, safe_end = environment_setup.get_safe_interpolation_interval(
                table
            )
            assert safe_start <= start < end <= safe_end
            assert table.frame_origin == "SSB" and table.frame_orientation == "J2000"
        differences: dict[str, list[list[float]]] = {
            "300s_direct": [],
            "150s_direct": [],
            "300s_150s": [],
            "300s_rational_polynomial": [],
            "300s_cell_rational": [],
            "300s_source_replay": [],
        }
        replay_exact_matches = 0
        roundoff_envelopes_si: list[list[float]] = []
        bounds_m: list[float] = []
        midpoint_defects_m: list[float] = []
        helper_elapsed_s = 0.0
        body_settings = settings.get(body).ephemeris_settings
        grid_start_s = body_settings.initial_time
        step_s = body_settings.time_step
        for epoch in epochs:
            direct = np.asarray(
                spice.get_body_cartesian_state_at_epoch(
                    body, "SSB", "J2000", "NONE", epoch
                )
            ).reshape(6)
            coarse = np.asarray(nominal.cartesian_state(epoch)).reshape(6)
            fine = np.asarray(dense.cartesian_state(epoch)).reshape(6)
            lower_index = math.floor((epoch - grid_start_s) / step_s)
            # Native six-stage interior window: two knots before the lower knot,
            # that knot, and three after it. Never reconstruct a boundary spline.
            nodes_tdb_s = [grid_start_s + index * step_s
                           for index in range(lower_index - 2, lower_index + 4)]
            assert grid_start_s < nodes_tdb_s[0] < nodes_tdb_s[-1] < body_settings.final_time
            node_states_si = np.asarray([
                spice.get_body_cartesian_state_at_epoch(body, "SSB", "J2000", "NONE", node)
                for node in nodes_tdb_s
            ]).reshape(6, 6)
            _assert_pinned_state_range(node_states_si)
            rational_state_si = _rational_lagrange_state(nodes_tdb_s, node_states_si, epoch)
            replay_state_si = _replay_lagrange_state(nodes_tdb_s, node_states_si, epoch)
            replay_exact_matches += int(np.array_equal(coarse, replay_state_si))
            unit = Fraction(1, 2 ** 53)
            envelope_si = [16 * unit / (1 - 16 * unit) * Fraction(89, 64)
                           * max(abs(Fraction(float(value))) for value in column)
                           for column in node_states_si.T]
            for actual, oracle, envelope in zip(coarse, rational_state_si, envelope_si):
                assert abs(Fraction(float(actual)) - Fraction(float(oracle))) <= envelope
            roundoff_envelopes_si.append([
                math.nextafter(float(sum(envelope_si[:3])), math.inf),
                math.nextafter(float(sum(envelope_si[3:])), math.inf),
            ])
            cell_start_s, cell_end_s = nodes_tdb_s[2:4]
            positions_m = tuple((float(row[0]), float(row[1]), float(row[2])) for row in node_states_si)
            helper_started_s = time.perf_counter()
            bound_m = trajectory._ephemeris_cell_chord_bound(
                cell_budget, tuple(nodes_tdb_s), positions_m, cell_start_s, cell_end_s,
            )
            helper_elapsed_s += time.perf_counter() - helper_started_s
            midpoint_s = cell_start_s + (cell_end_s - cell_start_s) / 2
            native_cell_si = np.asarray([
                nominal.cartesian_state(tdb_s) for tdb_s in (cell_start_s, midpoint_s, cell_end_s)
            ]).reshape(3, 6)
            rational_midpoint_si = _rational_lagrange_state(nodes_tdb_s, node_states_si, midpoint_s)
            for native_si, polynomial_si in zip(
                native_cell_si, (node_states_si[2], rational_midpoint_si, node_states_si[3]),
            ):
                difference_si = native_si - polynomial_si
                assert np.all(np.isfinite(difference_si))
                differences["300s_cell_rational"].append([
                    float(np.linalg.norm(difference_si[:3])),
                    float(np.linalg.norm(difference_si[3:])),
                ])
            # The two sampled errors are midpoint error and convex endpoint-chord
            # error. Their allowance does not establish uniform native accuracy.
            defect_m = float(np.linalg.norm(
                (native_cell_si[1, :3] - native_cell_si[0, :3])
                - 0.5 * (native_cell_si[2, :3] - native_cell_si[0, :3]),
            ))
            assert defect_m <= bound_m + 2 * 0.025, (body, midpoint_s, defect_m, bound_m)
            bounds_m.append(bound_m)
            midpoint_defects_m.append(defect_m)
            cell_budget.check()
            for label, difference in (
                ("300s_direct", coarse - direct),
                ("150s_direct", fine - direct),
                ("300s_150s", coarse - fine),
                ("300s_rational_polynomial", coarse - rational_state_si),
                ("300s_source_replay", coarse - replay_state_si),
            ):
                assert np.all(np.isfinite(difference))
                differences[label].append(
                    [
                        float(np.linalg.norm(difference[:3])),
                        float(np.linalg.norm(difference[3:])),
                    ]
                )
        errors[body] = {
            label: np.max(values, axis=0).tolist()
            for label, values in differences.items()
        }
        for position_m, velocity_m_s in errors[body].values():
            assert position_m <= 0.025, (body, errors[body])
            assert velocity_m_s <= 2.5e-6, (body, errors[body])
        cell_measurements[body] = {
            "cell_requests": len(bounds_m),
            "source_replay_exact_state_matches": replay_exact_matches,
            "state_arithmetic_range_cell_requests": len(bounds_m),
            "max_conditional_roundoff_envelope_position_m": max(row[0] for row in roundoff_envelopes_si),
            "max_conditional_roundoff_envelope_velocity_m_s": max(row[1] for row in roundoff_envelopes_si),
            "max_polynomial_chord_bound_m": max(bounds_m),
            "max_sampled_native_midpoint_chord_deviation_m": max(midpoint_defects_m),
            "helper_only_elapsed_s": helper_elapsed_s,
        }
        del nominal, dense
    cell_budget.check()
    assert sum(item["cell_requests"] for item in cell_measurements.values()) == 304
    assert (cell_budget.control_attempts, cell_budget.propagation_evaluations,
            cell_budget.native_arc_propagations) == (0, 0, 0)
    print(
        json.dumps(
            {
                "candidate_id": candidate.candidate_id,
                "epoch_tdb_s": epochs,
                "error_units": ["m", "m/s"],
                "origin": "SSB",
                "orientation": "J2000",
                "time_scale": "TDB seconds since J2000",
                "interpolation": "Tudat default six-point Lagrange",
                "steps_s": [300.0, 150.0],
                "state_error_limits": {"position_m": 0.025, "velocity_m_s": 2.5e-6},
                "scope": "Sampled input-state qualification, not a bound on propagated trajectory error",
                "python": platform.python_version(),
                "platform": platform.platform(),
                "tudatpy": tudatpy.__version__,
                "numpy": version("numpy"),
                "kernels": ephemeris.kernel_metadata(),
                "max_errors": errors,
                "cell_bound_qualification": cell_measurements,
                "cell_bound_scope": "304 requests include repeated cells; helper-only timings, "
                                    "not native spacecraft counts or full-mission runtime",
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
