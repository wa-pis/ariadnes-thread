"""Bounded-significand arithmetic controls; not a qualified force evaluator."""

from fractions import Fraction

import pytest


def _outward_dyadic(value: Fraction, bits: int) -> tuple[Fraction, Fraction]:
    """Enclose an exact rational with at most bits binary significant digits.

    Exponents are unbounded. This limits significands, not absolute integer
    storage or the width accumulated by a subsequent interval calculation.
    """
    assert isinstance(value, Fraction)
    assert type(bits) is int and bits > 0
    if not value:
        return Fraction(0), Fraction(0)
    magnitude = abs(value)
    exponent = magnitude.numerator.bit_length() - magnitude.denominator.bit_length()
    if magnitude < Fraction(2)**exponent:
        exponent -= 1
    step = Fraction(2)**(exponent - bits + 1)
    scaled = value / step
    return (scaled.numerator // scaled.denominator) * step, (-(-scaled.numerator // scaled.denominator)) * step


@pytest.mark.parametrize("bits", [1, 24, 53, 80, 120])
@pytest.mark.parametrize("value", [Fraction(0), Fraction(1), Fraction(-1), Fraction(1, 3),
                                  Fraction(-1, 3), Fraction(7, 8), Fraction(-7, 8),
                                  Fraction(2)**-1074, Fraction(2)**1024,
                                  Fraction(2)**80 + Fraction(1, 7)])
def test_dyadic_outward_rounding(value: Fraction, bits: int) -> None:
    lower, upper = _outward_dyadic(value, bits)
    assert lower <= value <= upper
    assert _outward_dyadic(-value, bits) == (-upper, -lower)
    for endpoint in (lower, upper):
        assert endpoint.denominator & (endpoint.denominator - 1) == 0
        numerator = abs(endpoint.numerator)
        if numerator:
            odd_part = numerator // (numerator & -numerator)
            assert odd_part.bit_length() <= bits
        assert _outward_dyadic(endpoint, bits) == (endpoint, endpoint)
    if value:
        # Independent relative-width upper bound, including binade boundaries.
        assert upper - lower <= abs(value) * Fraction(2)**(1 - bits)


@pytest.mark.parametrize("value,bits", [(0.5, 53), (Fraction(1), True),
                                       (Fraction(1), 0), (Fraction(1), -1)])
def test_dyadic_rounding_rejects_invalid_input(value: object, bits: object) -> None:
    with pytest.raises(AssertionError):
        _outward_dyadic(value, bits)  # type: ignore[arg-type] -- rejection control.


@pytest.mark.parametrize("bits", [24, 53, 80, 120])
@pytest.mark.parametrize("x", [Fraction(-9, 10), Fraction(0), Fraction(1, 3), Fraction(9, 10)])
def test_rounded_horner_encloses_exact_degree_120_polynomial(bits: int, x: Fraction) -> None:
    # Manufactured polynomial, not a gravity recurrence or timing benchmark.
    # Four-corner multiplication handles negative and zero-crossing intervals.
    x_bounds = _outward_dyadic(x, bits)
    lower = upper = exact = Fraction(0)
    for degree in range(121):
        coefficient = Fraction((-1)**degree, degree + 7)
        products = [a*b for a in (lower, upper) for b in x_bounds]
        lower = _outward_dyadic(min(products) + coefficient, bits)[0]
        upper = _outward_dyadic(max(products) + coefficient, bits)[1]
        exact = exact*x + coefficient
        assert lower <= exact <= upper, degree
        # Endpoints stay bounded in significand size at EVERY operation.
        assert _outward_dyadic(lower, bits) == (lower, lower)
        assert _outward_dyadic(upper, bits) == (upper, upper)
    assert upper - lower < Fraction(1, 1000)


def test_rounding_does_not_erase_cancellation_uncertainty() -> None:
    value = Fraction(1, 3)
    lower, upper = _outward_dyadic(value, 24)
    # Two occurrences treated independently: their enclosure cannot collapse
    # to zero just because the exact symbolic difference is zero.
    difference = (lower - upper, upper - lower)
    assert difference[0] < value - value < difference[1]
