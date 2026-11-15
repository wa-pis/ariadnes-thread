"""Independent Decimal invariants for the ADR0207 point-body impulse worksheet."""

from decimal import Context, Decimal, DecimalException, localcontext

type Vec = tuple[Decimal, Decimal, Decimal]
type TextVec = tuple[str, str, str]

PRECISION = Context(prec=96)
INVARIANT_REL = Decimal("1e-70")


def _dot(a: Vec, b: Vec) -> Decimal:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _cross(a: Vec, b: Vec) -> Vec:
    x, y, z = a
    i, j, k = b
    return (y*k - z*j, z*i - x*k, x*j - y*i)


def _scale(a: Vec, s: Decimal) -> Vec:
    return (s*a[0], s*a[1], s*a[2])


def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _norm(a: Vec) -> Decimal:
    return _dot(a, a).sqrt()


def _unit(a: Vec) -> Vec:
    return _scale(a, 1/_norm(a))


def _text_vec(raw: TextVec) -> Vec:
    x, y, z = raw
    return (Decimal(x), Decimal(y), Decimal(z))


def _relative_match(a: Decimal, b: Decimal) -> bool:
    return abs(a-b) <= INVARIANT_REL * max(abs(a), abs(b))


def _check_branch(r: Vec, v_inf: Vec, orbital: Vec, mu: Decimal, guard: Decimal, signed_h: Vec,
                  *, arrival: bool) -> dict[str, object]:
    radius, w = _norm(r), _norm(v_inf)
    r_hat, u = _unit(r), _unit(v_inf)
    e_inf = _add(_scale(_cross(v_inf, signed_h), 1/mu), _scale(u, Decimal(-1)))
    v = _scale(_cross(signed_h, _add(e_inf, r_hat)), mu/_dot(signed_h, signed_h))
    # Reconstruct invariants from the recovered state, independently of the solved h.
    h = _cross(r, v)
    e = _add(_scale(_cross(v, h), 1/mu), _scale(r_hat, Decimal(-1)))
    w2 = _dot(v, v) - 2*mu/radius
    ecc = _norm(e)
    if (w2 <= 0 or ecc <= 1 or _norm(_add(h, _scale(signed_h, Decimal(-1)))) >
            INVARIANT_REL*_norm(signed_h) or not _relative_match(w2, w*w)):
        return {"reason": "invariant"}
    e_hat, h_hat = _unit(e), _unit(h)
    outgoing = _scale(_add(_scale(e_hat, -1/ecc),
                           _scale(_cross(h_hat, e_hat), (1-1/(ecc*ecc)).sqrt())), w2.sqrt())
    if _norm(_add(outgoing, _scale(v_inf, Decimal(-1)))) > INVARIANT_REL*w:
        return {"reason": "invariant"}

    radial = _dot(v, r_hat)
    radial_kind = ("turning" if abs(radial) <= INVARIANT_REL*_norm(v)
                   else "inward" if radial < 0 else "outward")
    minimum = _dot(h, h)/(mu*(1+ecc)) if radial < 0 else radius
    physical_sign = Decimal(-1 if arrival else 1)
    physical_v = _scale(v, physical_sign)
    impulse = (_add(orbital, _scale(physical_v, Decimal(-1))) if arrival
               else _add(physical_v, _scale(orbital, Decimal(-1))))
    before = physical_v if arrival else orbital
    if _dot(impulse, impulse) == 0 or _dot(before, before) == 0:
        return {"reason": "degenerate"}
    w_axis = _cross(r, before)
    if _dot(w_axis, w_axis) == 0:
        return {"reason": "degenerate"}
    t, w_hat, kick = _unit(before), _unit(w_axis), _unit(impulse)
    return {"reason": "guard" if minimum - guard <= Decimal("0.001") else None,
            "velocity": physical_v, "reconstructed_excess": _scale(outgoing, physical_sign),
            "impulse": impulse, "radius": minimum, "radial": radial_kind,
            "tnw": (_dot(kick, t), _dot(kick, _cross(w_hat, t)), _dot(kick, w_hat)),
            "speed": _norm(impulse)}


def branches(position: TextVec, orbital: TextVec, excess: TextVec, mu: str, guard: str,
             *, arrival: bool) -> dict[str, dict[str, object]]:
    """Invert the signed conic angular momentum and verify each root at 96 digits."""
    degenerate: dict[str, dict[str, object]] = {key: {"reason": "degenerate"}
                                                for key in ("positive", "negative")}
    with localcontext(PRECISION):
        r, orbit_v, given = _text_vec(position), _text_vec(orbital), _text_vec(excess)
        gm, surface = Decimal(mu), Decimal(guard)
        if (not all(x.is_finite() for x in (*r, *orbit_v, *given, gm, surface)) or
                gm <= 0 or surface <= 0 or _dot(r, r) <= 0 or _dot(given, given) <= 0):
            return degenerate
        v_inf = _scale(given, Decimal(-1 if arrival else 1))
        r_hat, direction = _unit(r), _unit(v_inf)
        normal = _cross(r_hat, direction)
        s = _norm(normal)
        if s <= Decimal("1e-8"):
            return degenerate
        # Solve for angular momentum in SI, not the binary64 transverse-speed roots.
        radius = _norm(r)
        linear = _norm(_cross(r, v_inf))
        constant = gm*radius*(1-_dot(r_hat, direction))
        disc = (linear*linear + 4*constant).sqrt()
        axis = _unit(normal)
        result = {}
        for name, root in (("positive", (linear+disc)/2), ("negative", (linear-disc)/2)):
            if root == 0:
                result[name] = {"reason": "degenerate"}
                continue
            try:
                result[name] = _check_branch(r, v_inf, orbit_v, gm, surface,
                                             _scale(axis, root), arrival=arrival)
            except DecimalException:
                result[name] = {"reason": "invariant"}
        return result


def mass(departure_speed: Decimal, arrival_speed: Decimal
         ) -> tuple[tuple[Decimal, Decimal], tuple[Decimal, Decimal]]:
    """Compare sequential ideal burn durations and masses using the frozen binary64 constants."""
    with localcontext(PRECISION):
        exhaust = Decimal.from_float(9.80665 * 450)
        rate = Decimal.from_float(1000 / (9.80665 * 450))
        initial = Decimal(2000)
        coast = initial * (-departure_speed/exhaust).exp()
        final = initial * (-(departure_speed+arrival_speed)/exhaust).exp()
        return ((initial-coast)/rate, (coast-final)/rate), (coast, final)
