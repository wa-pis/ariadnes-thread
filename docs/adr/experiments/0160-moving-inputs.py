"""ADR0159 frozen moving-probe operands; metadata only, no force evaluations."""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
Check = Callable[[], None]
INPUT_SHA = {
    "0136-retained-boundary-audit.json":
        "81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063",
    "0148-short-coast-study.json":
        "8bbe6f5f7d08f4e220ee3cff450488531da0776b8a69cb4c37e1c9af9872b096",
    "0155-real-source.json":
        "278b094cff6dd417ac15c04d3b4e4da137acede17de7147babd72fe9e3812102",
    "0158-fixed-gravity-study.json":
        "08b37c96df1bff965e0a93015085e5acf733747ddd1f97805b5b21f135bd02ed",
    "0158-fixed-gravity-audit.json":
        "19f89eda69d5d4b184a21f611a07287ea29c41041f72d6e305c1cb896c2d442d",
    "0158-verification.json":
        "834268e321b96355b3a2cb0ac7928bf6b8a0f2a39387735f90eec88f8007d3f9",
}
HELPER_SHA = {
    "0157-fixed-gravity-inputs.py":
        "5592d0295da35351a37795865f5ccaab0bcc64961b2dc0173245bbfe81e20f97",
    "0157-fixed-gravity-reference.py":
        "1337ba2b1fea94381e175603a501ec36b992a2194faf46dea6a3e429a7aef9b8",
    "0157-fixed-gravity-study.py":
        "9bcbfe35e14bdb0f25e68e0e3c76b5303fa0ca8ee61bcb178131dbd02f0d7ad4",
    "0157-fixed-gravity-audit.py":
        "c53cdbe8b556029dac311a3065bf31a07b0211235fa2af2c548a33387a976ef2",
    "0153-real-ephemeris-oracle.py":
        "23915fee1feacca37f4a4c0f794feec177aac777407b9c87cc0f8176b0b4a6c8",
    "0145-short-coast-evidence.py":
        "426fe4e0abe9b9dfcf6380d09e86e8dbf5748f66875f74b26b45dceb6ba5da14",
}
SOURCE_ORDER = ("Sun", "Earth", "Moon")
MODEL_ORDER = {"A": ["Sun", "Moon"], "B": ["Sun", "Moon", "Earth"]}
COUNTS = {"source_rows": 21, "reference_fields": 168,
          "binary64_fields": 63, "model_totals": 14}
SNAPSHOT = ("position_m", "initial", "gm_m3_s2", "input_sha256", "source_provenance", "identity")


def idle() -> None:
    """Default callback for unbudgeted metadata preparation."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def same(actual: object, expected: object, label: str) -> None:
    """Compare JSON types too, preventing true/1 identity substitution."""
    require(json.dumps(actual, sort_keys=True, allow_nan=False)
            == json.dumps(expected, sort_keys=True, allow_nan=False), label + " mismatch")


def load_base(root: Path = ROOT, check: Check = idle) -> ModuleType:
    """Execute only hash-checked immutable input code; never load old runners."""
    path = root / "docs/adr/experiments/0157-fixed-gravity-inputs.py"
    check()
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == HELPER_SHA[path.name], "input helper identity")
    check()
    module = ModuleType("moving_inputs_0157_base")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check()
    return module


def validate_retained(bundle: dict[str, Any], records: dict[str, Any],
                      check: Check = idle) -> dict[str, Any]:
    """Validate parsed frozen records against an already validated base bundle.

    This does not evaluate gravity or repeat the saved audit. Direct calls with
    synthetic/mutated records are preparation fixtures; only load_inputs binds
    all six file digests and the current pinned interpreter.
    """
    check()
    require(type(bundle) is dict and type(records) is dict, "input objects")
    require(set(records) == set(INPUT_SHA), "six retained input records")
    study = records["0158-fixed-gravity-study.json"]
    audit = records["0158-fixed-gravity-audit.json"]
    proof = records["0158-verification.json"]
    require(all(type(v) is dict for v in (study, audit, proof)), "0158 record objects")
    same(study["contract"], "ADR0156", "saved study contract")
    same(study["study"], "fixed-position-real-gravity-v1", "saved study kind")
    same(study["status"], "passed", "saved study status")
    same(study["adapter_mode"], "reference", "saved study adapter")
    same(study["finalization_gate"], "passed", "saved study finalization")
    same({k: study[k] for k in ("origin", "orientation", "time_scale",
                               "aberration_correction", "acceleration_units")},
         {"origin": "SSB", "orientation": "J2000", "time_scale": "TDB",
          "aberration_correction": "NONE", "acceleration_units": "m/s^2"},
         "saved study conventions")
    for name in ("native_calls", "kernel_loads", "gm_acquisitions", "spacecraft_propagations", "scientific_imports"):
        same(study[name], 0, "saved study " + name)
        same(audit[name], 0, "saved audit " + name)
    same(study["reference_replayed"], False, "saved reference replay")
    same(study["research_only"], True, "saved research label")
    same(study["mission_accuracy_verified"], False, "saved mission scope")
    same(study["continuous_safety_verified"], False, "saved safety scope")
    expected_counts = {name: {"attempted": cap, "completed": cap} for name, cap in COUNTS.items()}
    same(study["counts"], expected_counts, "saved complete counts")
    same(audit["counts"], expected_counts, "saved audit counts")
    same(study["helper_sha256"], HELPER_SHA, "saved helper identities")
    same(audit["helper_sha256"], HELPER_SHA, "saved audit helper identities")
    snapshot = {key: bundle[key] for key in SNAPSHOT}
    same(study["inputs"], snapshot, "saved input snapshot")
    same(study["identity_after"], snapshot, "saved final input identity")
    same(audit["contract"], "ADR0156", "saved audit contract")
    same(audit["audit_status"], "passed", "saved audit status")
    same(audit["scientific_verified"], True, "saved audit verification")
    same(audit["source_study_status"], "passed", "saved audit source status")
    same(audit["adapter_mode"], "reference", "saved audit adapter")
    same(audit["finalization_gate"], "passed", "saved audit finalization")
    same(audit["evidence_sha256"], INPUT_SHA["0158-fixed-gravity-study.json"], "saved audit evidence binding")
    same(audit["checks"]["complete_saved_data_checked"], True, "saved audit complete data")
    same(audit["checks"]["first_required_gate_failure"], None, "saved first required failure")
    same(audit["checks"]["source_counts"], expected_counts, "saved audit source counts")
    same(proof["study_runs"], 1, "verified study count")
    same(proof["saved_data_audit_runs"], 1, "verified audit count")
    same(proof["retries"], 0, "verified retry count")
    same(proof["study_status"], "passed", "verified study status")
    same(proof["saved_data_audit_status"], "passed", "verified audit status")
    same(proof["all_protected_and_tested_bytes_unchanged"], True, "verified source history")
    same(proof["no_new_integration"], True, "verified integration scope")
    same(proof["strict_m3_closed"], False, "verified M3 scope")
    same(proof["mission_safety_verified"], False, "verified mission safety scope")
    same(proof["input_sha256"], bundle["input_sha256"], "verified frozen input hashes")
    same(proof["helper_sha256"], HELPER_SHA, "verified helper hashes")
    for name in ("0158-fixed-gravity-study.json", "0158-fixed-gravity-audit.json"):
        same(proof["artifact_sha256"][name], INPUT_SHA[name], "verified evidence digest")

    rows = study["rows"]
    audited_rows = audit["checks"]["source_rows"]
    totals = study["totals"]
    audited_totals = audit["checks"]["model_totals"]
    require(type(rows) is list and len(rows) == 21 and type(audited_rows) is list
            and len(audited_rows) == 21, "saved source row count")
    require(type(totals) is list and len(totals) == 7 and type(audited_totals) is list
            and len(audited_totals) == 7, "saved model time count")
    for index, (row, audited) in enumerate(zip(rows, audited_rows, strict=True)):
        check()
        same(row["index"], index, "saved source row index")
        same(row["source_row"], bundle["rows"][index], "saved raw source row")
        same(row["source_row"]["body"], SOURCE_ORDER[index % 3], "saved source order")
        same(row["assessment"]["passed"], True, "saved source assessment")
        same(audited["index"], index, "audited source index")
        same(audited["assessment_checked"], True, "audited source coverage")
        same(audited["arms"], row["arms"], "audited source operands")
        same(audited["assessment"], row["assessment"], "audited source assessment")
    for index, (total, audited) in enumerate(zip(totals, audited_totals, strict=True)):
        check()
        same(total["index"], index, "saved model time index")
        same(total["elapsed_s"], bundle["rows"][3 * index]["elapsed_s"], "saved model epoch")
        same(sorted(total["assessment"]), sorted(MODEL_ORDER), "saved model set")
        same(audited["index"], index, "audited model index")
        same(audited["models_checked"], list(MODEL_ORDER), "audited model coverage")
        same(audited["arms"], total["arms"], "audited model operands")
        same(audited["assessment"], total["assessment"], "audited model assessment")
        for model, order in MODEL_ORDER.items():
            same(total["assessment"][model]["source_order"], order, "saved model source order")
            same(total["assessment"][model]["passed"], True, "saved model gate")
    zero_sources = {}
    for row in rows[:3]:
        same(row["source_row"]["elapsed_s"], 0.0, "saved zero source epoch")
        zero_sources[row["source_row"]["body"]] = deepcopy(row["arms"]["compensated"])
    same(totals[0]["elapsed_s"], 0.0, "saved zero model epoch")
    zero_totals = {model: deepcopy(totals[0]["arms"][model]["compensated"])
                   for model in MODEL_ORDER}
    check()
    result = deepcopy(bundle)
    result["input_sha256"] = dict(INPUT_SHA)
    result["helper_sha256"] = dict(HELPER_SHA)
    result["zero_reference"] = {"sources": zero_sources, "totals": zero_totals}
    return result


def load_inputs(root: Path = ROOT, check: Check = idle) -> dict[str, Any]:
    """Load six frozen artifacts and saved zero-state vectors without new physics."""
    base = load_base(root, check)
    parser = base.strict_json(check)
    records: dict[str, Any] = {}
    for name, expected in INPUT_SHA.items():
        check()
        raw = (root / "docs/adr/experiments" / name).read_bytes()
        require(sha256(raw).hexdigest() == expected, "frozen input identity: " + name)
        check()
        records[name] = parser.parse(raw)
        check()
    for name, expected in HELPER_SHA.items():
        check()
        raw = (root / "docs/adr/experiments" / name).read_bytes()
        require(sha256(raw).hexdigest() == expected, "historical helper identity: " + name)
        check()
    bundle = base.load_inputs(root, check)
    result = validate_retained(bundle, records, check)
    check()
    return result
