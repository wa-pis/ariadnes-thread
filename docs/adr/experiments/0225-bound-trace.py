"""Observe unchanged signed bounds through a full-reference hash boundary."""

from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction
from hashlib import sha256
import json
import sys
from types import FrameType, ModuleType
from typing import Any

type Row = dict[str, Any]

REFERENCE_SHA256 = "6b845f74881f658d2eeea28bfdde43c9190a283da5bb166644bb845c4f847c5b"
ARTIFICIAL_REFERENCE_SHA256 = (
    "cf20fb7d66cb6efe54b809519d1c0ca8f3031aee83c8532de4a20e2c6f0b1cec",
    "5316e28ef1c7c27035ba9ef08c2fa26ac9d600d04ba8a06af1dc69fe6c4c5467",
)


def trace_bound(
    ref: Row, lo: Fraction, hi: Fraction, sign: str, methods: dict[str, ModuleType],
    *, independent: bool, check: Callable[[], None], emit: Callable[[Row], None],
    reference_sha256: str, retained: bool,
) -> Row:
    """Observe one authenticated reference; the caller owns budgets and authorization."""
    check()
    if (type(reference_sha256) is not str or len(reference_sha256) != 64
            or any(char not in "0123456789abcdef" for char in reference_sha256)):
        raise ValueError("expected reference SHA-256")
    if type(retained) is not bool or type(independent) is not bool:
        raise ValueError("trace mode must be boolean")
    if type(ref) is not dict or type(ref.get("normalized")) is not dict:
        raise ValueError("invalid trace reference")
    raw = (json.dumps(ref, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    if sha256(raw).hexdigest() != reference_sha256:
        raise ValueError("reference SHA-256 mismatch")
    source = ref["normalized"]
    expected_scope = ("retained", "d0001-t0035") if retained else (
        "artificial", "artificial-moon-mars")
    if ((source.get("scope"), source.get("candidate_id")) != expected_scope
            or source.get("live_authorized") is not False
            or "command_words" not in source or source["command_words"] is not None
            or (reference_sha256 != REFERENCE_SHA256 if retained
                else reference_sha256 not in ARTIFICIAL_REFERENCE_SHA256)):
        raise ValueError("retained trace scope required" if retained else "artificial trace scope required")
    check()
    previous = sys.getprofile()
    if previous is not None:
        raise ValueError("foreign profiler is active")
    bounds, interval, schema = methods["bounds"], methods["interval"], methods["trace_schema"]
    codes = {getattr(bounds, name).__code__: name for name in schema._STAGES if name != "_binary64"}
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
        fields, scalars = schema._snapshot(values)
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
    record = dict(result=result, events=events, stages=schema._inventory(events), lo=str(lo), hi=str(hi),
                  sign=sign, independent=independent,
                  status="early-failure" if "detail" in result else "complete")
    record["seal"] = schema._seal(record)
    schema.verify_trace(record, result)
    return record
