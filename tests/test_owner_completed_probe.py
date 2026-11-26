"""ADR0281 producer qualification uses artificial owners only, never native work."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from space_nav import _owner_completed_probe as probe
from space_nav._owner_endpoint_fixture import Budget, FixtureError

PHASES = ("bootstrap-ready", "import-ready", "context-ready", "factory-enter",
          "factory-return", "metadata-enter", "metadata-ready", "visitor-enter",
          "visitor-return", "complete")
SCHEMA = "cartesian-position-m_velocity-m-s_mass-kg"
SCOPE = "single-forward-completed-owner-only"


def _raw(value: object) -> bytes:
    return json.dumps(value).encode()


def _profile(tmp_path: Path) -> dict[str, str]:
    kernel = tmp_path / "fake-kernel.bin"
    kernel.write_bytes(b"artificial identity only, no executable code")
    sources = {"probe_sha256": "_owner_completed_probe.py",
               "owner_fixture_sha256": "_owner_endpoint_fixture.py",
               "owner_auditor_sha256": "_owner_endpoint_audit.py",
               "trajectory_sha256": "trajectory.py",
               "completed_auditor_sha256": "_owner_completed_audit.py"}
    package = Path(probe.__file__).parent
    return {"schema": "ariadna-owner-completed-input-v1", "scope": SCOPE,
            "mode": "injected", "kernel_path": str(kernel),
            "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest()} | {
                key: hashlib.sha256((package / name).read_bytes()).hexdigest()
                for key, name in sources.items()}


def _markers(trace: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in trace.read_bytes().splitlines()]


def _injected(monkeypatch: pytest.MonkeyPatch, profile: dict[str, str], trace: Path,
              defect: str | None = None
              ) -> tuple[list[str], dict[str, Callable[..., object]], Budget]:
    calls: list[str] = []
    budget = Budget(time.monotonic())
    kernel = ModuleType("tudatpy.kernel")
    kernel.__file__ = profile["kernel_path"]
    monkeypatch.setitem(sys.modules, "tudatpy.kernel", kernel)
    mass = "Mass state of body Spacecraft"
    results = SimpleNamespace(
        propagation_is_performed=True, integration_completed_successfully=True,
        propagated_state_vector_length=7, total_number_of_function_evaluations=41,
        termination_details=SimpleNamespace(termination_reason="termination_condition_reached",
                                            terminated_on_exact_condition=True),
        processed_state_ids={(0, 6): "Translational state, in Cartesian elements, of body "
                                      "Spacecraft w.r.t. SSB", (6, 1): mass},
        propagated_state_ids={(0, 6): "Translational state (Cowell formulation) of body "
                                       "Spacecraft w.r.t. SSB", (6, 1): mass},
    )
    if defect == "provenance-precharges":
        assert "context" not in calls
    if defect in {"not-performed", "not-completed", "wrong-length", "wrong-count"}:
        field, value = {"not-performed": ("propagation_is_performed", False),
                        "not-completed": ("integration_completed_successfully", False),
                        "wrong-length": ("propagated_state_vector_length", 6),
                        "wrong-count": ("total_number_of_function_evaluations", -1)}[defect]
        setattr(results, field, value)
    if defect == "wrong-termination":
        results.termination_details.terminated_on_exact_condition = False
    if defect == "wrong-row-meaning":
        results.processed_state_ids[(0, 6)] = "unrelated Cartesian row"

    class Owner:
        @property
        def propagation_results(self) -> object:
            assert _markers(trace)[-1]["phase"] == "metadata-enter"
            assert (budget.factory_attempts, budget.integration_attempts,
                    budget.visitor_calls) == (1, 1, 0)
            calls.append("metadata")
            return results

        def _ariadna_original_endpoint(self, selector: bool, schema: str) -> object:
            assert selector is True and schema == SCHEMA
            assert _markers(trace)[-1]["phase"] == "visitor-enter"
            assert (budget.factory_attempts, budget.integration_attempts,
                    budget.visitor_calls) == (1, 1, 1)
            calls.append("visitor")
            state = (10000000.0, 1050000.0, 0.0, 0.0, 1100.0, 0.0, 2000.0)
            if defect == "endpoint-list":
                return [0, 1000.0, state]
            if defect == "state-list":
                return (0, 1000.0, list(state))
            if defect == "nonfinite":
                return (0, 1000.0, (float("nan"), *state[1:]))
            if defect == "bool-state":
                return (0, 1000.0, (True, *state[1:]))
            if defect == "visitor-refusal":
                raise RuntimeError("artificial completed result unavailable")
            return (0, 0.0 if defect == "wrong-selected-epoch" else 1000.0, state)

    def prepare(started_s: float) -> object:
        assert _markers(trace)[-1]["phase"] == "bootstrap-ready"
        calls.append("prepare")
        budget.started_s = started_s
        if defect == "wrong-budget":
            return object()
        if defect == "precharged-factory":
            budget.factory_attempts = 1
        if defect == "precharged-visitor":
            budget.visitor_calls = 1
        return budget

    def import_spice() -> object:
        calls.append("import")
        return None

    def guard_spice(actual: object, spice: object) -> None:
        assert actual is budget and spice is None
        calls.append("guard")

    def provenance() -> object:
        calls.append("provenance")
        result = {"producer_sha256": profile["owner_fixture_sha256"],
                  "auditor_sha256": profile["owner_auditor_sha256"],
                  "trajectory_sha256": profile["trajectory_sha256"]}
        if defect == "provenance":
            result["producer_sha256"] = "0" * 64
        if defect == "provenance-precharges":
            budget.factory_attempts = 1
        return result

    def context() -> object:
        calls.append("context")
        if defect == "context-tuple":
            return (53, 53, 8)
        if defect == "context-float":
            return [53.0, 53, 8]
        return [53, 53, 8]

    def factory(arc_id: str, simulate: bool, actual: Budget) -> object:
        assert arc_id == "forward" and simulate is True and actual is budget
        assert _markers(trace)[-1]["phase"] == "factory-enter"
        assert (budget.factory_attempts, budget.integration_attempts,
                budget.visitor_calls) == (1, 1, 0)
        calls.append("factory")
        # Deliberately distinct from the independently reported native41 RHS count.
        budget.acceleration_callbacks = 3
        if defect == "factory-count":
            budget.factory_attempts = 2
        if defect == "integration-count":
            budget.integration_attempts = 2
        if defect == "factory-precharges-visitor":
            budget.visitor_calls = 1
        if defect == "callback-overflow":
            budget.acceleration_callbacks = 100001
        if defect == "callback-limit":
            budget.acceleration_callbacks = 100000
        if defect == "callback-bool":
            budget.acceleration_callbacks = True
        if defect == "spice-count":
            budget.spice_queries = 1
        if defect == "missing-method":
            return SimpleNamespace(propagation_results=results)
        return Owner()

    return calls, {"prepare": prepare, "import_spice": import_spice,
                   "guard_spice": guard_spice, "provenance": provenance,
                   "context": context, "factory": factory}, budget


def _call(profile: dict[str, str], trace: Path, callbacks: dict[str, Callable[..., object]],
          raw: bytes | None = None) -> dict[str, object]:
    started_s = time.monotonic()
    return probe.probe(_raw(profile) if raw is None else raw, trace,
                       started_s=started_s, deadline_s=started_s + 45, **callbacks)


def test_original_metadata_precedes_single_same_owner_last_endpoint(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, hooks, budget = _injected(monkeypatch, profile, trace)
    synced: list[str] = []
    original_sync = probe._sync

    def sync(path: Path) -> None:
        original_sync(path)
        synced.append(_markers(path)[-1]["phase"])

    monkeypatch.setattr(probe, "_sync", sync)
    report = _call(profile, trace, hooks)
    assert calls == ["prepare", "import", "guard", "provenance", "context",
                     "factory", "metadata", "visitor"]
    assert synced == list(PHASES)
    assert [row["index"] for row in _markers(trace)] == list(range(10))
    assert report["arguments"] == {"arc_id": "forward", "simulate": True,
                                   "selector": True, "schema": SCHEMA}
    assert report["metadata_attempts"] == report["context_checks"] == 1
    assert report["metadata"]["integration_completed_successfully"] is True
    assert report["endpoint"]["remainder_hex"] == (1000.0).hex()
    assert report["counts"] == budget.snapshot() | {
        "native_reported_function_evaluations": [41]}
    assert report["counts"]["acceleration_callbacks"] == 3
    assert report["mode"] == "injected" and report["physical_admission"] == "unavailable"
    assert _markers(trace)[-1]["report_sha256"] == hashlib.sha256(
        probe._json_bytes(report)).hexdigest()
    assert trace.stat().st_size <= 4096
    assert all(len(line) <= 512 for line in trace.read_bytes().splitlines(keepends=True))


@pytest.mark.parametrize("defect", [
    "wrong-budget", "precharged-factory", "precharged-visitor", "provenance",
    "provenance-precharges", "context-tuple",
    "context-float", "factory-count", "integration-count", "factory-precharges-visitor",
    "callback-overflow", "callback-bool", "spice-count", "not-performed", "not-completed",
    "wrong-length", "wrong-count", "wrong-termination", "wrong-row-meaning", "missing-method",
    "endpoint-list", "state-list", "nonfinite", "bool-state", "wrong-selected-epoch",
    "visitor-refusal",
])
def test_partial_failures_never_return_success_or_repeat_native_operations(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, hooks, _ = _injected(monkeypatch, profile, trace, defect)
    with pytest.raises((probe.RunError, FixtureError, RuntimeError, ValueError, TypeError)):
        _call(profile, trace, hooks)
    assert "complete" not in [row["phase"] for row in _markers(trace)]
    assert calls.count("factory") <= 1 and calls.count("metadata") <= 1
    assert calls.count("visitor") <= 1
    if defect == "provenance-precharges":
        assert "context" not in calls
    if defect in {"not-performed", "not-completed", "wrong-length", "wrong-count",
                  "wrong-termination", "wrong-row-meaning"}:
        assert "visitor" not in calls


@pytest.mark.parametrize("field", ["factory_attempts", "integration_attempts", "visitor_calls"])
@pytest.mark.parametrize("phase", ["factory-enter", "metadata-enter", "visitor-enter"])
def test_scope_is_rechecked_after_marker_fsync_before_native_entry(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, phase: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, hooks, budget = _injected(monkeypatch, profile, trace)
    original_sync = probe._sync

    def sync(path: Path) -> None:
        original_sync(path)
        if _markers(path)[-1]["phase"] == phase:
            setattr(budget, field, 2)

    monkeypatch.setattr(probe, "_sync", sync)
    with pytest.raises(probe.RunError, match="scope"):
        _call(profile, trace, hooks)
    assert {"factory-enter": "factory", "metadata-enter": "metadata",
            "visitor-enter": "visitor"}[phase] not in calls


@pytest.mark.parametrize("field,value", [
    ("schema", "old-setup"), ("scope", "never-run-owner-setup-only"), ("mode", "other"),
    ("kernel_path", "relative.bin"), ("kernel_path", "/bad\0kernel"),
    ("kernel_sha256", "bad"), ("probe_sha256", "0" * 64),
    ("owner_fixture_sha256", "0" * 64), ("owner_auditor_sha256", "0" * 64),
    ("trajectory_sha256", "0" * 64), ("completed_auditor_sha256", "0" * 64),
    ("extra", "forbidden"),
])
def test_profile_identity_is_checked_before_observation(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "unused.jsonl"
    calls, hooks, _ = _injected(monkeypatch, profile, trace)
    profile[field] = value
    with pytest.raises((probe.RunError, ValueError, TypeError)):
        _call(profile, trace, hooks)
    assert not trace.exists() and not calls


@pytest.mark.parametrize("raw", [b"{}", b"[]", b"{", b'{"x":NaN}',
                                  b'{"x":1,"x":2}', b"x" * 65537, "{}"])
def test_invalid_input_has_no_native_entry(tmp_path: Path, raw: object) -> None:
    started_s = time.monotonic()
    trace = tmp_path / "unused.jsonl"
    with pytest.raises((probe.RunError, ValueError, TypeError)):
        probe.probe(raw, trace, started_s=started_s, deadline_s=started_s + 45)
    assert not trace.exists()


@pytest.mark.parametrize("mode,hooks_used", [("injected", "none"), ("injected", "partial"),
                                           ("native", "all"), ("native", "none")])
def test_native_and_injected_modes_cannot_cross(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, hooks_used: str) -> None:
    profile = _profile(tmp_path)
    profile["mode"] = mode
    trace = tmp_path / "unused.jsonl"
    calls, hooks, _ = _injected(monkeypatch, profile, trace)
    if hooks_used == "none":
        hooks = {}
    elif hooks_used == "partial":
        hooks.pop("factory")
    with pytest.raises(probe.RunError):
        _call(profile, trace, hooks)
    assert not trace.exists() and not calls


@pytest.mark.parametrize("phase", PHASES)
def test_failed_marker_fsync_never_returns_a_report(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, hooks, _ = _injected(monkeypatch, profile, trace)
    original_sync = probe._sync

    def sync(path: Path) -> None:
        original_sync(path)
        if _markers(path)[-1]["phase"] == phase:
            raise OSError("artificial marker fsync failure")

    monkeypatch.setattr(probe, "_sync", sync)
    with pytest.raises(OSError, match="fsync"):
        _call(profile, trace, hooks)
    assert _markers(trace)[-1]["phase"] == phase


@pytest.mark.parametrize("start_offset,deadline_offset", [(1, 45), (-61, 45), (0, 46), (0, 0)])
def test_original_clock_cannot_be_reset_or_extended(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        start_offset: float, deadline_offset: float) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "unused.jsonl"
    _, hooks, _ = _injected(monkeypatch, profile, trace)
    started_s = time.monotonic() + start_offset
    with pytest.raises(probe.RunError):
        probe.probe(_raw(profile), trace, started_s=started_s,
                    deadline_s=started_s + deadline_offset, **hooks)
    assert not trace.exists()


def test_full_input_capacity_original_callback_cap_and_exclusive_trace(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, hooks, _ = _injected(monkeypatch, profile, trace, "callback-limit")
    raw = _raw(profile)
    raw += b" " * (65536 - len(raw))
    report = _call(profile, trace, hooks, raw)
    assert report["counts"]["acceleration_callbacks"] == 100000
    assert report["counts"]["native_reported_function_evaluations"] == [41]
    saved = trace.read_bytes()
    with pytest.raises(FileExistsError):
        _call(profile, trace, hooks)
    assert trace.read_bytes() == saved


def test_scope_and_time_checked_after_complete_marker_fsync(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, hooks, budget = _injected(monkeypatch, profile, trace)
    original_sync = probe._sync

    def sync(path: Path) -> None:
        original_sync(path)
        if _markers(trace)[-1]["phase"] == "complete":
            budget.visitor_calls = 2

    monkeypatch.setattr(probe, "_sync", sync)
    with pytest.raises(probe.RunError, match="scope"):
        _call(profile, trace, hooks)
    assert _markers(trace)[-1]["phase"] == "complete"


@pytest.mark.parametrize("limit", ["MARKER_BYTES", "TRACE_BYTES", "REPORT_BYTES"])
def test_marker_trace_and_report_partitions_refuse_overflow(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, limit: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, hooks, _ = _injected(monkeypatch, profile, trace)
    monkeypatch.setattr(probe, limit, 100)
    with pytest.raises(probe.RunError, match="byte"):
        _call(profile, trace, hooks)
    assert "complete" not in [row["phase"] for row in _markers(trace)]


@pytest.mark.parametrize("defect", ["missing", "path", "hash"])
def test_loaded_kernel_identity_refuses_before_factory(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, hooks, _ = _injected(monkeypatch, profile, trace)
    if defect == "missing":
        monkeypatch.delitem(sys.modules, "tudatpy.kernel")
    elif defect == "path":
        sys.modules["tudatpy.kernel"].__file__ = str(tmp_path / "another.bin")
    else:
        Path(profile["kernel_path"]).write_bytes(b"changed identity")
    with pytest.raises(probe.RunError, match="identity"):
        _call(profile, trace, hooks)
    assert "factory" not in calls


def test_artificial_emitted_report_passes_separate_guarded_saved_audit(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, hooks, _ = _injected(monkeypatch, profile, trace)
    started_s = time.monotonic()
    report = probe.probe(_raw(profile), trace, started_s=started_s,
                         deadline_s=started_s + 45, **hooks)
    report_raw = probe._json_bytes(report)
    producer_elapsed_s = time.monotonic() - started_s
    profile_path = tmp_path / "input.json"
    report_path = tmp_path / "producer.json"
    observation_path = tmp_path / "observation.json"
    for path, raw in ((profile_path, _raw(profile)), (report_path, report_raw)):
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finalized_elapsed_s = time.monotonic() - started_s
    observation = {
        "schema": "ariadna-owner-completed-observation-v1", "exit_code": 0,
        "producer_elapsed_s": producer_elapsed_s,
        "finalized_elapsed_s": finalized_elapsed_s,
        "trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest(),
        "report_sha256": hashlib.sha256(report_raw).hexdigest(),
        "probe_sha256": profile["probe_sha256"], "finalization": "checked-after-fsync",
    }
    with observation_path.open("xb") as stream:
        stream.write(_raw(observation))
        stream.flush()
        os.fsync(stream.fileno())
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "space_nav._owner_completed_audit", "--audit",
         str(profile_path), str(report_path), str(observation_path), str(trace),
         repr(time.monotonic() + 10)], capture_output=True, check=False, timeout=10,
    )
    assert completed.returncode == 0, completed.stderr.decode()
    result = json.loads(completed.stdout)
    assert result["status"] == "passed" and result["mode"] == "injected"
    assert result["markers_checked"] == 10
    assert result["completion_requires_outer_finalization"] is True
    assert result["physical_admission"] == "unavailable"


def test_private_main_passes_inherited_clock_and_serializes_only_report(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "input.json"
    source.write_bytes(b"artificial opaque profile")
    observed: list[tuple[bytes, Path, float, float]] = []

    def artificial(raw: bytes, trace: Path, *, started_s: float,
                   deadline_s: float) -> dict[str, object]:
        observed.append((raw, trace, started_s, deadline_s))
        return {"mode": "injected", "physical_admission": "unavailable"}

    monkeypatch.setattr(probe, "probe", artificial)
    assert probe.main(["--probe", str(source), "1.0", "46.0"]) == 0
    assert observed == [(source.read_bytes(), tmp_path / "trace.jsonl", 1.0, 46.0)]
    assert json.loads(capfd.readouterr().out)["mode"] == "injected"


def test_private_main_refuses_wrong_shape_without_native_work(
        capsys: pytest.CaptureFixture[str]) -> None:
    assert probe.main(["--parent"]) == 2
    assert "private completed probe" in capsys.readouterr().err


@pytest.mark.parametrize("clock_defect", ["reversed", "expired"])
def test_marker_fsync_clock_change_stops_before_next_native_operation(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock_defect: str) -> None:
    from space_nav import _import_probe
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, hooks, budget = _injected(monkeypatch, profile, trace)
    started_s = time.monotonic()
    now = [started_s + 1]
    budget.clock = lambda: now[0]
    monkeypatch.setattr(_import_probe, "_now", lambda: now[0])
    original_sync = probe._sync

    def sync(path: Path) -> None:
        original_sync(path)
        if _markers(path)[-1]["phase"] == "metadata-enter":
            now[0] = started_s + (0.5 if clock_defect == "reversed" else 45)

    monkeypatch.setattr(probe, "_sync", sync)
    with pytest.raises(probe.RunError, match="clock|deadline"):
        probe.probe(_raw(profile), trace, started_s=started_s,
                    deadline_s=started_s + 45, **hooks)
    assert "metadata" not in calls and "visitor" not in calls
