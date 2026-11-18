"""Read saved midpoint gates and describe widths without constructing a point or bound."""

from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from hashlib import sha256
import json
import math
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type Methods = dict[str, ModuleType]

REFERENCE_SHA256 = "6b845f74881f658d2eeea28bfdde43c9190a283da5bb166644bb845c4f847c5b"
ARTIFICIAL_REFERENCE_PINS = frozenset({
    "cf20fb7d66cb6efe54b809519d1c0ca8f3031aee83c8532de4a20e2c6f0b1cec",
    "5316e28ef1c7c27035ba9ef08c2fa26ac9d600d04ba8a06af1dc69fe6c4c5467",
})
SELECTION = (
    (62, "150", "4801/32", "9601/64", "0b0496cd04fdc22c2e73d8f05b0d8d0d9e9ca685c78614a0ba5c8d129c9d11d6"),
    (94, "151", "4833/32", "9665/64", "104f208f88d8403cd14aa97f2af0defc4cfee87ca452ff321ae075ea72d0ba9d"),
    (125, "4863/32", "152", "9727/64", "ac7fa698e5e5eac79b390e97c6ee0439cccea18a41765412604e47e882365c4c"),
)
SIGNS = ("positive", "negative")
SELECTED_STAGES = ("bounds", "_ellipse", "_reverse", "_mass_exclusion", "_clearance")
_STATE_GATES = {"relative_position_m": 0.001, "relative_velocity_m_s": 1e-6,
                "ssb_position_m": 0.001, "ssb_velocity_m_s": 1e-6}


def _need(ok: object, message: str) -> None:
    if not ok:
        raise ValueError(f"saved trace checks: {message}")


def _row(value: Any, label: str) -> Row:
    _need(type(value) is dict, f"{label} must be a record")
    return value


def _wire(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _digest(value: Any) -> str:
    return sha256(_wire(value)).hexdigest()


def _decimal(value: Any, label: str) -> Decimal:
    _need(type(value) is str and 0 < len(value) <= 512, f"{label} decimal text")
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"saved trace checks: {label} invalid decimal") from error
    _need(number.is_finite() and str(number) == value and abs(number.adjusted()) <= 400,
          f"{label} canonical finite decimal")
    return number


def _reference(ref: Row, reference_sha256: str, retained: bool) -> str:
    _need(type(retained) is bool and type(reference_sha256) is str
          and len(reference_sha256) == 64
          and all(c in "0123456789abcdef" for c in reference_sha256), "reference pin or mode")
    _need(_digest(ref) == reference_sha256, "reference SHA-256 mismatch")
    source = _row(ref.get("normalized"), "reference source")
    mode, candidate = ("retained", "d0001-t0035") if retained else ("artificial", "artificial-moon-mars")
    _need(source.get("scope") == mode and source.get("candidate_id") == candidate
          and source.get("live_authorized") is False
          and "command_words" in source and source["command_words"] is None
          and (reference_sha256 == REFERENCE_SHA256 if retained else reference_sha256 in ARTIFICIAL_REFERENCE_PINS),
          "reference scope or identity")
    return mode


def _gates(value: Any, limits: dict[str, float], label: str) -> None:
    values = _row(value, label)
    _need(set(values) == set(limits)
          and all(type(values[key]) is float and math.isfinite(values[key])
                  and 0 <= values[key] <= limit for key, limit in limits.items()), f"{label} parity gates")


def _point_gates(ref: Row, point: Row, sign: str, methods: Methods) -> tuple[Decimal, Decimal]:
    """Reuse signed-root readback, which performs no signed-conic solve or exponential."""
    source = ref["normalized"]
    endpoints = source.get("endpoints")
    _need(type(endpoints) is list and len(endpoints) == 2, "fixed endpoint inventory")
    moon, mars = (_row(endpoint, "endpoint") for endpoint in endpoints)
    _need(moon.get("body") == "Moon" and mars.get("body") == "Mars", "fixed endpoint order")
    _need(point.get("unresolved") is False, "unresolved saved point")
    local = point.get("relative_si")
    _need(type(local) is list and len(local) == 6
          and all(type(value) is float and math.isfinite(value) for value in local), "binary64 point state")
    precise = point.get("independent_relative_si")
    _need(type(precise) is list and len(precise) == 6, "independent point state")
    for value in precise:
        _decimal(value, "independent point state")
    _decimal(point.get("independent_angle_rad"), "independent anomaly")
    _gates(point.get("discrepancies"), _STATE_GATES, "point state")
    branches = _row(point.get("branches"), "point branches")
    _need(set(branches) == set(SIGNS), "both saved signed roots required")
    branch = _row(branches.get(sign), "point branch")
    _need(branch.get("reason") in (None, "guard"), "saved root failed existing gates")
    endpoint = mars | {"relative_si": [str(Decimal.from_float(value)) for value in local]}
    reader = methods["reader"]
    _need(reader._root(ref["lunar"], moon) is None, "fixed lunar point gates")
    _need(reader._root(branch, endpoint) == branch["reason"], "arrival point gates")
    departure = _decimal(ref["lunar"]["independent_speed_m_s"], "lunar oracle impulse")
    arrival = _decimal(branch["independent_speed_m_s"], "arrival oracle impulse")
    _need(min(departure, arrival) > 0, "positive independent impulse norms")
    return departure, arrival


def prepare_points(ref: Row, points: list[Row], methods: Methods, *, reference_sha256: str,
                   retained: bool, charge_mass: Callable[[], None]) -> Row:
    """Validate three saved SI/J2000 midpoints, charging before each of six Decimal96 masses."""
    scope = _reference(ref, reference_sha256, retained)
    _need(type(points) is list and len(points) == 3, "three saved midpoint points required")
    checked: list[tuple[Row, dict[str, tuple[Decimal, Decimal]]]] = []
    for point, (_, _, _, phase, pin) in zip(points, SELECTION, strict=True):
        _row(point, "midpoint point")
        _need(point.get("phase_deg") == phase, "saved midpoint order or phase")
        _need(not retained or _digest(point) == pin, "saved retained point pin")
        branches = {sign: _point_gates(ref, point, sign, methods) for sign in SIGNS}
        pairs = point.get("pairs")
        _need(type(pairs) is list, "saved pair inventory")
        expected = [["positive", sign] for sign in SIGNS if point["branches"][sign]["reason"] is None]
        _need([_row(pair, "saved pair").get("roots") for pair in pairs] == expected, "saved signed pair inventory")
        for pair in pairs:
            _gates(pair.get("independent_mass_discrepancies"), {"duration_s": 1e-6, "mass_kg": 1e-8}, "saved mass")
        checked.append((point, branches))
    cache: Row = dict(scope=scope, reference_sha256=reference_sha256, points={}, oracle_mass_calls=0)
    for point, branches in checked:
        saved: Row = dict(point_sha256=_digest(point))
        for sign, (departure, arrival) in branches.items():
            charge_mass()
            durations, masses = methods["oracle"].mass(departure, arrival)
            cache["oracle_mass_calls"] += 1
            _need(type(durations) in (tuple, list) and type(masses) in (tuple, list)
                  and len(durations) == len(masses) == 2
                  and all(type(value) is Decimal and value.is_finite() and value > 0
                          for value in (*durations, *masses)), "Decimal96 mass return inventory")
            saved[sign] = dict(departure_m_s=str(departure), arrival_m_s=str(arrival),
                               durations_s=list(map(str, durations)), masses_kg=list(map(str, masses)))
        cache["points"][point["phase_deg"]] = saved
    cache["seal"] = _digest(cache)
    return cache


def _completed(events: list[Row], stage: str) -> Row | None:
    found = [event for event in events if event["stage"] == stage and event["event"] == "return"]
    _need(len(found) <= 1, f"repeated completed {stage}")
    return found[0] if found else None


def verify_containment(ref: Row, point: Row, trace: Row, sign: str, methods: Methods, cache: Row) -> Row:
    """Check applicable saved quantities against sealed ranges, reusing the six cached masses."""
    _need(sign in SIGNS, "signed branch required")
    scope = cache.get("scope")
    _need(scope in ("artificial", "retained"), "cache scope")
    _reference(ref, cache.get("reference_sha256"), scope == "retained")
    _need(cache.get("seal") == _digest({key: value for key, value in cache.items() if key != "seal"})
          and cache.get("oracle_mass_calls") == 6, "prepared point cache seal or inventory")
    schema, original = methods["trace_schema"], methods["containment"]
    schema.verify_trace(trace)
    _need(trace.get("sign") == sign, "point/trace branch identity")
    phase = original._phase(point.get("phase_deg"), "point")
    lo, hi = (original._phase(trace.get(key), f"trace {key}") for key in ("lo", "hi"))
    _need(lo <= phase <= hi, "point outside traced domain")
    saved = _row(_row(cache.get("points"), "cached points").get(str(phase)), "cached point")
    _need(saved.get("point_sha256") == _digest(point), "saved point/cache identity")
    quantities = _row(saved.get(sign), "cached signed quantities")
    departure = _decimal(quantities.get("departure_m_s"), "cached departure")
    arrival = _decimal(quantities.get("arrival_m_s"), "cached arrival")
    durations = [_decimal(value, "cached duration") for value in quantities["durations_s"]]
    masses = [_decimal(value, "cached mass") for value in quantities["masses_kg"]]
    _need(len(durations) == len(masses) == 2, "cached mass return inventory")
    events = trace["events"]
    ellipse, reverse, mass, bound = (_completed(events, stage) for stage in (
        "_ellipse", "_reverse", "_mass_exclusion", "bounds"))
    _need(bound is not None, "missing bound return")
    checks = 0
    not_reached: list[str] = []
    if ellipse is not None:
        for index, value in enumerate(point["independent_relative_si"]):
            group, component = divmod(index, 3)
            path = f"return[{group}][{component}]"
            original._contains(ellipse, path, _decimal(value, "independent ellipse state"))
            original._same(ellipse, path, bound, f"{'r' if group == 0 else 'orbital'}[{component}]")
        original._contains(ellipse, "anomaly", _decimal(point["independent_angle_rad"], "independent anomaly"))
        original._same(ellipse, "return[2]", bound, "mu")
        checks += 7
    else:
        not_reached += ["ellipse_state[0:6]", "ellipse_anomaly"]
    if reverse is not None:
        for index in range(3):
            original._same(reverse, f"return[{index}]", bound, f"future[{index}]")
        root_lo, root_hi = original._range(reverse, "root")
        _need(root_lo > 0 if sign == "positive" else root_hi < 0, "root enclosure sign")
    if "speed" in bound["fields"]:
        original._contains(bound, "speed", arrival)
        checks += 1
    else:
        not_reached.append("arrival_speed")
    comparison_words: list[str] = []
    if mass is not None:
        original._contains(mass, "departure", departure)
        original._contains(mass, "arrival", arrival)
        original._same(mass, "arrival", bound, "speed")
        result = _row(trace.get("result"), "bound result")
        speed_bounds = result.get("arrival_speed_bounds_m_s")
        _need(type(speed_bounds) is list and len(speed_bounds) == 2
              and tuple(_decimal(value, "final norm endpoint") for value in speed_bounds)
              == original._range(bound, "speed"), "final norm endpoint identity")
        for path, value in zip(("coast", "final", "durations[0]", "durations[1]"), (*masses, *durations), strict=True):
            original._contains(mass, path, value)
        words = result.get("duration_comparison_lower_words")
        _need(type(words) is list and len(words) == 2, "comparison duration endpoint inventory")
        scalars = _row(mass.get("scalars"), "mass scalar inventory")
        for index, duration in enumerate(durations):
            comparison = float(duration)
            _need(math.isfinite(comparison), "finite designated binary64 duration")
            original._contains(mass, f"observed_duration_binary64[{index}]", Decimal.from_float(comparison))
            word = words[index]
            _need(type(word) is str, "binary64 lower word")
            try:
                lower = float.fromhex(word)
            except ValueError as error:
                raise ValueError("saved trace checks: malformed binary64 lower word") from error
            _need(math.isfinite(lower) and lower.hex() == word and lower <= comparison
                  and scalars.get(f"conversion_lower[{index}]") == word, "designated duration lower endpoint")
            comparison_words.append(comparison.hex())
        checks += 8
    else:
        not_reached += ["mass_departure", "mass_arrival", "coast_mass", "final_mass",
                        "duration[0]", "duration[1]", "duration_binary64[0]", "duration_binary64[1]"]
    stages = trace["stages"]
    _need(stages["_clearance"]["status"] != "not-reached"
          or trace["result"].get("reason") == "mass" or trace["status"] == "early-failure",
          "unexplained non-reached clearance")
    return dict(status="verified", scope=scope, phase_deg=str(phase), sign=sign,
                independent_arrival_speed_m_s=str(arrival), independent_relative_si=list(point["independent_relative_si"]),
                independent_durations_s=list(map(str, durations)), independent_masses_kg=list(map(str, masses)),
                comparison_duration_words=comparison_words, containment_checks=checks,
                not_reached_quantities=not_reached, root_status=stages["_reverse"]["status"],
                clearance_status=stages["_clearance"]["status"])


def _unit(stage: str, field: str) -> str:
    base = field.split("[", 1)[0]
    units = {
        "bounds": {"ldeg": "deg", "hdeg": "deg", "pi": "rad", "anomaly": "rad", "mu": "m3/s2",
                   "r": "m", "orbital": "m/s", "future": "m/s", "speed": "m/s",
                   "clearance": "m", "minimum": "m", "radial": "m/s"},
        "_ellipse": {"anomaly": "rad", "mu": "m3/s2", "peri": "m", "a": "m", "p": "m", "h": "m2/s",
                     "radius": "m", "u": "m/s", "t": "m/s"},
        "_reverse": {"r": "m", "given": "m/s", "v_inf": "m/s", "mu": "m3/s2", "radius": "m",
                     "linear": "m2/s", "constant": "m4/s2", "discriminant_sq": "m4/s2", "disc": "m2/s",
                     "root": "m2/s", "signed_h": "m2/s", "return": "m/s"},
        "_mass_exclusion": {"departure": "m/s", "arrival": "m/s", "init": "kg", "coast": "kg", "final": "kg",
                            "rate": "kg/s", "durations": "s", "observed_duration_binary64": "s"},
        "_clearance": {"r": "m", "v": "m/s", "mu": "m3/s2", "surface": "m", "radius": "m",
                       "radial": "m/s", "minimum": "m", "h": "m2/s", "peri": "m"},
    }
    dimensionless = {
        "_ellipse": {"e", "sin_i", "cos_i", "sin_o", "cos_o", "sin_u", "cos_u", "sin_nu", "cos_nu",
                     "node", "normal", "onto_plane", "radial_hat", "transverse_hat"},
        "_reverse": {"r_hat", "direction", "normal", "e_inf"}, "_clearance": {"r_hat", "ecc"},
    }
    if stage == "_ellipse" and base == "return":
        return "m" if field.startswith("return[0]") else "m/s" if field.startswith("return[1]") else "m3/s2"
    if stage == "_clearance" and base == "return":
        return "m/s" if field == "return[2]" else "m"
    if base in dimensionless.get(stage, set()):
        return "1"
    _need(base in units[stage], f"unclassified selected numeric field {stage}.{field}")
    return units[stage][base]


def _widths(trace: Row) -> dict[tuple[int, str, str], Row]:
    widths: dict[tuple[int, str, str], Row] = {}
    for event in trace["events"]:
        if event["stage"] not in SELECTED_STAGES or event["event"] == "call":
            continue
        for field, endpoint in sorted(_row(event["fields"], "selected fields").items()):
            endpoint = _row(endpoint, "selected endpoints")
            _need(set(endpoint) == {"lo", "hi"}, "selected endpoint inventory")
            lo, hi = (_decimal(endpoint[side], "selected endpoint") for side in ("lo", "hi"))
            _need(lo <= hi, "selected endpoint order")
            key = event["call"], event["stage"], field
            _need(key not in widths, "repeated selected field")
            widths[key] = dict(call=key[0], stage=key[1], field=field, units=_unit(key[1], field),
                               event=event["event"], lo=str(lo), hi=str(hi), width=str(Fraction(hi)-Fraction(lo)))
    return widths


def summarize(rows: list[Row]) -> Row:
    """Describe exact SI widths and corresponding cell-minus-singleton widths, without ranking."""
    expected = [(index, domain, lo if domain == "cell" else mid, hi if domain == "cell" else mid, sign, ind)
                for index, lo, hi, mid, _ in SELECTION for domain in ("cell", "singleton")
                for sign in SIGNS for ind in (False, True)]
    _need(type(rows) is list and len(rows) == len(expected), "fixed 24-row width matrix")
    records: list[Row] = []
    by_domain: dict[tuple[int, str, str, bool], dict[tuple[int, str, str], Row]] = {}
    for row, identity in zip(rows, expected, strict=True):
        _need(tuple(row.get(key) for key in ("row_index", "domain", "lo_deg", "hi_deg", "sign", "independent"))
              == identity and type(row.get("row_index")) is int and type(row.get("independent")) is bool,
              "width matrix identity or order")
        trace = _row(row.get("trace"), "width trace")
        _need(tuple(trace.get(key) for key in ("lo", "hi", "sign", "independent")) == identity[2:]
              and _wire(trace["result"]) == _wire(row.get("control")), "width trace/control identity")
        widths = _widths(trace)
        key = identity[0], identity[1], identity[4], identity[5]
        by_domain[key] = widths
        records.append(dict(row_index=identity[0], domain=identity[1], sign=identity[4], independent=identity[5],
                            stages=trace["stages"], quantities=list(widths.values())))
    comparisons: list[Row] = []
    for index, _, _, _, _ in SELECTION:
        for sign in SIGNS:
            for independent in (False, True):
                cell = by_domain[index, "cell", sign, independent]
                singleton = by_domain[index, "singleton", sign, independent]
                for key in sorted(cell.keys() | singleton.keys()):
                    a, b = cell.get(key), singleton.get(key)
                    match = a is not None and b is not None
                    _need(not match or a["units"] == b["units"], "comparison dimensions")
                    cell_width = Fraction(a["width"]) if a is not None else None
                    singleton_width = Fraction(b["width"]) if b is not None else None
                    comparisons.append(dict(row_index=index, sign=sign, independent=independent,
                        call=key[0], stage=key[1], field=key[2], units=(a if a is not None else b)["units"],
                        status="matched" if match else "cell-not-reached" if a is None else "singleton-not-reached",
                        cell_width=str(cell_width) if cell_width is not None else None,
                        singleton_width=str(singleton_width) if singleton_width is not None else None,
                        difference=str(cell_width-singleton_width) if match else None,
                        ratio=str(cell_width/singleton_width) if match and singleton_width else None))
    return dict(status="descriptive-only", selected_stages=list(SELECTED_STAGES),
                selection="all interval fields on selected-stage return/error events",
                excluded_primitives="_cross/_unit/_norm2/_binary64 raw fields remain unclassified; no width ranking",
                endpoint_evidence="canonical decimal endpoints retained in traces and quantities",
                width_definition="Fraction(Decimal(hi))-Fraction(Decimal(lo))", records=records, comparisons=comparisons)
