"""Hash-bound R5.20 inputs from saved evidence, with no scientific imports."""
from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction
import gzip
from hashlib import sha256
from pathlib import Path
from typing import Any

from ariadna_split_common import number, parse_json, require, same

INPUT_PATH = "docs/adr/experiments/0166-inputs.json"
INPUT_SHA256 = "8fa40d6a1ec812400a8dc8d052f48700b09f6ba5eadf351f55c3a647519bb136"
ARCHIVE_PREFIX = "docs/adr/experiments/0164-corrected-"
SAMPLES = (
    (13, "rhs", 6, 0.25, "0x1.d2d247fbd7e7ap+29", False),
    (0, "output", 0, 0.0, "0x1.d2d247f9d7e7ap+29", True),
    (5, "output", 5, 250.0, "0x1.d2d24fc9d7e7ap+29", True),
)
ZERO_HEX = "0x0.0p+0"


def _numbers(value: Any, size: int, field: str) -> list[float]:
    require(type(value) is list and len(value) == size, field + " dimensions")
    return [number(component, field) for component in value]


def _rational(value: Any, field: str) -> Fraction:
    require(type(value) is dict and set(value) == {"numerator", "denominator"}, field)
    n, d = value["numerator"], value["denominator"]
    require(type(n) is str and type(d) is str, field + " integer strings")
    denominator = int(d)
    require(denominator > 0, field + " positive denominator")
    return Fraction(int(n), denominator)


def _rational_vector(value: Any, field: str) -> list[Fraction]:
    require(type(value) is list and len(value) == 3, field + " dimensions")
    return [_rational(component, field) for component in value]


def _decimal(value: Any, field: str) -> Decimal:
    require(type(value) is str, field + " decimal string")
    result = Decimal(value)
    require(result.is_finite(), field + " finite decimal")
    return result


def _read_bound(path: Path, expected: str, check: Callable[[], None]) -> bytes:
    check()
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == expected, "archive hash: " + path.name)
    check()
    return raw


def _require_coepoch(row: dict[str, Any], elapsed_s: float, hi: str, field: str) -> None:
    require(number(row["elapsed_s"], field).hex() == elapsed_s.hex()
            and number(row["hi_tdb_s"], field).hex() == hi
            and number(row["lo_s"], field).hex() == ZERO_HEX, field + " coepoch")


def _segment_checks(metadata: dict[str, Any], study_inputs: dict[str, Any]) -> None:
    records = metadata["records"]
    archived = study_inputs["source_rows_template"]["Moon"]["segments"]
    require(len(records) == len(archived) == 2, "two retained descriptors")
    for record, source, body, centre in zip(records, archived, (301, 399), (399, 0), strict=True):
        require(record["body"] == body and record["centre"] == centre
                and record["frame"] == 1 and record["type"] == 2, "retained descriptor chain")
        keys = ("body", "centre", "frame", "type", "begin", "end", "path", "label", "address", "index",
                "trailer", "first_tdb_s", "last_tdb_s")
        same({key: record[key] for key in keys}, {key: source[key] for key in keys},
             "study descriptor binding")
        same(record["descriptor_hex"],
             [word.hex() for word in _numbers(source["descriptor"], 5, "descriptor words")],
             "study descriptor bits")
        start, step, size, count = _numbers(record["trailer"], 4, "Type 2 trailer")
        # Degree 12 means a midpoint, radius, then 13 coefficients per axis.
        require(size == record["word_count"] == 41 and step > 0 and count.is_integer(),
                "Type 2 record size")
        index = record["index"]
        require(index == 12192 and 0 <= index < count
                and record["address"] == record["begin"] + index * size
                and record["end"] == record["begin"] + count * size + 3,
                "Type 2 record addresses")
        lower = start + step * index
        same(record["record_interval_tdb_s"], [int(lower), int(lower + step)], "Type 2 interval")
        require(record["first_tdb_s"] <= lower < lower + step <= record["last_tdb_s"]
                and all(lower <= float.fromhex(hi) < lower + step for _, _, _, _, hi, _ in SAMPLES),
                "Type 2 sample coverage")


def _references(metadata: dict[str, Any], study: dict[str, Any], audit: dict[str, Any],
                check: Callable[[], None]) -> list[dict[str, Any]]:
    require(study["contract"] == audit["contract"] == "ADR0162"
            and study["status"] == "failed" and audit["audit_status"] == "partial"
            and study["scientific_verified"] is False and audit["scientific_verified"] is False
            and study["finalization_gate"] == audit["finalization_gate"] == "passed",
            "retained R5.17 verdict/finalization")
    require(audit["evidence_sha256"] == metadata["retained_uncompressed_sha256"]["study"]
            and audit["checks"]["observations"] == 14
            and audit["counts"]["source_rows"] == {"attempted": 28, "completed": 27}
            and audit["counts"]["reference_fields"] == {"attempted": 224, "completed": 224},
            "partial audit study hash and verified prefix")
    for key, expected in (("origin", "SSB"), ("orientation", "J2000"), ("time_scale", "TDB"),
                          ("aberration_correction", "NONE"), ("position_units", "m"),
                          ("velocity_units", "m/s"), ("acceleration_units", "m/s^2")):
        require(study[key] == expected, "retained convention: " + key)

    study_inputs = study["inputs"]
    initial = metadata["frozen_initial"]
    same(study_inputs["initial"], initial, "study initial state")
    same(metadata["moon_gm_m3_s2"], study_inputs["gm_m3_s2"]["Moon"], "study Moon GM")
    same(metadata["moon_radius_m"], study_inputs["radii_m"]["Moon"], "study Moon radius")
    pool = metadata["original_ordered_pool_manifest"]
    same(study_inputs["kernel_manifest"], pool, "study kernel manifest")
    same(study["identities"]["before"]["kernels"], pool, "study before kernel manifest")
    require(pool["loaded_kernel_count"] == len(pool["kernels"]) == 13, "retained kernel count")
    selected = [kernel for kernel in pool["kernels"]
                if kernel["name"] == Path(metadata["records"][0]["path"]).name]
    require(len(selected) == 1 and selected[0]["sha256"] == metadata["locked_selected_kernel_sha256"]
            and selected[0]["type"] == "SPK" and metadata["records"][0]["path"] == metadata["records"][1]["path"],
            "retained INPOP19a digest and record path")
    _segment_checks(metadata, study_inputs)

    r0 = [Fraction(v) for v in _numbers(initial["position_m"], 3, "r0_m")]
    v0 = [Fraction(v) for v in _numbers(initial["velocity_m_s"], 3, "v0_m_s")]
    t0 = Fraction(number(initial["epoch_tdb_s"], "t0_tdb_s"))
    require(len(metadata["samples_in_probe_order"]) == len(SAMPLES), "three frozen rows")
    refs = []
    for sample, (ordinal, kind, index, elapsed_s, hi, baseline) in zip(
            metadata["samples_in_probe_order"], SAMPLES, strict=True):
        check()
        same([sample[key] for key in ("observation_ordinal", "normal_kind", "source_index", "elapsed_s",
                                      "hi_hex", "retained_moon_overall_gate_passed")],
             [ordinal, kind, index, elapsed_s, hi, baseline], "frozen sample identifier")
        require(number(sample["hi_tdb_s"], "sample hi").hex() == hi and sample["lo_hex"] == ZERO_HEX,
                "frozen sample epoch")
        epoch = Fraction(float.fromhex(hi))
        require(t0 + Fraction(elapsed_s) == epoch, "exact elapsed-time coepoch")
        obs = study["observations"][ordinal]
        same([obs["profile"], obs["kind"], obs["index"]], ["normal", kind, index], "study observation")
        progress = obs["progress"]
        if kind == "rhs":
            motion_row = body_row = study["rhs"][index]
            require(body_row["completed"] is True, "study RHS completed")
        else:
            require(study["profiles"][0]["name"] == "normal", "study output profile")
            motion_row = study["profiles"][0]["outputs"][index]
            body_row = study["node_table"][index]
        same([motion_row["profile"], motion_row["index"]], ["normal", index], "study motion row")
        _require_coepoch(motion_row, elapsed_s, hi, "study motion")
        _require_coepoch(body_row, elapsed_s, hi, "study body")
        motion = motion_row["motion"]
        same(motion["elapsed_s"], elapsed_s, "study elapsed motion")
        same(motion["q_m"], sample["frozen_q_m"], "study q")
        same(motion["drift_m"], sample["frozen_drift_m"], "study rounded drift")
        q = [Fraction(v) for v in _numbers(motion["q_m"], 3, "q_m")]
        ref: dict[str, Any] = {}
        for body in ("Earth", "Moon"):
            saved = body_row["bodies"][body]
            require(saved["body"] == body and number(saved["epoch_tdb_s"], body).hex() == hi,
                    "study source identity/coepoch: " + body)
            raw = _numbers(saved["state_km_km_s"], 6, body + " raw state")
            same([v.hex() for v in raw], sample["raw_hex"][body], body + " retained raw state bits")
            saved_si = _numbers(saved["state_si"], 6, body + " SI state")
            same(saved_si, [1000.0 * v for v in raw], body + " saved SI conversion")
            source = progress["bodies"][body]["source_assessment"]
            require(source["passed"] is True and source["hi_hex"] == hi and source["lo_hex"] == ZERO_HEX
                    and number(source["hi_tdb_s"], body).hex() == hi
                    and number(source["lo_tdb_s"], body).hex() == ZERO_HEX
                    and _rational(source["exact_epoch_tdb_s"], "source epoch") == epoch,
                    "audited exact source epoch: " + body)
            exact = source["exact"]
            position_m = _rational_vector(exact["position_hi_m"], body + " exact position")
            velocity_m_s = _rational_vector(exact["velocity_hi_m_s"], body + " exact velocity")
            residual = _rational_vector(exact["source_position_floor_m"], body + " source residual")
            require(not any(_rational_vector(exact["displacement_m"], body + " displacement"))
                    and residual == [Fraction(v) - exact_v
                                     for v, exact_v in zip(saved_si[:3], position_m, strict=True)],
                    body + " zero rephasing and saved source residual")
            ref[body.lower() + "_state_si"] = position_m + velocity_m_s
            if body == "Moon":
                ref["saved_moon_m"] = saved_si[:3]
                ref["saved_moon_source_residual_m"] = residual

        ref["d0_m"] = _rational_vector(progress["bodies"]["Moon"]["exact_geometries_m"]["d0"], "d0_m")
        require(ref["d0_m"] == [ref["moon_state_si"][j] - (r0[j] + v0[j] * Fraction(elapsed_s) + q[j])
                                for j in range(3)], "archived exact Moon geometry at frozen motion")
        fields = progress["sources"]["Moon"]
        a0: dict[int, list[Decimal]] = {}
        a0_norm: dict[int, Decimal] = {}
        for precision in (80, 100):
            p = str(precision)
            field = fields["reference"][p]["d0"]
            require(type(field) is list and len(field) == 3, "saved reference d0 dimensions")
            same(field, fields["raw_reference"][p]["d0"], "saved reference field return")
            require(fields["gates"][p]["overall"]["passed"] is baseline, "retained Moon overall verdict")
            a0[precision] = [_decimal(v, "saved reference d0") for v in field]
            a0_norm[precision] = _decimal(fields["reference_norms_m_s2"][p]["d0"], "saved d0 norm")
            require(a0_norm[precision] > 0 and any(a0[precision]), "nonzero retained Moon field")
        refs.append({**ref, "a0": a0, "a0_norm": a0_norm})
    check()
    return refs


def load_inputs(root: Path, check: Callable[[], None]) -> dict[str, Any]:
    """Load the three frozen states and audited references, never replaying the archives."""
    metadata = parse_json(_read_bound(root / INPUT_PATH, INPUT_SHA256, check))
    archives = {}
    paths = {ARCHIVE_PREFIX + label + ".json.gz": label for label in ("study", "audit")}
    for name, expected in metadata["archival_sha256"].items():
        raw = _read_bound(root / name, expected, check)
        if name in paths:
            label = paths[name]
            unpacked = gzip.decompress(raw)
            require(sha256(unpacked).hexdigest() == metadata["retained_uncompressed_sha256"][label],
                    "uncompressed archive hash: " + label)
            check()
            archives[label] = parse_json(unpacked)
            check()
    study, audit = archives["study"], archives["audit"]
    references = _references(metadata, study, audit, check)
    return {**metadata, "historical_identity": study["identities"]["before"], "references": references}
