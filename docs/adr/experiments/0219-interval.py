"""Outward scalar bounds for real and rounded Decimal96 operations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Context, Decimal
from fractions import Fraction
import math

type Number = Decimal | int | float | str

_LO = Context(prec=96, rounding=ROUND_FLOOR)
_HI = Context(prec=96, rounding=ROUND_CEILING)
_NEAREST = Context(prec=96, rounding=ROUND_HALF_EVEN)
_ZERO = Decimal(0)
_CONVERGENCE = Decimal("1e-99")
# Historical 0213 input literal and rounded quadrant-reduction constant.
ORACLE_PI = Decimal("3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679821480865132823")


def _dec(value: Number) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if type(value) is float:
        return Decimal.from_float(value)
    if type(value) in (str, int):
        return Decimal(value)
    raise TypeError("expected an exact scalar")


@dataclass(frozen=True, slots=True)
class Interval:
    """Closed finite bounds; arithmetic encloses exact and nearest-rounded results."""

    lo: Decimal
    hi: Decimal

    def __post_init__(self) -> None:
        if not (self.lo.is_finite() and self.hi.is_finite() and self.lo <= self.hi):
            raise ValueError("empty or nonfinite interval")

    def __add__(self, other: I | Number) -> I:
        b = _coerce(other)
        return I(_LO.add(self.lo, b.lo), _HI.add(self.hi, b.hi))

    __radd__ = __add__

    def __sub__(self, other: I | Number) -> I:
        b = _coerce(other)
        return I(_LO.subtract(self.lo, b.hi), _HI.subtract(self.hi, b.lo))

    def __rsub__(self, other: I | Number) -> I:
        return _coerce(other) - self

    def __neg__(self) -> I:
        return I(_LO.minus(self.hi), _HI.minus(self.lo))

    def __mul__(self, other: I | Number) -> I:
        b = _coerce(other)
        corners = tuple((x, y) for x in (self.lo, self.hi) for y in (b.lo, b.hi))
        return I(min(_LO.multiply(x, y) for x, y in corners),
                 max(_HI.multiply(x, y) for x, y in corners))

    __rmul__ = __mul__

    def __truediv__(self, other: I | Number) -> I:
        b = _coerce(other)
        if b.lo <= 0 <= b.hi:
            raise ValueError("interval divisor includes zero")
        corners = tuple((x, y) for x in (self.lo, self.hi) for y in (b.lo, b.hi))
        return I(min(_LO.divide(x, y) for x, y in corners),
                 max(_HI.divide(x, y) for x, y in corners))

    def __rtruediv__(self, other: I | Number) -> I:
        return _coerce(other) / self

    def abs(self) -> I:
        hi = max(_HI.abs(self.lo), _HI.abs(self.hi))
        lo = _ZERO if self.lo <= 0 <= self.hi else min(_LO.abs(self.lo), _LO.abs(self.hi))
        return I(lo, hi)

    def square(self) -> I:
        a = self.abs()
        return I(_LO.multiply(a.lo, a.lo), _HI.multiply(a.hi, a.hi))

    def sqrt(self) -> I:
        if self.lo < 0:
            raise ValueError("interval square root includes negative numbers")
        lo = _ZERO if self.lo.is_zero() else _NEAREST.next_minus(_NEAREST.sqrt(self.lo))
        hi = _ZERO if self.hi.is_zero() else _NEAREST.next_plus(_NEAREST.sqrt(self.hi))
        return I(max(_ZERO, lo), hi)

    def exp(self) -> I:
        lo = _NEAREST.next_minus(_NEAREST.exp(self.lo))
        hi = _NEAREST.next_plus(_NEAREST.exp(self.hi))
        return I(max(_ZERO, lo), hi)

    def binary64(self) -> I:
        """Bind both the real interval and values rounded to binary64."""
        return box(binary64_lower(self.lo), binary64_upper(self.hi))


I = Interval  # noqa: E741 - short alias used by the interval geometry


def box(lo: Number, hi: Number | None = None) -> I:
    """Construct endpoints exactly, including the exact value of a float."""
    left = _dec(lo)
    return I(left, left if hi is None else _dec(hi))


def _coerce(value: I | Number) -> I:
    return value if isinstance(value, I) else box(value)


def hull(*values: I) -> I:
    return I(min(r.lo for r in values), max(r.hi for r in values))


def rational(value: Fraction) -> I:
    return box(value.numerator) / value.denominator


def _binary64(value: Decimal, upward: bool) -> float:
    nearest = float(value)
    if not math.isfinite(nearest):
        raise ValueError("binary64 conversion overflow")
    decimal_value = Decimal.from_float(nearest)
    if (upward and decimal_value < value) or (not upward and decimal_value > value):
        nearest = math.nextafter(nearest, math.inf if upward else -math.inf)
    if not math.isfinite(nearest):
        raise ValueError("no finite binary64 enclosure")
    return nearest


def binary64_lower(value: Decimal) -> float:
    return _binary64(value, False)


def binary64_upper(value: Decimal) -> float:
    return _binary64(value, True)


def _atan_reciprocal(q: int, count: int) -> tuple[Fraction, Fraction]:
    # Alternating arctan series; the exact sum and next partial sum bracket.
    result = sum((Fraction((-1)**j, (2*j+1)*q**(2*j+1)) for j in range(count)), Fraction())
    next_sum = result + Fraction((-1)**count, (2*count+1)*q**(2*count+1))
    return min(result, next_sum), max(result, next_sum)


def _pi() -> I:
    a, b = _atan_reciprocal(5, 96)
    c, d = _atan_reciprocal(239, 32)
    # Machin's identity (principal positive angle).
    return I(rational(16*a-4*d).lo, rational(16*b-4*c).hi)


PI = _pi()
_PI_ORACLE = box(_NEAREST.plus(ORACLE_PI))


def _clip(v: I, lo: Decimal, hi: Decimal) -> I | None:
    a, b = max(v.lo, lo), min(v.hi, hi)
    return I(a, b) if a <= b else None


def _reduce(angle: I, p: I) -> list[tuple[I, int]]:
    """Enclose both sides of each possible reduction boundary."""
    period = p*2
    ratio = angle/period
    lower, upper = int(ratio.lo), int(ratio.hi)
    if lower < -4 or upper > 4:
        raise ValueError("angle outside supported quadrant enumeration")
    ranges = []
    half = p/2
    for quotient in range(lower, upper+1):
        # Decimal remainder truncates the quotient toward zero. Keep all
        # possible quotients when the input cell straddles a multiple of 2π.
        x = _clip(angle - quotient*period, period.hi.copy_negate(), period.hi)
        if x is None:
            continue
        parts = []
        v = _clip(x, x.lo, p.hi)
        if v is not None:
            parts.append(v)
        v = _clip(x, p.lo, x.hi)
        if v is not None:
            parts.append(v-period)
        for center in parts:
            v = _clip(center, half.hi.copy_negate(), half.hi)
            if v is not None:
                ranges.append((v, 1))
            v = _clip(center, half.lo, center.hi)
            if v is not None:
                ranges.append((p-v, -1))
            v = _clip(center, center.lo, half.lo.copy_negate())
            if v is not None:
                ranges.append((-p-v, -1))
    return ranges


def _taylor(x: I, oracle: bool) -> tuple[I, I]:
    # The historical remainder is signed: a negative argument may
    # reduce to an argument as large as pi after its final reflection.
    if x.abs().hi > Decimal("3.142"):
        raise ValueError("range reduction did not bound the Taylor argument")
    x_sq = x.square()
    t_sin, t_cos = x, box(1)
    sin, cos = t_sin, t_cos
    stopped: list[tuple[I, I]] = []
    for j in range(2, 256, 2):
        t_sin *= -x_sq/(j*(j+1))
        t_cos *= -x_sq/(j*(j-1))
        sin, cos = sin+t_sin, cos+t_cos
        if oracle:
            # The historical stop test is point-dependent. All possible
            # terminating partial sums must be enclosed, even across zero.
            if max(t_sin.abs().lo, t_cos.abs().lo) < _CONVERGENCE:
                stopped.append((sin, cos))
            if max(t_sin.abs().hi, t_cos.abs().hi) < _CONVERGENCE:
                return hull(*(s for s, _ in stopped)), hull(*(c for _, c in stopped))
        else:
            # Alternating series tail after the retained terms is bounded by
            # the first omitted term; magnitudes decrease on the reduced range.
            rs = (t_sin*x_sq/((j+2)*(j+3))).abs().hi
            rc = (t_cos*x_sq/((j+2)*(j+1))).abs().hi
            if max(rs, rc) < _CONVERGENCE:
                return sin+box(rs.copy_negate(), rs), cos+box(rc.copy_negate(), rc)
    raise ValueError("Taylor tail or historical stopping point was not enclosed")


def _sin_cos(angle: I, p: I, oracle: bool) -> tuple[I, I]:
    ranges = [(_taylor(x, oracle), sign) for x, sign in _reduce(angle, p)]
    return (hull(*(sin for (sin, _), _ in ranges)),
            hull(*(sign*cos for (_, cos), sign in ranges)))


def sin_cos(angle: I) -> tuple[I, I]:
    """Enclose mathematical sine and cosine, including the Taylor remainder."""
    return _sin_cos(angle, PI, False)


def oracle_trig(angle: I) -> tuple[I, I]:
    """Enclose 0213's rounded 96-digit trigonometric recurrence and stop test."""
    return _sin_cos(angle, _PI_ORACLE, True)
