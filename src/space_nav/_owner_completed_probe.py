"""Private ADR0281 single-forward observation; native execution needs admission.

Artificial owners qualify plumbing only. A separately qualified external caller
must supervise the original clock, children, evidence and outer finalization.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import hashlib
import math
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, Any

from ._import_probe import _check, _guard_spice, _import_spice, _prepare, _start
from ._owner_endpoint_run import (
    INPUT_BYTES, REPORT_BYTES, RunError, _decode, _json_bytes, _now, _sync,
)

if TYPE_CHECKING:
    from ._owner_endpoint_fixture import Budget

TRACE_BYTES = 4096
MARKER_BYTES = 512
_SCOPE = "single-forward-completed-owner-only"
_SCHEMA = "cartesian-position-m_velocity-m-s_mass-kg"
_PHASES = ("bootstrap-ready", "import-ready", "context-ready", "factory-enter",
           "factory-return", "metadata-enter", "metadata-ready", "visitor-enter",
           "visitor-return", "complete")
_PROFILE_KEYS = {"schema", "scope", "mode", "kernel_path", "kernel_sha256", "probe_sha256",
                 "owner_fixture_sha256", "owner_auditor_sha256", "trajectory_sha256",
                 "completed_auditor_sha256"}


def _profile(raw: bytes) -> dict[str, Any]:
    profile = _decode(raw, INPUT_BYTES)
    if (set(profile) != _PROFILE_KEYS or profile["schema"] != "ariadna-owner-completed-input-v1"
            or profile["scope"] != _SCOPE or type(profile["mode"]) is not str
            or profile["mode"] not in ("native", "injected")):
        raise RunError("fixed completed-owner profile mismatch")
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
             "completed_auditor_sha256": "_owner_completed_audit.py"}
    for field, name in files.items():
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != profile[field]:
            raise RunError(field + ": source identity mismatch")
    return profile


def _counts(budget: Budget, factory: int, visitor: int,
            reported: int | None = None) -> dict[str, object]:
    """Enforce one arc/readback rather than the reused Budget's wider maxima."""
    budget.check()
    counts = budget.snapshot()
    fixed = {"factory_attempts": factory, "integration_attempts": factory,
             "visitor_calls": visitor, "spice_queries": 0, "kernel_reads": 0,
             "real_archive_reads": 0, "optimizer_entries": 0}
    if type(counts) is not dict or set(counts) != set(fixed) | {
            "acceleration_callbacks", "native_reported_function_evaluations"}:
        raise RunError("completed counts: fixed fields required")
    for field, value in fixed.items():
        if type(counts[field]) is not int or counts[field] != value:
            raise RunError("completed counts: strict1/1/1 scope: " + field)
    callbacks = counts["acceleration_callbacks"]
    if type(callbacks) is not int or not 0 <= callbacks <= 100000:
        raise RunError("completed counts: acceleration callback cap100000")
    if type(counts["native_reported_function_evaluations"]) is not list or counts[
            "native_reported_function_evaluations"]:
        raise RunError("completed counts: unexpected original Budget telemetry")
    if reported is not None:
        if type(reported) is not int or reported < 0:
            raise RunError("completed counts: nonnegative function report required")
        counts["native_reported_function_evaluations"] = [reported]
    return counts


def probe(raw: bytes, trace: Path, *, started_s: float, deadline_s: float,
          prepare: Callable[[float], object] | None = None,
          import_spice: Callable[[], object] | None = None,
          guard_spice: Callable[[object, object], None] | None = None,
          context: Callable[[], object] | None = None,
          provenance: Callable[[], object] | None = None,
          factory: Callable[[str, bool, Budget], object] | None = None) -> dict[str, object]:
    """Observe original forward completion and one endpoint; units SI, time elapsed s."""
    from ._owner_endpoint_fixture import (
        Budget, _endpoint, _metadata, _native_context, _native_factory,
        _provenance as fixture_provenance,
    )
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
    context = _native_context if context is None else context
    provenance = fixture_provenance if provenance is None else provenance
    factory = _native_factory if factory is None else factory
    used = 0
    with trace.open("xb") as stream:
        def emit(index: int, report_sha256: str | None = None) -> None:
            nonlocal last, used
            last = _check(deadline_s, last)
            record: dict[str, object] = {
                "schema": "ariadna-owner-completed-marker-v1", "scope": _SCOPE,
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
            raise RunError("completed probe requires the original-start Budget")
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
        expected = {"producer_sha256": profile["owner_fixture_sha256"],
                    "auditor_sha256": profile["owner_auditor_sha256"],
                    "trajectory_sha256": profile["trajectory_sha256"]}
        if type(source_provenance) is not dict or source_provenance != expected:
            raise RunError("owner source provenance mismatch")
        _counts(budget, 0, 0)
        native_context = context()
        if (type(native_context) is not list or native_context != [53, 53, 8]
                or any(type(v) is not int for v in native_context)):
            raise RunError("native context: exact helper list required")
        _counts(budget, 0, 0)
        emit(2)
        _counts(budget, 0, 0)
        budget.charge_factory(True)
        emit(3)
        _counts(budget, 1, 0)
        owner = factory("forward", True, budget)
        _counts(budget, 1, 0)
        emit(4)
        metadata_attempts = 1
        emit(5)
        _counts(budget, 1, 0)
        metadata, reported = _metadata(owner)
        _counts(budget, 1, 0, reported)
        emit(6)
        _counts(budget, 1, 0, reported)
        budget.charge_visitor()
        emit(7)
        _counts(budget, 1, 1, reported)
        method = getattr(owner, "_ariadna_original_endpoint", None)
        if not callable(method):
            raise RunError("completed owner method unavailable")
        _counts(budget, 1, 1, reported)
        endpoint = _endpoint(method(True, _SCHEMA))
        if endpoint["remainder_hex"] != (1000.0).hex():
            raise RunError("selectorTrue requires chronological-last epoch1000")
        counts = _counts(budget, 1, 1, reported)
        emit(8)
        report: dict[str, object] = {
            "schema": "ariadna-owner-completed-report-v1", "scope": _SCOPE,
            "mode": profile["mode"], "status": "passed", "physical_admission": "unavailable",
            "kernel_path": profile["kernel_path"], "kernel_sha256": profile["kernel_sha256"],
            "probe_sha256": profile["probe_sha256"],
            "completed_auditor_sha256": profile["completed_auditor_sha256"],
            "provenance": source_provenance, "native_context": native_context,
            "arguments": {"arc_id": "forward", "simulate": True, "selector": True,
                          "schema": _SCHEMA},
            "metadata": metadata, "endpoint": endpoint, "counts": counts,
            "context_checks": 1, "metadata_attempts": metadata_attempts,
        }
        encoded = _json_bytes(report)
        if len(encoded) > REPORT_BYTES:
            raise RunError("producer report byte partition")
        emit(9, hashlib.sha256(encoded).hexdigest())
    _check(deadline_s, last)
    if _counts(budget, 1, 1, reported) != counts:
        raise RunError("completed counts changed during final marker recording")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Private producer only; separate caller admission/watchdog are mandatory."""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(args) != 4 or args[0] != "--probe":
            raise RunError("private completed probe requires input and inherited clock")
        source = Path(args[1])
        with source.open("rb") as stream:
            raw = stream.read(INPUT_BYTES + 1)
        report = probe(raw, source.parent / "trace.jsonl",
                       started_s=float(args[2]), deadline_s=float(args[3]))
        sys.stdout.buffer.write(_json_bytes(report))
        return 0
    except (RunError, OSError, ValueError, TypeError, RuntimeError, AttributeError) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {str(exc)[:1024]}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
