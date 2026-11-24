"""Fabricate dense saved-archive shapes without opening historical operands."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from bounded_witness_fixtures import artificial_records, load_methods, wire

type Row = dict[str, Any]
FIXED_INPUT_BYTES = 1_065_958


def _refresh(records: dict[str, Row]) -> dict[str, bytes]:
    attempt, report, receipt, audit = (records[name] for name in (
        "attempt.json", "report.json", "receipt.json", "audit.json"))
    attempt_raw = wire(attempt)
    attempt_pin = sha256(attempt_raw).hexdigest()
    report["attempt_sha256"] = receipt["attempt_sha256"] = attempt_pin
    report_raw = wire(report)
    receipt["report_sha256"] = sha256(report_raw).hexdigest()
    receipt_raw = wire(receipt)
    raw = dict(zip(("attempt.json", "report.json", "receipt.json"),
                   (attempt_raw, report_raw, receipt_raw), strict=True))
    audit["source_pins"] = {name: sha256(value).hexdigest() for name, value in raw.items()}
    audit["evidence_bytes"] = sum(map(len, raw.values()))
    raw["audit.json"] = (json.dumps(audit, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    return raw


def source_archive(root: Path, case: str, *, full_size: bool = False) -> tuple[Path, dict[str, str]]:
    """Compute only three fabricated anchors; dense other rows are labelled metadata."""
    methods = load_methods()
    records = artificial_records(methods, case)
    report, audit = records["report.json"], records["audit.json"]
    if full_size:
        for row in report["rows"]:
            if not row.get("fabricated_inventory_only"):
                continue
            row["branches"]["negative"]["reason"] = None
            second = deepcopy(row["pairs"][0])
            second["roots"] = ["positive", "negative"]
            row["pairs"].append(second)
        pairs = [pair for row in report["rows"] for pair in row["pairs"]]
        report["work"]["pairs"] = len(pairs)
        audit["work"] = report["work"]
        audit["branch_decisions"] = {
            sign: dict(Counter(row["branches"][sign]["reason"] or "passes" for row in report["rows"]))
            for sign in ("positive", "negative")}
        audit["pair_decisions"] = {"commanded-dry-floor": len(pairs)}
        least = min(pairs, key=lambda pair: pair["total_delta_v_m_s"])
        audit["least_recorded_pair"] = audit["least_independent_pair"] = {
            field: least[field] for field in methods["archive"].PAIR_FIELDS}
        report["fabricated_volume_padding"] = ""
        for _ in range(8):
            raw = _refresh(records)
            missing = FIXED_INPUT_BYTES - sum(map(len, raw.values()))
            if missing <= 0:
                break
            report["fabricated_volume_padding"] += "x" * missing
        else:
            raise AssertionError("fabricated full-volume fixed point did not settle")
    raw = _refresh(records)
    root.mkdir()
    for name, value in raw.items():
        (root / name).write_bytes(value)
    pins = {name: sha256(value).hexdigest() for name, value in raw.items()}
    methods["archive"].bind({name: (records[name], pins[name]) for name in records},
                            methods["io"], retained=False)
    if full_size:
        assert sum(map(len, raw.values())) >= FIXED_INPUT_BYTES
    return root, pins


def retained_metadata_gate() -> tuple[Row, Any, Any]:
    """Reach unchanged retained metadata gates in memory; no authentic input claim.

    The fake digest supplies a deliberately fabricated reference identity only in
    this isolated unit. The cold dispatcher never receives this IO substitute.
    """
    from types import SimpleNamespace

    methods = load_methods()
    archive, io = methods["archive"], methods["io"]
    records = artificial_records(methods, "refusal")
    attempt, report, receipt, audit = (records[name] for name in (
        "attempt.json", "report.json", "receipt.json", "audit.json"))
    normalized = report["reference"]["normalized"]
    epochs = [float.fromhex(word) for word in archive.EPOCH_WORDS]
    normalized.update(scope="retained", candidate_id="d0001-t0035",
                      epochs_tdb_s=epochs, epoch_words=list(archive.EPOCH_WORDS))
    for endpoint, epoch in zip(normalized["endpoints"], epochs[::2], strict=True):
        endpoint.update(epoch_tdb_s=epoch, epoch_word=epoch.hex())
    method_pins = dict(attempt["source_sha256"], binding=archive.BINDING_SHA256)
    for row in (attempt, report, receipt):
        row.update(mode="retained", synthetic=False, r559f_attempts=1,
                   source_pins=dict(archive.UPSTREAM_PINS), source_sha256=method_pins)
    report.update(source_bytes=13_363, archive_open_attempts=list(archive.UPSTREAM_PINS))
    for row in report["rows"]:
        for branch_index, pair in enumerate(row["pairs"]):
            cost = float(10_000 + abs(row["index"] - 151) + branch_index)
            pair.update(total_delta_v_m_s=cost, oracle_total_delta_v_m_s=str(cost))
    least = report["rows"][151]["pairs"][0]
    audit.update(source_pins=dict(archive.SAVED_PINS), source_bytes=13_363,
                 source_sha256=method_pins, candidate_id="d0001-t0035", adapter_uses=1,
                 least_recorded_pair={field: least[field] for field in archive.PAIR_FIELDS},
                 least_independent_pair={field: least[field] for field in archive.PAIR_FIELDS},
                 zero_phase_delta_v_m_s=report["rows"][0]["pairs"][0]["total_delta_v_m_s"],
                 zero_encoding=dict(phase_index=0, velocity_component_index=0,
                                    original="0E-569", audit_view="0"))
    report["attempt_sha256"] = receipt["attempt_sha256"] = archive.SAVED_PINS["attempt.json"]
    receipt["report_sha256"] = archive.SAVED_PINS["report.json"]
    audit["evidence_bytes"] = sum(len(wire(row)) for row in (attempt, report, receipt))
    reference_bytes = wire(report["reference"])
    fake_io = SimpleNamespace(_pin=io._pin, _wire=io._wire,
                              _sha=lambda raw: archive.REFERENCE_SHA256 if raw == reference_bytes else io._sha(raw))
    pins = dict(archive.SAVED_PINS, **{"audit.json": "f" * 64})
    return {name: (row, pins[name]) for name, row in records.items()}, fake_io, archive
