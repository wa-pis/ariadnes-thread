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
