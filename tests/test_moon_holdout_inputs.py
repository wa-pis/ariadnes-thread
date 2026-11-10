"""R5.26 archived metadata only; never execute a source query or evaluate a field."""
from __future__ import annotations

from copy import deepcopy
import gzip
from importlib import import_module
import json
from math import inf, nextafter
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs" / "adr" / "experiments"
SCRIPTS = [str(ARCHIVE / number) for number in ("0173", "0170", "0167")]


def idle() -> None:
    pass


@pytest.fixture
def inputs(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    for path in reversed(SCRIPTS):
        monkeypatch.syspath_prepend(path)
    return import_module("ariadna_moon_holdout_inputs")


@pytest.fixture(scope="module")
def evidence() -> tuple[dict[str, Any], dict[str, Any], dict[str, bytes]]:
    inventory, manifest = (json.loads((ARCHIVE / name).read_bytes()) for name in (
        "0172-inputs.json", "0171-verification.json",
    ))
    saved = {}
    for name, entry in manifest["retained_files"].items():
        raw = (ROOT / entry["path"]).read_bytes()
        saved[name] = gzip.decompress(raw) if entry["compression"] == "gzip" else raw
    return inventory, manifest, saved


def test_archived_metadata_loads_in_isolated_process_without_scientific_modules() -> None:
    probe = """
import sys
from pathlib import Path
class RejectScientific:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in ('numpy', 'scipy', 'spiceypy', 'tudatpy', 'space_nav',
                                      'ariadna_frozen_moon_math', 'ariadna_split_analysis',
                                      'ariadna_frozen_moon_run'):
            raise AssertionError('unexpected calculation or native import: ' + fullname)
sys.meta_path.insert(0, RejectScientific())
sys.path[:0] = sys.argv[1:4]
from ariadna_moon_holdout_inputs import load_inputs
bundle = load_inputs(Path(sys.argv[4]), lambda: None)
assert len(bundle['epochs']) == 16
assert sum(len(row['observation_ordinals']) for row in bundle['epochs']) == 21
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", probe, *SCRIPTS, str(ROOT)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_frozen_epoch_order_native_pins_and_nested_archive_binding(inputs: ModuleType) -> None:
    data = inputs.load_inputs(ROOT, idle)
    epochs = data["epochs"]
    assert [row["observation_ordinals"] for row in epochs] == [
        [1, 15], [2, 16], [3, 17], [4, 18], [6, 20],
        [8], [9], [10], [11], [12], [22], [23], [24], [25], [26], [27],
    ]
    assert epochs[0]["hi_tdb_s"].hex() == "0x1.d2d24989d7e7ap+29"
    assert epochs[-1]["hi_tdb_s"].hex() == "0x1.d2d247fad7e7ap+29"
    assert all(len(row["reference_si"]) == 6 and len(row["proxy_position_km"]) == 3 for row in epochs)
    assert data["records"][0]["body"] == 301 and data["records"][0]["centre"] == 399
    assert data["records"][0]["index"] == 12192
    assert data["historical_identity"]["versions"]["spiceypy"]
    assert len(data["original_ordered_pool_manifest"]["kernels"]) == 13
    assert data["local_cspice_file_pin"]["sha256"]
    paths = data["identity"]["retained_evidence_sha256"]
    assert "docs/adr/experiments/0168/capture.parent-receipt.json" in paths
    assert "docs/adr/experiments/0164-corrected-study.json.gz" in paths
    assert "docs/adr/experiments/0171/screen.ledger.jsonl.gz" in paths


@pytest.mark.parametrize("name", [
    "0172-inputs.json", "0171/screen.json.gz", "0171/screen.ledger.jsonl.gz",
    "0171/screen.parent-receipt.json", "0170-verification.json",
])
def test_archive_mutation_rejected_before_decompression(
    inputs: ModuleType, evidence: tuple[dict[str, Any], dict[str, Any], dict[str, bytes]],
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str,
) -> None:
    inventory, _, _ = evidence
    archive_prefix = ARCHIVE.relative_to(ROOT)
    for relative in [Path(inputs.INPUT_PATH), *map(Path, inventory["retained_evidence_sha256"])]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative.relative_to(archive_prefix).as_posix() == name:
            target.write_bytes(b"changed protected bytes")
        else:
            target.symlink_to(ROOT / relative)

    def unexpected(_: bytes) -> bytes:
        pytest.fail("untrusted archive reached decompression")

    monkeypatch.setattr(inputs.gzip, "decompress", unexpected)
    with pytest.raises(ValueError, match=f"archive hash: {Path(name).name}"):
        inputs.load_inputs(tmp_path, idle)


def test_uncompressed_report_digest_independent_of_container(
    inputs: ModuleType, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(inputs.gzip, "decompress", lambda _: b"changed uncompressed bytes")
    with pytest.raises(ValueError, match="R5.24 uncompressed hash"):
        inputs.load_inputs(ROOT, idle)


@pytest.mark.parametrize(("change", "match"), [
    ("late-parent", "receipt timeline"),
    ("child-finalization", "child receipt"),
    ("rebound-journal", "durable journal"),
])
def test_retained_receipt_and_journal_contract(
    inputs: ModuleType, evidence: tuple[dict[str, Any], dict[str, Any], dict[str, bytes]], change: str, match: str,
) -> None:
    _, manifest, raw = evidence
    raw = raw.copy()
    if change == "late-parent":
        parent = inputs.parse_json(raw["screen.parent-receipt.json"])
        parent["external_elapsed_s"] = 10.001
        raw["screen.parent-receipt.json"] = inputs.encode(parent)
    else:
        child = inputs.parse_json(raw["screen.receipt.json"])
        if change == "child-finalization":
            child["finalization"] = "failed"
        else:
            raw["screen.ledger.jsonl"] += b"\n"
            child["journal_sha256"] = inputs._sha(raw["screen.ledger.jsonl"])
        raw["screen.receipt.json"] = inputs.encode(child)
        parent = inputs.parse_json(raw["screen.parent-receipt.json"])
        parent["child_receipt_sha256"] = inputs._sha(raw["screen.receipt.json"])
        raw["screen.parent-receipt.json"] = inputs.encode(parent)
    with pytest.raises(ValueError, match=match):
        inputs._validate_screen(manifest, raw, manifest["preparation_sha256"], idle)


@pytest.mark.parametrize(("change", "match"), [
    ("changed-hi", "frozen epoch hi_tdb_s"),
    ("duplicate-proxy", "rounded proxy bits"),
    ("duplicate-state", "duplicate epoch operands"),
    ("reordered-inventory", "ordered epoch and operand identity"),
    ("lost-duplicate", "ordered epoch and operand identity"),
])
def test_metadata_rejects_changed_row_or_epoch_mapping(
    inputs: ModuleType, evidence: tuple[dict[str, Any], dict[str, Any], dict[str, bytes]], change: str, match: str,
) -> None:
    saved_inventory, _, raw = evidence
    inventory = deepcopy(saved_inventory)
    rows = inputs.parse_json(raw["screen.json"])["rows"]
    frozen = inputs.load_frozen_screen_inputs(ROOT, idle)["rows"]
    if change == "changed-hi":
        rows[1]["hi_tdb_s"] = nextafter(rows[1]["hi_tdb_s"], inf)
    elif change == "duplicate-proxy":
        proxy = rows[15]["geocentric_position_km"]
        proxy[0] = nextafter(proxy[0], inf)
    elif change == "duplicate-state":
        ref = rows[15]["reference_states_si"]["hi"]["G"]
        ref[3] = "0" if ref[3] != "0" else "1"
    elif change == "reordered-inventory":
        inventory["epochs_in_query_order"].reverse()
    else:
        inventory["epochs_in_query_order"][0]["observation_ordinals"] = [1]
    with pytest.raises(ValueError, match=match):
        inputs._epochs(inventory, rows, frozen, idle)


def test_deadline_is_checked_before_archive_io(inputs: ModuleType, tmp_path: Path) -> None:
    def expired() -> None:
        raise ValueError("synthetic deadline")

    with pytest.raises(ValueError, match="synthetic deadline"):
        inputs.load_inputs(tmp_path, expired)
