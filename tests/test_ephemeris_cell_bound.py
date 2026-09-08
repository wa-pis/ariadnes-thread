from __future__ import annotations

from fractions import Fraction
import math

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


NODES_TDB_S = (-2.0, -1.0, 0.0, 1.0, 2.0, 3.0)


@pytest.mark.parametrize("degree", range(6))
@pytest.mark.parametrize("step_s", [1.0, 300.0])
def test_cell_bound_matches_exact_monomial_bernstein_hull(degree: int, step_s: float) -> None:
    positions_m = tuple((t ** degree, -2 * t ** degree, 3 * t ** degree) for t in NODES_TDB_S)
    budget = trajectory._RefinementBudget("cell", 300.0, lambda: 0.0)
    actual_m = trajectory._ephemeris_cell_chord_bound(
        budget, tuple(t * step_s for t in NODES_TDB_S), positions_m, 0.0, step_s,
    )
    if degree < 2:
        assert actual_m == 0.0
    else:
        exact_m = 6 * max(
            Fraction(k, 5) - Fraction(math.comb(k, degree), math.comb(5, degree))
            for k in range(6)
        )
        assert actual_m == math.nextafter(float(exact_m), math.inf)
        assert Fraction(actual_m) >= exact_m
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (0, 0, 0)
    assert budget.deadline_monotonic_s == 300.0


def test_cell_bound_scales_subinterval_and_cancels_ssb_translation() -> None:
    positions_m = tuple((t * t, -2 * t * t, 3 * t * t) for t in NODES_TDB_S)
    translated_m = tuple((x + 2 ** 40, y - 2 ** 41, z + 2 ** 42) for x, y, z in positions_m)
    budget = trajectory._RefinementBudget("cell", 300.0)
    for start_s, end_s in ((0.0, 1.0), (0.0, 0.5), (0.25, 0.75)):
        bound_m = trajectory._ephemeris_cell_chord_bound(
            budget, NODES_TDB_S, positions_m, start_s, end_s,
        )
        exact_m = Fraction(9, 5) * Fraction(end_s - start_s) ** 2
        assert bound_m == math.nextafter(float(exact_m), math.inf)
        assert trajectory._ephemeris_cell_chord_bound(
            budget, NODES_TDB_S, translated_m, start_s, end_s,
        ) == bound_m


def test_cell_bound_encloses_independent_rational_lagrange_defects() -> None:
    epochs_s = (-3.0, -1.0, 0.0, 1.0, 2.0, 4.0)
    positions_m = ((3.0, -1.0, 9.0), (-2.0, 7.0, 2.0), (0.0, 2.0, -3.0),
                   (5.0, -4.0, 1.0), (8.0, 1.0, -7.0), (-3.0, 9.0, 2.0))
    bound_m = trajectory._ephemeris_cell_chord_bound(
        trajectory._RefinementBudget("cell", 300.0), epochs_s, positions_m, 0.0, 1.0,
    )
    for index in range(33):
        u = Fraction(index, 32)
        # Keep the oracle rational, including nodes: no mixed float arithmetic.
        weights = [math.prod((u - Fraction(other)) / (Fraction(node) - Fraction(other))
                             for j, other in enumerate(epochs_s) if i != j)
                   for i, node in enumerate(epochs_s)]
        defect_m = [sum(weight * Fraction(position[axis])
                        for weight, position in zip(weights, positions_m))
                    - (1 - u) * Fraction(positions_m[2][axis])
                    - u * Fraction(positions_m[3][axis]) for axis in range(3)]
        assert sum(value * value for value in defect_m) <= Fraction(bound_m) ** 2


@pytest.mark.parametrize("case", [
    "few_epochs", "few_positions", "position_dimension", "duplicate_epoch",
    "reversed_epochs", "nan_epoch", "infinite_position", "boolean_position",
    "boolean_start", "zero_interval", "reverse_interval", "cross_left", "cross_right",
])
def test_cell_bound_rejects_invalid_inputs(case: str) -> None:
    epochs_s = NODES_TDB_S
    positions_m = tuple((t * t, 0.0, 0.0) for t in epochs_s)
    start_s, end_s = 0.0, 1.0
    if case == "few_epochs":
        epochs_s = epochs_s[:-1]
    elif case == "few_positions":
        positions_m = positions_m[:-1]
    elif case == "position_dimension":
        positions_m = ((0.0, 0.0),) + positions_m[1:]  # type: ignore[assignment]  # Invalid shape.
    elif case == "duplicate_epoch":
        epochs_s = epochs_s[:1] + epochs_s
        epochs_s = epochs_s[:6]
    elif case == "reversed_epochs":
        epochs_s = tuple(reversed(epochs_s))
    elif case == "nan_epoch":
        epochs_s = (math.nan,) + epochs_s[1:]
    elif case in {"infinite_position", "boolean_position"}:
        positions_m = ((math.inf if case == "infinite_position" else True, 0.0, 0.0),) + positions_m[1:]
    elif case == "boolean_start":
        start_s = False
    elif case == "zero_interval":
        end_s = start_s
    elif case == "reverse_interval":
        start_s, end_s = 1.0, 0.0
    elif case == "cross_left":
        start_s = -0.001
    elif case == "cross_right":
        end_s = 1.001
    with pytest.raises(TrajectoryRefinementError, match="ephemeris-cell-bound") as caught:
        trajectory._ephemeris_cell_chord_bound(
            trajectory._RefinementBudget("cell", 300.0), epochs_s, positions_m, start_s, end_s,
        )
    assert caught.value.__cause__ is not None


def test_cell_bound_preserves_positive_subnormal_and_rejects_overflow() -> None:
    budget = trajectory._RefinementBudget("cell", 300.0)
    tiny_m = math.ulp(0.0)
    positions_m = tuple((t * t * tiny_m, 0.0, 0.0) for t in NODES_TDB_S)
    bound_m = trajectory._ephemeris_cell_chord_bound(budget, NODES_TDB_S, positions_m, 0.0, 1.0)
    assert Fraction(bound_m) >= Fraction(3, 10) * Fraction(tiny_m) > 0
    amplitude_m = 1.7e308
    huge_positions_m = tuple((sign * amplitude_m,) * 3 for sign in (1, -1, 1, 1, -1, 1))
    # At u=1/2 the exact six-node weights are (3,-25,150,150,-25,3)/256.
    # The L1 chord defect alone is 75/64 times the amplitude, beyond float max.
    assert Fraction(75, 64) * Fraction(amplitude_m) > Fraction(math.nextafter(math.inf, 0.0))
    with pytest.raises(TrajectoryRefinementError, match="ephemeris-cell-bound"):
        trajectory._ephemeris_cell_chord_bound(budget, NODES_TDB_S, huge_positions_m, 0.0, 1.0)


@pytest.mark.parametrize("expiry_check", [1, 3, 9, 14])
def test_cell_bound_checks_shared_deadline_without_propagation(expiry_check: int) -> None:
    clock = iter([0.0] * expiry_check + [300.0])
    budget = trajectory._RefinementBudget("cell", 300.0, lambda: next(clock))
    with pytest.raises(TrajectoryRefinementError, match="shared deadline"):
        trajectory._ephemeris_cell_chord_bound(
            budget, NODES_TDB_S, tuple((t * t, 0.0, 0.0) for t in NODES_TDB_S), 0.0, 1.0,
        )
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (0, 0, 0)


@pytest.mark.parametrize("offset_m", [0.0, 2.0 ** 40])
def test_chord_composition_handles_corner_and_unequal_durations(offset_m: float) -> None:
    budget = trajectory._RefinementBudget("compose", 300.0, lambda: 0.0)
    budget.begin_control()
    budget.begin_arc(first_in_evaluation=True)
    epochs_s = (0.0, 1.0, 4.0)
    positions_m = ((offset_m, 0.0, 0.0), (offset_m + 2.0, 1.0, 0.0),
                   (offset_m + 8.0, 0.0, 0.0))
    actual_m = trajectory._compose_ephemeris_chord_bounds(budget, epochs_s, positions_m, (0.1, 0.2))
    exact_m = Fraction(1) + Fraction(0.2)
    assert actual_m == math.nextafter(float(exact_m), math.inf)
    assert Fraction(actual_m) >= exact_m
    # Zero cell curvature still leaves the one-metre corner, not zero deviation.
    assert trajectory._compose_ephemeris_chord_bounds(
        budget, epochs_s, positions_m, (0.0, 0.0),
    ) == math.nextafter(1.0, math.inf)
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (1, 1, 1)
    assert budget.deadline_monotonic_s == 300.0


def test_chord_composition_handles_affine_single_cell_and_local_pairing() -> None:
    budget = trajectory._RefinementBudget("compose", 300.0)
    assert trajectory._compose_ephemeris_chord_bounds(
        budget, (0.0, 1.0, 4.0), ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (8.0, 0.0, 0.0)),
        (0.0, 0.0),
    ) == 0.0
    assert trajectory._compose_ephemeris_chord_bounds(
        budget, (0.0, 1.0), ((0.0, 0.0, 0.0), (2.0, 1.0, 0.0)), (0.25,),
    ) == math.nextafter(0.25, math.inf)
    # The largest local bound is away from the five-metre corner: max is 10, not 15.
    assert trajectory._compose_ephemeris_chord_bounds(
        budget, (0.0, 1.0, 2.0, 3.0),
        ((0.0, 0.0, 0.0), (0.0, 5.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        (0.0, 0.0, 10.0),
    ) == math.nextafter(10.0, math.inf)


def test_composed_cell_bounds_cover_polynomial_derivative_jump() -> None:
    budget = trajectory._RefinementBudget("compose", 300.0)
    local_bounds_m = []
    for start_s in (0.0, 1.0):
        nodes_s = tuple(t + start_s for t in NODES_TDB_S)
        local_bounds_m.append(trajectory._ephemeris_cell_chord_bound(
            budget, nodes_s, tuple((t ** 6, 0.0, 0.0) for t in nodes_s), start_s, start_s + 1.0,
        ))
    bound_m = trajectory._compose_ephemeris_chord_bounds(
        budget, (0.0, 1.0, 2.0), ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (64.0, 0.0, 0.0)),
        tuple(local_bounds_m),
    )
    # Closed remainder oracle, including both sides of the derivative jump at t=1.
    for index in range(65):
        t = Fraction(index, 32)
        nodes = range(-2, 4) if t <= 1 else range(-1, 5)
        position_m = t ** 6 - math.prod(t - node for node in nodes)
        assert abs(position_m - 32 * t) <= Fraction(bound_m)


@pytest.mark.parametrize("case", [
    "one_knot", "position_count", "bound_count", "duplicate", "reverse", "nan_time",
    "bad_position", "boolean_position", "negative_bound", "boolean_bound", "infinite_bound",
])
def test_chord_composition_rejects_invalid_inputs(case: str) -> None:
    epochs_s = (0.0, 1.0, 2.0)
    positions_m = ((0.0, 0.0, 0.0),) * 3
    bounds_m = (0.0, 0.0)
    if case == "one_knot":
        epochs_s, positions_m, bounds_m = epochs_s[:1], positions_m[:1], ()
    elif case == "position_count":
        positions_m = positions_m[:2]
    elif case == "bound_count":
        bounds_m = bounds_m[:1]
    elif case == "duplicate":
        epochs_s = (0.0, 0.0, 2.0)
    elif case == "reverse":
        epochs_s = tuple(reversed(epochs_s))
    elif case == "nan_time":
        epochs_s = (0.0, math.nan, 2.0)
    elif case in {"bad_position", "boolean_position"}:
        positions_m = ((math.inf if case == "bad_position" else True, 0.0, 0.0),) * 3
    elif case == "negative_bound":
        bounds_m = (-1.0, 0.0)
    elif case == "boolean_bound":
        bounds_m = (False, 0.0)
    elif case == "infinite_bound":
        bounds_m = (math.inf, 0.0)
    with pytest.raises(TrajectoryRefinementError, match="ephemeris-chord-composition") as caught:
        trajectory._compose_ephemeris_chord_bounds(
            trajectory._RefinementBudget("compose", 300.0), epochs_s, positions_m, bounds_m,
        )
    assert caught.value.__cause__ is not None


def test_chord_composition_preserves_subnormal_and_rejects_overflow() -> None:
    budget = trajectory._RefinementBudget("compose", 300.0)
    for amplitude_m in (math.ulp(0.0), 1e308):
        positions_m = ((0.0, 0.0, 0.0), (amplitude_m,) * 3, (0.0, 0.0, 0.0))
        if amplitude_m < 1.0:
            actual_m = trajectory._compose_ephemeris_chord_bounds(
                budget, (0.0, 1.0, 2.0), positions_m, (0.0, 0.0),
            )
            assert Fraction(actual_m) >= 3 * Fraction(amplitude_m) > 0
        else:
            with pytest.raises(TrajectoryRefinementError, match="ephemeris-chord-composition"):
                trajectory._compose_ephemeris_chord_bounds(
                    budget, (0.0, 1.0, 2.0), positions_m, (0.0, 0.0),
                )


@pytest.mark.parametrize("expiry_check", [1, 3, 6, 9, 10])
def test_chord_composition_checks_deadline_throughout(expiry_check: int) -> None:
    clock = iter([0.0] * expiry_check + [300.0])
    budget = trajectory._RefinementBudget("compose", 300.0, lambda: next(clock))
    with pytest.raises(TrajectoryRefinementError, match="shared deadline"):
        trajectory._compose_ephemeris_chord_bounds(
            budget, (0.0, 1.0, 2.0), ((0.0, 0.0, 0.0),) * 3, (0.0, 0.0),
        )
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (0, 0, 0)
