"""Conservative signed-conic exclusions for the closed ADR0218 phase cells."""

from decimal import Decimal
from fractions import Fraction
import math
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
# Interval objects come from the hash-bound scalar kernel.
type Vec = tuple[Any, Any, Any]

_DRY_MARGIN_KG = Fraction(1500)
_EXHAUST = 9.80665 * 450
_RATE = 1000 / _EXHAUST
_E = Fraction(math.nextafter(1e-6, math.inf))


class _Unresolved(ArithmeticError):
    """A denominator, alignment or sign cannot be certified over the cell."""


def _dot(a: Vec, b: Vec) -> Any:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    x, y, z = a
    i, j, k = b
    return y*k - z*j, z*i - x*k, x*j - y*i


def _scale(v: Vec, s: Any) -> Vec:
    return s*v[0], s*v[1], s*v[2]


def _sum(a: Vec, b: Vec) -> Vec:
    return a[0]+b[0], a[1]+b[1], a[2]+b[2]


def _positive(a: Any) -> Any:
    if a.lo <= 0:
        raise _Unresolved("zero-touch denominator")
    return a


def _norm2(v: Vec, interval: ModuleType, independent: bool) -> Any:
    if independent:
        # Treat the two copies of each factor independently in replay.
        # The exact Decimal96 sum of rounded squares is always nonnegative.
        raw = _dot(v, v)
        return interval.box(max(Decimal(0), raw.lo), raw.hi)
    x, y, z = v
    return x.square()+y.square()+z.square()


def _unit(v: Vec, interval: ModuleType, independent: bool) -> Vec:
    return _scale(v, 1/_positive(_norm2(v, interval, independent).sqrt()))


def _ellipse(mars: Row, anomaly: Any, interval: ModuleType, independent: bool) -> tuple[Vec, Vec, Any]:
    # Follow 0213's independent, rounded Decimal96 orbit state operations.
    orbit, box = mars["orbit"], interval.box
    mu = _positive(box(mars["gm_m3_s2"]))
    peri = _positive(box(mars["shape_radius_m"])+box(orbit["periapsis_altitude_m"]))
    e = box(orbit["eccentricity"])
    def trig(angle: Any) -> tuple[Any, Any]:
        finite_sin, finite_cos = interval.oracle_trig(angle)
        if not independent:
            return finite_sin, finite_cos
        exact_sin, exact_cos = interval.sin_cos(angle)
        return interval.hull(finite_sin, exact_sin), interval.hull(finite_cos, exact_cos)

    sin_i, cos_i = trig(box(orbit["inclination_rad"]))
    sin_o, cos_o = trig(box(orbit["raan_rad"]))
    sin_u, cos_u = trig(box(orbit["argument_of_periapsis_rad"])+anomaly)
    sin_nu, cos_nu = trig(anomaly)
    node = cos_o, sin_o, box(0)
    normal = sin_o*sin_i, -cos_o*sin_i, cos_i
    onto_plane = _cross(normal, node)
    radial_hat = _sum(_scale(node, cos_u), _scale(onto_plane, sin_u))
    transverse_hat = _cross(normal, radial_hat)
    a = peri/_positive(1-e)
    p = a*(1-e*e)
    h = _positive((mu*_positive(p)).sqrt())
    radius = p/_positive(1+e*cos_nu)
    u, t = mu*e*sin_nu/h, h/_positive(radius)
    return _scale(radial_hat, radius), _sum(_scale(radial_hat, u), _scale(transverse_hat, t)), mu


def _reverse(mars: Row, r: Vec, mu: Any, sign: str,
             interval: ModuleType, independent: bool) -> Vec:
    # Follow 0208's Decimal96 angular-momentum construction, not the binary64 root
    # formula. The saved arrival excess is in physical time, so reverse it here.
    given = tuple(interval.box(speed) for speed in mars["v_infinity_m_s"])
    v_inf = _scale(given, interval.box(-1))
    r_hat, direction = (_unit(w, interval, independent) for w in (r, v_inf))
    normal = _cross(r_hat, direction)
    if _norm2(normal, interval, independent).sqrt().lo <= Decimal("1e-8"):
        raise _Unresolved("asymptote alignment")
    radius = _norm2(r, interval, independent).sqrt()
    linear = _norm2(_cross(r, v_inf), interval, independent).sqrt()
    constant = mu*radius*(1-_dot(r_hat, direction))
    discriminant_sq = _norm2((linear, interval.box(0), interval.box(0)), interval, independent) + 4*constant
    if discriminant_sq.lo < 0:
        raise _Unresolved("unbounded root discriminant")
    disc = discriminant_sq.sqrt()
    root = (linear+disc)/2 if sign == "positive" else (linear-disc)/2
    if (sign == "positive" and root.lo <= 0) or (sign == "negative" and root.hi >= 0):
        raise _Unresolved("signed root touches zero")
    signed_h = _scale(_unit(normal, interval, independent), root)
    e_inf = _sum(_scale(_cross(v_inf, signed_h), 1/mu), _scale(direction, interval.box(-1)))
    return _scale(_cross(signed_h, _sum(e_inf, r_hat)), mu/_positive(_norm2(signed_h, interval, independent)))


def _clearance(r: Vec, v: Vec, mu: Any, surface: Any, interval: ModuleType,
               independent: bool) -> tuple[Any, Any, Any]:
    radius = _norm2(r, interval, independent).sqrt()
    r_hat = _unit(r, interval, independent)
    radial = _dot(v, r_hat)
    if radial.lo >= 0:
        minimum = radius
    else:
        h = _cross(r, v)
        ecc = _norm2(_sum(_scale(_cross(v, h), 1/mu), _scale(r_hat, interval.box(-1))),
                     interval, independent).sqrt()
        peri = _norm2(h, interval, independent)/(mu*(1+ecc))
        minimum = peri if radial.hi < 0 else interval.box(min(radius.lo, peri.lo), max(radius.hi, peri.hi))
    return minimum - surface, minimum, radial


def dry_floor_exclusion(departure_lower_s: Fraction, arrival_lower_s: Fraction,
                        *, independent: bool = False) -> tuple[bool, Fraction]:
    """Check the strict 1500 kg limit from binary64-oracle duration bounds."""
    td, ta = (max(Fraction(0), x-_E) for x in (departure_lower_s, arrival_lower_s))
    q = Fraction(_RATE)
    used_kg = q*td + q*ta if independent else q*(td+ta)
    return used_kg > _DRY_MARGIN_KG, used_kg


def _mass_exclusion(departure: Any, arrival: Any, interval: ModuleType,
                    independent: bool) -> Row:
    # Reproduce each rounded Decimal operation in 0208.mass, then enclose its
    # conversion to the binary64 comparison duration (not the command duration).
    init = interval.box(2000)
    coast = init*(-departure/interval.box(_EXHAUST)).exp()
    final = init*(-(departure+arrival)/interval.box(_EXHAUST)).exp()
    rate = interval.box(_RATE)
    durations = ((init-coast)/rate, (coast-final)/rate)
    conversion_lower = tuple(interval.binary64_lower(d.lo) for d in durations)
    excluded, used_kg = dry_floor_exclusion(*(Fraction(x) for x in conversion_lower), independent=independent)
    return dict(reason="mass" if excluded else None,
                duration_comparison_lower_words=[x.hex() for x in conversion_lower],
                consumed_mass_lower_kg=str(used_kg))


def bounds(ref: Row, lo: Fraction, hi: Fraction, sign: str, interval: ModuleType,
           *, independent: bool = False) -> Row:
    """Enclose a single sign on one closed cell; uncertainty never excludes."""
    if (sign not in ("positive", "negative") or not isinstance(lo, Fraction)
        or not isinstance(hi, Fraction) or not 150 <= lo <= hi <= 152
        or any(x.denominator & (x.denominator-1) for x in (lo, hi))):
        raise ValueError("invalid signed dyadic phase cell")
    mars = ref["normalized"]["endpoints"][1]
    lunar = Decimal(ref["lunar"]["independent_speed_m_s"])
    if mars["body"] != "Mars" or not lunar.is_finite() or lunar <= 0:
        raise ValueError("invalid fixed conic evidence")
    try:
        ldeg, hdeg = (interval.box(x.numerator)/x.denominator for x in (lo, hi))
        pi = interval.hull(interval.PI, interval.box(interval.ORACLE_PI))
        anomaly = 2*pi*interval.box(ldeg.lo, hdeg.hi)/360
        r, orbital, mu = _ellipse(mars, anomaly, interval, independent)
        future = _reverse(mars, r, mu, sign, interval, independent)
        # The physical arrival velocity is -future. Thus v_target-v_arrival is
        # v_target+future; retain all vector components until the impulse norm.
        speed = _norm2(_sum(orbital, future), interval, independent).sqrt()
        proof = _mass_exclusion(interval.box(lunar), speed, interval, independent)
        proof["arrival_speed_bounds_m_s"] = [str(speed.lo), str(speed.hi)]
        if proof["reason"] == "mass":
            return proof
        clearance, minimum, radial = _clearance(
            r, future, mu, interval.box(mars["guard_m"]), interval, independent)
        return proof | dict(reason="guard" if clearance.hi < Decimal("0.001") else None,
                            clearance_upper_m=str(clearance.hi), minimum_radius_upper_m=str(minimum.hi),
                            reverse_radial_bounds_m_s=[str(radial.lo), str(radial.hi)])
    except ArithmeticError as error:
        return dict(reason=None, detail=str(error))


def validate_claim(claim: Row) -> None:
    """Reject malformed saved proof arithmetic before recomputing the exclusions."""
    reason = claim["reason"]
    if reason == "mass":
        words = claim["duration_comparison_lower_words"]
        durations = tuple(float.fromhex(word) for word in words)
        if (len(durations) != 2 or not all(math.isfinite(x) for x in durations)
                or [x.hex() for x in durations] != words):
            raise ValueError("noncanonical proof duration")
        excluded, used = dry_floor_exclusion(*(Fraction(x) for x in durations))
        if not excluded or str(used) != claim["consumed_mass_lower_kg"]:
            raise ValueError("invalid saved mass proof")
    elif reason == "guard":
        upper = Decimal(claim["clearance_upper_m"])
        if not upper.is_finite() or not upper < Decimal("0.001"):
            raise ValueError("invalid saved clearance proof")
