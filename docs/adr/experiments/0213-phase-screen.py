"""Screen and audit a manufactured single-coordinate Mars phase grid."""

from collections.abc import Callable
from decimal import Decimal, localcontext
from fractions import Fraction
import math
from types import ModuleType, SimpleNamespace
from typing import Any

type Row = dict[str, Any]
type Vector = tuple[float, ...]
GRID = 360
SIGNS = ("positive", "negative")
PROPOSAL = "artificial-phase-proposal"
REFUSAL = "no-eligible-pair-on-grid"
INCONCLUSIVE = "inconclusive"
INVALID = "invalid-evidence"


def need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(f"phase screen: {reason}")


def reference(report: Row) -> Row:
    """Select the fixed artificial operands from an independently audited archive."""
    source = report["normalized"]
    moon, mars = source["endpoints"]
    lunar = report["branch_decisions"]["Moon"]["positive"]
    zero = [pair for pair in report["pairs"] if pair["roots"][0] == "positive"]
    need(source["scope"] == "artificial" and source["candidate_id"] == "artificial-moon-mars"
         and source["command_words"] is None and source["live_authorized"] is False
         and report["status"] == "command-seed-unavailable" and report["reason"] == "no-eligible-pair"
         and report["command_words"] is None and lunar["reason"] is None
         and zero and all(pair["reason"] == "commanded-dry-floor" for pair in zero),
         "artificial zero-phase fuel refusal and fixed lunar root required")
    need(moon["body"] == "Moon" and mars["body"] == "Mars", "endpoint order")
    return dict(normalized=source, lunar=lunar, zero_branches=report["branch_decisions"]["Mars"], zero_pairs=zero)


def _pair(index: int, sign: str, moon: Row, mars: Row, source: Row,
          core: ModuleType, oracle: ModuleType, excluded: set[Vector]) -> Row:
    d, a = (math.hypot(*leg["impulse_m_s"]) for leg in (moon, mars))
    speeds = tuple(Decimal(leg["independent_speed_m_s"]) for leg in (moon, mars))
    with localcontext(prec=96):
        precise_cost = str(sum(speeds))
    pair = dict(index=index, roots=["positive", sign], reason=None,
                total_delta_v_m_s=d+a, oracle_total_delta_v_m_s=precise_cost)
    durations, masses = core.sequence(d, a)
    ref_durations, ref_masses = oracle.mass(*speeds)
    dt = max(abs(x-float(y)) for x, y in zip(durations, ref_durations, strict=True))
    dm = max(abs(x-float(y)) for x, y in zip(masses, ref_masses, strict=True))
    pair["independent_mass_discrepancies"] = dict(duration_s=dt, mass_kg=dm)
    if dt > core.DURATION_LIMIT_S or dm > core.MASS_LIMIT_KG:
        return pair | dict(reason="independent-mass")
    try:
        pair["ledgers"] = core.ledgers(source["epochs_tdb_s"], durations)
    except core.Unavailable as error:
        return pair | dict(reason=str(error))
    controls = (*moon["angles_rad"], durations[0], *mars["angles_rad"], durations[1])
    if controls in excluded:
        return pair | dict(reason="historically-rejected")
    return pair | dict(command_words=[value.hex() for value in controls], ideal_end_masses_kg=masses)


def _proposal(row: Row, pair: Row) -> Row:
    return {key: row[key] for key in ("index", "angle_word", "relative_si", "ssb_si")} | {
        key: pair[key] for key in ("roots", "command_words", "ledgers", "total_delta_v_m_s", "ideal_end_masses_kg")
    }


def _unresolved(branches: Row) -> bool:
    return any(row["reason"] not in (None, "guard", "degenerate") for row in branches.values())


def scan(ref: Row, *, core: ModuleType, oracle: ModuleType, orbit: ModuleType,
         check: Callable[[], None], rows: list[Row], work: dict[str, int]) -> Row:
    """Evaluate the two arithmetic paths for each of the 360 manufactured phases."""
    source = ref["normalized"]
    mars = source["endpoints"][1]
    excluded = {tuple(float.fromhex(word) for word in row) for row in source["rejected_command_words"]}
    for index in range(GRID):
        check()
        work["phase_positions"] += 1
        phase = orbit.state(mars, index)
        endpoint = mars | dict(relative_si=[str(Decimal(x)) for x in phase["relative_si"]])
        precise = phase["independent_relative_si"]

        def independent(_pos: tuple[str, ...], _vel: tuple[str, ...], *args: Any, **kwargs: Any) -> Row:
            return oracle.branches(tuple(precise[:3]), tuple(precise[3:]), *args, **kwargs)

        # One call to the pinned worksheet evaluates at most the two signed roots per path.
        check()
        work["mars_roots"] += 2
        try:
            roots, branches = core.audited_roots(endpoint, mars["v_infinity_m_s"],
                                                SimpleNamespace(branches=independent), arrival=True)
        except core.Unavailable as error:
            roots = {}
            branches = {sign: dict(reason="unresolved", detail=str(error)) for sign in SIGNS}
        pairs = []
        phase.update(branches=branches, pairs=pairs)
        rows.append(phase)
        if not _unresolved(branches):
            for sign in roots:
                check()
                work["pairs"] += 1
                pairs.append(_pair(index, sign, ref["lunar"], branches[sign], source, core, oracle, excluded))
    need(len(rows) == GRID, "phase count")
    all_pairs = [pair for row in rows for pair in row["pairs"]]
    if any(_unresolved(row["branches"]) for row in rows) or any(
        pair["reason"] == "independent-mass" for pair in all_pairs
    ):
        return dict(status=INCONCLUSIVE, reason="independent-disagreement", selected=None, command_words=None)
    try:
        selected = core.rank(all_pairs)
    except core.Unavailable as error:
        status = REFUSAL if str(error) == "no-eligible-pair" else INCONCLUSIVE
        return dict(status=status, reason=str(error), selected=None, command_words=None)
    return dict(status=PROPOSAL, reason=None, selected=_proposal(rows[selected["index"]], selected),
                command_words=selected["command_words"])


def _read_state(row: Row, mars: Row, index: int, reader: ModuleType) -> None:
    # Reconstruct the stored orbital position and velocity from the original periapsis axes.
    angle = math.tau*index/GRID
    need(type(row["index"]) is int and row["index"] == index and row["angle_word"] == angle.hex(),
         "grid inventory or angle word")
    relative = reader._vector(row["relative_si"], 6)
    ssb = reader._vector(row["ssb_si"], 6)
    precise = tuple(reader._decimal(x) for x in row["independent_relative_si"])
    need(len(precise) == 6, "independent state size")
    body = reader._vector(mars["body_ssb_si"], 6)
    translated = tuple(x+y for x, y in zip(relative, body, strict=True))
    need(ssb == translated, "body translation")
    computed = {}
    with localcontext(prec=96):
        precise_ssb = tuple(x+Decimal(y) for x, y in zip(precise, body, strict=True))
        for label, vector, reference in (("relative", relative, precise), ("ssb", ssb, precise_ssb)):
            delta = tuple(Decimal(a)-b for a, b in zip(vector, reference, strict=True))
            position = sum(x*x for x in delta[:3]).sqrt()
            velocity = sum(x*x for x in delta[3:]).sqrt()
            need(position <= Decimal("0.001") and velocity <= Decimal("1e-6"),
                 "saved independent state disagreement")
            computed[f"{label}_position_m"] = float(position)
            computed[f"{label}_velocity_m_s"] = float(velocity)
    d = row["discrepancies"]
    need(set(d) == set(computed) and all(reader._number(d[k]) == v for k, v in computed.items()),
         "state discrepancy evidence")
    original = tuple(float(reader._decimal(x)) for x in mars["relative_si"])
    nr, nv = math.hypot(*original[:3]), math.hypot(*original[3:])
    p_axis, q_axis = tuple(x/nr for x in original[:3]), tuple(x/nv for x in original[3:])
    e = reader._number(mars["orbit"]["eccentricity"])
    p = (mars["shape_radius_m"]+mars["orbit"]["periapsis_altitude_m"])*(1+e)
    c, s = math.cos(angle), math.sin(angle)
    radius, speed = p/(1+e*c), math.sqrt(mars["gm_m3_s2"]/p)
    r = tuple(radius*(c*x+s*y) for x, y in zip(p_axis, q_axis, strict=True))
    v = tuple(speed*(-s*x+(e+c)*y) for x, y in zip(p_axis, q_axis, strict=True))
    need(math.dist(r, relative[:3]) <= 0.001 and math.dist(v, relative[3:]) <= 1e-6,
         "state not on the specified orbit phase")


def _verify_zero(row: Row, ref: Row) -> None:
    mars = ref["normalized"]["endpoints"][1]
    need(math.dist(row["ssb_si"][:3], mars["endpoint_ssb_si"][:3]) <= 0.001
         and math.dist(row["ssb_si"][3:], mars["endpoint_ssb_si"][3:]) <= 1e-6, "zero phase state")
    for sign in SIGNS:
        a, b = row["branches"][sign], ref["zero_branches"][sign]
        need(a["reason"] == b["reason"], "zero phase root decision")
        if "minimum_radius_m" in b:
            need(abs(a["minimum_radius_m"]-b["minimum_radius_m"]) <= 0.001
                 and math.dist(a["impulse_m_s"], b["impulse_m_s"]) <= 1e-6, "zero phase root replay")
    for a, b in zip(row["pairs"], ref["zero_pairs"], strict=True):
        need(a["roots"] == b["roots"] and a["reason"] == b["reason"] == "commanded-dry-floor"
             and abs(a["total_delta_v_m_s"]-b["total_delta_v_m_s"]) <= 1e-6, "zero phase dry floor")


def _select(good: list[Row]) -> Row | None:
    if not good:
        return None
    local = sorted(good, key=lambda pair: pair["total_delta_v_m_s"])
    precise = sorted(good, key=lambda pair: Decimal(pair["oracle_total_delta_v_m_s"]))
    winner = local[0]
    if len(good) > 1:
        gap = Fraction(precise[1]["oracle_total_delta_v_m_s"])-Fraction(precise[0]["oracle_total_delta_v_m_s"])
        if winner is not precise[0] or local[1]["total_delta_v_m_s"]-winner["total_delta_v_m_s"] <= 4e-6 or gap <= Fraction("0.000004"):
            return None
    return winner


def audit(report: Row, reader: ModuleType, check: Callable[[], None]) -> None:
    """Verify persisted results and ranking without evaluating new conics or phases."""
    work, rows, status = report["work"], report["rows"], report["status"]
    need(set(work) == {"phase_positions", "mars_roots", "pairs"}
         and all(type(x) is int and x >= 0 for x in work.values())
         and isinstance(rows, list) and len(rows) <= work["phase_positions"] <= GRID
         and work["mars_roots"] <= 2*work["phase_positions"] and work["pairs"] <= work["mars_roots"],
         "work caps")
    if status == INVALID:
        need(report["command_words"] is None and report["selected"] is None and report["error"], "invalid output")
        return
    need(work["phase_positions"] == len(rows) == GRID and work["mars_roots"] == 2*GRID, "incomplete grid")
    ref = report["reference"]
    source = ref["normalized"]
    moon, mars = source["endpoints"]
    need(source["scope"] == "artificial" and source["candidate_id"] == "artificial-moon-mars"
         and source["command_words"] is None and source["live_authorized"] is False
         and moon["body"] == "Moon" and mars["body"] == "Mars"
         and reader._root(ref["lunar"], moon) is None, "fixed artificial operands")
    excluded = {tuple(reader._word(word) for word in item) for item in source["rejected_command_words"]}
    good = []
    count = 0
    inconclusive = False
    for index, row in enumerate(rows):
        check()
        _read_state(row, mars, index, reader)
        branches, pairs = row["branches"], row["pairs"]
        need(set(branches) == set(SIGNS) and isinstance(pairs, list), "signed root inventory")
        state = mars | dict(relative_si=[str(Decimal(x)) for x in row["relative_si"]])
        accepted = []
        for sign in SIGNS:
            branch = branches[sign]
            if branch["reason"] == "unresolved":
                need(type(branch.get("detail")) is str and branch["detail"], "unresolved root")
            elif reader._root(branch, state) is None:
                accepted.append(sign)
        unresolved = _unresolved(branches)
        expected = [["positive", sign] for sign in accepted if not unresolved]
        need([pair["roots"] for pair in pairs] == expected, "phase pair inventory")
        inconclusive |= unresolved
        for pair in pairs:
            need(type(pair["index"]) is int and pair["index"] == index, "pair phase")
            count += 1
            if reader._pair(pair, ref["lunar"], branches[pair["roots"][1]], tuple(source["epochs_tdb_s"]),
                            source["spacecraft"], excluded):
                good.append(pair)
            inconclusive |= pair["reason"] == "independent-mass"
    _verify_zero(rows[0], ref)
    need(count == work["pairs"], "pair count")
    winner = None if inconclusive else _select(good)
    if winner is None:
        expected_status = INCONCLUSIVE if inconclusive or good else REFUSAL
        reason = "independent-disagreement" if inconclusive else "ambiguous-rank" if good else "no-eligible-pair"
        need(status == expected_status and report["reason"] == reason and report["command_words"] is None
             and report["selected"] is None, "refusal or ambiguity binding")
    else:
        need(status == PROPOSAL and report["reason"] is None and report["command_words"] == winner["command_words"]
             and report["selected"] == _proposal(rows[winner["index"]], winner), "winning phase binding")
