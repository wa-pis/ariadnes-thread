"""Exercise the fixed restart, receipt chain and once-only entry gates."""

from hashlib import sha256
import json
from pathlib import Path
import runpy
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "docs/adr/experiments/0194-extension-launch.py"
INPUTS = ROOT / "docs/adr/experiments/0194-extension-inputs.py"


def no_work() -> None:
    pass


def test_archived_restart_binds_without_science() -> None:
    loaded = runpy.run_path(str(INPUTS))
    _, bundle = loaded["design_inputs"](ROOT, no_work)
    i = bundle["initial"]
    assert i["epoch_tdb_s"].hex() == "0x1.d2d2b41fb54adp+29"
    assert i["epoch_tdb_s"] == bundle["origin_cutoff"]["epoch_tdb_s"] + 600
    assert bundle["mass_kg"].hex() == "0x1.51efd83b95a06p+10"


def test_input_pin_rejects_same_size_replacement(tmp_path: Path) -> None:
    target = tmp_path / "input"
    target.write_bytes(b"1234")
    expected = sha256(b"1234").hexdigest()
    loaded = runpy.run_path(str(INPUTS))
    assert loaded["read"](tmp_path, "input", expected, no_work) == b"1234"
    target.write_bytes(b"1235")
    with pytest.raises(ValueError, match="input SHA256"):
        loaded["read"](tmp_path, "input", expected, no_work)


def make_chain(runner: dict[str, Any], directory: Path) -> tuple[str, str]:
    linked = runner["paths"](directory, "study")
    write = runner["save"]
    revision, preparation = "1"*40, "2"*64
    parent = {"contract": "ADR0193", "phase": "study", "revision": revision,
              "preparation_sha256": preparation}
    parent_sha = write(linked["parent-attempt"], parent)
    start = 123.0
    attempt_sha = write(linked["attempt"], {**parent, "started_s": start})
    data_sha = write(linked["evidence"], {"status": "passed", "contract": "ADR0193",
                                        "adapter_mode": "reference", "preparation_sha256": preparation})
    receipt = {
        "contract": "ADR0193", "phase": "study", "started_s": start,
        "elapsed_s": 1.0, "status": "passed", "finalization_gate": "passed",
        "attempt_sha256": attempt_sha, "evidence_sha256": data_sha,
    }
    child_sha = write(linked["receipt"], receipt)
    write(linked["parent-receipt"], {
        **parent, **receipt, "elapsed_s": 2.0, "checkout_frozen": True, "returncode": 0,
        "parent_attempt_sha256": parent_sha, "child_receipt_sha256": child_sha,
    })
    return revision, preparation


@pytest.mark.parametrize("fault", ["none", "evidence", "receipt", "late"])
def test_study_parent_receipt_binds_chain(tmp_path: Path, fault: str) -> None:
    runner = runpy.run_path(str(RUNNER))
    revision, preparation = make_chain(runner, tmp_path)
    if fault == "none":
        report, pins = runner["read_study"](tmp_path, revision, preparation)
        assert report["status"] == "passed" and len(pins) == 5
    else:
        if fault == "late":
            (tmp_path / "study.late.json").write_text("{}")
        else:
            links = runner["paths"](tmp_path, "study")
            path = links[fault]
            wire = json.loads(path.read_text())
            path.write_text(json.dumps({**wire, "unbound_change": 1}))
        with pytest.raises(ValueError, match="receipt digests|flush exceeded"):
            runner["read_study"](tmp_path, revision, preparation)


def test_no_retry_after_parent_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = runpy.run_path(str(RUNNER))
    (tmp_path / "study.parent-attempt.json").write_text("{}")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "envs/space-nav/bin/python"))
    with pytest.raises(ValueError, match="already attempted"):
        runner["launch"]("study", tmp_path, "a"*64)


def test_receipt_at_hard_deadline_fails() -> None:
    gate = runpy.run_path(str(RUNNER))["receipt_gate"]
    receipt = {"phase": "audit", "contract": "ADR0193", "finalization_gate": "passed",
               "status": "passed", "started_s": 100., "attempt_sha256": "attempt",
               "evidence_sha256": "evidence", "elapsed_s": 9.99}
    assert gate(receipt, "audit", 100., 9.99, "attempt", "evidence", "passed")
    assert not gate(receipt, "audit", 100., 10., "attempt", "evidence", "passed")
    assert not gate({**receipt, "elapsed_s": True}, "audit", 100., 9.99, "attempt", "evidence", "passed")
