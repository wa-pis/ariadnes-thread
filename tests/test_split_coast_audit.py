"""Synthetic audit mutations: no native queries or trajectory runs."""
from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0180-split-audit.py"
spec = importlib.util.spec_from_file_location("split_coast_audit_tests", PATH)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
type Row = dict[str, Any]


def row_fixture() -> tuple[Row, Row]:
    # The input epoch rounds up, so the velocity rephasing must be signed.
    start = 2.**30
    s = 2.**-22 - 2.**-27
    hi, lo = start+2.**-22, -2.**-27
    # The low limb would vanish if the Earth and Moon were summed in km first.
    earth_x = 2.**28
    x0 = 1000*earth_x
    r0 = [x0, 0., 0.]
    moon_x = 10000. + 2.**-25
    q, w = [0., 4., 0.], [0., 2., 0.]
    bundle: Row = {"initial": {"epoch_tdb_s": start, "position_m": r0, "velocity_m_s": [0.]*3},
                   "radii_m": {"Sun": 696000000., "Moon": 1737400., "Earth": 6378136.6},
                   "gm_m3_s2": {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8}}
    raw = {"Sun": [-earth_x, 0., 0., 0., 0., 0.],
           "Moon": [earth_x+10000., 10000., 0., 1., 0., -0.],
           "Earth": [earth_x, 10000., 0., 0., 0., 0.]}
    bodies = {body: {**audit.request(body, "SSB", hi), "state_km_km_s": words,
                     "state_si": [word*1000 for word in words]} for body, words in raw.items()}
    moon_earth = {**audit.request("Moon", "Earth", hi),
                  "state_km_km_s": [moon_x, 0., 0., -5000., 5., 7.]}
    exact = [10_000_000 + Fraction(1000, 2**25) - Fraction(1000, 2**27), Fraction(9_999_996), Fraction(0)]
    d = {"Sun": [-2*x0, -4., 0.], "Moon": list(map(float, exact)), "Earth": [0., 9_999_996., 0.]}
    geometry: Row = {}
    for body, displacement in d.items():
        rho = math.hypot(*displacement)
        c = [word*lo for word in bodies[body]["state_si"][3:]]
        geometry[body] = {"rephasing_m": c, "separation_m": displacement, "distance_m": rho}
        if body == "Moon":
            geometry[body]["pre_round_separation_m"] = list(map(str, exact))
        if body in bundle["gm_m3_s2"]:
            mu = bundle["gm_m3_s2"][body]
            geometry[body]["acceleration_m_s2"] = [mu*(v/rho)/(rho*rho) for v in displacement]
    return {"elapsed_s": s, "hi_tdb_s": hi, "lo_s": lo, "correction": q+w,
            "motion": {"elapsed_s": s, "q_m": q, "w_m_s": w, "drift_m": [0.]*3,
                       "position_m": [x0, 4., 0.], "velocity_m_s": w},
            "bodies": bodies, "moon_earth": moon_earth, "geometry": geometry,
            "derivative": w + [math.fsum(geometry[b]["acceleration_m_s2"][j] for b in ("Sun", "Moon"))
                               for j in range(3)]}, bundle


def test_signed_split_and_partial_field_replay() -> None:
    row, bundle = row_fixture()
    budget = audit.Budget(lambda: 0., 0.)
    rebuilt = audit.reconstruct_row(row, bundle, event=budget.event)
    assert rebuilt["geometry"]["Moon"]["separation_m"][0] > 10_000_000.
    assert row["lo_s"] < 0 and rebuilt["geometry"]["Moon"]["rephasing_m"][0] < 0
    assert budget.counts["dynamic_totals"]["completed"] == 1
    del row["derivative"]
    del row["geometry"]["Moon"]["acceleration_m_s2"]
    replay = audit.reconstruct_row(row, bundle, complete=False, event=budget.event)
    assert replay["geometry"]["Moon"]["separation_m"] == rebuilt["geometry"]["Moon"]["separation_m"]
    assert budget.counts["binary64_fields"]["completed"] == 3


@pytest.mark.parametrize(
    ("mutate", "diagnostic"), [
        (lambda row: row["moon_earth"].update(observer="SSB"), "source provenance"),
        (lambda row: row["moon_earth"].update(frame="ECLIPJ2000"), "source provenance"),
        (lambda row: row["moon_earth"].update(epoch_tdb_s=row["hi_tdb_s"]-1.), "source provenance"),
        (lambda row: row["bodies"]["Earth"]["state_si"].__setitem__(0, 2.**28), "SI conversion"),
        (lambda row: row["geometry"]["Moon"]["pre_round_separation_m"].__setitem__(0, "10000000"), "Moon geometry"),
        (lambda row: row["geometry"]["Moon"]["rephasing_m"].__setitem__(0, -5e6*row["lo_s"]), "Moon geometry"),
        (lambda row: row["geometry"]["Moon"]["separation_m"].__setitem__(2, -0.), "Moon geometry"),
        (lambda row: row.pop("moon_earth"), "missing Moon/Earth"),
    ],
)
def test_mutated_source_geometry_rejected(mutate: Callable[[Row], Any], diagnostic: str) -> None:
    row, bundle = row_fixture()
    mutate(row)
    with pytest.raises(ValueError, match=diagnostic):
        audit.reconstruct_row(row, bundle)


def test_partial_geocentric_return_requires_order_and_attempt_provenance() -> None:
    row, bundle = row_fixture()
    node = {key: row[key] for key in ("elapsed_s", "hi_tdb_s", "lo_s", "bodies", "moon_earth")}
    # Simulate a returned but malformed fourth value at the shared t0 node.
    node.update(elapsed_s=0., hi_tdb_s=bundle["initial"]["epoch_tdb_s"], lo_s=0.)
    for source in [*node["bodies"].values(), node["moon_earth"]]:
        source["epoch_tdb_s"] = node["hi_tdb_s"]
    node["moon_earth"]["state_km_km_s"] = [{"invalid_numeric": "nan"}]
    order = [audit.request(body, "SSB", node["hi_tdb_s"]) for body in audit.BODIES]
    order.append(audit.request("Moon", "Earth", node["hi_tdb_s"]))
    report = {"node_table": [node], "rhs": [], "state_requests": order, "status": "failed",
              "counts": {"states": {"attempted": 4, "returned": 4, "completed": 3}}}
    audit.check_request_sequence(report, bundle, lambda: None)
    report["state_requests"][2:] = reversed(report["state_requests"][2:])
    with pytest.raises(ValueError, match="ordered state"):
        audit.check_request_sequence(report, bundle, lambda: None)


def receipt_fixture(tmp_path: Path, *, status: str = "passed") -> tuple[Path, Row, bytes]:
    study = tmp_path/"study.json"
    report = {"status": status, "preparation_manifest_sha256": "a"*64,
              "finalization_gate": "passed", "elapsed_before_flush_s": 0.1,
              "identities": {"before": {"revision": "b"*40}}}

    def save(path: Path, payload: Row) -> str:
        raw = json.dumps(payload, allow_nan=False).encode()
        path.write_bytes(raw)
        return sha256(raw).hexdigest()

    evidence = save(study, report)
    attempt = save(study.with_suffix(".attempt.json"), {
        "contract": audit.CONTRACT, "adapter_mode": "reference", "started_s": 123.
    })
    child = save(study.with_suffix(".receipt.json"), {
        "status": status, "finalization_gate": "passed", "evidence_sha256": evidence,
        "started_s": 123., "elapsed_s": 0.2
    })
    parent_attempt = save(study.with_suffix(".parent-attempt.json"), {
        "contract": audit.CONTRACT, "phase": "study", "revision": "b"*40, "preparation_sha256": "a"*64
    })
    save(study.with_suffix(".parent-receipt.json"), {
        "contract": audit.CONTRACT, "phase": "study", "revision": "b"*40, "preparation_sha256": "a"*64,
        "evidence_sha256": evidence, "attempt_sha256": attempt, "child_receipt_sha256": child,
        "parent_attempt_sha256": parent_attempt, "started_s": 123., "elapsed_s": 0.3,
        "checkout_frozen": True, "returncode": 0 if status == "passed" else 2, "finalization_gate": "passed"
    })
    return study, report, study.read_bytes()


@pytest.mark.parametrize("status", ["passed", "failed"])
def test_study_receipts_preserve_negative_outcome(tmp_path: Path, status: str) -> None:
    study, report, raw = receipt_fixture(tmp_path, status=status)
    assert len(audit.check_study_receipts(study, report, raw, lambda: None)) == 4
    receipt = study.with_suffix(".receipt.json")
    receipt.write_bytes(receipt.read_bytes()+b" ")
    with pytest.raises(ValueError, match="child_receipt_sha256"):
        audit.check_study_receipts(study, report, raw, lambda: None)


@pytest.mark.parametrize(("key", "value"), [
    ("elapsed_s", 60.00001), ("started_s", 123.00001), ("checkout_frozen", False),
    ("returncode", 2), ("finalization_gate", "failed"), ("evidence_sha256", "0"*64)
])
def test_finalized_pass_cannot_hide_parent_failure(tmp_path: Path, key: str, value: Any) -> None:
    study, report, raw = receipt_fixture(tmp_path)
    path = study.with_suffix(".parent-receipt.json")
    payload = json.loads(path.read_bytes())
    payload[key] = value
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="study"):
        audit.check_study_receipts(study, report, raw, lambda: None)


def test_record_evaluation_budget_counts_attempt_before_work() -> None:
    budget = audit.Budget(lambda: 0., 0.)
    for _ in range(168):
        budget.event("record_evaluations", "attempt")
        budget.event("record_evaluations", "complete")
    with pytest.raises(ValueError, match="record_evaluations"):
        budget.event("record_evaluations", "attempt")
    assert budget.counts["record_evaluations"] == {"attempted": 168, "completed": 168}
