"""ADR0267 controls run fake subprocesses; never the proposed native packet."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import sys
import time

import pytest

from space_nav import _owner_endpoint_run as runner

RAW = json.dumps(runner._INPUT).encode()


def _command(value: object, *, code: int = 0, prefix: str = "") -> list[str]:
    raw = json.dumps(value)
    return [sys.executable, "-c", prefix + f"import sys;sys.stdout.write({raw!r});sys.exit({code})"]


def _producer() -> dict[str, object]:
    return {"schema": "ariadna-owner-fixture-v1", "status": "passed", "mode": "injected"}


def _audit() -> dict[str, object]:
    return {"schema": "ariadna-owner-audit-v1", "status": "passed", "mode": "injected",
            "physical_admission": "unavailable", "calls_checked": 8, "analytic_arcs_checked": 2}


@pytest.fixture
def fake_workers(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, float, float]]:
    calls: list[tuple[str, float, float]] = []

    def command(kind: str, source: Path, start: float, deadline: float) -> list[str]:
        calls.append((kind, start, deadline))
        return _command(_producer() if kind == "produce" else _audit())

    monkeypatch.setattr(runner, "_worker_command", command)
    return calls


def test_fake_pipeline_keeps_one_start_and_prefinal_receipt(
        tmp_path: Path, fake_workers: list[tuple[str, float, float]]) -> None:
    started = time.monotonic() - 2
    directory = tmp_path / "once"
    report = runner.run(RAW, directory, started_s=started)
    assert report["status"] == "passed"
    assert report["physical_admission"] == "unavailable"
    assert report["producer_mode"] == "injected"
    assert report["finalization"] == "checked-after-fsync"
    assert fake_workers[0] == ("produce", started, started + 45)
    assert fake_workers[1][0:2] == ("audit", started)
    assert fake_workers[1][2] <= started + 55
    retained = json.loads((directory / "receipt.json").read_bytes())
    assert retained["finalization"] == "pending-after-fsync-observation"
    assert report["structured_bytes"] == sum(p.stat().st_size for p in directory.iterdir()
                                             if p.suffix != ".log")
    assert report["log_bytes"] == 0
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(FileExistsError):
        runner.run(RAW, directory)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}


@pytest.mark.parametrize("raw", [b"x" * 65537, b'{"schema":NaN}', b'{"x":1,"x":2}',
                                    b'{"x":1e999}', b"[]", b"{", b"{}", "{}"])
def test_bad_input_refuses_before_namespace(tmp_path: Path, raw: object) -> None:
    with pytest.raises(runner.RunError):
        runner.run(raw, tmp_path / "unused")
    assert not (tmp_path / "unused").exists()


@pytest.mark.parametrize("started", [True, float("nan"), float("inf"), float("-inf")])
def test_bad_start_refuses_before_namespace(tmp_path: Path, started: float) -> None:
    with pytest.raises(runner.RunError, match="parent start"):
        runner.run(RAW, tmp_path / "unused", started_s=started)
    assert not (tmp_path / "unused").exists()


def test_expired_or_future_start_cannot_refresh_budget(tmp_path: Path) -> None:
    for started in (time.monotonic() - 61, time.monotonic() + 5):
        with pytest.raises(runner.RunError):
            runner.run(RAW, tmp_path / "unused", started_s=started)
    assert not (tmp_path / "unused").exists()


def test_full_input_capacity_keeps_original_bytes(
        tmp_path: Path, fake_workers: list[tuple[str, float, float]]) -> None:
    raw = RAW + b" " * (65536 - len(RAW))
    directory = tmp_path / "capacity"
    assert runner.run(raw, directory)["status"] == "passed"
    assert (directory / "input.json").read_bytes() == raw


def test_partial_or_failed_producer_never_launches_audit(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def command(kind: str, *args: object) -> list[str]:
        calls.append(kind)
        return _command({"status": "failed", "failure": "first injected defect"}, code=2)

    monkeypatch.setattr(runner, "_worker_command", command)
    report = runner.run(RAW, tmp_path / "failed")
    assert calls == ["produce"]
    assert report["status"] == "failed"
    assert "first injected defect" in report["failure"]
    assert not (tmp_path / "failed" / "audit.json").exists()


@pytest.mark.parametrize("field,value", [("mode", "native"), ("calls_checked", True),
                                           ("analytic_arcs_checked", 3),
                                           ("physical_admission", "passed")])
def test_audit_summary_cannot_change_scope_or_counts(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object) -> None:
    audit = _audit()
    audit[field] = value
    monkeypatch.setattr(runner, "_worker_command", lambda kind, *args: _command(
        _producer() if kind == "produce" else audit))
    report = runner.run(RAW, tmp_path / "forged")
    assert report["status"] == "failed"
    assert "audit contract mismatch" in report["failure"]


def test_log_capacity_is_shared_across_workers(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def command(kind: str, *args: object) -> list[str]:
        prefix = "import sys;sys.stderr.write('x'*40000);sys.stderr.flush();"
        return _command(_producer() if kind == "produce" else _audit(), prefix=prefix)

    monkeypatch.setattr(runner, "_worker_command", command)
    directory = tmp_path / "logs"
    report = runner.run(RAW, directory)
    assert report["status"] == "failed"
    assert "log byte cap" in report["failure"]
    assert report["log_bytes"] == 65536
    assert sum(p.stat().st_size for p in directory.glob("*.log")) == 65536


def test_producer_stdout_is_streamed_to_its_partition(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_worker_command", lambda *args: [sys.executable, "-c",
                       "import sys;sys.stdout.write('x'*(1024*1024+8192));sys.stdout.flush()"])
    directory = tmp_path / "oversize"
    report = runner.run(RAW, directory)
    assert report["status"] == "failed"
    assert "structured evidence byte cap" in report["failure"]
    assert (directory / "producer.json").stat().st_size == 1024 * 1024
    assert (directory / "receipt.json").exists()


def test_full_evidence_budget_reserves_durable_receipt(tmp_path: Path) -> None:
    evidence = runner._Evidence(tmp_path)
    evidence.structured = runner.EVIDENCE_BYTES - runner.REPORT_BYTES
    with pytest.raises(runner.RunError, match="structured"):
        evidence.write(tmp_path / "producer.json", b"x")
    evidence.write(tmp_path / "receipt.json", b"r" * runner.REPORT_BYTES)
    assert evidence.structured == runner.EVIDENCE_BYTES
    with pytest.raises(runner.RunError, match="structured"):
        evidence.write(tmp_path / "receipt.json", b"x")


def test_post_fsync_failure_preserves_prefinal_record(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        fake_workers: list[tuple[str, float, float]]) -> None:
    started = time.monotonic()
    real_sync = runner._sync

    def sync(path: Path) -> None:
        real_sync(path)
        if path.name == "receipt.json":
            monkeypatch.setattr(runner, "_now", lambda: started + 60.1)

    monkeypatch.setattr(runner, "_sync", sync)
    directory = tmp_path / "late"
    report = runner.run(RAW, directory, started_s=started)
    assert report["status"] == "failed" and report["finalization"] == "failed-after-fsync"
    assert json.loads((directory / "receipt.json").read_bytes())["status"] == "passed"


def test_bad_clock_and_backward_clock_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in (float("nan"), float("inf"), True):
        monkeypatch.setattr(runner.time, "monotonic", lambda: value)
        with pytest.raises(runner.RunError, match="finite"):
            runner._now()
    monkeypatch.setattr(runner, "_now", lambda: 2.0)
    with pytest.raises(runner.RunError, match="backwards"):
        runner._check(5.0, 3.0)


@pytest.mark.parametrize("closed_pipes", [False, True])
def test_watchdog_bounds_a_stalled_fake_cold_parent_or_worker(
        tmp_path: Path, closed_pipes: bool) -> None:
    evidence = runner._Evidence(tmp_path)
    command = [sys.executable, "-c", "import os,time;" +
               ("os.close(1);os.close(2);" if closed_pipes else "") + "time.sleep(30)"]
    before = time.monotonic()
    with pytest.raises(runner.RunError, match="deadline|stalled"):
        runner._watch_worker(command, tmp_path / "producer.json", tmp_path / "producer.stderr.log",
                             before + 0.2, evidence)
    assert time.monotonic() - before < 3


@pytest.mark.skipif(not hasattr(os, "fork"), reason="process-group fixture requires POSIX fork")
def test_dead_leader_does_not_leave_a_grandchild_running(tmp_path: Path) -> None:
    heartbeat = tmp_path / "heartbeat"
    script = ("import os,time,pathlib\n"
              "pid=os.fork()\n"
              "if pid:\n print(pid,flush=True);os._exit(0)\n"
              f"p=pathlib.Path({str(heartbeat)!r})\n"
              "while True:\n p.write_text(str(time.monotonic()));time.sleep(.01)\n")
    evidence = runner._Evidence(tmp_path)
    try:
        with pytest.raises(runner.RunError, match="deadline"):
            runner._watch_worker([sys.executable, "-c", script], tmp_path / "producer.json",
                                 tmp_path / "producer.stderr.log", time.monotonic() + .3, evidence)
        assert heartbeat.exists()
        first = heartbeat.read_bytes()
        time.sleep(.05)
        assert heartbeat.read_bytes() == first
    finally:
        output = tmp_path / "producer.json"
        if output.exists():
            try:
                os.kill(int(output.read_text().strip()), signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_audit_guard_blocks_new_producer_before_import(tmp_path: Path) -> None:
    code = ("from space_nav._owner_endpoint_run import _install_audit_guard;"
            "_install_audit_guard();import space_nav._owner_endpoint_fixture")
    child = __import__("subprocess").run([sys.executable, "-c", code], capture_output=True, timeout=5)
    assert child.returncode != 0
    assert b"independent auditor forbids owner producer" in child.stderr


def test_direct_bad_producer_input_is_rejected_without_native_import(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_bytes(b"{}")
    command = runner._worker_command("produce", source, time.monotonic(), time.monotonic() + 10)
    child = __import__("subprocess").run(command, capture_output=True, timeout=5)
    assert child.returncode == 2 and b"fixed input mismatch" in child.stderr
    assert b"tudat" not in child.stderr.lower()


def test_injected_owner_packet_passes_actual_cold_independent_audit(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from space_nav._owner_endpoint_fixture import Budget, produce
    from test_owner_endpoint_fixture import Clock, _factory
    packet = produce(factory=_factory, budget=Budget(0.0, Clock()))
    assert packet["status"] == "passed"
    original = runner._worker_command

    def command(kind: str, source: Path, started: float, deadline: float) -> list[str]:
        return (_command(packet) if kind == "produce"
                else original(kind, source, started, deadline))

    monkeypatch.setattr(runner, "_worker_command", command)
    directory = tmp_path / "cold-artificial"
    report = runner.run(RAW, directory)
    assert report["status"] == "passed", report["failure"]
    audit = json.loads((directory / "audit.json").read_bytes())
    assert audit["calls_checked"] == 8 and audit["analytic_arcs_checked"] == 2
    assert audit["mode"] == "injected" and audit["physical_admission"] == "unavailable"


def _parent_script(source: Path, directory: Path, started: float, extra: str = "") -> list[str]:
    prefix = ("import sys,json,pathlib,time\n"
              "from space_nav import _owner_endpoint_run as r\n"
              f"p={_producer()!r};a={_audit()!r}\n"
              "r._worker_command=lambda kind,*args:[sys.executable,'-c',"
              "'import sys;sys.stdout.write('+repr(json.dumps(p if kind==\"produce\" else a))+')']\n")
    return [sys.executable, "-c", prefix + extra +
            f"sys.exit(r.main(['--parent',{str(source)!r},{str(directory)!r},{repr(started)!r}]))"]


def test_cold_parent_and_fake_workers_inherit_one_supervised_group(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_parent_command", _parent_script)
    directory = tmp_path / "outer"
    report = runner.run_isolated(RAW, directory)
    assert report["status"] == "passed", report["failure"]
    assert report["parent"]["producer_mode"] == "injected"
    assert report["finalization"] == "checked-after-fsync"
    assert report["parent"]["finalization"] == "checked-after-fsync"
    assert json.loads((directory / "receipt.json").read_bytes())["finalization"] == "pending-after-fsync-observation"
    assert sum(p.stat().st_size for p in directory.rglob("*") if p.is_file()) < 2 * 1024 * 1024
    with pytest.raises(FileExistsError):
        runner.run_isolated(RAW, directory)


@pytest.mark.parametrize("stall", ["receipt-fsync", "worker-stream-write"])
def test_outer_watchdog_stops_actual_cold_parent_and_live_inherited_descendants(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stall: str) -> None:
    directory = tmp_path / stall
    marker, heartbeat = directory / "marker", directory / "heartbeat"
    if stall == "receipt-fsync":
        extra = ("original=r._sync\n"
                 "def sync(path):\n"
                 " original(path)\n"
                 f" if path.name=='receipt.json':pathlib.Path({str(marker)!r}).write_text('stalled');time.sleep(30)\n"
                 "r._sync=sync\n")
    else:
        payload = ("import os,time,pathlib\n"
                   f"p=pathlib.Path({str(heartbeat)!r})\n"
                   "pid=os.fork()\n"
                   "if pid:\n print('{',flush=True);time.sleep(30)\n"
                   "else:\n"
                   " while True:\n  p.write_text(str(time.monotonic()));time.sleep(.01)\n")
        extra = (f"payload={payload!r}\n"
                 "r._worker_command=lambda *args:[sys.executable,'-c',payload]\n"
                 "original=r._Evidence.write\n"
                 "def write(self,path,data):\n"
                 f" if path.name=='producer.json' and data:pathlib.Path({str(marker)!r}).write_text('stalled');time.sleep(30)\n"
                 " return original(self,path,data)\n"
                 "r._Evidence.write=write\n")
    monkeypatch.setattr(runner, "_parent_command", lambda s, d, t: _parent_script(s, d, t, extra))
    original_watch = runner._watch_worker

    def short_watch(command: list[str], output: Path, errors: Path, deadline: float,
                    evidence: runner._Evidence, **kwargs: object) -> dict[str, object]:
        return original_watch(command, output, errors, min(deadline, time.monotonic() + 1.5), evidence,
                              **kwargs)

    monkeypatch.setattr(runner, "_watch_worker", short_watch)
    before = time.monotonic()
    report = runner.run_isolated(RAW, directory)
    assert report["status"] == "failed" and "deadline" in report["failure"]
    assert time.monotonic() - before < 4
    assert marker.read_text() == "stalled"
    if stall == "receipt-fsync":
        assert (directory / "packet" / "receipt.json").exists()
    else:
        first = heartbeat.read_bytes()
        time.sleep(.05)
        assert heartbeat.read_bytes() == first
