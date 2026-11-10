"""Exercise the private screen envelope without archived arithmetic or native imports."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
sys.path[:0] = [str(SCRIPTS / "0170"), str(SCRIPTS / "0167")]

import ariadna_frozen_moon_math as math_helper  # noqa: E402
import ariadna_frozen_moon_run as run  # noqa: E402
from ariadna_split_common import digest, encode, parse_json  # noqa: E402
from test_frozen_moon_math import frozen_bundle  # noqa: E402

START = 50.0
MANIFEST_SHA = "a" * 64
PIN = {"preparation_sha256": MANIFEST_SHA}


def pin_loader(check: Callable[[], float]) -> dict[str, Any]:
    check()
    return PIN


def screen(
    directory: Path, bundle: dict[str, Any], *, clock: Callable[[], float] = lambda: START,
    pin: Callable[[Callable[[], float]], dict[str, Any]] = pin_loader,
) -> bool:
    return run.run_screen(
        directory, START, execution="synthetic", input_loader=lambda check: bundle,
        pin_loader=pin, clock=clock, boot_s=START,
    )


def test_synthetic_screen_finalizes_with_full_raw_ledger(tmp_path: Path) -> None:
    assert screen(tmp_path, frozen_bundle())
    report, receipt = run.read_saved(tmp_path, "synthetic")
    assert report["status"] == "passed"
    assert report["native_calls"] == report["new_record_acquisitions"] == report["propagations"] == 0
    assert report["counts"] == {
        op: dict.fromkeys(("attempted", "returned", "completed"), count) for op, count in run.CAPS.items()
    }
    assert len(report["rows"]) == 28
    files = run.paths(tmp_path)
    assert receipt["journal_sha256"] == digest(files["journal"])
    before = {file: file.read_bytes() for file in (files["report"], files["journal"], files["receipt"])}
    with pytest.raises(ValueError, match="existing screen evidence"):
        screen(tmp_path, frozen_bundle())
    assert all(file.read_bytes() == data for file, data in before.items())
    files["journal"].write_bytes(before[files["journal"]] + b"\n")
    with pytest.raises(ValueError, match="journal hash"):
        run.read_saved(tmp_path, "synthetic")


def test_input_failure_keeps_failed_evidence(tmp_path: Path) -> None:
    def invalid(check: Callable[[], float]) -> dict[str, Any]:
        check()
        raise ValueError("fixture inventory mismatch")

    assert not run.run_screen(
        tmp_path, START, execution="synthetic", input_loader=invalid,
        pin_loader=pin_loader, clock=lambda: START, boot_s=START,
    )
    report, receipt = run.read_saved(tmp_path, "synthetic")
    assert receipt["finalization"] == "passed"
    assert report["status"] == "failed"
    assert report["error"]["stage"] == "archived inputs"
    assert report["execution_incomplete"] and not report["rows"] and not report["ledger"]


def test_identity_failure_preserves_completed_rows(tmp_path: Path) -> None:
    pins = iter((PIN, {"preparation_sha256": "b" * 64}))

    assert not screen(tmp_path, frozen_bundle(), pin=lambda _: next(pins))
    report, receipt = run.read_saved(tmp_path, "synthetic")
    assert receipt["finalization"] == "passed"
    assert report["error"]["stage"] == "final preparation identity"
    assert report["identity_pin"] != report["final_identity_pin"]
    assert len(report["rows"]) == 28


def test_late_return_keeps_raw_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = START

    def analyze(bundle: dict[str, Any], report: dict[str, Any], recorder: Any) -> None:
        def late() -> dict[str, float]:
            nonlocal now
            now += 10.125
            return {"synthetic": 3.0}

        recorder.call("record", "synthetic", [], late)

    monkeypatch.setattr(math_helper, "analyze", analyze)
    assert not screen(tmp_path, {}, clock=lambda: now)
    files = run.paths(tmp_path)
    receipt = parse_json(files["receipt"].read_bytes())
    report = parse_json(files["report"].read_bytes())
    assert receipt["finalization"] == report["status"] == "failed"
    assert report["error"]["stage"] == "numerical screen"
    assert report["counts"]["record"] == {"attempted": 1, "returned": 1, "completed": 0}
    assert report["ledger"][0]["raw"] == {"synthetic": 3.0}
    with pytest.raises(ValueError, match="child finalization"):
        run.read_saved(tmp_path, "synthetic")


def test_watchdog_does_not_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def timeout(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[1:4] == ["-I", "-S", "-B"]
        assert kwargs["timeout"] == 15.0
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(run, "require_offline", lambda: None)
    monkeypatch.setattr(run.subprocess, "run", timeout)
    directory = tmp_path / "fixture"
    assert not run.supervise(directory, MANIFEST_SHA)
    files = run.paths(directory)
    receipt = parse_json(files["parent"].read_bytes())
    assert receipt["finalization"] == "failed"
    assert receipt["error"]["type"] == "TimeoutExpired"
    assert parse_json(files["attempt"].read_bytes())["preparation_sha256"] == MANIFEST_SHA
    with pytest.raises(ValueError, match="existing screen evidence"):
        run.supervise(directory, MANIFEST_SHA)


@pytest.mark.parametrize("after_parent_flush", [10.0, 10.125])
def test_supervisor_uses_inclusive_finalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_parent_flush: float,
) -> None:
    stamps = iter((START, START + 9.9, START + 9.95, START + after_parent_flush))
    monkeypatch.setattr(run, "ROOT", tmp_path)
    archive = tmp_path / "fixture archive"
    archive.write_bytes(b"synthetic")
    identity = {"inputs_sha256": run.DESIGN_SHA256, "archive_and_evidence_sha256": {archive.name: digest(archive)}}

    def completed(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert command[-3:] == ["_child", MANIFEST_SHA, repr(START)]
        assert kwargs["timeout"] == 15.0
        assert run.run_screen(
            tmp_path, START, execution="archived", input_loader=lambda _: {**frozen_bundle(), "identity": identity},
            pin_loader=pin_loader, clock=lambda: START, boot_s=START,
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(run, "require_offline", lambda: None)
    monkeypatch.setattr(run, "monotonic", lambda: next(stamps))
    monkeypatch.setattr(run.subprocess, "run", completed)
    assert run.supervise(tmp_path, MANIFEST_SHA) is (after_parent_flush == 10.0)
    files = run.paths(tmp_path)
    parent = parse_json(files["parent"].read_bytes())
    assert parent["finalization"] == ("passed" if after_parent_flush == 10.0 else "failed")
    assert parent["child_receipt_sha256"] == digest(files["receipt"])
    assert run.read_saved(tmp_path, "archived")[0]["status"] == "passed"


def test_preparation_pin_rejects_changed_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / run.DESIGN_INPUTS
    design.parent.mkdir(parents=True)
    design.write_text("synthetic inventory", encoding="utf-8")
    monkeypatch.setattr(run, "DESIGN_SHA256", digest(design))
    sources = {}
    for name in run.TESTED | run.REUSED:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name, encoding="utf-8")
        sources[name] = digest(path)
    proof = tmp_path / run.MANIFEST
    proof.write_bytes(encode({
        "preparation_complete": True, "design_inputs_sha256": run.DESIGN_SHA256,
        "tested_source_sha256": {key: sources[key] for key in run.TESTED},
        "reused_source_sha256": {key: sources[key] for key in run.REUSED},
    }))
    sha = digest(proof)
    assert run.prep_pin(tmp_path, sha, lambda: None)["preparation_sha256"] == sha
    (tmp_path / sorted(run.TESTED)[0]).write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="tested or reused source hash"):
        run.prep_pin(tmp_path, sha, lambda: None)



def test_final_archive_identity_detects_changed_bytes(tmp_path: Path) -> None:
    archive = tmp_path / "fixture archive"
    archive.write_bytes(b"before")
    identity = {"inputs_sha256": run.DESIGN_SHA256, "archive_and_evidence_sha256": {archive.name: digest(archive)}}
    run.verify_bound_inputs(tmp_path, identity, lambda: None)
    archive.write_bytes(b"after")
    with pytest.raises(ValueError, match="final archive hash"):
        run.verify_bound_inputs(tmp_path, identity, lambda: None)
