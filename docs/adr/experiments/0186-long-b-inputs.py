"""Load the R5.37 B prefix and R5.39 pins without evaluating any force or record."""
from __future__ import annotations

from collections.abc import Callable
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = Path("docs/adr/experiments")
DESIGN = ARTIFACTS / "0185-design-inputs.json"
DESIGN_SHA = "a106d2ceac3521dcdfe40b1adb61e86de1c00c96a807299b826b47bbb3c04ec8"
PREPARATION = ARTIFACTS / "0186-verification.json"
ARCHIVE = ARTIFACTS / "0184"
RUNTIME_KEYS = ("versions", "imports", "native_binary", "conda_build", "resource_build",
                "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime", "kernels")
SCRIPTS = tuple(f"0186-long-b-{v}.py" for v in (
    "inputs", "integrator", "reference", "native", "native-replay", "study", "audit", "launch"))
type Row = dict[str, Any]
type Check = Callable[[], None]


def require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(label)


def idle() -> None:
    pass


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def read(root: Path, name: str | Path, expected: str, check: Check) -> bytes:
    check()
    path = (root / name).resolve()
    require(path.is_relative_to(root.resolve()), "path outside checkout")
    raw = path.read_bytes()
    require(digest(raw) == expected, f"input SHA256: {name}")
    check()
    return raw


def preparation(root: Path, check: Check) -> tuple[str, dict[str, str]]:
    check()
    raw = (root / PREPARATION).read_bytes()
    doc = json.loads(raw)
    require(doc["stage"] == "R5.39" and doc["contract"] == "ADR0185"
            and doc["preparation_complete"] is True, "verified R5.39 preparation required")
    design = json.loads(read(root, DESIGN, DESIGN_SHA, check))
    require(doc["design_input_sha256"] == design["immutable_input_sha256"] | {str(DESIGN): DESIGN_SHA},
            "preparation and design inputs disagree")
    tested = doc["tested_source_sha256"]
    require(all(str(ARTIFACTS / name) in tested for name in SCRIPTS), "tested R5.39 scripts missing")
    for name, expected in tested.items():
        read(root, name, expected, check)
    return digest(raw), tested


def _archive(root: Path, anchors: dict[str, str], check: Check) -> tuple[Row, Row]:
    def saved(name: str) -> bytes:
        key = str(ARCHIVE / name)
        return read(root, key, anchors[key], check)

    manifest = json.loads(saved("manifest.json"))
    require(manifest["stage"] == "R5.37"
            and manifest["verdict"] == "passed_conditional_short_coast_earth_sensitivity", "R5.37 B verdict")
    contents, reports = {}, {}
    for name, meta in manifest["files"].items():
        stored = saved(name)
        require(digest(stored) == meta["retained_sha256"] and len(stored) == meta["retained_bytes"],
                "R5.37 retained bytes")
        raw = gzip.decompress(stored) if name.endswith(".gz") else stored
        require(digest(raw) == meta["original_sha256"] and len(raw) == meta["original_bytes"],
                "R5.37 original bytes")
        contents[name.removesuffix(".gz")] = raw
    for phase, limit in (("study", 60.), ("audit", 10.)):
        raw = contents[phase + ".json"]
        report = reports[phase] = json.loads(raw)
        marker, child, parent_marker, parent = (json.loads(contents[f"{phase}.{suffix}.json"]) for suffix in
                                                ("attempt", "receipt", "parent-attempt", "parent-receipt"))
        require(report["contract"] == marker["contract"] == parent_marker["contract"] == parent["contract"]
                == "ADR0182" and marker["adapter_mode"] == report["adapter_mode"] == "reference",
                "R5.37 contract and mode")
        require(report["status" if phase == "study" else "audit_status"] == child["status"] == "passed"
                and parent["returncode"] == 0 and parent["checkout_frozen"] is True and not parent["stderr"],
                "R5.37 phase status")
        require(parent["phase"] == parent_marker["phase"] == phase
                and parent["revision"] == parent_marker["revision"] == manifest["measured_revision"]
                and parent["preparation_sha256"] == parent_marker["preparation_sha256"] ==
                manifest["preparation_sha256"], "R5.37 phase provenance")
        require(parent["evidence_sha256"] == child["evidence_sha256"] == digest(raw)
                and parent["attempt_sha256"] == digest(contents[f"{phase}.attempt.json"])
                and parent["child_receipt_sha256"] == digest(contents[f"{phase}.receipt.json"])
                and parent["parent_attempt_sha256"] == digest(contents[f"{phase}.parent-attempt.json"]),
                "R5.37 receipt linkage")
        require(report["finalization_gate"] == parent["finalization_gate"] == child["finalization_gate"] == "passed"
                and marker["started_s"] == child["started_s"] == parent["started_s"]
                and 0 <= report["elapsed_before_flush_s"] <= child["elapsed_s"] <= parent["elapsed_s"] <= limit,
                "R5.37 receipt timing")
    study, audit = reports["study"], reports["audit"]
    require(audit["study_sha256"] == digest(contents["study.json"]) and audit["study_receipts"] ==
            {key + "_sha256": digest(contents[f"study.{key}.json"])
             for key in ("attempt", "receipt", "parent-attempt", "parent-receipt")}, "R5.37 audit receipt linkage")
    require(audit["checks"] == manifest["audit_checks"] and audit["checks"]["passed"] is True
            and audit["checks"]["complete_native_profiles"] == audit["checks"]["complete_profiles"] == 2
            and audit["checks"]["native_telemetry"] == 14 and audit["checks"]["observations"] == 28
            and audit["checks"]["comparisons"] == 21 and audit["checks"]["effects"] == 7
            and all(type(audit[k]) is int and audit[k] == 0 for k in
                    ("native_calls", "scientific_imports", "kernel_loads", "spacecraft_propagations")),
            "R5.37 B audit coverage")
    return study, manifest


def _state(raw: object) -> list[float]:
    require(type(raw) is list and len(raw) == 6 and
            all(type(x) in (int, float) and math.isfinite(x) for x in raw), "B prefix finite six-state")
    return [float(x) for x in raw]


def _same_state(first: list[float], second: list[float]) -> bool:
    return [x.hex() for x in _state(first)] == [x.hex() for x in _state(second)]


def load_inputs(root: Path = ROOT, check: Check = idle) -> Row:
    """Bind the prior B profiles and cover the 600 s interval by metadata only."""
    design = json.loads(read(root, DESIGN, DESIGN_SHA, check))
    anchors = design["immutable_input_sha256"]
    study, manifest = _archive(root, anchors, check)
    for name, expected in anchors.items():
        if not Path(name).is_relative_to(ARCHIVE):
            read(root, name, expected, check)
    inputs = study["inputs"]
    initial, t0 = inputs["initial"], design["epoch_tdb_s"]
    prior_start = design["initial_state"]
    t0_state = _state(initial["position_m"] + initial["velocity_m_s"])
    require(initial["epoch_tdb_s"] == prior_start["epoch_tdb_s"] == t0 and
            _same_state(t0_state, prior_start["position_m"] + prior_start["velocity_m_s"]), "B initial state")
    require(study["model"] == "B" and study["origin"] == prior_start["origin"] == "SSB"
            and study["orientation"] == prior_start["orientation"] == "J2000"
            and study["aberration_correction"] == "NONE" and study["time_scale"] == "TDB"
            and all(inputs[k] == design[k] for k in ("gm_m3_s2", "radii_m"))
            and inputs["kernel_manifest"]["loaded_kernel_count"] == 13, "B physical inputs")
    runtime = study["identities"]["before"]
    require(runtime == study["identities"]["after"] and runtime["revision"] == manifest["measured_revision"]
            and runtime["dirty"] == []
            and all(runtime[k] == inputs["historical_identity"][k] for k in RUNTIME_KEYS)
            and runtime["kernels"] == inputs["kernel_manifest"], "archived B runtime identity")
    offsets = design["offsets_s"]
    require(offsets == list(range(0, 601, 50)) and offsets[:7] == inputs["offsets_s"] == [
        row["elapsed_s"] for row in study["node_table"]], "B exact offsets and prefix")
    epochs = [t0 + s for s in offsets]
    require(epochs == design["coepochs_tdb_s"] and epochs[-1] == design["end_tdb_s"], "B exact coepochs")
    metadata = {(r["body_id"], r["centre_id"]): r for r in design["retained_record_metadata"]}
    require(set(metadata) == {(10, 0), (301, 399), (399, 0)}, "three pinned source records")
    seen = set()
    for source in inputs["source_rows_template"].values():
        for segment in source["segments"]:
            key = (segment["body"], segment["centre"])
            row = metadata[key]
            mid, half = segment["words"][:2]
            span, record = row["segment_interval_tdb_s"], row["record_interval_tdb_s"]
            require([segment["first_tdb_s"], segment["last_tdb_s"]] == span
                    and [mid-half, mid+half] == record and segment["type"] == row["type"] == 2
                    and segment["frame"] == row["frame_id"] == 1 and segment["address"] == row["record_address"]
                    and segment["index"] == row["record_index"] and Path(segment["path"]).name == row["segment_file"]
                    and max(span[0], record[0]) < t0 < epochs[-1] < min(span[1], record[1]),
                    "B retained Type 2 coverage")
            seen.add(key)
    require(seen == set(metadata), "required source coverage")
    prefix: dict[str, dict[str, list[list[float]]]] = {"native": {}, "dop853": {}}
    for name, step, cfg, native, dop in zip(("normal", "tighter"), design["native_steps_s"],
            design["dop853_settings"], study["native_profiles"], study["profiles"], strict=True):
        result, outputs = native["result"], dop["outputs"]
        require(native["name"] == dop["name"] == name and native["step_s"] == step
                and result["retained_states"] == int(300/step)+1 and
                [row["epoch_tdb_s"] for row in result["samples"]] == epochs[:7] and
                [row["hi_tdb_s"] for row in outputs] == epochs[:7] and
                [row["elapsed_s"] for row in outputs] == offsets[:7] and dop["settings"] == cfg
                and dop["raw_returned"]["success"] is True and dop["solver_state"]["t_s"] == 300.,
                "B prefix profiles/coepochs")
        prefix["native"][name] = [_state(row["state"]) for row in result["samples"]]
        prefix["dop853"][name] = [_state(row["motion"]["position_m"] + row["motion"]["velocity_m_s"])
                                 for row in outputs]
        require(all(_same_state(arm[name][0], t0_state) for arm in prefix.values()), "B exact prefix start")
    check()
    keys = ("initial", "gm_m3_s2", "radii_m", "source_rows_template", "kernel_manifest", "historical_identity",
            "protected_sha256")
    return {**{key: inputs[key] for key in keys}, "offsets_s": offsets,
            "b_prefix": prefix, "b_runtime": runtime, "input_sha256": anchors | {str(DESIGN): DESIGN_SHA},
            "b_archive_sha256": manifest["files"]["study.json.gz"]["original_sha256"]}
