"""Bind scoped ADR0215/0217 saved records without evaluating a state or conic."""

from collections import Counter
from decimal import Decimal
import math
from types import ModuleType
from typing import Any

type Row = dict[str, Any]
type Records = dict[str, tuple[Row, str]]

SAVED_PINS = {
    "attempt.json": "ac1d02f445ebed82ac5b4f728193ea8533890188ed2422117523db50d087bf0a",
    "report.json": "323c2c71e17168a46e9dd5280015a3fecb0865016b9b6954dcb051de4def1800",
    "receipt.json": "395d20ab4771b9a9e4743e038e5c50338d12b8d890018befc3879bf3de21a18b",
}
UPSTREAM_PINS = {
    "attempt.json": "8df6fdaa9e1ecdb75d1e9def89d14da51dde6b34817065836d9b9bfda26570f5",
    "report.json": "421fb33a5ba76750e5524cd9734e2729f4e222b8a7838bd44fc8edfd86e29781",
    "receipt.json": "627396cd7ba4e4934fda33c8c62fa611c0b7918fed74c035f568e4a222ab4189",
    "completion.json": "bb0e6bf9eddcd77aebf698f2c8a55d339e2e84d91d6ce6df4166b3f2519d82b5",
}
REFERENCE_SHA256 = "6b845f74881f658d2eeea28bfdde43c9190a283da5bb166644bb845c4f847c5b"
BINDING_SHA256 = "e5f9e671aa4716e1a6b953569cfa86e5b06b90322b8faec480ec032b5bc1c9ab"
EPOCH_WORDS = ["0x1.d2d247f9d7e7ap+29", "0x1.d2d4a9afb54adp+29", "0x1.ded341cb4c44bp+29"]
WALL_NS = 30_000_000_000
MODEL = ("ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-"
         "cannonball-srp-schwarzschild-direct-spice-v2")
FLAGS = dict(spice_queries=0, kernel_accesses=0, force_evaluations=0, integrations=0, r560_attempts=0,
             live_authorized=False, physical_launch_authorized=False, physical_status="physical-join-not-established")
SPACECRAFT = dict(initial_mass_kg=2000., dry_mass_kg=500., max_thrust_n=1000.,
                  isp_s=450., srp_area_m2=20., reflectivity_coefficient=1.3)
SIGNS = ("positive", "negative")
REFUSAL = "no-eligible-pair-on-grid"
PAIR_FIELDS = ("index", "roots", "reason", "total_delta_v_m_s", "oracle_total_delta_v_m_s")


def _need(ok: object, reason: str) -> None:
    if not ok:
        raise ValueError(f"R5.59i saved archive: {reason}")


def _fields(row: Row, expected: Row) -> bool:
    return all(type(row.get(key)) is type(value) and row[key] == value for key, value in expected.items())


def _number(value: Any) -> float:
    _need(type(value) in (int, float) and math.isfinite(value), "nonfinite or nonnumeric field")
    return float(value)


def _digest_map(value: Row, io: ModuleType) -> None:
    _need(isinstance(value, dict) and value, "digest map")
    for digest in value.values():
        io._pin(digest)


def _reference(ref: Row, mode: str, candidate: str, io: ModuleType) -> None:
    _need(set(ref) == {"normalized", "lunar", "zero_branches", "zero_pairs"}, "reference inventory")
    src = ref["normalized"]
    _need(_fields(src, dict(
        schema="ariadna-r559c-normalized-input-v1", status="archive-inputs-validated", scope=mode,
        candidate_id=candidate, model_id=MODEL, origin="SSB", orientation="J2000", units="SI",
        time_scale="TDB seconds since J2000", command_words=None, live_authorized=False,
    )), "normalized input identity")
    craft = src["spacecraft"]
    _need(set(craft) == set(SPACECRAFT)
          and all(_number(craft[key]) == value for key, value in SPACECRAFT.items()),
          "frozen spacecraft")
    times = [_number(x) for x in src["epochs_tdb_s"]]
    _need(len(times) == 3 and times[0] < times[1] < times[2]
          and src["epoch_words"] == [t.hex() for t in times], "exact epoch words")
    moon, mars = src["endpoints"]
    for endpoint, body, label, epoch in ((moon, "Moon", "departure-ignition", times[0]),
                                         (mars, "Mars", "arrival-cutoff", times[2])):
        _need(_fields(endpoint, dict(body=body, label=label, epoch_word=epoch.hex()))
              and _number(endpoint["epoch_tdb_s"]) == epoch, "endpoint order or epoch")
        for key, count in (("body_ssb_si", 6), ("endpoint_ssb_si", 6), ("v_infinity_m_s", 3)):
            values = endpoint[key]
            _need(isinstance(values, list) and len(values) == count, "fixed state vector")
            tuple(map(_number, values))
        _need(all(_number(endpoint[key]) > 0 for key in ("gm_m3_s2", "shape_radius_m", "guard_m")),
              "fixed gravitational or radius constant")
    _need(ref["lunar"]["reason"] is None and set(ref["zero_branches"]) == set(SIGNS)
          and bool(ref["zero_pairs"])
          and all(pair["roots"][0] == "positive" and pair["reason"] == "commanded-dry-floor"
                  for pair in ref["zero_pairs"]), "fixed lunar root or zero phase refusal")
    if mode == "retained":
        _need(src["epoch_words"] == EPOCH_WORDS
              and io._sha(io._wire(ref)) == REFERENCE_SHA256, "frozen retained operands")


def _inventory(report: Row, audit: Row, retained: bool) -> list[Row]:
    rows, work = report["rows"], report["work"]
    _need(isinstance(rows, list) and len(rows) == 360
          and isinstance(work, dict) and set(work) == {"phase_positions", "mars_roots", "pairs"}
          and _fields(work, {"phase_positions": 360, "mars_roots": 720})
          and type(work["pairs"]) is int and 0 < work["pairs"] <= 720, "grid inventory")
    branches = {s: Counter() for s in SIGNS}
    pairs = []
    for index, row in enumerate(rows):
        _need(_fields(row, {"index": index}) and row["angle_word"] == (math.tau*index/360).hex()
              and set(row["branches"]) == set(SIGNS) and isinstance(row["pairs"], list),
              "ordered phase, angle or signed roots")
        expected = []
        for sign in SIGNS:
            reason = row["branches"][sign]["reason"]
            _need(reason in (None, "guard", "degenerate"), "unresolved saved root")
            branches[sign][reason or "passes"] += 1
            if reason is None:
                expected.append(["positive", sign])
        _need(expected == [pair["roots"] for pair in row["pairs"]]
              and all(_fields(pair, {"index": index, "reason": "commanded-dry-floor"})
                      and pair.get("command_words") is None for pair in row["pairs"]), "saved pair refusal")
        pairs.extend(row["pairs"])
    _need(len(pairs) == work["pairs"] and audit["branch_decisions"] == branches
          and audit["pair_decisions"] == {"commanded-dry-floor": len(pairs)},
          "audit branch or pair inventory")
    low = min(pairs, key=lambda p: _number(p["total_delta_v_m_s"]))
    independent = min(pairs, key=lambda p: _decimal(p["oracle_total_delta_v_m_s"]))
    for key, saved in (("least_recorded_pair", low), ("least_independent_pair", independent)):
        _need(audit[key] == {field: saved[field] for field in PAIR_FIELDS}, "audit least pair binding")
        if retained:
            _need(saved["index"] == 151 and saved["roots"] == ["positive", "positive"], "fixed 151 degree neighborhood")
    _need(_number(audit["zero_phase_delta_v_m_s"]) == _number(rows[0]["pairs"][0]["total_delta_v_m_s"]),
          "audit zero-phase cost")
    return rows[150:153]


def _decimal(value: Any) -> Decimal:
    _need(type(value) is str and 0 < len(value) <= 256, "independent pair cost")
    cost = Decimal(value)
    _need(cost.is_finite() and cost > 0 and abs(cost.adjusted()) <= 400, "independent pair cost")
    return cost


def _bind(records: Records, io: ModuleType, retained: bool) -> Row:
    _need(type(retained) is bool and set(records) == set(SAVED_PINS) | {"audit.json"}, "four-record inventory")
    records_pins = {name: records[name][1] for name in SAVED_PINS}
    _digest_map({name: pair[1] for name, pair in records.items()}, io)
    if retained:
        _need(records_pins == SAVED_PINS, "retained ADR0215 pins")
    else:
        _need(not set(records_pins.values()) & set(SAVED_PINS.values()), "artificial/retained pin overlap")

    attempt, report, receipt = (records[name][0] for name in SAVED_PINS)
    audit = records["audit.json"][0]
    mode = "retained" if retained else "artificial"
    candidate = "d0001-t0035" if retained else "artificial-moon-mars"
    run_id = attempt["run_id"]
    _need(type(run_id) is str and len(run_id) == 32
          and all(c in "0123456789abcdef" for c in run_id), "run identity")
    pins, methods = attempt["source_pins"], attempt["source_sha256"]
    _digest_map(pins, io)
    _digest_map(methods, io)
    _need(set(pins) == set(UPSTREAM_PINS), "upstream record inventory")
    if retained:
        _need(pins == UPSTREAM_PINS and methods["binding"] == BINDING_SHA256, "upstream and binding pins")
    else:
        _need(not set(pins.values()) & set(UPSTREAM_PINS.values()), "artificial upstream overlaps retained")
    identity = FLAGS | dict(schema="ariadna-r559f-phase-evidence-v1", stage="R5.59f", mode=mode,
                            synthetic=not retained, r559f_attempts=int(retained), source_pins=pins,
                            source_sha256=methods, run_id=run_id)
    _need(all(_fields(row, identity) for row in (attempt, report, receipt)), "source lineage, mode or authority")
    _need(records_pins["attempt.json"] == report["attempt_sha256"] == receipt["attempt_sha256"]
          and receipt["report_sha256"] == records_pins["report.json"]
          and _fields(report, dict(status=REFUSAL, reason="no-eligible-pair", command_words=None, selected=None))
          and receipt["status"] == REFUSAL, "attempt/report/receipt or refusal binding")
    before, wall = receipt["elapsed_before_receipt_ns"], attempt["wall_ns"]
    _need(type(before) is int and type(wall) is int and 0 <= before < wall <= WALL_NS, "original receipt deadline")
    size = report["source_bytes"]
    _need(type(size) is int and 0 < size <= 128*1024 and report["archive_open_attempts"] == list(UPSTREAM_PINS)
          and (not retained or size == 13_363), "historical archive read inventory")

    ref = report["reference"]
    _reference(ref, mode, candidate, io)
    audit_identity = FLAGS | dict(
        schema="ariadna-r559f-saved-grid-audit-v1", saved_grid_verified=True,
        original_invocation_completed=False, original_new_completion_witness=False,
        source_pins=records_pins, evidence_bytes=sum(len(io._wire(row)) for row in (attempt, report, receipt)),
        archive_reopens=0, new_r559f_attempts=0, new_phase_scans=0, new_conic_solves=0, wall_ns=WALL_NS,
        original_elapsed_before_receipt_ns=before, candidate_id=candidate, work=report["work"],
        source_bytes=size, source_sha256=methods, status=REFUSAL, reason="no-eligible-pair",
        commands=None, state_checks=360, adapter_uses=int(retained),
    )
    elapsed = audit["elapsed_ns"]
    _need(_fields(audit, audit_identity) and type(elapsed) is int and 0 <= elapsed < WALL_NS,
          "saved audit identity, provenance or deadline")
    if retained:
        _need(audit["zero_encoding"] == dict(phase_index=0, velocity_component_index=0,
                                             original="0E-569", audit_view="0"),
              "retained exact-zero audit identity")
    return {"scope": mode, "reference": ref, "anchors": _inventory(report, audit, retained)}


def bind(records: Records, io: ModuleType, *, retained: bool) -> Row:
    """Validate pinned, already decoded evidence; expose only frozen inputs and three saved anchors."""
    try:
        return _bind(records, io, retained)
    except (ArithmeticError, AttributeError, IndexError, KeyError, TypeError) as exc:
        raise ValueError(f"R5.59i saved archive: malformed record ({type(exc).__name__})") from exc
