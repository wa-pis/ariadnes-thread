"""Sharp ideal C20 spatial sensitivity; no full-field or native certificate."""

from fractions import Fraction
import math

import numpy as np
import pytest

from space_nav import trajectory
from test_trajectory_spk import _dyadic_sqrt_bounds, _harmonic_spatial_jacobian_bound_s_inv2


def _c20_spatial_jacobian_bound_s_inv2(
    gm_m3_s2: float, reference_radius_m: float, distance_lower_m: float, c20: float,
) -> Fraction:
    """Bound the Euclidean operator norm of the normalized C20 force Jacobian.

    Valid for ideal proper rotations and r>=distance_lower_m; all other
    harmonic terms and source/rotation arithmetic must be bounded separately.
    """
    assert all(type(value) is float and math.isfinite(value)
               for value in (gm_m3_s2, reference_radius_m, distance_lower_m, c20))
    assert gm_m3_s2 > 0 and reference_radius_m > 0 and distance_lower_m > 0
    sqrt5_upper = _dyadic_sqrt_bounds(Fraction(5))[1]
    return 12*sqrt5_upper*abs(Fraction(c20))*Fraction(gm_m3_s2)*Fraction(reference_radius_m)**2/Fraction(distance_lower_m)**5


@pytest.mark.parametrize("tangent", [Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(1)])
@pytest.mark.parametrize("sign", [-1, 1])
def test_c20_cartesian_hessian_has_uniform_spectral_bound(tangent: Fraction, sign: int) -> None:
    x = (1-tangent**2)/(1+tangent**2)
    z = sign*2*tangent/(1+tangent**2)
    radial = (x, Fraction(0), z)
    pole = (Fraction(0), Fraction(0), Fraction(1))
    t = z*z
    assert x*x+t == 1
    # Cartesian derivative of g=K/r^4*[3(1-5*u_z^2)*u+6*u_z*e_z],
    # with K=sqrt(5)*C20*GM*R^2/2. Matrix below factors out K/r^5.
    hessian = tuple(tuple(3*(1-5*t)*int(i == j) + (-15+105*t)*radial[i]*radial[j]
                           - 30*z*(radial[i]*pole[j]+pole[i]*radial[j]) + 6*pole[i]*pole[j]
                           for j in range(3)) for i in range(3))
    basis = (radial, (-z, Fraction(0), x), (Fraction(0), Fraction(1), Fraction(0)))
    projected = tuple(tuple(sum((left[i]*hessian[i][j]*right[j] for i in range(3) for j in range(3)), Fraction(0))
                            for right in basis) for left in basis)
    a, b, d, azimuth = -12+36*t, -24*z*x, 9-21*t, 3-15*t
    assert projected == ((a, b, 0), (b, d, 0), (0, 0, azimuth))
    # Exact principal-minor factorizations prove 24I +/- H >= 0 for
    # every 0<=t<=1, not just these controls (see design proof).
    assert (24-a)*(24-d)-b*b == 180*(1-t)*(3+t) >= 0
    assert (24+a)*(24+d)-b*b == 36*(11+10*t-5*t*t) > 0
    assert all(value >= 0 for value in (24-a, 24-d, 24+a, 24+d, 24-azimuth, 24+azimuth))
    if t == 1:
        assert a == 24  # The upper bound is attained at the pole.


@pytest.mark.parametrize("gm_m3_s2", [1.0, 7.0])
@pytest.mark.parametrize("reference_radius_m", [1.0, 2.0])
@pytest.mark.parametrize("distance_m", [1.0, 5.0])
@pytest.mark.parametrize("c20", [-0.125, 0.0, 0.125])
def test_c20_bound_encloses_exact_polar_eigenvalue(
    gm_m3_s2: float, reference_radius_m: float, distance_m: float, c20: float,
) -> None:
    bound = _c20_spatial_jacobian_bound_s_inv2(gm_m3_s2, reference_radius_m, distance_m, c20)
    # At the pole dg_z/dz=12*sqrt(5)*C20*GM*R^2/r^5, in s^-2.
    scale = 12*abs(Fraction(c20))*Fraction(gm_m3_s2)*Fraction(reference_radius_m)**2/Fraction(distance_m)**5
    assert 0 <= bound**2-5*scale**2 <= scale**2/Fraction(2)**90
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[2, 0] = c20
    generic = _harmonic_spatial_jacobian_bound_s_inv2(
        trajectory._RefinementBudget("c20-spectral", 300.0), gm_m3_s2,
        reference_radius_m, distance_m, cosine, sine,
    )
    assert bound <= generic and (bound < generic) is (c20 != 0)


@pytest.mark.parametrize("field", range(4))
@pytest.mark.parametrize("invalid", [True, math.nan, math.inf])
def test_c20_bound_rejects_nonfinite_or_boolean(field: int, invalid: float) -> None:
    values = [1.0]*4
    values[field] = invalid
    with pytest.raises(AssertionError):
        _c20_spatial_jacobian_bound_s_inv2(*values)


@pytest.mark.parametrize("field", range(3))
@pytest.mark.parametrize("invalid", [0.0, -1.0])
def test_c20_bound_rejects_nonpositive_scale(field: int, invalid: float) -> None:
    values = [1.0]*4
    values[field] = invalid
    with pytest.raises(AssertionError):
        _c20_spatial_jacobian_bound_s_inv2(*values)
