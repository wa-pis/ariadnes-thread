"""ADR0270 qualification uses injected imports and artificial subprocesses only."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import ModuleType

import pytest

from space_nav import _import_probe as probe

PHASES = ("bootstrap-ready", "guards-ready", "native-import-enter",
          "native-import-return", "spice-guard-ready", "complete")


def _profile(tmp_path: Path) -> dict[str, str]:
    kernel = tmp_path / "artificial-kernel.bin"
    kernel.write_bytes(b"injected kernel identity; not a native library")
    return {"schema": "ariadna-import-input-v1", "scope": "import-only", "mode": "injected",
            "kernel_path": str(kernel), "kernel_sha256": hashlib.sha256(kernel.read_bytes()).hexdigest(),
            "probe_sha256": hashlib.sha256(Path(probe.__file__).read_bytes()).hexdigest()}


def _raw(profile: dict[str, str]) -> bytes:
    return json.dumps(profile).encode()


def _markers(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def _injected(monkeypatch: pytest.MonkeyPatch, profile: dict[str, str], trace: Path
              ) -> tuple[list[str], dict[str, Callable[..., object]]]:
    calls: list[str] = []
    budget, spice = object(), object()
    kernel = ModuleType("tudatpy.kernel")
    kernel.__file__ = profile["kernel_path"]

    def forbidden(name: str) -> object:
        pytest.fail("probe must not inspect native context: " + name)

    kernel.__getattr__ = forbidden
    monkeypatch.setitem(sys.modules, "tudatpy.kernel", kernel)

    def prepare(started: float) -> object:
        assert type(started) is float
        assert [m["phase"] for m in _markers(trace)] == ["bootstrap-ready"]
        calls.append("prepare")
        return budget

    def import_spice() -> object:
        assert _markers(trace)[-1]["phase"] == "native-import-enter"
        calls.append("import")
        return spice

    def guard_spice(actual_budget: object, actual_spice: object) -> None:
        assert actual_budget is budget and actual_spice is spice
        assert _markers(trace)[-1]["phase"] == "native-import-return"
        calls.append("guard")

    return calls, {"prepare": prepare, "import_spice": import_spice, "guard_spice": guard_spice}


def test_injected_import_has_fixed_durable_order_and_loaded_identity(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, callbacks = _injected(monkeypatch, profile, trace)
    synced: list[str] = []
    original = probe._sync

    def sync(path: Path) -> None:
        original(path)
        synced.append(str(_markers(path)[-1]["phase"]))

    monkeypatch.setattr(probe, "_sync", sync)
    started = time.monotonic()
    assert probe.probe(_raw(profile), trace, started_s=started, deadline_s=started + 45,
                       **callbacks) is None
    records = _markers(trace)
    assert calls == ["prepare", "import", "guard"]
    assert synced == list(PHASES)
    assert [r["phase"] for r in records] == list(PHASES)
    assert [r["index"] for r in records] == list(range(6))
    assert all(r["schema"] == "ariadna-import-marker-v1" and r["scope"] == "import-only"
               for r in records)
    assert all(0 <= r["elapsed_s"] < 45 for r in records)
    assert [r["elapsed_s"] for r in records] == sorted(r["elapsed_s"] for r in records)
    assert records[-1]["kernel_path"] == profile["kernel_path"]
    assert records[-1]["kernel_sha256"] == profile["kernel_sha256"]
    assert all(len(line) <= 512 for line in trace.read_bytes().splitlines(keepends=True))
    assert trace.stat().st_size <= 4096


@pytest.mark.parametrize("field,value", [
    ("schema", "other"), ("scope", "owner"), ("mode", "other"),
    ("kernel_path", "relative.bin"), ("kernel_sha256", "bad"),
    ("probe_sha256", "0" * 64), ("extra", "forbidden"),
])
def test_bad_profile_is_refused_before_observation(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "unused.jsonl"
    _, callbacks = _injected(monkeypatch, profile, trace)
    profile[field] = value
    started = time.monotonic()
    with pytest.raises((probe.RunError, ValueError)):
        probe.probe(_raw(profile), trace, started_s=started, deadline_s=started + 45, **callbacks)
    assert not trace.exists()


@pytest.mark.parametrize("raw", [b"{}", b"[]", b"{", b'{"x":NaN}',
                                  b'{"x":1,"x":2}', b"x" * 65537, "{}"])
def test_bad_input_is_refused_before_trace_or_import(tmp_path: Path, raw: object) -> None:
    trace = tmp_path / "unused.jsonl"
    started = time.monotonic()
    with pytest.raises((probe.RunError, ValueError, TypeError)):
        probe.probe(raw, trace, started_s=started, deadline_s=started + 45)
    assert not trace.exists()


def test_input_full_capacity_and_fresh_trace(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    _, callbacks = _injected(monkeypatch, profile, trace)
    raw = _raw(profile)
    raw += b" " * (65536 - len(raw))
    started = time.monotonic()
    probe.probe(raw, trace, started_s=started, deadline_s=started + 45, **callbacks)
    before = trace.read_bytes()
    with pytest.raises(FileExistsError):
        probe.probe(raw, trace, started_s=started, deadline_s=started + 45, **callbacks)
    assert trace.read_bytes() == before


@pytest.mark.parametrize("injection", ["none", "partial", "native-with-injection"])
def test_partial_or_mislabeled_injection_cannot_start_native_path(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, injection: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "unused.jsonl"
    _, callbacks = _injected(monkeypatch, profile, trace)
    if injection == "none":
        callbacks = {}
    elif injection == "partial":
        callbacks.pop("guard_spice")
    else:
        profile["mode"] = "native"
    started = time.monotonic()
    with pytest.raises((probe.RunError, ValueError)):
        probe.probe(_raw(profile), trace, started_s=started, deadline_s=started + 45, **callbacks)
    assert not trace.exists()


@pytest.mark.parametrize("defect", ["missing", "origin", "hash"])
def test_loaded_kernel_identity_cannot_be_fabricated_or_reimported(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, callbacks = _injected(monkeypatch, profile, trace)
    if defect == "missing":
        monkeypatch.delitem(sys.modules, "tudatpy.kernel")
    elif defect == "origin":
        sys.modules["tudatpy.kernel"].__file__ = str(tmp_path / "other.bin")
    else:
        Path(profile["kernel_path"]).write_bytes(b"changed artificial identity")
    started = time.monotonic()
    with pytest.raises((probe.RunError, ValueError)):
        probe.probe(_raw(profile), trace, started_s=started, deadline_s=started + 45, **callbacks)
    assert calls == ["prepare", "import", "guard"]
    assert "complete" not in [r["phase"] for r in _markers(trace)]


@pytest.mark.parametrize("failure_phase", ["bootstrap-ready", "complete"])
def test_visible_marker_does_not_prove_fsync_completed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_phase: str) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    calls, callbacks = _injected(monkeypatch, profile, trace)
    original = probe._sync

    def fail_sync(path: Path) -> None:
        original(path)
        if _markers(path)[-1]["phase"] == failure_phase:
            raise OSError("injected marker fsync failure")

    monkeypatch.setattr(probe, "_sync", fail_sync)
    started = time.monotonic()
    with pytest.raises(OSError, match="fsync"):
        probe.probe(_raw(profile), trace, started_s=started, deadline_s=started + 45, **callbacks)
    assert _markers(trace)[-1]["phase"] == failure_phase
    assert calls == ([] if failure_phase == "bootstrap-ready" else ["prepare", "import", "guard"])


@pytest.mark.parametrize("started_offset,deadline_offset", [(1, 45), (-61, 45), (0, 46), (0, 0)])
def test_inherited_clock_cannot_refresh_or_extend_phase(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        started_offset: float, deadline_offset: float) -> None:
    profile = _profile(tmp_path)
    trace = tmp_path / "unused.jsonl"
    _, callbacks = _injected(monkeypatch, profile, trace)
    now = time.monotonic()
    started = now + started_offset
    with pytest.raises((probe.RunError, ValueError)):
        probe.probe(_raw(profile), trace, started_s=started,
                    deadline_s=started + deadline_offset, **callbacks)
    assert not trace.exists()


def _fake_probe_command(source: Path, started: float, *, exit_code: int = 0,
                        stdout: str = "", stderr_bytes: int = 0) -> list[str]:
    script = ("import pathlib,json,time,os,sys\n"
              f"p=pathlib.Path({str(source)!r});x=json.loads(p.read_bytes());start={started!r}\n"
              f"phases={PHASES!r}\n"
              "with (p.parent/'trace.jsonl').open('xb') as f:\n"
              " for i,phase in enumerate(phases):\n"
              "  m={'schema':'ariadna-import-marker-v1','scope':'import-only',"
              "'index':i,'phase':phase,'elapsed_s':time.monotonic()-start}\n"
              "  if i==5:m.update(kernel_path=x['kernel_path'],kernel_sha256=x['kernel_sha256'])\n"
              "  f.write((json.dumps(m)+'\\n').encode());f.flush();os.fsync(f.fileno())\n"
              f"sys.stdout.write({stdout!r});sys.stderr.write('x'*{stderr_bytes});"
              f"sys.exit({exit_code})\n")
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


def test_artificial_trace_passes_real_cold_stdlib_audit_and_parent_finalization(
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
    assert (directory / "producer.json").read_bytes() == b""
    audit = json.loads((directory / "audit.json").read_bytes())
    assert audit["schema"] == "ariadna-import-audit-v1" and audit["status"] == "passed"
    assert audit["mode"] == "injected" and audit["markers_checked"] == 6
    assert audit["physical_admission"] == "unavailable"
    assert sum(p.stat().st_size for p in directory.iterdir()) < 2 * 1024 * 1024
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(FileExistsError):
        probe.run(_raw(profile), directory)
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before


@pytest.mark.parametrize("exit_code,stdout", [(2, ""), (0, "forged scientific result")])
def test_complete_trace_with_failed_child_or_unexpected_stdout_cannot_pass(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int, stdout: str) -> None:
    profile = _profile(tmp_path)
    calls: list[str] = []

    def command(kind: str, source: Path, started: float, deadline: float) -> list[str]:
        calls.append(kind)
        return _fake_probe_command(source, started, exit_code=exit_code, stdout=stdout)

    monkeypatch.setattr(probe, "_worker_command", command)
    directory = tmp_path / "failed"
    report = probe.run(_raw(profile), directory)
    assert report["status"] == "failed" and calls == ["probe"]
    assert len(_markers(directory / "trace.jsonl")) == 6


def test_log_overflow_stops_before_audit_and_retains_fixed_cap(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    monkeypatch.setattr(probe, "_worker_command", lambda kind, source, start, deadline:
                        _fake_probe_command(source, start, stderr_bytes=65537))
    directory = tmp_path / "logs"
    report = probe.run(_raw(profile), directory)
    assert report["status"] == "failed"
    assert sum(p.stat().st_size for p in directory.glob("*.log")) == 65536
    assert not (directory / "audit.json").exists()


def test_proposed_worker_uses_fixed_module_flags_without_executing_it(tmp_path: Path) -> None:
    command = probe._worker_command("probe", tmp_path / "input.json", 100.0, 145.0)
    assert command[:3] == [sys.executable, "-m", "space_nav._import_probe"]
    assert "-I" not in command and "-B" not in command
    assert command[-2:] == ["100.0", "145.0"]


def test_independent_auditor_imports_no_producer_or_scientific_runtime() -> None:
    script = ("import sys\n"
              "import space_nav._import_probe_audit\n"
              "bad={'space_nav._import_probe','space_nav._owner_endpoint_fixture',"
              "'tudatpy','numpy','scipy','spiceypy'} & set(sys.modules)\n"
              "assert not bad,bad\n")
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script],
                            capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not hasattr(os, "killpg"), reason="outer group watchdog requires POSIX")
def test_outer_watchdog_rejects_complete_trace_with_stalled_observer_fsync(
        tmp_path: Path) -> None:
    from space_nav import _owner_endpoint_run as controls
    profile = _profile(tmp_path)
    trace = tmp_path / "trace.jsonl"
    stall = tmp_path / "observer-stalled"
    script = ("import pathlib,sys,time,types\n"
              "from space_nav import _import_probe as p\n"
              f"x={profile!r};trace=pathlib.Path({str(trace)!r});raw={_raw(profile)!r}\n"
              "k=types.ModuleType('tudatpy.kernel');k.__file__=x['kernel_path']\n"
              "sys.modules['tudatpy.kernel']=k\n"
              "original=p._sync\n"
              "def sync(path):\n"
              " original(path)\n"
              " if len(path.read_bytes().splitlines())==6:\n"
              f"  pathlib.Path({str(stall)!r}).write_text('stalled');time.sleep(30)\n"
              "p._sync=sync\n"
              "start=time.monotonic()\n"
              "p.probe(raw,trace,started_s=start,deadline_s=start+45,"
              "prepare=lambda start:object(),import_spice=lambda:object(),"
              "guard_spice=lambda budget,spice:None)\n")
    before = time.monotonic()
    with pytest.raises(controls.RunError, match="deadline|stalled"):
        controls._watch_worker([sys.executable, "-c", script], tmp_path / "producer.json",
                               tmp_path / "producer.stderr.log", before + 1.5,
                               controls._Evidence(tmp_path))
    assert time.monotonic() - before < 4
    assert stall.read_text() == "stalled"
    assert _markers(trace)[-1]["phase"] == "complete"


def test_failed_probe_still_accounts_partial_trace(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)
    monkeypatch.setattr(probe, "_worker_command", lambda kind, source, start, deadline:
                        _fake_probe_command(source, start, exit_code=2))
    directory = tmp_path / "partial-accounting"
    report = probe.run(_raw(profile), directory)
    assert report["status"] == "failed"
    retained_structured = sum(p.stat().st_size for p in directory.iterdir() if p.suffix != ".log")
    assert report["structured_bytes"] == retained_structured
    assert (directory / "trace.jsonl").stat().st_size > 0
    assert not (directory / "audit.json").exists()


def test_oversized_trace_retains_and_accounts_only_fixed_prefix(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _profile(tmp_path)

    def command(kind: str, source: Path, start: float, deadline: float) -> list[str]:
        trace = source.parent / "trace.jsonl"
        script = f"from pathlib import Path;Path({str(trace)!r}).write_bytes(b'x'*4097)"
        return [sys.executable, "-c", script]

    monkeypatch.setattr(probe, "_worker_command", command)
    directory = tmp_path / "oversized"
    report = probe.run(_raw(profile), directory)
    assert report["status"] == "failed"
    assert (directory / "trace.jsonl").read_bytes() == b"x" * 4096
    assert report["structured_bytes"] == sum(p.stat().st_size for p in directory.iterdir()
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
    report = probe.run(_raw(profile), directory, started_s=started)
    assert report["status"] == "failed"
    assert report["finalization"] == "failed-after-fsync"
    assert json.loads((directory / "receipt.json").read_bytes())["finalization"] == "pending-after-fsync-observation"
