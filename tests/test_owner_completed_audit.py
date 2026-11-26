"""Independent literal artificial packets; no producer/native runtime execution."""

from __future__ import annotations

from decimal import Decimal, localcontext
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import pytest

from space_nav import _owner_completed_audit as candidate

_SCOPE = "single-forward-completed-owner-only"
_PHASES = ("bootstrap-ready", "import-ready", "context-ready", "factory-enter",
           "factory-return", "metadata-enter", "metadata-ready", "visitor-enter",
           "visitor-return", "complete")


def _encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode()


def _profile() -> dict[str, object]:
    return {"schema": "ariadna-owner-completed-input-v1", "scope": _SCOPE,
            "mode": "injected", "kernel_path": "/artificial/kernel.so", "kernel_sha256": "a" * 64,
            "probe_sha256": "b" * 64, "owner_fixture_sha256": "c" * 64,
            "owner_auditor_sha256": "d" * 64, "trajectory_sha256": "e" * 64,
            "completed_auditor_sha256": "f" * 64}


def _report() -> dict[str, Any]:
    metadata: dict[str, object] = {
        "propagated_state_vector_length": 7, "propagation_is_performed": True,
        "integration_completed_successfully": True, "termination_reason": "termination_condition_reached",
        "terminated_on_exact_condition": True, "clear_numerical_solution": False,
        "set_integrated_result": False, "origin": "SSB", "orientation": "J2000"}
    for field, desc in (
        ("processed_state_ids", "Translational state, in Cartesian elements, of body Spacecraft w.r.t. SSB"),
        ("propagated_state_ids", "Translational state (Cowell formulation) of body Spacecraft w.r.t. SSB")):
        metadata[field] = [{"start": 0, "size": 6, "description": desc},
                           {"start": 6, "size": 1, "description": "Mass state of body Spacecraft"}]
    return {"schema": "ariadna-owner-completed-report-v1", "scope": _SCOPE, "mode": "injected",
            "status": "passed", "physical_admission": "unavailable", "kernel_path": "/artificial/kernel.so",
            "kernel_sha256": "a" * 64, "probe_sha256": "b" * 64, "completed_auditor_sha256": "f" * 64,
            "provenance": {"producer_sha256": "c" * 64, "auditor_sha256": "d" * 64,
                           "trajectory_sha256": "e" * 64},
            "native_context": [53, 53, 8],
            "arguments": {"arc_id": "forward", "simulate": True, "selector": True,
                          "schema": "cartesian-position-m_velocity-m-s_mass-kg"},
            "counts": {"factory_attempts": 1, "integration_attempts": 1, "visitor_calls": 1,
                       "acceleration_callbacks": 17, "spice_queries": 0, "kernel_reads": 0,
                       "real_archive_reads": 0, "optimizer_entries": 0,
                       "native_reported_function_evaluations": [23]},
            "context_checks": 1, "metadata_attempts": 1, "metadata": metadata,
            "endpoint": {"hour": 0, "remainder_hex": 1000.0.hex(),
                         "state_hex": [v.hex() for v in
                                       (10000000.0, 1050000.0, 0.0, 0.0, 1100.0, 0.0, 2000.0)]}}


def _markers(report_raw: bytes) -> list[dict[str, object]]:
    rows = [{"schema": "ariadna-owner-completed-marker-v1", "scope": _SCOPE, "index": i,
             "phase": phase, "elapsed_s": float(i)} for i, phase in enumerate(_PHASES)]
    rows[-1]["report_sha256"] = sha256(report_raw).hexdigest()
    return rows


def _trace(rows: list[dict[str, object]]) -> bytes:
    return b"".join(_encode(row) for row in rows)


def _observation(trace: bytes, report: bytes) -> dict[str, object]:
    return {"schema": "ariadna-owner-completed-observation-v1", "exit_code": 0,
            "producer_elapsed_s": 10.0, "finalized_elapsed_s": 10.1,
            "trace_sha256": sha256(trace).hexdigest(), "report_sha256": sha256(report).hexdigest(),
            "probe_sha256": "b" * 64, "finalization": "checked-after-fsync"}


def _audit(*, profile: object | None = None, report: bytes | None = None,
           trace: bytes | None = None, observation: object | None = None) -> dict[str, object]:
    report = _encode(_report()) if report is None else report
    trace = _trace(_markers(report)) if trace is None else trace
    return candidate.audit(trace, _profile() if profile is None else profile, report,
                           _observation(trace, report) if observation is None else observation,
                           deadline_s=10.0, clock=lambda: 0.0)


@pytest.mark.parametrize("mode", ["injected", "native"])
@pytest.mark.parametrize("callbacks,function_count", [(0, 0), (17, 23), (100000, 123456)])
def test_literal_success_preserves_separate_counts_and_external_admission(
    mode: str, callbacks: int, function_count: int
) -> None:
    p, r = _profile(), _report()
    p["mode"] = r["mode"] = mode
    r["counts"]["acceleration_callbacks"] = callbacks
    r["counts"]["native_reported_function_evaluations"] = [function_count]
    raw = _encode(r)
    assert _audit(profile=p, report=raw) == {
        "schema": "ariadna-owner-completed-audit-v1", "status": "passed", "scope": _SCOPE,
        "physical_admission": "unavailable", "mode": mode, "markers_checked": 10,
        "kernel_sha256": "a" * 64, "report_sha256": sha256(raw).hexdigest(),
        "completion_requires_outer_finalization": True}


@pytest.mark.parametrize("field,value", [
    ("schema", "ariadna-owner-setup-input-v1"), ("scope", "never-run-owner-setup-only"),
    ("mode", "other"), ("kernel_path", "relative"), ("kernel_path", "/bad\0path"),
    ("kernel_sha256", "A" * 64), ("probe_sha256", True), ("completed_auditor_sha256", "x"),
    ("extra", 1)])
def test_profile_rejects_old_scope_and_bad_identity(field: str, value: object) -> None:
    p = _profile()
    p[field] = value
    with pytest.raises(candidate.CompletedAuditError):
        _audit(profile=p)


@pytest.mark.parametrize("record,field,value", [
    (None, "schema", "ariadna-owner-setup-report-v1"), (None, "mode", "native"),
    (None, "physical_admission", "passed"), (None, "context_checks", True),
    (None, "metadata_attempts", 0), (None, "metadata_attempts", 1.0),
    (None, "native_context", [53, 53, 8.0]), (None, "kernel_sha256", "0" * 64),
    (None, "completed_auditor_sha256", "0" * 64),
    ("provenance", "trajectory_sha256", "0" * 64),
    ("arguments", "arc_id", "reverse"), ("arguments", "simulate", False),
    ("arguments", "simulate", 1), ("arguments", "selector", 1),
    ("arguments", "schema", "different"), ("counts", "factory_attempts", 2),
    ("counts", "integration_attempts", 0), ("counts", "visitor_calls", True),
    ("counts", "acceleration_callbacks", 100001), ("counts", "acceleration_callbacks", False),
    ("counts", "spice_queries", 1), ("counts", "kernel_reads", 1),
    ("counts", "real_archive_reads", 1), ("counts", "optimizer_entries", 1),
    ("counts", "native_reported_function_evaluations", []),
    ("counts", "native_reported_function_evaluations", [1, 2]),
    ("counts", "native_reported_function_evaluations", [True]),
    ("counts", "native_reported_function_evaluations", [1.0]),
    ("counts", "native_reported_function_evaluations", [-1]),
    ("metadata", "integration_completed_successfully", False),
    ("metadata", "propagation_is_performed", 1), ("metadata", "propagated_state_vector_length", 7.0),
    ("metadata", "terminated_on_exact_condition", False), ("metadata", "origin", "Moon"),
    ("metadata", "orientation", "ECLIPJ2000"), ("metadata", "clear_numerical_solution", True),
    ("metadata", "termination_reason", "runtime_error_caught"),
    ("endpoint", "hour", False), ("endpoint", "hour", 0.0),
    ("endpoint", "remainder_hex", 0.0.hex()), ("endpoint", "remainder_hex", "1000"),
    ("endpoint", "state_hex", ["nan"] * 7), ("endpoint", "state_hex", [0.0] * 7),
])
def test_exact_scope_metadata_selected_epoch_and_counts_refuse(
    record: str | None, field: str, value: object
) -> None:
    r = _report()
    (r if record is None else r[record])[field] = value
    with pytest.raises(candidate.CompletedAuditError):
        _audit(report=_encode(r))


@pytest.mark.parametrize("record", ["provenance", "arguments", "counts", "metadata", "endpoint"])
@pytest.mark.parametrize("change", ["missing", "extra", "not-object"])
def test_nested_report_keys_are_exact(record: str, change: str) -> None:
    r = _report()
    if change == "missing":
        r[record].pop(next(iter(r[record])))
    elif change == "extra":
        r[record]["extra"] = True
    else:
        r[record] = []
    with pytest.raises(candidate.CompletedAuditError):
        _audit(report=_encode(r))


def test_wrong_processed_state_description_refuses() -> None:
    r = _report()
    r["metadata"]["processed_state_ids"][0]["description"] += " changed"
    with pytest.raises(candidate.CompletedAuditError, match="description"):
        _audit(report=_encode(r))


@pytest.mark.parametrize("index,limit", [(0, 0.001), (4, 1e-6), (6, 1e-9)])
def test_numeric_gate_boundary_has_independent_decimal_oracle(index: int, limit: float) -> None:
    r = _report()
    state = r["endpoint"]["state_hex"]
    base = float.fromhex(state[index])
    rounded = base + limit
    # Decimal.from_float independently establishes exact binary64 distances.
    with localcontext() as context:
        context.prec = 80
        decimal_limit = {0: Decimal("0.001"), 4: Decimal("0.000001"), 6: Decimal("0.000000001")}[index]
        if Decimal.from_float(rounded) - Decimal.from_float(base) > decimal_limit:
            above, below = rounded, math.nextafter(rounded, base)
        else:
            below, above = rounded, math.nextafter(rounded, math.inf)
        assert Decimal.from_float(above) - Decimal.from_float(base) > decimal_limit
        assert Decimal.from_float(below) - Decimal.from_float(base) < decimal_limit
    state[index] = below.hex()
    assert _audit(report=_encode(r))["status"] == "passed"
    state[index] = above.hex()
    with pytest.raises(candidate.CompletedAuditError, match={0: "position", 4: "velocity", 6: "mass"}[index]):
        _audit(report=_encode(r))


@pytest.mark.parametrize("indices,delta", [((0, 1), 0.0008), ((3, 4), 0.0000008)])
def test_gate_is_euclidean_not_per_component(indices: tuple[int, int], delta: float) -> None:
    r = _report()
    for i in indices:
        r["endpoint"]["state_hex"][i] = (float.fromhex(r["endpoint"]["state_hex"][i]) + delta).hex()
    with pytest.raises(candidate.CompletedAuditError, match="norm"):
        _audit(report=_encode(r))


@pytest.mark.parametrize("field,value", [
    ("exit_code", True), ("exit_code", 2), ("producer_elapsed_s", -1),
    ("producer_elapsed_s", 45), ("producer_elapsed_s", True),
    ("finalized_elapsed_s", 9.9), ("finalized_elapsed_s", 45),
    ("trace_sha256", "0" * 64), ("report_sha256", "0" * 64),
    ("finalization", "pending-after-fsync-observation"), ("probe_sha256", "0" * 64)])
def test_observation_requires_childexit_identity_and_durability(field: str, value: object) -> None:
    r = _encode(_report())
    trace = _trace(_markers(r))
    o = _observation(trace, r)
    o[field] = value
    with pytest.raises(candidate.CompletedAuditError):
        _audit(report=r, trace=trace, observation=o)


@pytest.mark.parametrize("index", range(10))
def test_each_missing_marker_refuses(index: int) -> None:
    r = _encode(_report())
    rows = _markers(r)
    rows.pop(index)
    with pytest.raises(candidate.CompletedAuditError, match="ten"):
        _audit(report=r, trace=_trace(rows))


@pytest.mark.parametrize("field,value", [("index", True), ("phase", "complete"),
    ("elapsed_s", -1), ("elapsed_s", 0), ("scope", "physical"), ("extra", 1)])
def test_marker_shape_order_and_clock(field: str, value: object) -> None:
    r = _encode(_report())
    rows = _markers(r)
    rows[5][field] = value
    with pytest.raises(candidate.CompletedAuditError):
        _audit(report=r, trace=_trace(rows))


@pytest.mark.parametrize("defect", ["hash", "truncated", "duplicate-key", "nonfinite", "oversize"])
def test_trace_requires_complete_bounded_hashed_markers(defect: str) -> None:
    r = _encode(_report())
    rows = _markers(r)
    if defect == "hash":
        rows[-1]["report_sha256"] = "0" * 64
    trace = _trace(rows)
    if defect == "truncated":
        trace = trace[:-1]
    elif defect == "duplicate-key":
        trace = trace.replace(b'"index": 0', b'"index":0,"index":0', 1)
    elif defect == "nonfinite":
        trace = trace.replace(b'"elapsed_s": 0.0', b'"elapsed_s":NaN', 1)
    elif defect == "oversize":
        trace += b" " * (4097 - len(trace))
    with pytest.raises(candidate.CompletedAuditError):
        _audit(report=r, trace=trace)


@pytest.mark.parametrize("raw", [b"", b"[]", b"NaN", b'{"schema":0,"schema":1}', b"x" * 65537])
def test_report_bytes_are_bounded_unique_finite(raw: bytes) -> None:
    with pytest.raises(candidate.CompletedAuditError):
        _audit(report=raw)


def test_ten_marker_total_capacity_and_individual_limit_are_independent() -> None:
    report = _encode(_report())
    report += b" " * (65536 - len(report))
    lines = _trace(_markers(report)).splitlines(keepends=True)
    # Ten512B lines would exceed4KiB; use10lines with one exactly512B and total4096B.
    sizes = [512] + [398] * 8 + [400]
    assert sum(sizes) == 4096
    trace = b"".join(line[:-1] + b" " * (size - len(line)) + b"\n"
                     for line, size in zip(lines, sizes, strict=True))
    assert len(trace) == 4096
    assert _audit(report=report, trace=trace)["status"] == "passed"
    lines = trace.splitlines(keepends=True)
    lines[0] = lines[0][:-1] + b" \n"
    lines[1] = lines[1][:-2] + b"\n"
    with pytest.raises(candidate.CompletedAuditError, match="512"):
        _audit(report=report, trace=b"".join(lines))
    with pytest.raises(candidate.CompletedAuditError, match="65536"):
        _audit(report=report + b" ")


@pytest.mark.parametrize("times", [(0.0, 1.0, 0.0), (0.0, 1.0, 10.0), (float("nan"),), (10.0,)])
def test_clock_reversal_expiry_and_nonfinite_refuse(times: tuple[float, ...]) -> None:
    r = _encode(_report())
    trace = _trace(_markers(r))
    it = iter(times)
    with pytest.raises(candidate.CompletedAuditError):
        candidate.audit(trace, _profile(), r, _observation(trace, r), deadline_s=10,
                        clock=lambda: next(it))


def _cli(tmp_path: Path, *, prefix: str = "") -> subprocess.CompletedProcess[str]:
    report = _encode(_report())
    trace = _trace(_markers(report))
    values = {"profile.json": _encode(_profile()), "report.json": report,
              "observation.json": _encode(_observation(trace, report)), "trace.jsonl": trace}
    for name, raw in values.items():
        (tmp_path / name).write_bytes(raw)
    source = str(Path(candidate.__file__).parents[1])
    args = ["--audit", *(str(tmp_path / name) for name in values), repr(time.monotonic() + 8)]
    script = (f"import sys;sys.path.insert(0,{source!r});" + prefix
              + f"from space_nav._owner_completed_audit import main;raise SystemExit(main({args!r}))")
    return subprocess.run([sys.executable, "-I", "-B", "-c", script],
                          capture_output=True, text=True, timeout=10)


def test_separate_saved_only_cli_passes(tmp_path: Path) -> None:
    result = _cli(tmp_path)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["markers_checked"] == 10


@pytest.mark.parametrize("module", ["numpy", "space_nav._owner_completed_probe", "space_nav.trajectory"])
def test_cli_refuses_preloaded_runtime_or_producer(tmp_path: Path, module: str) -> None:
    result = _cli(tmp_path, prefix=f"import types;sys.modules[{module!r}]=types.ModuleType({module!r});")
    assert result.returncode == 2 and "already loaded" in result.stderr


def test_guard_blocks_future_producer_and_science_imports(tmp_path: Path) -> None:
    source = str(Path(candidate.__file__).parents[1])
    script = f"""
import importlib,sys
sys.path.insert(0,{source!r})
from space_nav._owner_completed_audit import _install_guard
_install_guard()
for name in ('space_nav._owner_completed_probe','space_nav._owner_setup_probe',
             'space_nav._owner_endpoint_fixture','space_nav._owner_endpoint_run',
             'space_nav._import_probe','space_nav.trajectory','tudatpy','numpy','scipy','spiceypy'):
    try:importlib.import_module(name)
    except ImportError:pass
    else:raise AssertionError(name)
assert not {{'numpy','scipy','tudatpy','spiceypy'}} & set(sys.modules)
"""
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
