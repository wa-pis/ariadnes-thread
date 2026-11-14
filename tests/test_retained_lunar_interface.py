"""Validate the private R5.53 audit with artificial, hash-bound archives."""

from hashlib import sha256
import json
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

ART = Path(__file__).resolve().parents[1] / "docs/adr/experiments"
type Row = dict[str, Any]


@pytest.fixture(scope="module")
def modules() -> tuple[Row, Row]:
    return (
        run_path(str(ART / "0200-interface-audit.py")),
        run_path(str(ART / "0200-interface-fixtures.py")),
    )


def idle() -> None:
    pass


def json_object(path: Path) -> Row:
    return json.loads(path.read_bytes())


def assert_no_join(report: Row) -> None:
    assert report["source_status"] == "source-state-authenticated"
    assert report["ideal_status"] == "ideal-reference-coepoch-unavailable"
    assert report["physical_status"] == "physical-join-not-established"
    assert report["continuity_residuals"] == dict(epoch_s=None, position_m=None, velocity_m_s=None, mass_kg=None)
    assert report["receiving"]["ideal"]["exact_coepochs"] == 0


def test_selected_source_is_authenticated_without_physical_join(tmp_path: Path, modules: tuple[Row, Row]) -> None:
    audit, fixture = modules
    pins_path = fixture["build"](tmp_path)
    pins = json_object(pins_path)
    report = audit["evaluate"](pins, tmp_path / "inputs", idle)
    assert_no_join(report)
    outgoing = report["outgoing"]
    assert len(outgoing["state_si"]) == 6
    assert outgoing["epoch_tdb_s"].hex() == pins["export_selector"]["epoch_binary64_hex"]
    assert outgoing["mass_kg"].hex() == pins["export_selector"]["mass_binary64_hex"]
    assert len(report["receiving"]["physical"]) == 5


def test_exact_epoch_of_an_ineligible_target_does_not_establish_join(
    tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    audit, fixture = modules
    pins = json_object(fixture["build"](tmp_path, variant="receiver"))
    report = audit["evaluate"](pins, tmp_path / "inputs", idle)
    assert_no_join(report)
    terminal = report["outgoing"]["epoch_tdb_s"]
    refs = report["receiving"]["physical"]
    matches = [rec for source in refs.values() for rec in source["records"] if rec["epoch_tdb_s"] == terminal]
    assert matches and all("not-coast-entry" in rec["reasons"] for rec in matches)


@pytest.mark.parametrize(("variant", "reason"), [
    ("state", "state|word"),
    ("signed-zero", "state|word"),
    ("epoch", "epoch"),
    ("mass", "mass"),
    ("metric", "radius|metric|direction"),
    ("moon-words", "Moon|moon|operand"),
    ("ideal", "ideal|epoch|coepoch"),
])
def test_authenticated_bytes_can_still_fail_scientific_checks(
    variant: str, reason: str, tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    audit, fixture = modules
    pins = json_object(fixture["build"](tmp_path, variant=variant))
    with pytest.raises(ValueError, match=reason):
        audit["evaluate"](pins, tmp_path / "inputs", idle)


@pytest.mark.parametrize(("phase_path", "mutation"), [
    ("study.receipt.json", "remove"),
    ("audit.parent_receipt.json", "digest"),
    ("study/manifest.json", "digest"),
    ("study/00000.shard", "truncate"),
    ("audit/00000.shard", "digest"),
    ("audit/00000.shard", "symlink"),
])
def test_damaged_archive_never_authenticates(
    phase_path: str, mutation: str, tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    audit, fixture = modules
    pins = json_object(fixture["build"](tmp_path))
    target = Path(pins["external_r551"]["retention_root"]) / phase_path
    raw = target.read_bytes()
    if mutation == "remove":
        target.unlink()
    elif mutation == "symlink":
        stored = tmp_path / "outside-archive.shard"
        target.rename(stored)
        target.symlink_to(stored)
    elif mutation == "digest":
        target.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    else:
        target.write_bytes(raw[:-1])
    with pytest.raises((OSError, ValueError)):
        audit["evaluate"](pins, tmp_path / "inputs", idle)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "float_index", "wrong_kind"])
def test_invalid_selected_record_locator_is_rejected(
    mutation: str, tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    audit, fixture = modules
    pins = json_object(fixture["build"](tmp_path))
    member = pins["external_r551"]["selected_members"][3]
    selectors = member["selectors"]
    if mutation == "missing":
        selectors.pop()
    elif mutation == "duplicate":
        selectors[1] = selectors[0]
    elif mutation == "float_index":
        selectors[0]["row_in_member"] = float(selectors[0]["row_in_member"])
    else:
        selectors[0]["kind"] = "direction"
    with pytest.raises(ValueError):
        audit["evaluate"](pins, tmp_path / "inputs", idle)


@pytest.mark.parametrize("cap", [
    "input_shards", "bytes_per_raw_shard", "raw_bytes", "gzip_payload_bytes", "rows",
    "shard_metadata_bytes", "compact_input_bytes",
])
def test_independent_audit_limits_are_not_advisory(
    cap: str, tmp_path: Path, modules: tuple[Row, Row], monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit, fixture = modules
    pins = json_object(fixture["build"](tmp_path))
    evaluate = audit["evaluate"]
    monkeypatch.setitem(evaluate.__globals__["CAPS"], cap, 1)
    pins["future_audit_maxima"][cap] = 1
    with pytest.raises((OSError, ValueError), match="cap|size|budget|limit|metadata|bound|count"):
        evaluate(pins, tmp_path / "inputs", idle)


def test_child_uses_exclusive_output_and_late_marker_vetoes_pass(
    tmp_path: Path, modules: tuple[Row, Row], monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit, fixture = modules
    pins_path = fixture["build"](tmp_path)
    result_dir = tmp_path / "result"
    assert audit["run_synthetic"](pins_path, result_dir)
    verify = audit["verify_result"]
    report = verify(result_dir)
    assert report["status"] == "passed"
    assert_no_join(report)
    original_outputs = {p.name: sha256(p.read_bytes()).hexdigest() for p in result_dir.iterdir()}
    with pytest.raises(FileExistsError):
        audit["run_synthetic"](pins_path, result_dir)
    assert {p.name: sha256(p.read_bytes()).hexdigest() for p in result_dir.iterdir()} == original_outputs
    with monkeypatch.context() as patch:
        patch.setitem(verify.__globals__["CAPS"], "output_bytes", 64)
        with pytest.raises(ValueError, match="cap|size|budget|limit|bound"):
            verify(result_dir)
    report_path = result_dir / "report.json"
    original = report_path.read_bytes()
    report_path.write_bytes(original + b" ")
    with pytest.raises(ValueError):
        audit["verify_result"](result_dir)
    report_path.write_bytes(original)
    (result_dir / "late.json").touch()
    with pytest.raises(ValueError):
        audit["verify_result"](result_dir)


def test_first_invalid_result_is_preserved_without_certifying_source(
    tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    audit, fixture = modules
    pins_path = fixture["build"](tmp_path)
    (tmp_path / "archive" / "study.receipt.json").unlink()
    result_dir = tmp_path / "result"
    assert not audit["run_synthetic"](pins_path, result_dir)
    failure = json_object(result_dir / "report.json")
    assert failure["status"] == "invalid-evidence"
    assert failure.get("source_status") != "source-state-authenticated"
    assert (result_dir / "receipt.json").is_file()
    with pytest.raises(ValueError):
        audit["verify_result"](result_dir)


def test_watchdog_cannot_accept_a_late_run(
    tmp_path: Path, modules: tuple[Row, Row], monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit, fixture = modules
    pins_path = fixture["build"](tmp_path)
    result_dir = tmp_path / "result"
    run = audit["run_synthetic"]
    monkeypatch.setitem(run.__globals__, "WALL_S", .001)
    assert not run(pins_path, result_dir)
    with pytest.raises((OSError, ValueError)):
        audit["verify_result"](result_dir)


def test_synthetic_mode_cannot_reserve_a_retained_attempt(tmp_path: Path, modules: tuple[Row, Row]) -> None:
    audit, _ = modules
    result_dir = tmp_path / "result"
    with pytest.raises(ValueError, match="synthetic|artificial"):
        audit["run_synthetic"](ART / "0199-design-inputs.json", result_dir)
    assert not result_dir.exists()
