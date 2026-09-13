"""Independent point-gravity component oracles, not fresh-state qualification."""

from fractions import Fraction

import numpy as np
import pytest

from test_trajectory_spk import (
    _dyadic_sqrt_bounds, _point_gravity_anchor_error_bound_m_s2, _point_gravity_intervals_m_s2,
)


@pytest.mark.parametrize("direction,radius", [((3, 4, 0), 5), ((-3, 4, -12), 13), ((0, 0, -5), 5)])
@pytest.mark.parametrize("scale", [Fraction(1), Fraction(1, 3), Fraction(2)**600, Fraction(2)**-600])
def test_point_vector_rational_radius(direction: tuple[int, ...], radius: int, scale: Fraction) -> None:
    relative = tuple(scale * value for value in direction)
    actual = _point_gravity_intervals_m_s2(125.0, relative)
    expected = tuple(Fraction(125 * value, radius**3) / scale**2 for value in direction)
    assert all(lo <= value <= hi for (lo, hi), value in zip(actual, expected, strict=True))
    assert all(lo == hi == 0 for (lo, hi), value in zip(actual, direction, strict=True) if value == 0)


@pytest.mark.parametrize("direction", [(1, 1, 0), (-1, 0, 1), (1, -2, 3)])
def test_point_vector_irrational_radius_squared_identity(direction: tuple[int, ...]) -> None:
    relative = tuple(map(Fraction, direction))
    squared_radius = sum(value**2 for value in relative)
    for (lo, hi), coordinate in zip(_point_gravity_intervals_m_s2(3.0, relative), relative, strict=True):
        assert lo <= hi
        if coordinate == 0:
            assert lo == hi == 0
        else:
            assert (lo > 0 if coordinate > 0 else hi < 0)
            # a_i^2 * |r|^6 = GM^2 * r_i^2, independent of the square-root helper.
            small, large = sorted((abs(lo), abs(hi)))
            assert small**2 * squared_radius**3 <= 9 * coordinate**2 <= large**2 * squared_radius**3


@pytest.mark.parametrize("offset_m", [0.0, 1e12])
@pytest.mark.parametrize("direction", [(3.0, -4.0, 0.0), (1.0, 1.0, -1.0)])
@pytest.mark.parametrize("observed", [(0.0, 0.0, 0.0), (-3.0, 4.0, 0.125)])
def test_point_vector_preserves_original_error_reduction(
    offset_m: float, direction: tuple[float, ...], observed: tuple[float, ...],
) -> None:
    ship = np.full(3, offset_m)
    body = ship + np.asarray(direction)
    relative = tuple(Fraction(b) - Fraction(s) for b, s in zip(body, ship, strict=True))
    squared = sum(value**2 for value in relative)
    roots = _dyadic_sqrt_bounds(squared)
    original_error = sum((max(abs(Fraction(value) - Fraction(125)*r/(squared*root)) for root in roots)
                          for value, r in zip(observed, relative, strict=True)), Fraction(0))
    assert _point_gravity_anchor_error_bound_m_s2(125.0, body, ship, np.asarray(observed)) == original_error


@pytest.mark.parametrize("gm", [True, 0.0, -1.0, float("nan"), float("inf")])
def test_point_vector_rejects_invalid_gm(gm: float) -> None:
    with pytest.raises(AssertionError):
        _point_gravity_intervals_m_s2(gm, (Fraction(1),) * 3)


@pytest.mark.parametrize("relative", [(), (Fraction(1),), (Fraction(0),) * 3,
                                      (True, Fraction(0), Fraction(1)),
                                      (1.0, Fraction(0), Fraction(1)),
                                      (float("inf"), Fraction(0), Fraction(1))])
def test_point_vector_rejects_invalid_geometry(relative: tuple[Fraction, ...]) -> None:
    with pytest.raises(AssertionError):
        _point_gravity_intervals_m_s2(1.0, relative)
