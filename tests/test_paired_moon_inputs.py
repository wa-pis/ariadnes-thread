"""Hash and archive checks for ADR0175, using saved metadata only."""
from __future__ import annotations

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
EXPERIMENTS = ROOT / "docs/adr/experiments"
SCRIPTS = [str(EXPERIMENTS / number) for number in ("0176", "0173", "0170", "0167")]


def idle() -> None:
    pass


@pytest.fixture
def inputs(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    for path in reversed(SCRIPTS):
        monkeypatch.syspath_prepend(path)
    return import_module("ariadna_paired_moon_inputs")


@pytest.fixture(scope="module")
def inventory() -> dict[str, Any]:
    return json.loads((EXPERIMENTS / "0175-inputs.json").read_bytes())


def test_loads_exact_pairs_in_isolated_process_without_science_modules() -> None:
    probe = """
import sys
from pathlib import Path
class RejectScience:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in (
            'numpy', 'scipy', 'spiceypy', 'tudatpy', 'space_nav',
            'ariadna_frozen_moon_math', 'ariadna_split_analysis',
            'ariadna_moon_holdout_run', 'ariadna_paired_moon_math',
        ):
            raise AssertionError('unexpected scientific import: ' + fullname)
sys.meta_path.insert(0, RejectScience())
sys.path[:0] = sys.argv[1:-1]
from ariadna_paired_moon_inputs import load_inputs, verify_bound_inputs
root = Path(sys.argv[-1])
bundle = load_inputs(root, lambda: None)
verify_bound_inputs(root, bundle['identity'], lambda: None)
assert len(bundle['rows']) == 11
"""
    completed = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", probe, *SCRIPTS, str(ROOT)],
                               capture_output=True, text=True, timeout=10)
    assert completed.returncode == 0, completed.stderr


def test_observation_pairs_use_saved_capture_and_preserve_separate_motion(inputs: ModuleType) -> None:
    bundle = inputs.load_inputs(ROOT, idle)
    rows = {pair["archive"]["observation_ordinal"]: pair for pair in bundle["rows"]}
    assert list(rows) == [1, 2, 4, 6, 11, 15, 16, 18, 20, 25, 27]
    assert len(bundle["identity"]["retained_evidence_sha256"]) == 41
    assert bundle["gm_m3_s2"].hex() == "0x1.1d616a37fdb33p+42"
    assert bundle["radius_m"] == 1737400.0
    assert rows[1]["captured_state_km_km_s"] == rows[15]["captured_state_km_km_s"]
    assert rows[1]["archive"]["motion"]["q_m"] != rows[15]["archive"]["motion"]["q_m"]
    assert rows[11]["archive"]["lo_s"] < 0 < rows[25]["archive"]["lo_s"]
    assert all(len(pair["captured_state_km_km_s"]) == 6 for pair in rows.values())
    assert all(pair["captured_state_km_km_s"][:3] != pair["archive"]["geocentric_position_km"]
               for pair in rows.values())


@pytest.mark.parametrize("name", [
    "0175-inputs.json", "0171/screen.json.gz", "0171/screen.ledger.jsonl.gz",
    "0174/capture.json", "0174/analysis.ledger.jsonl", "0174/analysis.parent-receipt.json",
])
def test_refuses_changed_bytes_before_decoding_evidence(
    inputs: ModuleType, inventory: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str,
) -> None:
    for relative in [inputs.INPUT_PATH, *inventory["retained_evidence_sha256"]]:
        copy = tmp_path / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        if relative == inputs.EXPERIMENTS + name:
            copy.write_bytes(b"untrusted replacement")
        else:
            copy.symlink_to(ROOT / relative)

    def unexpected(*args: Any) -> None:
        pytest.fail("archive read before all pinned bytes were verified")

    monkeypatch.setattr(inputs, "load_holdout_inputs", unexpected)
    with pytest.raises(ValueError, match=f"archive hash: {Path(name).name}"):
        inputs.load_inputs(tmp_path, idle)


@pytest.mark.parametrize(("change", "match"), [
    ("late-parent", "receipt timeline"),
    ("child-finalization", "child receipt"),
    ("parent-return-code", "parent receipt"),
    ("rebound-journal", "durable journal"),
])
def test_analysis_receipt_rejects_invalid_finalization_even_with_rebound_hashes(
    inputs: ModuleType, inventory: dict[str, Any], change: str, match: str,
) -> None:
    bound = {path: (ROOT / path).read_bytes() for path in inventory["retained_evidence_sha256"]
             if "/0174/" in path}
    prefix = inputs.EXPERIMENTS + "0174/analysis."
    report = inputs.parse_json(bound[prefix + "json"])
    child = inputs.parse_json(bound[prefix + "receipt.json"])
    parent = inputs.parse_json(bound[prefix + "parent-receipt.json"])
    if change == "late-parent":
        parent["external_elapsed_s"] = 10.01
    elif change == "child-finalization":
        child["finalization"] = "failed"
    elif change == "parent-return-code":
        parent["returncode"] = 0
    else:
        bound[prefix + "ledger.jsonl"] += b"\n"
        child["journal_sha256"] = inputs.sha256(bound[prefix + "ledger.jsonl"]).hexdigest()
    bound[prefix + "receipt.json"] = inputs.encode(child)
    parent["child_receipt_sha256"] = inputs.sha256(bound[prefix + "receipt.json"]).hexdigest()
    bound[prefix + "parent-receipt.json"] = inputs.encode(parent)
    with pytest.raises(ValueError, match=match):
        inputs._phase(bound, "analysis", report["identity_pin"], report["input_identity"], idle)


@pytest.mark.parametrize(("mutation", "match"), [
    ("epoch", "R5.27 state analysis mapping"),
    ("lost-ordinal", "R5.27 state analysis mapping"),
    ("state", "R5.27 captured state"),
])
def test_pairing_refuses_changed_joins(
    inputs: ModuleType, monkeypatch: pytest.MonkeyPatch, mutation: str, match: str,
) -> None:
    original = inputs._holdout

    def changed(*args: Any) -> tuple[dict[str, Any], dict[str, Any], list[list[float]]]:
        capture, analysis, states = original(*args)
        row = analysis["rows"][0]
        if mutation == "epoch":
            row["hi_tdb_s"] = nextafter(row["hi_tdb_s"], inf)
        elif mutation == "lost-ordinal":
            row["observation_ordinals"] = row["observation_ordinals"][:1]
        else:
            states[0][0] = nextafter(states[0][0], inf)
        return capture, analysis, states

    monkeypatch.setattr(inputs, "_holdout", changed)
    with pytest.raises(ValueError, match=match):
        inputs.load_inputs(ROOT, idle)


def test_original_motion_bits_are_checked(inputs: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    original = inputs.load_screen_inputs

    def changed(*args: Any) -> dict[str, Any]:
        bundle = original(*args)
        motion = bundle["rows"][11]["motion"]
        motion["q_m"][0] = nextafter(motion["q_m"][0], inf)
        return bundle

    monkeypatch.setattr(inputs, "load_screen_inputs", changed)
    with pytest.raises(ValueError, match="R5.24 original frozen motion"):
        inputs.load_inputs(ROOT, idle)


def test_recheck_requires_full_identity(inputs: ModuleType, inventory: dict[str, Any]) -> None:
    identity = inputs._identity(inventory)
    identity["retained_evidence_sha256"] = {}
    with pytest.raises(ValueError, match="ADR0175 input identity"):
        inputs.verify_bound_inputs(ROOT, identity, idle)
