"""Synthetic time compensation; no R5 reference execution or native queries."""

from __future__ import annotations

from decimal import Decimal, localcontext
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0152-compensated-time-diagnostic.py"
SPEC = importlib.util.spec_from_file_location("compensated_time_tests", PATH)
assert SPEC is not None and SPEC.loader is not None
candidate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = candidate
SPEC.loader.exec_module(candidate)
BASE = candidate.BASE
ZERO = (0.0,) * 6


def decimal_force(separation: tuple[Decimal, ...], mu: Decimal) -> tuple[Decimal, ...]:
    radius_squared = sum(x * x for x in separation)
    radius_cubed = radius_squared * radius_squared.sqrt()
    return tuple(mu * x / radius_cubed for x in separation)


def ideal_force(elapsed_s: float, q: list[float]) -> tuple[Decimal, ...]:
    d = Decimal.from_float
    return decimal_force(
        (
            -d(BASE.RADIUS_M) - d(q[0]),
            -d(BASE.SPEED) * d(elapsed_s) - d(q[1]),
            -d(q[2]),
        ),
        d(BASE.MU),
    )


@pytest.fixture
def saved_stages() -> list[dict[str, Any]]:
    path = ROOT / "docs/adr/experiments/0150-synthetic-trace.json"
    trace = json.loads(path.read_text())
    return trace["cases"][2]["rhs"][:13]


@pytest.mark.parametrize(
    ("epoch", "offset"),
    [
        (978995455.2304223, 0.0),
        (978995455.2304223, 1.0),
        (978995455.2304223, 10.0),
        (978995455.2304223, math.nextafter(1.0, math.inf)),
        (978995455.2304223, -0.2),
        (978995455.2304223, 0.05260015195876773),
        (978995455.2304223, 0.2),
        (1.5 * 2**30, 2**-24),
        (1.5 * 2**30, 2**-23),
    ],
)
def test_split_preserves_exact_binary64_input_sum(epoch: float, offset: float) -> None:
    high, low = candidate.split_epoch(epoch, offset)
    assert type(high) is float and type(low) is float
    assert high == epoch + offset
    with localcontext() as context:
        context.prec = 200
        d = Decimal.from_float
        assert d(high) + d(low) == d(epoch) + d(offset)
    assert abs(low) <= math.ulp(high) / 2


def test_split_rejects_boolean_nonfinite_and_nonnumeric_inputs() -> None:
    for value in (True, float("nan"), float("inf"), "1", None):
        with pytest.raises((ValueError, TypeError)):
            candidate.split_epoch(value, 1.0)
        with pytest.raises((ValueError, TypeError)):
            candidate.split_epoch(BASE.T0, value)


def test_split_rejects_overflow_instead_of_returning_nonfinite_parts() -> None:
    with pytest.raises((ValueError, OverflowError)):
        candidate.split_epoch(sys.float_info.max, sys.float_info.max)


def test_geometry_rejects_invalid_times() -> None:
    for value in (True, float("nan"), float("inf"), -0.1, 10.1):
        with pytest.raises((ValueError, TypeError)):
            candidate.sample_geometry(value, ZERO)


def test_geometry_rejects_invalid_corrections_and_source_collision() -> None:
    for q in ((0.0,) * 5, (True,) + (0.0,) * 5, (float("nan"),) + (0.0,) * 5):
        with pytest.raises((ValueError, TypeError)):
            candidate.sample_geometry(0.2, q)
    with pytest.raises((ValueError, TypeError)):
        candidate.sample_geometry(0.0, (-BASE.RADIUS_M, 0.0, 0.0, 0.0, 0.0, 0.0))


def test_initial_force_has_correct_radial_sign_and_si_magnitude() -> None:
    force = candidate.compensated_field(0.0, ZERO)
    expected = (-BASE.MU / BASE.RADIUS_M**2, 0.0, 0.0)
    assert math.dist(force, expected) <= 1e-15


@pytest.mark.parametrize("precision", [80, 100])
def test_saved_fractional_stages_match_independent_geometry_and_ideal_envelope(
    saved_stages: list[dict[str, Any]], precision: int
) -> None:
    with localcontext() as context:
        context.prec = precision
        d = Decimal.from_float
        for saved in saved_stages:
            sample = candidate.sample_geometry(saved["elapsed_s"], saved["q"])
            actual = tuple(d(x) for x in sample["force_m_s2"])
            geometry = decimal_force(
                tuple(d(x) for x in sample["separation_m"]), d(BASE.MU)
            )
            geometry_error = sum((x - y) ** 2 for x, y in zip(actual, geometry)).sqrt()
            assert geometry_error <= Decimal("1e-14")
            ideal = ideal_force(saved["elapsed_s"], saved["q"])
            ideal_error = sum((x - y) ** 2 for x, y in zip(actual, ideal)).sqrt()
            envelope = max(
                Decimal("1e-15"),
                Decimal("1e-11") * sum(x * x for x in ideal).sqrt(),
            )
            assert ideal_error <= envelope


def test_compensation_low_part_has_opposite_sign_to_saved_clock_error(
    saved_stages: list[dict[str, Any]],
) -> None:
    saved = saved_stages[1]
    sample = candidate.sample_geometry(saved["elapsed_s"], saved["q"])
    with localcontext() as context:
        context.prec = 200
        assert Decimal.from_float(sample["epoch_low_s"]) == -Decimal(
            saved["body_time_residual_s"]
        )
    assert sample["epoch_low_s"] > 0


def test_reversing_low_part_breaks_the_force_envelope(
    saved_stages: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    split = candidate.split_epoch

    def wrong_sign(epoch: object, elapsed: object) -> tuple[float, float]:
        high, low = split(epoch, elapsed)
        return high, -low

    monkeypatch.setattr(candidate, "split_epoch", wrong_sign)
    saved = saved_stages[1]
    force = candidate.compensated_field(saved["elapsed_s"], saved["q"])
    with localcontext() as context:
        context.prec = 100
        ideal = ideal_force(saved["elapsed_s"], saved["q"])
        error = sum(
            (Decimal.from_float(x) - y) ** 2 for x, y in zip(force, ideal)
        ).sqrt()
        envelope = max(
            Decimal("1e-15"),
            Decimal("1e-11") * sum(x * x for x in ideal).sqrt(),
        )
        assert error > envelope


def test_source_position_retains_the_rounded_provider_operands() -> None:
    sample = candidate.sample_geometry(0.2, ZERO)
    high, low = candidate.split_epoch(BASE.T0, 0.2)
    expected = tuple(
        math.fsum((origin, velocity * (high - BASE.T0)))
        for origin, velocity in zip(BASE.ORIGIN, BASE.VELOCITY)
    )
    assert sample["epoch_high_tdb_s"] == high
    assert sample["epoch_low_s"] == low
    assert tuple(sample["source_position_m"]) == expected
    assert tuple(sample["source_velocity_m_s"]) == BASE.VELOCITY
    assert sample["elapsed_s"] == 0.2 and tuple(sample["q"]) == ZERO
    json.dumps(sample, allow_nan=False)


def test_sub_coordinate_ulp_correction_can_be_lost_in_absolute_assembly() -> None:
    at = math.nextafter(1.0, math.inf)
    sample = candidate.sample_geometry(at, ZERO)
    correction_m = BASE.VELOCITY[0] * sample["epoch_low_s"]
    body_x_m = sample["source_position_m"][0]
    assert correction_m != 0
    assert abs(correction_m) < math.ulp(body_x_m) / 2
    assert body_x_m + correction_m == body_x_m


def test_private_adapter_restores_legacy_field_and_records_completed_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = candidate.load_base()
    field = engine.field
    original_base_field = BASE.field
    monkeypatch.setattr(candidate, "load_base", lambda: engine)
    before = (
        ROOT / "docs/adr/experiments/0150-synthetic-step-diagnostic.py"
    ).read_bytes()
    result = candidate.run_candidate(rhs_limit=2)
    assert engine.field is field
    assert BASE.field is original_base_field
    assert (
        ROOT / "docs/adr/experiments/0150-synthetic-step-diagnostic.py"
    ).read_bytes() == before
    assert result["mode"] == "compensated"
    assert result["internal_mode"] == "absolute-rounded"
    assert result["status"] == "capped"
    assert result["rhs_evaluations"] == 2
    assert result["synthetic_provider_calls"] == len(result["geometry_records"]) == 2
    assert result["callbacks_without_force_record"] == 1
    json.dumps(result, allow_nan=False)


def test_candidate_finishes_with_analytic_gates_and_predeclared_work_limit() -> None:
    result = candidate.run_candidate()
    assert result["status"] == "finished" and result["final_t_s"] == 10.0
    assert result["trials"][0]["accepted"]
    assert result["nfev"] == result["rhs_evaluations"] <= 241
    assert (
        result["synthetic_provider_calls"]
        == len(result["geometry_records"])
        == result["rhs_evaluations"]
    )
    assert all(not row["force_bad"] for row in result["rhs"])
    assert all(row["position_error_m"] <= 1e-6 for row in result["accepted"])
    assert all(row["velocity_error_m_s"] <= 1e-8 for row in result["accepted"])
    assert result["first_events"]["analytic"]["index"] is None


def test_observation_does_not_change_candidate_solver_state_or_work() -> None:
    traced = candidate.run_candidate(traced=True)
    vanilla = candidate.run_candidate(traced=False)
    assert traced["status"] == vanilla["status"] == "finished"
    for key in ("final_t_s", "final_q", "nfev", "rhs", "accepted", "geometry_records"):
        assert traced[key] == vanilla[key]
    assert vanilla["trials"] == []


def test_deadline_before_work_returns_finite_partial_result_and_restores_adapter() -> (
    None
):
    original = BASE.field

    def expired() -> None:
        raise RuntimeError("synthetic deadline")

    result = candidate.run_candidate(check=expired)
    assert result["status"] == "failed"
    assert result["rhs_evaluations"] == result["synthetic_provider_calls"] == 0
    assert result["geometry_records"] == []
    assert BASE.field is original
    json.dumps(result, allow_nan=False)


def test_import_remains_lazy_without_scientific_or_native_modules() -> None:
    code = f"import runpy,sys;runpy.run_path({str(PATH)!r});assert not any(k.startswith(('numpy','scipy','spiceypy','tudatpy','space_nav')) for k in sys.modules)"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)


def test_existing_output_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "retained.json"
    output.write_bytes(b"keep retained evidence")
    monkeypatch.setattr(candidate, "sys", SimpleNamespace(modules={}))
    with pytest.raises(FileExistsError):
        candidate.execute(output)
    assert output.read_bytes() == b"keep retained evidence"


def test_invalid_run_arguments_restore_the_private_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = candidate.load_base()
    field = engine.field
    monkeypatch.setattr(candidate, "load_base", lambda: engine)
    with pytest.raises(ValueError):
        candidate.run_candidate(rhs_limit=0)
    assert engine.field is field


def complete_case() -> dict[str, Any]:
    baseline = json.loads(
        (ROOT / "docs/adr/experiments/0150-synthetic-trace.json").read_text()
    )
    return {
        "mode": "compensated",
        "internal_mode": "absolute-rounded",
        "status": "finished",
        "final_t_s": 10.0,
        "final_q": baseline["cases"][0]["final_q"],
        "rhs_evaluations": 37,
        "rhs": [{"force_bad": False}],
        "accepted": [{"analytic_bad": False}],
        "trials": [{"accepted": True}],
    }


def test_execute_success_uses_one_candidate_and_saved_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(candidate, "sys", SimpleNamespace(modules={}))
    monkeypatch.setattr(candidate, "monotonic", lambda: candidate.PROCESS_START)
    calls = 0

    def run(**kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        kwargs["check"]()
        return complete_case()

    monkeypatch.setattr(candidate, "run_candidate", run)
    output = tmp_path / "candidate.json"
    result = candidate.execute(output)
    assert calls == 1
    assert result["status"] == "passed"
    assert all(result["scientific_gates"].values())
    assert all(result["behavioral_targets"].values())
    assert result["baseline_rhs"] == {
        "relative": 37,
        "absolute-local": 73,
        "absolute-rounded": 2413,
    }
    assert (
        result["spice_queries"]
        == result["tudat_propagations"]
        == result["r5_reference_replays"]
        == 0
    )
    assert result["real_ephemeris_fix_verified"] is False
    assert result["historical_r5_causality_proven"] is False
    assert result["finalization_gate"] == "passed"
    assert json.loads(output.read_text()) == result


def test_execute_retains_failed_force_gate_without_claiming_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(candidate, "sys", SimpleNamespace(modules={}))
    monkeypatch.setattr(candidate, "monotonic", lambda: candidate.PROCESS_START)
    case = complete_case()
    case["rhs"][0]["force_bad"] = True
    monkeypatch.setattr(candidate, "run_candidate", lambda **kwargs: case)
    output = tmp_path / "failed.json"
    result = candidate.execute(output)
    assert result["status"] == "failed"
    assert result["scientific_gates"]["all_retained_forces"] is False
    assert result["candidate"] == case
    assert result["finalization_gate"] == "passed"
    assert json.loads(output.read_text()) == result


def test_execute_retains_injected_candidate_error_as_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(candidate, "sys", SimpleNamespace(modules={}))
    monkeypatch.setattr(candidate, "monotonic", lambda: candidate.PROCESS_START)

    def fail(**kwargs: Any) -> dict[str, Any]:
        raise ValueError("injected candidate error")

    monkeypatch.setattr(candidate, "run_candidate", fail)
    output = tmp_path / "partial.json"
    result = candidate.execute(output)
    assert result["status"] == "partial"
    assert result["candidate"] is None
    assert result["scientific_gates"] is None
    assert result["error"]["message"] == "injected candidate error"
    assert json.loads(output.read_text()) == result


def test_one_shot_overrun_after_gate_evaluation_cannot_leave_passed_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(candidate, "sys", SimpleNamespace(modules={}))
    monkeypatch.setattr(candidate, "run_candidate", lambda **kwargs: complete_case())
    calls = 0

    def clock() -> float:
        nonlocal calls
        calls += 1
        # No fake RHS checks: the fourth outer check follows gate/status assignment.
        return candidate.PROCESS_START + (11.0 if calls == 4 else 0.0)

    monkeypatch.setattr(candidate, "monotonic", clock)
    output = tmp_path / "transient-deadline.json"
    result = candidate.execute(output)
    assert result["status"] == "partial"
    assert all(result["scientific_gates"].values())
    assert all(result["behavioral_targets"].values())
    assert result["candidate"] is not None
    assert result["error"]["message"] == "candidate process deadline"
    assert result["finalization_gate"] == "passed"
    assert calls >= 6
    assert json.loads(output.read_text()) == result


def test_reconciliation_failure_preserves_raw_case_geometry_and_restores_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = candidate.load_base()
    field = engine.field
    raw = {
        "status": "finished",
        "rhs_evaluations": 1,
        "rhs": [
            {
                "elapsed_s": 0.0,
                "q": list(ZERO),
                "force_m_s2": [1.0, 2.0, 3.0],
            }
        ],
    }

    def run_case(mode: str, **kwargs: Any) -> dict[str, Any]:
        engine.field(0.0, ZERO, mode)
        return raw

    monkeypatch.setattr(engine, "run_case", run_case)
    monkeypatch.setattr(candidate, "load_base", lambda: engine)
    result = candidate.run_candidate()
    assert result is raw
    assert result["status"] == "failed"
    assert result["failure_context"]["phase"] == "adapter-reconciliation"
    assert result["error"]["message"] == "completed saved operands reconciliation"
    assert result["rhs"][0]["force_m_s2"] == [1.0, 2.0, 3.0]
    assert len(result["geometry_records"]) == result["synthetic_provider_calls"] == 1
    assert result["geometry_records"][0]["force_m_s2"] != [1.0, 2.0, 3.0]
    assert engine.field is field
    json.dumps(result, allow_nan=False)


def test_three_dimensional_correction_matches_independent_local_field() -> None:
    q = [-0.4, 0.1, 0.2, 0.3, 0.0, -0.1]
    with localcontext() as context:
        context.prec = 100
        actual = candidate.compensated_field(0.2, q)
        reference = ideal_force(0.2, q)
        error = sum(
            (Decimal.from_float(x) - y) ** 2
            for x, y in zip(actual, reference, strict=True)
        ).sqrt()
        envelope = max(
            Decimal("1e-15"), Decimal("1e-11") * sum(x * x for x in reference).sqrt()
        )
        assert error <= envelope
        assert actual[2] < 0


def test_changed_baseline_source_is_rejected_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed = tmp_path / "changed.py"
    changed.write_text("raise RuntimeError('must not execute')")
    monkeypatch.setattr(candidate, "BASE_PATH", changed)
    with pytest.raises(ValueError, match="baseline helper identity"):
        candidate.load_base()
