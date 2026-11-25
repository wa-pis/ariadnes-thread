"""Private isolated ADR0255 fabricated-packet checks; no native producer."""

from __future__ import annotations

from collections.abc import Sequence
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any

from ._coupled_benchmark_run import (
    RunError, _Evidence, _install_import_guard, _json_bytes, _watch_worker,
)

_INPUT_BYTES = 64 * 1024
_EVIDENCE_BYTES = 2 * 1024 * 1024
_REPORT_RESERVE = 16 * 1024
_TOTAL_SECONDS = 15.0


def _now() -> float:
    value = time.monotonic()
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise RunError("monotonic clock: finite number required")
    return float(value)


def _check(deadline_s: float, *, minimum_s: float) -> float:
    now = _now()
    if now < minimum_s:
        raise RunError("monotonic clock moved backwards")
    if now >= deadline_s:
        raise RunError("inherited15s deadline exhausted")
    return now


def _worker_command(source: Path, deadline_s: float) -> list[str]:
    return [sys.executable, "-m", "space_nav._realized_clock_run", "--worker",
            str(source), "--deadline", repr(deadline_s)]


def _sync(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _result(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(_EVIDENCE_BYTES + 1)
    if len(raw) > _EVIDENCE_BYTES:
        raise RunError("worker result exceeds evidence byte cap")
    try:
        value = json.loads(raw)
        _json_bytes(value)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise RunError("worker result: invalid finite JSON") from exc
    if not isinstance(value, dict):
        raise RunError("worker result: object required")
    return value


def run(raw: bytes, directory: Path, *, started_s: float | None = None) -> dict[str, object]:
    """Check fabricated bytes once, including startup and final fsync.

    The caller must supervise this parent with the same absolute15s watchdog to
    bound opaque parent I/O; cooperative checks alone cannot interrupt fsync.
    """
    entered_s = _now()
    if type(raw) is not bytes or len(raw) > _INPUT_BYTES:
        raise RunError("input: bytes of at most64KiB required before decode")
    if started_s is None:
        started_s = entered_s
    if (isinstance(started_s, bool) or not isinstance(started_s, (int, float))
            or not math.isfinite(started_s) or started_s > entered_s):
        raise RunError("parent start: finite past monotonic time required")
    started_s = float(started_s)
    deadline_s = started_s + _TOTAL_SECONDS
    last_s = _check(deadline_s, minimum_s=entered_s)
    directory.mkdir(parents=False, exist_ok=False)
    evidence = _Evidence(directory)
    source, output, errors = (directory / name for name in
                              ("input.json", "result.json", "worker.stderr.log"))
    report: dict[str, object] = {
        "schema": "ariadna-realized-clock-run-v1", "status": "failed",
        "scope": "fabricated packet diagnostic only", "physical_admission": "unavailable",
        "failure": None, "worker": None, "result": None,
        "started_monotonic_s": started_s, "startup_elapsed_s": entered_s - started_s,
        "limits": {"overall_s": _TOTAL_SECONDS, "input_bytes": _INPUT_BYTES,
                   "combined_evidence_bytes": _EVIDENCE_BYTES},
        "finalization": "pending-parent-check",
    }
    try:
        evidence.write(source, raw)
        _sync(source)
        last_s = _check(deadline_s, minimum_s=last_s)
        for path in (output, errors):
            with path.open("xb"):
                pass
        worker = _watch_worker(_worker_command(source, deadline_s), output, errors,
                               deadline_s, evidence)
        report["worker"] = worker
        last_s = _check(deadline_s, minimum_s=last_s)
        result = _result(output)
        report["result"] = result
        if worker["exit_code"] != 0:
            raise RunError(str(result.get("error", "fabricated checker failed")))
        if (result.get("schema") != "ariadna-realized-clock-check-v1"
                or result.get("structural_status") != "valid"
                or result.get("status") not in {"passed", "failed", "unavailable", "inconclusive"}
                or result.get("scientific_admission") != "unavailable"
                or result.get("physical_admission") != "unavailable"):
            raise RunError("worker result: fixed diagnostic contract mismatch")
        report["status"] = "passed"
    except (RunError, OSError, ValueError, TypeError) as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"
    report["evidence_bytes_before_report"] = evidence.used
    # The durable record cannot attest to a clock observation made after its own fsync.
    report_data = _json_bytes(report)
    if len(report_data) > _REPORT_RESERVE or evidence.used + len(report_data) > _EVIDENCE_BYTES:
        raise RunError("combined report/evidence byte cap exhausted")
    report_path = directory / "report.json"
    try:
        with report_path.open("xb") as stream:
            stream.write(report_data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        reason = report["failure"] or "durable report write failed"
        raise RunError(f"{reason}; final report: {exc}") from exc
    try:
        for path in (source, output, errors):
            if path.exists():
                _sync(path)
            last_s = _check(deadline_s, minimum_s=last_s)
        last_s = _check(deadline_s, minimum_s=last_s)
    except (RunError, OSError, ValueError) as exc:
        report["status"] = "failed"
        if report["failure"] is None:
            report["failure"] = f"{type(exc).__name__}: {exc}"
        report["finalization"] = "failed-after-fsync"
    else:
        report["finalization"] = "checked-after-fsync"
    report["evidence_bytes"] = evidence.used + len(report_data)
    report["elapsed_at_last_valid_check_s"] = last_s - started_s
    return report


def _worker(source: Path, deadline_s: float) -> int:
    _check(deadline_s, minimum_s=0.0)
    _install_import_guard(True)
    from ._realized_clock_packet import PacketError, check_packet
    try:
        with source.open("rb") as stream:
            raw = stream.read(_INPUT_BYTES + 1)
        if len(raw) > _INPUT_BYTES:
            raise RunError("input byte cap64KiB before decode")
        result = check_packet(raw, deadline_s=deadline_s)
        _check(deadline_s, minimum_s=0.0)
    except (PacketError, RunError, OSError) as exc:
        result = {"status": "failed", "error_type": type(exc).__name__, "error": str(exc),
                  "physical_admission": "unavailable"}
        sys.stdout.buffer.write(_json_bytes(result))
        return 2
    sys.stdout.buffer.write(_json_bytes(result))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Private fixed worker entry; no public command or native execution path."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 4 or args[0] != "--worker" or args[2] != "--deadline":
        raise RunError("private worker requires --worker INPUT --deadline ABS_MONOTONIC")
    try:
        deadline_s = float(args[3])
    except ValueError as exc:
        raise RunError("worker deadline: finite number required") from exc
    if not math.isfinite(deadline_s):
        raise RunError("worker deadline: finite number required")
    return _worker(Path(args[1]), deadline_s)


if __name__ == "__main__":
    raise SystemExit(main())
