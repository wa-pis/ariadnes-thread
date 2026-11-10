"""R5.23 input validation using saved bytes only; never evaluate a record or field."""
from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
import gzip
from hashlib import sha256
from pathlib import Path
from typing import Any

from ariadna_split_capture import validate_capture
from ariadna_split_common import ANALYSIS_CAPS, encode, number, parse_json, require, same
from ariadna_split_inputs import (
    ARCHIVE_PREFIX, _decimal, _numbers, _read_bound, _segment_checks,
)
from ariadna_split_run import in_budget, prep_pin, read_capture, read_phase

EXPERIMENTS = Path("docs/adr/experiments")
INPUT_SHA256 = "9a983ef4af96b4458559869fd4e35fdff4aabcbeb20135f4d2d373e99777eb93"
PROFILES = ("normal", "tighter")
KINDS = ("output", "rhs")
ARCHIVES = {ARCHIVE_PREFIX + name + ".json.gz": name for name in ("study", "audit")}


def _scope(study: dict[str, Any], audit: dict[str, Any], previous: dict[str, Any]) -> None:
    require(study["contract"] == audit["contract"] == "ADR0162"
            and study["status"] == "failed" and audit["audit_status"] == "partial"
            and study["scientific_verified"] is False and audit["scientific_verified"] is False
            and study["finalization_gate"] == audit["finalization_gate"] == "passed"
            and study["historical_final_identity_complete"] is False
            and set(study["identities"]) == {"before"}, "R5.17 retained negative verdict/identity")
    require(audit["evidence_sha256"] == previous["retained_uncompressed_sha256"]["study"]
            and audit["checks"]["observations"] == 14
            and audit["counts"]["source_rows"] == {"attempted": 28, "completed": 27}
            and audit["counts"]["reference_fields"] == {"attempted": 224, "completed": 224},
            "R5.17 retained audit prefix")
    same([study[key] for key in ("origin", "orientation", "time_scale", "aberration_correction",
                                 "position_units", "velocity_units", "acceleration_units")],
         ["SSB", "J2000", "TDB", "NONE", "m", "m/s", "m/s^2"], "R5.17 source conventions")
    data = study["inputs"]
    same(data["initial"], previous["frozen_initial"], "frozen initial state")
    same(data["gm_m3_s2"]["Moon"], previous["moon_gm_m3_s2"], "frozen Moon GM")
    same(data["radii_m"]["Moon"], previous["moon_radius_m"], "frozen Moon radius")
    same(data["kernel_manifest"], previous["original_ordered_pool_manifest"], "frozen kernel manifest")
    same(study["identities"]["before"]["kernels"], data["kernel_manifest"], "R5.17 before identity")


def _records(metadata: dict[str, Any], previous: dict[str, Any],
             data: dict[str, Any]) -> dict[str, list[float]]:
    _segment_checks(previous, data)
    moon = data["source_rows_template"]["Moon"]["segments"]
    same(data["source_rows_template"]["Earth"]["segments"], [moon[1]], "shared Earth segment")
    records = {}
    for key, expected, segment in zip(("G", "E"), metadata["records"], moon, strict=True):
        same([expected["body"], expected["centre"], expected["index"], expected["degree"]],
             [segment["body"], segment["centre"], segment["index"], 12], "R5.22 record identity")
        words = _numbers(segment["words"], 41, key + " Type 2 record")
        require(sha256(encode(words)).hexdigest() == expected["words_sha256"], key + " record words hash")
        midpoint, radius = (Fraction(x) for x in words[:2])
        lower, upper = (Fraction(x) for x in expected["interval_tdb_s"])
        require(radius > 0 and (lower, upper) == (midpoint - radius, midpoint + radius)
                and segment["first_tdb_s"] <= lower < upper <= segment["last_tdb_s"],
                key + " record/segment coverage")
        records[key] = words
    return records


def _controls(root: Path, metadata: dict[str, Any], previous: dict[str, Any], study: dict[str, Any],
              bound: dict[str, bytes], check: Callable[[], Any]) -> tuple[dict, dict]:
    directory = root / EXPERIMENTS / "0168"
    prefix = str(EXPERIMENTS / "0168") + "/"
    hashes = metadata["archive_and_evidence_sha256"]
    verification = parse_json(bound[str(EXPERIMENTS / "0168-verification.json")])
    same(verification["raw_evidence_sha256"],
         {name: h for name, h in hashes.items() if name.startswith(prefix)}, "R5.21 evidence inventory")
    same(verification["attempts"], {"capture": 1, "analysis": 1}, "R5.21 attempt counts")
    same([verification[key] for key in ("new_trajectory_propagations", "r517_requalified",
                                        "strict_m3_closed", "mission_safety_verified")],
         [0, False, False, False], "R5.21 limited scope")
    pin = prep_pin(root, metadata["previous_preparation"]["preparation_sha256"], check)
    same(pin, metadata["previous_preparation"], "R5.21 preparation binding")
    same(pin, verification["preparation"], "R5.21 verified preparation")
    capture = read_capture(directory, "live", pin)
    states = validate_capture({**previous, "historical_identity": study["identities"]["before"]}, capture, pin)
    check()
    analysis, child = read_phase(directory, "analysis", "live")
    parent = parse_json(bound[prefix + "analysis.parent-receipt.json"])
    attempt = parse_json(bound[prefix + "analysis.attempt.json"])
    same(attempt, {"phase": "analysis", "preparation_sha256": pin["preparation_sha256"]},
         "R5.21 analysis attempt binding")
    same([parent[key] for key in ("phase", "returncode", "stderr", "finalization", "preparation_sha256",
                                  "external_start_s", "attempt_sha256", "child_receipt_sha256")],
         ["analysis", 0, "", "passed", pin["preparation_sha256"], analysis["external_start_s"],
          hashes[prefix + "analysis.attempt.json"], hashes[prefix + "analysis.receipt.json"]],
         "R5.21 analysis parent binding")
    require(in_budget(parent["external_elapsed_s"], "analysis", "R5.21 analysis parent time")
            >= child["elapsed_before_receipt_s"], "R5.21 analysis receipt timeline")
    same(analysis["identity_pin"], pin, "R5.21 analysis identity")
    same(analysis["capture_receipt_sha256"], hashes[prefix + "capture.receipt.json"],
         "R5.21 analysis/capture binding")
    same(analysis["counts"], {k: {"attempted": n, "returned": n, "completed": n}
                              for k, n in ANALYSIS_CAPS.items()}, "R5.21 analysis exact counts")
    require(analysis["status"] == "passed" and "error" not in analysis and not analysis["unavailable"]
            and all(analysis[key] is True for key in ("numerical_passed", "state_prerequisites_passed",
                                                     "position_closure_passed", "static_force_passed"))
            and analysis["production_or_mission_verified"] is False, "R5.21 finalized control verdict")
    samples = previous["samples_in_probe_order"]
    ledger_order = [(entry["operation"], entry["args"][:2 if entry["operation"] == "binary64_field" else 3])
                    for entry in analysis["ledger"]
                    if {"raw", "returned_s", "completed_s"} <= entry.keys()]
    expected_order = []
    for sample in samples:
        ordinal = sample["observation_ordinal"]
        expected_order.append(("binary64_field", [ordinal, "d3"]))
        expected_order.extend(("decimal_field", [ordinal, d, precision])
                              for precision in (80, 100) for d in ("d1", "d2", "d3"))
    require(ledger_order == expected_order and len(analysis["ledger"]) == len(expected_order),
            "R5.21 analysis completed ledger order")
    measured, controls = {}, {}
    for sample, state, row in zip(samples, states, analysis["rows"], strict=True):
        ordinal = sample["observation_ordinal"]
        same([row["observation_ordinal"], row["elapsed_s"], row["hi_tdb_s"]],
             [ordinal, sample["elapsed_s"], sample["hi_tdb_s"]], "R5.21 control coepoch")
        require(sample["lo_hex"] == 0.0.hex(), "R5.21 control low word")
        require(row["static_force"]["passed"] is True and row["state_prerequisites_passed"] is True,
                "R5.21 control prerequisites")
        measured[sample["hi_hex"]] = {key: list(v) for key, v in state.items()}
        controls[("normal", sample["normal_kind"], sample["source_index"])] = row
    require(len(measured) == len(controls) == 3, "three distinct R5.21 controls and hi epochs")
    check()
    return measured, controls


def _archived_direct(observation: dict[str, Any]) -> dict[str, Any] | None:
    overall = observation["progress"]["sources"].get("Moon", {}).get("gates", {}).get("100", {}).get("overall")
    if overall is not None:
        require(type(overall) is dict and set(overall) == {"error_norm_m_s2", "envelope_m_s2", "passed"}
                and type(overall["passed"]) is bool, "R5.17 saved Moon gate")
        error = _decimal(overall["error_norm_m_s2"], "R5.17 saved Moon error")
        limit = _decimal(overall["envelope_m_s2"], "R5.17 saved Moon limit")
        require(error >= 0 and limit > 0 and (error <= limit) == overall["passed"],
                "R5.17 saved Moon gate consistency")
    return overall


def _coepoch(row: dict[str, Any], field: str) -> tuple[float, float, float]:
    return (number(row["elapsed_s"], field), number(row["hi_tdb_s"], field), number(row["lo_s"], field))


def _states(body_row: dict[str, Any], hi: float) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    states, states_si = {}, {}
    for key, body in (("E", "Earth"), ("B", "Moon")):
        saved = body_row["bodies"][body]
        require(saved["body"] == body and number(saved["epoch_tdb_s"], body).hex() == hi.hex(),
                body + " archive state/coepoch")
        raw = _numbers(saved["state_km_km_s"], 6, body + " raw state")
        si = _numbers(saved["state_si"], 6, body + " rounded SI state")
        same([v.hex() for v in si], [(1000.0 * v).hex() for v in raw], body + " original signed SI conversion")
        states[key], states_si[key] = raw, si
    return states, states_si


def _rows(metadata: dict[str, Any], study: dict[str, Any], records: dict[str, list[float]],
          measured: dict, controls: dict, check: Callable[[], Any]) -> list[dict[str, Any]]:
    profiles = study["profiles"]
    same([profile["name"] for profile in profiles], list(PROFILES), "frozen profile order")
    require(len(study["node_table"]) == 7
            and all(p["raw_returned"]["success"] is True and len(p["outputs"]) == 7 for p in profiles),
            "frozen profile/outputs completed")
    identities = [(profile, kind, i) for profile in PROFILES for kind in KINDS for i in range(7)]
    observations = study["observations"]
    same([[o[k] for k in ("profile", "kind", "index")] for o in observations],
         [list(key) for key in identities[:14]], "R5.17 assessed observation order")
    archived_direct = dict(zip(identities[:14], map(_archived_direct, observations), strict=True))
    failed = [key for key, gate in archived_direct.items() if gate is not None and not gate["passed"]]
    require(failed == [("normal", "rhs", 6)], "R5.17 original failed Moon gate")
    rhs = {profile: [row for row in study["rhs"] if row["profile"] == profile and row["completed"] is True][:7]
           for profile in PROFILES}
    require(all(len(rows) == 7 for rows in rhs.values()), "seven completed RHS per profile")
    t0 = Fraction(number(study["inputs"]["initial"]["epoch_tdb_s"], "initial TDB epoch"))
    result, hi_epochs, exact_epochs = [], set(), set()
    states_by_hi = {}
    lo_counts = {profile: {"positive": 0, "negative": 0} for profile in PROFILES}
    for inventory, (profile, kind, index) in zip(metadata["rows"], identities, strict=True):
        check()
        same([inventory[k] for k in ("profile", "kind", "index")], [profile, kind, index], "frozen row order")
        if kind == "output":
            motion_row = profiles[PROFILES.index(profile)]["outputs"][index]
            body_row = study["node_table"][index]
        else:
            motion_row = body_row = rhs[profile][index]
        same([motion_row["profile"], motion_row["index"]], [profile, index], "frozen motion row")
        elapsed, hi, lo = _coepoch(motion_row, "motion coepoch")
        words = [elapsed.hex(), hi.hex(), lo.hex()]
        same(words, [inventory[k] for k in ("elapsed_s_hex", "hi_hex", "lo_hex")], "frozen epoch words")
        same(words, [v.hex() for v in _coepoch(body_row, "source coepoch")], "frozen source coepoch")
        exact_t = Fraction(hi) + Fraction(lo)
        require(t0 + Fraction(elapsed) == exact_t and float(exact_t).hex() == hi.hex(),
                "exact frozen coepoch and rounded hi")
        for key, record in records.items():
            midpoint, radius = (Fraction(v) for v in record[:2])
            require(all(midpoint - radius <= epoch < midpoint + radius for epoch in (Fraction(hi), exact_t)),
                    key + " frozen epoch record coverage")
        motion = motion_row["motion"]
        same(number(motion["elapsed_s"], "archived motion elapsed").hex(), elapsed.hex(), "archived motion elapsed")
        for field in ("q_m", "w_m_s", "drift_m", "position_m", "velocity_m_s"):
            _numbers(motion[field], 3, field)
        geometry = motion_row["geometry"]["Moon"]
        _numbers(geometry["rephasing_m"], 3, "archived Moon rephasing")
        states, si = _states(body_row, hi)
        h = hi.hex()
        same(states, states_by_hi.setdefault(h, states.copy()), "shared hi Earth/Moon raw state bits")
        is_measured = h in measured
        same(inventory["moon_earth_leg"], "measured_0168" if is_measured else "unmeasured", "frozen source mode")
        if is_measured:
            for key in ("E", "B"):
                same(states[key], measured[h][key], "R5.17/R5.21 " + key + " raw state bits")
            states["G"] = measured[h]["G"]
        key = (profile, kind, index)
        control = controls.get(key)
        direct = archived_direct.get(key)
        if control is not None:
            require(is_measured and direct is not None and lo == 0, "R5.21 original control mapping")
            same(control["static_force"]["archived_direct_overall_passed"], direct["passed"],
                 "R5.21 archived direct verdict binding")
        result.append({"profile": profile, "kind": kind, "index": index,
                       "elapsed_s": elapsed, "hi_tdb_s": hi, "lo_s": lo, "motion": motion,
                       "moon_geometry": geometry, "states": states, "states_si": si,
                       "source_mode": "measured" if is_measured else "proxy",
                       "control": control, "archived_direct": direct})
        hi_epochs.add(Fraction(hi))
        exact_epochs.add(exact_t)
        if lo:
            lo_counts[profile]["positive" if lo > 0 else "negative"] += 1
    same({"rounded_hi": len(hi_epochs), "exact_t": len(exact_epochs),
          "union_for_reference": len(hi_epochs | exact_epochs), "measured_hi": len(measured),
          "unmeasured_hi": len(hi_epochs) - len(measured), "nonzero_low": lo_counts},
         metadata["epochs"], "frozen epoch inventory")
    require(sum(r["source_mode"] == "measured" for r in result) == 7
            and sum(r["control"] is not None for r in result) == 3,
            "frozen measured observation/control counts")
    return result


def load_inputs(root: Path, check: Callable[[], Any]) -> dict[str, Any]:
    """Bind 28 frozen rows and R5.21 controls without consulting any native data."""
    metadata = parse_json(_read_bound(root / EXPERIMENTS / "0169-inputs.json", INPUT_SHA256, check))
    hashes = metadata["archive_and_evidence_sha256"]
    bound = {name: _read_bound(root / name, expected, check) for name, expected in hashes.items()}
    previous = parse_json(bound[str(EXPERIMENTS / "0166-inputs.json")])
    archives = {}
    for path, name in ARCHIVES.items():
        unpacked = gzip.decompress(bound[path])
        require(sha256(unpacked).hexdigest() == previous["retained_uncompressed_sha256"][name],
                "uncompressed archive hash: " + name)
        check()
        archives[name] = parse_json(unpacked)
        check()
    study, audit = archives["study"], archives["audit"]
    _scope(study, audit, previous)
    measured, controls = _controls(root, metadata, previous, study, bound, check)
    records = _records(metadata, previous, study["inputs"])
    rows = _rows(metadata, study, records, measured, controls, check)
    check()
    return {"initial": study["inputs"]["initial"], "gm_m3_s2": previous["moon_gm_m3_s2"],
            "radius_m": previous["moon_radius_m"], "records": records, "rows": rows,
            "identity": {"inputs_sha256": INPUT_SHA256, "archive_and_evidence_sha256": hashes,
                         "retained_uncompressed_sha256": previous["retained_uncompressed_sha256"],
                         "historical_status": study["status"], "historical_audit_status": audit["audit_status"],
                         "historical_scientific_verified": study["scientific_verified"],
                         "historical_final_identity_complete": study["historical_final_identity_complete"],
                         "previous_preparation": metadata["previous_preparation"]}}
