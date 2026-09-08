from __future__ import annotations

from decimal import Decimal, Inexact, ROUND_FLOOR, localcontext
from fractions import Fraction
import json
import math
import time

import pytest

from space_nav import trajectory
from space_nav.errors import TrajectoryRefinementError


def test_pinned_harmonic_surface_bounds_are_finite_and_decrease_with_distance() -> None:
    from tudatpy.dynamics import environment_setup

    surfaces = trajectory._build_collision_resource("surface-bound").surfaces
    for spec, path, _ in trajectory._verified_coefficient_files(
        trajectory._default_gravity_models_path(),
    ):
        field = trajectory._load_harmonic_field_settings(environment_setup, spec, path)
        radius_m = next(surface.guard_radius_m for surface in surfaces if surface.body == spec.body)
        started_s = time.monotonic()
        bound_m_s2 = trajectory._harmonic_acceleration_upper_bound(
            "surface-bound", field.gravitational_parameter, field.reference_radius, radius_m,
            field.normalized_cosine_coefficients, field.normalized_sine_coefficients,
        )
        elapsed_s = time.monotonic() - started_s
        distant_bound_m_s2 = trajectory._harmonic_acceleration_upper_bound(
            "surface-bound", field.gravitational_parameter, field.reference_radius, 2 * radius_m,
            field.normalized_cosine_coefficients, field.normalized_sine_coefficients,
        )
        assert math.isfinite(bound_m_s2) and bound_m_s2 > field.gravitational_parameter / radius_m**2
        assert 0 < distant_bound_m_s2 < bound_m_s2 / 4
        print(json.dumps({
            "body": spec.body, "degree": spec.degree, "minimum_distance_m": radius_m,
            "acceleration_upper_bound_m_s2": bound_m_s2, "elapsed_s": elapsed_s,
            "coefficient_sha256": spec.expected_sha256,
            "scope": "Declared finite harmonic field only; not a trajectory safety certificate",
        }, sort_keys=True, allow_nan=False))


def test_monopole_bound_rounds_outward_against_exact_rational_oracle() -> None:
    for gm, radius_m in ((1.0, 3.0), (4.9e12, 1737400.0), (1e-300, 1e100)):
        bound = trajectory._harmonic_acceleration_upper_bound(
            "bound", gm, 1738000.0, radius_m, [[1.0]], [[0.0]],
        )
        exact = Fraction(gm) / Fraction(radius_m)**2
        assert Fraction(bound) >= exact
        assert math.isclose(bound, float(exact), rel_tol=1e-15, abs_tol=5e-324)


def test_harmonic_bound_matches_high_precision_degree_sum_and_scales() -> None:
    cosine = [[1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [-0.001, 0.002, 0.003]]
    sine = [[0.0] * 3, [0.0] * 3, [0.0, -0.004, 0.005]]
    # Independently sum squared binary coefficients exactly, then evaluate the
    # closed degree-0/degree-2 expression with 100-digit arithmetic.
    q2 = sum((Fraction(v)**2 for v in cosine[2] + sine[2]), Fraction(0))
    with localcontext() as context:
        context.prec = 100
        q2_decimal = Decimal(q2.numerator) / Decimal(q2.denominator)
        reference = Decimal(7) / 9 * (1 + Decimal(4) / 9 * 5 * (3 * q2_decimal).sqrt())
    bound = trajectory._harmonic_acceleration_upper_bound("bound", 7.0, 2.0, 3.0, cosine, sine)
    assert Decimal.from_float(bound) >= reference
    assert math.isclose(bound, float(reference), rel_tol=1e-15)
    distant = trajectory._harmonic_acceleration_upper_bound("bound", 7.0, 2.0, 6.0, cosine, sine)
    assert 0.0 < distant < bound / 4.0
    doubled = trajectory._harmonic_acceleration_upper_bound("bound", 14.0, 2.0, 3.0, cosine, sine)
    assert doubled == 2 * bound
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_FLOOR
        context.traps[Inexact] = True
        assert trajectory._harmonic_acceleration_upper_bound(
            "bound", 7.0, 2.0, 3.0, cosine, sine,
        ) == bound


def test_zero_harmonic_field_has_zero_bound() -> None:
    assert trajectory._harmonic_acceleration_upper_bound(
        "bound", 1.0, 2.0, 3.0, [[0.0]], [[0.0]],
    ) == 0.0


@pytest.mark.parametrize("field", ["gm", "radius", "distance"])
@pytest.mark.parametrize("value", [True, 0.0, -1.0, math.nan, math.inf])
def test_harmonic_bound_rejects_invalid_scientific_scalars(field: str, value: float) -> None:
    values = {"gm": 1.0, "radius": 1.0, "distance": 1.0}
    values[field] = value
    with pytest.raises(TrajectoryRefinementError, match="gravity-bound") as caught:
        trajectory._harmonic_acceleration_upper_bound(
            "bound", values["gm"], values["radius"], values["distance"], [[1.0]], [[0.0]],
        )
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize(("cosine", "sine"), [
    ([], []), ([[1.0, 0.0]], [[0.0]]), ([[1.0]], [[0.0, 0.0], [0.0, 0.0]]),
    ([[True]], [[0.0]]), ([[math.nan]], [[0.0]]), ([[1.0]], [[math.inf]]),
    ([[1.0]], [[0.1]]), ([[1.0, 0.1], [0.0, 0.0]], [[0.0, 0.0], [0.0, 0.0]]),
])
def test_harmonic_bound_rejects_invalid_coefficients(
    cosine: list[list[float]], sine: list[list[float]],
) -> None:
    with pytest.raises(TrajectoryRefinementError, match="gravity-bound"):
        trajectory._harmonic_acceleration_upper_bound("bound", 1.0, 1.0, 1.0, cosine, sine)


def test_harmonic_bound_rejects_float_overflow() -> None:
    with pytest.raises(TrajectoryRefinementError, match="upper bound_m_s2"):
        trajectory._harmonic_acceleration_upper_bound(
            "bound", 1e300, 1.0, 1e-100, [[1.0]], [[0.0]],
        )


@pytest.mark.parametrize("thrust_enabled", [False, True])
def test_complete_force_bound_sum_is_outward_and_preserves_work(thrust_enabled: bool) -> None:
    gravity = dict.fromkeys(trajectory.PHYSICAL_BODY_NAMES, 1.0)
    gravity["Sun"] = 1e16
    thrust, srp, relativity = (0.1 if thrust_enabled else 0.0), 0.2, 1e-9
    exact = sum((Fraction(value) for value in (*gravity.values(), thrust, srp, relativity)), Fraction(0))
    budget = trajectory._RefinementBudget("sum-bound", 300.0, lambda: 0.0)
    budget.begin_control()
    budget.begin_arc(first_in_evaluation=True)
    result = trajectory._sum_force_acceleration_bounds(
        budget, gravity, thrust, srp, relativity, thrust_enabled=thrust_enabled,
    )
    assert Fraction(result) >= exact
    assert math.isclose(result, float(exact), rel_tol=1e-15)
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (1, 1, 1)
    assert budget.deadline_monotonic_s == 300.0
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_FLOOR
        context.traps[Inexact] = True
        assert trajectory._sum_force_acceleration_bounds(
            budget, gravity, thrust, srp, relativity, thrust_enabled=thrust_enabled,
        ) == result


@pytest.mark.parametrize("case", ["missing", "extra", "order"])
def test_complete_force_bound_sum_requires_exact_sources(case: str) -> None:
    gravity = dict.fromkeys(trajectory.PHYSICAL_BODY_NAMES, 1.0)
    if case == "missing":
        del gravity["Moon"]
    elif case == "extra":
        gravity["Moon-monopole"] = 1.0
    else:
        gravity = dict(reversed(tuple(gravity.items())))
    with pytest.raises(TrajectoryRefinementError, match="ordered eight bodies"):
        trajectory._sum_force_acceleration_bounds(
            trajectory._RefinementBudget("sum-bound", 300.0), gravity, 1.0, 1.0, 1.0,
            thrust_enabled=True,
        )


@pytest.mark.parametrize("field", ["gravity", "thrust", "srp", "relativity"])
@pytest.mark.parametrize("value", [0.0, -1.0, True, math.nan, math.inf])
def test_complete_force_bound_sum_rejects_invalid_component(field: str, value: float) -> None:
    gravity = dict.fromkeys(trajectory.PHYSICAL_BODY_NAMES, 1.0)
    parts = {"thrust": 1.0, "srp": 1.0, "relativity": 1.0}
    if field == "gravity":
        gravity["Sun"] = value
    else:
        parts[field] = value
    with pytest.raises(TrajectoryRefinementError, match="force-bound-sum") as caught:
        trajectory._sum_force_acceleration_bounds(
            trajectory._RefinementBudget("sum-bound", 300.0), gravity,
            parts["thrust"], parts["srp"], parts["relativity"], thrust_enabled=True,
        )
    assert caught.value.__cause__ is not None


def test_complete_force_bound_sum_rejects_coast_thrust_bad_flag_and_overflow() -> None:
    gravity = dict.fromkeys(trajectory.PHYSICAL_BODY_NAMES, 1.0)
    budget = trajectory._RefinementBudget("sum-bound", 300.0)
    with pytest.raises(TrajectoryRefinementError, match="zero for coast"):
        trajectory._sum_force_acceleration_bounds(budget, gravity, 1.0, 1.0, 1.0, thrust_enabled=False)
    with pytest.raises(TrajectoryRefinementError, match="boolean"):
        trajectory._sum_force_acceleration_bounds(
            budget, gravity, 1.0, 1.0, 1.0,
            thrust_enabled=1,  # type: ignore[arg-type]  # Invalid input probe.
        )
    with pytest.raises(TrajectoryRefinementError, match="total force bound_m_s2"):
        trajectory._sum_force_acceleration_bounds(
            budget, dict.fromkeys(trajectory.PHYSICAL_BODY_NAMES, 1e308), 1.0, 1.0, 1.0,
            thrust_enabled=True,
        )


@pytest.mark.parametrize("expiry_check", [3, 11])
def test_complete_force_bound_sum_rejects_midcollection_and_final_expiry(expiry_check: int) -> None:
    clock = iter([0.0] * expiry_check + [300.0])
    budget = trajectory._RefinementBudget("sum-bound", 300.0, lambda: next(clock))
    with pytest.raises(TrajectoryRefinementError, match="shared deadline"):
        trajectory._sum_force_acceleration_bounds(
            budget, dict.fromkeys(trajectory.PHYSICAL_BODY_NAMES, 1.0), 0.0, 1.0, 1.0,
            thrust_enabled=False,
        )
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (0, 0, 0)
