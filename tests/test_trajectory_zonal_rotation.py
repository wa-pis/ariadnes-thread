"""Exact ideal zonal spin symmetry, not a native PCK arithmetic certificate."""

from fractions import Fraction

import pytest

from space_nav import trajectory
from test_trajectory_spk import _regular_solid_harmonic_jets


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
