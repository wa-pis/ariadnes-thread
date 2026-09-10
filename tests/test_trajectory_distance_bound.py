"""Exact geometry controls for conditional interval separation bounds."""

from decimal import Inexact, ROUND_CEILING, localcontext
from fractions import Fraction
import math

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


@pytest.mark.parametrize("offset", [0.0, 1e12])
@pytest.mark.parametrize("reach", [(0.0, 0.0), (0.1, 0.2), (2.0, 3.0), (4.0, 5.0)])
def test_distance_bound_matches_translated_exact_triangle(
    offset: float, reach: tuple[float, float],
) -> None:
    budget = trajectory._RefinementBudget("distance-bound", 300.0, lambda: 0.0)
    result = trajectory._relative_distance_lower_bound(
        budget, (offset + 3, offset + 4, offset), (offset, offset, offset), *reach,
    )
    exact_m = Fraction(5) - sum((Fraction(value) for value in reach), Fraction(0))
    assert Fraction(result) <= exact_m
    assert 0 <= float(exact_m - Fraction(result)) <= 1e-14  # m
    # Collinear displacements toward one another attain the positive bound.
    if sum(reach) < 5:
        remaining = 1 - sum((Fraction(value) for value in reach), Fraction(0)) / 5
        assert (3 * remaining) ** 2 + (4 * remaining) ** 2 == exact_m ** 2
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)


@pytest.mark.parametrize("scale", [1e-300, 1.0, 1e300])
def test_distance_bound_irrational_norm_is_outward(scale: float) -> None:
    result = trajectory._relative_distance_lower_bound(
        trajectory._RefinementBudget("distance-bound", 300.0),
        (scale, scale, scale), (0.0, 0.0, 0.0), 0.0, 0.0,
    )
    squared_m2 = 3 * Fraction(scale) ** 2
    assert result > 0 and Fraction(result) ** 2 <= squared_m2
    assert Fraction(math.nextafter(math.nextafter(result, math.inf), math.inf)) ** 2 >= squared_m2


def test_distance_bound_preserves_zero_and_overlapping_uncertainty() -> None:
    budget = trajectory._RefinementBudget("distance-bound", 300.0)
    assert trajectory._relative_distance_lower_bound(budget, (0.0,) * 3, (0.0,) * 3, 0.0, 0.0) == 0.0
    assert trajectory._relative_distance_lower_bound(budget, (0.0,) * 3, (0.0,) * 3, 2.0, 3.0) == -5.0


def test_distance_bound_ignores_external_decimal_context() -> None:
    budget = trajectory._RefinementBudget("distance-bound", 300.0)
    args = (budget, (1.0, 2.0, 3.0), (0.0,) * 3, 0.1, 0.2)
    expected = trajectory._relative_distance_lower_bound(*args)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_CEILING
        context.traps[Inexact] = True
        assert trajectory._relative_distance_lower_bound(*args) == expected


@pytest.mark.parametrize("field", ["spacecraft", "body", "spacecraft_reach", "body_reach"])
@pytest.mark.parametrize("value", [True, math.nan, math.inf])
def test_distance_bound_rejects_invalid_values(field: str, value: float) -> None:
    spacecraft = (value, 0.0, 0.0) if field == "spacecraft" else (3.0, 4.0, 0.0)
    body = (value, 0.0, 0.0) if field == "body" else (0.0,) * 3
    with pytest.raises(TrajectoryRefinementError, match="relative-distance-bound") as caught:
        trajectory._relative_distance_lower_bound(
            trajectory._RefinementBudget("distance-bound", 300.0), spacecraft, body,
            value if field == "spacecraft_reach" else 0.0,
            value if field == "body_reach" else 0.0,
        )
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize("reach", [(-1.0, 0.0), (0.0, -1.0)])
def test_distance_bound_rejects_negative_reach(reach: tuple[float, float]) -> None:
    with pytest.raises(TrajectoryRefinementError, match="nonnegative"):
        trajectory._relative_distance_lower_bound(
            trajectory._RefinementBudget("distance-bound", 300.0), (0.0,) * 3, (0.0,) * 3, *reach,
        )


@pytest.mark.parametrize("expiry_check", [1, 2])
def test_distance_bound_preserves_shared_deadline(expiry_check: int) -> None:
    clock = iter([0.0] * expiry_check + [300.0])
    budget = trajectory._RefinementBudget("distance-bound", 300.0, lambda: next(clock))
    with pytest.raises(TrajectoryRefinementError, match="shared deadline"):
        trajectory._relative_distance_lower_bound(budget, (3.0, 4.0, 0.0), (0.0,) * 3, 0.0, 0.0)


def test_distance_bound_rejects_unrepresentable_result() -> None:
    with pytest.raises(TrajectoryRefinementError, match="relative-distance-bound"):
        trajectory._relative_distance_lower_bound(
            trajectory._RefinementBudget("distance-bound", 300.0),
            (1e308,) * 3, (-1e308,) * 3, 0.0, 0.0,
        )
