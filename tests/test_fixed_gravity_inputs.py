"""Synthetic Type2 provenance fixtures; no retained-source gravity evaluation."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import importlib.util
import math
from pathlib import Path
import struct
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/adr/experiments"


def module(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location("inputs_test_" + name[:4] + name[5:10], HERE / name)
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


inputs = module("0157-fixed-gravity-inputs.py")
oracle = inputs.load_oracle(ROOT)


def fixture_bundle() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Build exact linear polynomials and a complete synthetic native-return ledger."""
    initial = {"epoch_tdb_s": inputs.T0, "epoch_utc": "fixture epoch", "label": "fixture",
               "orientation": "J2000", "origin": "SSB", "position_m": list(inputs.POSITION_M),
               "velocity_m_s": list(inputs.VELOCITY_M_S)}
    boundary = {"rows": [{"body": "Moon", "stored_endpoint": deepcopy(initial),
                           "gm_m3_s2": inputs.GM_M3_S2["Moon"]}]}
    kernels = [{"name": f"fixture-{i}.bsp", "version": "fixture", "type": "SPK",
                "source": None, "size_bytes": 100, "sha256": "a" * 64} for i in range(13)]
    kernels[7].update(name=inputs.KERNEL_NAME, sha256=inputs.KERNEL_SHA)
    manifest = {"kernel_source": "tudatpy-standard", "loaded_kernel_count": 13,
                "spiceypy_version": "8.2.0", "kernels": kernels, "kernel_list_status": "complete"}
    study = {"inputs": {"initial": initial, "state_si": initial["position_m"] + initial["velocity_m_s"],
             "origin": "SSB", "orientation": "J2000", "time_scale": "TDB seconds since J2000",
             "position_units": "m", "velocity_units": "m/s", "original_kernel_manifest": manifest},
             "models": {"A": {"model_id": "r5-ssb-sun-moon-point-v1",
                               "included_sources": ["Sun", "Moon"],
                               "gm_m3_s2": dict(inputs.GM_M3_S2)}}}
    identity = {"kernels": deepcopy(manifest), "versions": {"python": "3.12.14", "tudatpy": "1.0.0",
                "tudat-resources": "2.4", "numpy": "1.26.4", "scipy": "1.17.1", "spiceypy": "8.2.0"},
                "dirty": [], "source_sha256": {
                    "docs/adr/experiments/0153-real-ephemeris-oracle.py": inputs.ORACLE_SHA}}
    source: dict[str, Any] = {"stage": "R5.8 real ephemeris time boundary", "status": "passed",
        "budget_s": 60.0, "origin": "SSB", "orientation": "J2000", "time_scale": "TDB",
        "aberration_correction": "NONE", "state_units": ["m"] * 3 + ["m/s"] * 3,
        "t0_tdb_s": inputs.T0, "t0_hex": inputs.T0.hex(), "offsets_s": list(inputs.OFFSETS),
        "rows": [], "spacecraft_propagations": 0, "force_evaluations": 0,
        "reference_replayed": False, "counts": {}, "native_returns": [],
        "identity_before": identity, "identity_after": deepcopy(identity), "elapsed_before_flush_s": 1.0}
    for elapsed in inputs.OFFSETS:
        epoch = Fraction(inputs.T0) + Fraction(elapsed)
        hi = float(epoch)
        lo = float(epoch - Fraction(hi))
        for body, targets in inputs.CHAINS.items():
            segments = []
            raw = [Fraction()] * 6
            for target in targets:
                begin = 100 * target
                end = begin + 11
                first, last = inputs.T0 - 1000, inputs.T0 + 1000
                packed = struct.unpack("<3d", struct.pack("<6i", target,
                    inputs.CENTRES[target], 1, 2, begin, end))
                words = [inputs.T0, 1000.0, 100000.1 * target, 0.125,
                         -20000.25 * target, -0.25, 30000.5 * target, 0.5]
                segments.append({"body": target, "centre": inputs.CENTRES[target], "frame": 1,
                    "type": 2, "first_tdb_s": first, "last_tdb_s": last, "begin": begin,
                    "end": end, "label": str(target), "path": "/synthetic/" + inputs.KERNEL_NAME,
                    "descriptor": [first, last, *packed], "words": words,
                    "trailer": [first, 2000.0, 8.0, 1.0], "address": begin, "index": 0})
                for axis in range(3):
                    constant, slope = map(Fraction, words[2 + 2 * axis:4 + 2 * axis])
                    raw[axis] += constant + slope * (Fraction(hi) - Fraction(inputs.T0)) / 1000
                    raw[axis + 3] += slope / 1000
            raw_float = [float(v) for v in raw]
            state = [v * 1000 for v in raw_float]
            records = [oracle.parse_record(s["words"]) for s in segments]
            source["rows"].append({"body": body, "elapsed_s": elapsed, "elapsed_hex": elapsed.hex(),
                "hi_tdb_s": hi, "hi_hex": hi.hex(), "lo_s": lo, "lo_hex": lo.hex(),
                "segments": segments, "state_km_km_s": raw_float, "state_si": state,
                "assessment": oracle.assess(state, records, hi, lo)})
    cached = set()
    seen_handle = False
    for row in source["rows"]:
        for segment in row["segments"]:
            append_return(source, "selections", [2, segment["descriptor"], segment["label"]])
            append_return(source, "descriptors", [segment[k] for k in (
                "body", "centre", "frame", "type", "first_tdb_s", "last_tdb_s", "begin", "end")])
            if not seen_handle:
                append_return(source, "paths", ["SPK", "", 2])
                seen_handle = True
            if segment["body"] not in cached:
                append_return(source, "arrays", segment["trailer"])
                append_return(source, "arrays", segment["words"])
                cached.add(segment["body"])
        append_return(source, "states", [row["state_km_km_s"], 0.0])
    return boundary, study, source


def append_return(source: dict[str, Any], name: str, returned: Any) -> None:
    source["native_returns"].append({"call": name, "returned": deepcopy(returned)})
    for key in (name, name + "_returned"):
        source["counts"][key] = source["counts"].get(key, 0) + 1


@pytest.fixture
def bundle() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return fixture_bundle()


def test_valid_synthetic_bundle_preserves_si_and_original_rows(bundle: tuple[dict[str, Any], ...]) -> None:
    result = inputs.validate_bundle(*bundle, oracle)
    assert result["rows"] is bundle[2]["rows"]
    assert result["position_m"] == inputs.POSITION_M
    assert result["gm_m3_s2"]["Moon"] == 4902800121846.8
    assert result["input_sha256"] == result["identity"] == {}
    assert result["source_provenance"]["historical_loaded_memory_verified"] is False
    assert result["source_provenance"]["adr0148_final_identity_available"] is False
    assert [r["body"] for r in result["rows"]] == ["Sun", "Earth", "Moon"] * 7
    assert any(r["lo_s"] > 0 for r in result["rows"])
    assert any(r["lo_s"] < 0 for r in result["rows"])


@pytest.mark.parametrize("mutation,match", [
    ("endpoint", "exact endpoint"), ("six-state", "frozen initial"),
    ("moon-gm", "frozen GM"), ("gm-bool", "nonboolean"), ("gm-missing", "GM source"),
    ("model-sources", "source contract"), ("row-schema", "source row schema"),
    ("units", "source conventions"), ("origin", "source conventions"),
    ("time-scale", "source conventions"), ("aberration", "source conventions"),
    ("offset", "saved offsets"), ("time-hex", "numeric/hex"), ("time-split", "epoch"),
    ("body-order", "body/offset order"), ("row-count", "row count"),
    ("km-conversion", "km-to-SI"), ("nonfinite", "finite nonboolean"),
    ("assessment", "saved assessment"), ("count-bool", "integer"),
    ("count", "attempted/returned"), ("raw-state", "raw state"),
    ("raw-order", "raw-return order"), ("raw-extra", "extra return"),
    ("snapshot", "before/after"), ("kernel-order", "original ordered"),
    ("kernel-count", "13-kernel"), ("kernel-sha", "selected kernel identity"),
    ("source-helper", "helper identity"),
])
def test_corrupt_synthetic_bundle_rejected(bundle: tuple[dict[str, Any], ...],
                                         mutation: str, match: str) -> None:
    boundary, study, source = bundle
    row = source["rows"][0]
    if mutation == "endpoint":
        boundary["rows"][0]["stored_endpoint"]["label"] = "changed"
    elif mutation == "six-state":
        study["inputs"]["initial"]["position_m"][0] += 1
        boundary["rows"][0]["stored_endpoint"]["position_m"][0] += 1
    elif mutation == "moon-gm":
        study["models"]["A"]["gm_m3_s2"]["Moon"] = 4902800205346.301
    elif mutation == "gm-bool":
        study["models"]["A"]["gm_m3_s2"]["Sun"] = True
    elif mutation == "gm-missing":
        del study["models"]["A"]["gm_m3_s2"]["Earth"]
    elif mutation == "model-sources":
        study["models"]["A"]["included_sources"] = ["Sun"]
    elif mutation == "row-schema":
        row["unexpected"] = "not part of the saved schema"
    elif mutation == "units":
        source["state_units"][0] = "km"
    elif mutation == "origin":
        source["origin"] = "Moon"
    elif mutation == "time-scale":
        source["time_scale"] = "UTC"
    elif mutation == "aberration":
        source["aberration_correction"] = "LT"
    elif mutation == "offset":
        source["offsets_s"][1] *= 2
    elif mutation == "time-hex":
        row["lo_hex"] = "0x1p0"
    elif mutation == "time-split":
        row["lo_s"] = inputs.U
    elif mutation == "body-order":
        source["rows"][0], source["rows"][1] = source["rows"][1], row
    elif mutation == "row-count":
        source["rows"].pop()
    elif mutation == "km-conversion":
        row["state_si"][0] = math.nextafter(row["state_si"][0], math.inf)
    elif mutation == "nonfinite":
        row["state_km_km_s"][0] = math.inf
    elif mutation == "assessment":
        row["assessment"]["passed"] = False
    elif mutation == "count-bool":
        source["counts"]["paths"] = True
    elif mutation == "count":
        source["counts"]["arrays"] += 1
    elif mutation == "raw-state":
        next(r for r in source["native_returns"] if r["call"] == "states")["returned"][0][0] += 1
    elif mutation == "raw-order":
        source["native_returns"][0]["call"] = "states"
    elif mutation == "raw-extra":
        source["native_returns"].append({"call": "states", "returned": [[], 0.0]})
    elif mutation == "snapshot":
        source["identity_after"]["dirty"].append("changed")
    elif mutation == "kernel-order":
        study["inputs"]["original_kernel_manifest"]["kernels"].reverse()
    elif mutation == "kernel-count":
        study["inputs"]["original_kernel_manifest"]["loaded_kernel_count"] = 12
    elif mutation == "kernel-sha":
        study["inputs"]["original_kernel_manifest"]["kernels"][7]["sha256"] = "0" * 64
    elif mutation == "source-helper":
        for key in ("identity_before", "identity_after"):
            source[key]["source_sha256"]["docs/adr/experiments/0153-real-ephemeris-oracle.py"] = "0" * 64
    with pytest.raises(ValueError, match=match):
        inputs.validate_bundle(boundary, study, source, oracle)


@pytest.mark.parametrize("mutation,match", [
    ("body", "body/centre/frame"), ("centre", "body/centre/frame"),
    ("frame", "body/centre/frame"), ("type", "body/centre/frame"),
    ("coverage-hi", "segment coverage"), ("coverage-exact", "segment coverage"),
    ("descriptor", "descriptor integer"), ("directory", "directory alignment"),
    ("record-coverage", "record coverage"), ("address", "record address"),
    ("index", "record index"), ("trailer", "trailer layout"),
    ("path", "kernel path"), ("chain", "chain length"),
])
def test_selected_type2_metadata_rejected(bundle: tuple[dict[str, Any], ...],
                                         mutation: str, match: str) -> None:
    row = deepcopy(bundle[2]["rows"][3])
    segment = row["segments"][0]
    if mutation in ("body", "centre", "frame", "type"):
        segment[mutation] += 1
    elif mutation == "coverage-hi":
        segment["first_tdb_s"] = row["hi_tdb_s"] + 1
    elif mutation == "coverage-exact":
        segment["last_tdb_s"] = row["hi_tdb_s"]
    elif mutation == "descriptor":
        segment["descriptor"][2] = 0.0
    elif mutation == "directory":
        segment["words"][0] += 1
    elif mutation == "record-coverage":
        row["hi_tdb_s"] = inputs.T0 + 999.0
        row["lo_s"] = 2.0
        segment["last_tdb_s"] = inputs.T0 + 2000.0
        segment["descriptor"][1] = segment["last_tdb_s"]
    elif mutation == "address":
        segment["address"] += 1
    elif mutation == "index":
        segment["index"] += 1
    elif mutation == "trailer":
        segment["trailer"][1] = -1.0
    elif mutation == "path":
        segment["path"] = "/synthetic/other.bsp"
    elif mutation == "chain":
        row["segments"].append(deepcopy(segment))
    with pytest.raises(ValueError, match=match):
        inputs.records_for_row(row, oracle)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'[]'])
def test_strict_json_boundary(raw: bytes) -> None:
    with pytest.raises(ValueError):
        inputs.strict_json().parse(raw)


def test_hash_failure_precedes_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "docs/adr/experiments"
    target.mkdir(parents=True)
    (target / next(iter(inputs.INPUT_SHA))).write_bytes(b'{"synthetic":true}')
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("identity mismatch must stop before operand validation")
    monkeypatch.setattr(inputs, "validate_bundle", forbidden)
    with pytest.raises(ValueError, match="frozen input identity"):
        inputs.load_inputs(tmp_path)


def test_helper_hash_failure_precedes_import(tmp_path: Path) -> None:
    target = tmp_path / "docs/adr/experiments"
    target.mkdir(parents=True)
    (target / "0153-real-ephemeris-oracle.py").write_text("raise RuntimeError('must not execute')")
    with pytest.raises(ValueError, match="helper identity"):
        inputs.load_oracle(tmp_path)


def test_cooperative_check_reaches_reconstruction(bundle: tuple[dict[str, Any], ...]) -> None:
    count = 0
    def check() -> None:
        nonlocal count
        count += 1
        if count == 20:
            raise TimeoutError("synthetic deadline")
    with pytest.raises(TimeoutError, match="synthetic deadline"):
        inputs.validate_bundle(*bundle, oracle, check)
    assert count == 20


def test_current_pinned_interpreter_identity() -> None:
    identity = inputs.interpreter_identity()
    assert identity["python_version"] == "3.12.14"
    assert Path(identity["prefix"]).name == "space-nav"
    assert identity["executable_sha256"] == sha256(Path(identity["executable"]).read_bytes()).hexdigest()
    assert identity["current_kernel_pool_queried"] is False


def test_imports_stay_stdlib_only() -> None:
    script = f"""
import importlib.util, pathlib, sys
path = pathlib.Path({str(HERE / '0157-fixed-gravity-inputs.py')!r})
spec = importlib.util.spec_from_file_location('isolated_inputs', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.load_oracle(path.parents[3])
module.strict_json()
assert not any(name.split('.')[0] in {{'numpy','scipy','spiceypy','tudatpy','space_nav'}} for name in sys.modules)
"""
    subprocess.run([sys.executable, "-I", "-c", script], check=True, capture_output=True)


@pytest.mark.parametrize("value", [True, math.nan, math.inf, 10**1000, "1"])
def test_nonfinite_or_nonbinary64_operand_rejected(value: Any) -> None:
    with pytest.raises(ValueError, match="finite"):
        inputs.number(value, "synthetic operand")


@pytest.mark.parametrize("mutation,match", [("version", "3.12.14"), ("prefix", "space-nav")])
def test_current_interpreter_mismatch_rejected(monkeypatch: pytest.MonkeyPatch,
                                               tmp_path: Path, mutation: str, match: str) -> None:
    if mutation == "version":
        monkeypatch.setattr(inputs.sys, "version_info", (3, 12, 13))
    else:
        monkeypatch.setattr(inputs.sys, "prefix", str(tmp_path / "space-nav"))
    with pytest.raises(ValueError, match=match):
        inputs.interpreter_identity()
