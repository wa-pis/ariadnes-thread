"""Ideal symmetric trace-free gravity Hessians; no native error certificate."""

from fractions import Fraction
import math

import numpy as np
import pytest

from test_trajectory_spk import _dyadic_sqrt_bounds
from test_trajectory_spk import _harmonic_spatial_jacobian_bound_s_inv2
from test_trajectory_c20 import _c20_spatial_jacobian_bound_s_inv2
from space_nav import trajectory


def _tracefree_operator_bound_s_inv2(frobenius_bound_s_inv2: Fraction) -> Fraction:
    """Bound a 3D symmetric trace-free Jacobian's operator norm in s^-2.

    Caller must establish symmetry, zero trace and a Frobenius (not merely
    operator) norm bound. Native arithmetic and other forces stay separate.
    """
    assert isinstance(frobenius_bound_s_inv2, Fraction) and frobenius_bound_s_inv2 >= 0
    return _dyadic_sqrt_bounds(Fraction(2, 3))[1] * frobenius_bound_s_inv2


@pytest.mark.parametrize("coefficients", [(0, 0, 0, 0), (1, 2, 0, 0), (0, 0, 1, 2), (1, -2, 3, -4)])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("distance_m", [1.0, 2.0])
def test_generic_remainder_bound_has_frobenius_provenance(
    coefficients: tuple[int, ...], sign: int, distance_m: float,
) -> None:
    c21, s21, c22, s22 = (Fraction(sign*value, 8) for value in coefficients)
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[2, 1], sine[2, 1], cosine[2, 2], sine[2, 2] = map(float, (c21, s21, c22, s22))
    generic = _harmonic_spatial_jacobian_bound_s_inv2(
        trajectory._RefinementBudget("frobenius-provenance", 300.0), 1.0, 1.0, distance_m, cosine, sine,
    )
    # Independent polar Hessian divided by sqrt(15)/r^5, GM=R=1 SI,
    # from V21=sqrt(15)*xz/r^5 and V22=sqrt(15)*(x^2-y^2)/(2*r^5).
    matrix = ((c22, s22, -4*c21), (s22, -c22, -4*s21), (-4*c21, -4*s21, Fraction(0)))
    scale_squared = 15/Fraction(distance_m)**10
    exact_frobenius_squared = scale_squared*sum((value*value for row in matrix for value in row), Fraction(0))
    assert exact_frobenius_squared == 30*(16*(c21*c21+s21*s21)+c22*c22+s22*s22)/Fraction(distance_m)**10
    assert generic*generic >= exact_frobenius_squared
    corrected = _tracefree_operator_bound_s_inv2(generic)
    for direction in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (Fraction(3, 5), 0, Fraction(4, 5))):
        action = tuple(sum((value*v for value, v in zip(row, direction, strict=True)), Fraction(0)) for row in matrix)
        assert scale_squared*sum((value*value for value in action), Fraction(0)) <= corrected*corrected
    assert 0 <= corrected <= generic


@pytest.mark.parametrize("c20", [-0.125, 0.125])
@pytest.mark.parametrize("distance_m", [1.0, 2.0])
def test_tracefree_factor_cannot_reduce_sharp_c20_operator_bound(c20: float, distance_m: float) -> None:
    sharp = _c20_spatial_jacobian_bound_s_inv2(1.0, 1.0, distance_m, c20)
    exact_polar_operator_squared = 720*Fraction(c20)**2/Fraction(distance_m)**10
    assert sharp*sharp >= exact_polar_operator_squared
    assert _tracefree_operator_bound_s_inv2(sharp)**2 < exact_polar_operator_squared


@pytest.mark.parametrize("entries", [
    (0, 0, 0, 0, 0), (2, 0, 0, -1, 0), (-2, 0, 0, 1, 0),
    (24, 0, 0, -12, 0), (1, 2, 3, 4, 5), (0, 1, 1, 0, 1),
])
def test_tracefree_directional_gap_is_sum_of_squares(entries: tuple[int, ...]) -> None:
    a, b, c, d, e = map(Fraction, entries)
    matrix = ((a, b, c), (b, d, e), (c, e, -a-d))
    frobenius_squared = sum((value**2 for row in matrix for value in row), Fraction(0))
    action_squared = a*a + b*b + c*c  # Exact J*e1, with entries in s^-2.
    gap = Fraction(2, 3)*frobenius_squared - action_squared
    assert gap == ((a+2*d)**2 + b*b + c*c + 4*e*e)/3 >= 0


@pytest.mark.parametrize("eigenvalues", [(-1, -1, 2), (-12, -12, 24), (-1, 0, 1), (-3, 1, 2), (0, 0, 0)])
@pytest.mark.parametrize("tangent", [Fraction(0), Fraction(1, 3), Fraction(1)])
def test_tracefree_bound_encloses_independent_rotated_spectrum(
    eigenvalues: tuple[int, ...], tangent: Fraction,
) -> None:
    c, s = (1-tangent*tangent)/(1+tangent*tangent), 2*tangent/(1+tangent*tangent)
    zero, one = Fraction(0), Fraction(1)
    rz = np.array(((c, -s, zero), (s, c, zero), (zero, zero, one)), dtype=object)
    ry = np.array(((c, zero, s), (zero, one, zero), (-s, zero, c)), dtype=object)
    rotation = rz @ ry
    assert np.array_equal(rotation.T @ rotation, np.eye(3))
    diagonal = np.diag(tuple(map(Fraction, eigenvalues)))
    matrix = rotation @ diagonal @ rotation.T
    assert np.array_equal(matrix, matrix.T) and sum(matrix.diagonal(), Fraction(0)) == 0
    for index, eigenvalue in enumerate(eigenvalues):
        assert np.array_equal(matrix @ rotation[:, index], eigenvalue*rotation[:, index])
    frobenius_squared = sum((value**2 for value in matrix.flat), Fraction(0))
    assert frobenius_squared == sum(value*value for value in eigenvalues)
    frobenius_upper = _dyadic_sqrt_bounds(frobenius_squared)[1] if frobenius_squared else Fraction(0)
    bound = _tracefree_operator_bound_s_inv2(frobenius_upper)
    exact_operator = max(map(abs, eigenvalues))
    assert exact_operator <= bound <= frobenius_upper
    if exact_operator:
        assert bound < frobenius_upper
    if eigenvalues[0] == eigenvalues[1]:
        # Monopole and scaled polar C20 attain the ideal factor; no stronger
        # universal factor can follow from symmetry and zero trace alone.
        assert exact_operator**2 == Fraction(2, 3)*frobenius_squared


@pytest.mark.parametrize("missing_premise", ["symmetry", "zero-trace"])
def test_tracefree_factor_requires_both_matrix_premises(missing_premise: str) -> None:
    matrix = np.array(((0, 1, 0), (0, 0, 0), (0, 0, 0)) if missing_premise == "symmetry"
                      else ((1, 0, 0), (0, 0, 0), (0, 0, 0)))
    vector = np.array((0, 1, 0) if missing_premise == "symmetry" else (1, 0, 0))
    assert sum((matrix @ vector)**2) == 1  # Independent unit-vector action.
    assert Fraction(2, 3)*int(np.sum(matrix*matrix)) < 1


@pytest.mark.parametrize("invalid", [Fraction(-1), True, 1.0, math.nan, math.inf])
def test_tracefree_bound_rejects_invalid_norm(invalid: object) -> None:
    with pytest.raises(AssertionError):
        _tracefree_operator_bound_s_inv2(invalid)  # type: ignore[arg-type] -- boundary rejection.
