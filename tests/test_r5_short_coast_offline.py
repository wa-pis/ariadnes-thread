"""Offline orchestration fixtures only; never generate a reference trajectory."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import io
import json
import math
from pathlib import Path
import runpy
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0146-audit-short-coast.py"
spec = importlib.util.spec_from_file_location("r5_offline_entry_tests", PATH)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
# Reuse already-tested static fixture builders; no solver/runner is imported.
fixtures = runpy.run_path(str(ROOT / "tests/test_r5_short_coast_audit.py"))


def delta(left: list[float], right: list[float]) -> dict[str, Any]:
    value = [b - a for a, b in zip(left, right, strict=True)]
    return {
        "right_minus_left_si": value,
        "position_norm_m": math.hypot(*value[:3]),
        "velocity_norm_m_s": math.hypot(*value[3:]),
    }


def numerical(block: dict[str, Any]) -> list[dict[str, Any]]:
    results = {k: v["result"]["samples"] for k, v in block["profiles"].items()}
    rows = []
    for j, epoch in enumerate(audit.core.OFFSETS):
        row: dict[str, Any] = {"epoch_tdb_s": epoch, "gates": {}}
        for name, left, right, pos, vel in [
            ("native_profile", "native-normal", "native-tight", 0.01, 1e-5),
            ("native_oracle", "native-tight", "oracle-tight", 0.01, 1e-5),
            ("oracle_profile", "oracle-normal", "oracle-tight", 0.001, 1e-6),
        ]:
            row[name] = delta(results[left][j]["state"], results[right][j]["state"])
            row["gates"][name] = (
                row[name]["position_norm_m"] <= pos
                and row[name]["velocity_norm_m_s"] <= vel
            )
        rows.append(row)
    return rows


def make_report() -> tuple[dict[str, Any], dict[str, Any]]:
    a, bodies = fixtures["block"]("A")
    b, _ = fixtures["block"]("B")
    initial = list(fixtures["INITIAL"])
    bundle = {
        "state_si": initial,
        "epoch_tdb_s": 0.0,
        "nodes_tdb_s": list(audit.core.OFFSETS),
        "fixture": "injected; not R5",
    }
    minima = {"Sun": 1e9, "Moon": 1e9, "Earth": 2e9}
    prior = {
        "rhs_attempted": 0,
        "rhs_completed": 0,
        "states_attempted": 21,
        "states_completed": 21,
    }
    for block in (a, b):
        for tag, entry in block["profiles"].items():
            entry["result"]["minimum_checked_distances_m"] = dict(minima)
            if tag.startswith("oracle"):
                result = entry["result"]
                result["counts_before"] = dict(prior)
                prior = {
                    k: v + (48 if k.startswith("states") else 16)
                    for k, v in prior.items()
                }
                result["counts_after"] = dict(prior)
        block["numerical_comparison"] = numerical(block)
    for row in bodies:
        row["request"] = {
            "body": "Earth",
            "epoch_tdb_s": row["epoch_tdb_s"],
            "origin": "SSB",
            "orientation": "J2000",
            "aberration_correction": "NONE",
        }
    labels = ["inputs", "initial identity"]
    labels += [
        f"node table {t} {body}" for t in audit.core.OFFSETS for body in audit.core.GM
    ]
    labels += [
        f"{m} {tag.replace('-', ' ')}" for m in ("A", "B") for tag in audit.core.TAGS
    ]
    labels += ["final identity"]
    zeros = delta([0.0] * 6, [0.0] * 6)
    report = {
        "contract": "ADR0137",
        "study": "r5-short-coast-earth-gravity-v1",
        "status": "passed",
        "adapter_mode": "injected-test",
        "research_only": True,
        "mission_accuracy_verified": False,
        "continuous_safety_verified": False,
        **audit.core.LABELS,
        "acceleration_units": "m/s^2",
        "budget_s": 60.0,
        "constant_mass_metadata_kg": 2000.0,
        "omissions": list(audit.OMISSIONS),
        "inputs": bundle,
        "body_table": bodies,
        "models": {"A": a, "B": b},
        "calls": [
            {
                "label": label,
                "start_s": j / 1000,
                "end_s": j / 1000 + 0.0005,
                "returned": True,
            }
            for j, label in enumerate(labels)
        ],
        "counts": {
            "native_arcs_attempted": 4,
            "native_arcs_returned": 4,
            "native_arcs_completed": 4,
            "native_guard_reads_attempted": 5424,
            "native_guard_reads_returned": 5424,
            "oracle": prior,
        },
        "oracle_solves_attempted": 4,
        "oracle_solves_returned": 4,
        "oracle_solves_completed": 4,
        "native_minimum_checked_distances_m": dict(minima),
        "oracle_minimum_checked_distances_m": dict(minima),
        "guard_minimum_scope": "cumulative whole study; sampled states/RHS only, not continuous safety",
        "signed_model_differences": [
            {
                "epoch_tdb_s": t,
                "native_B_minus_A": deepcopy(zeros),
                "oracle_B_minus_A": deepcopy(zeros),
                "oracle_minus_native_sensitivity": deepcopy(zeros),
                "gate": True,
            }
            for t in audit.core.OFFSETS
        ],
        "elapsed_sample_before_flush_s": 0.1,
        "finalization_gate": "passed",
        "interpretation": "restricted300s model sensitivity; empirical numerical comparison only",
    }
    return report, bundle


def failed_setup() -> dict[str, Any]:
    report, _ = make_report()
    report.update(
        status="failed",
        adapter_mode="reference",
        body_table=[],
        models={},
        calls=[],
        signed_model_differences=[],
        error={"stage": "setup", "type": "ValueError", "message": "fixture failure"},
        interpretation="unavailable until every numerical gate passes",
    )
    report.pop("inputs")
    report["counts"] = {
        "native_arcs_attempted": 0,
        "native_arcs_returned": 0,
        "native_arcs_completed": 0,
        "native_guard_reads_attempted": 0,
        "native_guard_reads_returned": 0,
        "oracle": {
            "rhs_attempted": 0,
            "rhs_completed": 0,
            "states_attempted": 0,
            "states_completed": 0,
        },
    }
    for key in (
        "oracle_solves_attempted",
        "oracle_solves_returned",
        "oracle_solves_completed",
    ):
        report[key] = 0
    return report


def test_complete_injected_saved_data_never_grants_reference_verdict() -> None:
    report, bundle = make_report()
    result = audit.check_saved(report, bundle, lambda: None)
    assert result["complete_saved_data_checked"] and not result["study_verified"]
    assert len(result["models"]["A"]["node_forces"]) == 28
    assert len(result["models"]["B"]["node_forces"]) == 28
    assert len(result["signed_model_differences"]) == 7
    assert result["ledger"]["events_checked"] == 32
    assert result["ledger"]["oracle_results_with_reconciled_counts"] == 4
    assert not result["ledger"]["internal_native_reads_recounted"]
    assert not result["ledger"]["historical_flush_remeasured"]


@pytest.mark.parametrize(
    "fault",
    [
        "calls",
        "return_flag",
        "time",
        "rhs",
        "queries",
        "guard_reads",
        "before",
        "nfev",
        "gate",
        "norm",
        "source",
        "minima",
        "claim",
        "mass_boolean",
        "profile",
        "body_return",
    ],
)
def test_saved_ledger_and_numerical_corruption_is_rejected(fault: str) -> None:
    r, bundle = make_report()
    if fault == "calls":
        r["calls"][2], r["calls"][3] = r["calls"][3], r["calls"][2]
    elif fault == "return_flag":
        r["calls"][-1]["returned"] = False
    elif fault == "time":
        r["calls"][-1]["end_s"] = 61.0
    elif fault == "rhs":
        r["counts"]["oracle"]["rhs_attempted"] = True
    elif fault == "queries":
        r["counts"]["oracle"]["states_completed"] -= 1
    elif fault == "guard_reads":
        r["counts"]["native_guard_reads_returned"] -= 1
    elif fault == "before":
        r["models"]["B"]["profiles"]["oracle-normal"]["result"]["counts_before"][
            "rhs_completed"
        ] += 1
    elif fault == "nfev":
        r["models"]["A"]["profiles"]["oracle-normal"]["result"]["nfev"] += 1
    elif fault == "gate":
        r["models"]["A"]["numerical_comparison"][0]["gates"]["native_profile"] = False
    elif fault == "norm":
        r["signed_model_differences"][0]["native_B_minus_A"]["position_norm_m"] = 1.0
    elif fault == "source":
        r["models"]["B"]["node_forces"][0]["per_source_m_s2"]["Earth"][0] *= -1
    elif fault == "minima":
        r["oracle_minimum_checked_distances_m"]["Moon"] += 1.0
    elif fault == "claim":
        r["interpretation"] = "mission safe"
    elif fault == "mass_boolean":
        r["constant_mass_metadata_kg"] = True
    elif fault == "profile":
        r["models"]["A"]["profiles"]["native-tight"]["result"]["samples"][1]["state"][
            0
        ] += 1
    else:
        r["body_table"][0]["states"].pop("Earth")
    with pytest.raises((ValueError, KeyError)):
        audit.check_saved(r, bundle, lambda: None)


def test_declared_numerical_failure_preserves_false_gates_as_partial() -> None:
    r, bundle = make_report()
    r.update(
        status="failed",
        interpretation="unavailable until every numerical gate passes",
        error={
            "stage": "A numerical comparison",
            "type": "ValueError",
            "message": "numerical gate",
        },
    )
    r["models"].pop("B")
    r["signed_model_differences"] = []
    profile = r["models"]["A"]["profiles"]["oracle-tight"]["result"]
    profile["corrections"][-1][3] = 0.001
    profile["samples"][-1]["state"][3] = 0.001
    r["models"]["A"]["numerical_comparison"] = numerical(r["models"]["A"])
    r["calls"] = r["calls"][:27]
    for key in (
        "native_arcs_attempted",
        "native_arcs_returned",
        "native_arcs_completed",
    ):
        r["counts"][key] = 2
    for key in ("native_guard_reads_attempted", "native_guard_reads_returned"):
        r["counts"][key] = 2712
    r["counts"]["oracle"] = dict(profile["counts_after"])
    for key in (
        "oracle_solves_attempted",
        "oracle_solves_returned",
        "oracle_solves_completed",
    ):
        r[key] = 2
    checked = audit.check_saved(r, bundle, lambda: None)
    assert not checked["complete_saved_data_checked"] and not checked["study_verified"]
    assert (
        checked["models"]["A"]["numerical_comparisons"][-1]["comparisons"][
            "native_oracle"
        ]["gate"]
        is False
    )
    r["models"]["B"] = make_report()[0]["models"]["B"]
    with pytest.raises(ValueError, match="downstream"):
        audit.check_saved(r, bundle, lambda: None)


def test_partial_failed_profile_keeps_unavailable_operands_without_promotion() -> None:
    r, bundle = make_report()
    r.update(
        status="failed",
        interpretation="unavailable until every numerical gate passes",
        error={
            "stage": "A native normal",
            "type": "ValueError",
            "message": "invalid returned arrays",
        },
    )
    block = r["models"]["A"]
    block.update(
        profiles={"native-normal": {"failed_operand": {"nonfinite": "NaN"}}},
        node_forces=[],
        numerical_comparison=[],
    )
    r["models"] = {"A": block}
    r["signed_model_differences"] = []
    r["calls"] = r["calls"][:24]
    r["calls"][-1]["returned"] = False
    r["counts"].update(
        native_arcs_attempted=1,
        native_arcs_returned=1,
        native_arcs_completed=0,
        native_guard_reads_attempted=3,
        native_guard_reads_returned=3,
        oracle={
            "rhs_attempted": 0,
            "rhs_completed": 0,
            "states_attempted": 21,
            "states_completed": 21,
        },
    )
    for key in (
        "oracle_solves_attempted",
        "oracle_solves_returned",
        "oracle_solves_completed",
    ):
        r[key] = 0
    result = audit.check_saved(r, bundle, lambda: None)
    assert len(result["unavailable"]) == 1 and not result["study_verified"]
    r["error"]["stage"] = "A oracle normal"
    with pytest.raises(ValueError, match="nonfailing profile"):
        audit.check_saved(r, bundle, lambda: None)


def test_signed_sensitivity_is_3d_and_rejects_equal_norm_wrong_sign() -> None:
    vectors = [
        [float(j), 2.0 * j, -3.0 * j, 0.1 * j, -0.2 * j, 0.3 * j] for j in range(7)
    ]
    zero = [[0.0] * 6 for _ in range(7)]
    states = {
        "A": {"native-tight": zero, "oracle-tight": zero},
        "B": {"native-tight": vectors, "oracle-tight": vectors},
    }
    rows = [
        {
            "epoch_tdb_s": t,
            "native_B_minus_A": delta(zero[j], vectors[j]),
            "oracle_B_minus_A": delta(zero[j], vectors[j]),
            "oracle_minus_native_sensitivity": delta(vectors[j], vectors[j]),
            "gate": True,
        }
        for j, t in enumerate(audit.core.OFFSETS)
    ]
    bundle = {"nodes_tdb_s": list(audit.core.OFFSETS)}
    assert audit.sensitivity(rows, states, bundle, True)[1]
    rows[-1]["native_B_minus_A"]["right_minus_left_si"] = [-v for v in vectors[-1]]
    with pytest.raises(ValueError, match="signed"):
        audit.sensitivity(rows, states, bundle, True)


def test_readonly_partial_file_audit_is_never_a_verified_study(tmp_path: Path) -> None:
    path = tmp_path / "failed.json"
    path.write_text(json.dumps(failed_setup()))
    result = audit.audit_file(path, clock=lambda: 0.0, start_s=0.0)
    assert result["audit_status"] == "partial" and not result["study_verified"]
    assert result["audit_mode"] == "injected-test" and result["native_calls"] == 0
    assert result["evidence_sha256"] == audit.files.digest(path)
    assert len(result["audit_revision"]) == 40


def test_relabelled_injected_fixture_cannot_bypass_real_frozen_input_binding(
    tmp_path: Path,
) -> None:
    report, _ = make_report()
    report["adapter_mode"] = "reference"
    path = tmp_path / "forged.json"
    path.write_text(json.dumps(report))
    result = audit.audit_file(path, clock=lambda: 0.0, start_s=0.0)
    assert result["audit_status"] == "rejected" and not result["study_verified"]
    assert "frozen wire inputs" in result["error"]["message"]
    report["adapter_mode"] = "injected-test"
    path.write_text(json.dumps(report))
    assert (
        "injected study"
        in audit.audit_file(path, clock=lambda: 0.0, start_s=0.0)["error"]["message"]
    )


@pytest.mark.parametrize(
    "raw", ['{"status":"failed","status":"passed"}', '{"bad":NaN}', '{"x":1e400}', "[]"]
)
def test_malformed_file_is_rejected_with_finite_diagnostic(
    tmp_path: Path, raw: str
) -> None:
    path = tmp_path / "bad.json"
    path.write_text(raw)
    r = audit.audit_file(path, clock=lambda: 0.0, start_s=0.0)
    assert r["audit_status"] == "rejected" and not r["study_verified"]
    json.dumps(r, allow_nan=False)


def test_missing_file_expired_budget_and_helper_drift_stop_without_work(
    tmp_path: Path, monkeypatch: Any
) -> None:
    path = tmp_path / "missing"
    r = audit.audit_file(path, clock=lambda: 11.0, start_s=0.0)
    assert "deadline" in r["error"]["message"] and "evidence_sha256" not in r
    r = audit.audit_file(path, clock=lambda: 0.0, start_s=0.0)
    assert r["error"]["type"] == "FileNotFoundError"
    monkeypatch.setitem(audit.PINS, "0144-short-coast-audit.py", "0" * 64)
    r = audit.audit_file(path, clock=lambda: 0.0, start_s=0.0)
    assert "prepared offline helper" in r["error"]["message"]


def test_invalid_saved_identity_is_not_ignored_on_partial_evidence(
    tmp_path: Path,
) -> None:
    report = failed_setup()
    report["identity"] = {}
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(report))
    r = audit.audit_file(path, clock=lambda: 0.0, start_s=0.0)
    assert r["audit_status"] == "rejected" and "snapshot field" in r["error"]["message"]


def test_real_execute_in_fresh_process_is_zero_native_exclusive_and_finite(
    tmp_path: Path,
) -> None:
    source, output = tmp_path / "failed.json", tmp_path / "audit.json"
    source.write_text(json.dumps(failed_setup()))
    code = f"import runpy,sys;m=runpy.run_path({str(PATH)!r});from pathlib import Path;r=m['execute'](Path({str(source)!r}),Path({str(output)!r}));assert r['audit_status']=='partial' and not r['study_verified'];assert not any(k.startswith(('numpy','scipy','spiceypy','tudatpy','space_nav')) for k in sys.modules)"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
    before = output.read_bytes()
    saved = json.loads(before)
    assert saved["finalization_gate"] == "passed" and saved["native_calls"] == 0
    again = subprocess.run([sys.executable, "-c", code], capture_output=True)
    assert again.returncode != 0 and b"FileExistsError" in again.stderr
    assert output.read_bytes() == before


def test_fresh_guard_happens_before_output_creation(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setitem(sys.modules, "numpy.fake_already_loaded", object())
    path = tmp_path / "unused"
    with pytest.raises(ValueError, match="fresh process"):
        audit.execute(tmp_path / "absent", path)
    assert not path.exists()


def test_finalization_overrun_preserves_first_error_and_revokes_success() -> None:
    value = [0.0]

    class LateStream(io.StringIO):
        def flush(self) -> None:
            value[0] = 11.0

    r = {
        "audit_status": "passed",
        "study_verified": True,
        "error": {"type": "ValueError", "message": "first"},
    }
    stream = LateStream()
    result = audit.save(r, stream, audit.Budget(lambda: value[0], 0.0))
    assert result["audit_status"] == "rejected" and not result["study_verified"]
    assert result["first_error"]["message"] == "first"
    assert result["actual_elapsed_after_flush_s"] == 11.0
    assert json.loads(stream.getvalue()) == result


def test_write_failure_is_not_reported_as_saved_success() -> None:
    class Broken(io.StringIO):
        def write(self, value: str) -> int:
            raise OSError("disk fixture")

    with pytest.raises(OSError, match="disk fixture"):
        audit.save(
            {"audit_status": "passed", "study_verified": True},
            Broken(),
            audit.Budget(lambda: 0.0, 0.0),
        )
