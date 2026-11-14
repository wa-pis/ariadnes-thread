"""Hash-bound R5.37 inputs, with no ephemeris or force evaluation."""
from __future__ import annotations

from collections.abc import Callable
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = Path("docs/adr/experiments")
DESIGN = ARTIFACTS / "0182-design-inputs.json"
DESIGN_SHA = "5f0ac97e3aae532417d5e2583864837881ad8feb9f24caa41ec045405bc45df3"
PREPARATION = ARTIFACTS / "0183-verification.json"
RUNTIME_KEYS = ("versions", "imports", "native_binary", "conda_build", "resource_build",
                "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime", "kernels")
type Row = dict[str, Any]
type Check = Callable[[], None]


def require(ok: bool, label: str) -> None:
    if not ok:
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


def load(root: Path, name: str, expected: str, check: Check) -> ModuleType:
    path = root / ARTIFACTS / name
    raw = read(root, ARTIFACTS / name, expected, check)
    module = ModuleType("earth_private_" + path.stem.replace("-", "_"))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def design_hashes(root: Path, check: Check) -> dict[str, str]:
    return json.loads(read(root, DESIGN, DESIGN_SHA, check))["input_sha256"]


def preparation(root: Path, check: Check) -> tuple[str, dict[str, str]]:
    check()
    raw = (root / PREPARATION).read_bytes()
    manifest = json.loads(raw)
    require(manifest["preparation_complete"] is True, "verified preparation required")
    require(manifest["design_input_sha256"] == design_hashes(root, check) | {str(DESIGN): DESIGN_SHA},
            "preparation and design inputs disagree")
    tested = manifest["tested_source_sha256"]
    for name, expected in tested.items():
        read(root, name, expected, check)
    return digest(raw), tested


def load_inputs(root: Path = ROOT, check: Check = idle) -> Row:
    """Pin both A engines and validate prior R5.34 study and audit receipts."""
    anchors = design_hashes(root, check)

    def from_design(name: str) -> bytes:
        return read(root, ARTIFACTS / name, anchors[str(ARTIFACTS / name)], check)

    for path, expected in anchors.items():
        read(root, path, expected, check)
    manifest = json.loads(from_design("0181/manifest.json"))
    require(manifest["verdict"] == "passed_conditional_numerical_A", "saved A verdict")
    raw: dict[str, bytes] = {}
    for name, meta in manifest["files"].items():
        stored = from_design("0181/" + name)
        require(digest(stored) == meta["retained_sha256"] and len(stored) == meta["retained_bytes"],
                "A retained bytes")
        content = gzip.decompress(stored) if name.endswith(".gz") else stored
        require(digest(content) == meta["original_sha256"] and len(content) == meta["original_bytes"],
                "A original bytes")
        raw[name.removesuffix(".gz")] = content
    reports = {}
    for phase, cap in (("study", 60), ("audit", 10)):
        report = reports[phase] = json.loads(raw[phase + ".json"])
        records = {k: raw[f"{phase}.{k}.json"] for k in
                   ("attempt", "receipt", "parent-attempt", "parent-receipt")}
        mark, child, parent_mark, parent = (json.loads(v) for v in records.values())
        require(report["contract"] == mark["contract"] == parent["contract"] == parent_mark["contract"] == "ADR0179"
                and report["adapter_mode"] == mark["adapter_mode"] == "reference", "A provenance mode")
        status = report["status" if phase == "study" else "audit_status"]
        require(status == child["status"] == "passed" and parent["returncode"] == 0
                and parent["checkout_frozen"] is True
                and parent["phase"] == parent_mark["phase"] == phase, "A phase status")
        require(parent["revision"] == parent_mark["revision"] == manifest["measured_revision"]
                and parent["preparation_sha256"] == parent_mark["preparation_sha256"]
                == manifest["preparation_sha256"], "A phase revision/preparation")
        require(parent["evidence_sha256"] == child["evidence_sha256"] == digest(raw[phase + ".json"])
                and parent["attempt_sha256"] == digest(records["attempt"])
                and parent["child_receipt_sha256"] == digest(records["receipt"])
                and parent["parent_attempt_sha256"] == digest(records["parent-attempt"]), "A receipt hashes")
        require(report["finalization_gate"] == parent["finalization_gate"] == child["finalization_gate"] == "passed"
                and parent["started_s"] == child["started_s"] == mark["started_s"]
                and 0 <= report["elapsed_before_flush_s"] <= child["elapsed_s"] <= parent["elapsed_s"] < cap,
                "A receipt timing")
    audit, study = reports["audit"], reports["study"]
    require(audit["study_sha256"] == digest(raw["study.json"])
            and audit["study_receipts"] == {k + "_sha256": digest(raw[f"study.{k}.json"]) for k in
                                             ("attempt", "receipt", "parent-attempt", "parent-receipt")},
            "A audit linkage")
    require(audit["checks"] == manifest["audit_checks"] and audit["checks"]["passed"] is True
            and audit["checks"]["complete_profiles"] == 2 and audit["checks"]["comparisons"] == 21
            and audit["checks"]["observations"] == 28, "A audit coverage")
    require(study["identities"]["before"] == study["identities"]["after"], "A before/after snapshot")
    default_loader = "0163-corrected-inputs.py"
    base = load(root, default_loader, anchors[str(ARTIFACTS / default_loader)], check)
    bundle = base.load_inputs(root, check)
    prior = study["inputs"]
    for key in ("initial", "offsets_s", "gm_m3_s2", "radii_m", "source_rows_template", "native_samples",
                "kernel_manifest", "historical_identity"):
        require(bundle[key] == prior[key], "A initial/model/grid anchor: " + key)
    require(not bundle["historical_final_identity_available"], "historical final identity must remain unavailable")
    require(all(study["identities"]["before"][k] == bundle["historical_identity"][k] for k in RUNTIME_KEYS),
            "A common historical/runtime identity")
    profiles = study["profiles"]
    require([v["name"] for v in profiles] == ["normal", "tighter"], "saved A DOP853 profiles")
    for profile, rtol, p, v, maximum, first in zip(profiles,
            (1e-12, 1e-13), (1e-7, 1e-8), (1e-10, 1e-11), (5., 2.5), (1., .5), strict=True):
        require(profile["settings"] == {"rtol": rtol, "atol": [p]*3+[v]*3,
                                         "max_step": maximum, "first_step": first}
                and profile["raw_returned"]["success"] is True and profile["solver_state"]["t_s"] == 300.,
                "saved A DOP853 controls")
        outputs = profile["outputs"]
        require([row["elapsed_s"] for row in outputs] == bundle["offsets_s"]
                and [row["hi_tdb_s"] for row in outputs] ==
                [bundle["initial"]["epoch_tdb_s"]+t for t in bundle["offsets_s"]]
                and outputs[0]["correction"] == [0.]*6, "saved A DOP853 coepochs and initial correction")
        start = outputs[0]["motion"]
        require(start["position_m"] == bundle["initial"]["position_m"]
                and start["velocity_m_s"] == bundle["initial"]["velocity_m_s"], "saved A DOP853 initial state")
    bundle["a_samples"] = {"native": bundle["native_samples"]["tighter"], "dop853": [
        v["motion"]["position_m"] + v["motion"]["velocity_m_s"] for v in profiles[1]["outputs"]]}
    bundle["a_runtime"] = study["identities"]["before"]
    bundle["a_archive_sha256"] = digest(raw["study.json"])
    check()
    return bundle
