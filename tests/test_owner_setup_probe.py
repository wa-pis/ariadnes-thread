"""ADR0273 setup qualification uses only fake owners and injected native prefixes."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
from types import ModuleType
from typing import Any

import pytest

from space_nav import _owner_setup_probe as probe
from space_nav._owner_endpoint_fixture import Budget, FixtureError

PHASES = ("bootstrap-ready", "import-ready", "context-ready", "factory-enter",
          "factory-return", "visitor-enter", "visitor-refused", "complete")
SCOPE = "never-run-owner-setup-only"
SCHEMA = "cartesian-position-m_velocity-m-s_mass-kg"
UNAVAILABLE = "completed original results unavailable"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _profile(tmp_path: Path) -> dict[str, str]:
    kernel = tmp_path / "artificial-kernel.bin"
    kernel.write_bytes(b"artificial identity, never executable native code")
    package = Path(probe.__file__).parent
    sources = {"probe_sha256": "_owner_setup_probe.py",
               "owner_fixture_sha256": "_owner_endpoint_fixture.py",
               "owner_auditor_sha256": "_owner_endpoint_audit.py",
               "trajectory_sha256": "trajectory.py",
               "setup_auditor_sha256": "_owner_setup_audit.py"}
    return {"schema": "ariadna-owner-setup-input-v1", "scope": SCOPE, "mode": "injected",
            "kernel_path": str(kernel), "kernel_sha256": _digest(kernel)} | {
                field: _digest(package / name) for field, name in sources.items()}


def _raw(value: object) -> bytes:
    return json.dumps(value).encode()


def _markers(trace: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in trace.read_bytes().splitlines()]


def _provenance(profile: dict[str, str]) -> dict[str, str]:
    return {"producer_sha256": profile["owner_fixture_sha256"],
            "auditor_sha256": profile["owner_auditor_sha256"],
            "trajectory_sha256": profile["trajectory_sha256"]}


def _injected(monkeypatch: pytest.MonkeyPatch, profile: dict[str, str], trace: Path,
              *, defect: str | None = None
              ) -> tuple[list[str], dict[str, Callable[..., object]], Budget]:
    calls: list[str] = []
    budget = Budget(time.monotonic())
    spice = object()
    kernel = ModuleType("tudatpy.kernel")
    kernel.__file__ = profile["kernel_path"]
    monkeypatch.setitem(sys.modules, "tudatpy.kernel", kernel)

    class WrongRefusal(RuntimeError):
        pass

    class Owner:
        def _ariadna_original_endpoint(self, selector: bool, schema: str) -> object:
            assert selector is True and schema == SCHEMA
            assert _markers(trace)[-1]["phase"] == "visitor-enter"
            assert (budget.factory_attempts, budget.integration_attempts,
                    budget.visitor_calls) == (1, 0, 1)
            calls.append("visitor")
            if defect == "returned-row":
                return (0, 0, 0)
            if defect == "refusal-subclass":
                raise WrongRefusal(UNAVAILABLE)
            if defect == "wrong-message":
                raise RuntimeError(UNAVAILABLE + " changed")
            if defect == "wrong-type":
                raise ValueError(UNAVAILABLE)
            raise RuntimeError(UNAVAILABLE)

        @property
        def propagation_results(self) -> object:
            pytest.fail("setup probe must not inspect metadata/history/results")

    def prepare(started_s: float) -> Budget:
        assert _markers(trace)[-1]["phase"] == "bootstrap-ready"
        budget.started_s = started_s
        calls.append("prepare")
        if defect == "precharged-factory":
            budget.factory_attempts = 1
        elif defect == "precharged-visitor":
            budget.visitor_calls = 1
        return budget

    def import_spice() -> object:
        assert _markers(trace)[-1]["phase"] == "bootstrap-ready"
        calls.append("import")
        return spice

    def guard_spice(actual: object, actual_spice: object) -> None:
        assert actual is budget and actual_spice is spice
        assert _markers(trace)[-1]["phase"] == "bootstrap-ready"
        calls.append("guard")

    def provenance() -> object:
        assert _markers(trace)[-1]["phase"] == "import-ready"
        calls.append("provenance")
        result = _provenance(profile)
        if defect == "provenance":
            result["producer_sha256"] = "0" * 64
        return result

    def context() -> object:
        assert _markers(trace)[-1]["phase"] == "import-ready"
        calls.append("context")
        if defect == "context-tuple":
            return (53, 53, 8)
        if defect == "context-float":
            return [53.0, 53, 8]
        if defect == "context-wrong":
            return [53, 53, 9]
        return [53, 53, 8]

    def factory(arc_id: str, simulate: bool, actual: Budget) -> object:
        assert arc_id == "never-run" and simulate is False and actual is budget
        assert _markers(trace)[-1]["phase"] == "factory-enter"
        assert (budget.factory_attempts, budget.integration_attempts,
                budget.visitor_calls) == (1, 0, 0)
        calls.append("factory")
        if defect == "factory-count":
            budget.factory_attempts = 2
        elif defect == "integration-count":
            budget.integration_attempts = 1
        elif defect == "factory-precharges-visitor":
            budget.visitor_calls = 1
        elif defect == "callback-overflow":
            budget.acceleration_callbacks = 100001
        elif defect == "callback-limit":
            budget.acceleration_callbacks = 100000
        elif defect == "callback-bool":
            budget.acceleration_callbacks = True
        elif defect == "spice-count":
            budget.spice_queries = 1
        elif defect == "missing-method":
            return object()
        elif defect == "noncallable-method":
            return type("NotCallable", (), {"_ariadna_original_endpoint": None})()
        return Owner()

    return calls, {"prepare": prepare, "import_spice": import_spice,
                   "guard_spice": guard_spice, "provenance": provenance,
                   "context": context, "factory": factory}, budget


def _call(profile: dict[str, str], trace: Path, callbacks: dict[str, Callable[..., object]],
          *, raw: bytes | None = None) -> dict[str, object]:
    started = time.monotonic()
    return probe.probe(_raw(profile) if raw is None else raw, trace, started_s=started,
                       deadline_s=started + 45, **callbacks)


def test_injected_setup_has_exact_order_counts_refusal_and_durable_markers(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, callbacks, budget = _injected(monkeypatch, profile, trace)
    synced: list[str] = []
    original = probe._sync

    def sync(path: Path) -> None:
        original(path)
        synced.append(str(_markers(path)[-1]["phase"]))

    monkeypatch.setattr(probe, "_sync", sync)
    report = _call(profile, trace, callbacks)
    assert calls == ["prepare", "import", "guard", "provenance", "context", "factory", "visitor"]
    records = _markers(trace)
    assert synced == [r["phase"] for r in records] == list(PHASES)
    assert [r["index"] for r in records] == list(range(8))
    assert all(r["schema"] == "ariadna-owner-setup-marker-v1" and r["scope"] == SCOPE
               for r in records)
    assert report["schema"] == "ariadna-owner-setup-report-v1"
    assert report["mode"] == "injected" and report["status"] == "passed"
    assert report["physical_admission"] == "unavailable"
    assert report["context_checks"] == 1 and report["native_context"] == [53, 53, 8]
    assert report["counts"] == budget.snapshot()
    assert report["arguments"] == {"arc_id": "never-run", "simulate": False,
                                   "selector": True, "schema": SCHEMA}
    assert report["refusal"] == {"type": "RuntimeError", "message": UNAVAILABLE}
    assert report["provenance"] == _provenance(profile)
    assert records[-1]["report_sha256"] == hashlib.sha256(probe._json_bytes(report)).hexdigest()
    assert all(len(line) <= 512 for line in trace.read_bytes().splitlines(keepends=True))
    assert trace.stat().st_size <= 4096
    times = [r["elapsed_s"] for r in records]
    assert all(0 <= value < 45 for value in times) and times == sorted(times)


@pytest.mark.parametrize("defect", [
    "returned-row", "refusal-subclass", "wrong-message", "wrong-type", "provenance",
    "context-tuple", "context-float", "context-wrong", "precharged-factory", "precharged-visitor",
    "factory-count", "integration-count", "factory-precharges-visitor", "callback-overflow",
    "callback-bool", "spice-count", "missing-method", "noncallable-method",
])
def test_unexpected_setup_stops_without_complete_or_forward_work(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, callbacks, _ = _injected(monkeypatch, profile, trace, defect=defect)
    with pytest.raises((probe.RunError, FixtureError, ValueError, TypeError, AttributeError)):
        _call(profile, trace, callbacks)
    assert "complete" not in [r["phase"] for r in _markers(trace)]
    assert calls.count("factory") <= 1 and calls.count("visitor") <= 1
    if defect in {"precharged-factory", "precharged-visitor", "context-tuple", "context-float",
                  "context-wrong", "provenance"}:
        assert "factory" not in calls
    if defect in {"factory-count", "integration-count", "factory-precharges-visitor",
                  "callback-overflow", "callback-bool", "spice-count", "missing-method",
                  "noncallable-method"}:
        assert "visitor" not in calls


def test_constructor_callbacks_may_reach_original_cap_without_claiming_zero(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, callbacks, _ = _injected(monkeypatch, profile, trace, defect="callback-limit")
    report = _call(profile, trace, callbacks)
    assert report["counts"]["acceleration_callbacks"] == 100000
    assert report["counts"]["integration_attempts"] == 0


@pytest.mark.parametrize("field,value", [
    ("schema", "other"), ("scope", "owner"), ("mode", "other"),
    ("kernel_path", "relative.bin"), ("kernel_path", "/invalid\0kernel"),
    ("kernel_sha256", "bad"), ("probe_sha256", "0" * 64),
    ("owner_fixture_sha256", "0" * 64), ("owner_auditor_sha256", "0" * 64),
    ("trajectory_sha256", "0" * 64), ("setup_auditor_sha256", "0" * 64),
    ("extra", "forbidden"),
])
def test_profile_and_all_source_pins_refuse_before_observation(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "unused.jsonl"
    calls, callbacks, _ = _injected(monkeypatch, profile, trace)
    profile[field] = value
    with pytest.raises((probe.RunError, ValueError, TypeError)):
        _call(profile, trace, callbacks)
    assert not trace.exists() and not calls


@pytest.mark.parametrize("raw", [b"{}", b"[]", b"{", b'{"x":NaN}',
                                  b'{"x":1,"x":2}', b"x" * 65537, "{}"])
def test_invalid_input_cannot_start_trace_or_native_work(tmp_path: Path, raw: object) -> None:
    started = time.monotonic()
    trace = tmp_path / "unused.jsonl"
    with pytest.raises((probe.RunError, ValueError, TypeError)):
        probe.probe(raw, trace, started_s=started, deadline_s=started + 45)
    assert not trace.exists()


@pytest.mark.parametrize("injection", ["none", "partial", "native-with-hooks"])
def test_injection_requires_complete_hooks_and_cannot_label_itself_native(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, injection: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "unused.jsonl"
    calls, callbacks, _ = _injected(monkeypatch, profile, trace)
    if injection == "none":
        callbacks = {}
    elif injection == "partial":
        callbacks.pop("factory")
    else:
        profile["mode"] = "native"
    with pytest.raises((probe.RunError, ValueError, TypeError)):
        _call(profile, trace, callbacks)
    assert not trace.exists() and not calls


def test_native_mode_requires_cold_process_before_calling_default_helpers(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    profile["mode"] = "native"
    kernel = ModuleType("tudatpy.kernel")
    kernel.__file__ = profile["kernel_path"]
    monkeypatch.setitem(sys.modules, "tudatpy.kernel", kernel)
    trace = tmp_path / "unused.jsonl"
    with pytest.raises((probe.RunError, ValueError), match="cold"):
        _call(profile, trace, {})
    assert not trace.exists()


@pytest.mark.parametrize("defect", ["missing", "origin", "hash"])
def test_loaded_identity_is_checked_before_any_owner_factory(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, callbacks, _ = _injected(monkeypatch, profile, trace)
    if defect == "missing":
        monkeypatch.delitem(sys.modules, "tudatpy.kernel")
    elif defect == "origin":
        sys.modules["tudatpy.kernel"].__file__ = str(tmp_path / "other.bin")
    else:
        Path(profile["kernel_path"]).write_bytes(b"changed identity")
    with pytest.raises((probe.RunError, ValueError)):
        _call(profile, trace, callbacks)
    assert "factory" not in calls and "complete" not in [m["phase"] for m in _markers(trace)]


def test_full_input_capacity_and_exclusive_trace(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, callbacks, _ = _injected(monkeypatch, profile, trace)
    raw = _raw(profile)
    raw += b" " * (65536 - len(raw))
    assert _call(profile, trace, callbacks, raw=raw)["status"] == "passed"
    before = trace.read_bytes()
    with pytest.raises(FileExistsError):
        _call(profile, trace, callbacks)
    assert trace.read_bytes() == before


@pytest.mark.parametrize("phase", ["bootstrap-ready", "complete"])
def test_visible_marker_with_failed_fsync_cannot_complete(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, callbacks, _ = _injected(monkeypatch, profile, trace)
    original = probe._sync

    def sync(path: Path) -> None:
        original(path)
        if _markers(path)[-1]["phase"] == phase:
            raise OSError("artificial marker fsync failed")

    monkeypatch.setattr(probe, "_sync", sync)
    with pytest.raises(OSError, match="fsync"):
        _call(profile, trace, callbacks)
    assert _markers(trace)[-1]["phase"] == phase


@pytest.mark.parametrize("start_offset,deadline_offset", [(1, 45), (-61, 45), (0, 46), (0, 0)])
def test_original_clock_cannot_be_refreshed_or_extended(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        start_offset: float, deadline_offset: float) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "unused.jsonl"
    _, callbacks, _ = _injected(monkeypatch, profile, trace)
    started = time.monotonic() + start_offset
    with pytest.raises((probe.RunError, ValueError)):
        probe.probe(_raw(profile), trace, started_s=started,
                    deadline_s=started + deadline_offset, **callbacks)
    assert not trace.exists()


def _fake_probe_command(source: Path, started: float, *, exit_code: int = 0,
                        stderr_bytes: int = 0, invalid_report: bool = False,
                        pad_report: bool = False, pad_trace: bool = False) -> list[str]:
    script = ("import pathlib,json,time,os,sys,hashlib\n"
              f"p=pathlib.Path({str(source)!r});x=json.loads(p.read_bytes());start={started!r}\n"
              f"scope={SCOPE!r};phases={PHASES!r}\n"
              "counts={'factory_attempts':1,'integration_attempts':0,'visitor_calls':1,"
              "'acceleration_callbacks':0,'spice_queries':0,'kernel_reads':0,'real_archive_reads':0,"
              "'optimizer_entries':0,'native_reported_function_evaluations':[]}\n"
              "r={'schema':'ariadna-owner-setup-report-v1','scope':scope,'mode':x['mode'],"
              "'status':'passed','physical_admission':'unavailable','kernel_path':x['kernel_path'],"
              "'kernel_sha256':x['kernel_sha256'],'probe_sha256':x['probe_sha256'],"
              "'setup_auditor_sha256':x['setup_auditor_sha256'],'context_checks':1,"
              "'provenance':{'producer_sha256':x['owner_fixture_sha256'],"
              "'auditor_sha256':x['owner_auditor_sha256'],'trajectory_sha256':x['trajectory_sha256']},"
              "'native_context':[53,53,8],"
              f"'arguments':{{'arc_id':'never-run','simulate':False,'selector':True,'schema':{SCHEMA!r}}},"
              f"'refusal':{{'type':'RuntimeError','message':{UNAVAILABLE!r}}},'counts':counts}}\n"
              "raw=(json.dumps(r,sort_keys=True,allow_nan=False)+'\\n').encode()\n"
              f"if {pad_report!r}:raw+=b' '*(65536-len(raw))\n"
              "digest=hashlib.sha256(raw).hexdigest()\n"
              "with (p.parent/'trace.jsonl').open('xb') as f:\n"
              " for i,phase in enumerate(phases):\n"
              "  m={'schema':'ariadna-owner-setup-marker-v1','scope':scope,'index':i,"
              "'phase':phase,'elapsed_s':time.monotonic()-start}\n"
              "  if i==7:m['report_sha256']=digest\n"
              "  line=(json.dumps(m)+'\\n').encode()\n"
              f"  if {pad_trace!r}:line=line[:-1]+b' '*(512-len(line))+b'\\n'\n"
              "  f.write(line);f.flush();os.fsync(f.fileno())\n"
              f"sys.stdout.buffer.write(b'invalid report' if {invalid_report!r} else raw)\n"
              f"sys.stderr.write('x'*{stderr_bytes});sys.exit({exit_code})\n")
    return [sys.executable, "-c", script]


@pytest.fixture
def artificial_workers(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, float, float]]:
    original = probe._worker_command
    calls: list[tuple[str, float, float]] = []

    def command(kind: str, source: Path, started: float, deadline: float) -> list[str]:
        calls.append((kind, started, deadline))
        return (_fake_probe_command(source, started) if kind == "probe"
                else original(kind, source, started, deadline))

    monkeypatch.setattr(probe, "_worker_command", command)
    return calls


def test_artificial_setup_report_passes_real_cold_stdlib_audit_and_outer_finalization(
        tmp_path: Path, artificial_workers: list[tuple[str, float, float]]) -> None:
    profile = _profile(tmp_path)
    directory = tmp_path / "once"
    started = time.monotonic() - 1
    report = probe.run(_raw(profile), directory, started_s=started)
    assert report["status"] == "passed", report
    assert report["physical_admission"] == "unavailable"
    assert report["finalization"] == "checked-after-fsync"
    assert artificial_workers[0] == ("probe", started, started + 45)
    assert artificial_workers[1][:2] == ("audit", started)
    assert artificial_workers[1][2] <= started + 55
    audit = json.loads((directory / "audit.json").read_bytes())
    assert audit["schema"] == "ariadna-owner-setup-audit-v1" and audit["status"] == "passed"
    assert audit["mode"] == "injected" and audit["markers_checked"] == 8
    assert audit["physical_admission"] == "unavailable"
    assert json.loads((directory / "producer.json").read_bytes())["counts"]["factory_attempts"] == 1
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(FileExistsError):
        probe.run(_raw(profile), directory)
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before


@pytest.mark.parametrize("exit_code,invalid_report", [(2, False), (0, True)])
def test_complete_trace_requires_successful_child_and_valid_report(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        exit_code: int, invalid_report: bool) -> None:
    profile = _profile(tmp_path)
    calls: list[str] = []

    def command(kind: str, source: Path, started: float, deadline: float) -> list[str]:
        calls.append(kind)
        return _fake_probe_command(source, started, exit_code=exit_code, invalid_report=invalid_report)

    monkeypatch.setattr(probe, "_worker_command", command)
    directory = tmp_path / "failed"
    result = probe.run(_raw(profile), directory)
    assert result["status"] == "failed" and calls == ["probe"]
    assert len(_markers(directory / "trace.jsonl")) == 8


def test_complete_full_input_report_trace_and_log_capacity(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    original = probe._worker_command

    def command(kind: str, source: Path, started: float, deadline: float) -> list[str]:
        return (_fake_probe_command(source, started, stderr_bytes=65536,
                                    pad_report=True, pad_trace=True)
                if kind == "probe" else original(kind, source, started, deadline))

    monkeypatch.setattr(probe, "_worker_command", command)
    raw = _raw(profile)
    raw += b" " * (65536 - len(raw))
    directory = tmp_path / "full-capacity"
    result = probe.run(raw, directory)
    assert result["status"] == "passed", result
    assert (directory / "input.json").stat().st_size == 65536
    assert (directory / "producer.json").stat().st_size == 65536
    assert (directory / "trace.jsonl").stat().st_size == 4096
    assert sum(p.stat().st_size for p in directory.glob("*.log")) == 65536
    assert result["structured_bytes"] == sum(p.stat().st_size for p in directory.iterdir()
                                             if p.suffix != ".log")


def test_log_overflow_stops_before_audit_and_retains_only_fixed_cap(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    monkeypatch.setattr(probe, "_worker_command", lambda kind, source, start, deadline:
                        _fake_probe_command(source, start, stderr_bytes=65537))
    directory = tmp_path / "logs"
    result = probe.run(_raw(profile), directory)
    assert result["status"] == "failed"
    assert sum(p.stat().st_size for p in directory.glob("*.log")) == 65536
    assert not (directory / "audit.json").exists()


def test_failed_child_preserves_and_accounts_partial_trace(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    monkeypatch.setattr(probe, "_worker_command", lambda kind, source, start, deadline:
                        _fake_probe_command(source, start, exit_code=2))
    directory = tmp_path / "partial"
    result = probe.run(_raw(profile), directory)
    assert result["status"] == "failed"
    assert result["structured_bytes"] == sum(p.stat().st_size for p in directory.iterdir()
                                             if p.suffix != ".log")
    assert (directory / "trace.jsonl").stat().st_size > 0
    assert not (directory / "audit.json").exists()


def test_oversized_trace_is_truncated_and_accounted_before_refusal(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)

    def command(kind: str, source: Path, started: float, deadline: float) -> list[str]:
        script = f"from pathlib import Path;Path({str(source.parent / 'trace.jsonl')!r}).write_bytes(b'x'*4097)"
        return [sys.executable, "-c", script]

    monkeypatch.setattr(probe, "_worker_command", command)
    directory = tmp_path / "oversized"
    result = probe.run(_raw(profile), directory)
    assert result["status"] == "failed"
    assert (directory / "trace.jsonl").read_bytes() == b"x" * 4096
    assert result["structured_bytes"] == sum(p.stat().st_size for p in directory.iterdir()
                                             if p.suffix != ".log")
    assert not (directory / "audit.json").exists()


def test_parent_post_fsync_deadline_cannot_be_promoted_to_success(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        artificial_workers: list[tuple[str, float, float]]) -> None:
    profile = _profile(tmp_path)
    started = time.monotonic()
    original = probe._sync

    def sync(path: Path) -> None:
        original(path)
        if path.name == "receipt.json":
            monkeypatch.setattr(probe, "_now", lambda: started + 60.1)

    monkeypatch.setattr(probe, "_sync", sync)
    directory = tmp_path / "late-finalization"
    result = probe.run(_raw(profile), directory, started_s=started)
    assert result["status"] == "failed" and result["finalization"] == "failed-after-fsync"
    assert json.loads((directory / "receipt.json").read_bytes())["finalization"] == "pending-after-fsync-observation"


def test_worker_flags_are_fixed_without_executing_native_command(tmp_path: Path) -> None:
    command = probe._worker_command("probe", tmp_path / "input.json", 100.0, 145.0)
    assert command[:3] == [sys.executable, "-m", "space_nav._owner_setup_probe"]
    assert "-I" not in command and "-B" not in command
    assert command[-2:] == ["100.0", "145.0"]


def test_independent_auditor_imports_no_producer_or_scientific_runtime() -> None:
    script = ("import sys\nimport space_nav._owner_setup_audit\n"
              "bad={'space_nav._owner_setup_probe','space_nav._owner_endpoint_fixture',"
              "'tudatpy','numpy','scipy','spiceypy'} & set(sys.modules)\nassert not bad,bad\n")
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script],
                            capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="outer group watchdog requires POSIX")
def test_outer_watchdog_rejects_visible_complete_with_stalled_observer_fsync(
        tmp_path: Path) -> None:
    from space_nav import _owner_endpoint_run as controls
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    stalled = tmp_path / "observer-stalled"
    script = ("import pathlib,sys,time,types\n"
              "from space_nav import _owner_setup_probe as p\n"
              "from space_nav._owner_endpoint_fixture import Budget\n"
              f"x={profile!r};trace=pathlib.Path({str(trace)!r});raw={_raw(profile)!r}\n"
              "k=types.ModuleType('tudatpy.kernel');k.__file__=x['kernel_path']\n"
              "sys.modules['tudatpy.kernel']=k\n"
              "original=p._sync\n"
              "def sync(path):\n original(path)\n if len(path.read_bytes().splitlines())==8:\n"
              f"  pathlib.Path({str(stalled)!r}).write_text('stalled');time.sleep(30)\n"
              "p._sync=sync\n"
              "class Owner:\n def _ariadna_original_endpoint(self,selector,schema):\n"
              f"  raise RuntimeError({UNAVAILABLE!r})\n"
              "start=time.monotonic()\n"
              "p.probe(raw,trace,started_s=start,deadline_s=start+45,"
              "prepare=lambda start:Budget(start),import_spice=lambda:object(),"
              "guard_spice=lambda budget,spice:None,context=lambda:[53,53,8],"
              f"provenance=lambda:{_provenance(profile)!r},factory=lambda arc,simulate,budget:Owner())\n")
    before = time.monotonic()
    with pytest.raises(controls.RunError, match="deadline|stalled"):
        controls._watch_worker([sys.executable, "-c", script], tmp_path / "producer.json",
                               tmp_path / "producer.stderr.log", before + 1.5,
                               controls._Evidence(tmp_path))
    assert time.monotonic() - before < 4
    assert stalled.read_text() == "stalled" and _markers(trace)[-1]["phase"] == "complete"


@pytest.mark.parametrize("defect", [None, "pending", "scope", "mode", "nonzero"])
def test_cold_supervisor_qualifies_only_matching_finalized_parent_and_cleans_descendants(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None) -> None:
    profile = _profile(tmp_path)
    descendant = tmp_path / "artificial-descendant.pid"
    heartbeat = tmp_path / "artificial-descendant-heartbeat"

    def command(source: Path, directory: Path, started: float) -> list[str]:
        report = {"schema": "ariadna-owner-setup-run-v1", "scope": SCOPE, "mode": "injected",
                  "status": "passed", "physical_admission": "unavailable",
                  "finalization": "checked-after-fsync"}
        if defect == "pending":
            report["finalization"] = "pending-after-fsync-observation"
        elif defect == "scope":
            report["scope"] = "wrong"
        elif defect == "mode":
            report["mode"] = "native"
        child_script = ("from pathlib import Path;import time\n"
                        f"p=Path({str(heartbeat)!r})\n"
                        "while True:p.write_text(str(time.monotonic()));time.sleep(.005)\n")
        script = ("import pathlib,json,os,subprocess,sys,time\n"
                  "assert os.getpid()==os.getpgrp()==os.getsid(0)\n"
                  f"child=subprocess.Popen([sys.executable,'-I','-B','-c',{child_script!r}],"
                  "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
                  f"pathlib.Path({str(descendant)!r}).write_text(str(child.pid))\n"
                  f"heartbeat=pathlib.Path({str(heartbeat)!r});cutoff=time.monotonic()+2\n"
                  "while not heartbeat.exists():\n assert time.monotonic()<cutoff;time.sleep(.001)\n"
                  f"print(json.dumps({report!r}),flush=True);sys.exit({2 if defect == 'nonzero' else 0})\n")
        return [sys.executable, "-c", script]

    monkeypatch.setattr(probe, "_parent_command", command)
    report = probe.run_isolated(_raw(profile), tmp_path / "supervised")
    assert report["schema"] == "ariadna-owner-setup-supervisor-v1"
    assert report["physical_admission"] == "unavailable"
    assert (report["status"] == "passed") is (defect is None)
    assert report["finalization"] == "checked-after-fsync"
    pid = int(descendant.read_text())
    try:
        first = heartbeat.read_bytes()
        time.sleep(.05)
        assert heartbeat.read_bytes() == first
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_cold_parent_stall_inherits_original_deadline_without_refresh(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    entered = tmp_path / "cold-parent-entered"

    def command(source: Path, directory: Path, started: float) -> list[str]:
        script = ("import pathlib,time,os\n"
                  "assert os.getpid()==os.getpgrp()==os.getsid(0)\n"
                  f"pathlib.Path({str(entered)!r}).write_text('entered');time.sleep(30)\n")
        return [sys.executable, "-c", script]

    monkeypatch.setattr(probe, "_parent_command", command)
    before = time.monotonic()
    report = probe.run_isolated(_raw(profile), tmp_path / "cold-stall", started_s=before - 59)
    assert time.monotonic() - before < 4
    assert entered.read_text() == "entered"
    assert report["status"] == "failed" and "deadline" in report["failure"]
    assert report["finalization"] == "failed-after-fsync"


def test_cold_parent_command_preserves_role_specific_flags(tmp_path: Path) -> None:
    command = probe._parent_command(tmp_path / "input.json", tmp_path / "packet", 100.0)
    assert command[:4] == [sys.executable, "-B", "-m", "space_nav._owner_setup_probe"]
    assert command[4:] == ["--parent", str(tmp_path / "input.json"), str(tmp_path / "packet"), "100.0"]
    assert "-I" not in command


def test_failed_report_fsync_cannot_create_success_observation_or_launch_audit(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    calls: list[str] = []
    original_command, original_sync = probe._worker_command, probe._sync

    def command(kind: str, source: Path, started: float, deadline: float) -> list[str]:
        calls.append(kind)
        return (_fake_probe_command(source, started) if kind == "probe"
                else original_command(kind, source, started, deadline))

    def sync(path: Path) -> None:
        original_sync(path)
        if path.name == "producer.json":
            raise OSError("artificial report fsync failure")

    monkeypatch.setattr(probe, "_worker_command", command)
    monkeypatch.setattr(probe, "_sync", sync)
    directory = tmp_path / "report-fsync-failed"
    result = probe.run(_raw(profile), directory)
    assert result["status"] == "failed" and "report fsync" in result["failure"]
    assert calls == ["probe"]
    assert not (directory / "observation.json").exists()
    assert not (directory / "audit.json").exists()
    assert _markers(directory / "trace.jsonl")[-1]["phase"] == "complete"


def test_report_fsync_finishing_after_producer_phase_cannot_launch_audit(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    calls: list[str] = []
    started = time.monotonic()
    original_command, original_sync = probe._worker_command, probe._sync

    def command(kind: str, source: Path, start: float, deadline: float) -> list[str]:
        calls.append(kind)
        return (_fake_probe_command(source, start) if kind == "probe"
                else original_command(kind, source, start, deadline))

    def sync(path: Path) -> None:
        original_sync(path)
        if path.name == "producer.json":
            monkeypatch.setattr(probe, "_now", lambda: started + 45.1)

    monkeypatch.setattr(probe, "_worker_command", command)
    monkeypatch.setattr(probe, "_sync", sync)
    directory = tmp_path / "report-fsync-late"
    result = probe.run(_raw(profile), directory, started_s=started)
    assert result["status"] == "failed" and "deadline" in result["failure"]
    assert calls == ["probe"]
    assert not (directory / "observation.json").exists()
    assert not (directory / "audit.json").exists()


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="outer group watchdog requires POSIX")
def test_outer_watchdog_stops_report_fsync_stall_before_observation_or_audit(
        tmp_path: Path) -> None:
    from space_nav import _owner_endpoint_run as controls
    profile = _profile(tmp_path)
    directory = tmp_path / "packet"
    stalled, audit_started = tmp_path / "report-fsync-stalled", tmp_path / "audit-started"
    started = time.monotonic()
    fake_command = _fake_probe_command(directory / "input.json", started)
    script = ("import pathlib,time,json,sys\n"
              "from space_nav import _owner_setup_probe as p\n"
              "original_command=p._worker_command;original_sync=p._sync\n"
              "def command(kind,source,start,deadline):\n"
              f" if kind=='probe':return {fake_command!r}\n"
              f" pathlib.Path({str(audit_started)!r}).write_text('audit-started')\n"
              " return original_command(kind,source,start,deadline)\n"
              "def sync(path):\n original_sync(path)\n if path.name=='producer.json':\n"
              f"  pathlib.Path({str(stalled)!r}).write_text('stalled');time.sleep(30)\n"
              "p._worker_command=command;p._sync=sync\n"
              f"p.run({_raw(profile)!r},pathlib.Path({str(directory)!r}),"
              f"started_s={started!r},inherited_group=True)\n")
    with pytest.raises(controls.RunError, match="deadline|stalled"):
        controls._watch_worker([sys.executable, "-I", "-B", "-c", script],
                               tmp_path / "producer.json", tmp_path / "producer.stderr.log",
                               started + 1.5, controls._Evidence(tmp_path))
    assert time.monotonic() - started < 4
    assert stalled.read_text() == "stalled" and not audit_started.exists()
    assert not (directory / "observation.json").exists()
    assert _markers(directory / "trace.jsonl")[-1]["phase"] == "complete"
