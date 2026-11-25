"""Private ADR0273 never-run setup observation; F18.9 needs separate authority.

Artificial qualification never creates a native owner. External admission and a
same-clock caller watchdog remain mandatory for any later native observation.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import hashlib
import math
import os
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, Any

from ._import_probe import _guard_spice, _import_spice, _prepare, _retain_trace, _start
from ._owner_endpoint_run import (
    AUDIT_BYTES, EVIDENCE_BYTES, INPUT_BYTES, LOG_BYTES, REPORT_BYTES, RunError,
    _Evidence, _decode, _json_bytes, _now, _read, _sync, _watch_worker,
)

if TYPE_CHECKING:
    from ._owner_endpoint_fixture import Budget


TRACE_BYTES = 4096
MARKER_BYTES = 512
_SCOPE = "never-run-owner-setup-only"
_PHASES = ("bootstrap-ready", "import-ready", "context-ready", "factory-enter",
           "factory-return", "visitor-enter", "visitor-refused", "complete")
_SCHEMA = "cartesian-position-m_velocity-m-s_mass-kg"
_UNAVAILABLE = "completed original results unavailable"
_PROFILE_KEYS = {"schema", "scope", "mode", "kernel_path", "kernel_sha256", "probe_sha256",
                 "owner_fixture_sha256", "owner_auditor_sha256", "trajectory_sha256",
                 "setup_auditor_sha256"}


def _check(deadline_s: float, minimum_s: float) -> float:
    now = _now()
    if now < minimum_s:
        raise RunError("monotonic clock moved backwards")
    if now >= deadline_s:
        raise RunError("absolute deadline exhausted")
    return now


def _profile(raw: bytes) -> dict[str, Any]:
    profile = _decode(raw, INPUT_BYTES)
    if (set(profile) != _PROFILE_KEYS or profile["schema"] != "ariadna-owner-setup-input-v1"
            or profile["scope"] != _SCOPE or type(profile["mode"]) is not str
            or profile["mode"] not in ("native", "injected")):
        raise RunError("fixed owner-setup profile mismatch")
    for field in _PROFILE_KEYS - {"schema", "scope", "mode", "kernel_path"}:
        if type(profile[field]) is not str or re.fullmatch(r"[0-9a-f]{64}", profile[field]) is None:
            raise RunError(field + ": lowercase SHA256 required")
    path = profile["kernel_path"]
    if type(path) is not str or not Path(path).is_absolute() or "\0" in path:
        raise RunError("kernel_path: absolute path without NUL required")
    files = {"probe_sha256": Path(__file__).name,
             "owner_fixture_sha256": "_owner_endpoint_fixture.py",
             "owner_auditor_sha256": "_owner_endpoint_audit.py",
             "trajectory_sha256": "trajectory.py",
             "setup_auditor_sha256": "_owner_setup_audit.py"}
    for field, name in files.items():
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != profile[field]:
            raise RunError(field + ": source identity mismatch")
    return profile


def _context() -> object:
    from ._owner_endpoint_fixture import _native_context
    return _native_context()


def _provenance() -> object:
    from ._owner_endpoint_fixture import _provenance as native_provenance
    return native_provenance()


def _factory(arc_id: str, simulate: bool, budget: Budget) -> object:
    from ._owner_endpoint_fixture import _native_factory
    return _native_factory(arc_id, simulate, budget)


def _counts(budget: Budget, factory: int, visitor: int) -> dict[str, object]:
    """Enforce the small scope, beyond the reused Budget's wider old maxima."""
    budget.check()
    counts = budget.snapshot()
    fixed = {"factory_attempts": factory, "integration_attempts": 0,
             "visitor_calls": visitor, "spice_queries": 0, "kernel_reads": 0,
             "real_archive_reads": 0, "optimizer_entries": 0}
    if type(counts) is not dict or set(counts) != set(fixed) | {
            "acceleration_callbacks", "native_reported_function_evaluations"}:
        raise RunError("setup counts: fixed fields required")
    for field, value in fixed.items():
        if type(counts[field]) is not int or counts[field] != value:
            raise RunError("setup counts: strict1/0/1 scope: " + field)
    callbacks = counts["acceleration_callbacks"]
    if type(callbacks) is not int or not 0 <= callbacks <= 100000:
        raise RunError("setup counts: acceleration callback cap100000")
    if type(counts["native_reported_function_evaluations"]) is not list or counts[
            "native_reported_function_evaluations"]:
        raise RunError("setup counts: no integrated function report")
    return counts


def probe(raw: bytes, trace: Path, *, started_s: float, deadline_s: float,
          prepare: Callable[[float], object] | None = None,
          import_spice: Callable[[], object] | None = None,
          guard_spice: Callable[[object, object], None] | None = None,
          context: Callable[[], object] | None = None,
          provenance: Callable[[], object] | None = None,
          factory: Callable[[str, bool, Budget], object] | None = None) -> dict[str, object]:
    """Observe exactly one never-run owner/refusal; injected evidence stays labelled."""
    from ._owner_endpoint_fixture import Budget
    entered = _now()
    started_s = _start(started_s, entered)
    if (type(deadline_s) not in (int, float) or not math.isfinite(deadline_s)
            or deadline_s > started_s + 45.0):
        raise RunError("producer deadline exceeds fixed phase")
    last = _check(deadline_s, entered)
    profile = _profile(raw)
    hooks = (prepare, import_spice, guard_spice, context, provenance, factory)
    if profile["mode"] == "injected":
        if not all(callable(hook) for hook in hooks):
            raise RunError("injected mode requires all six injected hooks")
    elif any(hook is not None for hook in hooks):
        raise RunError("native mode forbids injected hooks")
    if profile["mode"] == "native" and any(
            name == "tudatpy" or name.startswith("tudatpy.") for name in sys.modules):
        raise RunError("cold native import required")
    prepare = _prepare if prepare is None else prepare
    import_spice = _import_spice if import_spice is None else import_spice
    guard_spice = _guard_spice if guard_spice is None else guard_spice
    context = _context if context is None else context
    provenance = _provenance if provenance is None else provenance
    factory = _factory if factory is None else factory
    used = 0
    with trace.open("xb") as stream:
        def emit(index: int, report_sha256: str | None = None) -> None:
            nonlocal last, used
            last = _check(deadline_s, last)
            record: dict[str, object] = {
                "schema": "ariadna-owner-setup-marker-v1", "scope": _SCOPE,
                "index": index, "phase": _PHASES[index], "elapsed_s": last - started_s,
            }
            if report_sha256 is not None:
                record["report_sha256"] = report_sha256
            data = _json_bytes(record)
            if len(data) > MARKER_BYTES or used + len(data) > TRACE_BYTES:
                raise RunError("trace marker byte cap")
            stream.write(data)
            stream.flush()
            _sync(trace)
            used += len(data)
            last = _check(deadline_s, last)

        emit(0)
        budget = prepare(started_s)
        if not isinstance(budget, Budget) or budget.started_s != started_s:
            raise RunError("setup requires the original-start Budget")
        _counts(budget, 0, 0)
        spice = import_spice()
        guard_spice(budget, spice)
        kernel = sys.modules.get("tudatpy.kernel")
        path = getattr(kernel, "__file__", None)
        if (type(path) is not str or path != profile["kernel_path"]
                or hashlib.sha256(Path(path).read_bytes()).hexdigest() != profile["kernel_sha256"]):
            raise RunError("loaded kernel path/hash identity mismatch")
        _counts(budget, 0, 0)
        emit(1)
        source_provenance = provenance()
        expected_provenance = {"producer_sha256": profile["owner_fixture_sha256"],
                               "auditor_sha256": profile["owner_auditor_sha256"],
                               "trajectory_sha256": profile["trajectory_sha256"]}
        if type(source_provenance) is not dict or source_provenance != expected_provenance:
            raise RunError("owner source provenance mismatch")
        native_context = context()
        if (type(native_context) is not list or native_context != [53, 53, 8]
                or any(type(v) is not int for v in native_context)):
            raise RunError("native context: exact helper list required")
        _counts(budget, 0, 0)
        emit(2)
        # Check the narrower scope both before precharge and before native entry.
        _counts(budget, 0, 0)
        budget.charge_factory(False)
        _counts(budget, 1, 0)
        emit(3)
        owner = factory("never-run", False, budget)
        method = getattr(owner, "_ariadna_original_endpoint", None)
        if not callable(method):
            raise RunError("never-run owner method unavailable")
        _counts(budget, 1, 0)
        emit(4)
        budget.charge_visitor()
        _counts(budget, 1, 1)
        emit(5)
        try:
            method(True, _SCHEMA)
        except Exception as exc:  # Exact untyped native/injected method boundary.
            if type(exc) is not RuntimeError or str(exc) != _UNAVAILABLE:
                raise RunError("unexpected never-run visitor refusal") from exc
        else:
            raise RunError("never-run visitor unexpectedly returned an endpoint")
        counts = _counts(budget, 1, 1)
        emit(6)
        report: dict[str, object] = {
            "schema": "ariadna-owner-setup-report-v1", "scope": _SCOPE,
            "mode": profile["mode"], "status": "passed", "physical_admission": "unavailable",
            "kernel_path": profile["kernel_path"], "kernel_sha256": profile["kernel_sha256"],
            "probe_sha256": profile["probe_sha256"],
            "setup_auditor_sha256": profile["setup_auditor_sha256"],
            "provenance": source_provenance, "native_context": native_context,
            "arguments": {"arc_id": "never-run", "simulate": False, "selector": True,
                          "schema": _SCHEMA},
            "refusal": {"type": "RuntimeError", "message": _UNAVAILABLE},
            "counts": counts, "context_checks": 1,
        }
        encoded = _json_bytes(report)
        if len(encoded) > REPORT_BYTES:
            raise RunError("producer report byte partition")
        emit(7, hashlib.sha256(encoded).hexdigest())
    _check(deadline_s, last)
    return report


def _worker_command(kind: str, source: Path, started_s: float, deadline_s: float) -> list[str]:
    if kind == "probe":
        return [sys.executable, "-m", "space_nav._owner_setup_probe", "--probe", str(source),
                repr(started_s), repr(deadline_s)]
    return [sys.executable, "-m", "space_nav._owner_setup_audit", "--audit", str(source),
            str(source.parent / "producer.json"), str(source.parent / "observation.json"),
            str(source.parent / "trace.jsonl"), repr(deadline_s)]


def run(raw: bytes, directory: Path, *, started_s: float | None = None,
        inherited_group: bool = False) -> dict[str, object]:
    """Run one never-run setup child and independent audit in a fresh namespace.

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
    evidence.caps.update({"producer.json": REPORT_BYTES, "audit.json": REPORT_BYTES,
                          "observation.json": REPORT_BYTES})
    source = directory / "input.json"
    report: dict[str, Any] = {
        "schema": "ariadna-owner-setup-run-v1", "scope": _SCOPE, "mode": profile["mode"],
        "status": "failed", "failure": None, "physical_admission": "unavailable", "workers": [],
        "parent_started_s": started_s, "finalization": "pending-after-fsync-observation",
        "limits": {"total_s": 60, "producer_finish_s": 45, "audit_s": 10, "audit_finish_s": 55,
                   "finalization_reserve_s": 5, "input_bytes": INPUT_BYTES, "logs_bytes": LOG_BYTES,
                   "structured_evidence_bytes": EVIDENCE_BYTES, "trace_bytes": TRACE_BYTES,
                   "marker_bytes": MARKER_BYTES, "cold_prefix_attempts": 1, "context_checks": 1,
                   "factory_attempts": 1, "integration_attempts": 0, "visitor_calls": 1},
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
            raise RunError("probe child failed; trace does not establish setup completion")
        producer_raw = (directory / "producer.json").read_bytes()
        producer = _decode(producer_raw, REPORT_BYTES)
        if (producer.get("schema") != "ariadna-owner-setup-report-v1"
                or producer.get("status") != "passed" or producer.get("scope") != _SCOPE
                or producer.get("mode") != profile["mode"]):
            raise RunError("setup producer report mismatch")
        trace = _retain_trace(directory, evidence)
        _sync(directory / "producer.json")
        last = _check(started_s + 45.0, last)
        observation = {
            "schema": "ariadna-owner-setup-observation-v1", "exit_code": worker["exit_code"],
            "producer_elapsed_s": producer_elapsed_s,
            "trace_sha256": hashlib.sha256(trace).hexdigest(),
            "report_sha256": hashlib.sha256(producer_raw).hexdigest(),
            "probe_sha256": profile["probe_sha256"],
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
        if (worker["exit_code"] != 0 or audit.get("schema") != "ariadna-owner-setup-audit-v1"
                or audit.get("status") != "passed" or audit.get("scope") != _SCOPE
                or audit.get("mode") != profile["mode"] or type(audit.get("markers_checked")) is not int
                or audit["markers_checked"] != 8 or audit.get("kernel_sha256") != profile["kernel_sha256"]
                or audit.get("report_sha256") != hashlib.sha256(producer_raw).hexdigest()
                or audit.get("completion_requires_outer_finalization") is not True
                or audit.get("physical_admission") != "unavailable"):
            raise RunError("independent setup audit failed or scope mismatch")
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


def _parent_command(source: Path, directory: Path, started_s: float) -> list[str]:
    return [sys.executable, "-B", "-m", "space_nav._owner_setup_probe", "--parent",
            str(source), str(directory), repr(started_s)]


def run_isolated(raw: bytes, directory: Path, *, started_s: float | None = None) -> dict[str, object]:
    """Supervise the cold parent and all inherited worker descendants once.

    Opaque supervisor I/O still requires caller supervision. Native work is
    stopped before the supervisor records its own final receipt, even on failure.
    """
    entered = _now()
    profile = _profile(raw)
    if started_s is None:
        started_s = entered
    if (type(started_s) not in (int, float) or not math.isfinite(started_s)
            or started_s > entered):
        raise RunError("parent start must be finite past monotonic time")
    started_s = float(started_s)
    last = _check(started_s + 60.0, entered)
    directory.mkdir(parents=False, exist_ok=False)
    evidence = _Evidence(directory, 2048)
    evidence.caps["producer.json"] = REPORT_BYTES
    source, output, errors = (directory / n for n in
                              ("input.json", "producer.json", "producer.stderr.log"))
    report: dict[str, Any] = {"schema": "ariadna-owner-setup-supervisor-v1", "status": "failed",
                              "failure": None, "parent": None,
                              "physical_admission": "unavailable",
                              "finalization": "pending-after-fsync-observation"}
    try:
        evidence.write(source, raw)
        _sync(source)
        last = _check(started_s + 60.0, last)
        evidence.write(output, b"")
        evidence.write(errors, b"")
        worker = _watch_worker(_parent_command(source, directory / "packet", started_s),
                               output, errors, started_s + 60.0, evidence)
        # The entire parent/worker group is gone before any supervisor recording.
        report["worker"] = worker
        last = _check(started_s + 60.0, last)
        parent = _read(output, REPORT_BYTES)
        report["parent"] = parent
        if (worker["exit_code"] != 0 or parent.get("schema") != "ariadna-owner-setup-run-v1"
                or parent.get("scope") != _SCOPE or parent.get("mode") != profile["mode"]
                or parent.get("status") != "passed"
                or parent.get("finalization") != "checked-after-fsync"
                or parent.get("physical_admission") != "unavailable"):
            raise RunError("cold parent failed/unfinalized")
        report["status"] = "passed"
    except (RunError, OSError, ValueError, TypeError) as exc:
        report["failure"] = f"{type(exc).__name__}: {exc}"[:2048]
    evidence.write(directory / "receipt.json", _json_bytes(report))
    try:
        for path in directory.iterdir():
            if path.is_file():
                _sync(path)
                last = _check(started_s + 60.0, last)
    except (RunError, OSError, ValueError) as exc:
        report["status"] = "failed"
        report["failure"] = report["failure"] or f"{type(exc).__name__}: {exc}"[:2048]
        report["finalization"] = "failed-after-fsync"
    else:
        report["finalization"] = "checked-after-fsync"
    report["elapsed_at_last_valid_check_s"] = last - started_s
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Private entry; external admission and caller watchdog remain mandatory."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 4 or args[0] not in {"--probe", "--parent"}:
        raise RunError("private owner setup requires fixed input and inherited clock")
    try:
        source = Path(args[1])
        with source.open("rb") as stream:
            raw = stream.read(INPUT_BYTES + 1)
        if args[0] == "--probe":
            report = probe(raw, source.parent / "trace.jsonl",
                           started_s=float(args[2]), deadline_s=float(args[3]))
            sys.stdout.buffer.write(_json_bytes(report))
            return 0
        report = run(raw, Path(args[2]), started_s=float(args[3]), inherited_group=True)
        sys.stdout.buffer.write(_json_bytes(report))
        return 0 if report["status"] == "passed" else 2
    except (RunError, OSError, ValueError, TypeError, RuntimeError) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {str(exc)[:1024]}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
