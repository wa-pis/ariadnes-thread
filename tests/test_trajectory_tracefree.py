"""Ideal symmetric trace-free gravity Hessians; no native error certificate."""

from fractions import Fraction
import math

import numpy as np
import pytest

from test_trajectory_spk import _dyadic_sqrt_bounds


def _tracefree_operator_bound_s_inv2(frobenius_bound_s_inv2: Fraction) -> Fraction:
    """Bound a 3D symmetric trace-free Jacobian's operator norm in s^-2.

    Caller must establish symmetry, zero trace and a Frobenius (not merely
    operator) norm bound. Native arithmetic and other forces stay separate.
    """
    assert isinstance(frobenius_bound_s_inv2, Fraction) and frobenius_bound_s_inv2 >= 0
    return _dyadic_sqrt_bounds(Fraction(2, 3))[1] * frobenius_bound_s_inv2


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
