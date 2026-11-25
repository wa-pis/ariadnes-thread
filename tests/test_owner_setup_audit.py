"""Independent literal artificial data; no setup producer or native runtime."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from space_nav import _owner_setup_audit as candidate

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


def _encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def _profile() -> dict[str, object]:
    return {
        "schema": "ariadna-owner-setup-input-v1",
        "scope": _SCOPE,
        "mode": "injected",
        "kernel_path": "/artificial/kernel.so",
        "kernel_sha256": "a" * 64,
        "probe_sha256": "b" * 64,
        "owner_fixture_sha256": "c" * 64,
        "owner_auditor_sha256": "d" * 64,
        "trajectory_sha256": "e" * 64,
        "setup_auditor_sha256": "f" * 64,
    }


def _report() -> dict[str, object]:
    return {
        "schema": "ariadna-owner-setup-report-v1",
        "scope": _SCOPE,
        "mode": "injected",
        "status": "passed",
        "physical_admission": "unavailable",
        "kernel_path": "/artificial/kernel.so",
        "kernel_sha256": "a" * 64,
        "probe_sha256": "b" * 64,
        "setup_auditor_sha256": "f" * 64,
        "provenance": {
            "producer_sha256": "c" * 64,
            "auditor_sha256": "d" * 64,
            "trajectory_sha256": "e" * 64,
        },
        "native_context": [53, 53, 8],
        "arguments": {
            "arc_id": "never-run",
            "simulate": False,
            "selector": True,
            "schema": "cartesian-position-m_velocity-m-s_mass-kg",
        },
        "refusal": {
            "type": "RuntimeError",
            "message": "completed original results unavailable",
        },
        "counts": {
            "factory_attempts": 1,
            "integration_attempts": 0,
            "visitor_calls": 1,
            "acceleration_callbacks": 0,
            "spice_queries": 0,
            "kernel_reads": 0,
            "real_archive_reads": 0,
            "optimizer_entries": 0,
            "native_reported_function_evaluations": [],
        },
        "context_checks": 1,
    }


def _markers(report_raw: bytes) -> list[dict[str, object]]:
    rows = [
        {
            "schema": "ariadna-owner-setup-marker-v1",
            "scope": _SCOPE,
            "index": i,
            "phase": phase,
            "elapsed_s": float(i),
        }
        for i, phase in enumerate(_PHASES)
    ]
    rows[-1]["report_sha256"] = sha256(report_raw).hexdigest()
    return rows


def _trace(rows: list[dict[str, object]]) -> bytes:
    return b"".join(_encode(row) for row in rows)


def _observation(raw: bytes, report_raw: bytes) -> dict[str, object]:
    return {
        "schema": "ariadna-owner-setup-observation-v1",
        "exit_code": 0,
        "producer_elapsed_s": 8.0,
        "finalized_elapsed_s": 8.1,
        "trace_sha256": sha256(raw).hexdigest(),
        "report_sha256": sha256(report_raw).hexdigest(),
        "probe_sha256": "b" * 64,
        "finalization": "checked-after-fsync",
    }


def _audit(
    *,
    profile: object | None = None,
    report: bytes | None = None,
    trace: bytes | None = None,
    observation: object | None = None,
) -> dict[str, object]:
    report = _encode(_report()) if report is None else report
    trace = _trace(_markers(report)) if trace is None else trace
    return candidate.audit(
        trace,
        _profile() if profile is None else profile,
        report,
        _observation(trace, report) if observation is None else observation,
        deadline_s=10.0,
        clock=lambda: 0.0,
    )


@pytest.mark.parametrize("mode", ["injected", "native"])
@pytest.mark.parametrize("callbacks", [0, 17, 100000])
def test_literal_complete_setup_is_conditional_on_external_admission(
    mode: str, callbacks: int
) -> None:
    profile, report = _profile(), _report()
    profile["mode"] = report["mode"] = mode
    report["counts"]["acceleration_callbacks"] = callbacks
    raw = _encode(report)
    assert _audit(profile=profile, report=raw) == {
        "schema": "ariadna-owner-setup-audit-v1",
        "status": "passed",
        "scope": _SCOPE,
        "physical_admission": "unavailable",
        "mode": mode,
        "markers_checked": 8,
        "kernel_sha256": "a" * 64,
        "report_sha256": sha256(raw).hexdigest(),
        "completion_requires_outer_finalization": True,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", "other"),
        ("scope", "physical"),
        ("mode", []),
        ("mode", "other"),
        ("kernel_path", False),
        ("kernel_path", "relative"),
        ("kernel_path", "/bad\0path"),
        ("kernel_sha256", "A" * 64),
        ("probe_sha256", True),
        ("owner_fixture_sha256", "x"),
        ("owner_auditor_sha256", "z" * 64),
        ("trajectory_sha256", []),
        ("setup_auditor_sha256", "short"),
        ("extra", 1),
    ],
)
def test_profile_exact_scope_paths_and_pins(field: str, value: object) -> None:
    profile = _profile()
    profile[field] = value
    with pytest.raises(candidate.SetupAuditError):
        _audit(profile=profile)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", "other"),
        ("scope", "physical"),
        ("mode", "native"),
        ("status", "failed"),
        ("physical_admission", "passed"),
        ("kernel_path", "/different"),
        ("kernel_sha256", "0" * 64),
        ("probe_sha256", "0" * 64),
        ("setup_auditor_sha256", "0" * 64),
        ("native_context", [53, 53, True]),
        ("native_context", [53, 53, 8.0]),
        ("native_context", [53, 53]),
        ("native_context", [53, 53, 9]),
        ("context_checks", True),
        ("context_checks", 0),
        ("context_checks", 2),
        ("extra", 1),
    ],
)
def test_report_exact_identity_scope_and_context(field: str, value: object) -> None:
    report = _report()
    report[field] = value
    with pytest.raises(candidate.SetupAuditError):
        _audit(report=_encode(report))


@pytest.mark.parametrize(
    "record,field,value",
    [
        ("provenance", "producer_sha256", "0" * 64),
        ("provenance", "auditor_sha256", "0" * 64),
        ("provenance", "trajectory_sha256", "0" * 64),
        ("arguments", "arc_id", "forward"),
        ("arguments", "simulate", 0),
        ("arguments", "simulate", True),
        ("arguments", "selector", 1),
        ("arguments", "selector", False),
        ("arguments", "schema", "invalid"),
        ("refusal", "type", "DerivedRuntimeError"),
        ("refusal", "type", "ValueError"),
        ("refusal", "message", "completed original results unavailable "),
        ("counts", "factory_attempts", 2),
        ("counts", "factory_attempts", True),
        ("counts", "integration_attempts", 1),
        ("counts", "integration_attempts", False),
        ("counts", "visitor_calls", 0),
        ("counts", "visitor_calls", 8),
        ("counts", "acceleration_callbacks", -1),
        ("counts", "acceleration_callbacks", 100001),
        ("counts", "acceleration_callbacks", True),
        ("counts", "acceleration_callbacks", 0.0),
        ("counts", "spice_queries", 1),
        ("counts", "kernel_reads", 1),
        ("counts", "real_archive_reads", 1),
        ("counts", "optimizer_entries", 1),
        ("counts", "native_reported_function_evaluations", [0]),
        ("counts", "native_reported_function_evaluations", None),
    ],
)
def test_fixed_arguments_refusal_and_stricter_than_old_budget_counts(
    record: str, field: str, value: object
) -> None:
    report = _report()
    report[record][field] = value
    with pytest.raises(candidate.SetupAuditError):
        _audit(report=_encode(report))


@pytest.mark.parametrize("record", ["provenance", "arguments", "refusal", "counts"])
@pytest.mark.parametrize("change", ["missing", "extra", "not-object"])
def test_nested_report_keys_are_exact(record: str, change: str) -> None:
    report = _report()
    if change == "missing":
        report[record].pop(next(iter(report[record])))
    elif change == "extra":
        report[record]["extra"] = True
    else:
        report[record] = []
    with pytest.raises(candidate.SetupAuditError):
        _audit(report=_encode(report))


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", "other"),
        ("exit_code", True),
        ("exit_code", False),
        ("exit_code", 2),
        ("exit_code", 0.0),
        ("producer_elapsed_s", True),
        ("producer_elapsed_s", -1),
        ("producer_elapsed_s", 45),
        ("producer_elapsed_s", float("nan")),
        ("finalized_elapsed_s", 7.9),
        ("finalized_elapsed_s", 45),
        ("finalized_elapsed_s", float("inf")),
        ("probe_sha256", "0" * 64),
        ("trace_sha256", "0" * 64),
        ("report_sha256", "0" * 64),
        ("finalization", "pending-after-fsync-observation"),
        ("extra", 1),
    ],
)
def test_observation_does_not_replace_exit_identity_or_finalization(
    field: str, value: object
) -> None:
    report = _encode(_report())
    trace = _trace(_markers(report))
    observation = _observation(trace, report)
    observation[field] = value
    with pytest.raises(candidate.SetupAuditError):
        _audit(report=report, trace=trace, observation=observation)


@pytest.mark.parametrize("index", range(8))
def test_each_missing_marker_refuses(index: int) -> None:
    report = _encode(_report())
    markers = _markers(report)
    markers.pop(index)
    with pytest.raises(candidate.SetupAuditError, match="eight"):
        _audit(report=report, trace=_trace(markers))


@pytest.mark.parametrize(
    "field,value",
    [
        ("index", True),
        ("index", 3),
        ("index", 2.0),
        ("schema", "other"),
        ("scope", "physical"),
        ("phase", "complete"),
        ("elapsed_s", True),
        ("elapsed_s", -1),
        ("elapsed_s", 0),
        ("elapsed_s", 8.01),
        ("extra", 1),
    ],
)
def test_marker_types_order_scope_and_time_are_fixed(field: str, value: object) -> None:
    report = _encode(_report())
    markers = _markers(report)
    markers[2][field] = value
    with pytest.raises(candidate.SetupAuditError):
        _audit(report=report, trace=_trace(markers))


def test_complete_marker_must_bind_report() -> None:
    report = _encode(_report())
    markers = _markers(report)
    markers[-1]["report_sha256"] = "0" * 64
    with pytest.raises(candidate.SetupAuditError, match="complete report"):
        _audit(report=report, trace=_trace(markers))


@pytest.mark.parametrize(
    "change",
    [
        "duplicate",
        "truncated",
        "duplicate-key",
        "nonfinite",
        "invalid-utf8",
        "oversize",
    ],
)
def test_bad_trace_cannot_supply_complete_evidence(change: str) -> None:
    report = _encode(_report())
    raw = _trace(_markers(report))
    if change == "duplicate":
        raw += raw.splitlines(keepends=True)[0]
    elif change == "truncated":
        raw = raw[:-1]
    elif change == "duplicate-key":
        raw = raw.replace(b'"index": 0', b'"index": 0,"index": 0', 1)
    elif change == "nonfinite":
        raw = raw.replace(b'"elapsed_s": 0.0', b'"elapsed_s": NaN', 1)
    elif change == "invalid-utf8":
        raw = raw.replace(b"bootstrap", b"\xffootstrap", 1)
    else:
        raw += b" " * (4097 - len(raw))
    with pytest.raises(candidate.SetupAuditError):
        _audit(report=report, trace=raw)


@pytest.mark.parametrize(
    "raw", [b"", b"[]", b"NaN", b'{"schema":0,"schema":1}', b"x" * 65537]
)
def test_report_bytes_are_bounded_unique_and_finite(raw: bytes) -> None:
    with pytest.raises(candidate.SetupAuditError):
        _audit(report=raw)


def test_exact_full_marker_and_report_capacity_with_one_byte_over_refusal() -> None:
    report = _encode(_report())
    report += b" " * (65536 - len(report))
    lines = _trace(_markers(report)).splitlines(keepends=True)
    raw = b"".join(line[:-1] + b" " * (512 - len(line)) + b"\n" for line in lines)
    assert len(raw) == 4096
    assert _audit(report=report, trace=raw)["status"] == "passed"
    # Keep total trace fixed but exceed an individual marker's512byte limit.
    oversized_line = raw.replace(b"\n", b" \n", 1)[:-2] + b"\n"
    with pytest.raises(candidate.SetupAuditError, match="512"):
        _audit(report=report, trace=oversized_line)
    with pytest.raises(candidate.SetupAuditError, match="65536"):
        _audit(report=report + b" ")


@pytest.mark.parametrize(
    "clock,deadline",
    [
        (lambda: False, 10),
        (lambda: float("nan"), 10),
        (lambda: float("inf"), 10),
        (lambda: 10.0, 10.0),
        (lambda: 0.0, False),
        (lambda: 0.0, float("inf")),
    ],
)
def test_finite_unexpired_audit_clock_is_required(
    clock: object, deadline: object
) -> None:
    report = _encode(_report())
    trace = _trace(_markers(report))
    with pytest.raises(candidate.SetupAuditError):
        candidate.audit(
            trace,
            _profile(),
            report,
            _observation(trace, report),
            deadline_s=deadline,
            clock=clock,
        )


@pytest.mark.parametrize("times", [(0, 1, 0), (0, 1, 10)])
def test_clock_reversal_or_expiry_during_review_refuses(times: tuple[int, ...]) -> None:
    report = _encode(_report())
    trace = _trace(_markers(report))
    values = iter(times)
    with pytest.raises(candidate.SetupAuditError):
        candidate.audit(
            trace,
            _profile(),
            report,
            _observation(trace, report),
            deadline_s=10,
            clock=lambda: next(values),
        )


def _cli(
    tmp_path: Path, *, profile_raw: bytes | None = None, prefix: str = ""
) -> subprocess.CompletedProcess[str]:
    report = _encode(_report())
    raw = _trace(_markers(report))
    values = {
        "profile.json": _encode(_profile()) if profile_raw is None else profile_raw,
        "report.json": report,
        "observation.json": _encode(_observation(raw, report)),
        "trace.jsonl": raw,
    }
    for name, value in values.items():
        (tmp_path / name).write_bytes(value)
    source = str(Path(candidate.__file__).parents[1])
    args = [
        "--audit",
        *(str(tmp_path / name) for name in values),
        repr(time.monotonic() + 8),
    ]
    script = (
        f"import sys;sys.path.insert(0,{source!r});"
        + prefix
        + f"from space_nav._owner_setup_audit import main;raise SystemExit(main({args!r}))"
    )
    return subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_separate_saved_only_cli_passes(tmp_path: Path) -> None:
    result = _cli(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["markers_checked"] == 8


@pytest.mark.parametrize("profile", [b" " * 65537, b'{"schema":0,"schema":1}', b"NaN"])
def test_cli_refuses_bounded_malformed_profile(tmp_path: Path, profile: bytes) -> None:
    result = _cli(tmp_path, profile_raw=profile)
    assert result.returncode == 2 and not result.stdout


@pytest.mark.parametrize("module", ["numpy", "space_nav._owner_setup_probe"])
def test_cli_refuses_simulated_preloaded_runtime_or_producer(
    tmp_path: Path, module: str
) -> None:
    result = _cli(
        tmp_path,
        prefix=f"import types;sys.modules[{module!r}]=types.ModuleType({module!r});",
    )
    assert result.returncode == 2 and "already loaded" in result.stderr


def test_guard_blocks_new_old_producers_and_scientific_imports_without_loading(
    tmp_path: Path,
) -> None:
    source = str(Path(candidate.__file__).parents[1])
    script = f"""
import importlib, sys
sys.path.insert(0, {source!r})
from space_nav._owner_setup_audit import _install_guard
_install_guard()
for name in ('space_nav._owner_setup_probe', 'space_nav._owner_setup_run',
             'space_nav._owner_endpoint_fixture', 'space_nav._owner_endpoint_run',
             'space_nav._import_probe', 'tudatpy', 'numpy', 'scipy', 'spiceypy'):
    try:
        importlib.import_module(name)
    except ImportError:
        pass
    else:
        raise AssertionError(name)
assert not {{'tudatpy','numpy','scipy','spiceypy'}} & set(sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
