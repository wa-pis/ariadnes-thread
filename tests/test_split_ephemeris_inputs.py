"""R5.20 metadata tests use saved files only; no SPICE, polynomial or force work."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
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
SCRIPTS = HERE / "0167"


@pytest.fixture
def inputs(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    return import_module("ariadna_split_inputs")


def idle() -> None:
    pass


def test_bound_input_loader_is_stdlib_only() -> None:
    probe = """
import sys
from pathlib import Path
class BlockNative:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in ('numpy', 'scipy', 'spiceypy', 'tudatpy', 'space_nav'):
            raise AssertionError('unexpected scientific import: ' + fullname)
sys.meta_path.insert(0, BlockNative())
sys.path.insert(0, sys.argv[1])
from ariadna_split_inputs import load_inputs
assert len(load_inputs(Path(sys.argv[2]), lambda: None)['references']) == 3
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", probe, str(SCRIPTS), str(ROOT)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_metadata_contract_extracts_exact_saved_references(inputs: ModuleType) -> None:
    bundle = inputs.load_inputs(ROOT, idle)
    assert [row["hi_hex"] for row in bundle["samples_in_probe_order"]] == [
        "0x1.d2d247fbd7e7ap+29", "0x1.d2d247f9d7e7ap+29", "0x1.d2d24fc9d7e7ap+29"]
    assert [row["retained_moon_overall_gate_passed"] for row in bundle["samples_in_probe_order"]] == [
        False, True, True]
    assert bundle["historical_identity"]["kernels"] == bundle["original_ordered_pool_manifest"]
    assert bundle["moon_gm_m3_s2"] == 4902800121846.8
    assert bundle["moon_radius_m"] == 1737400.0
    assert [r["index"] for r in bundle["records"]] == [12192, 12192]
    for ref in bundle["references"]:
        assert len(ref["earth_state_si"]) == len(ref["moon_state_si"]) == 6
        assert all(type(x) is Fraction for x in ref["earth_state_si"] + ref["moon_state_si"])
        assert len(ref["d0_m"]) == 3 and all(type(x) is Fraction for x in ref["d0_m"])
        assert set(ref["a0"]) == set(ref["a0_norm"]) == {80, 100}
        assert all(type(x) is Decimal and x.is_finite() for v in ref["a0"].values() for x in v)
        assert ref["saved_moon_source_residual_m"] == [
            Fraction(v) - ref["moon_state_si"][j] for j, v in enumerate(ref["saved_moon_m"])]


@pytest.mark.parametrize("mutated", ["0166-inputs.json", "0164-corrected-study.json.gz",
                                    "0164-corrected-audit.json.gz", "0165-verification.json"])
def test_any_changed_archival_bytes_stop_before_reference_use(
        inputs: ModuleType, tmp_path: Path, mutated: str) -> None:
    target = tmp_path / "docs/adr/experiments"
    target.mkdir(parents=True)
    metadata = json.loads((HERE / "0166-inputs.json").read_bytes())
    names = ["0166-inputs.json", *(Path(k).name for k in metadata["archival_sha256"])]
    for name in names:
        if name == mutated:
            (target / name).write_bytes(b"invalid altered bytes")
        else:
            (target / name).symlink_to(HERE / name)
    with pytest.raises(ValueError, match="archive hash: " + mutated):
        inputs.load_inputs(tmp_path, idle)


@pytest.fixture(scope="module")
def saved() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    metadata = json.loads((HERE / "0166-inputs.json").read_bytes())
    study, audit = [json.loads(gzip.decompress((HERE / f"0164-corrected-{label}.json.gz").read_bytes()))
                    for label in ("study", "audit")]
    # The validator consumes only this prefix; never copy the 5132-RHS history per mutation.
    study["rhs"] = study["rhs"][:7]
    audit.pop("ledger")
    return metadata, study, audit


@pytest.mark.parametrize("record,path,value,field", [
    (0, ("samples_in_probe_order", 0, "lo_hex"), "-0x0.0p+0", "sample epoch"),
    (0, ("samples_in_probe_order", 0, "source_index"), 0, "sample identifier"),
    (0, ("samples_in_probe_order", 0, "raw_hex", "Earth", 0), "0x0.0p+0", "state bits"),
    (0, ("records", 1, "centre"), 399, "descriptor chain"),
    (0, ("records", 0, "record_interval_tdb_s", 0), 0, "Type 2 interval"),
    (1, ("rhs", 6, "motion", "q_m", 0), 0.0, "study q"),
    (1, ("profiles", 0, "outputs", 0, "motion", "drift_m", 0), 0.0, "rounded drift"),
    (1, ("node_table", 5, "bodies", "Earth", "epoch_tdb_s"), 0.0, "source identity/coepoch"),
    (1, ("observations", 0, "progress", "bodies", "Moon", "exact_geometries_m", "d0", 0,
         "denominator"), "0", "positive denominator"),
    (1, ("observations", 13, "progress", "sources", "Moon", "reference_norms_m_s2", "100",
         "d0"), "NaN", "finite decimal"),
    (1, ("observations", 13, "progress", "sources", "Moon", "gates", "80", "overall",
         "passed"), True, "retained Moon overall verdict"),
    (2, ("counts", "source_rows", "completed"), 26, "verified prefix"),
])
def test_metadata_semantics_reject_mutations(inputs: ModuleType,
                                             saved: tuple[dict[str, Any], ...],
                                             record: int, path: tuple[Any, ...],
                                             value: Any, field: str) -> None:
    changed = list(saved)
    changed[record] = deepcopy(changed[record])
    current: Any = changed[record]
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    with pytest.raises(ValueError, match=field):
        inputs._references(*changed, idle)


def test_deadline_before_archive_read(inputs: ModuleType, tmp_path: Path) -> None:
    def expired() -> None:
        raise ValueError("synthetic deadline")

    with pytest.raises(ValueError, match="synthetic deadline"):
        inputs.load_inputs(tmp_path, expired)
