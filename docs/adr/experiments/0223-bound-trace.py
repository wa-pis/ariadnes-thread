"""Observe unchanged, pinned signed bounds on explicitly artificial operands only."""

from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import sys
from types import FrameType, ModuleType
from typing import Any, Callable

type Row = dict[str, Any]

_STAGES = ("bounds", "_ellipse", "_reverse", "_unit", "_cross", "_norm2",
           "_mass_exclusion", "_clearance", "_binary64")
_CHILDREN = {
    "_ellipse": ["_cross", "_cross"], "_unit": ["_norm2"],
    "_cross": [], "_norm2": [], "_binary64": [],
    "_reverse": ["_unit", "_unit", "_cross", "_norm2", "_norm2", "_cross",
                 "_norm2", "_norm2", "_unit", "_cross", "_cross", "_norm2"],
    "_mass_exclusion": ["_binary64", "_binary64"],
}


def _required(stage: str) -> set[str]:
    scalar = {
        "_ellipse": "anomaly mu peri e sin_i cos_i sin_o cos_o sin_u cos_u sin_nu cos_nu a p h radius u t return[2]",
        "_reverse": "mu radius linear constant discriminant_sq disc root",
        "_norm2": "return", "_mass_exclusion": "departure arrival init coast final rate durations[0] durations[1] observed_duration_binary64[0] observed_duration_binary64[1]",
        "_clearance": "mu surface radius radial minimum return[0] return[1] return[2]",
        "bounds": "anomaly mu speed", "_cross": "", "_unit": "", "_binary64": "",
    }
    vectors = {
        "_ellipse": "node normal onto_plane radial_hat transverse_hat return[0] return[1]",
        "_reverse": "r given v_inf r_hat direction normal signed_h e_inf return",
        "_norm2": "v", "_unit": "v return", "_cross": "a b return",
        "_clearance": "r v r_hat", "bounds": "r orbital future", "_mass_exclusion": "", "_binary64": "",
    }
    return set(scalar[stage].split()) | {
        f"{name}[{index}]" for name in vectors[stage].split() for index in range(3)}


def _seal(record: Row) -> str:
    content = {key: value for key, value in record.items() if key != "seal"}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _snapshot(values: Row) -> tuple[Row, Row]:
    fields: Row = {}
    scalars: Row = {}

    def capture(path: str, value: Any) -> None:
        if hasattr(value, "lo") and hasattr(value, "hi"):
            if not (isinstance(value.lo, Decimal) and isinstance(value.hi, Decimal)
                    and value.lo.is_finite() and value.hi.is_finite() and value.lo <= value.hi):
                raise ValueError("invalid observed interval")
            fields[path] = {"lo": str(value.lo), "hi": str(value.hi)}
        elif isinstance(value, (tuple, list)):
            for index, part in enumerate(value):
                capture(f"{path}[{index}]", part)
        elif path.startswith("return") and isinstance(value, dict):
            for key, part in value.items():
                capture(f"{path}.{key}", part)
        elif isinstance(value, Fraction):
            scalars[path] = str(value)
        elif isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError("nonfinite observed scalar")
            scalars[path] = str(value)
        elif type(value) is float:
            if not math.isfinite(value):
                raise ValueError("nonfinite observed binary64")
            scalars[path] = value.hex()
        elif value is None or type(value) in (bool, int, str):
            scalars[path] = value

    for name, value in values.items():
        capture(name, value)
    return fields, scalars


def _inventory(events: list[Row]) -> Row:
    stages = {}
    for stage in _STAGES:
        counts = {name: sum(e["stage"] == stage and e["event"] == event for e in events)
                  for name, event in (("calls", "call"), ("returns", "return"), ("errors", "error"))}
        stages[stage] = counts | {"status": "error" if counts["errors"] else
                                 "complete" if counts["returns"] else "not-reached"}
    return stages


def trace_bound(ref: Row, lo: Fraction, hi: Fraction, sign: str, methods: dict[str, ModuleType],
                *, independent: bool, check: Callable[[], None], emit: Callable[[Row], None]) -> Row:
    """Emit before retaining each event; the caller owns the shared resource budget."""
    source = ref.get("normalized", {})
    if (source.get("scope"), source.get("candidate_id"), source.get("live_authorized"), source.get("command_words")) != (
            "artificial", "artificial-moon-mars", False, None):
        raise ValueError("artificial trace scope required")
    previous = sys.getprofile()
    if previous is not None:
        raise ValueError("foreign profiler is active")
    bounds, interval = methods["bounds"], methods["interval"]
    codes = {getattr(bounds, name).__code__: name for name in _STAGES if name != "_binary64"}
    codes[interval._binary64.__code__] = "_binary64"
    events: list[Row] = []
    stack: list[tuple[int, int | None]] = []
    calls = 0

    def observe(frame: FrameType, event: str, value: Any) -> None:
        nonlocal calls
        if event not in ("call", "return"):
            return
        check()
        stage = codes.get(frame.f_code)
        if stage is None:
            return
        if event == "call":
            call, parent = calls, stack[-1][0] if stack else None
            calls += 1
            stack.append((call, parent))
        else:
            call, parent = stack.pop()
        values = dict(frame.f_locals)
        if event == "return":
            values["return"] = value
        fields, scalars = _snapshot(values)
        if stage == "_mass_exclusion" and event == "return" and value is not None:
            # Metadata: monotone nearest-binary64 image of the observed duration endpoints.
            for index, duration in enumerate(values["durations"]):
                fields[f"observed_duration_binary64[{index}]"] = {
                    "lo": str(Decimal.from_float(float(duration.lo))),
                    "hi": str(Decimal.from_float(float(duration.hi)))}
        item = dict(index=len(events), call=call, parent=parent, stage=stage,
                    event="error" if event == "return" and value is None else event,
                    fields=fields, scalars=scalars)
        if len(events) >= 8192:
            raise ValueError("trace event cap exhausted")
        emit(item)
        events.append(item)

    check()
    try:
        sys.setprofile(observe)
        result = bounds.bounds(ref, lo, hi, sign, interval, independent=independent)
    finally:
        sys.setprofile(previous)
    check()
    record = dict(result=result, events=events, stages=_inventory(events), lo=str(lo), hi=str(hi),
                  sign=sign, independent=independent,
                  status="early-failure" if "detail" in result else "complete")
    record["seal"] = _seal(record)
    verify_trace(record, result)
    return record


def _decimal(value: Any) -> Decimal:
    if type(value) is not str:
        raise ValueError("noncanonical trace endpoint")
    try:
        result = Decimal(value)
    except ArithmeticError as error:
        raise ValueError("invalid trace endpoint") from error
    if not result.is_finite() or str(result) != value:
        raise ValueError("noncanonical trace endpoint")
    return result


def verify_trace(record: Row, expected_result: Row | None = None) -> None:
    """Check structure and observation links without replaying any enclosure formula."""
    if record["seal"] != _seal(record):
        raise ValueError("trace seal mismatch")
    if expected_result is not None and record["result"] != expected_result:
        raise ValueError("original bound result mismatch")
    events, result = record["events"], record["result"]
    if not isinstance(events, list) or not 0 < len(events) <= 8192:
        raise ValueError("invalid trace events")
    stack: list[int] = []
    opened: dict[int, Row] = {}
    closed: dict[int, Row] = {}
    children: dict[int, list[str]] = {}
    for index, event in enumerate(events):
        if event["index"] != index or event["stage"] not in _STAGES:
            raise ValueError("unordered trace stage")
        for value in event["fields"].values():
            if set(value) != {"lo", "hi"} or _decimal(value["lo"]) > _decimal(value["hi"]):
                raise ValueError("invalid trace interval")
        call = event["call"]
        if event["event"] == "call":
            parent = stack[-1] if stack else None
            if call != len(opened) or event["parent"] != parent:
                raise ValueError("invalid trace call order")
            if parent is not None:
                children[parent].append(event["stage"])
            opened[call], children[call] = event, []
            stack.append(call)
        elif event["event"] in ("return", "error"):
            if (not stack or stack.pop() != call or call in closed
                    or (event["parent"], event["stage"]) !=
                    (opened[call]["parent"], opened[call]["stage"])):
                raise ValueError("unpaired trace return")
            closed[call] = event
        else:
            raise ValueError("invalid trace event kind")
    if stack or len(opened) != len(closed) or record["stages"] != _inventory(events):
        raise ValueError("incomplete trace inventory")
    if opened[0]["stage"] != "bounds" or closed[0]["event"] != "return":
        raise ValueError("missing original bound return")
    _, expected_scalars = _snapshot({"return": result})
    if {key: value for key, value in closed[0]["scalars"].items()
            if key.startswith("return.")} != expected_scalars:
        raise ValueError("bound return observation mismatch")
    early = "detail" in result
    if record["status"] != ("early-failure" if early else "complete"):
        raise ValueError("false trace completion")
    for call, start in opened.items():
        end, stage = closed[call], start["stage"]
        expected = _CHILDREN.get(stage)
        if stage == "bounds":
            expected = ["_ellipse", "_reverse", "_norm2", "_mass_exclusion"]
            if result.get("reason") != "mass":
                expected += ["_clearance"]
        elif stage == "_clearance":
            expected = ["_norm2", "_unit"]
            radial = end["fields"].get("radial")
            if radial is not None and _decimal(radial["lo"]) < 0:
                expected += ["_cross", "_cross", "_norm2", "_norm2"]
        if expected is None or (children[call] != expected and not (
                (end["event"] == "error" or early and stage == "bounds")
                and children[call] == expected[:len(children[call])])):
            raise ValueError("missing or incompatible trace stage")
        for key, value in start["fields"].items():
            if end["fields"].get(key) != value:
                raise ValueError("observed argument changed")
        if end["event"] == "return" and not (early and stage == "bounds"):
            if not _required(stage) <= end["fields"].keys():
                raise ValueError("missing mandatory trace interval")
            if stage in ("_norm2", "_unit", "_cross", "_ellipse", "_reverse", "_clearance"):
                if not any(key == "return" or key.startswith("return[") for key in end["fields"]):
                    raise ValueError("missing observed interval result")
            if stage == "_mass_exclusion":
                for index in range(2):
                    value = end["fields"][f"durations[{index}]"]
                    image = {side: str(Decimal.from_float(float(_decimal(value[side]))))
                             for side in ("lo", "hi")}
                    if end["fields"].get(f"observed_duration_binary64[{index}]") != image:
                        raise ValueError("binary64 duration image mismatch")
    if any(opened[0]["scalars"].get(key) != record[key] for key in ("lo", "hi", "sign", "independent")):
        raise ValueError("trace input metadata mismatch")
    errors = any(event["event"] == "error" for event in events)
    if errors != early:
        raise ValueError("unreported trace stage failure")
    if not early:
        mass = next(e for e in events if e["stage"] == "_mass_exclusion" and e["event"] == "return")
        speed = closed[0]["fields"]["speed"]
        if mass["fields"]["arrival"] != speed or [speed["lo"], speed["hi"]] != result["arrival_speed_bounds_m_s"]:
            raise ValueError("arrival speed observation mismatch")
