"""Exercise the coepoch worksheet with synthetic, receipt-bound inputs only."""

from hashlib import sha256
import json
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest


ART = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
type Row = dict[str, Any]


@pytest.fixture(scope="module")
def modules() -> tuple[Row, Row]:
    return (
        run_path(str(ART / "0203-coepoch-worksheet.py")),
        run_path(str(ART / "0203-coepoch-fixtures.py")),
    )


def idle() -> None:
    pass


def read_object(path: Path) -> Row:
    return json.loads(path.read_bytes())


def assert_no_physical_join(report: Row) -> None:
    assert report["physical_status"] == "physical-join-not-established"
    assert report["continuity_residuals"] == dict(epoch_s=None, position_m=None, velocity_m_s=None, mass_kg=None)
    assert report["ideal_mass_kg"] is None
    assert report["ideal_status"] == "ideal-reference-coepoch-computed"


def test_full_one_shard_artificial_workload_finishes_and_reads_back(
    tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path, full=True)
    result = tmp_path / "result"
    assert worksheet["run_synthetic"](pins, result)
    report = worksheet["verify_result"](result)
    assert report["status"] == "passed"
    assert report["stage"] == "R5.56" and report["synthetic"] is True
    assert_no_physical_join(report)
    assert report["forward"] and report["backward"] and report["analytic_evaluations"] == 2
    for counter in ("native_or_scientific_calls", "kernel_accesses", "force_evaluations",
                    "propagation_calls", "fit_attempts"):
        assert report[counter] == 0
    assert report["archive"]["rows"] == 42_862
    assert 16_777_139 <= report["archive"]["raw"] <= 16 * 2**20
    assert 5_176_745 <= report["archive"]["gzip"] <= 5 * 2**20
    assert sum(p.stat().st_size for p in result.iterdir()) <= 128 * 2**10


@pytest.mark.parametrize("path", [
    "inputs/0129-reference-coast.json",
    "inputs/0201-verification.json",
    "archive/study/manifest.json",
    "archive/audit.parent_receipt.json",
    "archive/study/00000.shard",
])
def test_digest_corruption_is_rejected(
    path: str, tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path)
    target = tmp_path / path
    raw = target.read_bytes()
    target.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises((OSError, ValueError)):
        worksheet["evaluate"](pins, idle)


@pytest.mark.parametrize("path", ["archive/study.receipt.json", "archive/study/00000.shard"])
def test_missing_input_is_rejected(path: str, tmp_path: Path, modules: tuple[Row, Row]) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path)
    (tmp_path / path).unlink()
    with pytest.raises((OSError, ValueError)):
        worksheet["evaluate"](pins, idle)


def test_selected_shard_symlink_is_rejected(tmp_path: Path, modules: tuple[Row, Row]) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path)
    shard = tmp_path / "archive" / "study" / "00000.shard"
    renamed = shard.rename(tmp_path / "original.shard")
    shard.symlink_to(renamed)
    with pytest.raises((OSError, ValueError)):
        worksheet["evaluate"](pins, idle)


@pytest.mark.parametrize("variant", [
    "sun-request-epoch", "sun-return-epoch", "kernel-identity", "end-velocity", "state-label",
])
def test_bound_artificial_source_must_still_satisfy_the_contract(
    variant: str, tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path, variant=variant)
    with pytest.raises(ValueError):
        worksheet["evaluate"](pins, idle)


@pytest.mark.parametrize("cap", [
    "input_shards", "bytes_per_raw_shard", "gzip_payload_bytes", "rows",
    "compact_input_bytes", "shard_metadata_bytes",
])
def test_selected_input_caps_stop_evaluation(
    cap: str, tmp_path: Path, modules: tuple[Row, Row], monkeypatch: pytest.MonkeyPatch,
) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path)
    evaluate = worksheet["evaluate"]
    if cap == "input_shards":
        monkeypatch.setitem(evaluate.__globals__["CAPS"], cap, 0)
    else:
        monkeypatch.setitem(evaluate.__globals__["CAPS"], cap, 1)
    value = read_object(pins)
    for k in ("future_audit_maxima", "limits"):
        if k in value and cap in value[k]:
            value[k][cap] = evaluate.__globals__["CAPS"][cap]
            pins.write_text(json.dumps(value))
    with pytest.raises((OSError, ValueError), match="cap|limit|bound|size|metadata|budget|count"):
        evaluate(pins, idle)


def test_result_reservation_is_exclusive_and_readback_checks_digest(
    tmp_path: Path, modules: tuple[Row, Row], monkeypatch: pytest.MonkeyPatch,
) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path)
    result = tmp_path / "result"
    assert worksheet["run_synthetic"](pins, result)
    assert_no_physical_join(worksheet["verify_result"](result))
    original = {p.name: sha256(p.read_bytes()).hexdigest() for p in result.iterdir()}
    with pytest.raises(FileExistsError):
        worksheet["run_synthetic"](pins, result)
    assert {p.name: sha256(p.read_bytes()).hexdigest() for p in result.iterdir()} == original
    with monkeypatch.context() as patch:
        patch.setitem(worksheet["verify_result"].__globals__["CAPS"], "output_bytes", 64)
        with pytest.raises(ValueError, match="cap|limit|bound|size"):
            worksheet["verify_result"](result)
    report = result / "report.json"
    contents = report.read_bytes()
    report.write_bytes(contents + b" ")
    with pytest.raises(ValueError):
        worksheet["verify_result"](result)
    report.write_bytes(contents)
    (result / "late.json").write_text("{}")
    with pytest.raises(ValueError):
        worksheet["verify_result"](result)


def test_invalid_child_report_is_preserved_without_certification(
    tmp_path: Path, modules: tuple[Row, Row],
) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path)
    (tmp_path / "archive" / "study.receipt.json").unlink()
    result = tmp_path / "result"
    assert not worksheet["run_synthetic"](pins, result)
    report = read_object(result / "report.json")
    assert report["status"] == "invalid-evidence"
    assert not report.get("forward") and not report.get("backward")
    assert (result / "receipt.json").is_file()
    with pytest.raises(ValueError):
        worksheet["verify_result"](result)


def test_watchdog_rejects_a_late_attempt(
    tmp_path: Path, modules: tuple[Row, Row], monkeypatch: pytest.MonkeyPatch,
) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path)
    result = tmp_path / "result"
    launch = worksheet["run_synthetic"]
    monkeypatch.setitem(launch.__globals__, "WALL_S", .001)
    assert not launch(pins, result)
    with pytest.raises((OSError, ValueError)):
        worksheet["verify_result"](result)


def test_synthetic_mode_requires_artificial_pins(tmp_path: Path, modules: tuple[Row, Row]) -> None:
    worksheet, fixture = modules
    pins = fixture["build"](tmp_path)
    value = read_object(pins)
    value.pop("synthetic")
    pins.write_text(json.dumps(value))
    result = tmp_path / "result"
    with pytest.raises(ValueError, match="artificial|synthetic"):
        worksheet["run_synthetic"](pins, result)
    assert not result.exists()
