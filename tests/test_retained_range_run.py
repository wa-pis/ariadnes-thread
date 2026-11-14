"""Exercise the once-only saved-data audit's evidence and timing gates."""

from collections.abc import Callable
from hashlib import sha256
import json
from pathlib import Path
import runpy
from typing import Any

import pytest

RUNNER = Path(__file__).resolve().parents[1] / "docs/adr/experiments/0192-range-run.py"


def test_binds_reports_and_blocks_replay(tmp_path: Path) -> None:
    execute = runpy.run_path(str(RUNNER))["execute"]

    def work(report: dict[str, Any], check: Callable[[], None]) -> None:
        report["synthetic_marker"] = 1
        check()

    assert execute(tmp_path, work) == 0
    evidence = tmp_path / "evidence.json"
    receipt = json.loads((tmp_path / "receipt.json").read_bytes())
    assert receipt["status"] == receipt["finalization_gate"] == "passed"
    assert receipt["evidence_sha256"] == sha256(evidence.read_bytes()).hexdigest()
    assert receipt["attempt_sha256"] == sha256((tmp_path / "attempt.json").read_bytes()).hexdigest()
    with pytest.raises(FileExistsError, match="do not retry"):
        execute(tmp_path, work)


def test_preserves_partial_failure(tmp_path: Path) -> None:
    execute = runpy.run_path(str(RUNNER))["execute"]

    def work(report: dict[str, Any], check: Callable[[], None]) -> None:
        report["synthetic_marker"] = 1
        check()
        raise ValueError("bad mesh")

    assert execute(tmp_path, work) == 2
    evidence = json.loads((tmp_path / "evidence.json").read_bytes())
    receipt = json.loads((tmp_path / "receipt.json").read_bytes())
    assert receipt["status"] == evidence["status"] == "partial"
    assert evidence["synthetic_marker"] == 1
    assert "bad mesh" in evidence["error"]


def test_late_finalization_invalidates_pass(tmp_path: Path) -> None:
    execute = runpy.run_path(str(RUNNER))["execute"]
    times = iter((0.0, 0.0, 0.0, 1.0, 2.0, 11.0, 11.0))
    assert execute(tmp_path, lambda report, check: None, lambda: next(times)) == 2
    report = json.loads((tmp_path / "evidence.json").read_bytes())
    receipt = json.loads((tmp_path / "receipt.json").read_bytes())
    assert report["status"] == "passed"
    assert (receipt["status"], receipt["finalization_gate"]) == ("partial", "failed")
    assert receipt["elapsed_s"] == 11.0
