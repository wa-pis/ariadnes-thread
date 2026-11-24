"""Process boundaries use fabricated packets, never ephemerides or optimization."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

import space_nav
from space_nav import _coupled_benchmark_run as runner


def _candidate(reference: object) -> dict[str, object]:
    return {
        "schema": "ariadna-coupled-synthetic-v1", "status": "passed",
        "frame": "SYNTHETIC_INERTIAL", "time_scale": "elapsed_seconds",
        "reference": reference, "controls": [0.0] * 6, "shooting_nodes": [],
        "initial_defects": [], "defects": [], "arc_start_states": [],
        "arc_end_states": [], "witness": {}, "recovered": {}, "solver": {},
        "counts": {"rhs_attempts": 27},
    }


@pytest.fixture
def fake_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    reference = {"artificial": True}
    monkeypatch.setattr(space_nav, "_coupled_benchmark_oracle",
                        SimpleNamespace(reference=lambda: reference), raising=False)
    monkeypatch.setattr(runner, "__file__", str(tmp_path / "_coupled_benchmark_run.py"))
    for name in ("_coupled_benchmark_run", "_coupled_benchmark",
                 "_coupled_benchmark_oracle", "trajectory"):
        (tmp_path / f"{name}.py").write_text("# fabricated source\n")
    commands: list[list[str]] = []

    def command(kind: str, source: Path, deadline: float) -> list[str]:
        packet = (_candidate(reference) if kind == "producer" else {
            "schema": "ariadna-coupled-audit-v1", "status": "passed",
            "frame": "SYNTHETIC_INERTIAL", "time_scale": "elapsed_seconds",
            "controls": [0.0] * 6, "counts": {"rhs_attempts": 42},
        })
        result = [sys.executable, "-c", f"import sys; sys.stdout.write({json.dumps(packet)!r})"]
        commands.append([kind, str(source), repr(deadline)])
        return result

    monkeypatch.setattr(runner, "_worker_command", command)
    return commands


def test_pipeline_uses_separate_workers_and_keeps_complete_evidence(
        tmp_path: Path, fake_pipeline: list[list[str]]) -> None:
    directory = tmp_path / "qualification"
    report = runner.run(directory)
    assert report["status"] == "passed"
    assert [item[0] for item in fake_pipeline] == ["producer", "audit"]
    assert float(fake_pipeline[1][2]) - float(fake_pipeline[0][2]) <= 60
    assert report["producer_counts"] == {"rhs_attempts": 27}
    assert report["audit_counts"] == {"rhs_attempts": 42}
    assert set(report["source_sha256"]) == {
        "_coupled_benchmark_run", "_coupled_benchmark", "_coupled_benchmark_oracle", "trajectory"}
    assert json.loads((directory / "report.json").read_text()) == report
    assert report["evidence_bytes"] == sum(path.stat().st_size for path in directory.iterdir())
    assert json.loads((directory / "producer.json").read_text())["reference"] == {"artificial": True}


def test_existing_output_directory_is_never_overwritten(tmp_path: Path) -> None:
    retained = tmp_path / "keep.json"
    retained.write_text("untouched")
    with pytest.raises(FileExistsError):
        runner.run(tmp_path)
    assert retained.read_text() == "untouched"
    assert not (tmp_path / "report.json").exists()


@pytest.mark.parametrize("text", ["[]", '{"x":NaN}', '{"x":1e999}', "{bad"])
def test_input_rejects_nonobject_and_nonfinite(tmp_path: Path, text: str) -> None:
    source = tmp_path / "input.json"
    source.write_text(text)
    with pytest.raises((ValueError, runner.RunError)):
        runner._read_packet(source, 128)


def test_explicit_input_cap_is_checked_before_parsing(tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    source.write_bytes(b" " * (runner.INPUT_BYTES + 1))
    with pytest.raises(runner.RunError, match="exceeds"):
        runner._read_packet(source, runner.INPUT_BYTES)


def test_watchdog_kills_stalled_worker(tmp_path: Path) -> None:
    start = time.monotonic()
    with pytest.raises(runner.RunError, match="deadline"):
        runner._watch_worker([sys.executable, "-c", "import time; time.sleep(30)"],
                             tmp_path / "out", tmp_path / "err", start + 0.15,
                             runner._Evidence(tmp_path))
    assert time.monotonic() - start < 3


def test_parent_bounds_stdout_and_stderr_while_running(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "EVIDENCE_BYTES", 50000)
    monkeypatch.setattr(runner, "REPORT_RESERVE", 10000)
    evidence = runner._Evidence(tmp_path)
    with pytest.raises(runner.RunError, match="byte cap"):
        runner._watch_worker(
            [sys.executable, "-c", "import os\nwhile True: os.write(1,b'x'*4096); os.write(2,b'y'*4096)"],
            tmp_path / "out", tmp_path / "err", time.monotonic() + 5, evidence)
    assert evidence.used == 40000
    assert sum(path.stat().st_size for path in tmp_path.iterdir()) == 40000


def test_failed_producer_preserves_partial_counts_and_skips_audit(
        tmp_path: Path, fake_pipeline: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    def command(kind: str, source: Path, deadline: float) -> list[str]:
        fake_pipeline.append([kind])
        return [sys.executable, "-c",
                "import sys; print('{\"status\":\"failed\",\"counts\":{\"rhs_attempts\":3}}');sys.exit(2)"]

    monkeypatch.setattr(runner, "_worker_command", command)
    report = runner.run(tmp_path / "failed")
    assert report["status"] == "failed"
    assert "producer worker failed" in report["failure"]["message"]
    assert report["producer_counts"] == {"rhs_attempts": 3}
    assert report["audit_counts"] is None
    assert fake_pipeline == [["producer"]]


def test_timeout_preserves_failure_with_unknown_counters(
        tmp_path: Path, fake_pipeline: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "PRODUCER_SECONDS", 0.2)
    monkeypatch.setattr(runner, "_worker_command", lambda *args: [
        sys.executable, "-c", "import time; time.sleep(30)"])
    report = runner.run(tmp_path / "stalled")
    assert report["status"] == "failed"
    assert report["producer_counts"] is None
    assert report["audit_counts"] is None
    assert not (tmp_path / "stalled" / "audit.json").exists()


def test_packet_cannot_claim_success_without_contract(
        tmp_path: Path, fake_pipeline: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_worker_command", lambda *args: [
        sys.executable, "-c", "print('{\"status\":\"passed\"}')"])
    report = runner.run(tmp_path / "invalid")
    assert report["status"] == "failed"
    assert "contract" in report["failure"]["message"]
    assert not (tmp_path / "invalid" / "audit.json").exists()


def test_runtime_pin_failure_is_retained(
        tmp_path: Path, fake_pipeline: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "version", lambda name: "wrong")
    report = runner.run(tmp_path / "unpinned")
    assert report["status"] == "failed"
    assert "pinned" in report["failure"]["message"]
    assert fake_pipeline == []


def test_late_durable_write_leaves_failed_report(
        tmp_path: Path, fake_pipeline: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    real_clock = time.monotonic
    offset = 0.0
    original_fsync = runner.os.fsync

    def fsync(descriptor: int) -> None:
        nonlocal offset
        original_fsync(descriptor)
        offset = 1000.0

    monkeypatch.setattr(runner.time, "monotonic", lambda: real_clock() + offset)
    monkeypatch.setattr(runner.os, "fsync", fsync)
    with pytest.raises(runner.RunError, match="durable report"):
        runner.run(tmp_path / "late")
    report = json.loads((tmp_path / "late" / "report.json").read_text())
    assert report["status"] == "failed"
    assert "durable report" in report["failure"]["message"]


def test_unexpected_failure_is_recorded_and_propagated(
        tmp_path: Path, fake_pipeline: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected(*args: object) -> None:
        raise KeyError("unexpected test failure")

    monkeypatch.setattr(runner, "_worker_command", unexpected)
    with pytest.raises(KeyError):
        runner.run(tmp_path / "unexpected")
    report = json.loads((tmp_path / "unexpected" / "report.json").read_text())
    assert report["failure"]["type"] == "KeyError"
    assert report["producer_counts"] is None


def test_worker_command_round_trips_private_argument_shape() -> None:
    command = runner._worker_command("audit", Path("/tmp/producer.json"), 123.5)
    assert command == [sys.executable, "-m", "space_nav._coupled_benchmark_run",
                       "--worker", "audit", "/tmp/producer.json", "--deadline", "123.5"]


@pytest.mark.parametrize("kind", ["producer", "audit"])
def test_worker_dispatches_fabricated_packet(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str], kind: str) -> None:
    packet = {"fixture": "fabricated"}
    source = tmp_path / "input.json"
    source.write_text(json.dumps(packet))
    deadline = time.monotonic() + 10
    seen: list[object] = []

    def operation(value: object, *, deadline: float) -> dict[str, object]:
        seen.extend([value, deadline])
        return {"status": "passed", "fabricated": True}

    implementation = SimpleNamespace(BenchmarkError=ValueError, OracleError=ValueError,
                                     run=operation, audit=operation)
    name = "_coupled_benchmark" if kind == "producer" else "_coupled_benchmark_oracle"
    monkeypatch.setattr(space_nav, name, implementation, raising=False)
    monkeypatch.setattr(runner, "_install_import_guard", lambda auditor: None)
    assert runner.main(["--worker", kind, str(source), "--deadline", str(deadline)]) == 0
    assert seen == [packet, deadline]
    assert json.loads(capfd.readouterr().out)["fabricated"] is True


def test_independent_worker_guard_blocks_cached_and_relative_imports() -> None:
    code = '''
import sys, types
from space_nav._coupled_benchmark_run import _install_import_guard
sys.modules["numpy"] = types.ModuleType("numpy")
_install_import_guard(True)
for statement in ("import numpy", "import scipy", "import tudatpy", "import spiceypy",
                  "from space_nav import trajectory", "from space_nav import _coupled_benchmark"):
    try:
        exec(statement)
    except ImportError:
        continue
    raise AssertionError(statement)
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                            text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_worker_bad_input_has_expected_exit_and_no_invented_counters(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "input.json"
    source.write_text("[]")
    monkeypatch.setattr(runner, "_install_import_guard", lambda auditor: None)
    assert runner.main(["--worker", "producer", str(source), "--deadline",
                        str(time.monotonic() + 10)]) == 2
    packet = json.loads(capfd.readouterr().out)
    assert packet["status"] == "failed"
    assert packet["counts"] is None


def test_audit_failure_does_not_leave_successful_report(
        tmp_path: Path, fake_pipeline: list[list[str]], monkeypatch: pytest.MonkeyPatch) -> None:
    original = runner._worker_command

    def command(kind: str, source: Path, deadline: float) -> list[str]:
        if kind == "audit":
            return [sys.executable, "-c", "import sys; sys.stderr.write('independent gate failed');sys.exit(2)"]
        return original(kind, source, deadline)

    monkeypatch.setattr(runner, "_worker_command", command)
    directory = tmp_path / "audit-failure"
    report = runner.run(directory)
    assert report["status"] == "failed"
    assert "audit worker failed" in report["failure"]["message"]
    assert report["producer_counts"] == {"rhs_attempts": 27}
    assert report["audit_counts"] is None
    assert (directory / "audit.stderr.log").read_text() == "independent gate failed"


def test_real_producer_dispatch_imports_pure_helpers_then_rejects_bad_fixture(
        tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    source.write_text("{}")
    deadline = time.monotonic() + 10
    output = tmp_path / "producer.json"
    result = runner._watch_worker(runner._worker_command("producer", source, deadline),
                                  output, tmp_path / "errors.log", deadline,
                                  runner._Evidence(tmp_path))
    assert result["exit_code"] == 2
    packet = json.loads(output.read_text())
    assert packet["status"] == "failed"
    assert "reference: wrong schema" in packet["error"]
    assert packet["error_type"] == "BenchmarkError"


def test_inherited_start_shortens_producer_deadline(
        tmp_path: Path, fake_pipeline: list[list[str]]) -> None:
    started = time.monotonic() - 25.0
    report = runner.run(tmp_path / "inherited", started=started)
    assert report["status"] == "passed"
    assert float(fake_pipeline[0][2]) == started + runner.PRODUCER_SECONDS
    assert float(fake_pipeline[1][2]) <= started + runner.AUDIT_FINISH_SECONDS
    assert report["parent_started_monotonic_s"] == started
    assert report["startup_elapsed_s"] >= 25.0
    assert report["elapsed_s"] >= 25.0


@pytest.mark.parametrize("elapsed", [211.0, 301.0])
def test_expired_inherited_budget_never_starts_worker(
        tmp_path: Path, fake_pipeline: list[list[str]], elapsed: float) -> None:
    directory = tmp_path / "expired"
    if elapsed < runner.TOTAL_SECONDS:
        report = runner.run(directory, started=time.monotonic() - elapsed)
        assert report["status"] == "failed"
        assert "deadline" in report["failure"]["message"]
        assert not (directory / "reference.json").exists()
    else:
        with pytest.raises(runner.RunError, match="deadline"):
            runner.run(directory, started=time.monotonic() - elapsed)
        assert not directory.exists()
    assert fake_pipeline == []


@pytest.mark.parametrize("started", [float("nan"), float("inf"), -float("inf"), True])
def test_invalid_parent_start_cannot_create_directory(
        tmp_path: Path, started: float) -> None:
    directory = tmp_path / "invalid-start"
    with pytest.raises(runner.RunError, match="finite past monotonic"):
        runner.run(directory, started=started)
    assert not directory.exists()


def test_future_parent_start_cannot_create_directory(tmp_path: Path) -> None:
    directory = tmp_path / "future-start"
    with pytest.raises(runner.RunError, match="finite past monotonic"):
        runner.run(directory, started=time.monotonic() + 10.0)
    assert not directory.exists()


def test_cli_passes_explicit_parent_start(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str]) -> None:
    seen: list[object] = []
    started = time.monotonic() - 1.0

    def run(directory: Path, *, started: float | None = None) -> dict[str, object]:
        seen.extend([directory, started])
        return {"status": "passed"}

    monkeypatch.setattr(runner, "run", run)
    assert runner.main([str(tmp_path / "new"), "--parent-start", repr(started)]) == 0
    assert seen == [tmp_path / "new", started]
    assert "passed" in capfd.readouterr().out


def test_worker_cannot_reset_parent_start(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        runner.main(["--worker", "producer", str(tmp_path / "input.json"),
                     "--deadline", "123", "--parent-start", "12"])
    assert exc.value.code == 2
