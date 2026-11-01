"""Synthetic step tracing and event search; never replay the failed R5 study."""

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
PATH = ROOT / "docs/adr/experiments/0150-synthetic-step-diagnostic.py"
spec = importlib.util.spec_from_file_location("synthetic_step_tests", PATH)
assert spec is not None and spec.loader is not None
diag = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = diag
spec.loader.exec_module(diag)

RADIUS_M = 1837400.0
GM_M3_S2 = 4902800121846.8
ZERO = (0.0,) * 6


def test_import_is_lazy_without_native_or_scientific_modules() -> None:
    code = f"import runpy,sys;runpy.run_path({str(PATH)!r});assert not any(k.startswith(('numpy','scipy','tudatpy','spiceypy','space_nav')) for k in sys.modules)"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)


def test_analytic_corrections_start_at_exact_zero() -> None:
    assert tuple(diag.analytic_state(0.0)) == ZERO
    assert diag.MODES == ("relative", "absolute-local", "absolute-rounded")


def test_analytic_corrections_match_independent_circle_at_ten_seconds() -> None:
    elapsed = 10.0
    omega = math.sqrt(GM_M3_S2 / RADIUS_M**3)
    angle = omega * elapsed
    speed = math.sqrt(GM_M3_S2 / RADIUS_M)
    expected = (
        -2 * RADIUS_M * math.sin(angle / 2) ** 2,
        RADIUS_M * math.sin(angle) - speed * elapsed,
        0.0,
        -speed * math.sin(angle),
        -2 * speed * math.sin(angle / 2) ** 2,
        0.0,
    )
    actual = tuple(diag.analytic_state(elapsed))
    assert math.dist(actual[:3], expected[:3]) <= 1e-9
    assert math.dist(actual[3:], expected[3:]) <= 1e-11


def test_all_fields_have_correct_initial_radial_acceleration() -> None:
    expected = (-GM_M3_S2 / RADIUS_M**2, 0.0, 0.0)
    for mode in diag.MODES:
        assert math.dist(diag.field(0.0, ZERO, mode), expected) <= 1e-15


def test_decimal_force_reference_matches_independent_local_geometry() -> None:
    elapsed = 0.2
    correction = (-0.4, 0.1, 0.2, 0.3, 0.0, -0.1)
    with localcontext() as context:
        context.prec = 80
        d = Decimal.from_float
        speed = math.sqrt(GM_M3_S2 / RADIUS_M)
        position = (
            d(RADIUS_M) + d(correction[0]),
            d(speed) * d(elapsed) + d(correction[1]),
            d(correction[2]),
        )
        radius = sum(x * x for x in position).sqrt()
        expected = tuple(-d(GM_M3_S2) * x / radius**3 for x in position)
        actual = diag.force_reference(elapsed, correction)
        assert len(actual) == 3 and all(isinstance(x, Decimal) for x in actual)
        assert sum(
            (x - y) ** 2 for x, y in zip(actual, expected, strict=True)
        ).sqrt() <= Decimal("1e-15")


def test_fractional_body_time_exposes_force_precision_asymmetry() -> None:
    elapsed = 0.2
    correction = diag.analytic_state(elapsed)
    reference = tuple(float(x) for x in diag.force_reference(elapsed, correction))
    relative = diag.field(elapsed, correction, "relative")
    rounded = diag.field(elapsed, correction, "absolute-rounded")
    assert math.dist(relative, reference) <= 1e-14
    assert math.dist(rounded, reference) > 1e-11
    assert math.dist(rounded, relative) > 1e-11


def test_integer_time_removes_only_the_body_timestamp_rounding() -> None:
    correction = diag.analytic_state(1.0)
    assert diag.field(1.0, correction, "absolute-local") == diag.field(
        1.0, correction, "absolute-rounded"
    )


@pytest.mark.parametrize(
    ("flags", "index"),
    [
        ([], None),
        ([False] * 8, None),
        ([True, False, False], 0),
        ([False, False, True, True], 2),
        ([False, False, False, True], 3),
        ([False, True, False, False, True], 1),
    ],
)
def test_binary_search_finds_first_recorded_failure_despite_recovery(
    flags: list[bool], index: int | None
) -> None:
    original = list(flags)
    result = diag.first_failure(flags)
    assert result["index"] == index
    assert result["previous_index"] == (
        index - 1 if index is not None and index else None
    )
    assert isinstance(result["probes"], list)
    assert len(result["probes"]) <= math.ceil(math.log2(len(flags) + 1)) + 1
    assert flags == original


def test_binary_search_rejects_nonboolean_flags() -> None:
    for flags in ([0, False], [True, 1], [None], ["bad"]):
        with pytest.raises((ValueError, TypeError)):
            diag.first_failure(flags)


def test_nonfinite_boolean_or_out_of_interval_times_are_rejected() -> None:
    for value in (True, float("nan"), float("inf"), -0.01, 10.01):
        with pytest.raises((ValueError, TypeError)):
            diag.analytic_state(value)
        with pytest.raises((ValueError, TypeError)):
            diag.field(value, ZERO, "relative")


def test_unknown_field_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        diag.field(0.2, ZERO, "unverified")


def test_invalid_correction_shapes_values_and_singularity_are_rejected() -> None:
    for value in ((0.0,) * 5, (True,) + (0.0,) * 5, (float("nan"),) + (0.0,) * 5):
        with pytest.raises((ValueError, TypeError)):
            diag.field(0.2, value, "relative")
    with pytest.raises((ValueError, TypeError)):
        diag.field(0.0, (-RADIUS_M, 0.0, 0.0, 0.0, 0.0, 0.0), "relative")


def test_relative_solver_finishes_and_matches_the_independent_analytic_gates() -> None:
    result = diag.run_case("relative")
    assert result["status"] == "finished" and result["final_t_s"] == 10.0
    assert result["rhs"] and result["trials"] and result["accepted"]
    assert result["nfev"] == len(result["rhs"])
    assert all(p["position_error_m"] <= 1e-6 for p in result["accepted"])
    assert all(p["velocity_error_m_s"] <= 1e-8 for p in result["accepted"])
    assert not any(p["analytic_bad"] for p in result["accepted"])
    assert result["first_events"]["analytic"]["index"] is None
    json.dumps(result, allow_nan=False)


def test_observing_trials_does_not_change_vanilla_solver_states_or_work() -> None:
    traced = diag.run_case("relative", traced=True)
    vanilla = diag.run_case("relative", traced=False)
    assert traced["status"] == vanilla["status"] == "finished"
    assert traced["final_t_s"] == vanilla["final_t_s"]
    assert traced["final_q"] == vanilla["final_q"]
    assert traced["nfev"] == vanilla["nfev"]
    assert traced["accepted"] == vanilla["accepted"]
    assert traced["rhs"] == vanilla["rhs"]
    assert vanilla["trials"] == []


def test_rhs_cap_preserves_available_partial_rows_without_claiming_completion() -> None:
    result = diag.run_case("relative", rhs_limit=2)
    assert result["status"] in ("capped", "failed")
    assert 0 < len(result["rhs"]) <= 2
    assert result["final_t_s"] < 10.0
    json.dumps(result, allow_nan=False)


def test_deadline_before_work_returns_finite_failed_diagnostic() -> None:
    def expired() -> None:
        raise RuntimeError("synthetic deadline")

    result = diag.run_case("relative", check=expired)
    assert result["status"] == "failed"
    assert not result["rhs"] and result["final_t_s"] < 10.0
    json.dumps(result, allow_nan=False)


def test_deadline_after_some_work_retains_rhs_rows() -> None:
    calls = 0

    def expire_later() -> None:
        nonlocal calls
        calls += 1
        if calls > 20:
            raise RuntimeError("synthetic deadline after work")

    result = diag.run_case("relative", check=expire_later)
    assert result["status"] == "failed"
    assert result["rhs"] and result["final_t_s"] < 10.0
    json.dumps(result, allow_nan=False)


def test_trial_cap_preserves_first_attempt_instead_of_repeating_solve() -> None:
    result = diag.run_case("relative", trial_limit=1)
    assert result["status"] in ("capped", "failed")
    assert len(result["trials"]) == 1
    assert result["final_t_s"] < 10.0


def test_trial_acceptance_and_error_components_match_pinned_estimator_meaning() -> None:
    result = diag.run_case("relative")
    for row in result["trials"]:
        assert row["accepted"] is (row["error_norm"] < 1.0)
        assert row["h_s"] > 0.0
        assert row["t_end_s"] == row["t_start_s"] + row["h_s"]
        assert (
            len(row["scale"])
            == len(row["error5_scaled"])
            == len(row["error3_scaled"])
            == 6
        )
        assert all(math.isfinite(v) and v > 0 for v in row["scale"])
        with localcontext() as context:
            context.prec = 80
            d = Decimal.from_float
            e5 = sum(d(float(x)) ** 2 for x in row["error5_scaled"])
            e3 = sum(d(float(x)) ** 2 for x in row["error3_scaled"])
            expected = (
                Decimal(0)
                if e5 == e3 == 0
                else abs(d(float(row["h_s"])))
                * e5
                / ((e5 + Decimal("0.01") * e3) * 6).sqrt()
            )
        assert math.isclose(
            row["error_norm"], float(expected), rel_tol=1e-12, abs_tol=1e-20
        )


def test_exclusive_output_does_not_overwrite_an_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "existing.json"
    output.write_bytes(b"preserve this evidence")
    code = f"import runpy;m=runpy.run_path({str(PATH)!r});from pathlib import Path;m['execute'](Path({str(output)!r}))"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True)
    assert result.returncode != 0
    assert b"FileExistsError" in result.stderr
    assert output.read_bytes() == b"preserve this evidence"


def test_cap_counts_attempts_separately_from_completed_force_records() -> None:
    result = diag.run_case("relative", rhs_limit=2)
    assert result["status"] == "capped"
    assert result["rhs_evaluations"] == 2
    assert result["callback_attempts"] == result["nfev"] == 3
    assert result["callbacks_without_force_record"] == 1
    assert result["failure_context"]["phase"] == "step"
    assert result["incomplete_trial"]["decision"] == "unavailable"


def test_constructor_failure_does_not_invent_solver_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = diag.field
    computed = False

    def field(*args: Any) -> Any:
        nonlocal computed
        value = original(*args)
        computed = True
        return value

    def check() -> None:
        if computed:
            raise RuntimeError("after first force")

    monkeypatch.setattr(diag, "field", field)
    result = diag.run_case("relative", check=check)
    assert result["status"] == "failed"
    assert result["nfev"] is None
    assert result["rhs_evaluations"] == result["callback_attempts"] == 1
    assert result["failure_context"]["phase"] == "constructor"
    assert "incomplete_trial" not in result


def test_after_accepted_failure_does_not_claim_an_incomplete_trial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = diag.analytic_state
    accepted = False

    def analytic(at: float) -> tuple[float, ...]:
        nonlocal accepted
        value = original(at)
        accepted = True
        return value

    def check() -> None:
        if accepted:
            raise RuntimeError("after accepted endpoint")

    monkeypatch.setattr(diag, "analytic_state", analytic)
    result = diag.run_case("relative", check=check)
    assert result["status"] == "failed" and len(result["accepted"]) == 1
    assert result["failure_context"]["phase"] == "after-accepted"
    assert "incomplete_trial" not in result
    assert result["final_t_s"] == result["accepted"][-1]["t_s"]


def test_execute_success_is_exclusive_and_finite_with_injected_cases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diag, "sys", SimpleNamespace(modules={}))
    monkeypatch.setattr(diag, "monotonic", lambda: diag.PROCESS_START)
    calls = []

    def case(mode: str, **kwargs: Any) -> dict[str, Any]:
        calls.append(mode)
        kwargs["check"]()
        return {
            "mode": mode,
            "status": "finished",
            "accepted": [{"analytic_bad": False}],
            "rhs_evaluations": 1,
        }

    monkeypatch.setattr(diag, "run_case", case)
    output = tmp_path / "trace.json"
    result = diag.execute(output)
    assert calls == list(diag.MODES)
    assert result["status"] == "finished" and result["finalization_gate"] == "passed"
    assert json.loads(output.read_text()) == result
    with pytest.raises(FileExistsError):
        diag.execute(output)


def test_late_flush_preserves_first_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(diag, "sys", SimpleNamespace(modules={}))
    flushed = False
    dump = json.dump

    def serialize(*args: Any, **kwargs: Any) -> None:
        nonlocal flushed
        dump(*args, **kwargs)
        flushed = True

    def fail(*args: Any, **kwargs: Any) -> None:
        raise ValueError("original failure")

    monkeypatch.setattr(diag, "run_case", fail)
    monkeypatch.setattr(diag.json, "dump", serialize)
    monkeypatch.setattr(
        diag, "monotonic", lambda: diag.PROCESS_START + (11.0 if flushed else 0.0)
    )
    output = tmp_path / "late.json"
    result = diag.execute(output)
    assert result["status"] == "partial" and result["finalization_gate"] == "failed"
    assert result["first_error"]["message"] == "original failure"
    assert result["error"]["message"] == "synthetic process deadline"
    assert json.loads(output.read_text()) == result
