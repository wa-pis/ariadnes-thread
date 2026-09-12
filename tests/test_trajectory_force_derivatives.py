"""Analytic point-mass force-curvature controls, not a full-force certificate."""

from fractions import Fraction
import math

import pytest


def _point_mass_force_curvature_bound_m_s4(
    gm_m3_s2: float, distance_floor_m: float,
    relative_speed_upper_m_s: Fraction, relative_acceleration_upper_m_s2: Fraction,
) -> Fraction:
    """Bound the second time derivative of acceleration along a relative curve.

    Distance, relative speed and relative acceleration bounds must hold
    throughout the interval. This function does not establish domain closure.
    """
    assert all(type(value) is float and math.isfinite(value) and value > 0
               for value in (gm_m3_s2, distance_floor_m))
    assert all(isinstance(value, Fraction) and value >= 0
               for value in (relative_speed_upper_m_s, relative_acceleration_upper_m_s2))
    gm, radius = Fraction(gm_m3_s2), Fraction(distance_floor_m)
    # D²g[u,w]: triangle bound 3*(1+1+1+5)=24; ||Dg|| <= 2*mu/r³.
    return (24 * gm * relative_speed_upper_m_s**2 / radius**4
            + 2 * gm * relative_acceleration_upper_m_s2 / radius**3)


@pytest.mark.parametrize("gm_m3_s2", [1.0, 7.0])
@pytest.mark.parametrize("position_m", [(0, 0, 5), (3, 4, 0), (-3, 0, 4)])
@pytest.mark.parametrize("velocity_m_s", [(0, 0, 0), (1, -2, 2), (0, 0, 3)])
@pytest.mark.parametrize("acceleration_m_s2", [(0, 0, 0), (-2, 1, 2)])
def test_force_curvature_encloses_cartesian_chain_rule(
    gm_m3_s2: float, position_m: tuple[int, ...], velocity_m_s: tuple[int, ...], acceleration_m_s2: tuple[int, ...],
) -> None:
    radius = Fraction(5)
    rv = sum(r * v for r, v in zip(position_m, velocity_m_s, strict=True))
    vv_ra = sum(v*v + r*a for r, v, a in zip(position_m, velocity_m_s, acceleration_m_s2, strict=True))
    # Independent scalar chain rule: g=-r*q^(-3/2), q=r.r;
    # q'=2*r.v, q''=2*(v.v+r.a), evaluated with exact rational arithmetic.
    scalar_first = -3 * rv / radius**5
    scalar_second = 15 * rv**2 / radius**7 - 3 * vv_ra / radius**5
    exact = tuple(-Fraction(gm_m3_s2) * (a / radius**3 + 2*v*scalar_first + r*scalar_second)
                  for r, v, a in zip(position_m, velocity_m_s, acceleration_m_s2, strict=True))
    bound = _point_mass_force_curvature_bound_m_s4(
        gm_m3_s2, 5.0, Fraction(sum(map(abs, velocity_m_s))), Fraction(sum(map(abs, acceleration_m_s2))),
    )
    assert sum(value**2 for value in exact) <= bound**2  # m²/s⁸
    assert (bound == 0) == (velocity_m_s == acceleration_m_s2 == (0, 0, 0))


@pytest.mark.parametrize("radius_m", [1.0, 2.0])
@pytest.mark.parametrize("omega_rad_s", [Fraction(1, 2), Fraction(1)])
def test_force_curvature_encloses_exact_circular_motion(radius_m: float, omega_rad_s: Fraction) -> None:
    radius = Fraction(radius_m)
    bound = _point_mass_force_curvature_bound_m_s4(1.0, radius_m, radius*omega_rad_s, radius*omega_rad_s**2)
    # g(t)=-(cos(wt),sin(wt),0)/R², so ||g''||=w²/R² at every time.
    exact_norm = omega_rad_s**2 / radius**2
    assert bound == 26 * exact_norm  # Deliberately conservative, not a tolerance.


@pytest.mark.parametrize("duration_s", [0.0, 1 / 32, 1 / 4])
@pytest.mark.parametrize("speed_m_s", [Fraction(0), Fraction(1)])
def test_force_curvature_bounds_radial_taylor_remainder(duration_s: float, speed_m_s: Fraction) -> None:
    # r(t)=2+v*t stays outside d=2 for the entire interval; r''=0.
    time, radius = Fraction(duration_s), Fraction(2)
    bound = _point_mass_force_curvature_bound_m_s4(1.0, 2.0, speed_m_s, Fraction(0))
    exact_force = -1 / (radius + speed_m_s*time)**2
    linear_force = -1 / radius**2 + 2 * speed_m_s * time / radius**3
    assert abs(exact_force - linear_force) <= bound * time**2 / 2  # m/s²
    assert (exact_force == linear_force) == (time == 0 or speed_m_s == 0)


@pytest.mark.parametrize("field", range(4))
@pytest.mark.parametrize("invalid", [-1.0, 0.0, True, math.nan, math.inf, Fraction(-1)])
def test_force_curvature_rejects_invalid_bounds(field: int, invalid: object) -> None:
    values: list[object] = [1.0, 1.0, Fraction(1), Fraction(1)]
    values[field] = invalid
    with pytest.raises(AssertionError):
        _point_mass_force_curvature_bound_m_s4(*values)  # type: ignore[arg-type] -- boundary rejection.
