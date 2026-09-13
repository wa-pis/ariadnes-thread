"""Stored-matrix source-position bounds; not full-force qualification."""

from fractions import Fraction
import math

import numpy as np
import pytest

from space_nav import trajectory

from test_trajectory_spk import _dyadic_sqrt_bounds, _harmonic_spatial_jacobian_bound_s_inv2


def _stored_harmonic_source_error_bound_m_s2(
    budget: trajectory._RefinementBudget, gm_m3_s2: float, reference_radius_m: float,
    cosine: np.ndarray, sine: np.ndarray, relative_m: tuple[Fraction, ...],
    inertial_to_fixed: np.ndarray, source_error_m: Fraction,
) -> Fraction:
    """Bound source effects in A.T*g(A*r); caller binds epoch/source allowance.

    r is spacecraft minus stored source, SI/J2000. A is held fixed; no
    orthogonality or PCK-error premise. A nonpositive chord floor is unresolved.
    """
    budget.check()
    assert len(relative_m) == 3 and all(isinstance(value, Fraction) for value in relative_m)
    assert isinstance(source_error_m, Fraction) and source_error_m >= 0
    assert inertial_to_fixed.shape == (3, 3) and inertial_to_fixed.dtype == np.float64
    assert np.all(np.isfinite(inertial_to_fixed))
    matrix = tuple(tuple(map(Fraction, row)) for row in inertial_to_fixed)
    norm_upper = sum((abs(value) for row in matrix for value in row), Fraction(0))
    fixed = tuple(sum((a*b for a, b in zip(row, relative_m, strict=True)), Fraction(0)) for row in matrix)
    radius_lower = _dyadic_sqrt_bounds(sum((value**2 for value in fixed), Fraction(0)))[0]
    exact_floor = radius_lower - norm_upper*source_error_m
    assert exact_floor > 0, "stored harmonic source chord is unresolved"
    floor = math.nextafter(float(exact_floor), -math.inf)
    assert math.isfinite(floor) and 0 < Fraction(floor) <= exact_floor
    jacobian = _harmonic_spatial_jacobian_bound_s_inv2(
        budget, gm_m3_s2, reference_radius_m, floor, cosine, sine,
    )
    budget.check()
    return norm_upper**2 * jacobian * source_error_m


@pytest.mark.parametrize("degree", [0, 2, 8])
@pytest.mark.parametrize("scale", [0.5, 1.0, 2.0])
@pytest.mark.parametrize("shift", [Fraction(-1, 128), Fraction(0), Fraction(1, 128)])
def test_stored_source_bound_encloses_exact_scaled_zonal_force(degree: int, scale: float, shift: Fraction) -> None:
    cosine, sine = np.zeros((degree+1, degree+1)), np.zeros((degree+1, degree+1))
    cosine[degree, 0] = 0.125
    bound = _stored_harmonic_source_error_bound_m_s2(
        trajectory._RefinementBudget("source-zonal", 300.0), 1.0, 1.0, cosine, sine,
        (Fraction(0), Fraction(0), Fraction(2)), scale*np.eye(3), abs(shift),
    )
    # At the pole, A=s*I gives s^(-n-1)*[-(n+1)*sqrt(2n+1)*C/r^(n+2)].
    exact_squared = (degree+1)**2*(2*degree+1)*Fraction(0.125)**2 * Fraction(scale)**(-2*degree-2) * (
        Fraction(2)**(-degree-2) - (2-shift)**(-degree-2)
    )**2
    assert exact_squared <= bound**2
    assert (bound == 0) == (shift == 0)


def test_stored_source_bound_requires_both_matrix_factors() -> None:
    epsilon = Fraction(1, 4096)
    bound = _stored_harmonic_source_error_bound_m_s2(
        trajectory._RefinementBudget("source-anisotropic", 300.0), 1.0, 1.0,
        np.ones((1, 1)), np.zeros((1, 1)), (Fraction(0), Fraction(0), Fraction(2)),
        np.diag([16.0, 1.0, 1.0]), epsilon,
    )
    # Shift in x: fixed x=16*epsilon, output x receives the other factor 16.
    # The original force has zero x; squared changed x is exact, no sqrt oracle.
    exact_x_squared = (256*epsilon)**2 / (4+(16*epsilon)**2)**3
    assert (bound/18)**2 < exact_x_squared <= bound**2


@pytest.mark.parametrize("invalid", ["negative-error", "inexact-error", "inexact-position", "matrix-shape", "matrix-nan", "singular", "overlap"])
def test_stored_source_bound_rejects_invalid_or_unresolved_domain(invalid: str) -> None:
    relative = (0.0, Fraction(0), Fraction(2)) if invalid == "inexact-position" else (Fraction(0), Fraction(0), Fraction(2))
    matrix = np.ones((2, 2)) if invalid == "matrix-shape" else np.eye(3)
    if invalid == "matrix-nan":
        matrix[0, 0] = math.nan
    if invalid == "singular":
        matrix[2, 2] = 0.0
    error = -Fraction(1) if invalid == "negative-error" else 0.0 if invalid == "inexact-error" else Fraction(1) if invalid == "overlap" else Fraction(0)
    with pytest.raises(AssertionError):
        _stored_harmonic_source_error_bound_m_s2(
            trajectory._RefinementBudget("source-invalid", 300.0), 1.0, 1.0,
            np.ones((1, 1)), np.zeros((1, 1)), relative, matrix, error,
        )


def test_stored_source_bound_rejects_expired_budget() -> None:
    clock = iter([0.0, 301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _stored_harmonic_source_error_bound_m_s2(
            trajectory._RefinementBudget("source-expired", 300.0, lambda: next(clock)), 1.0, 1.0,
            np.ones((1, 1)), np.zeros((1, 1)), (Fraction(0), Fraction(0), Fraction(2)), np.eye(3), Fraction(0),
        )
