"""Exact geometry controls for conditional interval separation bounds."""

from decimal import Inexact, ROUND_CEILING, localcontext
from fractions import Fraction
import math

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


@pytest.mark.parametrize("duration_s,expected_inclusion", [(0.1, True), (0.25, False), (0.75, False)])
def test_velocity_domain_is_required_for_velocity_dependent_force(
    duration_s: float, expected_inclusion: bool,
) -> None:
    budget = trajectory._RefinementBudget("phase-domain-control", 300.0)
    # SI control: x'=v, v'=k*v^2, k=1/m, x(0)=0 m, v(0)=1 m/s.
    # Exact solution: v=1/(1-t), x=-log(1-t), with t in seconds, t<1.
    position_domain_m, speed_domain_m_s = 2.0, 2.0
    acceleration_bound_m_s2 = 4.0  # Valid only while |v|<=2 m/s.
    reach_m = trajectory._position_reach_upper_bound(
        budget, duration_s, 0.0, 1.0, acceleration_bound_m_s2,
    )
    speed_upper_m_s = Fraction(1) + Fraction(acceleration_bound_m_s2) * Fraction(duration_s)
    assert reach_m < position_domain_m  # Position alone would accept every case.
    assert (reach_m < position_domain_m and speed_upper_m_s < Fraction(speed_domain_m_s)) is expected_inclusion
    end_velocity_m_s = 1 / (1 - Fraction(duration_s))
    end_position_m = -math.log1p(-duration_s)
    assert 0 < end_position_m < position_domain_m
    if expected_inclusion:
        for i in range(101):
            t_s = Fraction(duration_s) * i / 100
            assert 1 / (1 - t_s) <= speed_upper_m_s < Fraction(speed_domain_m_s)
            assert -math.log1p(-float(t_s)) <= reach_m
    elif duration_s == 0.25:
        assert speed_upper_m_s == Fraction(speed_domain_m_s)
        assert end_velocity_m_s < Fraction(speed_domain_m_s)  # Unresolved is not actual exit.
    else:
        assert end_velocity_m_s > Fraction(speed_domain_m_s)
        assert end_velocity_m_s ** 2 > Fraction(acceleration_bound_m_s2)
        # At 0.75 s the position box still contains x, but its assumed force bound is false.
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)


@pytest.mark.parametrize("duration_s,expected_inclusion", [(0.05, True), (1.0, False)])
@pytest.mark.parametrize("body_reach_m", [0.0, 0.25])
def test_first_exit_domain_closes_only_for_short_circular_control(
    duration_s: float, expected_inclusion: bool, body_reach_m: float,
) -> None:
    budget = trajectory._RefinementBudget("first-exit-control", 300.0)
    domain_radius_m = 1.0
    floor_m = trajectory._relative_distance_lower_bound(
        budget, (10.0, 0.0, 0.0), (0.0,) * 3, domain_radius_m, body_reach_m,
    )
    assert 0 < floor_m <= 9 - body_reach_m
    bound_m_s2 = trajectory._harmonic_acceleration_upper_bound(
        budget.candidate_id, 1000.0, 10.0, floor_m, ((1.0,),), ((0.0,),),
    )
    exact_domain_max_m_s2 = Fraction(1000) / (Fraction(9) - Fraction(body_reach_m)) ** 2
    assert Fraction(bound_m_s2) >= exact_domain_max_m_s2 > 10
    # Acceleration at the anchor (10 m/s^2) is not a bound on its 1 m domain.
    reach_m = trajectory._position_reach_upper_bound(budget, duration_s, 0.0, 10.0, bound_m_s2)
    assert (reach_m < domain_radius_m) is expected_inclusion
    # Independent exact solution: GM=1000, r=10, omega=1 rad/s, speed=10 m/s.
    for i in range(101):
        t_s = duration_s * i / 100
        displacement_m = 20 * abs(math.sin(t_s / 2))
        cartesian_displacement_m = math.hypot(10 * math.cos(t_s) - 10, 10 * math.sin(t_s))
        assert abs(displacement_m - cartesian_displacement_m) <= 1e-12  # m
        assert displacement_m <= reach_m
        if expected_inclusion:
            assert displacement_m < domain_radius_m
    if not expected_inclusion:
        assert 20 * math.sin(duration_s / 2) > domain_radius_m
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)


def test_first_exit_control_rejects_domain_containing_force_singularity() -> None:
    budget = trajectory._RefinementBudget("first-exit-control", 300.0)
    floor_m = trajectory._relative_distance_lower_bound(
        budget, (10.0, 0.0, 0.0), (0.0,) * 3, 11.0, 0.0,
    )
    assert floor_m < 0
    with pytest.raises(TrajectoryRefinementError, match="minimum_distance_m"):
        trajectory._harmonic_acceleration_upper_bound(
            budget.candidate_id, 1000.0, 10.0, floor_m, ((1.0,),), ((0.0,),),
        )


def test_first_exit_strict_inclusion_does_not_accept_equality() -> None:
    budget = trajectory._RefinementBudget("first-exit-control", 300.0)
    for duration_s in (math.nextafter(1.0, 0.0), 1.0):
        reach_m = trajectory._position_reach_upper_bound(budget, duration_s, 0.0, 1.0, 0.0)
        assert reach_m == duration_s
        assert (reach_m < 1.0) is (duration_s < 1.0)


@pytest.mark.parametrize("values", [
    (0.0, 0.0, 0.0, 0.0), (0.0, 0.1, 1e300, 1e300),
    (2.0, 0.0, 3.0, 0.0), (2.0, 0.0, 0.0, 4.0),
    (0.1, 0.2, 0.3, 0.4), (1e-300, 0.0, 1e-300, 0.0),
])
def test_position_reach_matches_exact_kinematics(values: tuple[float, float, float, float]) -> None:
    budget = trajectory._RefinementBudget("reach-bound", 300.0)
    result = trajectory._position_reach_upper_bound(budget, *values)
    h, error, speed, acceleration = map(Fraction, values)
    exact_m = error + speed * h + acceleration * h ** 2 / 2
    assert Fraction(result) >= exact_m
    if exact_m == 0:
        assert result == 0.0
    else:
        assert Fraction(math.nextafter(result, -math.inf)) <= exact_m
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)


def test_position_reach_composes_with_distance_floor_on_exact_motion() -> None:
    budget = trajectory._RefinementBudget("reach-bound", 300.0)
    # x_ship(t)=10-t-t^2; x_body(t)=t for 0<=t<=1, so minimum distance is 7 m.
    ship_reach_m = trajectory._position_reach_upper_bound(budget, 1.0, 0.0, 1.0, 2.0)
    body_reach_m = trajectory._position_reach_upper_bound(budget, 1.0, 0.0, 1.0, 0.0)
    floor_m = trajectory._relative_distance_lower_bound(
        budget, (10.0, 0.0, 0.0), (0.0,) * 3, ship_reach_m, body_reach_m,
    )
    assert 0 <= 7 - Fraction(floor_m) <= Fraction("1e-13")  # m
    for i in range(101):
        t = Fraction(i, 100)
        assert Fraction(floor_m) <= 10 - 2 * t - t * t
    assert floor_m > 6.0 and floor_m <= 8.0  # No clearance claim for an 8 m guard.


@pytest.mark.parametrize("field", range(4))
@pytest.mark.parametrize("value", [-1.0, True, math.nan, math.inf])
def test_position_reach_rejects_invalid_input(field: int, value: float) -> None:
    values = [1.0, 0.0, 1.0, 1.0]
    values[field] = value
    with pytest.raises(TrajectoryRefinementError, match="position-reach-bound") as caught:
        trajectory._position_reach_upper_bound(trajectory._RefinementBudget("reach-bound", 300.0), *values)
    assert caught.value.__cause__ is not None


def test_position_reach_rejects_overflow() -> None:
    with pytest.raises(TrajectoryRefinementError, match="position-reach-bound"):
        trajectory._position_reach_upper_bound(
            trajectory._RefinementBudget("reach-bound", 300.0), 1e300, 0.0, 1.0, 1e300,
        )


@pytest.mark.parametrize("expiry_check", [1, 2])
def test_position_reach_preserves_shared_deadline(expiry_check: int) -> None:
    clock = iter([0.0] * expiry_check + [300.0])
    budget = trajectory._RefinementBudget("reach-bound", 300.0, lambda: next(clock))
    with pytest.raises(TrajectoryRefinementError, match="shared deadline"):
        trajectory._position_reach_upper_bound(budget, 1.0, 0.0, 1.0, 1.0)


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
