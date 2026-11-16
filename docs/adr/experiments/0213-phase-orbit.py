"""Reconstruct a fixed Mars ellipse at one of 360 phases in SI/J2000."""

from decimal import Context, Decimal, InvalidOperation, localcontext
import math
from typing import Any

type Row = dict[str, Any]
type V3 = tuple[float, float, float]
type D3 = tuple[Decimal, Decimal, Decimal]

COUNT = 360
POSITION_M = 0.001
VELOCITY_M_S = 1e-6
_PRECISION = Context(prec=96)
_PI = Decimal("3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679821480865132823")
_CONVERGENCE = Decimal("1e-99")
_INVARIANT_REL = Decimal("1e-80")


def _number(value: object) -> float:
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError("orbit state requires finite numeric metadata")
    return float(value)


def _vector(raw: object) -> tuple[float, ...]:
    if not isinstance(raw, (tuple, list)) or len(raw) != 6:
        raise ValueError("orbit state requires a six-component state")
    return tuple(_number(x) for x in raw)


def _exact_vector(raw: object) -> tuple[Decimal, ...]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 6:
        raise ValueError("orbit state requires a six-component decimal state")
    values = []
    for word in raw:
        if type(word) is not str or not 1 <= len(word) <= 256:
            raise ValueError("invalid decimal state component")
        number = Decimal(word)
        if not number.is_finite() or abs(number.adjusted()) > 400:
            raise ValueError("unbounded decimal state component")
        values.append(number)
    return tuple(values)


def _dot(a: D3, b: D3) -> Decimal:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _cross(a: D3, b: D3) -> D3:
    x, y, z = a
    u, v, w = b
    return y*w - z*v, z*u - x*w, x*v - y*u


def _rotate(x: float, y: float, p_hat: V3, q_hat: V3) -> V3:
    return tuple(x*a + y*b for a, b in zip(p_hat, q_hat, strict=True))


def _trig(angle: Decimal) -> tuple[Decimal, Decimal]:
    """Evaluate sin/cos via Taylor recurrences after quadrant reduction."""
    pi = +_PI
    x = angle % (2*pi)
    if x > pi:
        x -= 2*pi
    sign = 1
    if x > pi/2:
        x = pi - x
        sign = -1
    if x < -pi/2:
        x = -pi - x
        sign = -1
    x_sq = x*x
    t_sin, t_cos = x, Decimal(1)
    sine, cosine = t_sin, t_cos
    for j in range(2, 256, 2):
        t_sin *= -x_sq / (j*(j+1))
        t_cos *= -x_sq / (j*(j-1))
        sine += t_sin
        cosine += t_cos
        if max(abs(t_sin), abs(t_cos)) < _CONVERGENCE:
            return sine, sign*cosine
    raise ValueError("independent phase trigonometry did not converge")


def _local_state(mu_m3_s2: float, periapsis_m: float, eccentricity: float,
                 inc_rad: float, node_rad: float, arg_rad: float, phase_rad: float) -> tuple[float, ...]:
    ci, si = math.cos(inc_rad), math.sin(inc_rad)
    co, so = math.cos(node_rad), math.sin(node_rad)
    cw, sw = math.cos(arg_rad), math.sin(arg_rad)
    cv, sv = math.cos(phase_rad), math.sin(phase_rad)
    p_hat = co*cw - so*sw*ci, so*cw + co*sw*ci, sw*si
    q_hat = -co*sw - so*cw*ci, -so*sw + co*cw*ci, cw*si
    p_m = periapsis_m*(1 + eccentricity)
    radius_m = p_m/(1 + eccentricity*cv)
    velocity_scale_m_s = math.sqrt(mu_m3_s2/p_m)
    return (*_rotate(radius_m*cv, radius_m*sv, p_hat, q_hat),
            *_rotate(-velocity_scale_m_s*sv, velocity_scale_m_s*(eccentricity + cv), p_hat, q_hat))


def _oracle_state(mu_m3_s2: Decimal, periapsis_m: Decimal, eccentricity: Decimal,
                  inc_rad: Decimal, node_rad: Decimal, arg_rad: Decimal,
                  index: int) -> tuple[Decimal, ...]:
    nu = 2*_PI*index / COUNT
    sin_i, cos_i = _trig(inc_rad)
    sin_o, cos_o = _trig(node_rad)
    sin_u, cos_u = _trig(arg_rad + nu)
    sin_w, cos_w = _trig(arg_rad)
    sin_nu, cos_nu = _trig(nu)
    node = cos_o, sin_o, Decimal(0)
    normal = sin_o*sin_i, -cos_o*sin_i, cos_i
    onto_plane = _cross(normal, node)
    radial_hat = tuple(cos_u*a + sin_u*b for a, b in zip(node, onto_plane, strict=True))
    transverse_hat = _cross(normal, radial_hat)
    peri_hat = tuple(cos_w*a + sin_w*b for a, b in zip(node, onto_plane, strict=True))
    semi_major_m = periapsis_m/(1 - eccentricity)
    p_m = semi_major_m*(1 - eccentricity*eccentricity)
    h_expected_m2_s = (mu_m3_s2*p_m).sqrt()
    radius_m = p_m/(1 + eccentricity*cos_nu)
    radial_m_s = mu_m3_s2*eccentricity*sin_nu/h_expected_m2_s
    transverse_m_s = h_expected_m2_s/radius_m
    position = tuple(radius_m*x for x in radial_hat)
    velocity = tuple(radial_m_s*a + transverse_m_s*b for a, b in zip(radial_hat, transverse_hat, strict=True))

    h = _cross(position, velocity)
    radius = _dot(position, position).sqrt()
    energy = _dot(velocity, velocity)/2 - mu_m3_s2/radius
    energy_expected = -mu_m3_s2/(2*semi_major_m)
    eccentricity_vec = tuple(u/mu_m3_s2 - v/radius
                             for u, v in zip(_cross(velocity, h), position, strict=True))
    if (abs(energy - energy_expected) > abs(energy_expected)*_INVARIANT_REL
        or any(abs(x - h_expected_m2_s*y) > h_expected_m2_s*_INVARIANT_REL
               for x, y in zip(h, normal, strict=True))
        or any(abs(x - eccentricity*y) > _INVARIANT_REL
               for x, y in zip(eccentricity_vec, peri_hat, strict=True))):
        raise ValueError("independent Mars energy, angular momentum or eccentricity failed")
    return (*position, *velocity)


def _discrepancy(actual: tuple[Decimal, ...], expected: tuple[Decimal, ...]) -> tuple[float, float]:
    d = tuple(x - y for x, y in zip(actual, expected, strict=True))
    position = sum(x*x for x in d[:3]).sqrt()
    velocity = sum(x*x for x in d[3:]).sqrt()
    if position > Decimal("0.001") or velocity > Decimal("1e-6"):
        raise ValueError("Mars phase state exceeds 0.001 m / 1e-6 m/s reconstruction gates")
    return float(position), float(velocity)


def state(endpoint: Row, index: int) -> Row:
    """Compare the binary64 perifocal and 96-digit radial/transverse Mars state."""
    if type(index) is not int or not 0 <= index < COUNT:
        raise ValueError("Mars phase must use a canonical grid index")
    try:
        orbit = endpoint["orbit"]
        if (not isinstance(orbit, dict) or endpoint["body"] != "Mars" or endpoint["label"] != "arrival-cutoff"
            or orbit["central_body"] != "Mars" or _number(orbit["true_anomaly_rad"]) != 0):
            raise ValueError("Mars phase requires original zero-phase arrival-cutoff boundary")
        mu = _number(endpoint["gm_m3_s2"])
        shape = _number(endpoint["shape_radius_m"])
        peri_alt = _number(orbit["periapsis_altitude_m"])
        apo_alt = _number(orbit["apoapsis_altitude_m"])
        e = _number(orbit["eccentricity"])
        incidence, node, arg = (_number(orbit[k]) for k in (
            "inclination_rad", "raan_rad", "argument_of_periapsis_rad"))
        if not (mu > 0 and shape > 0 and 0 <= peri_alt <= apo_alt and 0 <= e < 1
                and 0 <= incidence <= math.pi and 0 <= node < math.tau and 0 <= arg < math.tau):
            raise ValueError("invalid Mars ellipse or frozen orientation")
        body = _vector(endpoint["body_ssb_si"])
        angle = math.tau*index/COUNT
        relative = _local_state(mu, shape + peri_alt, e, incidence, node, arg, angle)
        ssb = tuple(a + b for a, b in zip(relative, body, strict=True))
        if not all(math.isfinite(x) for x in (*relative, *ssb)):
            raise ValueError("nonfinite Mars phase reconstruction")
        with localcontext(_PRECISION):
            periapsis = Decimal(shape) + Decimal(peri_alt)
            apoapsis = Decimal(shape) + Decimal(apo_alt)
            eccentricity = Decimal(e)
            if abs(periapsis*(1 + eccentricity)/(1 - eccentricity) - apoapsis) > Decimal("0.001"):
                raise ValueError("archived Mars apsides disagree with binding eccentricity")
            ref = _oracle_state(Decimal(mu), periapsis, eccentricity, Decimal(incidence),
                                Decimal(node), Decimal(arg), index)
            ref_ssb = tuple(x + Decimal(y) for x, y in zip(ref, body, strict=True))
            local = tuple(map(Decimal, relative))
            absolute = tuple(map(Decimal, ssb))
            d_r, d_v = _discrepancy(local, ref)
            d_r_ssb, d_v_ssb = _discrepancy(absolute, ref_ssb)
            if index == 0:
                archived = _exact_vector(endpoint["relative_si"])
                archived_ssb = tuple(map(Decimal, _vector(endpoint["endpoint_ssb_si"])))
                for observed, expected in ((local, archived), (ref, archived),
                                           (absolute, archived_ssb), (ref_ssb, archived_ssb)):
                    _discrepancy(observed, expected)
            return dict(index=index, angle_word=angle.hex(), relative_si=relative, ssb_si=ssb,
                        independent_relative_si=tuple(map(str, ref)),
                        discrepancies=dict(relative_position_m=d_r, relative_velocity_m_s=d_v,
                                           ssb_position_m=d_r_ssb, ssb_velocity_m_s=d_v_ssb))
    except (KeyError, TypeError, InvalidOperation, OverflowError, ZeroDivisionError) as exc:
        raise ValueError("invalid Mars orbit-state evidence") from exc
