"""Read checked ADR0175 operands without calling a provider or evaluating a field."""
from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
import gzip
from hashlib import sha256
from pathlib import Path
from typing import Any

from ariadna_frozen_moon_inputs import load_inputs as load_screen_inputs
from ariadna_moon_holdout_capture import CAPTURE_CAPS, validate_capture
from ariadna_moon_holdout_inputs import load_inputs as load_holdout_inputs
from ariadna_split_common import BUDGETS, digest, encode, journal_rows, number, parse_json, require, same
from ariadna_split_inputs import _read_bound

EXPERIMENTS = "docs/adr/experiments/"
INPUT_PATH = EXPERIMENTS + "0175-inputs.json"
INPUT_SHA256 = "785bdb62e43e122d8e4bd70d35586ce481f215118d0254dfebecb85a1974524d"
ORDINALS = (1, 2, 4, 6, 11, 15, 16, 18, 20, 25, 27)
_HOLDOUT_PREFIX = EXPERIMENTS + "0174/"
_PHASE_SUFFIXES = ("json", "ledger.jsonl", "attempt.json", "receipt.json", "parent-receipt.json")
_PHASE_FILES = {f"{_HOLDOUT_PREFIX}{phase}.{suffix}" for phase in ("capture", "analysis")
                for suffix in _PHASE_SUFFIXES}
_CHECKS = {name: dict(checked=n, expected=n, passed=ok) for name, n, ok in (
    ("state_parity", 16, 16), ("position_parity", 16, 16), ("velocity_parity", 16, 16),
    ("archived_closure_bits", 48, 48), ("proxy_position_bits", 48, 39),
)}


def verify_bound_inputs(root: Path, identity: dict[str, Any], check: Callable[[], None]) -> None:
    """Recheck the exact archive inventory before finalizing new evidence."""
    saved = parse_json(_read_bound(root / INPUT_PATH, INPUT_SHA256, check))
    same(identity, _identity(saved), "ADR0175 input identity")
    for path, expected in identity["retained_evidence_sha256"].items():
        check()
        require(digest(root / path) == expected, "final archive hash: " + Path(path).name)
    check()


def _identity(saved: dict[str, Any]) -> dict[str, Any]:
    return {"inputs_sha256": INPUT_SHA256, "retained_evidence_sha256": saved["retained_evidence_sha256"],
            "r524_report_sha256": saved["r524_uncompressed_report_sha256"],
            "r524_journal_sha256": saved["r524_uncompressed_journal_sha256"]}


def _phase(
    bound: dict[str, bytes], phase: str, pin: dict[str, Any], input_identity: dict[str, Any],
    check: Callable[[], None],
) -> dict[str, Any]:
    """Verify already finalized R5.27 evidence from the bytes actually admitted."""
    report_raw, journal, attempt_raw, child_raw, parent_raw = (
        bound[f"{_HOLDOUT_PREFIX}{phase}.{suffix}"] for suffix in _PHASE_SUFFIXES
    )
    report, attempt, child, parent = map(parse_json, (report_raw, attempt_raw, child_raw, parent_raw))
    marker = {"contract": "ADR0172", "phase": phase, "preparation_sha256": pin["preparation_sha256"]}
    same(attempt, marker, f"R5.27 {phase} attempt marker")
    status, code = ("passed", 0) if phase == "capture" else ("failed", 2)
    budget = BUDGETS[phase]
    caps = CAPTURE_CAPS if phase == "capture" else {"epoch": 16}
    same({key: report[key] for key in (
        "contract", "phase", "execution", "status", "budget_s", "unavailable", "new_record_acquisitions",
        "propagations", "r517_requalified", "final_archive_identity_complete", "explicit_native_attempts",
    )}, {"contract": "ADR0172", "phase": phase, "execution": "live", "status": status,
         "budget_s": budget, "unavailable": [], "new_record_acquisitions": 0, "propagations": 0,
         "r517_requalified": False, "final_archive_identity_complete": True,
         "explicit_native_attempts": sum(caps.values()) if phase == "capture" else 0}, f"R5.27 {phase} scope")
    same([report["identity_pin"], report["final_identity_pin"], report["input_identity"]],
         [pin, pin, input_identity], f"R5.27 {phase} identity")
    start = report["external_start_s"]
    same(child, {"status": status, "finalization": "passed", "external_start_s": start,
                 "report_sha256": sha256(report_raw).hexdigest(), "journal_sha256": sha256(journal).hexdigest(),
                 "elapsed_before_receipt_s": child["elapsed_before_receipt_s"]}, f"R5.27 {phase} child receipt")
    same(parent, {**marker, "returncode": code, "stderr": "", "finalization": "passed",
                  "external_start_s": start, "attempt_sha256": sha256(attempt_raw).hexdigest(),
                  "child_receipt_sha256": sha256(child_raw).hexdigest(),
                  "external_elapsed_s": parent["external_elapsed_s"]}, f"R5.27 {phase} parent receipt")
    boot, reported, child_s, parent_s = (number(value, "R5.27 phase time") for value in (
        report["child_start_elapsed_s"], report["elapsed_before_report_s"], child["elapsed_before_receipt_s"],
        parent["external_elapsed_s"],
    ))
    require(0 <= boot <= reported <= child_s <= parent_s <= budget, f"R5.27 {phase} receipt timeline")
    observed = dict.fromkeys(caps, 0)
    events = []
    cursor = boot
    for index, entry in enumerate(report["ledger"]):
        check()
        require(entry["operation"] in caps and set(entry) == {
            "operation", "api", "args", "attempted_s", "raw", "returned_s", "completed_s",
        }, f"R5.27 {phase} incomplete ledger entry")
        for key in ("attempted_s", "returned_s", "completed_s"):
            stamp = number(entry[key], "R5.27 ledger time")
            require(cursor <= stamp <= reported, f"R5.27 {phase} ledger timeline")
            cursor = stamp
        observed[entry["operation"]] += 1
        events.extend(journal_rows(index, entry))
    same(observed, caps, f"R5.27 {phase} ledger counts")
    same(report["counts"], {op: dict.fromkeys(("attempted", "returned", "completed"), count)
                            for op, count in caps.items()}, f"R5.27 {phase} report counts")
    require(b"".join(map(encode, events)) == journal, f"R5.27 {phase} durable journal")
    check()
    return report


def _holdout(
    bound: dict[str, bytes], hashes: dict[str, str], bundle: dict[str, Any], check: Callable[[], None],
) -> tuple[dict[str, Any], dict[str, Any], list[list[float]]]:
    manifest = parse_json(bound[EXPERIMENTS + "0174-verification.json"])
    prep_path = EXPERIMENTS + "0173-verification.json"
    prep = parse_json(bound[prep_path])
    require(prep["preparation_complete"] is True and prep["inputs_sha256"] == bundle["identity"]["inputs_sha256"],
            "R5.26 preparation identity")
    pin = {"inputs_sha256": prep["inputs_sha256"], "preparation_sha256": hashes[prep_path],
           "tested_source_sha256": prep["tested_source_sha256"], "reused_source_sha256": prep["reused_source_sha256"]}
    same(manifest["preparation"], pin, "R5.27 preparation pin")
    same(manifest["raw_evidence_sha256"], {path: hashes[path] for path in _PHASE_FILES}, "R5.27 evidence pins")
    same(manifest["input_identity"], bundle["identity"], "R5.27 frozen input identity")
    same([manifest["attempts"], manifest["holdout_confirmed"], manifest["runner_returncode"], manifest["unavailable"]],
         [{"capture": 1, "analysis": 1}, False, 2, []], "R5.27 finalized proxy-bit negative")
    capture = _phase(bound, "capture", pin, bundle["identity"], check)
    require("error" not in capture, "R5.27 capture not clean")
    states = validate_capture(bundle, capture, pin)
    check()
    analysis = _phase(bound, "analysis", pin, bundle["identity"], check)
    same([analysis["capture_parent_sha256"], analysis["capture_receipt_sha256"]],
         [hashes[_HOLDOUT_PREFIX + "capture.parent-receipt.json"], hashes[_HOLDOUT_PREFIX + "capture.receipt.json"]],
         "R5.27 capture-to-analysis receipt binding")
    same([analysis["analysis_phase"], analysis["native_calls"], analysis["force_evaluations"],
          analysis["trajectory_propagations"], analysis.get("execution_incomplete", False)],
         ["complete", 0, 0, 0, False], "R5.27 analysis final scope")
    same(analysis["checks"], _CHECKS, "R5.27 original parity, closure and proxy counts")
    same(analysis["verdicts"], {key: key != "proxy_position_bits" for key in _CHECKS},
         "R5.27 verdict classification")
    same(manifest["checks"], analysis["checks"], "R5.27 manifest counts")
    same(manifest["verdicts"], analysis["verdicts"], "R5.27 manifest verdicts")
    require(analysis["error"]["type"] == "NumericalCheck" and analysis["error"]["message"] == "failed proxy_position",
            "R5.27 negative must be a completed proxy-bit comparison")
    same(manifest["earliest_failure"], analysis["error"], "R5.27 earliest failure")
    return capture, analysis, states


def _rows(
    saved: dict[str, Any], screen: dict[str, Any], original: dict[str, Any],
    epochs: list[dict[str, Any]], capture: dict[str, Any], analysis: dict[str, Any],
    states: list[list[float]], check: Callable[[], None],
) -> list[dict[str, Any]]:
    entries = [(i, entry) for i, entry in enumerate(capture["ledger"]) if entry["operation"] == "state"]
    rows, observed, matched, misses = {}, {}, [], []
    same(len(epochs), 16, "R5.27 epoch count")
    for idx, (epoch, state, row, (ledger_index, entry), compare) in enumerate(zip(
        epochs, states, analysis["rows"], entries, analysis["ledger"], strict=True,
    )):
        check()
        hi = epoch["hi_tdb_s"]
        same([entry["api"], entry["args"], entry["raw"][0]],
             ["spkezr", ["Moon", hi, "J2000", "NONE", "Earth"], state], "R5.27 captured state")
        same([row["epoch_index"], row["hi_tdb_s"], row["observation_ordinals"], row["raw_state_km_km_s"]],
             [idx, hi, epoch["observation_ordinals"], state], "R5.27 state analysis mapping")
        same([compare["api"], compare["args"], compare["raw"]],
             ["compare_geocentric_state", [idx, hi], row], "R5.27 analysis ledger binding")
        require(row["parity"]["passed"] is True and row["archived_closure"]["passed"] is True,
                "R5.27 state prerequisite")
        proxy = epoch["proxy_position_km"]
        bits = [a.hex() == b.hex() for a, b in zip(proxy, state[:3], strict=True)]
        same(row["proxy_position"]["bit_matches"], bits, "R5.27 proxy bit classification")
        if all(bits):
            matched.extend(row["observation_ordinals"])
            continue
        misses.append(idx)
        for ordinal in row["observation_ordinals"]:
            archive, frozen = screen["rows"][ordinal], original["rows"][ordinal]
            require(ordinal not in rows and archive["status"] == "passed"
                    and archive["source_mode"] == "proxy" and archive["hi_tdb_s"].hex() == hi.hex(),
                    "R5.24 affected row identity")
            lo, elapsed = archive["lo_s"], archive["elapsed_s"]
            exact = Fraction(archive["exact_tdb_s"])
            require(Fraction(original["initial"]["epoch_tdb_s"]) + Fraction(elapsed) == exact
                    == Fraction(hi) + Fraction(lo) and float(exact).hex() == hi.hex(), "R5.24 exact coepoch")
            same(archive["geocentric_position_km"], proxy, "R5.24 original proxy")
            same(archive["raw_states_km_km_s"], frozen["states"], "R5.24 original Earth and Moon states")
            same(archive["motion"], {
                **{key: frozen["motion"][key] for key in ("q_m", "w_m_s", "drift_m")},
                "saved_moon_velocity_m_s": frozen["states_si"]["B"][3:],
                "rephasing_m": frozen["moon_geometry"]["rephasing_m"],
            }, "R5.24 original frozen motion")
            observed[ordinal] = {
                "observation_ordinal": ordinal, "profile": archive["profile"], "kind": archive["kind"],
                "index": archive["index"], "elapsed_s_hex": elapsed.hex(), "hi_tdb_s_hex": hi.hex(),
                "lo_s_hex": lo.hex(), "holdout_epoch_index": idx, "capture_ledger_index": ledger_index,
                "r524_row_sha256": sha256(encode(archive)).hexdigest(),
                "r527_state_entry_sha256": sha256(encode(entry)).hexdigest(),
            }
            rows[ordinal] = {"archive": archive, "captured_state_km_km_s": state}
    same(sorted(rows), list(ORDINALS), "ADR0175 affected ordinal set")
    same(sorted(matched), saved["excluded_proxy_match_ordinals"], "ADR0175 excluded matched rows")
    same(misses, [0, 1, 3, 4, 8, 13, 15], "ADR0175 affected capture epochs")
    same([observed[n] for n in ORDINALS], saved["rows_in_r524_order"], "ADR0175 ordered row and state pins")
    return [rows[n] for n in ORDINALS]


def load_inputs(root: Path, check: Callable[[], None]) -> dict[str, Any]:
    """Admit only the eleven bound pairs in R5.24 order, with raw full states."""
    saved = parse_json(_read_bound(root / INPUT_PATH, INPUT_SHA256, check))
    require(saved["stage"] == "R5.28" and saved["excluded_original_measured_count"] == 7,
            "ADR0175 inventory scope")
    identity = _identity(saved)
    hashes = identity["retained_evidence_sha256"]
    require(len(hashes) == 41, "ADR0175 archive inventory size")
    bound = {name: _read_bound(root / name, expected, check) for name, expected in hashes.items()}
    holdout = load_holdout_inputs(root, check)
    old = load_screen_inputs(root, check)
    require(all(hashes[path] == value for path, value in holdout["identity"]["retained_evidence_sha256"].items()),
            "ADR0175 transitive archive digests")
    screen_report, screen_journal = (gzip.decompress(bound[EXPERIMENTS + f"0171/screen.{suffix}.gz"])
                                     for suffix in ("json", "ledger.jsonl"))
    check()
    same([sha256(screen_report).hexdigest(), sha256(screen_journal).hexdigest()],
         [identity["r524_report_sha256"], identity["r524_journal_sha256"]], "R5.24 uncompressed archive hashes")
    same([identity["r524_report_sha256"], identity["r524_journal_sha256"]],
         [holdout["identity"]["r524_report_sha256"], holdout["identity"]["r524_journal_sha256"]],
         "R5.24 finalized archive binding")
    report = parse_json(screen_report)
    same(report["input_identity"], old["identity"], "R5.24 frozen input identity")
    same([old["initial"]["epoch_tdb_s"].hex(), old["gm_m3_s2"].hex(), old["radius_m"].hex()],
         [saved["frozen_t0_tdb_s_hex"], saved["moon_gm_m3_s2_hex"], saved["moon_radius_m_hex"]],
         "ADR0175 original epoch and Moon constants")
    capture, analysis, states = _holdout(bound, hashes, holdout, check)
    rows = _rows(saved, report, old, holdout["epochs"], capture, analysis, states, check)
    check()
    return {"initial": old["initial"], "gm_m3_s2": old["gm_m3_s2"], "radius_m": old["radius_m"],
            "rows": rows, "identity": identity}
