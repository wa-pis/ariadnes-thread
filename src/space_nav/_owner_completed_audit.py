"""Independent saved-only audit of ADR0281's single completed forward owner.

Passing synthetic words does not admit native execution, certify the original
full owner fixture, or establish a physical Moon-to-Mars trajectory.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from fractions import Fraction
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys
from time import monotonic
from typing import cast

from ._import_probe_audit import (
    ProbeAuditError, _decode, _digest, _mapping, _need, _number, _read,
    _install_guard as _install_prefix_guard,
)
from ._owner_endpoint_audit import OracleError, _metadata, _state, _word

CompletedAuditError = ProbeAuditError
_SCOPE = "single-forward-completed-owner-only"
_PHASES = ("bootstrap-ready", "import-ready", "context-ready", "factory-enter",
           "factory-return", "metadata-enter", "metadata-ready", "visitor-enter",
           "visitor-return", "complete")
_PROFILE = {"schema", "scope", "mode", "kernel_path", "kernel_sha256", "probe_sha256",
            "owner_fixture_sha256", "owner_auditor_sha256", "trajectory_sha256",
            "completed_auditor_sha256"}
_REPORT = {"schema", "scope", "mode", "status", "physical_admission", "kernel_path",
           "kernel_sha256", "probe_sha256", "completed_auditor_sha256", "provenance",
           "native_context", "arguments", "counts", "context_checks", "metadata_attempts",
           "metadata", "endpoint"}
_OBSERVATION = {"schema", "exit_code", "producer_elapsed_s", "trace_sha256",
                "report_sha256", "probe_sha256", "finalization", "finalized_elapsed_s"}
_MARKER = {"schema", "scope", "index", "phase", "elapsed_s"}
_COUNTS = {"factory_attempts": 1, "integration_attempts": 1, "visitor_calls": 1,
           "spice_queries": 0, "kernel_reads": 0, "real_archive_reads": 0,
           "optimizer_entries": 0}
_FORBIDDEN = ("space_nav._owner_completed_probe", "space_nav._owner_setup_probe",
              "space_nav._owner_setup_run", "space_nav.trajectory")


def _completed_state(report: dict[str, object]) -> None:
    """Check row meaning and an independent binary64-literal polynomial in SI."""
    try:
        _metadata(report["metadata"], "metadata")
        metadata = cast(dict[str, object], report["metadata"])
        _need(type(metadata["propagated_state_vector_length"]) is int,
              "metadata: state vector length must be integer7")
        endpoint = _mapping(report["endpoint"], {"hour", "remainder_hex", "state_hex"},
                            "endpoint")
        _need(type(endpoint["hour"]) is int and endpoint["hour"] == 0,
              "endpoint: integer hour0 required")
        _need(_word(endpoint["remainder_hex"], "endpoint.remainder_hex") == 1000.0,
              "endpoint: selected chronological-last epoch1000 required")
        actual = tuple(Fraction(x) for x in _state(endpoint["state_hex"], "endpoint.state_hex"))
    except OracleError as exc:
        raise CompletedAuditError(str(exc)) from exc
    # Independent literals, not the producer's reference or decimal acceleration.
    initial = tuple(Fraction(x) for x in (10000000.0, 0.0, 0.0, 0.0, 1000.0, 0.0, 2000.0))
    acceleration = (Fraction(0), Fraction(0.1), Fraction(0))
    seconds = 1000
    expected = tuple(initial[i] + initial[i + 3] * seconds
                     + acceleration[i] * seconds * seconds / 2 for i in range(3))
    expected += tuple(initial[i + 3] + acceleration[i] * seconds for i in range(3))
    expected += (initial[6],)
    _need(sum((actual[i] - expected[i]) ** 2 for i in range(3)) <= Fraction(1, 1000) ** 2,
          "position norm exceeds0.001m")
    _need(sum((actual[i] - expected[i]) ** 2 for i in range(3, 6)) <= Fraction(1, 1000000) ** 2,
          "velocity norm exceeds1e-6m/s")
    _need(abs(actual[6] - expected[6]) <= Fraction(1, 1000000000), "mass exceeds1e-9kg")


def audit(trace_raw: bytes, profile: object, report_raw: bytes, observation: object, *,
          deadline_s: float, clock: Callable[[], float] = monotonic) -> dict[str, object]:
    """Validate ten markers and fixed synthetic final words without a producer.

    Elapsed seconds refer to the inherited parent clock. Source/kernel claims
    and cleanup still require a separately admitted outer continuation.
    """
    deadline = _number(deadline_s, "audit deadline_s")
    previous_clock = _number(clock(), "audit clock")
    _need(previous_clock < deadline, "audit deadline exhausted")

    def check() -> None:
        nonlocal previous_clock
        now = _number(clock(), "audit clock")
        _need(previous_clock <= now < deadline, "audit clock reversed or deadline exhausted")
        previous_clock = now

    p = _mapping(profile, _PROFILE, "profile")
    _need(p["schema"] == "ariadna-owner-completed-input-v1" and p["scope"] == _SCOPE,
          "profile: fixed completed schema/scope required")
    _need(type(p["mode"]) is str and p["mode"] in ("native", "injected"),
          "profile.mode: injected or native required")
    path = p["kernel_path"]
    _need(type(path) is str and "\0" not in cast(str, path)
          and Path(cast(str, path)).is_absolute(), "profile.kernel_path: absolute without NUL required")
    pins = {name: _digest(p[name], "profile." + name)
            for name in _PROFILE if name.endswith("_sha256")}
    check()
    _need(type(report_raw) is bytes and 0 < len(report_raw) <= 65536,
          "report: nonempty <=65536bytes required")
    report_sha = sha256(report_raw).hexdigest()
    report = _mapping(_decode(report_raw), _REPORT, "report")
    _need(report["schema"] == "ariadna-owner-completed-report-v1"
          and report["scope"] == _SCOPE and report["status"] == "passed"
          and report["physical_admission"] == "unavailable", "report: fixed successful scope required")
    _need(type(report["mode"]) is str and report["mode"] == p["mode"], "report.mode differs")
    _need(type(report["kernel_path"]) is str and report["kernel_path"] == path,
          "report.kernel_path differs")
    for name in ("kernel_sha256", "probe_sha256", "completed_auditor_sha256"):
        _need(_digest(report[name], "report." + name) == pins[name], "report identity differs: " + name)
    provenance = _mapping(report["provenance"],
                          {"producer_sha256", "auditor_sha256", "trajectory_sha256"}, "provenance")
    for name, pin in (("producer_sha256", "owner_fixture_sha256"),
                      ("auditor_sha256", "owner_auditor_sha256"),
                      ("trajectory_sha256", "trajectory_sha256")):
        _need(_digest(provenance[name], "provenance." + name) == pins[pin],
              "provenance identity differs: " + name)
    context = report["native_context"]
    _need(type(context) is list and len(context) == 3
          and all(type(v) is int for v in context) and context == [53, 53, 8],
          "native_context: exact integer list [53,53,8] required")
    for field in ("context_checks", "metadata_attempts"):
        _need(type(report[field]) is int and report[field] == 1, field + ": exactly one required")
    arguments = _mapping(report["arguments"], {"arc_id", "simulate", "selector", "schema"},
                         "arguments")
    _need(arguments["arc_id"] == "forward" and arguments["simulate"] is True
          and arguments["selector"] is True
          and arguments["schema"] == "cartesian-position-m_velocity-m-s_mass-kg",
          "arguments: fixed forward/True/True/schema required")
    counts = _mapping(report["counts"], set(_COUNTS) | {
        "acceleration_callbacks", "native_reported_function_evaluations"}, "counts")
    for field, expected in _COUNTS.items():
        _need(type(counts[field]) is int and counts[field] == expected, "strict completed count: " + field)
    callbacks = counts["acceleration_callbacks"]
    _need(type(callbacks) is int and 0 <= callbacks <= 100000, "acceleration_callbacks: integer0..100000")
    native = counts["native_reported_function_evaluations"]
    _need(type(native) is list and len(native) == 1 and type(native[0]) is int and native[0] >= 0,
          "native function counts: one nonnegative integer required")
    _completed_state(report)
    check()
    o = _mapping(observation, _OBSERVATION, "observation")
    _need(o["schema"] == "ariadna-owner-completed-observation-v1", "observation.schema differs")
    _need(type(o["exit_code"]) is int and o["exit_code"] == 0, "childexit0 required")
    _need(o["finalization"] == "checked-after-fsync", "durable child observation required")
    finished = _number(o["producer_elapsed_s"], "producer_elapsed_s")
    finalized = _number(o["finalized_elapsed_s"], "finalized_elapsed_s")
    _need(0 <= finished <= finalized < 45, "observation outside producer45s phase")
    _need(_digest(o["probe_sha256"], "observation.probe_sha256") == pins["probe_sha256"],
          "observation probe identity differs")
    _need(_digest(o["report_sha256"], "observation.report_sha256") == report_sha, "report hash differs")
    _need(type(trace_raw) is bytes and 0 < len(trace_raw) <= 4096, "trace: nonempty <=4096bytes required")
    _need(_digest(o["trace_sha256"], "observation.trace_sha256") == sha256(trace_raw).hexdigest(),
          "trace hash differs")
    _need(trace_raw.endswith(b"\n"), "trace: truncated final marker")
    lines = trace_raw.splitlines(keepends=True)
    _need(len(lines) == 10, "trace: ten complete markers required")
    previous_elapsed = 0.0
    for index, (phase, line) in enumerate(zip(_PHASES, lines, strict=True)):
        check()
        _need(len(line) <= 512 and line.endswith(b"\n"), "marker: <=512newline bytes required")
        marker = _mapping(_decode(line), _MARKER | ({"report_sha256"} if index == 9 else set()), "marker")
        _need(marker["schema"] == "ariadna-owner-completed-marker-v1" and marker["scope"] == _SCOPE,
              "marker schema/scope differs")
        _need(type(marker["index"]) is int and marker["index"] == index and marker["phase"] == phase,
              "marker phase order differs")
        elapsed = _number(marker["elapsed_s"], "marker.elapsed_s")
        _need(previous_elapsed <= elapsed <= finished, "marker clock reversed or beyond child")
        previous_elapsed = elapsed
        if index == 9:
            _need(_digest(marker["report_sha256"], "marker.report_sha256") == report_sha,
                  "complete report identity differs")
    check()
    return {"schema": "ariadna-owner-completed-audit-v1", "status": "passed", "scope": _SCOPE,
            "physical_admission": "unavailable", "mode": p["mode"], "markers_checked": 10,
            "kernel_sha256": pins["kernel_sha256"], "report_sha256": report_sha,
            "completion_requires_outer_finalization": True}


def _install_guard() -> None:
    if any(name == prefix or name.startswith(prefix + ".")
           for name in sys.modules for prefix in _FORBIDDEN):
        raise CompletedAuditError("independent auditor already loaded completed producer/runtime")
    _install_prefix_guard()

    class NoCompletedProducer(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
            if any(fullname == prefix or fullname.startswith(prefix + ".") for prefix in _FORBIDDEN):
                raise ImportError("independent auditor forbids " + fullname)

    sys.meta_path.insert(0, NoCompletedProducer())


def main(argv: Sequence[str] | None = None) -> int:
    """Read bounded saved files only; future native admission is external."""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        _need(len(args) == 6 and args[0] == "--audit",
              "private audit requires profile/report/observation/trace/deadline")
        _install_guard()
        result = audit(_read(args[4], 4096), _decode(_read(args[1], 65536)),
                       _read(args[2], 65536), _decode(_read(args[3], 65536)),
                       deadline_s=float(args[5]))
        sys.stdout.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
        return 0
    except (CompletedAuditError, OSError, ValueError, TypeError) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {str(exc)[:1024]}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
