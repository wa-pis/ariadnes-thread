"""Exact ideal zonal spin symmetry, not a native PCK arithmetic certificate."""

from fractions import Fraction

import numpy as np
import pytest

from space_nav import trajectory
from test_trajectory_spk import (
    _angle_limited_rotation_bound_m_s2, _harmonic_arbitrary_rotation_bound_m_s2,
    _harmonic_spatial_jacobian_bound_s_inv2, _pck_euler_rate_upper_rad_s,
    _pi_rational_bounds, _regular_solid_harmonic_jets,
)


def _partitioned_rotation_bound_m_s2(
    pole_angle_rad: Fraction, full_angle_rad: Fraction,
    zonal_norm_m_s2: Fraction, zonal_jacobian_s_inv2: Fraction,
    nonzonal_norm_m_s2: Fraction, nonzonal_jacobian_s_inv2: Fraction,
    radius_upper_m: Fraction,
) -> Fraction:
    """Compose ideal zonal pole motion and nonzonal full rotation allowances."""
    assert all(isinstance(value, Fraction) and value >= 0 for value in (
        pole_angle_rad, full_angle_rad, zonal_norm_m_s2, zonal_jacobian_s_inv2,
        nonzonal_norm_m_s2, nonzonal_jacobian_s_inv2, radius_upper_m,
    ))
    assert pole_angle_rad <= full_angle_rad and radius_upper_m > 0
    return (_angle_limited_rotation_bound_m_s2(pole_angle_rad, zonal_norm_m_s2, zonal_jacobian_s_inv2, radius_upper_m)
            + _angle_limited_rotation_bound_m_s2(full_angle_rad, nonzonal_norm_m_s2, nonzonal_jacobian_s_inv2, radius_upper_m))


@pytest.mark.parametrize("tangent", [Fraction(0), Fraction(1, 1000), Fraction(1, 2), Fraction(1)])
def test_partitioned_rotation_encloses_mixed_quadrupole(tangent: Fraction) -> None:
    budget = trajectory._RefinementBudget("split-rotation", 300.0)
    zonal, nonzonal, zero = np.zeros((3, 3)), np.zeros((3, 3)), np.zeros((3, 3))
    zonal[2, 0], nonzonal[2, 2] = 0.125, 0.03125
    norms = [_harmonic_arbitrary_rotation_bound_m_s2(budget, 1.0, 1.0, 1.0, field, zero) / 2
             for field in (zonal, nonzonal)]
    jacobians = [_harmonic_spatial_jacobian_bound_s_inv2(budget, 1.0, 1.0, 1.0, field, zero)
                 for field in (zonal, nonzonal)]
    bound = _partitioned_rotation_bound_m_s2(Fraction(0), 2*tangent, norms[0], jacobians[0], norms[1], jacobians[1], Fraction(1))
    c, s = (1 - tangent**2)/(1 + tangent**2), 2*tangent/(1 + tangent**2)
    # At r=(1,0,0) m the zonal term cancels under z spin. Independently
    # differentiate V22=sqrt(15)*C22*(x^2-y^2)/(2*r^5), GM=R=1 SI.
    coefficient = Fraction(0.03125)/2
    fixed_over_sqrt15 = (coefficient*(2*c - 5*(c*c-s*s)*c), coefficient*(-2*s - 5*(c*c-s*s)*s))
    delta_over_sqrt15 = (c*fixed_over_sqrt15[0] + s*fixed_over_sqrt15[1] + 3*coefficient,
                         -s*fixed_over_sqrt15[0] + c*fixed_over_sqrt15[1])
    assert 15*sum((value**2 for value in delta_over_sqrt15), Fraction(0)) <= bound**2
    old = _angle_limited_rotation_bound_m_s2(2*tangent,
        _harmonic_arbitrary_rotation_bound_m_s2(budget, 1.0, 1.0, 1.0, zonal+nonzonal, zero)/2,
        _harmonic_spatial_jacobian_bound_s_inv2(budget, 1.0, 1.0, 1.0, zonal+nonzonal, zero), Fraction(1))
    assert bound <= old and (bound < old) is (tangent > 0)
    assert _partitioned_rotation_bound_m_s2(2*tangent, 2*tangent+10, norms[0], jacobians[0], Fraction(0), Fraction(0), Fraction(1)) == (
        _angle_limited_rotation_bound_m_s2(2*tangent, norms[0], jacobians[0], Fraction(1))
    )


@pytest.mark.parametrize("field", range(7))
@pytest.mark.parametrize("invalid", [Fraction(-1), True])
def test_partitioned_rotation_rejects_invalid_bounds(field: int, invalid: object) -> None:
    values: list[object] = [Fraction(1)]*7
    values[field] = invalid
    with pytest.raises(AssertionError):
        _partitioned_rotation_bound_m_s2(*values)  # type: ignore[arg-type] -- boundary rejection.


@pytest.mark.parametrize("case", ["pole-exceeds-full", "zero-radius"])
def test_partitioned_rotation_rejects_inconsistent_domain(case: str) -> None:
    values = [Fraction(1)]*7
    values[0 if case == "pole-exceeds-full" else 6] = Fraction(2 if case == "pole-exceeds-full" else 0)
    with pytest.raises(AssertionError):
        _partitioned_rotation_bound_m_s2(*values)


def _partition_nonmonopole_coefficients(
    cosine: np.ndarray, sine: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Copy dimensionless normalized coefficients into zonal C and nonzonal C/S.

    Degree zero is excluded from both parts and remains with the caller.
    All degrees n>=1, including degree one, are retained without truncation.
    """
    assert cosine.ndim == 2 and cosine.shape == sine.shape and cosine.shape[0] == cosine.shape[1] > 0
    assert all(matrix.dtype == np.float64 and np.all(np.isfinite(matrix)) and not np.any(np.triu(matrix, 1))
               for matrix in (cosine, sine))
    assert not np.any(sine[:, 0])
    zonal = np.zeros_like(cosine)
    zonal[1:, 0] = cosine[1:, 0]
    nonzonal = cosine.copy()
    nonzonal[:, 0] = 0.0
    return zonal, nonzonal, sine.copy()


@pytest.mark.parametrize("degree", [0, 1, 2, 8, 120, 200])
def test_coefficient_partition_is_exact_disjoint_and_nonmutating(degree: int) -> None:
    size = degree + 1
    cosine = np.tril(np.arange(1, size*size + 1, dtype=np.float64).reshape(size, size))
    sine = -cosine.copy()
    sine[:, 0] = 0.0
    original_bytes = cosine.tobytes(), sine.tobytes()
    zonal, nonzonal, nonzonal_sine = _partition_nonmonopole_coefficients(cosine, sine)
    assert np.array_equal(zonal[1:, 0], cosine[1:, 0])
    assert zonal[0, 0] == 0 and not np.any(zonal[:, 1:])
    assert not np.any(nonzonal[:, 0]) and not np.any(nonzonal_sine[:, 0])
    assert np.array_equal(nonzonal[:, 1:], cosine[:, 1:])
    assert np.array_equal(nonzonal_sine, sine)
    assert np.count_nonzero(zonal) == degree
    assert np.count_nonzero(nonzonal) == np.count_nonzero(nonzonal_sine) == degree*(degree + 1)//2
    reconstructed = zonal + nonzonal
    reconstructed[0, 0] = cosine[0, 0]
    assert np.array_equal(reconstructed, cosine)
    assert (cosine.tobytes(), sine.tobytes()) == original_bytes
    assert all(not np.shares_memory(part, source) for part in (zonal, nonzonal, nonzonal_sine)
               for source in (cosine, sine))
    assert not np.shares_memory(zonal, nonzonal)
    assert not np.shares_memory(nonzonal, nonzonal_sine)


@pytest.mark.parametrize("invalid", ["empty", "nonsquare", "mismatch", "boolean", "float32", "nan", "infinity", "upper-c", "upper-s", "zonal-s"])
def test_coefficient_partition_rejects_invalid_input(invalid: str) -> None:
    cosine, sine = np.zeros((3, 3)), np.zeros((3, 3))
    if invalid == "empty":
        cosine = sine = np.zeros((0, 0))
    elif invalid == "nonsquare":
        cosine = sine = np.zeros((2, 3))
    elif invalid == "mismatch":
        sine = np.zeros((2, 2))
    elif invalid in {"boolean", "float32"}:
        cosine = cosine.astype(np.bool_ if invalid == "boolean" else np.float32)
    elif invalid in {"nan", "infinity"}:
        sine[2, 1] = np.nan if invalid == "nan" else np.inf
    elif invalid == "upper-c":
        cosine[0, 1] = 1.0
    elif invalid == "upper-s":
        sine[0, 1] = 1.0
    else:
        sine[2, 0] = 1.0
    with pytest.raises(AssertionError):
        _partition_nonmonopole_coefficients(cosine, sine)


@pytest.mark.parametrize("ra_deg_day,dec_deg_day", [(0.0, 0.0), (1.0, 0.0), (0.0, -2.0), (1.0, -2.0), (-1.0, 2.0)])
@pytest.mark.parametrize("declination_tangent", [Fraction(0), Fraction(1, 2), Fraction(1)])
def test_pole_rate_sum_encloses_exact_spherical_derivative(
    ra_deg_day: float, dec_deg_day: float, declination_tangent: Fraction,
) -> None:
    bound_rad_s = sum((_pck_euler_rate_upper_rad_s((0.0, rate, 0.0), 86400, Fraction(0), (), ())
                       for rate in (ra_deg_day, dec_deg_day)), Fraction(0))
    cosine = (1 - declination_tangent**2) / (1 + declination_tangent**2)
    # Independent derivative of n=(cos(dec)cos(ra), cos(dec)sin(ra), sin(dec)):
    # |n'|^2 = ra'^2*cos(dec)^2 + dec'^2. Exact pi enclosure, rad/s units.
    squared_deg_day = (Fraction(ra_deg_day) * cosine)**2 + Fraction(dec_deg_day)**2
    analytic_upper_squared_rad_s = squared_deg_day * (_pi_rational_bounds()[1] / (180 * 86400))**2
    assert analytic_upper_squared_rad_s <= bound_rad_s**2
    assert (bound_rad_s == 0) is (ra_deg_day == dec_deg_day == 0)


@pytest.mark.parametrize("coordinates_m", [(1, 2, 2), (0, 0, 3), (3, 0, 0)])
@pytest.mark.parametrize("spin_tangent", [Fraction(0), Fraction(1, 1000), Fraction(1, 2), Fraction(1)])
@pytest.mark.parametrize("pole_tangent", [Fraction(0), Fraction(1, 3)])
def test_zonal_force_cancels_spin_but_not_pole_motion(
    coordinates_m: tuple[int, int, int], spin_tangent: Fraction, pole_tangent: Fraction,
) -> None:
    budget = trajectory._RefinementBudget("zonal-spin-symmetry", 300.0)
    position_m = tuple(map(Fraction, coordinates_m))
    radius_m = Fraction(3)
    identity = tuple(tuple(Fraction(i == j) for j in range(3)) for i in range(3))
    # Exact proper rotations using tan(angle/2); no trigonometric roundoff.
    c, s = (1 - spin_tangent**2) / (1 + spin_tangent**2), 2 * spin_tangent / (1 + spin_tangent**2)
    cp, sp = (1 - pole_tangent**2) / (1 + pole_tangent**2), 2 * pole_tangent / (1 + pole_tangent**2)
    spin = ((c, -s, Fraction(0)), (s, c, Fraction(0)), (Fraction(0), Fraction(0), Fraction(1)))
    pole = ((Fraction(1), Fraction(0), Fraction(0)), (Fraction(0), cp, -sp), (Fraction(0), sp, cp))
    spun_pole = tuple(tuple(sum((spin[i][k] * pole[k][j] for k in range(3)), Fraction(0))
                            for j in range(3)) for i in range(3))
    forces: list[dict[tuple[int, int], tuple[Fraction, ...]]] = []
    for matrix in (identity, pole, spun_pole):
        assert all(sum((matrix[k][i] * matrix[k][j] for k in range(3)), Fraction(0)) == identity[i][j]
                   for i in range(3) for j in range(3))
        fixed_m = tuple(sum((a * r for a, r in zip(row, position_m, strict=True)), Fraction(0)) for row in matrix)
        q_m2 = sum((value**2 for value in fixed_m), Fraction(0))
        assert q_m2 == radius_m**2
        terms: dict[tuple[int, int], tuple[Fraction, ...]] = {}
        # Fixture GM=1 m^3/s^2, reference radius=1 m, one unit cosine
        # coefficient at a time. Divide out the common positive normalization.
        for degree, order, real, _ in _regular_solid_harmonic_jets(budget, fixed_m, 8):
            fixed_force_m_s2 = tuple((q_m2 * derivative - (2 * degree + 1) * real[0] * r)
                                     / radius_m**(2 * degree + 3)
                                     for derivative, r in zip(real[1:], fixed_m, strict=True))
            if (degree, order) == (0, 0):
                assert fixed_force_m_s2 == tuple(-r / radius_m**3 for r in fixed_m)
            if (degree, order) == (2, 0):
                # Independent Cartesian gradient of (3*z^2-r^2)/(2*r^5).
                x, y, z = fixed_m
                assert fixed_force_m_s2 == (
                    3*x*(q_m2 - 5*z*z)/(2*radius_m**7),
                    3*y*(q_m2 - 5*z*z)/(2*radius_m**7),
                    3*z*(3*q_m2 - 5*z*z)/(2*radius_m**7),
                )
            terms[degree, order] = tuple(sum((matrix[row][axis] * fixed_force_m_s2[row]
                                             for row in range(3)), Fraction(0)) for axis in range(3))
        assert len(terms) == 45
        forces.append(terms)
    for degree in range(9):
        assert forces[1][degree, 0] == forces[2][degree, 0]
    # Negative controls: spin cancellation does not extend to tesseral
    # terms, nor does zonal symmetry allow pole motion to be discarded.
    if coordinates_m == (3, 0, 0) and spin_tangent == 1 and pole_tangent == 0:
        assert forces[1][2, 2] != forces[2][2, 2]
    if coordinates_m == (0, 0, 3) and pole_tangent != 0:
        assert forces[0][2, 0] != forces[1][2, 0]
    assert budget.native_arc_propagations == 0
