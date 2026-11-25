"""F10 process limits use fabricated summaries, never a native producer."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import sys
import time

import pytest

from space_nav import _realized_clock_run as runner


def _summary(status: str = "passed") -> dict[str, object]:
    return {"schema": "ariadna-realized-clock-check-v1", "structural_status": "valid",
            "status": status, "gates": {}, "derived": {}, "first_nonpass": None,
            "scientific_admission": "unavailable", "physical_admission": "unavailable"}


def _command(packet: object, *, code: int = 0, prefix: str = "") -> list[str]:
    raw = json.dumps(packet)
    return [sys.executable, "-c", prefix +
            f"import sys; sys.stdout.write({raw!r}); sys.exit({code})"]


@pytest.fixture
def fake_worker(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, float]]:
    calls: list[tuple[Path, float]] = []

    def command(source: Path, deadline_s: float) -> list[str]:
        calls.append((source, deadline_s))
        return _command(_summary())

    monkeypatch.setattr(runner, "_worker_command", command)
    return calls


def test_isolated_success_retains_prefinal_record_and_postfsync_observation(
        tmp_path: Path, fake_worker: list[tuple[Path, float]]) -> None:
    raw = b'{"fabricated":true}'
    directory = tmp_path / "once"
    report = runner.run(raw, directory)
    assert report["status"] == "passed"
    assert report["result"] == _summary()
    assert report["physical_admission"] == "unavailable"
    assert report["finalization"] == "checked-after-fsync"
    retained = json.loads((directory / "report.json").read_bytes())
    assert retained["status"] == "passed"
    assert retained["finalization"] == "pending-parent-check"
    assert "elapsed_s" not in retained
    assert (directory / "input.json").read_bytes() == raw
    assert len(fake_worker) == 1
    assert report["evidence_bytes"] == sum(path.stat().st_size for path in directory.iterdir())
    assert report["evidence_bytes"] <= 2 * 1024 * 1024


@pytest.mark.parametrize("status", ["failed", "unavailable", "inconclusive"])
def test_completed_diagnostic_is_not_a_physical_success(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    monkeypatch.setattr(runner, "_worker_command", lambda source, deadline: _command(_summary(status)))
    report = runner.run(b"{}", tmp_path / status)
    assert report["status"] == "passed"
    assert report["result"]["status"] == status
    assert report["physical_admission"] == "unavailable"


@pytest.mark.parametrize("raw", [b"x" * (65536 + 1), "{}", bytearray(b"{}")])
def test_input_type_and_capacity_fail_before_directory_or_decode(
        tmp_path: Path, raw: object) -> None:
    directory = tmp_path / "no-work"
    with pytest.raises(runner.RunError, match="64KiB"):
        runner.run(raw, directory)
    assert not directory.exists()


@pytest.mark.parametrize("started", [True, float("nan"), float("inf"), float("-inf")])
def test_invalid_parent_clock_is_not_an_execution_request(tmp_path: Path, started: float) -> None:
    with pytest.raises(runner.RunError, match="parent start"):
        runner.run(b"{}", tmp_path / "unused", started_s=started)
    assert not (tmp_path / "unused").exists()


def test_startup_consumes_the_inherited_clock(
        tmp_path: Path, fake_worker: list[tuple[Path, float]]) -> None:
    started = time.monotonic() - 5.0
    report = runner.run(b"{}", tmp_path / "started", started_s=started)
    assert fake_worker[0][1] == started + 15.0
    assert report["startup_elapsed_s"] >= 5.0
    with pytest.raises(runner.RunError, match="deadline"):
        runner.run(b"{}", tmp_path / "expired", started_s=time.monotonic() - 15.1)
    assert not (tmp_path / "expired").exists()


def test_future_start_is_refused(tmp_path: Path) -> None:
    with pytest.raises(runner.RunError, match="parent start"):
        runner.run(b"{}", tmp_path / "future", started_s=time.monotonic() + 100)


def test_existing_namespace_and_failed_namespace_are_not_reused(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "failed"
    monkeypatch.setattr(runner, "_worker_command", lambda source, deadline: _command(
        {"status": "failed", "error": "first fabricated defect"}, code=2))
    report = runner.run(b"{}", directory)
    assert report["status"] == "failed"
    assert "first fabricated defect" in report["failure"]
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    with pytest.raises(FileExistsError):
        runner.run(b"changed", directory)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before


def test_worker_contract_does_not_accept_physical_admission(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet = _summary()
    packet["physical_admission"] = "passed"
    monkeypatch.setattr(runner, "_worker_command", lambda source, deadline: _command(packet))
    report = runner.run(b"{}", tmp_path / "forged")
    assert report["status"] == "failed"
    assert "contract mismatch" in report["failure"]


def test_stalled_worker_uses_remaining_parent_time_and_retains_partials(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_worker_command", lambda source, deadline: [
        sys.executable, "-c", "import time; time.sleep(30)"])
    before = time.monotonic()
    report = runner.run(b"{}", tmp_path / "stalled", started_s=before - 14.8)
    assert time.monotonic() - before < 3.0
    assert report["status"] == "failed"
    assert "deadline" in report["failure"]
    assert (tmp_path / "stalled" / "input.json").read_bytes() == b"{}"
    assert (tmp_path / "stalled" / "report.json").exists()


def test_stderr_and_input_share_the_combined_evidence_budget(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_worker_command", lambda source, deadline: [
        sys.executable, "-c", "import sys; sys.stderr.write('x'*(2*1024*1024)); sys.stderr.flush()"])
    directory = tmp_path / "logs"
    report = runner.run(b"{}", directory)
    assert report["status"] == "failed"
    assert "byte cap" in report["failure"]
    assert sum(path.stat().st_size for path in directory.iterdir()) <= 2 * 1024 * 1024
    assert (directory / "worker.stderr.log").stat().st_size > 0


@pytest.mark.parametrize("prior_failure", [False, True])
def test_postfsync_deadline_failure_never_rewrites_retained_record_or_first_failure(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prior_failure: bool) -> None:
    packet = {"error": "original defect"} if prior_failure else _summary()
    monkeypatch.setattr(runner, "_worker_command", lambda source, deadline: _command(
        packet, code=2 if prior_failure else 0))
    real_sync = runner._sync
    calls = 0
    started = time.monotonic()

    def delayed_sync(path: Path) -> None:
        nonlocal calls
        real_sync(path)
        calls += 1
        if calls == 2:
            monkeypatch.setattr(runner, "_now", lambda: started + 16.0)

    monkeypatch.setattr(runner, "_sync", delayed_sync)
    directory = tmp_path / "finalization"
    report = runner.run(b"{}", directory, started_s=started)
    retained = json.loads((directory / "report.json").read_bytes())
    assert retained["finalization"] == "pending-parent-check"
    assert report["status"] == "failed"
    assert report["finalization"] == "failed-after-fsync"
    assert ("original defect" if prior_failure else "deadline") in report["failure"]
    assert retained["status"] == ("failed" if prior_failure else "passed")


def test_worker_rejects_malformed_packet_in_a_cold_pure_process(tmp_path: Path) -> None:
    report = runner.run(b'{"bad":true}', tmp_path / "invalid-packet")
    assert report["status"] == "failed"
    assert report["worker"]["exit_code"] == 2
    assert report["result"]["error_type"] == "PacketError"
    assert report["physical_admission"] == "unavailable"


@pytest.mark.parametrize("argv", [[], ["--worker", "x"], ["--worker", "x", "--deadline", "NaN"]])
def test_private_worker_has_only_its_fixed_shape(argv: list[str]) -> None:
    with pytest.raises(runner.RunError):
        runner.main(argv)


def test_final_clock_backwards_is_a_failure(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        fake_worker: list[tuple[Path, float]]) -> None:
    original_sync = runner._sync
    started = time.monotonic()
    calls = 0

    def sync_then_backwards(path: Path) -> None:
        nonlocal calls
        original_sync(path)
        calls += 1
        if calls == 2:
            monkeypatch.setattr(runner, "_now", lambda: started - 1.0)

    monkeypatch.setattr(runner, "_sync", sync_then_backwards)
    report = runner.run(b"{}", tmp_path / "backwards", started_s=started)
    assert report["status"] == "failed"
    assert "backwards" in report["failure"]


@pytest.mark.parametrize("stall_finalization", [False, True])
def test_cold_valid_packet_has_outer15s_watchdog_through_parent_finalization(
        tmp_path: Path, stall_finalization: bool,
        record_testsuite_property: Callable[[str, object], None]) -> None:
    from test_realized_clock_packet import _packet
    from space_nav._coupled_benchmark_run import _Evidence, _watch_worker

    started = time.monotonic() - (14.0 if stall_finalization else 0.0)
    source = tmp_path / "fabricated.json"
    source.write_bytes(json.dumps(_packet(), allow_nan=False).encode())
    directory = tmp_path / "cold"
    script = (
        "import json,sys,time; from pathlib import Path; "
        "from space_nav import _realized_clock_run as r; "
        "original_sync=r._sync; "
        "r._sync=lambda p: (time.sleep(30) if p.name=='result.json' else None) "
        "or original_sync(p); "
        if stall_finalization else
        "import json,sys,time; from pathlib import Path; "
        "from space_nav import _realized_clock_run as r; "
    )
    script += ("report=r.run(Path(sys.argv[2]).read_bytes(),Path(sys.argv[3]),"
               "started_s=float(sys.argv[1])); print(json.dumps(report)); "
               "sys.exit(0 if report['status']=='passed' else 2)")
    command = [sys.executable, "-c", script, repr(started), str(source), str(directory)]
    output, errors = tmp_path / "outer.json", tmp_path / "outer.stderr.log"
    if stall_finalization:
        with pytest.raises(runner.RunError, match="deadline"):
            _watch_worker(command, output, errors, started + 15.0, _Evidence(tmp_path))
        retained = json.loads((directory / "report.json").read_bytes())
        assert retained["finalization"] == "pending-parent-check"
    else:
        observation = _watch_worker(command, output, errors, started + 15.0, _Evidence(tmp_path))
        assert observation["exit_code"] == 0
        report = json.loads(output.read_bytes())
        assert report["status"] == "passed"
        assert report["result"]["status"] == "passed"
        assert report["finalization"] == "checked-after-fsync"
        assert report["physical_admission"] == "unavailable"
        record_testsuite_property("ariadna-f10-isolated-fixture", json.dumps({
            "external_observation": observation,
            "external_total_s": time.monotonic() - started,
            "inherited_start_s": started,
            "outer_deadline_s": started + 15.0,
            "returned_postfsync": report,
            "durable_prefinal": json.loads((directory / "report.json").read_bytes()),
            "runner_evidence_bytes": sum(path.stat().st_size for path in directory.iterdir()),
        }, sort_keys=True, allow_nan=False))
