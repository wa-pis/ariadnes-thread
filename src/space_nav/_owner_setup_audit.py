"""Independent stdlib audit of ADR0273's saved never-run setup observation.

Acceptance is conditional on external runtime admission and observed outer
cleanup/finalization; a trace cannot establish a prior timeout's cause.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys
from time import monotonic

from ._import_probe_audit import (
    ProbeAuditError,
    _decode,
    _digest,
    _mapping,
    _need,
    _number,
    _read,
    _install_guard as _install_prefix_guard,
)

SetupAuditError = ProbeAuditError
_SCOPE = "never-run-owner-setup-only"
_PHASES = (
    "bootstrap-ready",
    "import-ready",
    "context-ready",
    "factory-enter",
    "factory-return",
    "visitor-enter",
    "visitor-refused",
    "complete",
)
_PROFILE = {
    "schema",
    "scope",
    "mode",
    "kernel_path",
    "kernel_sha256",
    "probe_sha256",
    "owner_fixture_sha256",
    "owner_auditor_sha256",
    "trajectory_sha256",
    "setup_auditor_sha256",
}
_REPORT = {
    "schema",
    "scope",
    "mode",
    "status",
    "physical_admission",
    "kernel_path",
    "kernel_sha256",
    "probe_sha256",
    "setup_auditor_sha256",
    "provenance",
    "native_context",
    "arguments",
    "refusal",
    "counts",
    "context_checks",
}
_OBSERVATION = {
    "schema",
    "exit_code",
    "producer_elapsed_s",
    "trace_sha256",
    "report_sha256",
    "probe_sha256",
    "finalization",
    "finalized_elapsed_s",
}
_MARKER = {"schema", "scope", "index", "phase", "elapsed_s"}
_COUNTS = {
    "factory_attempts": 1,
    "integration_attempts": 0,
    "visitor_calls": 1,
    "spice_queries": 0,
    "kernel_reads": 0,
    "real_archive_reads": 0,
    "optimizer_entries": 0,
}
_FORBIDDEN = ("space_nav._owner_setup_probe", "space_nav._owner_setup_run")


def audit(
    trace_raw: bytes,
    profile: object,
    report_raw: bytes,
    observation: object,
    *,
    deadline_s: float,
    clock: Callable[[], float] = monotonic,
) -> dict[str, object]:
    """Validate eight saved markers and a literal report; execute no producer.

    Times are elapsed seconds from the admitted inherited parent start. All
    source/kernel identity claims still require complete independent admission.
    """
    deadline = _number(deadline_s, "audit deadline_s")
    previous_clock = _number(clock(), "audit clock")
    _need(previous_clock < deadline, "audit deadline exhausted")

    def check() -> None:
        nonlocal previous_clock
        now = _number(clock(), "audit clock")
        _need(
            previous_clock <= now < deadline,
            "audit clock reversed or deadline exhausted",
        )
        previous_clock = now

    p = _mapping(profile, _PROFILE, "profile")
    _need(
        p["schema"] == "ariadna-owner-setup-input-v1" and p["scope"] == _SCOPE,
        "profile: fixed setup schema/scope required",
    )
    _need(
        type(p["mode"]) is str and p["mode"] in ("native", "injected"),
        "profile.mode: injected or native required",
    )
    _need(
        type(p["kernel_path"]) is str
        and "\0" not in p["kernel_path"]
        and Path(p["kernel_path"]).is_absolute(),
        "profile.kernel_path: absolute without NUL required",
    )
    pins = {
        name: _digest(p[name], "profile." + name)
        for name in _PROFILE
        if name.endswith("_sha256")
    }
    check()
    _need(
        type(report_raw) is bytes and 0 < len(report_raw) <= 65536,
        "report: nonempty <=65536bytes required",
    )
    report_sha = sha256(report_raw).hexdigest()
    report = _mapping(_decode(report_raw), _REPORT, "report")
    _need(
        report["schema"] == "ariadna-owner-setup-report-v1"
        and report["scope"] == _SCOPE
        and report["status"] == "passed"
        and report["physical_admission"] == "unavailable",
        "report: successful fixed setup scope required",
    )
    _need(
        type(report["mode"]) is str and report["mode"] == p["mode"],
        "report.mode differs",
    )
    _need(
        type(report["kernel_path"]) is str
        and report["kernel_path"] == p["kernel_path"],
        "report.kernel_path differs",
    )
    for name in ("kernel_sha256", "probe_sha256", "setup_auditor_sha256"):
        _need(
            _digest(report[name], "report." + name) == pins[name],
            "report identity differs: " + name,
        )
    provenance = _mapping(
        report["provenance"],
        {"producer_sha256", "auditor_sha256", "trajectory_sha256"},
        "provenance",
    )
    for name, pin in (
        ("producer_sha256", "owner_fixture_sha256"),
        ("auditor_sha256", "owner_auditor_sha256"),
        ("trajectory_sha256", "trajectory_sha256"),
    ):
        _need(
            _digest(provenance[name], "provenance." + name) == pins[pin],
            "provenance identity differs: " + name,
        )
    context = report["native_context"]
    _need(
        type(context) is list
        and len(context) == 3
        and all(type(value) is int for value in context)
        and context == [53, 53, 8],
        "native_context: exact integer list [53,53,8] required",
    )
    _need(
        type(report["context_checks"]) is int and report["context_checks"] == 1,
        "context_checks: exactly one required",
    )
    arguments = _mapping(
        report["arguments"], {"arc_id", "simulate", "selector", "schema"}, "arguments"
    )
    _need(
        type(arguments["arc_id"]) is str
        and arguments["arc_id"] == "never-run"
        and arguments["simulate"] is False
        and arguments["selector"] is True
        and type(arguments["schema"]) is str
        and arguments["schema"] == "cartesian-position-m_velocity-m-s_mass-kg",
        "arguments: fixed never-run/False/True/schema required",
    )
    refusal = _mapping(report["refusal"], {"type", "message"}, "refusal")
    _need(
        type(refusal["type"]) is str
        and refusal["type"] == "RuntimeError"
        and type(refusal["message"]) is str
        and refusal["message"] == "completed original results unavailable",
        "exact refusal required",
    )
    counts = _mapping(
        report["counts"],
        set(_COUNTS)
        | {"acceleration_callbacks", "native_reported_function_evaluations"},
        "counts",
    )
    for name, expected in _COUNTS.items():
        _need(
            type(counts[name]) is int and counts[name] == expected,
            "strict setup count: " + name,
        )
    _need(
        type(counts["acceleration_callbacks"]) is int
        and 0 <= counts["acceleration_callbacks"] <= 100000,
        "acceleration_callbacks: integer0..100000 required",
    )
    _need(
        type(counts["native_reported_function_evaluations"]) is list
        and not counts["native_reported_function_evaluations"],
        "native function counts unavailable",
    )
    check()
    o = _mapping(observation, _OBSERVATION, "observation")
    _need(
        o["schema"] == "ariadna-owner-setup-observation-v1",
        "observation.schema differs",
    )
    _need(type(o["exit_code"]) is int and o["exit_code"] == 0, "childexit0 required")
    _need(
        o["finalization"] == "checked-after-fsync", "durable child observation required"
    )
    finished = _number(o["producer_elapsed_s"], "producer_elapsed_s")
    finalized = _number(o["finalized_elapsed_s"], "finalized_elapsed_s")
    _need(0 <= finished <= finalized < 45, "observation outside producer45s phase")
    _need(
        _digest(o["probe_sha256"], "observation.probe_sha256") == pins["probe_sha256"],
        "observation probe identity differs",
    )
    _need(
        _digest(o["report_sha256"], "observation.report_sha256") == report_sha,
        "report hash differs",
    )
    _need(
        type(trace_raw) is bytes and 0 < len(trace_raw) <= 4096,
        "trace: nonempty <=4096bytes required",
    )
    _need(
        _digest(o["trace_sha256"], "observation.trace_sha256")
        == sha256(trace_raw).hexdigest(),
        "trace hash differs",
    )
    _need(trace_raw.endswith(b"\n"), "trace: truncated final marker")
    lines = trace_raw.splitlines(keepends=True)
    _need(len(lines) == 8, "trace: eight complete markers required")
    previous_elapsed = 0.0
    for index, (phase, line) in enumerate(zip(_PHASES, lines, strict=True)):
        check()
        _need(
            len(line) <= 512 and line.endswith(b"\n"),
            "marker: <=512newline bytes required",
        )
        marker = _mapping(
            _decode(line),
            _MARKER | ({"report_sha256"} if index == 7 else set()),
            "marker",
        )
        _need(
            marker["schema"] == "ariadna-owner-setup-marker-v1"
            and marker["scope"] == _SCOPE,
            "marker schema/scope differs",
        )
        _need(
            type(marker["index"]) is int
            and marker["index"] == index
            and marker["phase"] == phase,
            "marker phase order differs",
        )
        elapsed = _number(marker["elapsed_s"], "marker.elapsed_s")
        _need(
            previous_elapsed <= elapsed <= finished,
            "marker clock reversed or beyond child",
        )
        previous_elapsed = elapsed
        if index == 7:
            _need(
                _digest(marker["report_sha256"], "marker.report_sha256") == report_sha,
                "complete report identity differs",
            )
    check()
    return {
        "schema": "ariadna-owner-setup-audit-v1",
        "status": "passed",
        "scope": _SCOPE,
        "physical_admission": "unavailable",
        "mode": p["mode"],
        "markers_checked": 8,
        "kernel_sha256": pins["kernel_sha256"],
        "report_sha256": report_sha,
        "completion_requires_outer_finalization": True,
    }


def _install_guard() -> None:
    if any(
        name == prefix or name.startswith(prefix + ".")
        for name in sys.modules
        for prefix in _FORBIDDEN
    ):
        raise SetupAuditError("independent auditor already loaded setup producer")
    _install_prefix_guard()

    class NoSetupProducer(importlib.abc.MetaPathFinder):
        def find_spec(
            self, fullname: str, path: object = None, target: object = None
        ) -> None:
            if any(
                fullname == prefix or fullname.startswith(prefix + ".")
                for prefix in _FORBIDDEN
            ):
                raise ImportError("independent auditor forbids " + fullname)

    sys.meta_path.insert(0, NoSetupProducer())


def main(argv: Sequence[str] | None = None) -> int:
    """Read bounded saved files only; never execute a setup producer."""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        _need(
            len(args) == 6 and args[0] == "--audit",
            "private audit requires profile/report/observation/trace/deadline",
        )
        _install_guard()
        result = audit(
            _read(args[4], 4096),
            _decode(_read(args[1], 65536)),
            _read(args[2], 65536),
            _decode(_read(args[3], 65536)),
            deadline_s=float(args[5]),
        )
        sys.stdout.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
        return 0
    except (SetupAuditError, OSError, ValueError, TypeError) as exc:
        sys.stderr.write(f"{type(exc).__name__}: {str(exc)[:1024]}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
