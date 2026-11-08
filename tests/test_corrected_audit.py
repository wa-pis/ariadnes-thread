"""Handmade analytic audit records; no retained real-input solve is executed."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0163-corrected-audit.py"
spec = importlib.util.spec_from_file_location("corrected_audit_tests", PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
audit = module


def correction(s: float) -> list[float]:
    return [s*s*0.001, s*s*0.002, -s*s*0.003, 2*s*0.001, 2*s*0.002, -2*s*0.003]


def row(s: float, bundle: dict[str, Any]) -> dict[str, Any]:
    t0 = bundle["initial"]["epoch_tdb_s"]
    from fractions import Fraction
    exact = Fraction(t0) + Fraction(s)
    hi = float(exact)
    lo = float(exact - Fraction(hi))
    y = correction(s)
    initial = bundle["initial"]
    drift = [v*s for v in initial["velocity_m_s"]]
    motion = {"elapsed_s": s, "q_m": y[:3], "w_m_s": y[3:], "drift_m": drift,
              "position_m": [math.fsum((r, d, q)) for r, d, q in zip(initial["position_m"], drift, y[:3], strict=True)],
              "velocity_m_s": [math.fsum((v, w)) for v, w in zip(initial["velocity_m_s"], y[3:], strict=True)]}
    bodies = {}
    geometry = {}
    for j, body in enumerate(audit.BODIES):
        raw = [float(2**40 + j*2**20)/1000, float(2**39)/1000, -float(2**38)/1000, 0.0, 0.0, 0.0]
        state = [v*1000 for v in raw]
        bodies[body] = {"body": body, "epoch_tdb_s": hi, "state_km_km_s": raw, "state_si": state}
        c = [v*lo for v in state[3:]]
        delta = [math.fsum((state[k], -initial["position_m"][k], -drift[k], -y[k], c[k])) for k in range(3)]
        rho = math.hypot(*delta)
        geometry[body] = {"rephasing_m": c, "separation_m": delta, "distance_m": rho}
        if j < 2:
            mu = bundle["gm_m3_s2"][body]
            geometry[body]["acceleration_m_s2"] = [mu*(d/rho)/(rho*rho) for d in delta]
    acceleration = [math.fsum(geometry[b]["acceleration_m_s2"][j] for b in audit.BODIES[:2]) for j in range(3)]
    return {"elapsed_s": s, "hi_tdb_s": hi, "lo_s": lo, "correction": y, "motion": motion,
            "bodies": bodies, "geometry": geometry, "derivative": y[3:]+acceleration}


class Reference:
    def assess_observation(self, initial: Any, motion: Any, rows: Any, geometry: Any,
                           gm: Any, radii: Any, consume: Any, check: Any, *, progress: Any = None) -> dict[str, Any]:
        for name, count in (("body_checks", 3), ("source_rows", 2), ("reference_fields", 16), ("model_totals", 1)):
            for _ in range(count):
                consume(name, "attempt")
                check()
                consume(name, "complete")
        return {"passed": True, "fixture": "injected-reference-only"}

    def compare_states(self, left: list[float], right: list[float], rp: float, rv: float) -> dict[str, Any]:
        p = math.dist(left[:3], right[:3])
        v = math.dist(left[3:], right[3:])
        return {"position_norm_m": p, "velocity_norm_m_s": v, "passed": p <= rp and v <= rv}


def fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    bundle: dict[str, Any] = {"initial": {"epoch_tdb_s": 2.0**30, "position_m": [1e8, -2e8, 3e8],
                                          "velocity_m_s": [1.0, -2.0, 3.0]},
                              "gm_m3_s2": {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8, "Earth": 398600435468295.9},
                              "radii_m": {"Sun": 696000000.0, "Moon": 1737400.0, "Earth": 6378136.6},
                              "source_rows_template": {b: {"body": b, "segments": [], "assessment": {"stale": True}} for b in audit.BODIES}}
    outputs = [row(s, bundle) for s in audit.OFFSETS]
    states = [r["motion"]["position_m"] + r["motion"]["velocity_m_s"] for r in outputs]
    bundle["native_samples"] = {name: deepcopy(states) for name in audit.PROFILES}
    report: dict[str, Any] = {"contract": "ADR0162", "status": "passed", "origin": "SSB", "orientation": "J2000",
                              "time_scale": "TDB", "budget_s": 60.0, "aberration_correction": "NONE", "position_units": "m",
                              "velocity_units": "m/s", "acceleration_units": "m/s^2", "native_propagations": 0,
                              "gm_acquisitions": 0, "optimizer_calls": 0, "historical_final_identity_complete": False,
                              "mission_accuracy_verified": False, "continuous_safety_verified": False, "scientific_verified": False, "inputs": deepcopy(bundle), "profiles": [],
                              "rhs": [], "trials": [], "node_table": [{k: deepcopy(r[k]) for k in ("elapsed_s", "hi_tdb_s", "lo_s", "bodies")} for r in outputs],
                              "identities": {"before": {"fixture": True}, "after": {"fixture": True}}, "observations": [],
                              "finalization_gate": "passed", "counts": {}, "ledger": [], "native_guards": [], "adapter_mode": "injected-test"}
    for name in audit.PROFILES:
        start = len(report["rhs"])
        step = audit.settings(name)["max_step"]
        initial_row = row(0.0, bundle)
        initial_row.update(profile=name, index=0, global_index=start, completed=True)
        report["rhs"].append(initial_row)
        old_t, old_y = 0.0, [0.0]*6
        for j in range(int(300/step)):
            end = (j+1)*step
            left = len(report["rhs"])
            for stage in range(12):
                # The first six trial callbacks expose sub-ulp absolute epochs.
                elapsed = (stage+1)*2.0**-26 if j == 0 and stage < 6 else end
                r = row(elapsed, bundle)
                r.update(profile=name, index=len(report["rhs"])-start, global_index=len(report["rhs"]), completed=True)
                report["rhs"].append(r)
            cfg = audit.settings(name)
            scale = [cfg["atol"][k] + max(abs(old_y[k]), abs(r["correction"][k])) * cfg["rtol"] for k in range(6)]
            report["trials"].append({"profile": name, "index": len(report["trials"]), "t_before_s": old_t,
                                      "t_new_s": end, "h_s": end-old_t, "rhs_start": left,
                                      "rhs_end": len(report["rhs"]), "accepted": True, "decision": "accepted",
                                      "error_norm": 0.5, "scale": scale})
            old_t, old_y = end, r["correction"]
        profile = {"name": name, "settings": cfg, "rhs_start": start,
                   "raw_returned": {"success": True, "status": 0, "message": "fixture", "t": list(audit.OFFSETS),
                                    "y": [[r["correction"][k] for r in outputs] for k in range(6)], "nfev": len(report["rhs"])-start},
                   "outputs": deepcopy(outputs)}
        report["profiles"].append(profile)
        for kind in ("output", "rhs"):
            for i in range(7):
                report["observations"].append({"profile": name, "kind": kind, "index": i,
                                               "assessment": {"passed": True, "fixture": "injected-reference-only"}})
        for i in range(7):
            for body in audit.BODIES:
                distance = math.dist(states[i][:3], outputs[i]["bodies"][body]["state_si"][:3])
                report["native_guards"].append({"profile": name, "index": i, "body": body, "distance_m": distance, "passed": True})
    report["native_guards"].sort(key=lambda r: (r["index"], audit.PROFILES.index(r["profile"]), audit.BODIES.index(r["body"])))
    report["comparisons"] = audit.expected_comparisons(report, bundle, Reference())
    n = len(report["rhs"])
    counts = {"rhs": n, "states": 3*n+21, "trials": len(report["trials"]), "binary64_fields": 2*(n+14),
              "dynamic_totals": n+14, "body_checks": 84, "source_rows": 56, "reference_fields": 448,
              "model_totals": 28, "native_guards": 42, "solves": 2, "initializations": 1, "identities": 2, "metadata": 30}
    for name, count in counts.items():
        opaque = name in ("states", "solves", "identities", "metadata", "initializations")
        report["counts"][name] = {"attempted": count, "returned": count if opaque else 0, "completed": count}
        for _ in range(count):
            report["ledger"].append({"operation": name, "phase": "attempt"})
            if opaque:
                report["ledger"].append({"operation": name, "phase": "return"})
            report["ledger"].append({"operation": name, "phase": "complete"})
    return report, bundle


@pytest.fixture(scope="module")
def complete() -> tuple[dict[str, Any], dict[str, Any]]:
    return fixture()


def test_complete_independent_binary_replay(complete: Any) -> None:
    report, bundle = complete
    budget = audit.Budget(lambda: 0.0, 0.0)
    answer = audit.check_saved(report, bundle, Reference(), budget.check, budget.event)
    assert answer["passed"] and answer["observations"] == 28 and answer["comparisons"] == 21
    assert budget.counts["binary64_fields"]["completed"] == 2*(len(report["rhs"])+14)
    assert budget.counts["reference_fields"]["completed"] == 448
    assert answer["continuous_safety_verified"] is False


@pytest.mark.parametrize("mutation", ["time", "lo", "q", "drift", "position", "velocity", "source", "units", "sign", "field", "derivative", "earth_force", "body_order", "index", "global_index", "profile", "settings", "raw_y", "raw_nfev", "grid", "trial_norm", "trial_scale", "trial_h", "trial_range", "trial_accept", "guard", "count", "ledger", "selection", "reference", "identity", "finalization", "input"])
def test_corrupt_full_record_is_rejected(complete: Any, mutation: str) -> None:
    report, bundle = deepcopy(complete)
    r = report["rhs"][3]
    if mutation == "time":
        r["elapsed_s"] += 1e-3
    elif mutation == "lo":
        r["lo_s"] = -r["lo_s"]
    elif mutation == "q":
        r["correction"][0] += 1
    elif mutation == "drift":
        r["motion"]["drift_m"][0] += 1
    elif mutation == "position":
        r["motion"]["position_m"][0] += 1
    elif mutation == "velocity":
        r["motion"]["velocity_m_s"][0] += 1
    elif mutation == "source":
        r["bodies"]["Moon"]["body"] = "Earth"
    elif mutation == "units":
        r["bodies"]["Sun"]["state_si"][0] /= 1000
    elif mutation == "sign":
        r["geometry"]["Moon"]["separation_m"][0] *= -1
    elif mutation == "field":
        r["geometry"]["Moon"]["acceleration_m_s2"][0] *= -1
    elif mutation == "derivative":
        r["derivative"][0] += 1
    elif mutation == "earth_force":
        r["geometry"]["Earth"]["acceleration_m_s2"] = [0.0]*3
    elif mutation == "body_order":
        r["bodies"] = dict(reversed(list(r["bodies"].items())))
    elif mutation == "index":
        r["index"] += 1
    elif mutation == "global_index":
        r["global_index"] += 1
    elif mutation == "profile":
        r["profile"] = "B"
    elif mutation == "settings":
        report["profiles"][0]["settings"]["rtol"] *= 10
    elif mutation == "raw_y":
        report["profiles"][0]["raw_returned"]["y"][0][1] += 1
    elif mutation == "raw_nfev":
        report["profiles"][0]["raw_returned"]["nfev"] += 1
    elif mutation == "grid":
        report["profiles"][0]["raw_returned"]["t"][1] += 1
    elif mutation == "trial_norm":
        report["trials"][0]["error_norm"] = float("nan")
    elif mutation == "trial_scale":
        report["trials"][0]["scale"][0] *= 2
    elif mutation == "trial_h":
        report["trials"][0]["h_s"] *= 2
    elif mutation == "trial_range":
        report["trials"][0]["rhs_end"] += 1
    elif mutation == "trial_accept":
        report["trials"][0]["accepted"] = False
    elif mutation == "guard":
        report["native_guards"][0]["distance_m"] *= 2
    elif mutation == "count":
        report["counts"]["states"]["attempted"] += 1
    elif mutation == "ledger":
        report["ledger"][0]["phase"] = "complete"
    elif mutation == "selection":
        report["observations"][0]["kind"] = "rhs"
    elif mutation == "reference":
        report["observations"][0]["assessment"]["passed"] = False
    elif mutation == "identity":
        report["identities"]["after"] = {"changed": True}
    elif mutation == "finalization":
        report["finalization_gate"] = "failed"
    elif mutation == "input":
        report["inputs"]["initial"]["position_m"][0] += 1
    with pytest.raises((ValueError, KeyError)):
        audit.check_saved(report, bundle, Reference())


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]'])
def test_strict_json(raw: bytes) -> None:
    with pytest.raises(ValueError):
        audit.parse(raw)


@pytest.mark.parametrize("value", [True, "1", float("nan"), float("inf"), None])
def test_numeric_boundary(value: Any, complete: Any) -> None:
    report, bundle = deepcopy(complete)
    report["rhs"][0]["correction"][0] = value
    with pytest.raises(ValueError):
        audit.check_saved(report, bundle, Reference())


def test_reference_rows_drop_stale_assessment(complete: Any) -> None:
    report, bundle = complete
    rows = audit.source_rows(report["rhs"][0], bundle)
    assert all("assessment" not in r for r in rows.values())


def test_budget_attempt_cap_and_late_completion() -> None:
    budget = audit.Budget(lambda: 0.0, 0.0)
    budget.counts["binary64_fields"]["attempted"] = 20028
    with pytest.raises(ValueError, match="cap"):
        budget.event("binary64_fields", "attempt")
    clock = iter([0.0, 0.0, 11.0])
    budget = audit.Budget(lambda: next(clock), 0.0)
    budget.event("rhs", "attempt")
    with pytest.raises(ValueError, match="deadline"):
        budget.event("rhs", "complete")
    assert budget.counts["rhs"] == {"attempted": 1, "completed": 1}


def test_opaque_counter_order(complete: Any) -> None:
    report, _ = deepcopy(complete)
    report["counts"]["states"]["returned"] = 0
    with pytest.raises(ValueError):
        audit.validate_counts(report)


def test_partial_prefix_never_becomes_scientific_success(complete: Any) -> None:
    report, bundle = deepcopy(complete)
    report["status"] = "failed"
    report["error"] = {"stage": "finalization", "message": "fixture"}
    report["identities"]["after"] = {"unavailable": True}
    answer = audit.check_saved(report, bundle, Reference())
    assert answer["passed"] is False


def test_exclusive_output_and_injected_verification(tmp_path: Path, complete: Any) -> None:
    report, bundle = complete
    source = tmp_path/"input.json"
    output = tmp_path/"audit.json"
    source.write_text(json.dumps(report))
    answer = audit.audit(source, output, clock=lambda: 0.0, started_s=0.0,
                         inputs_loader=lambda *a: bundle, references=Reference())
    assert answer["audit_status"] == "passed"
    assert answer["scientific_verified"] is False
    assert output.with_suffix(".receipt.json").exists()
    with pytest.raises((FileExistsError, ValueError)):
        audit.audit(source, output, inputs_loader=lambda *a: bundle, references=Reference())


def test_late_flush_downgrades() -> None:
    result = {"audit_status": "passed", "scientific_verified": True}
    budget = audit.Budget(lambda: 11.0, 0.0)
    stream = io.StringIO()
    answer = audit.save(result, stream, budget)
    assert answer["finalization_gate"] == "failed"
    assert answer["audit_status"] == "rejected" and not answer["scientific_verified"]


def test_candidate_and_scientific_modules_not_imported() -> None:
    text = PATH.read_text()
    assert "prescribed_corrections" not in text
    assert not any(name.startswith("corrected_audit_0163_corrected_integrator") for name in sys.modules)


@pytest.mark.parametrize("field,value", [("aberration_correction", "LT"), ("position_units", "km"),
    ("native_propagations", 1), ("gm_acquisitions", True), ("mission_accuracy_verified", True),
    ("continuous_safety_verified", True), ("historical_final_identity_complete", True), ("scientific_verified", True)])
def test_scientific_boundary_claims_rejected(complete: Any, field: str, value: Any) -> None:
    report, bundle = deepcopy(complete)
    report[field] = value
    with pytest.raises(ValueError):
        audit.check_saved(report, bundle, Reference())


def test_fresh_import_never_loads_candidate_or_scientific_modules() -> None:
    import subprocess
    program = "import importlib.util,sys; p=" + repr(str(PATH)) + "; s=importlib.util.spec_from_file_location('isolated_audit',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.fresh(); assert not any('0163_corrected_integrator' in n for n in sys.modules)"
    subprocess.run([sys.executable, "-I", "-S", "-B", "-c", program], check=True, timeout=5)


def test_partial_comparison_prefix_is_retained(complete: Any) -> None:
    report, bundle = deepcopy(complete)
    report["status"] = "failed"
    report["error"] = {"stage": "trajectory-comparisons", "message": "fixture"}
    report["comparisons"] = report["comparisons"][:8]
    report["observations"] = []
    result = audit.check_saved(report, bundle, Reference())
    assert result["passed"] is False


def test_unavailable_trial_may_have_no_completed_callback() -> None:
    report = {"status": "failed", "rhs": [], "trials": [{"index": 0, "profile": "normal",
        "rhs_start": 0, "rhs_end": 0, "t_before_s": 0.0, "t_new_s": None, "h_s": None,
        "accepted": None, "decision": "unavailable"}]}
    audit.check_trials(report, lambda: None, lambda *a: None)


def test_default_entry_requires_external_baseline(tmp_path: Path) -> None:
    source, output = tmp_path/"missing.json", tmp_path/"not-created.json"
    with pytest.raises(ValueError, match="external pre-child baseline"):
        audit.audit(source, output)
    assert not output.exists()


@pytest.mark.parametrize("count", [0, 3, 6])
def test_successful_raw_arrays_allow_failed_export_prefix(complete: Any, count: int) -> None:
    report, bundle = deepcopy(complete)
    report.update(status="failed", error={"stage": "solve-normal", "message": "late raw return"})
    report["profiles"] = report["profiles"][:1]
    report["profiles"][0]["outputs"] = report["profiles"][0]["outputs"][:count]
    report["rhs"] = [r for r in report["rhs"] if r["profile"] == "normal"]
    report["trials"] = [r for r in report["trials"] if r["profile"] == "normal"]
    report["comparisons"] = report["comparisons"][:7]
    report["observations"] = []
    report["counts"]["states"]["attempted"] = 3*len(report["rhs"])+21
    report["counts"]["states"]["returned"] = report["counts"]["states"]["attempted"]
    report["counts"]["states"]["completed"] = report["counts"]["states"]["attempted"]
    report["ledger"] = []
    for name, c in report["counts"].items():
        for i in range(c["attempted"]):
            report["ledger"].append({"operation": name, "phase": "attempt"})
            if i < c["returned"]:
                report["ledger"].append({"operation": name, "phase": "return"})
            if i < c["completed"]:
                report["ledger"].append({"operation": name, "phase": "complete"})
    result = audit.check_saved(report, bundle, Reference())
    assert result["passed"] is False


def test_partial_node_body_prefix(complete: Any) -> None:
    report, bundle = complete
    node = deepcopy(report["node_table"][0])
    node["bodies"] = {"Sun": node["bodies"]["Sun"]}
    node["bodies"]["Sun"].pop("state_si")
    audit.validate_partial_sources(node, bundle)
    node["bodies"]["Sun"]["epoch_tdb_s"] += 1
    with pytest.raises(ValueError):
        audit.validate_partial_sources(node, bundle)


def test_partial_force_prefix_rebuilt_and_counted(complete: Any) -> None:
    report, bundle = complete
    row = deepcopy(report["rhs"][0])
    row.pop("derivative")
    row["geometry"]["Moon"].pop("acceleration_m_s2")
    budget = audit.Budget(lambda: 0.0, 0.0)
    audit.validate_partial_row(row, bundle, budget.check, budget.event)
    assert budget.counts["binary64_fields"]["completed"] == 1
    row["geometry"]["Sun"]["acceleration_m_s2"][0] *= -1
    with pytest.raises(ValueError):
        audit.validate_partial_row(row, bundle)


@pytest.mark.parametrize("field", ["hi_tdb_s", "lo_s"])
def test_complete_node_epoch_metadata_is_independently_checked(complete: Any, field: str) -> None:
    report, bundle = deepcopy(complete)
    report["node_table"][3][field] += 1.
    with pytest.raises(ValueError, match="epoch"):
        audit.check_saved(report, bundle, Reference())
