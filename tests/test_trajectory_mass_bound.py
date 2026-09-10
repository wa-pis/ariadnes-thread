"""Exact controls for a conditional interval mass floor, not native safety."""

from fractions import Fraction
import math

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


@pytest.mark.parametrize("initial,error,rate,duration", [
    (2000.0, 0.0, 1.0, 1000.0),
    (2000.0, 1e-14, 1.0, 1000.0),
    (2000.0, 0.1, 0.3, 100.1),
    (2000.0, 0.1, 0.0, 1000.0),
    (2000.0, 0.1, 1.0, 0.0),
    (1.0, 1.0, 0.0, 1.0),
    (1.0, 1.0, math.ulp(0.0), 0.5),
    (1.0, 2.0, 1.0, 1.0),
])
def test_mass_floor_is_outward_and_tight(
    initial: float, error: float, rate: float, duration: float,
) -> None:
    budget = trajectory._RefinementBudget("mass-bound-control", 300.0)
    result = trajectory._mass_lower_bound(budget, initial, error, rate, duration)
    exact = Fraction(initial) - Fraction(error) - Fraction(rate) * Fraction(duration)
    assert Fraction(result) <= exact < Fraction(math.nextafter(result, math.inf))
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)


@pytest.mark.parametrize("duration_s,clear", [(1.0, True), (2.0, True), (3.0, False)])
def test_mass_floor_encloses_variable_consumption_control(duration_s: float, clear: bool) -> None:
    budget = trajectory._RefinementBudget("mass-bound-control", 300.0)
    # Exact SI control: q(t)=t kg/s on [0,h], m(t)=10-t^2/2 kg.
    # Allow an additional signed mass perturbation bounded by 0.25 kg.
    result = trajectory._mass_lower_bound(budget, 10.0, 0.25, duration_s, duration_s)
    assert (result >= 5.0) is clear
    for index in range(101):
        t_s = Fraction(duration_s) * index / 100
        mass_kg = 10 - t_s**2 / 2 - Fraction(1, 4)
        assert Fraction(result) <= mass_kg
    if not clear:
        assert 10 - Fraction(duration_s)**2 / 2 - Fraction(1, 4) > 5
        # An unresolved conservative floor does not prove dry-mass crossing.


@pytest.mark.parametrize("index", range(4))
@pytest.mark.parametrize("invalid", [-1.0, True, math.nan, math.inf])
def test_mass_floor_rejects_invalid_inputs(index: int, invalid: object) -> None:
    budget = trajectory._RefinementBudget("mass-bound-control", 300.0)
    values = [2000.0, 0.0, 1.0, 1000.0]
    values[index] = invalid  # type: ignore[assignment]  # Deliberate boundary violation.
    with pytest.raises(TrajectoryRefinementError, match="mass-bound") as caught:
        trajectory._mass_lower_bound(budget, *values)
    assert isinstance(caught.value.__cause__, (TypeError, ValueError))


def test_mass_floor_rejects_zero_initial_mass_and_overflow() -> None:
    budget = trajectory._RefinementBudget("mass-bound-control", 300.0)
    for values in ((0.0, 0.0, 0.0, 0.0), (1.0, 0.0, 1e308, 1e308)):
        with pytest.raises(TrajectoryRefinementError, match="mass-bound") as caught:
            trajectory._mass_lower_bound(budget, *values)
        assert caught.value.__cause__ is not None


@pytest.mark.parametrize("expiry_check", [1, 2])
def test_mass_floor_preserves_shared_deadline(expiry_check: int) -> None:
    clock = iter([0.0] * expiry_check + [300.0])
    budget = trajectory._RefinementBudget("mass-bound-control", 300.0, lambda: next(clock))
    with pytest.raises(TrajectoryRefinementError, match="shared deadline"):
        trajectory._mass_lower_bound(budget, 2000.0, 0.0, 1.0, 1000.0)
