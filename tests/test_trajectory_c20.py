"""Ideal C20 sensitivity and remainder composition; no mission certificate."""

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


def _c20_remainder_jacobian_bound_s_inv2(
    budget: trajectory._RefinementBudget, gm_m3_s2: float, reference_radius_m: float,
    distance_lower_m: float, cosine: np.ndarray, sine: np.ndarray,
) -> Fraction:
    """Compose sharp C20 and generic remainder bounds; input C00 must be zero."""
    budget.check()
    assert cosine.ndim == 2 and cosine.shape == sine.shape and cosine.shape[0] == cosine.shape[1] >= 3
    assert all(matrix.dtype == np.float64 and np.all(np.isfinite(matrix)) and not np.any(np.triu(matrix, 1))
               for matrix in (cosine, sine))
    assert cosine[0, 0] == 0 and not np.any(sine[:, 0])
    c20_bound = _c20_spatial_jacobian_bound_s_inv2(gm_m3_s2, reference_radius_m, distance_lower_m, float(cosine[2, 0]))
    remainder = cosine.copy()
    remainder[2, 0] = 0.0
    reconstructed = remainder.copy()
    reconstructed[2, 0] = cosine[2, 0]
    assert np.array_equal(reconstructed, cosine)
    return c20_bound + _harmonic_spatial_jacobian_bound_s_inv2(
        budget, gm_m3_s2, reference_radius_m, distance_lower_m, remainder, sine,
    )


@pytest.mark.parametrize("c20", [-0.125, 0.125])
@pytest.mark.parametrize("c22", [0.0, 0.03125, 0.25])
@pytest.mark.parametrize("c30", [-0.0625, 0.0, 0.0625])
@pytest.mark.parametrize("distance_m", [1.0, 2.0])
def test_c20_remainder_encloses_mixed_polar_hessian(c20: float, c22: float, c30: float, distance_m: float) -> None:
    budget = trajectory._RefinementBudget("c20-remainder", 300.0)
    cosine, sine = np.zeros((4, 4)), np.zeros((4, 4))
    cosine[2, 0], cosine[2, 2], cosine[3, 0] = c20, c22, c30
    original = cosine.tobytes(), sine.tobytes()
    composed = _c20_remainder_jacobian_bound_s_inv2(budget, 1.0, 1.0, distance_m, cosine, sine)
    generic = _harmonic_spatial_jacobian_bound_s_inv2(budget, 1.0, 1.0, distance_m, cosine, sine)
    selected = min(composed, generic)
    # Independent diagonal polar Hessian: GM=R=1 SI. Jzz from C20/C30;
    # C22 adds +/-sqrt(15)*C22/r^5 to Jxx/Jyy, leaving Jzz unchanged.
    r = Fraction(distance_m)
    for root5 in _dyadic_sqrt_bounds(Fraction(5)):
        for root7 in _dyadic_sqrt_bounds(Fraction(7)):
            for root15 in _dyadic_sqrt_bounds(Fraction(15)):
                axial = 12*root5*Fraction(c20)/r**5 + 20*root7*Fraction(c30)/r**6
                tesseral = root15*Fraction(c22)/r**5
                assert max(abs(axial), abs(-axial/2+tesseral), abs(-axial/2-tesseral)) <= selected
    assert (cosine.tobytes(), sine.tobytes()) == original
    if c22 == 0:
        assert composed < generic
    assert selected <= generic and budget.native_arc_propagations == 0


@pytest.mark.parametrize("invalid", ["empty", "low-degree", "nonsquare", "mismatch", "boolean", "nan", "upper-c", "upper-s", "zonal-s", "monopole"])
def test_c20_remainder_rejects_invalid_coefficients(invalid: str) -> None:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    if invalid in {"empty", "low-degree"}:
        size = 0 if invalid == "empty" else 2
        cosine = sine = np.zeros((size, size))
    elif invalid == "nonsquare":
        cosine = sine = np.zeros((3, 4))
    elif invalid == "mismatch":
        sine = np.zeros((4, 4))
    elif invalid == "boolean":
        cosine = cosine.astype(np.bool_)
    elif invalid == "nan":
        cosine[2, 0] = np.nan
    elif invalid == "upper-c":
        cosine[0, 1] = 1.0
    elif invalid == "upper-s":
        sine[0, 1] = 1.0
    elif invalid == "zonal-s":
        sine[2, 0] = 1.0
    else:
        cosine[0, 0] = 1.0
    with pytest.raises(AssertionError):
        _c20_remainder_jacobian_bound_s_inv2(trajectory._RefinementBudget("invalid-c20-rest", 300.0), 1.0, 1.0, 1.0, cosine, sine)


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
