"""Bind the archived simulated cutoff and frozen model B inputs without native work."""
from __future__ import annotations

from collections.abc import Callable
from decimal import Context, Decimal
from fractions import Fraction
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS = Path("docs/adr/experiments")
DESIGN = ARTIFACTS / "0188-design-inputs.json"
DESIGN_SHA = "dca18b7a555c89e27ae0a3ac4251d93f33b28a354f195334ba0e4748136a797e"
PREVIOUS_DESIGN = ARTIFACTS / "0185-design-inputs.json"
PREVIOUS_PREPARATION = ARTIFACTS / "0186-verification.json"
R540 = ARTIFACTS / "0187"
ORIGINAL = ARTIFACTS / "0079-research-reference.json"
BASELINE = ARTIFACTS / "0098-central-correction-study.json"
CANDIDATE = ARTIFACTS / "0119-m2-reference.json"
RUNTIME_KEYS = ("versions", "imports", "native_binary", "conda_build", "resource_build",
                "resource_metadata_sha256", "conda_metadata_sha256", "r5_runtime", "kernels")
OFFSETS = list(range(0, 601, 50))
B_NOW = "r5-ssb-sun-moon-earth-point-v1"
type Row = dict[str, Any]
type Check = Callable[[], None]


def require(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(label)


def idle() -> None:
    pass


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def read(root: Path, path: str | Path, expected: str, check: Check = idle) -> bytes:
    """Read only a bound checkout-local file."""
    check()
    target = (root / path).resolve()
    require(target.is_relative_to(root.resolve()), "input outside checkout")
    raw = target.read_bytes()
    require(digest(raw) == expected, f"input SHA256: {path}")
    check()
    return raw


def _object(pairs: list[tuple[str, Any]]) -> Row:
    values = dict(pairs)
    require(len(values) == len(pairs), "duplicate JSON key")
    return values


def _nonfinite(value: str) -> None:
    raise ValueError("nonfinite JSON token: " + value)


def _wire_float(token: str) -> float:
    value = float(token)
    require(math.isfinite(value), "nonfinite JSON float")
    return value


def parse(raw: bytes) -> Row:
    """Decode a strict saved object; nonfinite floats and duplicate keys are invalid."""
    row = json.loads(raw, object_pairs_hook=_object, parse_constant=_nonfinite, parse_float=_wire_float)
    require(type(row) is dict, "expected JSON object")
    return row


def _exact(a: Any, b: Any) -> bool:
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys() == b.keys() and all(_exact(v, b[k]) for k, v in a.items())
    if type(a) is list:
        return len(a) == len(b) and all(_exact(x, y) for x, y in zip(a, b, strict=True))
    if type(a) is float:
        return math.isfinite(a) and a.hex() == b.hex()
    return a == b


def _real(value: Any, label: str) -> float:
    require(type(value) in (int, float) and math.isfinite(value), label)
    return float(value)


def _vector(value: Any, length: int, label: str) -> list[float]:
    require(type(value) is list and len(value) == length, label)
    return [_real(x, label) for x in value]


def _words(cutoff: Row, mass: float) -> Row:
    return {
        "epoch_tdb_s": _real(cutoff["epoch_tdb_s"], "cutoff epoch").hex(),
        "position_m": [x.hex() for x in _vector(cutoff["position_m"], 3, "cutoff position")],
        "velocity_m_s": [x.hex() for x in _vector(cutoff["velocity_m_s"], 3, "cutoff velocity")],
        "mass_kg": mass.hex(),
    }


def _mass(ignition: float, epoch: float, mass: float, dry: float, requested: float, burn: Row, recorded: Row) -> None:
    thrust, isp, initial_mass = (_real(burn[k], "stored burn " + k)
                                for k in ("thrust_n", "isp_s", "initial_mass_kg"))
    require(0 < dry < mass < initial_mass and thrust > 0 and isp > 0 and
            requested > 0 and epoch > ignition and ignition + requested == epoch,
            "represented burn interval or mass range")
    dt = Fraction(epoch) - Fraction(ignition)
    consumed = Fraction(thrust)*dt/(Fraction("9.80665")*Fraction(isp))
    expected = Fraction(initial_mass) - consumed
    limit = max(Fraction("1e-8"), Fraction("1e-11")*consumed)
    residual = expected-Fraction(mass)
    require(abs(residual) <= limit, "stored cutoff mass violates burn law")
    # The documentation used 80-digit arithmetic, subtracting stored mass
    # after rounding the predicted mass. Allow only its last-place rounding.
    ctx = Context(prec=80)

    def decimal(value: Fraction) -> Decimal:
        return ctx.divide(Decimal(value.numerator), Decimal(value.denominator))

    predicted = decimal(expected)
    require(recorded["g0_m_s2"] == "9.80665" and recorded["requested_duration_s"] == requested
            and recorded["dry_mass_kg"] == dry and Decimal(recorded["represented_duration_s"]) == decimal(dt)
            and Decimal(recorded["limit_kg"]) == decimal(limit)
            and abs(ctx.subtract(Decimal(recorded["predicted_mass_kg"]), predicted)) <= Decimal("1e-75")
            and abs(ctx.subtract(Decimal(recorded["predicted_minus_stored_mass_kg"]),
                                 ctx.subtract(predicted, Decimal.from_float(mass)))) <= Decimal("1e-75"),
            "documented mass arithmetic disagrees with exact burn law")


def bind_cutoff(design: Row, original: Row, replay: Row, candidate: Row) -> Row:
    """Require the designated simulated nominal cutoff and exact independent replay."""
    require(design["stage"] == "R5.41" and design["contract"] == "ADR0188", "cutoff design identity")
    reference, repeat = original["science"], replay["science"]
    nominal, baseline = reference["nominal"], repeat["runs"][0]["run"]
    require(repeat["runs"][0]["role"] == "baseline"
            and nominal["profile"] == baseline["profile"] == "nominal"
            and nominal["outcome"] == baseline["outcome"] == "completed"
            and reference["research_only"] is repeat["research_only"] is True
            and reference["numerical_agreement"] is False
            and design["historical_baseline_target_closed"] is False,
            "completed, unqualified original/replayed nominal cutoff")
    require(all((science["units"], science["origin"], science["orientation"], science["time_scale"]) ==
                ("SI", "SSB", "J2000", "TDB seconds since J2000") for science in (reference, repeat))
            and reference["force_model_id"] == design["boundary_original_force_model_id"],
            "original cutoff force model/frame/units")
    require(_exact(reference["scenario"], repeat["scenario"])
            and _exact(reference["scenario"], candidate["normalized_scenario"]), "original/replay/R1 scenario")
    chosen = candidate["runs"][0]["selected"]
    require(reference["candidate_id"] == chosen["candidate_id"] == design["candidate"] == "d0001-t0035"
            and _exact(reference["provenance"]["candidate"], chosen)
            and _exact(repeat["candidate"], chosen), "original/replay/R1 candidate")
    require(_exact(nominal["boundaries"][:2], baseline["boundaries"][:2])
            and _exact(nominal["boundary_masses_kg"][:2], baseline["boundary_masses_kg"][:2])
            and _exact(nominal["burns"][0], baseline["burns"][0]), "nominal versus 0098 cutoff replay")
    ignition, cutoff = nominal["boundaries"][:2]
    for row, label in ((ignition, "departure-ignition"), (cutoff, "departure-cutoff")):
        require((row["label"], row["origin"], row["orientation"]) == (label, "SSB", "J2000"),
                "fixed departure event label/frame")
    mass = _real(nominal["boundary_masses_kg"][1], "cutoff mass")
    require(_exact(cutoff, design["boundary_state"]) and _exact(mass, design["boundary_mass_kg"])
            and _exact(_words(cutoff, mass), design["cutoff_binary64_hex"]),
            "cutoff differs from frozen position/velocity/epoch/mass words")
    burn = nominal["burns"][0]
    dry = _real(reference["scenario"]["spacecraft"]["dry_mass_kg"], "dry mass")
    t0 = _real(ignition["epoch_tdb_s"], "ignition epoch")
    tcut = _real(cutoff["epoch_tdb_s"], "cutoff epoch")
    spacecraft = reference["scenario"]["spacecraft"]
    require(_exact(burn, design["stored_burn"]) and
            (burn["burn_id"], burn["direction_frame"]) == ("departure", "Moon-relative TNW") and
            _exact(burn["start_epoch_tdb_s"], t0) and _exact(burn["end_epoch_tdb_s"], tcut) and
            _exact(burn["initial_mass_kg"], nominal["boundary_masses_kg"][0])
            and _exact(burn["initial_mass_kg"], spacecraft["initial_mass_kg"])
            and _exact(burn["final_mass_kg"], mass)
            and _exact(burn["thrust_n"], spacecraft["max_thrust_n"])
            and _exact(burn["isp_s"], spacecraft["isp_s"]), "stored burn-to-cutoff event/mass linkage")
    _vector(burn["direction_tnw"], 3, "departure direction")
    requested = _real(reference["seed_commands"]["departure_duration_s"], "requested burn duration")
    _mass(t0, tcut, mass, dry, requested, burn, design["mass_arithmetic"])
    cut_delta = reference["integration_differences"][1]
    require(_exact(cut_delta, design["history_boundary_profile_differences"])
            and cut_delta["label"] == "departure-cutoff", "historical profiles remain distinct")
    coast = design["coast"]
    require(coast["model_id"] == B_NOW and coast["sources"] == ["Sun", "Moon", "Earth"]
            and coast["geometry"] == "SI, SSB, J2000, TDB seconds since J2000, NONE"
            and coast["duration_s"] == 600 and _exact(coast["offsets_s"], OFFSETS)
            and _exact(coast["coepochs_tdb_s"], [tcut + s for s in OFFSETS])
            and _exact(coast["constant_mass_metadata_kg"], mass)
            and all(type(coast[k]) is int and coast[k] == 0 for k in ("thrust_n", "mass_flow_kg_s")),
            "fixed post-cutoff coast contract")
    return {"initial": {k: cutoff[k] for k in ("position_m", "velocity_m_s", "epoch_tdb_s")},
            "cutoff": cutoff, "mass_kg": mass, "burn": burn,
            "mass_arithmetic": design["mass_arithmetic"], "coast": coast, "offsets_s": OFFSETS.copy()}


def _archive(root: Path, anchors: dict[str, str], check: Check) -> tuple[Row, str]:
    manifest = parse(read(root, R540 / "manifest.json", anchors[str(R540 / "manifest.json")], check))
    require(manifest["stage"] == "R5.40" and manifest["contract"] == "ADR0185" and
            manifest["result_record"] == "ADR0187" and
            manifest["verdict"] == "passed_sampled_same_model_b_numerical_agreement",
            "accepted R5.40 model B calibration")
    suffixes = ("attempt", "receipt", "parent-attempt", "parent-receipt")
    names = {phase+".json.gz" for phase in ("study", "audit")} | {
        f"{phase}.{suffix}.json" for phase in ("study", "audit") for suffix in suffixes}
    require(set(manifest["files"]) == names, "complete R5.40 report/receipt inventory")
    contents: dict[str, bytes] = {}
    for name, meta in manifest["files"].items():
        key = str(R540 / name)
        blob = read(root, key, anchors[key], check)
        require(meta["sha256"] == anchors[key] and len(blob) == meta["bytes"], "retained R5.40 bytes")
        if name.endswith(".gz"):
            blob = gzip.decompress(blob)
            require(digest(blob) == meta["original_sha256"] and len(blob) == meta["original_bytes"],
                    "original R5.40 bytes")
        contents[name.removesuffix(".gz")] = blob
    reports: dict[str, Row] = {}
    for phase, limit in (("study", 60), ("audit", 10)):
        check()
        raw = contents[phase+".json"]
        report = reports[phase] = parse(raw)
        rows = {k: contents[f"{phase}.{k}.json"] for k in suffixes}
        attempt, child, marker, parent = (parse(rows[k]) for k in suffixes)
        require(report["contract"] == attempt["contract"] == marker["contract"] == parent["contract"] == "ADR0185"
                and report["adapter_mode"] == attempt["adapter_mode"] == "reference"
                and report["status" if phase == "study" else "audit_status"] == child["status"] == "passed"
                and type(parent["returncode"]) is int and parent["returncode"] == 0
                and parent["checkout_frozen"] is True and not parent["stderr"], "R5.40 phase signature")
        require(parent["evidence_sha256"] == child["evidence_sha256"] == digest(raw)
                and parent["attempt_sha256"] == digest(rows["attempt"])
                and parent["child_receipt_sha256"] == digest(rows["receipt"])
                and parent["parent_attempt_sha256"] == digest(rows["parent-attempt"]), "R5.40 receipt linkage")
        require(parent["phase"] == marker["phase"] == phase
                and parent["revision"] == marker["revision"] == manifest["measured_revision"]
                and parent["preparation_sha256"] == marker["preparation_sha256"] == manifest["preparation_sha256"]
                == anchors[str(PREVIOUS_PREPARATION)], "R5.40 preparation and revision")
        require(report["finalization_gate"] == child["finalization_gate"] == parent["finalization_gate"] == "passed"
                and _exact(child["started_s"], parent["started_s"]) and _exact(child["started_s"], attempt["started_s"])
                and 0 <= _real(report["elapsed_before_flush_s"], "R5.40 preflush")
                <= _real(child["elapsed_s"], "R5.40 child elapsed")
                <= _real(parent["elapsed_s"], "R5.40 parent elapsed") <= limit, "R5.40 bounded finalization")
    audit, study = reports["audit"], reports["study"]
    study_digest = digest(contents["study.json"])
    require(audit["study_sha256"] == study_digest and
            audit["study_receipts"] == {k+"_sha256": digest(contents[f"study.{k}.json"]) for k in suffixes},
            "R5.40 audit binds study evidence")
    checks = audit["checks"]
    require(checks["passed"] is True and
            {k: v for k, v in checks.items() if k != "comparison_summary"} == manifest["audit_checks"] and
            checks["complete_profiles"] == checks["complete_native_profiles"] == 2 and
            checks["comparisons"] == 67 and checks["prefix_comparisons"] == 28 and
            checks["observations"] == 52 and checks["native_telemetry"] == 26 and
            all(type(audit[k]) is int and audit[k] == 0 for k in
                ("native_calls", "scientific_imports", "kernel_loads", "spacecraft_propagations")),
            "R5.40 independent audit metadata")
    require(study["identities"]["before"]["revision"] == manifest["measured_revision"],
            "R5.40 runtime revision")
    check()
    return study, study_digest


def _coverage(metadata: list[Row], template: Row, epochs: list[float]) -> None:
    by_route = {(r["body_id"], r["centre_id"]): r for r in metadata}
    require(len(metadata) == 3 and set(by_route) == {(10, 0), (301, 399), (399, 0)},
            "three unique pinned source records")
    routes = {"Sun": [(10, 0)], "Moon": [(301, 399), (399, 0)], "Earth": [(399, 0)]}
    require(set(template) == set(routes), "three force source templates")
    for body, expected in routes.items():
        source = template[body]
        require(source["body"] == body and [(s["body"], s["centre"]) for s in source["segments"]] == expected,
                "Type 2 source route order")
        for key, segment in zip(expected, source["segments"], strict=True):
            row = by_route[key]
            mid, half = (_real(v, "record interval") for v in segment["words"][:2])
            span, record = row["segment_interval_tdb_s"], row["record_interval_tdb_s"]
            require([segment["first_tdb_s"], segment["last_tdb_s"]] == span
                    and [mid-half, mid+half] == record
                    and segment["type"] == row["type"] == 2 and segment["frame"] == row["frame_id"] == 1
                    and segment["address"] == row["record_address"] and segment["index"] == row["record_index"]
                    and Path(segment["path"]).name == row["segment_file"]
                    and max(span[0], record[0]) < epochs[0] < epochs[-1] < min(span[1], record[1]),
                    "retained Type 2 metadata does not cover post-cutoff epochs")


def _inherited_controls(design: Row, earlier: Row, profile: Row) -> None:
    coast = design["coast"]
    require(all(_exact(coast[k], earlier[k]) for k in
                ("gm_m3_s2", "radii_m", "native_steps_s", "dop853_settings", "offsets_s", "geometry"))
            and _exact(design["retained_record_metadata"], earlier["retained_record_metadata"]),
            "coast profiles/GMs/geometry must inherit R5.40")
    changed_caps = {"prefix_comparisons": 0, "all_comparisons": 39,
                    "direction_rows": 52, "net_range_signs": 4, "direction_decimal_digits": [80,100]}
    require(_exact(design["caps"], earlier["caps"] | changed_caps)
            and _exact(coast["comparisons"], {
                "native_step_and_tighter_cross_engine": {"position_m": .01, "velocity_m_s": 1e-5},
                "dop853_step": {"position_m": .001, "velocity_m_s": 1e-6},
            }) and _exact(coast["direction_arithmetic_limits"], {"radius_m": 1e-6, "radial_speed_m_s": 1e-9,
                      "specific_energy_m2_s2": 1e-6, "net_range_change_m": 1e-6}), "fixed arithmetic gates/caps")
    require((profile["model"], profile["origin"], profile["orientation"], profile["time_scale"],
             profile["aberration_correction"], profile["duration_s"]) == ("B", "SSB", "J2000", "TDB", "NONE", 600)
            and all(_exact(coast[k], profile["inputs"][k]) for k in ("gm_m3_s2", "radii_m"))
            and [v["name"] for v in profile["native_profiles"]] == ["normal", "tighter"]
            and [v["step_s"] for v in profile["native_profiles"]] == coast["native_steps_s"]
            and [v["name"] for v in profile["profiles"]] == ["normal", "tighter"]
            and _exact([v["settings"] for v in profile["profiles"]], coast["dop853_settings"]),
            "R5.40 archived model and integrator profiles")


def load(root: Path = ROOT, check: Check = idle) -> Row:
    """Return independent, hash-bound model B restart inputs; no trajectory evaluation."""
    design = parse(read(root, DESIGN, DESIGN_SHA, check))
    anchors = design["immutable_input_sha256"]

    def pinned(name: Path) -> Row:
        return parse(read(root, name, anchors[str(name)], check))

    original, replay, candidate = (pinned(name) for name in (ORIGINAL, BASELINE, CANDIDATE))
    require(replay["science"]["reference_sha256"] == anchors[str(ORIGINAL)], "0098 links original nominal cutoff")
    bundle = bind_cutoff(design, original, replay, candidate)
    earlier, preparation = (pinned(name) for name in (PREVIOUS_DESIGN, PREVIOUS_PREPARATION))
    study, archive_digest = _archive(root, anchors, check)
    require(preparation["stage"] == "R5.39" and preparation["contract"] == "ADR0185"
            and preparation["preparation_complete"] is True
            and _exact(preparation["tested_source_sha256"], study["tested_source_sha256"])
            and study["preparation_manifest_sha256"] == anchors[str(PREVIOUS_PREPARATION)],
            "R5.40 frozen prepared sources")
    for path, sha in preparation["tested_source_sha256"].items():
        read(root, path, sha, check)
    require(set(preparation["design_input_sha256"]) == set(earlier["immutable_input_sha256"]) | {str(PREVIOUS_DESIGN)}
            and _exact(preparation["design_input_sha256"],
                       earlier["immutable_input_sha256"] | {str(PREVIOUS_DESIGN): anchors[str(PREVIOUS_DESIGN)]}),
            "R5.39 design/source binding")
    for path, sha in preparation["design_input_sha256"].items():
        if anchors.get(path) != sha:
            read(root, path, sha, check)
    _inherited_controls(design, earlier, study)
    prior = study["inputs"]
    runtime = study["identities"]["before"]
    require(_exact(runtime, study["identities"]["after"]) and runtime["dirty"] == []
            and all(_exact(runtime[k], prior["historical_identity"][k]) for k in RUNTIME_KEYS)
            and _exact(runtime["kernels"], prior["kernel_manifest"])
            and runtime["kernels"]["loaded_kernel_count"] == len(runtime["kernels"]["kernels"]) == 13,
            "R5.40 runtime and ordered kernel provenance")
    require(bundle["initial"]["epoch_tdb_s"] > prior["initial"]["epoch_tdb_s"]+600,
            "cutoff must not be an R5.40 parking-coast state")
    _coverage(design["retained_record_metadata"], prior["source_rows_template"], bundle["coast"]["coepochs_tdb_s"])
    check()
    keys = ("gm_m3_s2", "radii_m", "source_rows_template", "kernel_manifest", "historical_identity",
            "protected_sha256")
    return {**bundle, **{k: prior[k] for k in keys}, "b_runtime": runtime,
            "input_sha256": anchors | {str(DESIGN): DESIGN_SHA}, "b_archive_sha256": archive_digest}
