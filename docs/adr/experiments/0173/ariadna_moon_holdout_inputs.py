"""Read the hash-bound ADR0172 inputs without native calls or field evaluation."""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from fractions import Fraction
import gzip
from hashlib import sha256
from pathlib import Path
from typing import Any

from ariadna_frozen_moon_inputs import load_inputs as load_frozen_screen_inputs
from ariadna_split_common import encode, journal_rows, number, parse_json, require, same
from ariadna_split_inputs import _numbers, _read_bound
from ariadna_split_inputs import load_inputs as load_split_source_inputs

EXPERIMENTS = "docs/adr/experiments/"
INPUT_PATH = EXPERIMENTS + "0172-inputs.json"
INPUT_SHA256 = "79ec97b9985d4dbdcb581b0991f0c976afac9cfc71e97d30868db5785f97d1a8"
SCREEN_FILES = {
    "execution.json", "screen.attempt.json", "screen.json", "screen.ledger.jsonl",
    "screen.parent-receipt.json", "screen.receipt.json",
}
SCREEN_COMPRESSED = {"screen.json", "screen.ledger.jsonl"}
SCREEN_CAPS = {
    "observation": 28, "reference_epoch": 29, "record": 58,
    "binary64_field": 28, "decimal_field": 224,
}
SOURCE = {
    "target": "Moon", "target_id": 301, "observer": "Earth", "observer_id": 399,
    "orientation": "J2000", "aberration_correction": "NONE", "epoch_scale": "TDB seconds from J2000",
    "raw_state_units": ["km", "km/s"], "reference_state_units": ["m", "m/s"],
}
NATIVE_KEYS = (
    "historical_identity", "records", "original_ordered_pool_manifest",
    "local_cspice_file_pin", "locked_selected_kernel_sha256",
)


def _sha(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _screen_files(
    inventory: dict[str, Any], manifest: dict[str, Any], bound: dict[str, bytes], check: Callable[[], Any],
) -> dict[str, bytes]:
    require(set(manifest["retained_files"]) == SCREEN_FILES, "R5.24 retained file set")
    saved = {}
    for name, entry in manifest["retained_files"].items():
        compressed = name in SCREEN_COMPRESSED
        path = EXPERIMENTS + "0171/" + name + (".gz" if compressed else "")
        same([entry["path"], entry["compression"]], [path, "gzip" if compressed else None],
             "R5.24 retained path and encoding")
        require(entry["sha256"] == inventory["retained_evidence_sha256"][path], "R5.24 packed digest")
        raw = gzip.decompress(bound[path]) if compressed else bound[path]
        require(_sha(raw) == entry["uncompressed_sha256"] and len(raw) == entry["uncompressed_bytes"],
                "R5.24 uncompressed hash: " + name)
        saved[name] = raw
        check()
    same(manifest["raw_sha256"], {name: _sha(raw) for name, raw in saved.items() if name != "execution.json"},
         "R5.24 raw file digests")
    require(_sha(saved["execution.json"]) == manifest["invocation_sha256"], "R5.24 invocation hash")
    for key, name in (("report", "screen.json"), ("journal", "screen.ledger.jsonl")):
        require(_sha(saved[name]) == inventory[f"r524_uncompressed_{key}_sha256"],
                "R5.24 inventory uncompressed " + key + " hash")
    return saved


def _validate_screen(
    manifest: dict[str, Any], saved: dict[str, bytes], prep_sha: str, check: Callable[[], Any],
) -> dict[str, Any]:
    report, child, parent, attempt, invocation = (
        parse_json(saved[name]) for name in ("screen.json", "screen.receipt.json",
                                            "screen.parent-receipt.json", "screen.attempt.json", "execution.json")
    )
    require(manifest["stage"] == "R5.24" and manifest["attempts"] == 1
            and manifest["conditional_screen_passed"] is True and manifest["live_holdout_executed"] is False
            and manifest["r517_remains_failed"] is True, "R5.24 retained scope and verdict")
    same([report["contract"], report["execution"], report["budget_s"], report["status"], report["numerical_passed"],
          report["unavailable"], report["native_calls"], report["new_record_acquisitions"], report["propagations"],
          report["r517_requalified"], report["final_archive_identity_complete"]],
         ["ADR0169", "archived", 10.0, "passed", True, [], 0, 0, 0, False, True], "R5.24 completed report")
    require("error" not in report and len(report["rows"]) == 28, "R5.24 complete observation set")
    require(report["identity_pin"]["preparation_sha256"] == manifest["preparation_sha256"] == prep_sha,
            "R5.24 preparation identity")
    same(report["final_identity_pin"], report["identity_pin"], "R5.24 final preparation identity")
    same(attempt, {"contract": "ADR0169", "preparation_sha256": prep_sha}, "R5.24 attempt marker")
    same([child["status"], child["finalization"], child["external_start_s"],
          child["report_sha256"], child["journal_sha256"]],
         ["passed", "passed", report["external_start_s"], _sha(saved["screen.json"]), _sha(saved["screen.ledger.jsonl"])],
         "R5.24 child receipt")
    same([parent["contract"], parent["returncode"], parent["stderr"], parent["finalization"],
          parent["external_start_s"], parent["preparation_sha256"], parent["attempt_sha256"], parent["child_receipt_sha256"]],
         ["ADR0169", 0, "", "passed", report["external_start_s"], prep_sha,
          _sha(saved["screen.attempt.json"]), _sha(saved["screen.receipt.json"])], "R5.24 parent receipt")
    same([invocation["returncode"], invocation["argv"][1:4], invocation["argv"][-1]],
         [0, ["-I", "-S", "-B"], prep_sha], "R5.24 outer invocation")

    boot, reported, child_s, parent_s, outer_s = map(
        lambda value: number(value, "R5.24 timeline"),
        (report["child_start_elapsed_s"], report["elapsed_before_report_s"], child["elapsed_before_receipt_s"],
         parent["external_elapsed_s"], invocation["external_elapsed_s"]),
    )
    require(0 <= boot <= reported <= child_s <= parent_s <= outer_s <= 10.0, "R5.24 receipt timeline")
    observed: Counter[str] = Counter()
    events = []
    cursor = boot
    for index, entry in enumerate(report["ledger"]):
        check()
        require(set(entry) == {"operation", "api", "args", "attempted_s", "raw", "returned_s", "completed_s"},
                "R5.24 incomplete ledger operation")
        for stamp in ("attempted_s", "returned_s", "completed_s"):
            current = number(entry[stamp], "R5.24 ledger stamp")
            require(cursor <= current <= reported, "R5.24 ledger timeline")
            cursor = current
        observed[entry["operation"]] += 1
        events.extend(journal_rows(index, entry))
    require(observed == SCREEN_CAPS, "R5.24 ledger operation counts")
    same(report["counts"], {op: dict.fromkeys(("attempted", "returned", "completed"), n) for op, n in SCREEN_CAPS.items()},
         "R5.24 report counts")
    same(report["counts"], manifest["counts"], "R5.24 manifest counts")
    require(b"".join(map(encode, events)) == saved["screen.ledger.jsonl"], "R5.24 durable journal")
    check()
    return report


def _epochs(
    inventory: dict[str, Any], rows: list[dict[str, Any]], frozen: list[dict[str, Any]], check: Callable[[], Any],
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    selected_ordinals, measured = [], set()
    signs: Counter[str] = Counter()
    lower, upper = inventory["moon_segment"]["record_interval_tdb_s"]
    require(len(rows) == len(frozen) == 28, "R5.24 row inventory")
    for ordinal, (row, original) in enumerate(zip(rows, frozen, strict=True)):
        check()
        same([row["observation_ordinal"], row["status"]], [ordinal, "passed"], "R5.24 passed row identity")
        for key in ("profile", "kind", "index", "source_mode"):
            same(row[key], original[key], "R5.24 frozen row " + key)
        for key in ("elapsed_s", "hi_tdb_s", "lo_s"):
            require(number(row[key], key).hex() == original[key].hex(), "R5.24 frozen epoch " + key)
        hi = number(row["hi_tdb_s"], "R5.24 rounded epoch")
        hi_hex = hi.hex()
        if row["source_mode"] == "measured":
            measured.add(hi_hex)
            continue
        require(row["source_mode"] == "proxy" and lower <= hi < upper, "R5.24 proxy record coverage")
        lo = row["lo_s"]
        signs["positive" if lo > 0 else "negative" if lo < 0 else "zero"] += 1
        selected_ordinals.append(ordinal)
        ref = row["reference_states_si"]["hi"]["G"]
        require(type(ref) is list and len(ref) == 6
                and all(type(word) is str and str(Fraction(word)) == word for word in ref),
                "R5.24 canonical exact geocentric state")
        proxy = _numbers(row["geocentric_position_km"], 3, "R5.24 proxy position km")
        same([value.hex() for value in proxy], [float(Fraction(word) / 1000).hex() for word in ref[:3]],
             "R5.24 rounded proxy bits")
        states = row["raw_states_km_km_s"]
        same(states, original["states"], "R5.24 frozen E/B states")
        same(row["closure"]["position_matches"], [True] * 3, "R5.24 archived proxy closure")
        operands = {
            "hi_tdb_s": hi, "reference_si": ref, "proxy_position_km": proxy,
            "earth_ssb_km_km_s": _numbers(states["E"], 6, "R5.24 Earth/SSB"),
            "moon_ssb_km_km_s": _numbers(states["B"], 6, "R5.24 Moon/SSB"),
        }
        group = groups.setdefault(hi_hex, {"operands": operands, "ordinals": []})
        same(group["operands"], operands, "R5.24 duplicate epoch operands")
        group["ordinals"].append(ordinal)
    require(len(groups) == 16 and len(measured) == 3 and measured.isdisjoint(groups)
            and len(selected_ordinals) == 21 and sum(len(g["ordinals"]) == 2 for g in groups.values()) == 5,
            "ADR0172 exact proxy epoch coverage")
    same(selected_ordinals, inventory["covered_proxy_observation_ordinals"], "ADR0172 selected ordinals")
    same(sorted(measured), inventory["excluded_measured_hi_hex"], "ADR0172 excluded measured epochs")
    same(dict(signs), inventory["mapped_low_word_sign_counts"], "ADR0172 mapped low word signs")

    epochs = []
    for (hi_hex, group), expected in zip(groups.items(), inventory["epochs_in_query_order"], strict=True):
        check()
        operands, ordinals = group["operands"], group["ordinals"]
        states = {"E": operands["earth_ssb_km_km_s"], "B": operands["moon_ssb_km_km_s"]}
        same(expected, {
            "hi_hex": hi_hex, "first_observation_ordinal": ordinals[0], "observation_ordinals": ordinals,
            "proxy_position_km_hex": [value.hex() for value in operands["proxy_position_km"]],
            "exact_hi_geocentric_state_si_sha256": _sha(encode(operands["reference_si"])),
            "archived_earth_ssb_and_moon_ssb_state_km_km_s_sha256": _sha(encode(states)),
        }, "ADR0172 ordered epoch and operand identity")
        epochs.append({**operands, "observation_ordinals": ordinals})
    return epochs


def load_inputs(root: Path, check: Callable[[], Any]) -> dict[str, Any]:
    """Read and validate the fixed 16-epoch Moon/Earth reference and capture pins."""
    inventory = parse_json(_read_bound(root / INPUT_PATH, INPUT_SHA256, check))
    require(inventory["stage"] == "R5.25" and inventory["ordered_kernel_count"] == 13,
            "ADR0172 holdout stage and kernel count")
    same(inventory["source"], SOURCE, "ADR0172 source convention")
    direct = inventory["retained_evidence_sha256"]
    bound = {path: _read_bound(root / path, digest, check) for path, digest in direct.items()}
    manifest = parse_json(bound[EXPERIMENTS + "0171-verification.json"])
    saved = _screen_files(inventory, manifest, bound, check)
    report = _validate_screen(manifest, saved, direct[EXPERIMENTS + "0170-verification.json"], check)

    native = load_split_source_inputs(root, check)
    frozen = load_frozen_screen_inputs(root, check)
    same(report["input_identity"], frozen["identity"], "R5.24 original archive and provider identity")
    same(native["records"][0], inventory["moon_segment"], "ADR0172 selected Moon Type 2 record")
    require(native["locked_selected_kernel_sha256"] == inventory["selected_kernel_sha256"]
            and len(native["original_ordered_pool_manifest"]["kernels"]) == inventory["ordered_kernel_count"]
            and _sha(encode(frozen["records"]["G"])) == inventory["archived_moon_record_words_sha256"],
            "ADR0172 archived record and kernel identity")
    same(sorted(row["hi_hex"] for row in native["samples_in_probe_order"]), inventory["excluded_measured_hi_hex"],
         "ADR0172 R5.21 measured epochs")
    epochs = _epochs(inventory, report["rows"], frozen["rows"], check)

    hashes = direct.copy()
    for part in (native["archival_sha256"], frozen["identity"]["archive_and_evidence_sha256"]):
        for path, expected in part.items():
            require(hashes.setdefault(path, expected) == expected, "ADR0172 retained digest conflict: " + path)
    check()
    return {
        **{name: native[name] for name in NATIVE_KEYS},
        "epochs": epochs,
        "identity": {
            "inputs_sha256": INPUT_SHA256, "retained_evidence_sha256": hashes,
            "r524_report_sha256": inventory["r524_uncompressed_report_sha256"],
            "r524_journal_sha256": inventory["r524_uncompressed_journal_sha256"],
            "r521_preparation_sha256": frozen["identity"]["previous_preparation"]["preparation_sha256"],
        },
    }
