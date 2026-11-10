"""ADR0172 exact comparisons on artificial states only."""

from __future__ import annotations

from fractions import Fraction
from math import inf, nan, nextafter
from pathlib import Path
import sys
from typing import Any

import pytest

_EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
sys.path[:0] = [str(_EXPERIMENTS / "0173"), str(_EXPERIMENTS / "0167")]

import ariadna_moon_holdout_analysis as holdout  # noqa: E402
from ariadna_split_common import Recorder  # noqa: E402


def synthetic_analysis_inputs() -> tuple[dict[str, Any], list[list[float]]]:
    """Give one exact geocentric state at each of 16 synthetic epochs."""
    state = [1.0, -2.0, 0.0, 0.125, -0.25, 0.0]
    epochs = [
        {
            "hi_tdb_s": 1.0e9 + 2 * i,
            "observation_ordinals": [i, 16 + i] if i < 5 else [i],
            "reference_si": ["1000", "-2000", "0", "125", "-250", "0"],
            "proxy_position_km": state[:3],
            "earth_ssb_km_km_s": [float(2**30), 16.0, 0.0, 0.0, 0.0, 0.0],
            "moon_ssb_km_km_s": [float(2**30 + 1), 14.0, 0.0, 0.0, 0.0, 0.0],
        }
        for i in range(16)
    ]
    return {"epochs": epochs}, [state.copy() for _ in epochs]


def _analyze(bundle: dict[str, Any], states: list[list[float]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    holdout.analyze(bundle, states, report, Recorder(report, holdout.ANALYSIS_CAPS, 0.0, 10.0, clock=lambda: 0.0))
    return report


def test_complete_holdout_checks_every_epoch_once() -> None:
    bundle, states = synthetic_analysis_inputs()
    report = _analyze(bundle, states)
    assert report["status"] == "passed" and not report["unavailable"]
    assert report["native_calls"] == report["force_evaluations"] == report["trajectory_propagations"] == 0
    assert report["checks"]["proxy_position_bits"] == report["checks"]["archived_closure_bits"] == {
        "checked": 48, "passed": 48, "expected": 48,
    }
    assert report["checks"]["state_parity"] == {"checked": 16, "passed": 16, "expected": 16}
    assert report["counts"]["epoch"] == {"attempted": 16, "returned": 16, "completed": 16}
    assert [entry["args"] for entry in report["ledger"]] == [
        [i, row["hi_tdb_s"]] for i, row in enumerate(bundle["epochs"])
    ]
    assert report["rows"][0]["observation_ordinals"] == [0, 16]
    assert all(report["verdicts"].values())


@pytest.mark.parametrize(("position_scale", "velocity_scale", "expected"), [
    (Fraction(1), Fraction(1), (True, True)),
    (Fraction(1001, 1000), Fraction(999, 1000), (False, True)),
    (Fraction(999, 1000), Fraction(1001, 1000), (True, False)),
])
def test_exact_euclidean_limits(
    position_scale: Fraction, velocity_scale: Fraction, expected: tuple[bool, bool],
) -> None:
    bundle, states = synthetic_analysis_inputs()
    # Two residuals in each block give exact 3-4-5 triangles at the limits.
    error = [position_scale * Fraction(3, 5000), position_scale * Fraction(4, 5000), Fraction(),
             velocity_scale * Fraction(3, 5_000_000), velocity_scale * Fraction(4, 5_000_000), Fraction()]
    bundle["epochs"][0]["reference_si"] = [
        str(Fraction(x) - y) for x, y in zip(("1000", "-2000", "0", "125", "-250", "0"), error, strict=True)
    ]
    report = _analyze(bundle, states)
    parity = report["rows"][0]["parity"]
    assert (parity["position_passed"], parity["velocity_passed"]) == expected
    assert parity["position_error_squared_m2"] == (position_scale / 1000) ** 2
    assert parity["velocity_error_squared_m2_s2"] == (velocity_scale / 1_000_000) ** 2
    assert report["verdicts"]["proxy_position_bits"] and report["verdicts"]["archived_closure_bits"]
    assert len(report["rows"]) == 16 and not report["unavailable"]


def test_one_ulp_miss_can_pass_parity_and_archived_closure() -> None:
    bundle, states = synthetic_analysis_inputs()
    states[2][0] = nextafter(1.0, inf)
    report = _analyze(bundle, states)
    row = report["rows"][2]
    assert row["parity"]["passed"] and row["archived_closure"]["passed"]
    assert row["proxy_position"]["bit_matches"] == [False, True, True]
    assert row["proxy_position"]["signed_captured_minus_proxy_m"][0] == Fraction(1000, 2**52)
    assert report["error"]["epoch_index"] == 2 and report["status"] == "failed"
    assert report["verdicts"]["state_parity"] and not report["verdicts"]["proxy_position_bits"]
    assert len(report["rows"]) == 16 and not report["unavailable"]


def test_signed_zero_is_not_identical_position() -> None:
    bundle, states = synthetic_analysis_inputs()
    states[0][2] = -0.0
    report = _analyze(bundle, states)
    row = report["rows"][0]
    assert row["proxy_position"]["captured_km_hex"][2] == "-0x0.0p+0"
    assert row["proxy_position"]["archived_proxy_km_hex"][2] == "0x0.0p+0"
    assert row["proxy_position"]["signed_captured_minus_proxy_m"][2] == 0
    assert row["proxy_position"]["bit_matches"] == [True, True, False]
    assert row["parity"]["passed"] and row["archived_closure"]["passed"]


def test_archived_closure_remains_separate_from_proxy_identity() -> None:
    bundle, states = synthetic_analysis_inputs()
    bundle["epochs"][4]["moon_ssb_km_km_s"][1] = nextafter(14.0, inf)
    report = _analyze(bundle, states)
    row = report["rows"][4]
    assert row["parity"]["passed"] and row["proxy_position"]["passed"]
    assert row["archived_closure"]["bit_matches"] == [True, False, True]
    assert row["archived_closure"]["signed_archived_moon_minus_exact_legs_m"][1] == Fraction(1000, 2**49)
    assert report["status"] == "failed"
    assert report["verdicts"]["proxy_position_bits"] and not report["verdicts"]["archived_closure_bits"]


def test_archived_closure_rounds_ties_to_even_and_exact_zero_to_positive() -> None:
    bundle, states = synthetic_analysis_inputs()
    half_step = 2.0**-53
    states[0][:3] = [half_step, half_step, 1.0]
    epoch = bundle["epochs"][0]
    epoch["proxy_position_km"] = states[0][:3]
    epoch["reference_si"][:3] = [str(Fraction(1000, 2**53)), str(Fraction(1000, 2**53)), "1000"]
    epoch["earth_ssb_km_km_s"][:3] = [1.0, 1.0 + 2.0**-52, -1.0]
    epoch["moon_ssb_km_km_s"][:3] = [1.0, 1.0 + 2.0**-51, 0.0]
    report = _analyze(bundle, states)
    closure = report["rows"][0]["archived_closure"]
    assert report["status"] == "passed"
    assert closure["rounded_earth_plus_captured_moon_km_hex"] == [
        "0x1.0000000000000p+0", "0x1.0000000000002p+0", "0x0.0p+0",
    ]
    assert closure["signed_archived_moon_minus_exact_legs_m"] == (
        -Fraction(1000, 2**53), Fraction(1000, 2**53), Fraction(),
    )


@pytest.mark.parametrize(("key", "bad"), [
    ("reference_si", ["1/0"] * 6),
    ("reference_si", ["0/1"] * 6),
    ("proxy_position_km", [0.0, 1.0, nan]),
    ("earth_ssb_km_km_s", [False, 0.0, 0.0, 0.0, 0.0, 0.0]),
    ("moon_ssb_km_km_s", [0.0] * 5),
])
def test_malformed_operand_stops_after_valid_prefix(key: str, bad: object) -> None:
    bundle, states = synthetic_analysis_inputs()
    bundle["epochs"][2][key] = bad
    report = _analyze(bundle, states)
    assert report["status"] == "failed" and report["analysis_phase"] == "incomplete"
    assert len(report["rows"]) == 2 and report["error"]["epoch_index"] == 2
    assert report["unavailable"] == list(range(2, 16))
    assert report["counts"]["epoch"] == {"attempted": 3, "returned": 2, "completed": 2}
    assert report["verdicts"]["state_parity"] is None


def test_late_result_is_retained_but_does_not_count_as_a_completed_epoch(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle, states = synthetic_analysis_inputs()
    original = holdout._compare_epoch
    elapsed = 0.0

    def compare(index: int, hi_tdb_s: float, epoch: dict[str, Any], raw: list[float]) -> dict[str, Any]:
        nonlocal elapsed
        result = original(index, hi_tdb_s, epoch, raw)
        if index == 1:
            elapsed = 10.01
        return result

    monkeypatch.setattr(holdout, "_compare_epoch", compare)
    report: dict[str, Any] = {}
    holdout.analyze(bundle, states, report, Recorder(report, holdout.ANALYSIS_CAPS, 0.0, 10.0, clock=lambda: elapsed))
    assert report["status"] == "failed" and len(report["rows"]) == 1
    assert report["error"]["epoch_index"] == 1 and "deadline" in report["error"]["message"]
    assert report["counts"]["epoch"] == {"attempted": 2, "returned": 2, "completed": 1}
    assert report["ledger"][-1]["raw"]["parity"]["passed"] is True
    assert "completed_s" not in report["ledger"][-1] and report["unavailable"] == list(range(1, 16))


def test_first_numerical_failure_is_kept_when_a_later_operand_is_invalid() -> None:
    bundle, states = synthetic_analysis_inputs()
    states[0][2] = -0.0
    states[2].pop()
    report = _analyze(bundle, states)
    assert report["error"]["epoch_index"] == 0 and report["error"]["type"] == "NumericalCheck"
    assert report["stopped"]["epoch_index"] == 2 and report["stopped"]["type"] == "ValueError"
    assert report["analysis_phase"] == "incomplete" and report["unavailable"] == list(range(2, 16))
    assert report["verdicts"]["proxy_position_bits"] is False and report["verdicts"]["state_parity"] is None
