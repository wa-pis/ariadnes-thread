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


@pytest.mark.parametrize("duration_s,closed", [(4.0, True), (5.0, False), (6.0, False)])
def test_thrust_domain_requires_mass_as_well_as_position_and_speed(
    duration_s: float, closed: bool,
) -> None:
    budget = trajectory._RefinementBudget("thrust-domain", 300.0)
    # SI control: constant thrust 10 N, consumption 1 kg/s, m0=10 kg,
    # x0=v0=0. Trial domain: |x|<100 m, |v|<20 m/s, m>5 kg.
    acceleration_m_s2 = 2.0  # T/m <= 2 only while m >= 5 kg.
    reach_m = trajectory._position_reach_upper_bound(budget, duration_s, 0.0, 0.0, acceleration_m_s2)
    speed_upper_m_s = Fraction(acceleration_m_s2) * Fraction(duration_s)
    mass_floor_kg = trajectory._mass_lower_bound(budget, 10.0, 0.0, 1.0, duration_s)
    assert reach_m < 100 and speed_upper_m_s < 20  # These alone accept all three.
    assert (reach_m < 100 and speed_upper_m_s < 20 and mass_floor_kg > 5) is closed
    exact_final_mass_kg = 10 - Fraction(duration_s)
    assert Fraction(mass_floor_kg) == exact_final_mass_kg
    # Independent global bound: monotone mass gives a <= T/m(h) over [0,h].
    # It proves that actual position/speed stay inside their trial domains
    # even in the counterexample where the assumed 2 m/s^2 bound is false.
    actual_acceleration_upper = Fraction(10) / exact_final_mass_kg
    assert actual_acceleration_upper * Fraction(duration_s) < 20
    assert actual_acceleration_upper * Fraction(duration_s)**2 / 2 < 100
    if closed:
        assert actual_acceleration_upper < Fraction(acceleration_m_s2)
    elif duration_s == 5.0:
        assert mass_floor_kg == 5  # Strict first-exit proof is unresolved at equality.
        assert actual_acceleration_upper == Fraction(acceleration_m_s2)
    else:
        assert mass_floor_kg < 5
        assert actual_acceleration_upper > Fraction(acceleration_m_s2)
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)


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
