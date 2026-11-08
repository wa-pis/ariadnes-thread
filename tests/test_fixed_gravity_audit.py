"""Hand-built analytic saved-data fixtures; never execute the retained study."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0157-fixed-gravity-audit.py"
spec = importlib.util.spec_from_file_location("fixed_gravity_audit_tests", PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
audit = module
GM = {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8,
      "Earth": 398600435468295.9}
DISTANCES = {"Sun": float(2**40), "Earth": float(2**41), "Moon": float(3 * 2**40)}
ARMS = ("compensated", "uncorrected", "wrong_sign")
MODELS = {"A": ("Sun", "Moon"), "B": ("Sun", "Moon", "Earth")}


class References:
    """Injected arithmetic boundary with explicit calls and signed fixture values."""
    def __init__(self, source_failure: int | None = None,
                 model_failure: str | None = None) -> None:
        self.source_failure = source_failure
        self.model_failure = model_failure
        self.source_calls = 0

    def assess_source(self, row: dict[str, Any], _position: Any, _gm: Any,
                      _radius: Any, _arms: Any, consume: Any, *,
                      progress: dict[str, Any] | None = None) -> dict[str, Any]:
        self.source_calls += 1
        result = source_assessment(row, self.source_failure != row["fixture_index"])
        if progress is not None:
            progress["reference"] = {"80": {}, "100": {}}
        for profile in ("80", "100"):
            for geometry in ("d0", "d1", "d2", "d3"):
                consume("attempt")
                if progress is not None:
                    progress["reference"][profile][geometry] = result["reference"][profile][geometry]
                consume("complete")
        return result

    def assess_totals(self, _sources: Any, _arms: Any, *, consume_model: Any,
                      progress: dict[str, Any] | None = None) -> dict[str, Any]:
        result = {} if progress is None else progress
        for model in MODELS:
            consume_model("attempt")
            result[model] = model_assessment(model, self.model_failure != model)
            consume_model("complete")
            if not result[model]["passed"]:
                break
        return result


def source_assessment(row: dict[str, Any], passed: bool = True) -> dict[str, Any]:
    return {"body": row["body"], "reference": {profile: {geometry: ["1", "0", "0"]
        for geometry in ("d0", "d1", "d2", "d3")} for profile in ("80", "100")},
        "contributions_m_s2": {
        "native_source": ["-1e-20", "0", "0"],
        "residual_rephasing": ["2e-20", "0", "0"],
        "relative_assembly": ["-3e-20", "0", "0"],
        "field_evaluation": ["1e-20", "0", "0"]},
        "gates": {"returned_geometry": True, "overall": passed}, "passed": passed}


def model_assessment(model: str, passed: bool = True) -> dict[str, Any]:
    return {"model": model, "source_order": list(MODELS[model]),
            "gates": {"returned_geometry": True, "overall": passed}, "passed": passed}


def raw_rows() -> list[dict[str, Any]]:
    return [{"body": body, "fixture_index": index,
             "elapsed_s": float(index // 3), "lo_s": 0.0,
             "state_si": [DISTANCES[body], 0.0, 0.0, 0.0, 0.0, 0.0]}
            for index, body in enumerate(("Sun", "Earth", "Moon") * 7)]


def analytic_arms(body: str) -> dict[str, Any]:
    # Exact collinear geometry gives the independent scalar mu/r^2 formula.
    distance = DISTANCES[body]
    force = GM[body] / (distance * distance)
    return {arm: {"separation_m": [distance, 0.0, 0.0],
                  "acceleration_m_s2": [force, 0.0, 0.0],
                  "rephasing_m": [-0.0, -0.0, -0.0] if arm == "wrong_sign"
                                  else [0.0, 0.0, 0.0]} for arm in ARMS}


def bundle() -> dict[str, Any]:
    return {"position_m": [0.0, 0.0, 0.0], "initial": [0.0] * 6,
            "gm_m3_s2": dict(GM), "rows": raw_rows(),
            "input_sha256": {"synthetic": "analytic-fixture"},
            "source_provenance": {"fixture_only": True}, "identity": {"fixture_only": True}}


def event(ledger: list[dict[str, str]], operation: str) -> None:
    for phase in ("attempt", "complete"):
        ledger.append({"operation": operation, "phase": phase})


def recount(report: dict[str, Any]) -> None:
    report["counts"] = {name: {"attempted": 0, "completed": 0} for name in
                        ("source_rows", "reference_fields", "binary64_fields", "model_totals")}
    for entry in report["ledger"]:
        key = "attempted" if entry["phase"] == "attempt" else "completed"
        report["counts"][entry["operation"]][key] += 1


def saved_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    values = bundle()
    report: dict[str, Any] = {"contract": "ADR0156", "study": "fixed-position-real-gravity-v1",
        "status": "passed", "adapter_mode": "injected-test", "research_only": True,
        "mission_accuracy_verified": False, "continuous_safety_verified": False,
        "origin": "SSB", "orientation": "J2000", "time_scale": "TDB",
        "aberration_correction": "NONE", "acceleration_units": "m/s^2", "budget_s": 10.0,
        "native_calls": 0, "kernel_loads": 0, "gm_acquisitions": 0,
        "spacecraft_propagations": 0, "scientific_imports": 0, "reference_replayed": False,
        "inputs": {key: values[key] for key in ("position_m", "initial", "gm_m3_s2",
                   "input_sha256", "source_provenance", "identity")},
        "helper_sha256": {}, "rows": [], "totals": [], "ledger": [],
        "elapsed_before_flush_s": 0.01, "finalization_gate": "passed"}
    for index, raw in enumerate(values["rows"]):
        report["ledger"].append({"operation": "source_rows", "phase": "attempt"})
        arms = analytic_arms(raw["body"])
        for _ in range(3):
            event(report["ledger"], "binary64_fields")
        for _ in range(8):
            event(report["ledger"], "reference_fields")
        report["rows"].append({"index": index, "source_row": deepcopy(raw),
                               "arms": arms, "assessment": source_assessment(raw),
                               "reference_progress": {"reference": source_assessment(raw)["reference"]}})
        report["ledger"].append({"operation": "source_rows", "phase": "complete"})
        if index % 3 == 2:
            total_arms = {model: {arm: {"acceleration_m_s2": [math.fsum(
                GM[body] / DISTANCES[body] ** 2 for body in bodies), 0.0, 0.0]}
                for arm in ARMS} for model, bodies in MODELS.items()}
            report["totals"].append({"index": index // 3, "elapsed_s": float(index // 3),
                "arms": total_arms, "assessment": {model: model_assessment(model) for model in MODELS}})
            for _ in MODELS:
                event(report["ledger"], "model_totals")
    recount(report)
    report["identity_after"] = deepcopy(report["inputs"])
    return report, values


def failure(report: dict[str, Any], stage: str) -> None:
    report["status"] = "partial"
    report["error"] = {"stage": stage, "type": "ValueError", "message": "fixture failure"}
    report["first_error"] = dict(report["error"])


def run_saved(tmp_path: Path, report: dict[str, Any], values: dict[str, Any],
              references: Any = None) -> dict[str, Any]:
    path, output = tmp_path / "saved.json", tmp_path / "audit.json"
    path.write_text(json.dumps(report, allow_nan=False))
    result = audit.audit(path, output, clock=lambda: 0.0, start_s=0.0,
                         inputs_loader=lambda _root, _check: deepcopy(values),
                         references=references or References())
    assert json.loads(output.read_text()) == result
    return result


def test_import_has_no_candidate_or_scientific_imports() -> None:
    code = (f"import runpy,sys;runpy.run_path({str(PATH)!r});"
            "assert not any(k.startswith(('numpy','scipy','spiceypy','tudatpy','space_nav')) "
            "for k in sys.modules);assert not any('fixed_gravity_0157' in k for k in sys.modules)")
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
    assert "0157-fixed-gravity-study.py" not in PATH.read_text().split("def load_helper")[1].split("def reconstruct_arm")[0]


def test_complete_analytic_fixture_recomputes_all_caps_and_preserves_signs(tmp_path: Path) -> None:
    report, values = saved_fixture()
    result = run_saved(tmp_path, report, values)
    assert result["audit_status"] == "passed" and result["scientific_verified"] is False
    assert result["counts"] == report["counts"]
    assert result["counts"]["reference_fields"] == {"attempted": 168, "completed": 168}
    assert len(result["checks"]["source_rows"]) == 21
    assert len(result["checks"]["model_totals"]) == 7
    signed = result["checks"]["source_rows"][0]["assessment"]["contributions_m_s2"]
    assert signed["native_source"][0] == "-1e-20"
    assert signed["relative_assembly"][0] == "-3e-20"


@pytest.mark.parametrize("mutation", ["source", "rephasing", "field", "total", "reference", "gate", "bool", "count", "ledger", "identity"])
def test_saved_corruption_is_rejected(tmp_path: Path, mutation: str) -> None:
    report, values = saved_fixture()
    row = report["rows"][0]
    if mutation == "source":
        row["source_row"]["state_si"][0] += 1.0
    elif mutation == "rephasing":
        row["arms"]["wrong_sign"]["rephasing_m"][0] = 0.0
    elif mutation == "field":
        row["arms"]["compensated"]["acceleration_m_s2"][0] *= 1.00001
    elif mutation == "total":
        report["totals"][0]["arms"]["B"]["compensated"]["acceleration_m_s2"][0] *= 1.00001
    elif mutation == "reference":
        row["assessment"]["contributions_m_s2"]["native_source"][0] = "1e-20"
    elif mutation == "gate":
        row["assessment"]["gates"]["overall"] = False
    elif mutation == "bool":
        row["arms"]["compensated"]["acceleration_m_s2"][1] = False
    elif mutation == "identity":
        report["identity_after"]["identity"]["fixture_only"] = False
    elif mutation == "count":
        report["counts"]["native_calls"] = {"attempted": 0, "completed": 0}
    else:
        report["ledger"][1]["operation"] = "reference_fields"
    assert run_saved(tmp_path, report, values)["audit_status"] == "rejected"


def test_valid_required_source_failure_is_partial(tmp_path: Path) -> None:
    report, values = saved_fixture()
    report["rows"] = report["rows"][:1]
    report["rows"][0]["assessment"] = source_assessment(values["rows"][0], False)
    report["totals"] = []
    report["ledger"] = report["ledger"][:24]
    recount(report)
    failure(report, "source:0")
    result = run_saved(tmp_path, report, values, References(source_failure=0))
    assert result["audit_status"] == "partial" and not result["scientific_verified"]
    assert result["checks"]["first_required_gate_failure"] == "source:0"


@pytest.mark.parametrize("arms,reference_events", [(0, 0), (2, 0), (3, 5)])
def test_valid_incomplete_final_source_prefix_is_partial(tmp_path: Path, arms: int,
                                                       reference_events: int) -> None:
    report, values = saved_fixture()
    report["rows"] = report["rows"][:1]
    row = report["rows"][0]
    row["arms"] = {arm: row["arms"][arm] for arm in ARMS[:arms]}
    del row["assessment"]
    completed = reference_events // 2
    full_reference = row["reference_progress"]["reference"]
    row["reference_progress"] = {"reference": {"80": {}, "100": {}}}
    for profile, geometry in [(profile, geometry) for profile in ("80", "100")
                              for geometry in ("d0", "d1", "d2", "d3")][:completed]:
        row["reference_progress"]["reference"][profile][geometry] = full_reference[profile][geometry]
    report["totals"] = []
    report["ledger"] = report["ledger"][:1 + 2 * arms + reference_events]
    recount(report)
    failure(report, "source:0")
    result = run_saved(tmp_path, report, values)
    assert result["audit_status"] == "partial" and not result["scientific_verified"]
    assert result["counts"]["reference_fields"]["completed"] == (8 if arms == 3 else 0)


def test_valid_first_model_failure_stops_before_b(tmp_path: Path) -> None:
    report, values = saved_fixture()
    report["rows"] = report["rows"][:3]
    report["totals"] = report["totals"][:1]
    report["totals"][0]["assessment"] = {"A": model_assessment("A", False)}
    report["ledger"] = report["ledger"][:3 * 24 + 2]
    recount(report)
    failure(report, "totals:0:A")
    result = run_saved(tmp_path, report, values, References(model_failure="A"))
    assert result["audit_status"] == "partial"
    assert result["counts"]["model_totals"]["completed"] == 1


def test_downstream_data_after_failed_gate_is_rejected(tmp_path: Path) -> None:
    report, values = saved_fixture()
    report["rows"][0]["assessment"] = source_assessment(values["rows"][0], False)
    failure(report, "source:0")
    result = run_saved(tmp_path, report, values, References(source_failure=0))
    assert result["audit_status"] == "rejected"


def test_empty_failed_input_record_is_a_valid_partial(tmp_path: Path) -> None:
    report, values = saved_fixture()
    report["rows"], report["totals"], report["ledger"] = [], [], []
    del report["inputs"]
    del report["identity_after"]
    recount(report)
    failure(report, "inputs")
    result = run_saved(tmp_path, report, values)
    assert result["audit_status"] == "partial" and not result["scientific_verified"]


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}'])
def test_strict_json_rejects_duplicate_and_nonfinite(raw: bytes) -> None:
    with pytest.raises(ValueError):
        audit.parse(raw)


def test_exact_binary64_assembly_keeps_small_c_separate() -> None:
    raw = {"body": "Moon", "lo_s": 0.1,
           "state_si": [1e24, 0.0, 0.0, 3e8, 0.0, 0.0]}
    result = audit.reconstruct_arm(raw, [1e24, 0.0, 0.0], GM["Moon"], "compensated")
    assert result["separation_m"] == [30000000.0, 0.0, 0.0]
    assert (1e24 + 30000000.0) - 1e24 == 0.0
    wrong = audit.reconstruct_arm(raw, [1e24, 0.0, 0.0], GM["Moon"], "wrong_sign")
    assert wrong["separation_m"][0] == -result["separation_m"][0]
    with pytest.raises(ValueError, match="exclusion"):
        audit.reconstruct_arm(raw, [1e24, 0.0, 0.0], GM["Moon"], "uncorrected")


def test_exclusive_output_precedes_read_or_arithmetic(tmp_path: Path) -> None:
    output = tmp_path / "existing.json"
    output.write_text("retained")
    with pytest.raises(FileExistsError):
        audit.audit(tmp_path / "missing.json", output, clock=lambda: 0.0, start_s=0.0,
                    inputs_loader=lambda *_args: pytest.fail("input loader called"),
                    references=References())
    assert output.read_text() == "retained"


def test_post_flush_overrun_cannot_leave_passed_output() -> None:
    instant = [0.0]

    class LateFlush(io.StringIO):
        def flush(self) -> None:
            instant[0] = 10.0
            super().flush()

    stream = LateFlush()
    result = {"audit_status": "passed", "scientific_verified": True}
    budget = audit.Budget(lambda: instant[0], 0.0)
    audit.save(result, stream, budget)
    saved = json.loads(stream.getvalue())
    assert saved["audit_status"] == "rejected" and not saved["scientific_verified"]
    assert saved["finalization_gate"] == "failed"
    assert saved["error"]["stage"] == "finalization"


def test_reference_budget_counts_attempted_separately_and_stops_at_168() -> None:
    budget = audit.Budget(lambda: 0.0, 0.0)
    for _ in range(168):
        budget.consume_reference("attempt")
        budget.consume_reference("complete")
    with pytest.raises(ValueError, match="cap"):
        budget.consume_reference("attempt")
    assert budget.counts["reference_fields"] == {"attempted": 168, "completed": 168}


def test_false_failure_stage_cannot_hide_downstream_work(tmp_path: Path) -> None:
    report, values = saved_fixture()
    failure(report, "source:0")
    assert run_saved(tmp_path, report, values)["audit_status"] == "rejected"


def test_unknown_clock_elapsed_requires_explicit_finalization_failure(tmp_path: Path) -> None:
    report, values = saved_fixture()
    failure(report, "finalization")
    report["error"]["message"] = "clock: expected finite number"
    report["first_error"] = dict(report["error"])
    report["finalization_gate"] = "failed"
    report["elapsed_before_flush_s"] = None
    result = run_saved(tmp_path, report, values)
    assert result["audit_status"] == "partial" and not result["scientific_verified"]


def test_real_pure_reference_integrates_on_one_synthetic_constant_source(tmp_path: Path) -> None:
    reference_path = PATH.with_name("0157-fixed-gravity-reference.py")
    reference_spec = importlib.util.spec_from_file_location("fixed_gravity_audit_real_reference", reference_path)
    assert reference_spec is not None and reference_spec.loader is not None
    reference = importlib.util.module_from_spec(reference_spec)
    sys.modules[reference_spec.name] = reference
    reference_spec.loader.exec_module(reference)
    # Constant, collinear polynomial in km; this is wholly synthetic.
    words = [1000.0, 100.0, DISTANCES["Sun"] / 1000.0, 0.0, 0.0]
    record = reference.ORACLE.parse_record(words)
    state = [1000.0 * words[2], 0.0, 0.0, 0.0, 0.0, 0.0]
    source = {"body": "Sun", "elapsed_s": 0.0, "hi_tdb_s": 1000.0,
        "hi_hex": (1000.0).hex(), "lo_s": 0.0, "lo_hex": (0.0).hex(),
        "state_si": state, "segments": [{"body": 10, "centre": 0, "frame": 1,
        "type": 2, "first_tdb_s": 900.0, "last_tdb_s": 1100.0, "words": words}],
        "assessment": reference.ORACLE.assess(state, [record], 1000.0, 0.0)}
    report, values = saved_fixture()
    values["rows"][0] = source
    report["rows"] = report["rows"][:1]
    report["rows"][0]["source_row"] = deepcopy(source)
    arms = report["rows"][0]["arms"]
    report["rows"][0]["assessment"] = reference.assess_source(
        source, values["position_m"], GM["Sun"], audit.RADII_M["Sun"], arms, lambda _phase: None)
    assert report["rows"][0]["assessment"]["passed"]
    report["rows"][0]["reference_progress"] = {"reference": deepcopy(
        report["rows"][0]["assessment"]["reference"])}
    report["totals"], report["ledger"] = [], report["ledger"][:24]
    recount(report)
    failure(report, "source:0")
    result = run_saved(tmp_path, report, values, reference)
    assert result["audit_status"] == "partial" and not result["scientific_verified"]
    assert result["counts"]["reference_fields"]["completed"] == 8
    assert result["checks"]["source_rows"][0]["assessment"] == report["rows"][0]["assessment"]


def test_deleting_a_completed_binary64_arm_is_corruption(tmp_path: Path) -> None:
    report, values = saved_fixture()
    report["rows"], report["totals"] = report["rows"][:1], []
    report["rows"][0]["arms"].pop("wrong_sign")
    report["rows"][0].pop("assessment")
    report["rows"][0]["reference_progress"] = {}
    report["ledger"] = report["ledger"][:7]
    recount(report)
    failure(report, "source:0")
    assert run_saved(tmp_path, report, values)["audit_status"] == "rejected"


@pytest.mark.parametrize("mutation", ["delete", "change", "extra"])
def test_retained_reference_field_prefix_is_independently_checked(tmp_path: Path,
                                                               mutation: str) -> None:
    report, values = saved_fixture()
    progress = report["rows"][0]["reference_progress"]["reference"]["80"]
    if mutation == "delete":
        del progress["d3"]
    elif mutation == "change":
        progress["d0"][0] = "2"
    else:
        progress["d4"] = ["1", "0", "0"]
    assert run_saved(tmp_path, report, values)["audit_status"] == "rejected"


def test_reproducible_reference_domain_failure_stays_partial(tmp_path: Path) -> None:
    class FailingReference(References):
        def assess_source(self, _row: Any, _position: Any, _gm: Any, _radius: Any,
                          _arms: Any, _consume: Any, *, progress: Any = None) -> dict[str, Any]:
            if progress is not None:
                progress["reference"] = {"80": {}, "100": {}}
            raise ValueError("source exterior-domain guard: Sun")

    report, values = saved_fixture()
    report["rows"], report["totals"] = report["rows"][:1], []
    report["rows"][0].pop("assessment")
    report["rows"][0]["reference_progress"] = {"reference": {"80": {}, "100": {}}}
    report["ledger"] = report["ledger"][:7]
    recount(report)
    failure(report, "source:0")
    report["error"]["message"] = "source exterior-domain guard: Sun"
    report["first_error"] = dict(report["error"])
    result = run_saved(tmp_path, report, values, FailingReference())
    assert result["audit_status"] == "partial" and not result["scientific_verified"]
    assert result["checks"]["source_rows"][0]["reproduced_failure"] == report["error"]


def test_changed_reference_domain_failure_message_is_rejected(tmp_path: Path) -> None:
    class FailingReference(References):
        def assess_source(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
            raise ValueError("source exterior-domain guard: Sun")

    report, values = saved_fixture()
    report["rows"], report["totals"] = report["rows"][:1], []
    report["rows"][0].pop("assessment")
    report["rows"][0]["reference_progress"] = {}
    report["ledger"] = report["ledger"][:7]
    recount(report)
    failure(report, "source:0")
    assert run_saved(tmp_path, report, values, FailingReference())["audit_status"] == "rejected"


def test_helper_load_executes_exact_hashed_bytes_and_rejects_drift(tmp_path: Path) -> None:
    from hashlib import sha256

    directory = tmp_path / "docs/adr/experiments"
    directory.mkdir(parents=True)
    helper = directory / "analytic-helper.py"
    raw = b"VALUE = 7\n"
    helper.write_bytes(raw)
    loaded = audit.load_helper(tmp_path, helper.name, sha256(raw).hexdigest(), lambda: None)
    assert loaded.VALUE == 7
    helper.write_bytes(b"raise AssertionError('must never execute mismatched helper')\n")
    with pytest.raises(ValueError, match="SHA256"):
        audit.load_helper(tmp_path, helper.name, sha256(raw).hexdigest(), lambda: None)


def test_late_flush_failure_preserves_earliest_error() -> None:
    class OnceFailedFlush(io.StringIO):
        failed = False

        def flush(self) -> None:
            if not self.failed:
                self.failed = True
                raise OSError("fixture flush failed")
            super().flush()

    earliest = {"stage": "inputs", "type": "ValueError", "message": "earliest"}
    result = {"audit_status": "rejected", "scientific_verified": False,
              "error": {"stage": "saved-data", "type": "ValueError", "message": "later"},
              "first_error": deepcopy(earliest)}
    stream = OnceFailedFlush()
    audit.save(result, stream, audit.Budget(lambda: 0.0, 0.0))
    saved = json.loads(stream.getvalue())
    assert saved["first_error"] == earliest
    assert saved["error"]["stage"] == "finalization"
    assert saved["audit_status"] == "rejected" and not saved["scientific_verified"]


@pytest.mark.parametrize("explicit_start", [True, False])
def test_invalid_initial_baseline_is_argument_error_without_output(tmp_path: Path,
                                                                 explicit_start: bool) -> None:
    output = tmp_path / "unreserved.json"
    clock = (lambda: 0.0) if explicit_start else (lambda: float("nan"))
    with pytest.raises(ValueError, match="finite"):
        audit.audit(tmp_path / "missing.json", output, clock=clock,
                    start_s=float("nan") if explicit_start else None,
                    inputs_loader=lambda *_args: pytest.fail("input loader called"),
                    references=References())
    assert not output.exists()


def test_reproducible_model_b_failure_keeps_completed_a(tmp_path: Path) -> None:
    class FailingBReference(References):
        def assess_totals(self, _sources: Any, _arms: Any, *, consume_model: Any,
                          progress: Any = None) -> dict[str, Any]:
            assert progress is not None
            consume_model("attempt")
            progress["A"] = model_assessment("A")
            consume_model("complete")
            consume_model("attempt")
            raise ValueError("fixture model B boundary failure")

    report, values = saved_fixture()
    report["rows"], report["totals"] = report["rows"][:3], report["totals"][:1]
    report["totals"][0]["assessment"] = {"A": model_assessment("A")}
    report["ledger"] = report["ledger"][:3 * 24 + 3]
    recount(report)
    failure(report, "totals:0:B")
    report["error"]["message"] = "fixture model B boundary failure"
    report["first_error"] = dict(report["error"])
    result = run_saved(tmp_path, report, values, FailingBReference())
    assert result["audit_status"] == "partial" and not result["scientific_verified"]
    assert result["checks"]["model_totals"][0]["models_checked"] == ["A"]
    assert result["counts"]["model_totals"] == {"attempted": 2, "completed": 1}
