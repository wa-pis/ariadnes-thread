"""Private ADR0270 import-only observation; native execution needs F18.6 authority.

The unchanged owner watcher bounds children, including observer I/O. Its caller
must supervise cold parent imports and final fsync on the same inherited clock.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import hashlib
import math
import os
from pathlib import Path
import re
import sys
from typing import Any

from ._owner_endpoint_run import (
    AUDIT_BYTES, EVIDENCE_BYTES, INPUT_BYTES, LOG_BYTES, REPORT_BYTES, RunError,
    _Evidence, _decode, _json_bytes, _now, _read, _sync, _watch_worker,
)

TRACE_BYTES = 4096
MARKER_BYTES = 512
_PHASES = ("bootstrap-ready", "guards-ready", "native-import-enter",
           "native-import-return", "spice-guard-ready", "complete")
_PROFILE_KEYS = {"schema", "scope", "mode", "kernel_path", "kernel_sha256", "probe_sha256"}


def _check(deadline_s: float, minimum_s: float) -> float:
    now = _now()
    if now < minimum_s:
        raise RunError("monotonic clock moved backwards")
    if now >= deadline_s:
        raise RunError("absolute deadline exhausted")
    return now


def _start(started_s: float | None, entered_s: float) -> float:
    if started_s is None:
        return entered_s
    if (type(started_s) not in (int, float) or not math.isfinite(started_s)
            or started_s > entered_s):
        raise RunError("parent start must be finite past monotonic time")
    return float(started_s)


def _profile(raw: bytes) -> dict[str, Any]:
    profile = _decode(raw, INPUT_BYTES)
    if (set(profile) != _PROFILE_KEYS or profile["schema"] != "ariadna-import-input-v1"
            or profile["scope"] != "import-only" or profile["mode"] not in ("native", "injected")):
        raise RunError("fixed import-only profile mismatch")
    for field in ("probe_sha256", "kernel_sha256"):
        if type(profile[field]) is not str or re.fullmatch(r"[0-9a-f]{64}", profile[field]) is None:
            raise RunError(field + ": lowercase SHA256 required")
    path = profile["kernel_path"]
    if type(path) is not str or not Path(path).is_absolute() or "\0" in path:
        raise RunError("kernel_path: absolute path required")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != profile["probe_sha256"]:
        raise RunError("probe source identity mismatch")
    if len(_json_bytes(_marker(5, 44.99999999999999, profile))) > MARKER_BYTES:
        raise RunError("kernel_path exceeds fixed marker byte cap")
    return profile


def _marker(index: int, elapsed_s: float, profile: dict[str, Any]) -> dict[str, object]:
    marker: dict[str, object] = {
        "schema": "ariadna-import-marker-v1", "scope": "import-only", "index": index,
        "phase": _PHASES[index], "elapsed_s": elapsed_s,
    }
    if index == 5:
        marker.update(kernel_path=profile["kernel_path"], kernel_sha256=profile["kernel_sha256"])
    return marker


def _prepare(started_s: float) -> object:
    from ._owner_endpoint_fixture import Budget
    budget = Budget(started_s)
    from ._native_arc_conformance import _source_guard
    sys.addaudithook(lambda event, args: _source_guard(budget, event, args))
    return budget


def _import_spice() -> object:
    from tudatpy.interface import spice
    return spice


def _guard_spice(budget: object, spice: object) -> None:
    from ._native_arc_conformance import _guard_spice as install
    install(budget, spice)


def probe(raw: bytes, trace: Path, *, started_s: float, deadline_s: float,
          prepare: Callable[[float], object] | None = None,
          import_spice: Callable[[], object] | None = None,
          guard_spice: Callable[[object, object], None] | None = None) -> None:
    """Observe the fixed prefix only; injections cannot select the native path."""
    entered = _now()
    started_s = _start(started_s, entered)
    if (type(deadline_s) not in (int, float) or not math.isfinite(deadline_s)
            or deadline_s > started_s + 45.0):
        raise RunError("producer deadline exceeds fixed phase")
    last = _check(deadline_s, entered)
    profile = _profile(raw)
    hooks = (prepare, import_spice, guard_spice)
    if profile["mode"] == "injected":
        if not all(callable(hook) for hook in hooks):
            raise RunError("injected mode requires all three injected hooks")
    elif any(hook is not None for hook in hooks):
        raise RunError("native mode forbids injected hooks")
    prepare = _prepare if prepare is None else prepare
    import_spice = _import_spice if import_spice is None else import_spice
    guard_spice = _guard_spice if guard_spice is None else guard_spice
    if profile["mode"] == "native" and any(
            name == "tudatpy" or name.startswith("tudatpy.") for name in sys.modules):
        raise RunError("cold native import required")
    used = 0
    with trace.open("xb") as stream:
        def emit(index: int) -> None:
            nonlocal last, used
            last = _check(deadline_s, last)
            data = _json_bytes(_marker(index, last - started_s, profile))
            if len(data) > MARKER_BYTES or used + len(data) > TRACE_BYTES:
                raise RunError("trace marker byte cap")
            stream.write(data)
            stream.flush()
            _sync(trace)
            used += len(data)
            last = _check(deadline_s, last)

        emit(0)
        budget = prepare(started_s)
        emit(1)
        emit(2)
        spice = import_spice()
        emit(3)
        guard_spice(budget, spice)
        emit(4)
        # Do not import the kernel again or access any native context/visitor.
        kernel = sys.modules.get("tudatpy.kernel")
        path = getattr(kernel, "__file__", None)
        if (type(path) is not str or path != profile["kernel_path"]
                or hashlib.sha256(Path(path).read_bytes()).hexdigest() != profile["kernel_sha256"]):
            raise RunError("loaded kernel path/hash identity mismatch")
        emit(5)
    _check(deadline_s, last)


def _worker_command(kind: str, source: Path, started_s: float, deadline_s: float) -> list[str]:
    if kind == "probe":
        return [sys.executable, "-m", "space_nav._import_probe", "--probe", str(source),
                repr(started_s), repr(deadline_s)]
    return [sys.executable, "-m", "space_nav._import_probe_audit", "--audit", str(source),
            str(source.parent / "observation.json"), str(source.parent / "trace.jsonl"), repr(deadline_s)]


def _retain_trace(directory: Path, evidence: _Evidence) -> bytes:
    trace = directory / "trace.jsonl"
    with trace.open("rb") as stream:
        raw = stream.read(TRACE_BYTES + 1)
    oversized = len(raw) > TRACE_BYTES
    if oversized:
        raw = raw[:TRACE_BYTES]
        with trace.open("r+b") as stream:
            stream.truncate(TRACE_BYTES)
    evidence.used[trace.name] = len(raw)
    evidence.structured += len(raw)
    if evidence.structured > EVIDENCE_BYTES - REPORT_BYTES:
        raise RunError("structured evidence byte cap")
    _sync(trace)
    if oversized:
        raise RunError("trace byte cap")
    return raw


def run(raw: bytes, directory: Path, *, started_s: float | None = None,
        inherited_group: bool = False) -> dict[str, object]:
    """Run one import-only child and independent audit in a fresh namespace.

    Artificial tests replace the probe command. No native run follows from this
    module's qualification; the external caller still owes admission/finalization.
    """
    entered = _now()
    started_s = _start(started_s, entered)
    last = _check(started_s + 60.0, entered)
    profile = _profile(raw)
    if inherited_group and (os.getpid() != os.getpgrp() or os.getpid() != os.getsid(0)):
        raise RunError("inherited workers require isolated supervised parent session")
    directory.mkdir(parents=False, exist_ok=False)
    evidence = _Evidence(directory, LOG_BYTES - 2048 if inherited_group else LOG_BYTES)
    evidence.caps.update({"producer.json": 0, "audit.json": REPORT_BYTES,
                          "observation.json": REPORT_BYTES})
    source = directory / "input.json"
    report: dict[str, Any] = {
        "schema": "ariadna-import-run-v1", "scope": "import-only", "mode": profile["mode"],
        "status": "failed", "failure": None, "physical_admission": "unavailable", "workers": [],
        "parent_started_s": started_s, "finalization": "pending-after-fsync-observation",
        "limits": {"total_s": 60, "producer_finish_s": 45, "audit_s": 10, "audit_finish_s": 55,
                   "finalization_reserve_s": 5, "input_bytes": INPUT_BYTES, "logs_bytes": LOG_BYTES,
                   "structured_evidence_bytes": EVIDENCE_BYTES, "trace_bytes": TRACE_BYTES,
                   "marker_bytes": MARKER_BYTES, "explicit_import_attempts": 1,
                   "explicit_owner_work": 0},
    }
    try:
        evidence.write(source, raw)
        _sync(source)
        output, errors = directory / "producer.json", directory / "producer.stderr.log"
        evidence.write(output, b"")
        evidence.write(errors, b"")
        last = _check(started_s + 45.0, last)
        worker = _watch_worker(_worker_command("probe", source, started_s, started_s + 45.0),
                               output, errors, started_s + 45.0, evidence,
                               inherited_group=inherited_group)
        report["workers"].append({"kind": "probe", **worker})
        last = _check(started_s + 45.0, last)
        producer_elapsed_s = last - started_s
        if worker["exit_code"] != 0:
            raise RunError("probe child failed; trace does not establish import completion")
        trace = _retain_trace(directory, evidence)
        last = _check(started_s + 45.0, last)
        observation = {
            "schema": "ariadna-import-observation-v1", "exit_code": worker["exit_code"],
            "producer_elapsed_s": producer_elapsed_s,
            "trace_sha256": hashlib.sha256(trace).hexdigest(), "probe_sha256": profile["probe_sha256"],
            "finalization": "checked-after-fsync", "finalized_elapsed_s": last - started_s,
        }
        evidence.write(directory / "observation.json", _json_bytes(observation))
        _sync(directory / "observation.json")
        last = _check(started_s + 45.0, last)
        cutoff = min(last + 10.0, started_s + 55.0)
        output, errors = directory / "audit.json", directory / "audit.stderr.log"
        evidence.write(output, b"")
        evidence.write(errors, b"")
        worker = _watch_worker(_worker_command("audit", source, started_s, cutoff),
                               output, errors, cutoff, evidence, inherited_group=inherited_group)
        report["workers"].append({"kind": "audit", **worker})
        last = _check(cutoff, last)
        audit = _read(output, AUDIT_BYTES)
        if (worker["exit_code"] != 0 or audit.get("schema") != "ariadna-import-audit-v1"
                or audit.get("status") != "passed" or audit.get("scope") != "import-only"
                or audit.get("mode") != profile["mode"] or type(audit.get("markers_checked")) is not int
                or audit["markers_checked"] != 6 or audit.get("kernel_sha256") != profile["kernel_sha256"]
                or audit.get("completion_requires_outer_finalization") is not True
                or audit.get("physical_admission") != "unavailable"):
            raise RunError("independent import audit failed or scope mismatch")
        report["status"] = "passed"
    except (RunError, OSError, ValueError, TypeError) as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"[:2048]
    if (directory / "trace.jsonl").exists() and "trace.jsonl" not in evidence.used:
        try:
            _retain_trace(directory, evidence)
        except (RunError, OSError, ValueError) as exc:
            report["status"] = "failed"
            report["failure"] = report["failure"] or f"{type(exc).__name__}: {exc}"[:2048]
    evidence.write(directory / "receipt.json", _json_bytes(report))
    try:
        for path in directory.iterdir():
            _sync(path)
            last = _check(started_s + 60.0, last)
    except (RunError, OSError, ValueError) as exc:
        report["status"] = "failed"
        report["failure"] = report["failure"] or f"{type(exc).__name__}: {exc}"[:2048]
        report["finalization"] = "failed-after-fsync"
    else:
        report["finalization"] = "checked-after-fsync"
    report["structured_bytes"] = evidence.structured
    report["log_bytes"] = evidence.logs
    report["elapsed_at_last_valid_check_s"] = last - started_s
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Private entry; external admission and caller watchdog remain mandatory."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 4 or args[0] not in {"--probe", "--parent"}:
        raise RunError("private import probe requires fixed input and inherited clock")
    try:
        source = Path(args[1])
        with source.open("rb") as stream:
            raw = stream.read(INPUT_BYTES + 1)
        if args[0] == "--probe":
            probe(raw, source.parent / "trace.jsonl", started_s=float(args[2]), deadline_s=float(args[3]))
            return 0
        report = run(raw, Path(args[2]), started_s=float(args[3]), inherited_group=True)
        sys.stdout.buffer.write(_json_bytes(report))
        return 0 if report["status"] == "passed" else 2
    except (RunError, OSError, ValueError, TypeError, RuntimeError) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {str(exc)[:1024]}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
