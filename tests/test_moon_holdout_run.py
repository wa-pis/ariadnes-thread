"""Verify phase orchestration and durable evidence with an injected provider only."""
from __future__ import annotations

from collections.abc import Callable
from math import inf, nextafter
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from test_moon_holdout_capture import FakeHoldoutAdapter, synthetic_holdout_bundle

EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
sys.path[:0] = [str(EXPERIMENTS / number) for number in ("0173", "0170", "0167")]

import ariadna_moon_holdout_run as run  # noqa: E402
from ariadna_split_common import digest, encode, parse_json  # noqa: E402

START = 50.0
SHA = "a" * 64
PIN = {"preparation_sha256": SHA}


def pin_loader(check: Callable[[], Any]) -> dict[str, str]:
    check()
    return PIN


def synthetic_capture(directory: Path, bundle: dict[str, Any], adapter: FakeHoldoutAdapter) -> None:
    files = run.paths(directory, "capture")
    files["attempt"].write_bytes(encode(run.marker("capture", SHA)))
    assert run.run_phase(
        directory, "capture", START, execution="synthetic", input_loader=lambda _: bundle,
        pin_loader=pin_loader, adapter_factory=lambda: adapter, clock=lambda: START, boot_s=START,
    )
    files["parent"].write_bytes(encode({
        **run.marker("capture", SHA), "finalization": "passed", "returncode": 0,
        "external_start_s": START, "external_elapsed_s": 0.0,
        "attempt_sha256": digest(files["attempt"]), "child_receipt_sha256": digest(files["receipt"]),
    }))


def synthetic_analysis(directory: Path, bundle: dict[str, Any]) -> bool:
    return run.run_phase(
        directory, "analysis", START, execution="synthetic", input_loader=lambda _: bundle,
        pin_loader=pin_loader, clock=lambda: START, boot_s=START,
    )


@pytest.mark.parametrize("bit_miss", [False, True])
def test_saved_capture_and_analysis_finish(tmp_path: Path, bit_miss: bool) -> None:
    bundle = synthetic_holdout_bundle()
    adapter = FakeHoldoutAdapter(bundle)
    if bit_miss:
        adapter.geocentric[0][0] = nextafter(adapter.geocentric[0][0], inf)
    synthetic_capture(tmp_path, bundle, adapter)
    capture, receipt = run.read_saved(tmp_path, "capture", "synthetic")
    assert len(capture["ledger"]) == 63 and capture["explicit_native_attempts"] == 0
    assert receipt["finalization"] == "passed"
    assert synthetic_analysis(tmp_path, bundle) is (not bit_miss)
    report, analysis_receipt = run.read_saved(tmp_path, "analysis", "synthetic")
    assert len(report["rows"]) == 16 and not report["unavailable"]
    assert report["explicit_native_attempts"] == 0
    assert report["capture_parent_sha256"] == digest(run.paths(tmp_path, "capture")["parent"])
    assert analysis_receipt["finalization"] == "passed"
    assert report["status"] == ("failed" if bit_miss else "passed")
    paths = run.paths(tmp_path, "analysis")
    hashes = {key: digest(paths[key]) for key in ("report", "journal", "receipt")}
    with pytest.raises(ValueError, match="existing holdout evidence"):
        synthetic_analysis(tmp_path, bundle)
    assert all(digest(paths[key]) == expected for key, expected in hashes.items())


@pytest.mark.parametrize("which", ["attempt", "journal", "parent", "receipt"])
def test_analysis_rejects_tampered_capture_before_epoch_checks(tmp_path: Path, which: str) -> None:
    bundle = synthetic_holdout_bundle()
    synthetic_capture(tmp_path, bundle, FakeHoldoutAdapter(bundle))
    files = run.paths(tmp_path, "capture")
    if which == "journal":
        files[which].write_bytes(files[which].read_bytes() + b"\n")
    else:
        content = parse_json(files[which].read_bytes())
        field = {"attempt": "preparation_sha256", "parent": "child_receipt_sha256", "receipt": "report_sha256"}[which]
        content[field] = "b" * 64
        files[which].write_bytes(encode(content))
    assert not synthetic_analysis(tmp_path, bundle)
    report, receipt = run.read_saved(tmp_path, "analysis", "synthetic")
    assert receipt["finalization"] == "passed"
    assert report["error"]["stage"] == "capture evidence"
    assert report["unavailable"] == list(range(16))
    assert report["counts"]["epoch"]["attempted"] == 0


def test_late_capture_return_keeps_raw_and_failed_receipt(tmp_path: Path) -> None:
    bundle = synthetic_holdout_bundle()
    adapter = FakeHoldoutAdapter(bundle)
    now = START

    def late(value: Any) -> Any:
        nonlocal now
        now += 15.125
        return value

    adapter.mutations["spkezr", 2] = late
    assert not run.run_phase(
        tmp_path, "capture", START, execution="synthetic", input_loader=lambda _: bundle, pin_loader=pin_loader,
        adapter_factory=lambda: adapter, clock=lambda: now, boot_s=START,
    )
    files = run.paths(tmp_path, "capture")
    report = parse_json(files["report"].read_bytes())
    assert parse_json(files["receipt"].read_bytes())["finalization"] == "failed"
    assert report["counts"]["state"] == {"attempted": 2, "returned": 2, "completed": 1}
    assert report["unavailable"] == list(range(1, 16))
    assert report["ledger"][-1]["raw"][0] == adapter.geocentric[1]
    assert "completed_s" not in report["ledger"][-1]
    assert report["error"]["stage"] == "capture"
    with pytest.raises(ValueError, match="child finalization"):
        run.read_saved(tmp_path, "capture", "synthetic")


def test_final_pin_mismatch_preserves_analysis_and_rejects_qualification(tmp_path: Path) -> None:
    bundle = synthetic_holdout_bundle()
    synthetic_capture(tmp_path, bundle, FakeHoldoutAdapter(bundle))
    pins = iter((PIN, {"preparation_sha256": "b" * 64}))
    assert not run.run_phase(
        tmp_path, "analysis", START, execution="synthetic", input_loader=lambda _: bundle,
        pin_loader=lambda _: next(pins), clock=lambda: START, boot_s=START,
    )
    report, receipt = run.read_saved(tmp_path, "analysis", "synthetic")
    assert receipt["finalization"] == "passed"
    assert report["error"]["stage"] == "final preparation identity" and report["execution_incomplete"]
    assert len(report["rows"]) == 16


@pytest.mark.parametrize(("phase", "flags", "timeout"), [
    ("capture", ("-I", "-B"), 20.0),
    ("analysis", ("-I", "-S", "-B"), 15.0),
])
def test_supervisor_watchdog_preserves_exclusive_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, flags: tuple[str, ...], timeout: float,
) -> None:
    calls = []

    def expired(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert tuple(command[1:1 + len(flags)]) == flags
        assert command[-4:-1] == ["_child", phase, SHA] and kwargs["timeout"] == timeout
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(run, "require_offline", lambda: None)
    monkeypatch.setattr(run.subprocess, "run", expired)
    assert not run.supervise(tmp_path, phase, SHA)
    files = run.paths(tmp_path, phase)
    assert parse_json(files["attempt"].read_bytes()) == run.marker(phase, SHA)
    parent = parse_json(files["parent"].read_bytes())
    assert parent["finalization"] == "failed" and parent["error"]["type"] == "TimeoutExpired"
    with pytest.raises(ValueError, match="existing holdout evidence"):
        run.supervise(tmp_path, phase, SHA)
    assert len(calls) == 1


@pytest.mark.parametrize("after_flush", [10.0, 10.125])
def test_parent_inclusive_flush_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_flush: float,
) -> None:
    stamps = iter((START, START + 9.5, START + 9.75, START + after_flush))
    files = run.paths(tmp_path, "analysis")

    def child(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        files["receipt"].write_bytes(b"fixture finalized child")
        return subprocess.CompletedProcess(command, 0, "", "")

    def read(directory: Path, phase: str, execution: str) -> tuple[dict[str, Any], dict[str, Any]]:
        assert (directory, phase, execution) == (tmp_path, "analysis", "live")
        return {"status": "passed", "external_start_s": START, "identity_pin": PIN}, {"elapsed_before_receipt_s": 9.0}

    monkeypatch.setattr(run, "require_offline", lambda: None)
    monkeypatch.setattr(run, "monotonic", lambda: next(stamps))
    monkeypatch.setattr(run, "read_saved", read)
    monkeypatch.setattr(run.subprocess, "run", child)
    assert run.supervise(tmp_path, "analysis", SHA) is (after_flush == 10.0)
    parent = parse_json(files["parent"].read_bytes())
    assert parent["finalization"] == ("passed" if after_flush == 10.0 else "failed")
    assert parent["child_receipt_sha256"] == digest(files["receipt"])


def test_failed_capture_never_starts_analysis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "simulated"
    monkeypatch.setattr(run, "LIVE_DIR", run_dir)
    calls = []

    def fake_supervisor(directory: Path, phase: str, manifest_sha: str) -> bool:
        calls.append((directory, phase, manifest_sha))
        return False

    monkeypatch.setattr(run, "supervise", fake_supervisor)
    assert run.main([SHA]) == 2
    assert calls == [(run_dir, "capture", SHA)]


def test_manifest_pin_and_final_archive_reject_changed_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inventory = tmp_path / run.INPUTS
    inventory.parent.mkdir(parents=True)
    inventory.write_text("synthetic inventory", encoding="utf-8")
    monkeypatch.setattr(run, "INPUT_SHA256", digest(inventory))
    hashes = {}
    for name in run.TESTED | run.REUSED:
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(name, encoding="utf-8")
        hashes[name] = digest(file)
    proof = tmp_path / run.MANIFEST
    proof.write_bytes(encode({
        "preparation_complete": True, "inputs_sha256": run.INPUT_SHA256,
        "tested_source_sha256": {key: hashes[key] for key in run.TESTED},
        "reused_source_sha256": {key: hashes[key] for key in run.REUSED},
    }))
    assert run.prep_pin(tmp_path, digest(proof), lambda: None)["inputs_sha256"] == digest(inventory)
    (tmp_path / sorted(run.REUSED)[0]).write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="prepared or reused source"):
        run.prep_pin(tmp_path, digest(proof), lambda: None)
    archive = tmp_path / "fake archive"
    archive.write_bytes(b"original")
    identity = {"inputs_sha256": run.INPUT_SHA256, "retained_evidence_sha256": {archive.name: digest(archive)}}
    run.verify_bound_inputs(tmp_path, identity, lambda: None)
    archive.write_bytes(b"changed")
    with pytest.raises(ValueError, match="final archive SHA-256"):
        run.verify_bound_inputs(tmp_path, identity, lambda: None)


def test_import_is_isolated_and_side_effect_free() -> None:
    script = """
import sys
sys.path[:0] = sys.argv[1:]
import ariadna_moon_holdout_run as run
run.require_offline()
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", script, *(str(EXPERIMENTS / n) for n in ("0173", "0170", "0167"))],
        capture_output=True, text=True, check=True, timeout=5,
    )
    assert result.stdout == result.stderr == ""
