"""R5.59b: bounded command arithmetic for artificial endpoint packets only."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import math
from types import ModuleType
from typing import Any

type Row = dict[str, Any]  # Serialized evidence
type Vector = tuple[float, float, float]
type ExactVector = tuple[str, str, str]
type Controls = tuple[float, float, float, float, float, float]

NAMES = ("r1", "r4", "audit", "baseline", "fractions", "contract")
SIGNS = ("positive", "negative")
INPUT_CAP = 512 * 1024
EXHAUST_M_S = 9.80665 * 450
RATE_KG_S = 1000 / EXHAUST_M_S
VELOCITY_LIMIT_M_S = 1e-6
RADIUS_LIMIT_M = 0.001
DURATION_LIMIT_S = 1e-6
MASS_LIMIT_KG = 1e-8
RANK_GAP_M_S = 4e-6


class Unavailable(ValueError):
    """No independently established artificial seed can be returned."""


@dataclass(frozen=True, slots=True)
class Branch:
    """A physical-time velocity and impulse at a fixed endpoint."""

    velocity: Vector
    reconstructed_excess: Vector
    impulse: Vector
    radius: float
    radial: str
    tnw: Vector
    speed: float
    reason: str | None


def wire(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: object) -> str:
    return sha256(wire(value)).hexdigest()


def unique(pairs: list[tuple[str, Any]]) -> Row:
    result: Row = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate input key")
        result[key] = value
    return result


def number(value: object) -> float:
    if type(value) not in (int, float):
        raise ValueError("numeric binary64 field required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite input")
    return result


def exact(text: object) -> Fraction:
    if not isinstance(text, str) or not 1 <= len(text) <= 256:
        raise ValueError("invalid decimal word")
    value = Decimal(text)
    if not value.is_finite() or abs(value.adjusted()) > 400:
        raise ValueError("nonfinite or unbounded decimal word")
    return Fraction(value)


def vec(values: Any) -> Vector:
    a, b, c = values
    return number(a), number(b), number(c)


def fv(values: Any) -> Vector:
    return vec(tuple(float(x) for x in values))


def cross(a: Vector, b: Vector) -> Vector:
    return a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]


def dot(a: Vector, b: Vector) -> float:
    return math.fsum(x*y for x, y in zip(a, b, strict=True))


def scale(a: Vector, k: float) -> Vector:
    return a[0]*k, a[1]*k, a[2]*k


def add(a: Vector, b: Vector) -> Vector:
    return a[0]+b[0], a[1]+b[1], a[2]+b[2]


def unit(a: Vector) -> Vector:
    norm = math.hypot(*a)
    if norm <= 0 or not math.isfinite(norm):
        raise Unavailable("singular vector basis")
    return scale(a, 1 / norm)


def controls(values: Any) -> Controls:
    a, e, d, b, f, g = map(number, values)
    if not all(-math.pi <= x < math.pi for x in (a, b)) or not all(abs(x) <= math.pi/2 for x in (e, f)):
        raise ValueError("noncanonical command")
    if min(d, g) <= 0:
        raise ValueError("nonpositive command duration")
    return a, e, d, b, f, g


def float_branches(r_vec: Vector, orbital: Vector, v_inf: Vector, mu: float, guard: float,
                   *, arrival: bool) -> dict[str, Branch | None]:
    """Construct both signed roots; None denotes globally degenerate geometry."""
    r = math.hypot(*r_vec)
    w = math.hypot(*v_inf)
    if min(r, w, mu, guard) <= 0:
        return dict.fromkeys(SIGNS)
    n = unit(r_vec)
    u = scale(unit(v_inf), -1 if arrival else 1)
    c, s = dot(n, u), math.hypot(*cross(n, u))
    if s <= 1e-8:
        return dict.fromkeys(SIGNS)
    tangent = unit(cross(unit(cross(n, u)), n))
    constant = (mu/r) * (math.dist(u, n)**2 / 2)
    high = (w*s + math.hypot(w*s, 2*math.sqrt(constant))) / 2
    result = {}
    for label, vt in zip(SIGNS, (high, -constant/high), strict=True):
        vr = w*c + (mu/r)*s/vt
        future = add(scale(n, vr), scale(tangent, vt))
        h = cross(r_vec, future)
        e = add(scale(cross(future, h), 1/mu), scale(n, -1))
        e_norm = math.hypot(*e)
        excess_sq = dot(future, future) - 2*mu/r
        if e_norm <= 1 or excess_sq <= 0:
            raise Unavailable(f"nonhyperbolic-{label}")
        e_unit = unit(e)
        asymptote = add(scale(e_unit, -1/e_norm),
                        scale(cross(unit(h), e_unit), math.sqrt(1 - 1/e_norm**2)))
        signed = -1 if arrival else 1
        reconstructed = scale(asymptote, signed*math.sqrt(excess_sq))
        if math.dist(reconstructed, v_inf) > VELOCITY_LIMIT_M_S:
            raise Unavailable(f"asymptote-invariant-{label}")
        radial = "outward" if vr > 0 else "inward" if vr < 0 else "turning"
        radius = dot(h, h)/(mu*(1 + e_norm)) if radial == "inward" else r
        velocity = scale(future, signed)
        impulse = add(orbital, scale(velocity, -1)) if arrival else add(velocity, scale(orbital, -1))
        d = unit(impulse)
        before = velocity if arrival else orbital
        t, w_axis = unit(before), unit(cross(r_vec, before))
        nw = cross(w_axis, t)
        result[label] = Branch(velocity, reconstructed, impulse, radius, radial,
                               (dot(d, t), dot(d, nw), dot(d, w_axis)),
                               math.hypot(*impulse), None if radius > guard + RADIUS_LIMIT_M else "guard")
    return result


def audited_roots(row: Row, v_inf: Vector, oracle: ModuleType,
                  *, arrival: bool) -> tuple[dict[str, Branch], dict[str, Row]]:
    exact_state, gm, guard = row["relative_si"], row["gm_m3_s2"], row["guard_m"]
    reference = oracle.branches(tuple(exact_state[:3]), tuple(exact_state[3:]),
                                tuple(str(Decimal(x)) for x in v_inf),
                                str(Decimal(gm)), str(Decimal(guard)), arrival=arrival)
    primary = float_branches(fv(exact_state[:3]), fv(exact_state[3:]), v_inf, gm, guard, arrival=arrival)
    audit: dict[str, Row] = {}
    accepted: dict[str, Branch] = {}
    for sign in SIGNS:
        a, b = primary[sign], reference[sign]
        reason = "degenerate" if a is None else a.reason
        if reason != b["reason"] or reason not in (None, "guard", "degenerate"):
            audit[sign] = {"reason": "independent-classification", "primary": reason, "oracle": b["reason"]}
            continue
        if a is None:
            audit[sign] = {"reason": reason}
            continue
        asym = max(math.dist(a.reconstructed_excess, fv(b["reconstructed_excess"])),
                   math.dist(v_inf, fv(b["reconstructed_excess"])))
        impulse = math.dist(a.impulse, fv(b["impulse"]))
        velocity = math.dist(a.velocity, fv(b["velocity"]))
        radius = abs(a.radius - float(b["radius"]))
        angles = angles_of(a.tnw)
        azimuth, elevation = angles
        reconstructed_tnw = (math.cos(elevation)*math.cos(azimuth),
                             math.cos(elevation)*math.sin(azimuth), math.sin(elevation))
        tnw = math.dist(scale(reconstructed_tnw, a.speed), scale(fv(b["tnw"]), float(b["speed"])))
        if (a.radial != b["radial"] or max(asym, impulse, velocity, tnw) > VELOCITY_LIMIT_M_S
                or radius > RADIUS_LIMIT_M):
            reason = "independent-invariant"
        audit[sign] = dict(reason=reason, radial=a.radial, minimum_radius_m=a.radius,
                           impulse_m_s=a.impulse, hyperbolic_velocity_m_s=a.velocity,
                           reconstructed_excess_m_s=a.reconstructed_excess, angles_rad=angles,
                           independent_speed_m_s=str(b["speed"]),
                           discrepancies=dict(asymptote_m_s=asym, impulse_m_s=impulse,
                                              velocity_m_s=velocity, tnw_m_s=tnw, radius_m=radius))
        if reason is None:
            accepted[sign] = a
    return accepted, audit


def angles_of(tnw: Vector) -> tuple[float, float]:
    t, n, w = tnw
    planar = math.hypot(t, n)
    az = math.atan2(n, t) if planar else 0.0
    return (-math.pi if az == math.pi else az), math.atan2(w, planar)


def sequence(departure: float, arrival: float) -> tuple[tuple[float, float], tuple[float, float]]:
    before_kg = 2000.0
    durations_s, masses_kg = [], []
    for impulse in (departure, arrival):
        consumed_kg = -before_kg*math.expm1(-impulse/EXHAUST_M_S)
        before_kg -= consumed_kg
        durations_s.append(consumed_kg/RATE_KG_S)
        masses_kg.append(before_kg)
    return (durations_s[0], durations_s[1]), (masses_kg[0], masses_kg[1])


def ledgers(epochs: Vector, durations_s: tuple[float, float]) -> Row:
    t0, tx, tf = epochs
    td, ta = durations_s
    t1, t2 = t0 + td, tf - ta
    if not 0 < min(td, ta) or not t0 < t1 < tx < t2 < tf:
        raise Unavailable("exact-event-order")
    rate = Fraction(RATE_KG_S)
    declared = Fraction(td), Fraction(ta)
    spans = Fraction(t1) - Fraction(t0), Fraction(tf) - Fraction(t2)

    def balances(elapsed_s: tuple[Fraction, Fraction]) -> tuple[Fraction, Fraction]:
        m1 = 2000 - rate*elapsed_s[0]
        return m1, m1 - rate*elapsed_s[1]

    flows = {"commanded": balances(declared), "effective": balances(spans)}
    for label, (_, final_kg) in flows.items():
        if final_kg < 500:
            raise Unavailable(f"{label}-dry-floor")
    return dict(epoch_words=[t.hex() for t in (t0, t1, tx, t2, tf)],
                mass_kg_exact={name: [str(m1), str(m1), str(mf)] for name, (m1, mf) in flows.items()})


def rank(pairs: list[Row]) -> Row:
    good = [row for row in pairs if row["reason"] is None]
    if not good:
        raise Unavailable("no-eligible-pair")
    with_local = sorted(good, key=lambda row: row["total_delta_v_m_s"])
    by_oracle = sorted(good, key=lambda row: Decimal(row["oracle_total_delta_v_m_s"]))
    top = with_local[0]
    if top is not by_oracle[0] or (len(good) > 1 and (
        with_local[1]["total_delta_v_m_s"] - top["total_delta_v_m_s"] <= RANK_GAP_M_S
        or Fraction(Decimal(by_oracle[1]["oracle_total_delta_v_m_s"]))
        - Fraction(Decimal(top["oracle_total_delta_v_m_s"])) <= Fraction(Decimal("4e-6"))
    )):
        raise Unavailable("ambiguous-rank")
    return top


def pin_inputs(raw: bytes, expected: str) -> tuple[Row, Row, Vector, set[Controls]]:
    if len(raw) > INPUT_CAP or sha256(raw).hexdigest() != expected:
        raise ValueError("fixture size or identity")
    packet = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(packet, dict) or packet.get("schema") != "ariadna-r559b-artificial-v1":
        raise ValueError("artificial source bundle required")
    sections, pins = packet["sections"], packet["pins"]
    if set(sections) != set(NAMES) or set(pins) != set(NAMES) or any(
        digest(sections[name]) != pins[name] for name in NAMES
    ):
        raise ValueError("section pins")
    r1, r4, audit = (sections[name] for name in ("r1", "r4", "audit"))
    epochs = vec(sections["contract"]["epochs_tdb_s"])
    if (sections["contract"]["model"] != "artificial-two-body" or not epochs[0] < epochs[1] < epochs[2]
            or r1["candidate"] != "artificial-moon-mars" or r1["candidate"] != r4["candidate"]
            or wire(r1["scenario"]) != wire(r4["scenario"])
            or r1["scenario"] != dict(synthetic=True, frame="SSB/J2000", units="SI",
                                      time_scale="TDB seconds since J2000")):
        raise ValueError("contract, scenario or candidate")
    if len(r4["endpoints"]) != 2 or len(audit["endpoints"]) != 2 or len(r1["excess_m_s"]) != 2:
        raise ValueError("exactly two endpoints")
    for i, body in enumerate(("Moon", "Mars")):
        row, ref = audit["endpoints"][i], r4["endpoints"][i]
        epoch = number(row["epoch_tdb_s"])
        if (row["body"] != body or epoch.hex() != epochs[2*i].hex()
                or any(wire(ref[k]) != wire(row[k]) for k in ("body", "epoch_tdb_s", "body_ssb_si", "endpoint_ssb_si"))):
            raise ValueError("endpoint identity")
        relative = tuple(exact(x) for x in row["relative_si"])
        orbit = tuple(exact(x) for x in row["orbit_relative_si"])
        if len(relative) != 6 or len(orbit) != 6 or len(row["body_ssb_si"]) != 6 or len(row["endpoint_ssb_si"]) != 6:
            raise ValueError("six-state shape")
        delta = tuple(Fraction(number(a)) - Fraction(number(b)) for a, b in
                      zip(row["endpoint_ssb_si"], row["body_ssb_si"], strict=True))
        if relative != delta or any(
            sum((a-b)**2 for a, b in zip(relative[i:i+3], orbit[i:i+3], strict=True)) > limit**2
            for i, limit in ((0, Fraction("0.001")), (3, Fraction("1e-6")))
        ):
            raise ValueError("relative-state reconstruction")
        if min(number(row["gm_m3_s2"]), number(row["guard_m"])) <= 0:
            raise ValueError("nonpositive synthetic force metadata")
    prohibited = {controls(row) for name in ("r4", "baseline", "fractions") for row in sections[name]["failures"]}
    return sections, pins, epochs, prohibited


def evaluate(raw: bytes, expected_sha256: str, oracle: ModuleType) -> Row:
    """Compare two analytic paths and return at most one artificial command pair."""
    try:
        sections, pins, epochs, prohibited = pin_inputs(raw, expected_sha256)
        evidence: Row = dict(synthetic=True, status="command-seed-unavailable", command_words=None,
                             live_authorized=False, physical_status="physical-join-not-established",
                             source_pins=pins, candidate="artificial-moon-mars",
                             model="artificial-two-body", orientation="J2000",
                             time_scale="TDB seconds since J2000", units="SI", branch_decisions={}, pairs=[])
        roots = []
        for i, body in enumerate(("Moon", "Mars")):
            try:
                accepted, audit = audited_roots(sections["audit"]["endpoints"][i],
                                               vec(sections["r1"]["excess_m_s"][i]), oracle, arrival=i == 1)
            except Unavailable as exc:
                evidence["branch_decisions"][body] = dict(rejected=str(exc))
                return evidence | dict(reason="unresolved-geometry")
            evidence["branch_decisions"][body] = audit
            roots.append(accepted)
        audits = evidence["branch_decisions"]
        if any(row["reason"] not in (None, "guard", "degenerate") for group in audits.values() for row in group.values()):
            return evidence | dict(reason="unresolved-geometry")
        for a_sign, a in roots[0].items():
            for b_sign, b in roots[1].items():
                speeds = tuple(Decimal(audits[body][sign]["independent_speed_m_s"])
                               for body, sign in (("Moon", a_sign), ("Mars", b_sign)))
                with localcontext(prec=96):
                    oracle_total = str(speeds[0] + speeds[1])
                pair: Row = dict(roots=[a_sign, b_sign], reason=None, total_delta_v_m_s=a.speed + b.speed,
                                 oracle_total_delta_v_m_s=oracle_total)
                evidence["pairs"].append(pair)
                durations, masses = sequence(a.speed, b.speed)
                other_d, other_m = oracle.mass(speeds[0], speeds[1])
                duration_error = max(abs(x-float(y)) for x, y in zip(durations, other_d, strict=True))
                mass_error = max(abs(x-float(y)) for x, y in zip(masses, other_m, strict=True))
                pair["independent_mass_discrepancies"] = dict(duration_s=duration_error, mass_kg=mass_error)
                if duration_error > DURATION_LIMIT_S or mass_error > MASS_LIMIT_KG:
                    pair["reason"] = "independent-mass"
                    continue
                try:
                    pair["ledgers"] = ledgers(epochs, durations)
                except Unavailable as exc:
                    pair["reason"] = str(exc)
                    continue
                angles_a, angles_b = angles_of(a.tnw), angles_of(b.tnw)
                candidate = controls((*angles_a, durations[0], *angles_b, durations[1]))
                if candidate in prohibited:
                    pair["reason"] = "historically-rejected"
                    continue
                pair["command_words"] = [x.hex() for x in candidate]
                pair["ideal_end_masses_kg"] = masses
        if any(row["reason"] == "independent-mass" for row in evidence["pairs"]):
            return evidence | dict(reason="unresolved-mass")
        try:
            selected = rank(evidence["pairs"])
        except Unavailable as exc:
            return evidence | dict(reason=str(exc))
        return evidence | dict(status="synthetic-command-proposal", command_words=selected["command_words"],
                               selected_roots=selected["roots"])
    except (KeyError, TypeError, ValueError, OverflowError, InvalidOperation, ZeroDivisionError) as exc:
        raise ValueError(f"invalid synthetic seed evidence: {exc}") from exc
