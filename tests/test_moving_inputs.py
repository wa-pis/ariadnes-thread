"""Metadata/hash tests for ADR0159 inputs; no new source fields or motion."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/adr/experiments"
PATH = HERE / "0160-moving-inputs.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("moving_inputs_tests", PATH)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


inputs = load()


@pytest.fixture(scope="module")
def retained() -> tuple[dict[str, Any], dict[str, Any]]:
    """Read existing evidence only; immutable reference fields are not reevaluated."""
    base = inputs.load_base(ROOT)
    bundle = base.load_inputs(ROOT)
    records = {name: json.loads((HERE / name).read_bytes()) for name in inputs.INPUT_SHA}
    return bundle, records


def test_hash_bound_input_loader_exposes_saved_zero_reference() -> None:
    result = inputs.load_inputs(ROOT)
    assert len(result["input_sha256"]) == 6 and len(result["rows"]) == 21
    assert result["input_sha256"] == inputs.INPUT_SHA
    assert result["helper_sha256"] == inputs.HELPER_SHA
    assert list(result["zero_reference"]["sources"]) == ["Sun", "Earth", "Moon"]
    assert list(result["zero_reference"]["totals"]) == ["A", "B"]
    assert result["initial"]["position_m"] == result["position_m"]
    assert result["gm_m3_s2"]["Moon"] == 4902800121846.8
    assert result["identity"]["python_version"] == "3.12.14"
    assert result["identity"]["current_kernel_pool_queried"] is False
    for name, expected in inputs.INPUT_SHA.items():
        assert sha256((HERE / name).read_bytes()).hexdigest() == expected


def test_saved_zero_fields_are_copied_not_reevaluated(retained: tuple[dict[str, Any], ...]) -> None:
    bundle, records = retained
    result = inputs.validate_retained(bundle, records)
    study = records["0158-fixed-gravity-study.json"]
    for row in study["rows"][:3]:
        body = row["source_row"]["body"]
        assert result["zero_reference"]["sources"][body] == row["arms"]["compensated"]
        assert result["zero_reference"]["sources"][body] is not row["arms"]["compensated"]
    result["zero_reference"]["sources"]["Sun"]["acceleration_m_s2"][0] = 0.0
    assert result["zero_reference"]["sources"]["Sun"] != study["rows"][0]["arms"]["compensated"]
    assert result["rows"] is not bundle["rows"]


@pytest.mark.parametrize("target,path,value", [
    ("study", ["contract"], "other"),
    ("study", ["study"], "other"),
    ("study", ["status"], "partial"),
    ("study", ["adapter_mode"], "injected-test"),
    ("study", ["finalization_gate"], "failed"),
    ("study", ["origin"], "Moon"),
    ("study", ["orientation"], "ECLIPJ2000"),
    ("study", ["time_scale"], "UTC"),
    ("study", ["aberration_correction"], "LT"),
    ("study", ["acceleration_units"], "km/s^2"),
    ("study", ["native_calls"], True),
    ("study", ["scientific_imports"], 1),
    ("study", ["reference_replayed"], True),
    ("study", ["mission_accuracy_verified"], True),
    ("study", ["continuous_safety_verified"], True),
    ("study", ["research_only"], False),
    ("study", ["counts", "source_rows", "completed"], 20),
    ("study", ["helper_sha256", "0153-real-ephemeris-oracle.py"], "0" * 64),
    ("study", ["inputs", "initial", "velocity_m_s", 0], 0.0),
    ("study", ["inputs", "gm_m3_s2", "Moon"], 4902800205346.301),
    ("study", ["identity_after", "identity", "python_version"], "3.12.13"),
    ("study", ["rows", 0, "index"], True),
    ("study", ["rows", 0, "source_row", "elapsed_s"], 1.0),
    ("study", ["rows", 0, "source_row", "body"], "Moon"),
    ("study", ["rows", 0, "assessment", "passed"], False),
    ("study", ["totals", 0, "elapsed_s"], 1.0),
    ("study", ["totals", 0, "assessment", "A", "source_order"], ["Moon", "Sun"]),
    ("study", ["totals", 0, "assessment", "A", "passed"], False),
    ("audit", ["scientific_verified"], False),
    ("audit", ["audit_status"], "partial"),
    ("audit", ["adapter_mode"], "injected-test"),
    ("audit", ["source_study_status"], "failed"),
    ("audit", ["finalization_gate"], "failed"),
    ("audit", ["native_calls"], 1),
    ("audit", ["evidence_sha256"], "0" * 64),
    ("audit", ["checks", "complete_saved_data_checked"], False),
    ("audit", ["checks", "first_required_gate_failure"], "source:0"),
    ("audit", ["checks", "source_rows", 0, "assessment_checked"], False),
    ("audit", ["checks", "source_rows", 0, "arms", "compensated", "acceleration_m_s2", 0], 0.0),
    ("audit", ["checks", "model_totals", 0, "models_checked"], ["A"]),
    ("proof", ["study_runs"], True),
    ("proof", ["saved_data_audit_runs"], 2),
    ("proof", ["retries"], 1),
    ("proof", ["all_protected_and_tested_bytes_unchanged"], False),
    ("proof", ["no_new_integration"], False),
    ("proof", ["strict_m3_closed"], True),
    ("proof", ["mission_safety_verified"], True),
    ("proof", ["artifact_sha256", "0158-fixed-gravity-study.json"], "0" * 64),
])
def test_changed_saved_metadata_rejected(retained: tuple[dict[str, Any], ...],
                                        target: str, path: list[Any], value: Any) -> None:
    bundle, original = retained
    records = deepcopy(original)
    names = {"study": "0158-fixed-gravity-study.json", "audit": "0158-fixed-gravity-audit.json",
             "proof": "0158-verification.json"}
    current: Any = records[names[target]]
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    with pytest.raises(ValueError, match="mismatch"):
        inputs.validate_retained(bundle, records)


@pytest.mark.parametrize("name,path", [
    ("0158-fixed-gravity-study.json", ["rows"]),
    ("0158-fixed-gravity-study.json", ["totals"]),
    ("0158-fixed-gravity-audit.json", ["checks", "source_rows"]),
    ("0158-fixed-gravity-audit.json", ["checks", "model_totals"]),
])
def test_incomplete_saved_arrays_rejected(retained: tuple[dict[str, Any], ...],
                                         name: str, path: list[str]) -> None:
    bundle, original = retained
    records = deepcopy(original)
    current: Any = records[name]
    for key in path:
        current = current[key]
    current.pop()
    with pytest.raises(ValueError, match="count"):
        inputs.validate_retained(bundle, records)


def test_six_record_set_required(retained: tuple[dict[str, Any], ...]) -> None:
    bundle, original = retained
    records = dict(original)
    records.pop("0158-verification.json")
    with pytest.raises(ValueError, match="six retained"):
        inputs.validate_retained(bundle, records)


def test_deadline_callback_reaches_saved_record_validation(retained: tuple[dict[str, Any], ...]) -> None:
    calls = 0
    def check() -> None:
        nonlocal calls
        calls += 1
        if calls == 4:
            raise TimeoutError("synthetic metadata deadline")
    with pytest.raises(TimeoutError, match="metadata deadline"):
        inputs.validate_retained(*retained, check)
    assert calls == 4


@pytest.mark.parametrize("name", list(inputs.INPUT_SHA))
def test_each_input_hash_precedes_old_bundle_validation(tmp_path: Path, name: str) -> None:
    here = tmp_path / "docs/adr/experiments"
    here.mkdir(parents=True)
    for helper in ("0157-fixed-gravity-inputs.py", "0145-short-coast-evidence.py"):
        (here / helper).write_bytes((HERE / helper).read_bytes())
    for item in inputs.INPUT_SHA:
        (here / item).write_bytes(b'{}' if item == name else (HERE / item).read_bytes())
    with pytest.raises(ValueError, match="frozen input identity: " + name):
        inputs.load_inputs(tmp_path)


def test_old_input_code_is_hash_checked_before_execution(tmp_path: Path) -> None:
    here = tmp_path / "docs/adr/experiments"
    here.mkdir(parents=True)
    (here / "0157-fixed-gravity-inputs.py").write_text("raise RuntimeError('untrusted input code')")
    with pytest.raises(ValueError, match="input helper identity"):
        inputs.load_base(tmp_path)


@pytest.mark.parametrize("helper", [n for n in inputs.HELPER_SHA if n != "0157-fixed-gravity-inputs.py"])
def test_historical_helpers_stay_pinned(tmp_path: Path, helper: str) -> None:
    here = tmp_path / "docs/adr/experiments"
    here.mkdir(parents=True)
    for name in inputs.INPUT_SHA:
        (here / name).write_bytes((HERE / name).read_bytes())
    for name in inputs.HELPER_SHA:
        (here / name).write_bytes((HERE / name).read_bytes())
    if helper == "0145-short-coast-evidence.py":
        # This parser is checked while bootstrapping before any saved JSON is parsed.
        (here / helper).write_text("raise RuntimeError('untrusted parser')")
        match = "helper identity"
    else:
        (here / helper).write_text("raise RuntimeError('untrusted historical helper')")
        match = "historical helper identity"
    with pytest.raises(ValueError, match=match):
        inputs.load_inputs(tmp_path)


def test_real_metadata_preflight_stays_stdlib_only() -> None:
    script = f"""
import importlib.util,pathlib,sys
path=pathlib.Path({str(PATH)!r})
spec=importlib.util.spec_from_file_location('isolated_moving_inputs',path)
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)
b=m.load_inputs()
assert len(b['rows'])==21 and len(b['input_sha256'])==6
assert not any(n.split('.')[0] in {{'numpy','scipy','spiceypy','tudatpy','space_nav'}} for n in sys.modules)
assert not any(n.endswith('0160_moving_study') for n in sys.modules)
"""
    subprocess.run([sys.executable, "-I", "-S", "-B", "-c", script], check=True, capture_output=True)


def test_cached_bytecode_cannot_replace_checked_input_source(tmp_path: Path) -> None:
    # A timestamp/size-valid cache could substitute unverified code with exec_module.
    from importlib._bootstrap_external import _code_to_timestamp_pyc
    path = tmp_path / "docs/adr/experiments/0157-fixed-gravity-inputs.py"
    path.parent.mkdir(parents=True)
    path.write_bytes((HERE / path.name).read_bytes())
    stat = path.stat()
    cache = Path(importlib.util.cache_from_source(str(path)))
    cache.parent.mkdir()
    cache.write_bytes(_code_to_timestamp_pyc(
        compile("raise RuntimeError('unverified cached input code')", str(path), "exec"),
        int(stat.st_mtime), stat.st_size))
    base = inputs.load_base(tmp_path)
    assert base.T0 == 978995455.2304223
    assert base.POSITION_M == [-47124635282.7281, 128473304107.83153, 55670397503.89886]
