"""R5.23 archive checks exercise metadata only, without the screen or native calls."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from fractions import Fraction
import gzip
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/adr/experiments"
SCRIPTS = HERE / "0170"
PREVIOUS = HERE / "0167"


@pytest.fixture
def inputs(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(PREVIOUS))
    monkeypatch.syspath_prepend(str(SCRIPTS))
    return import_module("ariadna_frozen_moon_inputs")


def idle() -> None:
    pass


def test_stdlib_only_archive_preflight() -> None:
    probe = """
import sys
from pathlib import Path
class BlockScientific:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in ('numpy', 'scipy', 'spiceypy', 'tudatpy', 'space_nav',
                                      'ariadna_split_analysis', 'ariadna_frozen_moon_analysis',
                                      'ariadna_frozen_moon_run'):
            raise AssertionError('unexpected screen or scientific import: ' + fullname)
sys.meta_path.insert(0, BlockScientific())
sys.path[:0] = sys.argv[1:3]
from ariadna_frozen_moon_inputs import load_inputs
assert len(load_inputs(Path(sys.argv[3]), lambda: None)['rows']) == 28
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", probe, str(SCRIPTS),
                             str(PREVIOUS), str(ROOT)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_frozen_row_modes_and_original_controls(inputs: ModuleType) -> None:
    bundle = inputs.load_inputs(ROOT, idle)
    rows = bundle["rows"]
    assert [(row["profile"], row["kind"], row["index"]) for row in rows] == [
        (profile, kind, index) for profile in ("normal", "tighter")
        for kind in ("output", "rhs") for index in range(7)
    ]
    assert Counter(row["source_mode"] for row in rows) == {"measured": 7, "proxy": 21}
    assert all(("G" in row["states"]) == (row["source_mode"] == "measured") for row in rows)
    assert {i for i, row in enumerate(rows) if row["control"] is not None} == {0, 5, 13}
    assert [row["archived_direct"]["passed"] for row in rows[:14]] == [True] * 13 + [False]
    assert all(row["archived_direct"] is None for row in rows[14:])
    assert rows[0]["motion"]["drift_m"][0].hex() == "-0x0.0p+0"
    assert len({row["hi_tdb_s"] for row in rows}) == 19
    assert {row["lo_s"] > 0 for row in rows if row["lo_s"]} == {False, True}
    assert bundle["gm_m3_s2"] == 4902800121846.8
    assert bundle["radius_m"] == 1737400.0
    assert set(bundle["records"]) == {"E", "G"} and all(len(v) == 41 for v in bundle["records"].values())
    assert bundle["identity"]["historical_status"] == "failed"
    assert bundle["identity"]["historical_audit_status"] == "partial"
    assert bundle["identity"]["historical_final_identity_complete"] is False


@pytest.mark.parametrize("name", [
    "0169-inputs.json", "0164-corrected-study.json.gz", "0164-corrected-audit.json.gz",
    "0168/analysis.ledger.jsonl", "0168/capture.parent-receipt.json", "0168-verification.json",
])
def test_changed_bound_file_stops_before_any_semantic_use(
        inputs: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str) -> None:
    metadata = json.loads((HERE / "0169-inputs.json").read_bytes())
    paths = [HERE.relative_to(ROOT) / "0169-inputs.json", *map(Path, metadata["archive_and_evidence_sha256"])]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative.relative_to(HERE.relative_to(ROOT)).as_posix() == name:
            target.write_bytes(b"changed pinned bytes")
        else:
            target.symlink_to(ROOT / relative)

    def unexpected(*_args: Any) -> None:
        pytest.fail("untrusted archive was used")

    monkeypatch.setattr(inputs.gzip, "decompress", unexpected)
    with pytest.raises(ValueError, match=f"archive hash: {Path(name).name}"):
        inputs.load_inputs(tmp_path, idle)


def test_changed_uncompressed_archive_rejected(inputs: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inputs.gzip, "decompress", lambda _raw: b"changed uncompressed bytes")
    with pytest.raises(ValueError, match="uncompressed archive hash: study"):
        inputs.load_inputs(ROOT, idle)


@pytest.fixture(scope="module")
def frozen() -> tuple[dict[str, Any], ...]:
    metadata, previous = [json.loads((HERE / f"{name}-inputs.json").read_bytes()) for name in ("0169", "0166")]
    study = json.loads(gzip.decompress((HERE / "0164-corrected-study.json.gz").read_bytes()))
    study["rhs"] = [row for row in study["rhs"] if row["index"] < 7]
    study.pop("ledger")
    study.pop("trials")
    return metadata, previous, study


def test_wrong_record_words_rejected(inputs: ModuleType, frozen: tuple[dict[str, Any], ...]) -> None:
    metadata, previous, study = frozen
    data = deepcopy(study["inputs"])
    data["source_rows_template"]["Moon"]["segments"][0]["words"][2] = -0.0
    with pytest.raises(ValueError, match="G record words hash"):
        inputs._records(metadata, previous, data)


@pytest.mark.parametrize("change,match", [
    ("lo", "exact frozen coepoch"), ("boundary", "frozen epoch record coverage"),
    ("si", "original signed SI conversion"), ("measured", "R5.17/R5.21 E raw state bits"),
    ("failed-gate", "original failed Moon gate"), ("mapping", "frozen motion row"),
])
def test_archive_metadata_guards_at_fixed_sample(
        inputs: ModuleType, frozen: tuple[dict[str, Any], ...], change: str, match: str) -> None:
    metadata, previous, study = frozen
    metadata, study = deepcopy(metadata), deepcopy(study)
    bound = {name: (ROOT / name).read_bytes() for name in metadata["archive_and_evidence_sha256"]
             if "0168" in name}
    records = inputs._records(metadata, previous, study["inputs"])
    measured, controls = inputs._controls(ROOT, metadata, previous, study, bound, idle)
    if change == "lo":
        study["rhs"][1]["lo_s"] = 0.0
        metadata["rows"][8]["lo_hex"] = 0.0.hex()
    elif change == "boundary":
        t0 = study["inputs"]["initial"]["epoch_tdb_s"]
        records["E"][:2] = [t0 - 1, 1.0]  # At the open upper end.
        assert sum(Fraction(v) for v in records["E"][:2]) == Fraction(t0)
    elif change == "si":
        study["node_table"][0]["bodies"]["Moon"]["state_si"][3] = 0.0
    elif change == "measured":
        measured[metadata["rows"][0]["hi_hex"]]["E"][0] = -0.0
    elif change == "failed-gate":
        del study["observations"][13]["progress"]["sources"]["Moon"]["gates"]["100"]["overall"]
    else:
        study["profiles"][0]["outputs"][0]["index"] = 1
    with pytest.raises(ValueError, match=match):
        inputs._rows(metadata, study, records, measured, controls, idle)


def test_unavailable_direct_result_remains_unavailable(inputs: ModuleType) -> None:
    assert inputs._archived_direct({"progress": {"sources": {}}}) is None


def test_preparation_deadline_can_stop_before_any_archive_io(inputs: ModuleType, tmp_path: Path) -> None:
    def expired() -> None:
        raise ValueError("synthetic deadline")

    with pytest.raises(ValueError, match="synthetic deadline"):
        inputs.load_inputs(tmp_path, expired)
