"""Ideal degree-map bounds and composition; no full-mission certificate."""

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


def _nonmonopole_degree_map_bound_s_inv2(
    budget: trajectory._RefinementBudget, gm_m3_s2: float, radius_m: float,
    distance_m: float, cosine: np.ndarray, sine: np.ndarray,
) -> Fraction:
    """Sum ideal whole-degree operator bounds, requiring C00=0; retain C20."""
    budget.check()
    assert cosine.ndim == 2 and cosine.shape == sine.shape and cosine.shape[0] == cosine.shape[1] > 0
    assert all(matrix.dtype == np.float64 and np.all(np.isfinite(matrix)) and not np.any(np.triu(matrix, 1))
               for matrix in (cosine, sine))
    assert cosine[0, 0] == 0 and not np.any(sine[:, 0])
    bound = Fraction(0)
    for n, (c_row, s_row) in enumerate(zip(cosine, sine, strict=True)):
        budget.check()
        q = sum((Fraction(float(c))**2 + Fraction(float(s))**2
                 for c, s in zip(c_row[:n+1], s_row[:n+1], strict=True)), Fraction(0))
        bound += _degree_hessian_operator_bound_s_inv2(n, q, gm_m3_s2, radius_m, distance_m)
    budget.check()
    return bound


@pytest.mark.parametrize("signs", [(a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)])
@pytest.mark.parametrize("distance_m", [1.0, 2.0])
def test_degree_sum_encloses_mixed_zonal_polar_hessian(signs: tuple[int, ...], distance_m: float) -> None:
    cosine, sine = np.zeros((4, 4)), np.zeros((4, 4))
    for degree, sign in enumerate(signs, 1):
        cosine[degree, 0] = sign/8
    original = cosine.tobytes(), sine.tobytes()
    budget = trajectory._RefinementBudget("mixed-degree-sum", 300.0)
    bound = _nonmonopole_degree_map_bound_s_inv2(budget, 1.0, 1.0, distance_m, cosine, sine)
    assert bound == sum((_degree_hessian_operator_bound_s_inv2(n, Fraction(1, 64), 1.0, 1.0, distance_m)
                         for n in range(1, 4)), Fraction(0))
    # Independent radial second derivatives. Axisymmetry and zero trace
    # give the other two eigenvalues as -Jzz/2; normalization roots enclosed.
    for root3 in _dyadic_sqrt_bounds(Fraction(3)):
        for root5 in _dyadic_sqrt_bounds(Fraction(5)):
            for root7 in _dyadic_sqrt_bounds(Fraction(7)):
                jzz = sum((Fraction(sign, 8)*(n+1)*(n+2)*root/Fraction(distance_m)**(n+3)
                           for n, (sign, root) in enumerate(zip(signs, (root3, root5, root7), strict=True), 1)), Fraction(0))
                assert abs(jzz) <= bound
    assert (cosine.tobytes(), sine.tobytes()) == original and budget.native_arc_propagations == 0


@pytest.mark.parametrize("c20", [0.0, 0.125])
@pytest.mark.parametrize("distance_m", [1.0, 2.0])
def test_degree_sum_couples_cosine_and_sine_once(c20: float, distance_m: float) -> None:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    cosine[2, 0], sine[2, 2] = c20, 0.25
    bound = _nonmonopole_degree_map_bound_s_inv2(trajectory._RefinementBudget("sine-degree", 300.0), 1.0, 1.0, distance_m, cosine, sine)
    assert bound == _degree_hessian_operator_bound_s_inv2(2, Fraction(c20)**2+Fraction(1, 16), 1.0, 1.0, distance_m)


@pytest.mark.parametrize("size", [1, 9, 201])
def test_degree_sum_retains_zero_field(size: int) -> None:
    assert _nonmonopole_degree_map_bound_s_inv2(trajectory._RefinementBudget("zero-field", 300.0), 1.0, 1.0, 2.0,
                                              np.zeros((size, size)), np.zeros((size, size))) == 0


@pytest.mark.parametrize("invalid", ["empty", "dimension", "nonsquare", "mismatch", "boolean", "nan", "upper-c", "upper-s", "zonal-s", "monopole"])
def test_degree_sum_rejects_invalid_coefficients(invalid: str) -> None:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    if invalid == "empty":
        cosine = sine = np.zeros((0, 0))
    elif invalid == "dimension":
        cosine = sine = np.zeros(3)
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
        _nonmonopole_degree_map_bound_s_inv2(trajectory._RefinementBudget("invalid-degree-field", 300.0), 1.0, 1.0, 1.0, cosine, sine)


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
