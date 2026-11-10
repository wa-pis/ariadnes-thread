"""Synthetic end-to-end coverage for the R5.29 runner and receipt readback."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from typing import Any, NoReturn

import pytest

_EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
sys.path[:0] = [str(_EXPERIMENTS / n) for n in ("0176", "0173", "0170", "0167")]

import ariadna_paired_moon_math as model  # noqa: E402
import ariadna_paired_moon_run as run  # noqa: E402
from ariadna_split_common import digest, encode, journal_rows, parse_json  # noqa: E402
from test_paired_moon_math import paired_bundle  # noqa: E402

PIN = {"preparation_sha256": "a" * 64}
INPUT = {"synthetic": True}


def prohibit(*_args: object) -> NoReturn:
    pytest.fail("readback called a field evaluator")


def start(directory: Path, bundle: dict[str, Any]) -> bool:
    bundle["identity"] = INPUT
    return run.run_pair(directory, 12.0, execution="synthetic", input_loader=lambda _: bundle,
                        pin_loader=lambda _: PIN, boot_s=12.1, clock=lambda: 12.2)


def parent(directory: Path, returncode: int) -> dict[str, Any]:
    files = run.paths(directory)
    files["attempt"].write_bytes(encode(run.marker(PIN["preparation_sha256"])))
    value = {**run.marker(PIN["preparation_sha256"]), "finalization": "passed",
             "returncode": returncode, "external_start_s": 12.0, "external_elapsed_s": 0.3,
             "attempt_sha256": digest(files["attempt"]), "child_receipt_sha256": digest(files["receipt"])}
    files["parent"].write_bytes(encode(value))
    return value


def rebind(directory: Path, report: dict[str, Any], receipt: dict[str, Any]) -> None:
    files = run.paths(directory)
    files["report"].write_bytes(encode(report))
    files["journal"].write_bytes(b"".join(
        encode(row) for index, entry in enumerate(report["ledger"]) for row in journal_rows(index, entry)))
    receipt.update(report_sha256=digest(files["report"]), journal_sha256=digest(files["journal"]))
    files["receipt"].write_bytes(encode(receipt))
    parent(directory, 0 if report["status"] == "passed" else 2)


@pytest.mark.parametrize("near_gate", [False, True])
def test_full_pair_and_readback_never_recomputes_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, near_gate: bool,
) -> None:
    bundle = paired_bundle(near_gate=near_gate)
    assert start(tmp_path, bundle) is not near_gate
    parent(tmp_path, 2 if near_gate else 0)
    monkeypatch.setattr(model, "_binary64_field", prohibit)
    monkeypatch.setattr(model, "_decimal_field", prohibit)
    report = run.audit(tmp_path, "synthetic", PIN, bundle)
    assert report["outcome"] == ("negative" if near_gate else "confirmed")
    assert all(report[key] == expected for key, expected in run.SCOPE.items())
    assert report["unavailable"] == []
    assert {op: values["completed"] for op, values in report["counts"].items()} == model.CAPS
    assert len(run.paths(tmp_path)["journal"].read_bytes().splitlines()) == 429


def test_finalized_invalid_geometry_preserves_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = paired_bundle()
    bundle["rows"][2]["archive"]["motion"]["rephasing_m"][0] = 2.0
    assert not start(tmp_path, bundle)
    parent(tmp_path, 2)
    monkeypatch.setattr(model, "_binary64_field", prohibit)
    monkeypatch.setattr(model, "_decimal_field", prohibit)
    report = run.audit(tmp_path, "synthetic", PIN, bundle)
    assert report["outcome"] == "incomplete"
    assert [row["outcome"] for row in report["rows"]] == ["confirmed", "confirmed", "incomplete"]
    assert report["unavailable"] == list(run.ORDINALS[2:])
    assert report["counts"]["binary64_field"]["completed"] == 4


def test_inputs_fail_before_any_admission(tmp_path: Path) -> None:
    bundle = paired_bundle()
    bundle["rows"][0]["archive"]["observation_ordinal"] = 999
    assert not start(tmp_path, bundle)
    parent(tmp_path, 2)
    report = run.audit(tmp_path, "synthetic", PIN, bundle)
    assert report["ledger"] == [] and report["unavailable"] == list(run.ORDINALS)
    assert report["outcome"] == "incomplete" and report["stopped"]["stage"] == "admission"


def test_field_failure_preserves_completed_pairs_without_invoking_missing_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = paired_bundle()
    decimal = model._decimal_field
    calls = 0

    def abort_first_field_in_second_pair(*args: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls == 11:
            raise ValueError("synthetic field failure")
        return decimal(*args)

    monkeypatch.setattr(model, "_decimal_field", abort_first_field_in_second_pair)
    assert not start(tmp_path, bundle)
    parent(tmp_path, 2)
    monkeypatch.setattr(model, "_binary64_field", prohibit)
    monkeypatch.setattr(model, "_decimal_field", prohibit)
    report = run.audit(tmp_path, "synthetic", PIN, bundle)
    assert report["outcome"] == "incomplete" and report["unavailable"] == list(run.ORDINALS[1:])
    assert report["counts"]["decimal_field"] == {"attempted": 11, "returned": 10, "completed": 10}
    assert report["error"]["message"] == "synthetic field failure"
    report, receipt = run.read_saved(tmp_path, "synthetic")
    report["rows"][1]["exact_separations_m"]["d0"][0] = "1"
    rebind(tmp_path, report, receipt)
    with pytest.raises(ValueError, match="saved pair prefix"):
        run.audit(tmp_path, "synthetic", PIN, bundle)


@pytest.mark.parametrize("mutation", ["parent", "journal", "result", "operation", "unavailable", "identity"])
def test_readback_rejects_tampered_evidence(tmp_path: Path, mutation: str) -> None:
    bundle = paired_bundle()
    assert start(tmp_path, bundle)
    value = parent(tmp_path, 0)
    files = run.paths(tmp_path)
    report, receipt = run.read_saved(tmp_path, "synthetic")
    if mutation == "parent":
        value["child_receipt_sha256"] = "0" * 64
        files["parent"].write_bytes(encode(value))
    elif mutation == "journal":
        with files["journal"].open("ab") as stream:
            stream.write(b"{}\n")
    elif mutation == "identity":
        bundle["identity"] = {"synthetic": False}
    else:
        if mutation == "result":
            report["rows"][0]["signed_delta_acceleration_m_s2"][0] = "1"
        elif mutation == "operation":
            report["ledger"][1]["args"][3] *= 2.0
        else:
            report["unavailable"] = [27]
        rebind(tmp_path, report, receipt)
    with pytest.raises(ValueError, match="pair"):
        run.audit(tmp_path, "synthetic", PIN, bundle)


def test_returned_field_is_durable_when_deadline_expires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = paired_bundle()
    bundle["identity"] = INPUT
    now = 0.1
    original = model._binary64_field

    def late(*args: Any) -> Any:
        nonlocal now
        now = 10.01
        return original(*args)

    monkeypatch.setattr(model, "_binary64_field", late)
    assert not run.run_pair(tmp_path, 0.0, execution="synthetic", input_loader=lambda _: bundle,
                            pin_loader=lambda _: PIN, clock=lambda: now, boot_s=0.01)
    files = run.paths(tmp_path)
    report = parse_json(files["report"].read_bytes())
    last = report["ledger"][-1]
    assert last["operation"] == "binary64_field"
    assert len(last["raw"]) == 3 and last["returned_s"] == 10.01 and "completed_s" not in last
    assert parse_json(files["receipt"].read_bytes())["finalization"] == "failed"
    with pytest.raises(ValueError, match="child finalization"):
        run.read_saved(tmp_path, "synthetic")


def test_existing_child_files_are_never_overwritten(tmp_path: Path) -> None:
    bundle = paired_bundle()
    assert start(tmp_path, bundle)
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match="existing pair evidence"):
        start(tmp_path, bundle)
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_watchdog_leaves_one_attempt_and_disallows_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = tmp_path / "attempt"

    def timeout(command: list[str], **kwargs: Any) -> NoReturn:
        assert command[:4] == [str(run.PINNED_PYTHON), "-I", "-S", "-B"]
        assert kwargs["timeout"] == 15.0
        raise subprocess.TimeoutExpired(command, 15.0)

    # Exercise the injected watchdog here; the real launcher still requires a fresh interpreter.
    monkeypatch.setattr(run, "require_offline", lambda: None)
    monkeypatch.setattr(run.subprocess, "run", timeout)
    assert not run.supervise(directory, PIN["preparation_sha256"])
    files = run.paths(directory)
    assert parse_json(files["attempt"].read_bytes()) == run.marker(PIN["preparation_sha256"])
    report = parse_json(files["parent"].read_bytes())
    assert report["finalization"] == "failed" and report["error"]["type"] == "TimeoutExpired"
    before = {p: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(FileExistsError):
        run.supervise(directory, PIN["preparation_sha256"])
    assert {p: p.read_bytes() for p in directory.iterdir()} == before


def test_manifest_checks_exact_source_inventory_and_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = tmp_path / run.INPUT_PATH
    inputs.parent.mkdir(parents=True)
    inputs.write_bytes(b"synthetic design input")
    monkeypatch.setattr(run, "INPUT_SHA256", digest(inputs))
    proof = {"preparation_complete": True, "inputs_sha256": digest(inputs)}
    for key, paths in (("tested_source_sha256", run.TESTED), ("reused_source_sha256", run.REUSED)):
        proof[key] = {}
        for name in sorted(paths):
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(name.encode())
            proof[key][name] = digest(path)
    manifest = tmp_path / run.MANIFEST
    manifest.write_bytes(encode(proof))
    sha = digest(manifest)
    assert run.prep_pin(tmp_path, sha, lambda: None)["preparation_sha256"] == sha
    (tmp_path / sorted(run.REUSED)[0]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="prepared or reused SHA-256"):
        run.prep_pin(tmp_path, sha, lambda: None)
    bad = deepcopy(proof)
    bad["reused_source_sha256"].pop(next(iter(run.REUSED)))
    manifest.write_bytes(encode(bad))
    with pytest.raises(ValueError, match="prepared source inventory"):
        run.prep_pin(tmp_path, digest(manifest), lambda: None)
