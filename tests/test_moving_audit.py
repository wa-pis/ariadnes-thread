"""Handmade synthetic saved-data audit fixtures; no retained study is executed."""

from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
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
PATH = ROOT / "docs/adr/experiments/0160-moving-audit.py"
spec = importlib.util.spec_from_file_location("moving_audit_test_module", PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
audit = module
GM = {"Sun": 1.327124400420322e20, "Moon": 4902800121846.8, "Earth": 398600435468295.9}
ARMS = ("compensated", "flattened_craft", "omitted_q")
MODELS = {"A": ("Sun", "Moon"), "B": ("Sun", "Moon", "Earth")}
SOURCE_ORDER = ("Sun", "Earth", "Moon")
DISTANCE = float(2**40)


def ratios(values: list[float]) -> list[dict[str, str]]:
    result = []
    for value in values:
        n, d = value.as_integer_ratio()
        result.append({"numerator": str(n), "denominator": str(d)})
    return result


def motion(s: float, initial: dict[str, Any]) -> dict[str, Any]:
    # Integer fixture times make these prescribed dyadic corrections exact.
    q = [0.0 if v == 0 else v for v in (-s * s / 2, s * s / 4, -s * s / 8)]
    w = [0.0 if v == 0 else v for v in (-s, s / 2, -s / 4)]
    d = [v * s for v in initial["velocity_m_s"]]
    return {
        "label": "controlled-kinematic-arithmetic-probe",
        "elapsed_s": s,
        "elapsed_hex": s.hex(),
        "q_ideal_m": ratios(q),
        "w_ideal_m_s": ratios(w),
        "q_m": q,
        "q_hex": [v.hex() for v in q],
        "q_ratios": ratios(q),
        "w_m_s": w,
        "w_hex": [v.hex() for v in w],
        "w_ratios": ratios(w),
        "drift_m": d,
        "position_m": [initial["position_m"][j] + d[j] + q[j] for j in range(3)],
        "velocity_m_s": [initial["velocity_m_s"][j] + w[j] for j in range(3)],
    }


def fixture_arms(
    raw: dict[str, Any], m: dict[str, Any], initial: dict[str, Any]
) -> dict[str, Any]:
    # Prescribed source coordinates make the required separation exactly collinear.
    r = DISTANCE
    q = m["q_m"]
    required = [GM[raw["body"]] / (r * r), 0.0, 0.0]
    omitted = [r + q[0], q[1], q[2]]
    length = math.sqrt(sum(v * v for v in omitted))
    omitted_force = [
        GM[raw["body"]] * (v / length) / (length * length) for v in omitted
    ]
    return {
        "compensated": {
            "separation_m": [r, 0.0, 0.0],
            "rephasing_m": [0.0] * 3,
            "acceleration_m_s2": required,
        },
        "flattened_craft": {
            "separation_m": [r, 0.0, 0.0],
            "rephasing_m": [0.0] * 3,
            "acceleration_m_s2": required,
        },
        "omitted_q": {
            "separation_m": omitted,
            "rephasing_m": [0.0] * 3,
            "acceleration_m_s2": omitted_force,
        },
    }


def source_assessment(passed: bool = True) -> dict[str, Any]:
    return {
        "passed": passed,
        "gates": {"overall": passed},
        "reference": {
            p: {g: ["1", "0", "0"] for g in ("d0", "d1", "d2", "d3")}
            for p in ("80", "100")
        },
    }


def model_assessment(name: str, passed: bool = True) -> dict[str, Any]:
    return {"model": name, "passed": passed, "gates": {"overall": passed}}


class References:
    """Explicit injected reference boundary; source arithmetic tests stay separate."""

    def __init__(
        self,
        *,
        fail_motion: bool = False,
        fail_source: bool = False,
        fail_model: str | None = None,
        source_error: bool = False,
    ) -> None:
        self.fail_motion = fail_motion
        self.fail_source = fail_source
        self.fail_model = fail_model
        self.source_error = source_error

    def assess_motion(self, initial: Any, value: Any) -> dict[str, Any]:
        return {"passed": not self.fail_motion, "component_bounds": [True] * 3}

    def preflight_source(
        self,
        raw: Any,
        initial: Any,
        value: Any,
        gm: Any,
        radius: Any,
        arms: Any,
        *,
        progress: dict[str, Any],
    ) -> None:
        assert list(arms) == list(ARMS)
        assert all(set(arm) == {"separation_m", "rephasing_m"} for arm in arms.values())
        progress["component_checks"] = {"passed": not self.source_error}
        progress["reference"] = {"80": {}, "100": {}}
        if self.source_error:
            raise ValueError("synthetic reference-domain failure")

    def assess_source(
        self,
        raw: Any,
        initial: Any,
        value: Any,
        gm: Any,
        radius: Any,
        arms: Any,
        consume: Any,
        *,
        progress: dict[str, Any],
    ) -> dict[str, Any]:
        result = source_assessment(not self.fail_source)
        for p in ("80", "100"):
            for g in ("d0", "d1", "d2", "d3"):
                consume("attempt")
                progress["reference"][p][g] = result["reference"][p][g]
                consume("complete")
        return result

    def assess_totals(
        self, rows: Any, arms: Any, *, consume_model: Any, progress: dict[str, Any]
    ) -> dict[str, Any]:
        for model in MODELS:
            consume_model("attempt")
            progress[model] = model_assessment(model, self.fail_model != model)
            consume_model("complete")
            if not progress[model]["passed"]:
                break
        return progress


def fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    initial = {
        "epoch_tdb_s": 1.0,
        "position_m": [float(2**44), -float(2**43), float(2**42)],
        "velocity_m_s": [3.0, -2.0, 1.0],
    }
    values: dict[str, Any] = {
        "position_m": initial["position_m"],
        "initial": initial,
        "gm_m3_s2": dict(GM),
        "rows": [],
        "input_sha256": {"synthetic": "fixture"},
        "source_provenance": {"fixture_only": True},
        "identity": {"fixture_only": True},
    }
    report: dict[str, Any] = {
        "contract": "ADR0159",
        "study": "controlled-moving-assembly-v1",
        "status": "passed",
        "adapter_mode": "injected-test",
        "research_only": True,
        "mission_accuracy_verified": False,
        "continuous_safety_verified": False,
        "origin": "SSB",
        "orientation": "J2000",
        "time_scale": "TDB",
        "aberration_correction": "NONE",
        "position_units": "m",
        "velocity_units": "m/s",
        "acceleration_units": "m/s^2",
        "budget_s": 10.0,
        "native_calls": 0,
        "kernel_loads": 0,
        "gm_acquisitions": 0,
        "spacecraft_propagations": 0,
        "scientific_imports": 0,
        "optimizer_calls": 0,
        "reference_replayed": False,
        "motions": [],
        "rows": [],
        "totals": [],
        "ledger": audit.expected_ledger(),
        "helper_sha256": {},
        "elapsed_before_flush_s": 0.01,
        "finalization_gate": "passed",
    }
    for t in range(7):
        s = float(t)
        m = motion(s, initial)
        report["motions"].append(
            {
                "index": t,
                "motion": m,
                "assessment": {"passed": True, "component_bounds": [True] * 3},
            }
        )
        block = []
        for body in SOURCE_ORDER:
            state = [m["position_m"][0] + DISTANCE, *m["position_m"][1:], 0.0, 0.0, 0.0]
            raw = {"body": body, "elapsed_s": s, "lo_s": 0.0, "state_si": state}
            values["rows"].append(raw)
            arms = fixture_arms(raw, m, initial)
            row = {
                "index": len(report["rows"]),
                "source_row": deepcopy(raw),
                "arms": arms,
                "reference_progress": {
                    "component_checks": {"passed": True},
                    "reference": source_assessment()["reference"],
                },
                "assessment": source_assessment(),
            }
            report["rows"].append(row)
            block.append(row)
        source_by_body = {r["source_row"]["body"]: r for r in block}
        totals = {
            model: {
                arm: {
                    "acceleration_m_s2": [
                        math.fsum(
                            source_by_body[body]["arms"][arm]["acceleration_m_s2"][j]
                            for body in bodies
                        )
                        for j in range(3)
                    ]
                }
                for arm in ARMS
            }
            for model, bodies in MODELS.items()
        }
        report["totals"].append(
            {
                "index": t,
                "elapsed_s": s,
                "arms": totals,
                "assessment": {name: model_assessment(name) for name in MODELS},
            }
        )
    values["zero_reference"] = {
        "sources": {
            r["source_row"]["body"]: deepcopy(r["arms"]["compensated"])
            for r in report["rows"][:3]
        },
        "totals": {
            name: deepcopy(report["totals"][0]["arms"][name]["compensated"])
            for name in MODELS
        },
    }
    report["inputs"] = {key: deepcopy(values[key]) for key in audit.INPUT_KEYS}
    report["identity_after"] = deepcopy(report["inputs"])
    recount(report)
    return report, values


def recount(report: dict[str, Any]) -> None:
    report["counts"] = {name: {"attempted": 0, "completed": 0} for name in audit.LIMITS}
    for item in report["ledger"]:
        report["counts"][item["operation"]][
            "attempted" if item["phase"] == "attempt" else "completed"
        ] += 1


def negative(
    report: dict[str, Any], stage: str, message: str = "synthetic failure"
) -> None:
    report["status"] = "partial"
    report.pop("identity_after", None)
    report["error"] = {"stage": stage, "type": "ValueError", "message": message}
    report["first_error"] = deepcopy(report["error"])
    recount(report)


def run(
    tmp_path: Path, report: dict[str, Any], values: dict[str, Any], refs: Any = None
) -> dict[str, Any]:
    path = tmp_path / "source.json"
    path.write_text(json.dumps(report, allow_nan=False))
    return audit.audit(
        path,
        tmp_path / "audit.json",
        inputs_loader=lambda root, check: values,
        references=References() if refs is None else refs,
        clock=lambda: 0.0,
    )


def test_complete_handmade_fixture_audits_without_science_qualification(
    tmp_path: Path,
) -> None:
    report, values = fixture()
    result = run(tmp_path, report, values)
    assert result["audit_status"] == "passed", result
    assert (
        result["scientific_verified"] is False
        and result["adapter_mode"] == "injected-test"
    )
    assert (
        result["evidence_sha256"]
        == sha256((tmp_path / "source.json").read_bytes()).hexdigest()
    )
    assert result["counts"] == report["counts"]
    assert result["checks"]["complete_saved_data_checked"] is True
    assert json.loads((tmp_path / "audit.json").read_text()) == result


@pytest.mark.parametrize(
    "mutation",
    [
        "q",
        "qhex",
        "qratio",
        "ideal",
        "drift",
        "position",
        "velocity",
        "label",
        "raw_source",
        "arm_force",
        "arm_separation",
        "arm_rephasing",
        "source_gate",
        "source_reference",
        "progress_reference",
        "progress_component",
        "motion_gate",
        "model_gate",
        "model_sum",
        "zero_source",
        "zero_model",
        "final_identity",
        "units",
        "frame",
        "native",
        "optimizer",
        "counts",
        "ledger",
    ],
)
def test_saved_corruption_rejected(tmp_path: Path, mutation: str) -> None:
    report, values = fixture()
    m = report["motions"][1]["motion"]
    row = report["rows"][0]
    if mutation in {"q", "drift", "position", "velocity"}:
        key = {
            "q": "q_m",
            "drift": "drift_m",
            "position": "position_m",
            "velocity": "velocity_m_s",
        }[mutation]
        m[key][0] += 1.0
    elif mutation == "qhex":
        m["q_hex"][0] = "0x0.0p+0"
    elif mutation == "qratio":
        m["q_ratios"][0]["numerator"] = "123"
    elif mutation == "ideal":
        m["q_ideal_m"][0]["numerator"] = "123"
    elif mutation == "label":
        m["label"] = "real-trajectory"
    elif mutation == "raw_source":
        row["source_row"]["state_si"][0] += 1.0
    elif mutation.startswith("arm_"):
        key = {
            "arm_force": "acceleration_m_s2",
            "arm_separation": "separation_m",
            "arm_rephasing": "rephasing_m",
        }[mutation]
        row["arms"]["compensated"][key][0] += 1.0
    elif mutation == "source_gate":
        row["assessment"]["passed"] = False
    elif mutation == "source_reference":
        row["assessment"]["reference"]["80"]["d0"][0] = "2"
    elif mutation == "progress_reference":
        row["reference_progress"]["reference"]["80"]["d0"][0] = "2"
    elif mutation == "progress_component":
        row["reference_progress"]["component_checks"]["passed"] = False
    elif mutation == "motion_gate":
        report["motions"][0]["assessment"]["passed"] = False
    elif mutation == "model_gate":
        report["totals"][0]["assessment"]["A"]["passed"] = False
    elif mutation == "model_sum":
        report["totals"][0]["arms"]["B"]["omitted_q"]["acceleration_m_s2"][0] += 1.0
    elif mutation == "zero_source":
        values["zero_reference"]["sources"]["Sun"]["separation_m"][0] += 1.0
    elif mutation == "zero_model":
        values["zero_reference"]["totals"]["A"]["acceleration_m_s2"][0] += 1.0
    elif mutation == "final_identity":
        report.pop("identity_after")
    elif mutation == "units":
        report["position_units"] = "km"
    elif mutation == "frame":
        report["origin"] = "Sun"
    elif mutation == "native":
        report["native_calls"] = 1
    elif mutation == "optimizer":
        report["optimizer_calls"] = 1
    elif mutation == "counts":
        report["counts"]["six_state_assemblies"]["completed"] = 6
    else:
        report["ledger"][0]["operation"] = "source_rows"
    result = run(tmp_path, report, values)
    assert result["audit_status"] == "rejected" and not result["scientific_verified"]


def test_missing_earlier_motion_assessment_rejected(tmp_path: Path) -> None:
    report, values = fixture()
    report["motions"][0].pop("assessment")
    assert run(tmp_path, report, values)["audit_status"] == "rejected"


def test_valid_failed_motion_remains_partial(tmp_path: Path) -> None:
    report, values = fixture()
    report["motions"] = report["motions"][:1]
    report["motions"][0]["assessment"]["passed"] = False
    report["rows"], report["totals"] = [], []
    report["ledger"] = report["ledger"][:2]
    negative(report, "motion:0")
    result = run(tmp_path, report, values, References(fail_motion=True))
    assert result["audit_status"] == "partial", result
    assert result["checks"]["first_required_gate_failure"] == "motion:0"


def test_valid_incomplete_motion_array_remains_partial(tmp_path: Path) -> None:
    report, values = fixture()
    report["motions"] = [
        {
            "index": 0,
            "motion": {"label": "controlled-kinematic-arithmetic-probe", "q_m": [0.0]},
        }
    ]
    report["rows"], report["totals"] = [], []
    report["ledger"] = report["ledger"][:1]
    negative(report, "motion:0")
    result = run(tmp_path, report, values)
    assert result["audit_status"] == "partial", result
    assert result["counts"]["six_state_assemblies"] == {"attempted": 1, "completed": 0}


def first_source_prefix(
    report: dict[str, Any], *, arms: int = 3, fields: int = 8, completed: bool = False
) -> None:
    report["motions"] = report["motions"][:1]
    report["rows"], report["totals"] = report["rows"][:1], []
    row = report["rows"][0]
    row["arms"] = {name: row["arms"][name] for name in ARMS[:arms]}
    if not completed:
        row.pop("assessment")
    sequence = [(p, g) for p in ("80", "100") for g in ("d0", "d1", "d2", "d3")]
    row["reference_progress"]["reference"] = {"80": {}, "100": {}}
    for p, g in sequence[:fields]:
        row["reference_progress"]["reference"][p][g] = ["1", "0", "0"]
    report["ledger"] = report["ledger"][
        : 2 + 1 + 2 * arms + 2 * fields + int(completed)
    ]
    negative(report, "source:0")


def test_valid_required_source_failure_remains_partial(tmp_path: Path) -> None:
    report, values = fixture()
    first_source_prefix(report, completed=True)
    report["rows"][0]["assessment"]["passed"] = False
    report["rows"][0]["assessment"]["gates"]["overall"] = False
    result = run(tmp_path, report, values, References(fail_source=True))
    assert result["audit_status"] == "partial", result
    assert result["checks"]["first_required_gate_failure"] == "source:0"


@pytest.mark.parametrize("arms,fields", [(1, 0), (3, 1), (3, 8)])
def test_available_source_fields_survive_partial_clock_paths(
    tmp_path: Path, arms: int, fields: int
) -> None:
    report, values = fixture()
    first_source_prefix(report, arms=arms, fields=fields)
    result = run(tmp_path, report, values)
    assert result["audit_status"] == "partial", result
    assert not result["scientific_verified"]
    assert len(result["checks"]["source_rows"][0]["arms"]) == arms


def test_independent_pre_field_failure_is_reconciled(tmp_path: Path) -> None:
    report, values = fixture()
    first_source_prefix(report, arms=0, fields=0)
    report["rows"][0]["reference_progress"]["component_checks"]["passed"] = False
    report["error"]["message"] = report["first_error"]["message"] = (
        "synthetic reference-domain failure"
    )
    result = run(tmp_path, report, values, References(source_error=True))
    assert result["audit_status"] == "partial", result
    assert result["counts"]["reference_fields"] == {"attempted": 0, "completed": 0}
    assert result["counts"]["binary64_fields"] == {"attempted": 0, "completed": 0}
    assert (
        result["checks"]["source_rows"][0]["reference_progress"]["component_checks"][
            "passed"
        ]
        is False
    )


def test_failed_first_model_does_not_qualify_second(tmp_path: Path) -> None:
    report, values = fixture()
    report["motions"], report["rows"], report["totals"] = (
        report["motions"][:1],
        report["rows"][:3],
        report["totals"][:1],
    )
    report["totals"][0]["assessment"] = {"A": model_assessment("A", False)}
    report["ledger"] = report["ledger"][: 2 + 3 * 24 + 2]
    negative(report, "totals:0:A")
    result = run(tmp_path, report, values, References(fail_model="A"))
    assert result["audit_status"] == "partial", result
    assert result["checks"]["model_totals"][0]["models_checked"] == ["A"]
    assert result["counts"]["model_totals"] == {"attempted": 1, "completed": 1}


def test_motion_arithmetic_reconstruction_preserves_small_terms() -> None:
    initial = {"position_m": [1e16, 0.0, 0.0], "velocity_m_s": [1.0, 0.0, 0.0]}
    m = audit.reconstruct_motion(initial, 1.0)
    raw = {
        "body": "Moon",
        "state_si": [1e16 + 4e6, 0.0, 0.0, 0.0, 0.0, 0.0],
        "lo_s": 0.0,
    }
    required = audit.reconstruct_arm(raw, initial, m, 1.0, "compensated")
    flattened = audit.reconstruct_arm(raw, initial, m, 1.0, "flattened_craft")
    assert required["separation_m"] == [3999999.5, -0.25, 0.125]
    assert flattened["separation_m"] == [4e6, -0.25, 0.125]
    exact = (
        Fraction.from_float(1e16 + 4e6) - Fraction.from_float(1e16) - 1 + Fraction(1, 2)
    )
    assert Fraction.from_float(required["separation_m"][0]) == exact


def test_independent_analytic_3d_force() -> None:
    initial = {"position_m": [0.0] * 3, "velocity_m_s": [0.0] * 3}
    m = audit.reconstruct_motion(initial, 0.0)
    raw = {"body": "Moon", "state_si": [3e6, 4e6, 0.0, 0.0, 0.0, 0.0], "lo_s": 0.0}
    result = audit.reconstruct_arm(raw, initial, m, 25e12, "compensated")
    assert result["acceleration_m_s2"] == [0.6, 0.8, 0.0]


@pytest.mark.parametrize(
    "raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b"[]"]
)
def test_strict_json_boundary(raw: bytes) -> None:
    with pytest.raises(ValueError):
        audit.parse(raw)


@pytest.mark.parametrize("start", [True, math.nan, math.inf, "0"])
def test_invalid_initial_clock_leaves_no_empty_output(
    tmp_path: Path, start: Any
) -> None:
    with pytest.raises((ValueError, TypeError)):
        audit.audit(tmp_path / "missing", tmp_path / "out", start_s=start)
    assert not (tmp_path / "out").exists()


def test_output_is_exclusive(tmp_path: Path) -> None:
    report, values = fixture()
    run(tmp_path, report, values)
    original = (tmp_path / "audit.json").read_bytes()
    with pytest.raises(FileExistsError):
        run(tmp_path, report, values)
    assert (tmp_path / "audit.json").read_bytes() == original


def test_budget_caps_and_nonfinite_clock() -> None:
    b = audit.Budget(lambda: 0.0, 0.0)
    for _ in range(7):
        b.event("six_state_assemblies", "attempt")
        b.event("six_state_assemblies", "complete")
    with pytest.raises(ValueError, match="cap"):
        b.event("six_state_assemblies", "attempt")
    assert b.counts["six_state_assemblies"] == {"attempted": 7, "completed": 7}
    with pytest.raises(ValueError):
        audit.Budget(lambda: math.nan, 0.0).check()


def test_post_flush_failure_downgrades_persisted_success() -> None:
    ticks = iter([0.0, 0.0, 11.0, 11.0])
    b = audit.Budget(lambda: next(ticks), 0.0)
    stream = io.StringIO()
    result = audit.save(
        {"audit_status": "passed", "scientific_verified": True}, stream, b
    )
    persisted = json.loads(stream.getvalue())
    assert result == persisted
    assert result["audit_status"] == "rejected" and not result["scientific_verified"]
    assert (
        result["finalization_gate"] == "failed"
        and result["error"]["stage"] == "finalization"
    )


def test_fresh_import_does_not_load_candidate_or_science() -> None:
    code = "import runpy,sys,json; runpy.run_path(sys.argv[1]); print(json.dumps([n for n in sys.modules if n.split('.')[0] in ('numpy','scipy','spiceypy','tudatpy','space_nav') or n.startswith('moving_study')]))"
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", code, str(PATH)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == []


def test_reset_real_process_clock_rejected_before_saved_data(tmp_path: Path) -> None:
    result = audit.audit(
        tmp_path / "missing", tmp_path / "out", start_s=audit.monotonic()
    )
    assert result["audit_status"] == "rejected"
    assert result["error"]["stage"] == "inputs"


def test_corrupt_preflight_progress_rejected_before_fields(tmp_path: Path) -> None:
    report, values = fixture()
    first_source_prefix(report, arms=0, fields=0)
    report["error"]["message"] = report["first_error"]["message"] = (
        "synthetic reference-domain failure"
    )
    result = run(tmp_path, report, values, References(source_error=True))
    assert result["audit_status"] == "rejected", result
    assert result["counts"]["binary64_fields"] == {"attempted": 0, "completed": 0}
    assert result["counts"]["reference_fields"] == {"attempted": 0, "completed": 0}


def test_later_motion_after_incomplete_source_rejected(tmp_path: Path) -> None:
    report, values = fixture()
    extra = deepcopy(report["motions"][1])
    first_source_prefix(report, arms=1, fields=0)
    report["motions"].append(extra)
    report["ledger"].extend(
        [
            {"operation": "six_state_assemblies", "phase": "attempt"},
            {"operation": "six_state_assemblies", "phase": "complete"},
        ]
    )
    recount(report)
    assert run(tmp_path, report, values)["audit_status"] == "rejected"


def test_partial_reference_vector_cannot_be_truncated(tmp_path: Path) -> None:
    report, values = fixture()
    first_source_prefix(report, fields=1)
    report["rows"][0]["reference_progress"]["reference"]["80"]["d0"] = ["1"]
    assert run(tmp_path, report, values)["audit_status"] == "rejected"


def test_completed_preflight_metadata_cannot_be_deleted(tmp_path: Path) -> None:
    report, values = fixture()
    first_source_prefix(report, arms=1, fields=0)
    report["rows"][0]["reference_progress"].pop("component_checks")
    assert run(tmp_path, report, values)["audit_status"] == "rejected"


def test_elapsed_overflow_persists_finite_negative_result() -> None:
    b = audit.Budget(lambda: 1e308, -1e308)
    stream = io.StringIO()
    result = audit.save(
        {"audit_status": "passed", "scientific_verified": True}, stream, b
    )
    assert result == json.loads(stream.getvalue())
    assert result["audit_status"] == "rejected"
    assert result["elapsed_before_flush_s"] is None
    assert result["elapsed_after_failed_flush_s"] is None
