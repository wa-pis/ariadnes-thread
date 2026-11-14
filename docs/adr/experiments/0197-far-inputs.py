"""Authenticate the archived R5.48 restart and the fixed ADR0196 inputs offline."""

from __future__ import annotations

from collections.abc import Callable
import gzip
from hashlib import sha256
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

ART = Path("docs/adr/experiments")
DESIGN_SHA = "302872faf1d5819dbc438cb7efa4cbcdcb2da37fc3a1249fa26bfd2fa346fb22"
OLD_INPUTS_SHA = "83c2d3761cb4ec64ca96a6a6c8cd618a36765989de436c3858f5593a9073bb6b"
DURATION_S = 16_000.0
OFFSETS = tuple(float(i) for i in range(0, 16_001, 50))
BODIES = ("Sun", "Moon", "Earth")
type Row = dict[str, Any]
type Check = Callable[[], None]


def require(ok: object, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _archive(root: Path, old: Row, parse: Callable[[bytes], Row], pin: str, check: Check) -> tuple[Row, Row, Row]:
    base = ART / "0195"
    manifest = parse(old["read"](root, base / "manifest.json", pin, check))
    require(manifest["stage"] == "R5.48" and manifest["contract"] == "ADR0193"
            and [manifest[k] for k in ("study_status", "audit_status", "numerical_status")] == ["passed"] * 3,
            "qualified R5.48 archive")
    reports: list[Row] = []
    evidence_links: Row = {}
    for phase, limit in (("study", 60), ("audit", 10)):
        files = manifest["files"]
        stem = phase + ".json.gz"
        descriptor = files[stem]
        packed = old["read"](root, base / stem, descriptor["sha256"], check)
        raw = gzip.decompress(packed)
        require(len(packed) == descriptor["bytes"] and len(raw) == descriptor["original_bytes"]
                and sha256(raw).hexdigest() == descriptor["original_sha256"], "R5.48 lossless report")
        report = parse(raw)
        del raw, packed
        receipts: dict[str, Row] = {}
        for name in ("attempt", "receipt", "parent-attempt", "parent-receipt"):
            fname = f"{phase}.{name}.json"
            item = files[fname]
            raw = old["read"](root, base / fname, item["sha256"], check)
            require(len(raw) == item["bytes"], "R5.48 receipt length")
            receipts[name] = parse(raw)
        attempt, child, parent_attempt, parent = (receipts[k] for k in
                                                ("attempt", "receipt", "parent-attempt", "parent-receipt"))
        identity = {"contract": "ADR0193", "phase": phase, "revision": manifest["measured_revision"],
                    "preparation_sha256": manifest["preparation_sha256"]}
        hashes = {name + "_sha256": files[f"{phase}.{name}.json"]["sha256"] for name in receipts}
        require(parent_attempt == identity and all(attempt[k] == parent[k] == v for k, v in identity.items())
                and child["contract"] == identity["contract"] and child["phase"] == phase
                and parent["attempt_sha256"] == child["attempt_sha256"] == hashes["attempt_sha256"]
                and parent["parent_attempt_sha256"] == hashes["parent-attempt_sha256"]
                and parent["child_receipt_sha256"] == hashes["receipt_sha256"]
                and parent["evidence_sha256"] == child["evidence_sha256"] == descriptor["original_sha256"]
                and parent["returncode"] == 0 and parent["checkout_frozen"] is True
                and child["status"] == child["finalization_gate"] == parent["finalization_gate"] == "passed"
                and attempt["started_s"] == child["started_s"] == parent["started_s"]
                and 0 <= child["elapsed_s"] <= parent["elapsed_s"] < limit,
                "R5.48 receipt binding")
        require(report["contract"] == identity["contract"] and report["adapter_mode"] == "reference"
                and report["preparation_sha256"] == identity["preparation_sha256"], "R5.48 report identity")
        if phase == "study":
            evidence_links = hashes | {"evidence_sha256": descriptor["original_sha256"]}
            require(report["status"] == "passed", "R5.48 study status")
        else:
            require(report["audit_status"] == report["numerical_status"] == "passed"
                    and report["scientific_verified"] is False and report["study_sha256s"] == evidence_links
                    and all(report[key] == 0 for key in ("native_calls", "kernel_loads", "scientific_imports",
                                                        "spacecraft_propagations")), "R5.48 independent audit")
        reports.append(report)
    return manifest, reports[0], reports[1]


def _bind(design: Row, manifest: Row, study: Row, audit: Row, words: Callable[[list[float]], list[str]]) -> Row:
    restart, fixed, plan = (design[k] for k in ("restart", "fixed_model", "plan"))
    epoch, state, moon, mass = (restart[k] for k in ("epoch_tdb_s", "state_si", "moon_ssb_state_si", "mass_kg"))
    saved = study["inputs"]
    require(design["candidate"] == manifest["candidate"] == "d0001-t0035"
            and len(state) == len(moon) == 6 and mass > 0
            and words([epoch, mass]) == [restart["epoch_binary64_hex"], restart["mass_binary64_hex"]]
            and words([epoch, mass]) == words([manifest["stop_tdb_s"], study["coast_mass_kg"]])
            == words([saved["origin_cutoff"]["epoch_tdb_s"] + 650, saved["mass_kg"]])
            and words(state) == restart["state_binary64_hex"]
            and words(moon) == restart["moon_ssb_binary64_hex"], "R5.48 exact restart/epoch/mass words")
    tighter = study["native_profiles"][1]
    raw = tighter["raw_returned"]["state_history"]
    raw_t, raw_state = next(reversed(raw.items()))
    sample = tighter["result"]["samples"][-1]
    guard = tighter["guards"][-2]
    common_moon = study["node_table"][-1]["bodies"]["Moon"]
    require(tighter["name"] == "tighter" and tighter["step_s"] == .5 and guard["body"] == "Moon"
            and guard["passed"] is True and common_moon["body"] == "Moon"
            and words([float(raw_t), sample["epoch_tdb_s"], guard["epoch_tdb_s"], common_moon["epoch_tdb_s"]])
            == [epoch.hex()] * 4 and words(raw_state) == words(sample["state"]) == words(state)
            and words(guard["state_si"]) == words(common_moon["state_si"]) == words(moon), "archived native operands")
    grids = audit["direction_grids"]
    for name in ("mesh_tighter", "rk4_tighter"):
        point = grids[name]["rows"][-1]
        require(words([point["epoch_tdb_s"]]) == words([epoch])
                and words(point["spacecraft_si"]) == words(state) and words(point["moon_si"]) == words(moon),
                "audited tighter terminal operands")
    for name, end in zip(("rk4_normal", "rk4_tighter", "dop853_normal", "dop853_tighter"),
                         [p["result"]["samples"][-1]["state"] for p in study["native_profiles"]]
                         + [p["outputs"][-1]["motion"]["position_m"] + p["outputs"][-1]["motion"]["velocity_m_s"]
                            for p in study["profiles"]], strict=True):
        point = grids[name]["rows"][-1]
        require(words([point["epoch_tdb_s"]]) == words([epoch]) and words(point["spacecraft_si"]) == words(end)
                and words([a - b for a, b in zip(end, state, strict=True)])
                == words(restart["coepoch_end_state_minus_restart_si"][name]), "three nonrestart endpoint deltas")
    coast = saved["coast"]
    require(fixed["id"] == manifest["model"] == coast["model_id"]
            and fixed["geometry"] == "SI, SSB, J2000, TDB seconds since J2000, NONE"
            and fixed["kernel_manifest"] == saved["kernel_manifest"]
            and fixed["gm_m3_s2"] == saved["gm_m3_s2"] and fixed["exclusion_radii_m"] == saved["radii_m"]
            and plan["native_steps_s"] == coast["native_steps_s"]
            and plan["dop853_settings"] == coast["dop853_settings"]
            and plan["coepoch_gates"] == coast["comparisons"]
            and all(plan["direction_arithmetic_gates"][k] == coast["direction_arithmetic_limits"][k]
                    for k in ("radius_m", "radial_speed_m_s"))
            and fixed["thrust_n"] == fixed["mass_flow_kg_s"] == 0, "unchanged R5.48 model and gates")
    require(plan["horizon_s"] == DURATION_S and plan["common_stride_s"] == 50
            and plan["marker_radius_m"] == 18_374_000 and (stop := epoch + DURATION_S) == plan["stop_tdb_s"]
            and words([stop]) == [plan["stop_binary64_hex"]]
            and all((epoch + s) - epoch == s for s in OFFSETS), "fixed ADR0196 epoch grid")
    return {**saved, "initial": {"epoch_tdb_s": epoch, "position_m": state[:3], "velocity_m_s": state[3:]},
            "offsets_s": list(OFFSETS), "mass_kg": mass, "restart_moon_state_si": moon, "far": design}


def prepare(root: Path, check: Check) -> Row:
    """Read only archived checkout bytes; never initialize a scientific runtime."""
    source = root / ART / "0194-extension-inputs.py"
    raw = source.read_bytes()
    require(sha256(raw).hexdigest() == OLD_INPUTS_SHA, "frozen extension inputs helper")
    module = ModuleType("r550_frozen_inputs")
    module.__file__ = str(source)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(source), "exec"), module.__dict__)
    old = module.__dict__
    inherited = old["load_file"](root, "0189-post-cutoff-inputs.py",
                                 old["PURE_PINS"]["0189-post-cutoff-inputs.py"], check)
    parser = inherited["parse"]
    design = parser(old["read"](root, ART / "0196-design-inputs.json", DESIGN_SHA, check))
    require((design["stage"], design["contract"]) == ("R5.49", "ADR0196"), "frozen far design")
    for name, pin in design["source_manifest_sha256"].items():
        old["read"](root, ART / name, pin, check)
    manifest, study, audit = _archive(root, old, parser, design["source_manifest_sha256"]["0195/manifest.json"], check)
    bundle = _bind(design, manifest, study, audit, old["words"])
    start, stop = bundle["initial"]["epoch_tdb_s"], design["plan"]["stop_tdb_s"]
    inherited["_coverage"](design["fixed_model"]["record_interiors_metadata_only"], bundle["source_rows_template"],
                           [start, stop])
    check()
    return bundle
