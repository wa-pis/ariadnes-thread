"""Exact per-degree coefficient/Hessian map controls; no native application."""

from fractions import Fraction
import math

import numpy as np
import pytest

from space_nav import trajectory
from test_trajectory_spk import _dyadic_sqrt_bounds, _harmonic_spatial_jacobian_bound_s_inv2


def _degree_hessian_operator_bound_s_inv2(
    degree: int, coefficient_norm_squared: Fraction,
    gm_m3_s2: float, radius_m: float, distance_m: float,
) -> Fraction:
    """Bound one ideal 4pi-normalized exterior degree's operator norm in s^-2."""
    assert type(degree) is int and degree >= 0
    assert isinstance(coefficient_norm_squared, Fraction) and coefficient_norm_squared >= 0
    assert all(type(value) is float and math.isfinite(value) and value > 0 for value in (gm_m3_s2, radius_m, distance_m))
    gm, radius, distance = map(Fraction, (gm_m3_s2, radius_m, distance_m))
    root = _dyadic_sqrt_bounds((2*degree+1)*coefficient_norm_squared)[1] if coefficient_norm_squared else Fraction(0)
    return gm/distance**3*(radius/distance)**degree*(degree+1)*(degree+2)*root


@pytest.mark.parametrize("degree", [0, 1, 2, 3, 8, 19, 120, 200])
def test_polar_hessian_gram_from_expanded_rodrigues(degree: int) -> None:
    # Independent expanded Legendre polynomial, evaluated/differentiated
    # exactly at z=1; no special-function or floating-point recurrence.
    derivatives = []
    for order in range(3):
        value = Fraction(0)
        for k in range(degree//2+1):
            power = degree-2*k
            if power >= order:
                value += Fraction((-1)**k*math.factorial(2*degree-2*k),
                                  2**degree*math.factorial(k)*math.factorial(degree-k)*math.factorial(power-order))
        derivatives.append(value)
    p, dp, ddp = derivatives
    n = degree
    assert (p, dp, ddp) == (1, Fraction(n*(n+1), 2), Fraction((n-1)*n*(n+1)*(n+2), 8))
    a, b = (n+1)*(n+2)*p, -(n+1)*p-dp
    mixed, planar = -(n+2)*dp, 2*ddp
    matrices = [((b, 0, 0), (0, b, 0), (0, 0, a))]
    orders = [0]
    if n >= 1:
        matrices += [((0, 0, mixed), (0, 0, 0), (mixed, 0, 0)),
                     ((0, 0, 0), (0, 0, mixed), (0, mixed, 0))]
        orders += [1, 1]
    if n >= 2:
        matrices += [((planar, 0, 0), (0, -planar, 0), (0, 0, 0)),
                     ((0, planar, 0), (planar, 0, 0), (0, 0, 0))]
        orders += [2, 2]
    norms = []
    for index, (matrix, order) in enumerate(zip(matrices, orders, strict=True)):
        assert sum(matrix[i][i] for i in range(3)) == 0
        normalization_squared = Fraction((1 if order == 0 else 2)*(2*n+1)*math.factorial(n-order), math.factorial(n+order))
        norms.append(normalization_squared*sum(value*value for row in matrix for value in row))
        for other in matrices[:index]:
            assert sum(matrix[i][j]*other[i][j] for i in range(3) for j in range(3)) == 0
    a0 = Fraction(3, 2)*(2*n+1)*(n+1)**2*(n+2)**2
    a1 = (2*n+1)*n*(n+1)*(n+2)**2
    a2 = Fraction((2*n+1)*(n-1)*n*(n+1)*(n+2), 4)
    assert norms == [a0, a1, a1, a2, a2][:len(norms)]
    assert a0-a1 == Fraction((2*n+1)*(n+1)*(n+2)**2*(n+3), 2) > 0
    assert a0-a2 == Fraction((2*n+1)*(n+1)*(n+2)*(5*n+4)*(n+3), 4) > 0
    assert sum(norms) == (2*n+1)**2*(n+1)*(n+2)*(2*n+3)


@pytest.mark.parametrize("tangent", [Fraction(0), Fraction(1, 3), Fraction(1)])
def test_degree_one_two_coefficient_norm_is_rotation_invariant(tangent: Fraction) -> None:
    c, s = (1-tangent*tangent)/(1+tangent*tangent), 2*tangent/(1+tangent*tangent)
    rotation = np.array(((c*c, -s, c*s), (s*c, c, s*s), (-s, 0, c)), dtype=object)
    assert np.array_equal(rotation.T @ rotation, np.eye(3))
    vector = np.array(tuple(map(Fraction, (1, -2, 3))), dtype=object)
    assert sum((rotation @ vector)**2) == sum(vector**2)  # Degree one, common sqrt(3) normalization.
    tensor = np.array(((1, 2, 3), (2, 4, 5), (3, 5, -5)), dtype=object)
    coefficient_norms = []
    for matrix in (tensor, rotation @ tensor @ rotation.T):
        # V=r.T*T*r/r^5. Recover squared normalized C20/C21/S21/C22/S22
        # coefficients without introducing irrational normalization factors.
        q = (Fraction(matrix[2, 2]**2, 5) + Fraction((matrix[0, 0]-matrix[1, 1])**2, 15)
             + Fraction(4*(matrix[0, 1]**2+matrix[0, 2]**2+matrix[1, 2]**2), 15))
        assert q == Fraction(2, 15)*sum(value*value for value in matrix.flat)
        coefficient_norms.append(q)
    assert coefficient_norms[0] == coefficient_norms[1]


@pytest.mark.parametrize("degree", [0, 1, 2, 3, 8, 19, 120, 200])
@pytest.mark.parametrize("distance_m", [1.0, 2.0])
def test_degree_operator_bound_attains_polar_zonal_limit(degree: int, distance_m: float) -> None:
    q = Fraction(1, 64)
    bound = _degree_hessian_operator_bound_s_inv2(degree, q, 1.0, 1.0, distance_m)
    # Independent radial second derivative of sqrt(2n+1)*C_n0/r^(n+1).
    exact_squared = (degree+1)**2*(degree+2)**2*(2*degree+1)*q/Fraction(distance_m)**(2*degree+6)
    scale = Fraction((degree+1)*(degree+2))/Fraction(distance_m)**(degree+3)
    assert 0 <= bound*bound-exact_squared <= scale*scale/Fraction(2**90)
    cosine, sine = np.zeros((degree+1, degree+1)), np.zeros((degree+1, degree+1))
    cosine[degree, 0] = 0.125
    generic = _harmonic_spatial_jacobian_bound_s_inv2(
        trajectory._RefinementBudget("degree-map", 300.0), 1.0, 1.0, distance_m, cosine, sine,
    )
    assert bound < generic


def test_degree_operator_bound_retains_zero_coefficients() -> None:
    assert _degree_hessian_operator_bound_s_inv2(200, Fraction(0), 1.0, 1.0, 2.0) == 0


@pytest.mark.parametrize("field", range(5))
@pytest.mark.parametrize("invalid", ["negative", "boolean"])
def test_degree_operator_bound_rejects_invalid_inputs(field: int, invalid: str) -> None:
    values: list[object] = [2, Fraction(1, 64), 1.0, 1.0, 1.0]
    values[field] = True if invalid == "boolean" else (-1 if field == 0 else Fraction(-1) if field == 1 else -1.0)
    with pytest.raises(AssertionError):
        _degree_hessian_operator_bound_s_inv2(*values)  # type: ignore[arg-type] -- boundary rejection.


@pytest.mark.parametrize("field", [2, 3, 4])
@pytest.mark.parametrize("invalid", [0.0, math.nan, math.inf])
def test_degree_operator_bound_rejects_nonfinite_scales(field: int, invalid: float) -> None:
    values: list[object] = [2, Fraction(1, 64), 1.0, 1.0, 1.0]
    values[field] = invalid
    with pytest.raises(AssertionError):
        _degree_hessian_operator_bound_s_inv2(*values)  # type: ignore[arg-type] -- boundary rejection.


@pytest.mark.parametrize("field", [0, 1])
def test_degree_operator_bound_rejects_float_exact_inputs(field: int) -> None:
    values: list[object] = [2, Fraction(1, 64), 1.0, 1.0, 1.0]
    values[field] = 1.0
    with pytest.raises(AssertionError):
        _degree_hessian_operator_bound_s_inv2(*values)  # type: ignore[arg-type] -- boundary rejection.
