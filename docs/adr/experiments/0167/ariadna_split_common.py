"""Private ADR0166 evidence formats and time/call bounds (stdlib only)."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction
from hashlib import file_digest
import json
import math
from pathlib import Path
from time import monotonic
from typing import Any, TextIO

CAPTURE_CAPS = {"setup": 1, "inventory": 30, "state": 9, "selector": 6}
ANALYSIS_CAPS = {"binary64_field": 3, "decimal_field": 18}
BUDGETS = {"capture": 15.0, "analysis": 10.0}
FAILURES = (ValueError, RuntimeError, OSError, ImportError, LookupError, ArithmeticError, TypeError)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def number(value: Any, field: str) -> float:
    require(type(value) in (float, int), f"{field}: expected nonboolean number")
    result = float(value)
    require(math.isfinite(result), f"{field}: expected finite number")
    return result


def parse_json(raw: bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in items:
            require(name not in result, "duplicate JSON key: " + name)
            result[name] = value
        return result

    def finite(raw_number: str) -> float:
        value = float(raw_number)
        require(math.isfinite(value), "nonfinite JSON number: " + raw_number)
        return value

    result = json.loads(raw, object_pairs_hook=pairs, parse_float=finite, parse_constant=finite)
    require(type(result) is dict, "expected JSON object")
    return result


def wire(value: Any) -> Any:
    """Preserve invalid native returns as evidence, never as finite operands."""
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else {"invalid_numeric": repr(value)}
    if type(value) in (tuple, list):
        return [wire(item) for item in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: wire(item) for k, item in value.items()}
    if type(value) in (Fraction, Decimal):
        return str(value)
    if hasattr(value, "tolist"):
        return wire(value.tolist())
    return {"invalid_type": type(value).__name__, "representation": repr(value)}


def encode(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode() + b"\n"


def same(actual: Any, expected: Any, message: str) -> None:
    # JSON preserves signed zero and distinguishes bool from int.
    require(encode(actual) == encode(expected), message)


def journal_rows(index: int, entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Wire snapshots in ledger order, including any uncompleted call."""
    first = {k: entry[k] for k in ("operation", "api", "args", "attempted_s")}
    rows = [{"index": index, "phase": "attempt", "entry": first}]
    if "raw" in entry:
        returned = {**first, "raw": entry["raw"], "returned_s": entry["returned_s"]}
        rows.append({"index": index, "phase": "return", "entry": returned})
        if "completed_s" in entry:
            rows.append({"index": index, "phase": "complete",
                         "entry": {**returned, "completed_s": entry["completed_s"]}})
    return rows


class Recorder:
    """Count attempts before invocation and flush the raw result before validation."""

    def __init__(
        self, report: dict[str, Any], caps: dict[str, int], start_s: float, budget_s: float,
        *, clock: Callable[[], float] = monotonic, journal: TextIO | None = None,
    ) -> None:
        self.clock = clock
        self.start_s = number(start_s, "external process start")
        self.budget_s = budget_s
        self.journal = journal
        self.caps = dict(caps)
        self.last_s = 0.0
        self.ledger: list[dict[str, Any]] = []
        self.counts = {op: dict.fromkeys(("attempted", "returned", "completed"), 0) for op in caps}
        report.update(ledger=self.ledger, counts=self.counts, budget_s=budget_s)

    def elapsed(self) -> float:
        return self.clock() - self.start_s

    def check(self, elapsed: float | None = None) -> float:
        stamp = number(self.elapsed() if elapsed is None else elapsed, "elapsed time")
        require(self.last_s <= stamp <= self.budget_s, "deadline or nonmonotonic clock")
        self.last_s = stamp
        return stamp

    def _flush_event(self, entry: dict[str, Any]) -> None:
        if self.journal is not None:
            self.journal.write(encode(journal_rows(len(self.ledger) - 1, entry)[-1]).decode())
            self.journal.flush()

    def call(
        self, operation: str, api: str, args: list[Any], invoke: Callable[[], Any],
        validate: Callable[[Any], None] | None = None,
    ) -> Any:
        stamp = self.check()
        require(operation in self.caps, "unknown operation: " + operation)
        counts = self.counts[operation]
        require(counts["attempted"] < self.caps[operation], "call cap: " + operation)
        entry = {"operation": operation, "api": api, "args": wire(args), "attempted_s": stamp}
        self.ledger.append(entry)
        counts["attempted"] += 1
        self._flush_event(entry)
        self.check()
        result = invoke()
        entry["raw"] = wire(result)
        returned_s = self.elapsed()
        entry["returned_s"] = wire(returned_s)
        counts["returned"] += 1
        self._flush_event(entry)
        self.check(returned_s)
        self.check()
        if validate is not None:
            validate(result)
        entry["completed_s"] = self.check()
        counts["completed"] += 1
        self._flush_event(entry)
        self.check()
        return result
