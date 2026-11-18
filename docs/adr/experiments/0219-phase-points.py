"""Check one exact dyadic phase with the frozen binary64 and Decimal worksheets."""

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
MAX_DENOMINATOR = 64
SPACECRAFT = {"initial_mass_kg": 2000., "dry_mass_kg": 500., "max_thrust_n": 1000., "isp_s": 450.}


def _wire_row(row: Row) -> Row:
    """Normalize in-memory tuples to the pinned reader's JSON record shape."""
    return json.loads(json.dumps(row, allow_nan=False))


def _state(endpoint: Row, phase: Fraction, orbit: ModuleType) -> Row:
    """Keep the integer-anchor operation order and use the exact dyadic in Decimal."""
    if type(phase) is not Fraction or not START <= phase <= END or phase.denominator not in (1, 2, 4, 8, 16, 32, MAX_DENOMINATOR):
        raise ValueError("phase must be a dyadic degree in [150, 152] in the depth-five cell tree")
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
    angle = math.tau*float(phase)/orbit.COUNT
    relative = orbit._local_state(mu, shape+peri_alt, ecc, inc, node, arg, angle)
    ssb = tuple(a+b for a, b in zip(relative, body, strict=True))
    if not all(map(math.isfinite, (*relative, *ssb))):
        raise ValueError("nonfinite phase state")

    with localcontext(orbit._PRECISION):
        peri, apo = Decimal(shape)+Decimal(peri_alt), Decimal(shape)+Decimal(apo_alt)
        eccentricity = Decimal(ecc)
        if abs(peri*(1+eccentricity)/(1-eccentricity)-apo) > Decimal("0.001"):
            raise ValueError("archived Mars apsides disagree with eccentricity")
        index = Decimal(phase.numerator)/phase.denominator
        ref = orbit._oracle_state(Decimal(mu), peri, eccentricity, Decimal(inc), Decimal(node), Decimal(arg), index)
        ref_ssb = tuple(a+Decimal(b) for a, b in zip(ref, body, strict=True))
        dr, dv = orbit._discrepancy(tuple(map(Decimal, relative)), ref)
        sr, sv = orbit._discrepancy(tuple(map(Decimal, ssb)), ref_ssb)
        exact_angle = str(2*orbit._PI*index/orbit.COUNT)
    return dict(phase_deg=str(phase), angle_word=angle.hex(), independent_angle_rad=exact_angle,
                relative_si=list(relative), ssb_si=list(ssb), independent_relative_si=list(map(str, ref)),
                discrepancies=dict(relative_position_m=dr, relative_velocity_m_s=dv,
                                   ssb_position_m=sr, ssb_velocity_m_s=sv))


def point(ref: Row, phase: Fraction, methods: Methods) -> Row:
    """Construct both signed roots and admit only independently verified point witnesses."""
    core, oracle, orbit, screen, reader = (methods[name] for name in ("core", "oracle", "orbit", "screen", "reader"))
    source = ref["normalized"]
    moon, mars = source["endpoints"]
    craft = source["spacecraft"]
    fixed = {key: craft[key] for key in SPACECRAFT}
    if fixed != SPACECRAFT or source["command_words"] is not None or source["live_authorized"] is not False:
        raise ValueError("frozen spacecraft and diagnostic-only scope required")
    if moon["body"] != "Moon" or reader._root(ref["lunar"], moon) is not None:
        raise ValueError("the fixed lunar root is not admissible")

    result = _state(mars, phase, orbit)
    local = result["relative_si"]
    precise = result["independent_relative_si"]
    endpoint = mars | {"relative_si": [str(Decimal(x)) for x in local]}
    excess = tuple(mars["v_infinity_m_s"])

    if phase.denominator == 1:
        # The pinned integer-only readback supplies an extra parity check at the saved nodes.
        screen._read_state(result | {"index": phase.numerator}, mars, phase.numerator, reader)

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
            candidate = _wire_row(screen._pair(phase.numerator if phase.denominator == 1 else str(phase), sign,
                                               ref["lunar"], branch, source, core, oracle, excluded))
            accepted = reader._pair(candidate, ref["lunar"], branch, epochs, craft, excluded)
            if accepted:
                core.controls(tuple(reader._word(word) for word in candidate["command_words"]))
            cost, cost_hi = candidate["total_delta_v_m_s"], Decimal(candidate["oracle_total_delta_v_m_s"])
            within = cost <= budget and Decimal(cost) <= budget_lo and cost_hi <= budget_lo
            if accepted and within:
                eligible.append(sign)
            unresolved |= candidate["reason"] == "independent-mass"
            pairs.append({key: value for key, value in candidate.items() if key not in ("index", "command_words")}
                         | {"within_ideal_budget": within})
    return result | dict(branches=branches, pairs=pairs, eligible=[] if unresolved else eligible,
                         unresolved=unresolved, ideal_budget_m_s=budget,
                         independent_ideal_budget_m_s=str(budget_hi))


def fixture(case: str, methods: Methods) -> Row:
    """Fabricate a circular Mars boundary around a narrow witness, refusal, or guard transition."""
    profiles = {
        "witness": (5349.349022787791, 224.83586408220995),
        "refusal": (7600., 224.83586408220995),
        "transition": (7600., 97.),
    }
    try:
        speed, heading_deg = profiles[case]
    except KeyError as exc:
        raise ValueError(f"unknown artificial case: {case}") from exc
    core, oracle, orbit = (methods[name] for name in ("core", "oracle", "orbit"))
    epochs = (1073741952., 1073766952., 1073791952.)
    moon_r = (1611331.3351188295, 1100538.7023694925, 1467384.9364926568)
    moon_v = (-1064.628656781664, 561.1515742680841, 748.2020990241123)
    moon_excess = (-751.9908311490719, 1466.2085741254025, 1954.9447655005367)
    moon = dict(body="Moon", label="departure-ignition", gm_m3_s2=4_902_800_121_846.8, guard_m=1_744_010.,
                relative_si=[str(Decimal(x)) for x in (*moon_r, *moon_v)], v_infinity_m_s=moon_excess)
    _, roots = core.audited_roots(moon, moon_excess, oracle, arrival=False)
    mu, shape, radius, guard = 42_828_375_815_756.1, 3_389_500., 3_689_500., 3_396_190.
    inc, node, arg = math.acos(12/13), math.atan2(.8, .6), 0.
    body = (149_300_000_000., 15_200_000_000., -1_500_000_000., -3400., 23_900., 1100.)
    at_peri = orbit._local_state(mu, radius, 0., inc, node, arg, 0.)
    p = (.6, .8, 0.)
    q = (-48/65, 36/65, 5/13)
    n = core.cross(p, q)
    heading, tilt = math.radians(heading_deg), math.radians(4.)
    excess = tuple(speed*(math.cos(tilt)*(math.cos(heading)*a+math.sin(heading)*b)+math.sin(tilt)*c)
                   for a, b, c in zip(p, q, n, strict=True))
    mars = dict(body="Mars", label="arrival-cutoff", gm_m3_s2=mu, guard_m=guard, shape_radius_m=shape,
                orbit=dict(central_body="Mars", periapsis_altitude_m=radius-shape, apoapsis_altitude_m=radius-shape,
                           eccentricity=0., inclination_rad=inc, raan_rad=node,
                           argument_of_periapsis_rad=arg, true_anomaly_rad=0.),
                relative_si=[str(Decimal(x)) for x in at_peri], v_infinity_m_s=excess, body_ssb_si=body,
                endpoint_ssb_si=tuple(a+b for a, b in zip(at_peri, body, strict=True)))
    for endpoint, epoch in zip((moon, mars), epochs[::2], strict=True):
        endpoint.update(epoch_word=epoch.hex(), epoch_tdb_s=epoch)
    source = dict(scope="artificial", candidate_id="artificial-moon-mars", command_words=None, live_authorized=False,
                  origin="SSB", orientation="J2000", units="SI", time_scale="TDB seconds since J2000",
                  epochs_tdb_s=epochs, epoch_words=tuple(t.hex() for t in epochs), endpoints=[moon, mars],
                  spacecraft=dict(SPACECRAFT), rejected_command_words=[])
    ref = _wire_row(dict(normalized=source, lunar=roots["positive"]))
    return dict(scope="artificial", reference=ref, anchors=[point(ref, Fraction(n), methods) for n in (150, 151, 152)])
