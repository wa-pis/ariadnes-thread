"""Bounded-significand arithmetic controls; not a qualified force evaluator."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class _DyadicInterval:
    """Only the arithmetic required by the existing solid-harmonic recurrence.

    No square roots or interval division: this is not a force evaluator.
    """

    lower: Fraction
    upper: Fraction
    bits: int

    def __post_init__(self) -> None:
        assert isinstance(self.lower, Fraction) and isinstance(self.upper, Fraction)
        assert self.lower <= self.upper
        assert type(self.bits) is int and self.bits > 0
        object.__setattr__(self, "lower", _outward_dyadic(self.lower, self.bits)[0])
        object.__setattr__(self, "upper", _outward_dyadic(self.upper, self.bits)[1])

    def _coerce(self, other: _DyadicInterval | Fraction | int) -> _DyadicInterval:
        if isinstance(other, _DyadicInterval):
            assert self.bits == other.bits
            return other
        assert isinstance(other, Fraction) or type(other) is int
        return _DyadicInterval(Fraction(other), Fraction(other), self.bits)

    def __add__(self, other: _DyadicInterval | Fraction | int) -> _DyadicInterval:
        other = self._coerce(other)
        return _DyadicInterval(self.lower + other.lower, self.upper + other.upper, self.bits)

    __radd__ = __add__

    def __neg__(self) -> _DyadicInterval:
        return _DyadicInterval(-self.upper, -self.lower, self.bits)

    def __sub__(self, other: _DyadicInterval | Fraction | int) -> _DyadicInterval:
        return self + -self._coerce(other)

    def __rsub__(self, other: Fraction | int) -> _DyadicInterval:
        return self._coerce(other) + -self

    def __mul__(self, other: _DyadicInterval | Fraction | int) -> _DyadicInterval:
        other = self._coerce(other)
        products = [a*b for a in (self.lower, self.upper) for b in (other.lower, other.upper)]
        return _DyadicInterval(min(products), max(products), self.bits)

    __rmul__ = __mul__

    def __truediv__(self, other: int) -> _DyadicInterval:
        assert type(other) is int and other > 0
        return _DyadicInterval(self.lower / other, self.upper / other, self.bits)

    def __pow__(self, exponent: int) -> _DyadicInterval:
        assert type(exponent) is int and exponent == 2
        # Dependency-safe four-corner enclosure, possibly loose across zero.
        return self * self


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
