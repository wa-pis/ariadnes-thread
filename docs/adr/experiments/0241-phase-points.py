"""Artificial ADR0240 binary64 point checks and independent literal-command audit."""

from decimal import Decimal, localcontext, ROUND_FLOOR
from fractions import Fraction
import json
import math
from types import ModuleType, SimpleNamespace
from typing import Any

type Row = dict[str, Any]
type Methods = dict[str, ModuleType]

SIGNS = ("positive", "negative")
START, END = 150, 152
SCHEMA = "ariadna-r559-bounded-point-v1"
SPACECRAFT = {"initial_mass_kg": 2000., "dry_mass_kg": 500., "max_thrust_n": 1000., "isp_s": 450.}


def _wire_row(row: Row) -> Row:
    """Normalize in-memory tuples to the pinned reader's JSON record shape."""
    return json.loads(json.dumps(row, allow_nan=False))


def _phase(phase: float) -> Fraction:
    if type(phase) is not float or not math.isfinite(phase) or not START <= phase <= END:
        raise ValueError("phase must be a finite plain binary64 degree in [150, 152]")
    return Fraction(*phase.as_integer_ratio())


def _state(endpoint: Row, phase: float, orbit: ModuleType) -> Row:
    """Keep the frozen angle operation order; reconstruct the exact degree ratio."""
    ratio = _phase(phase)
    angles = endpoint["orbit"]
    if (endpoint["body"], endpoint["label"], angles["central_body"], angles["true_anomaly_rad"]) != (
        "Mars", "arrival-cutoff", "Mars", 0.,
    ):
        raise ValueError("fixed zero-phase Mars arrival boundary required")
    mu, shape = map(orbit._number, (endpoint["gm_m3_s2"], endpoint["shape_radius_m"]))
    peri_alt, apo_alt, ecc, inc, node, arg = (orbit._number(angles[key]) for key in (
        "periapsis_altitude_m", "apoapsis_altitude_m", "eccentricity",
        "inclination_rad", "raan_rad", "argument_of_periapsis_rad",
    ))
    if not (mu > 0 and shape > 0 and 0 <= peri_alt <= apo_alt and 0 <= ecc < 1
            and 0 <= inc <= math.pi and 0 <= node < math.tau and 0 <= arg < math.tau):
        raise ValueError("invalid Mars ellipse")
    body = orbit._vector(endpoint["body_ssb_si"])
    angle = math.tau*phase/orbit.COUNT
    relative = orbit._local_state(mu, shape+peri_alt, ecc, inc, node, arg, angle)
    ssb = tuple(a+b for a, b in zip(relative, body, strict=True))
    if not all(map(math.isfinite, (*relative, *ssb))):
        raise ValueError("nonfinite phase state")

    with localcontext(orbit._PRECISION):
        peri, apo = Decimal(shape)+Decimal(peri_alt), Decimal(shape)+Decimal(apo_alt)
        eccentricity = Decimal(ecc)
        if abs(peri*(1+eccentricity)/(1-eccentricity)-apo) > Decimal("0.001"):
            raise ValueError("archived Mars apsides disagree with eccentricity")
        index = Decimal(ratio.numerator)/ratio.denominator
        ref = orbit._oracle_state(Decimal(mu), peri, eccentricity, Decimal(inc), Decimal(node), Decimal(arg), index)
        ref_ssb = tuple(a+Decimal(b) for a, b in zip(ref, body, strict=True))
        dr, dv = orbit._discrepancy(tuple(map(Decimal, relative)), ref)
        sr, sv = orbit._discrepancy(tuple(map(Decimal, ssb)), ref_ssb)
        exact_angle = str(2*orbit._PI*index/orbit.COUNT)
    return dict(schema=SCHEMA, phase_deg=str(ratio), phase_word=phase.hex(),
                phase_ratio=[ratio.numerator, ratio.denominator],
                angle_word=angle.hex(), independent_angle_rad=exact_angle,
                relative_si=list(relative), ssb_si=list(ssb), independent_relative_si=list(map(str, ref)),
                discrepancies=dict(relative_position_m=dr, relative_velocity_m_s=dv,
                                   ssb_position_m=sr, ssb_velocity_m_s=sv))


def point(ref: Row, phase: float, methods: Methods) -> Row:
    """Construct both signed roots and admit only independently verified point witnesses."""
    core, oracle, orbit, screen, reader = (methods[name] for name in ("core", "oracle", "orbit", "screen", "reader"))
    ratio = _phase(phase)
    source = _reference(ref, reader)
    moon, mars = source["endpoints"]
    craft = source["spacecraft"]
    if moon["body"] != "Moon" or reader._root(ref["lunar"], moon) is not None:
        raise ValueError("the fixed lunar root is not admissible")

    result = _state(mars, phase, orbit)
    local = result["relative_si"]
    precise = result["independent_relative_si"]
    endpoint = mars | {"relative_si": [str(Decimal(x)) for x in local]}
    excess = tuple(mars["v_infinity_m_s"])

    if ratio.denominator == 1:
        # The pinned integer-only readback supplies an extra parity check at the saved nodes.
        screen._read_state(result | {"index": ratio.numerator}, mars, ratio.numerator, reader)

    def independent(_pos: tuple[str, ...], _vel: tuple[str, ...], *args: Any, **kwargs: Any) -> Row:
        return oracle.branches(tuple(precise[:3]), tuple(precise[3:]), *args, **kwargs)

    try:
        roots, branches = core.audited_roots(endpoint, excess, SimpleNamespace(branches=independent), arrival=True)
        branches = _wire_row(branches)
    except core.Unavailable as exc:
        roots, branches = {}, {s: dict(reason="unresolved", detail=str(exc)) for s in SIGNS}
    unresolved = screen._unresolved(branches)
    excluded = {tuple(reader._word(word) for word in row) for row in source["rejected_command_words"]}
    epochs = reader._vector(source["epochs_tdb_s"], 3)

    budget = core.EXHAUST_M_S*math.log(4.)
    with localcontext(oracle.PRECISION) as context:
        exhaust = Decimal(core.EXHAUST_M_S)
        logarithm = Decimal(4).ln()
        budget_hi = exhaust*logarithm
        # Decimal.ln is correctly rounded; round down both its lower neighbor and the product.
        context.rounding = ROUND_FLOOR
        budget_lo = exhaust*logarithm.next_minus()
    pairs, eligible = [], []
    if not unresolved:
        for sign in SIGNS:
            branch = branches[sign]
            if reader._root(branch, endpoint) is not None:
                if sign in roots:
                    raise ValueError("root readback disagrees with admitted branch")
                continue
            if sign not in roots:
                raise ValueError("admitted root is missing")
            candidate = _wire_row(screen._pair(ratio.numerator if ratio.denominator == 1 else str(ratio), sign,
                                               ref["lunar"], branch, source, core, oracle, excluded))
            accepted = reader._pair(candidate, ref["lunar"], branch, epochs, craft, excluded)
            if accepted:
                core.controls(tuple(reader._word(word) for word in candidate["command_words"]))
            cost, cost_hi = candidate["total_delta_v_m_s"], Decimal(candidate["oracle_total_delta_v_m_s"])
            within = cost <= budget and Decimal(cost) <= budget_lo and cost_hi <= budget_lo
            if accepted and within:
                eligible.append(sign)
            unresolved |= candidate["reason"] == "independent-mass"
            pairs.append({key: value for key, value in candidate.items() if key != "index"}
                         | {"within_ideal_budget": within})
    return result | dict(branches=branches, branch_dispositions=_dispositions(branches),
                         pairs=pairs, eligible=[] if unresolved else eligible,
                         unresolved=unresolved, ideal_budget_m_s=budget,
                         independent_ideal_budget_m_s=str(budget_hi))



def _need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(f"bounded point: {reason}")


def _reference(ref: Row, reader: ModuleType) -> Row:
    source = ref["normalized"]
    craft = source["spacecraft"]
    _need(source["scope"] == "artificial" and source["candidate_id"] == "artificial-moon-mars"
          and {key: craft[key] for key in SPACECRAFT} == SPACECRAFT
          and source["command_words"] is None and source["live_authorized"] is False,
          "fixed artificial spacecraft and diagnostic-only scope required")
    _need((source["origin"], source["orientation"], source["units"], source["time_scale"]) ==
          ("SSB", "J2000", "SI", "TDB seconds since J2000"), "scientific frame")
    moon, mars = source["endpoints"]
    epochs = reader._vector(source["epochs_tdb_s"], 3)
    _need(epochs[0] < epochs[1] < epochs[2]
          and source["epoch_words"] == [value.hex() for value in epochs], "epoch binding")
    for endpoint, body, epoch in zip((moon, mars), ("Moon", "Mars"), epochs[::2], strict=True):
        _need(endpoint["body"] == body and endpoint["epoch_word"] == epoch.hex()
              and reader._number(endpoint["epoch_tdb_s"]) == epoch, "endpoint binding")
    return source


def _dispositions(branches: Row) -> dict[str, str]:
    _need(set(branches) == set(SIGNS), "two signed branch slots required")
    return {sign: ("available" if branches[sign]["reason"] is None else
                   branches[sign]["reason"] if branches[sign]["reason"] in ("guard", "degenerate")
                   else "unresolved") for sign in SIGNS}


def _audit_state(mars: Row, row: Row, reader: ModuleType, orbit: ModuleType) -> tuple[str, ...]:
    """Rebuild only the independent orbit; never call the producer state helper."""
    phase = reader._word(row["phase_word"])
    ratio = _phase(phase)
    _need(row["schema"] == SCHEMA and row["phase_deg"] == str(ratio)
          and isinstance(row["phase_ratio"], list)
          and all(type(x) is int for x in row["phase_ratio"])
          and row["phase_ratio"] == [ratio.numerator, ratio.denominator]
          and row["angle_word"] == (math.tau*phase/360).hex(), "exact phase binding")
    angles = mars["orbit"]
    _need((mars["body"], mars["label"], angles["central_body"], angles["true_anomaly_rad"]) ==
          ("Mars", "arrival-cutoff", "Mars", 0.), "zero-phase Mars endpoint")
    mu, shape = (reader._number(mars[key]) for key in ("gm_m3_s2", "shape_radius_m"))
    peri, apo, ecc, inc, node, arg = (reader._number(angles[key]) for key in (
        "periapsis_altitude_m", "apoapsis_altitude_m", "eccentricity", "inclination_rad",
        "raan_rad", "argument_of_periapsis_rad"))
    _need(mu > 0 and shape > 0 and 0 <= peri <= apo and 0 <= ecc < 1
          and 0 <= inc <= math.pi and 0 <= node < math.tau and 0 <= arg < math.tau,
          "Mars ellipse domain")
    local = reader._vector(row["relative_si"], 6)
    ssb = reader._vector(row["ssb_si"], 6)
    body = reader._vector(mars["body_ssb_si"], 6)
    _need(ssb == tuple(a+b for a, b in zip(local, body, strict=True)), "SSB translation")
    with localcontext(orbit._PRECISION):
        peri_m, apo_m = Decimal(shape)+Decimal(peri), Decimal(shape)+Decimal(apo)
        e = Decimal(ecc)
        _need(abs(peri_m*(1+e)/(1-e)-apo_m) <= Decimal("0.001"), "Mars apsides")
        exact_phase = Decimal(ratio.numerator)/ratio.denominator
        precise = orbit._oracle_state(Decimal(mu), peri_m, e, Decimal(inc), Decimal(node), Decimal(arg), exact_phase)
        text = tuple(map(str, precise))
        _need(row["independent_relative_si"] == list(text)
              and row["independent_angle_rad"] == str(2*orbit._PI*exact_phase/360), "independent state binding")
        computed = {}
        for label, actual, expected in (("relative", local, precise),
                ("ssb", ssb, tuple(a+Decimal(b) for a, b in zip(precise, body, strict=True)))):
            delta = tuple(Decimal(a)-b for a, b in zip(actual, expected, strict=True))
            dr = sum(x*x for x in delta[:3]).sqrt()
            dv = sum(x*x for x in delta[3:]).sqrt()
            _need(dr <= Decimal("0.001") and dv <= Decimal("1e-6"), "state reconstruction gates")
            computed[f"{label}_position_m"], computed[f"{label}_velocity_m_s"] = float(dr), float(dv)
    _need(isinstance(row["discrepancies"], dict) and set(row["discrepancies"]) == set(computed)
          and all(reader._number(row["discrepancies"][key]) == value for key, value in computed.items()),
          "state discrepancy evidence")
    return text


def _cross(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, float, float]:
    return a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]


def _unit(a: tuple[float, ...]) -> tuple[float, ...]:
    norm = math.hypot(*a)
    _need(norm > 0 and math.isfinite(norm), "singular TNW basis")
    return tuple(x*(1/norm) for x in a)


def _audit_branch(branch: Row, endpoint: Row, expected: Row, reader: ModuleType) -> None:
    reason = reader._root(branch, endpoint)
    _need(reason == expected["reason"] and reason in (None, "guard", "degenerate"), "independent signed classification")
    if reason == "degenerate":
        return
    impulse = reader._vector(branch["impulse_m_s"], 3)
    velocity = reader._vector(branch["hyperbolic_velocity_m_s"], 3)
    excess = reader._vector(endpoint["v_infinity_m_s"], 3)
    reconstructed = reader._vector(branch["reconstructed_excess_m_s"], 3)
    speed = math.hypot(*impulse)
    before = velocity if endpoint["body"] == "Mars" else tuple(float(reader._decimal(x)) for x in endpoint["relative_si"][3:])
    position = tuple(float(reader._decimal(x)) for x in endpoint["relative_si"][:3])
    t, w, kick = _unit(before), _unit(_cross(position, before)), _unit(impulse)
    n = _cross(w, t)
    tnw = tuple(math.fsum(x*y for x, y in zip(kick, axis, strict=True)) for axis in (t, n, w))
    planar = math.hypot(*tnw[:2])
    azimuth = math.atan2(tnw[1], tnw[0]) if planar else 0.
    angles = (-math.pi if azimuth == math.pi else azimuth), math.atan2(tnw[2], planar)
    _need(reader._vector(branch["angles_rad"], 2) == angles, "canonical pre-impulse TNW binding")
    a, e = angles
    actual_tnw = tuple(x*speed for x in (math.cos(e)*math.cos(a), math.cos(e)*math.sin(a), math.sin(e)))
    errors = dict(
        asymptote_m_s=max(math.dist(reconstructed, tuple(map(float, expected["reconstructed_excess"]))),
                         math.dist(excess, tuple(map(float, expected["reconstructed_excess"])))),
        impulse_m_s=math.dist(impulse, tuple(map(float, expected["impulse"]))),
        velocity_m_s=math.dist(velocity, tuple(map(float, expected["velocity"]))),
        tnw_m_s=math.dist(actual_tnw, tuple(float(x)*float(expected["speed"]) for x in expected["tnw"])),
        radius_m=abs(branch["minimum_radius_m"]-float(expected["radius"])))
    _need(branch["radial"] == expected["radial"]
          and reader._decimal(branch["independent_speed_m_s"]) == expected["speed"]
          and branch["discrepancies"] == errors
          and all(value <= (0.001 if key == "radius_m" else 1e-6) for key, value in errors.items()),
          "independent signed impulse gates")


def audit_point(ref: Row, row: Row, methods: Methods) -> Row:
    """Audit recorded SI/J2000 operands and literal commands without producer replay."""
    oracle, orbit, reader = (methods[name] for name in ("oracle", "orbit", "reader"))
    source = _reference(ref, reader)
    moon, mars = source["endpoints"]
    precise = _audit_state(mars, row, reader, orbit)
    endpoint = mars | {"relative_si": [str(Decimal(x)) for x in row["relative_si"]]}

    def branches(state: Row, exact: tuple[str, ...], arrival: bool) -> Row:
        return oracle.branches(tuple(exact[:3]), tuple(exact[3:]),
                               tuple(str(Decimal(x)) for x in state["v_infinity_m_s"]),
                               str(Decimal(state["gm_m3_s2"])), str(Decimal(state["guard_m"])), arrival=arrival)

    lunar = branches(moon, tuple(moon["relative_si"]), False)
    _audit_branch(ref["lunar"], moon, lunar["positive"], reader)
    _need(ref["lunar"]["reason"] is None, "fixed positive lunar root")
    independent = branches(mars, precise, True)
    dispositions = _dispositions(row["branches"])
    unresolved = any(value == "unresolved" for value in dispositions.values())
    for sign in SIGNS:
        branch = row["branches"][sign]
        if dispositions[sign] != "unresolved":
            _audit_branch(branch, endpoint, independent[sign], reader)
        else:
            _need(branch["reason"] in ("unresolved", "independent-classification", "independent-invariant"),
                  "unresolved classification")
    expected = [["positive", sign] for sign in SIGNS if dispositions[sign] == "available"] if not unresolved else []
    _need(isinstance(row["pairs"], list) and [pair["roots"] for pair in row["pairs"]] == expected,
          "signed pair inventory")
    excluded = {tuple(reader._word(word) for word in words) for words in source["rejected_command_words"]}
    epochs = reader._vector(source["epochs_tdb_s"], 3)
    exhaust = 9.80665*450
    budget = exhaust*math.log(4.)
    with localcontext(oracle.PRECISION) as context:
        logarithm = Decimal(4).ln()
        budget_hi = Decimal(exhaust)*logarithm
        context.rounding = ROUND_FLOOR
        budget_lo = Decimal(exhaust)*logarithm.next_minus()
    _need(row["ideal_budget_m_s"] == budget
          and row["independent_ideal_budget_m_s"] == str(budget_hi), "ideal budget binding")
    eligible = []
    for pair in row["pairs"]:
        sign = pair["roots"][1]
        accepted = reader._pair(pair, ref["lunar"], row["branches"][sign], epochs, source["spacecraft"], excluded)
        cost = reader._number(pair["total_delta_v_m_s"])
        precise_cost = reader._decimal(pair["oracle_total_delta_v_m_s"])
        within = cost <= budget and Decimal(cost) <= budget_lo and precise_cost <= budget_lo
        _need(type(pair["within_ideal_budget"]) is bool and pair["within_ideal_budget"] == within,
              "unrounded ideal budget decision")
        if accepted and within:
            eligible.append(sign)
        unresolved |= pair["reason"] == "independent-mass"
    eligible = [] if unresolved else eligible
    _need(type(row["unresolved"]) is bool and row["unresolved"] == unresolved
          and row["eligible"] == eligible and row["branch_dispositions"] == dispositions,
          "point admissibility binding")
    return dict(phase_word=row["phase_word"], phase_ratio=row["phase_ratio"], eligible=eligible,
                unresolved=unresolved, branch_dispositions=dispositions)
