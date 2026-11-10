"""Synthetic force and evidence fixtures for ADR0175; no archived force work."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal, localcontext
from fractions import Fraction
from math import inf, nextafter
from pathlib import Path
import sys
from typing import Any

import pytest

_EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
sys.path[:0] = [str(_EXPERIMENTS / n) for n in ("0176", "0170", "0167")]

from ariadna_paired_moon_math import CAPS, ORDINALS, analyze  # noqa: E402
from ariadna_split_common import Recorder  # noqa: E402

_GM = 4_000_000_000_000.0
_T0 = float(2**30)
_DISTANCE_M = 2_000_000
_EARTH_X_KM = 100_000_000.0


def _strings(x: Fraction | int) -> list[str]:
    return [str(x), "0", "0"]


def _archived_force(x: Fraction, d0: Fraction, d2: Fraction) -> dict[str, Any]:
    # Independent collinear oracle: a_x = GM / x²; acceleration y and z vanish.
    assert d2.denominator == 1
    archived_fields: dict[str, dict[str, list[str]]] = {}
    for precision in (80, 100):
        with localcontext() as context:
            context.prec = precision
            ref0 = (Decimal(d0.numerator) / Decimal(d0.denominator))**2
            ref3 = Decimal(d2.numerator**2)
            archived_fields[str(precision)] = {
                "d0": [str(Decimal.from_float(_GM) / ref0), "0", "0"],
                "d3": [str(Decimal.from_float(_GM) / ref3), "0", "0"],
            }
    return {
        "exact_spacecraft_m": _strings(x),
        "exact_spacecraft_with_rounded_drift_m": _strings(x),
        "exact_separations_m": {"d0": _strings(d0), "d2": _strings(d2), "d3": _strings(d2)},
        "rounded_separation_m": [float(d2), 0.0, 0.0],
        "binary64_m_s2": [_GM / d2.numerator**2, 0.0, 0.0],
        "reference_m_s2": archived_fields,
        "gates": {key: {"overall": {"passed": True}, "returned_geometry": {"passed": True}}
                  for key in archived_fields},
    }


def paired_bundle(*, geocentric_km: float = 400_000.0, near_gate: bool = False) -> dict[str, Any]:
    """Eleven analytic pairs with coepoch duplicates and signed time corrections."""
    e, g = _EARTH_X_KM, geocentric_km
    p_base = 1000 * (e + g)
    r0 = p_base - _DISTANCE_M
    v0 = (1.0, -0.0, 0.0)
    v_b = (-1.0, -0.0, 0.0)
    offsets = (1.0, 2.0, 3.0, 4.0, 5.0 - 2.0**-24, 1.0, 2.0, 3.0, 4.0, 6.0 + 2.0**-24, 7.0)
    rows = []
    for i, (ordinal, s) in enumerate(zip(ORDINALS, offsets, strict=True)):
        hi = _T0 + s
        exact = Fraction(_T0) + Fraction(s)
        lo = float(exact - Fraction(hi))
        drift = [value * s for value in v0]
        c = [value * lo for value in v_b]
        q_x = c[0] - drift[0] + (i % 4 if i < 5 else i % 4 + 1)
        x = Fraction(r0) + Fraction(drift[0]) + Fraction(q_x)
        d2 = Fraction(p_base) + Fraction(c[0]) - x
        extra = Fraction(499, 50_000_000) if near_gate and i == 0 else Fraction(0)
        # Shift the exact reference at both times, preserving its signed increment.
        p_hi = Fraction(p_base) + extra
        p_t = p_hi + Fraction(c[0])
        d0 = p_t - x
        rows.append({
            "archive": {
                "observation_ordinal": ordinal, "profile": "normal" if i < 5 else "tighter",
                "kind": "rhs" if ordinal in (11, 25, 27) else "output", "index": i,
                "source_mode": "proxy", "status": "passed", "elapsed_s": s, "hi_tdb_s": hi,
                "lo_s": lo, "exact_tdb_s": str(exact),
                "motion": {"q_m": [q_x, 0.0, 0.0], "w_m_s": [float(i), 0.0, 0.0], "drift_m": drift,
                           "rephasing_m": c, "saved_moon_velocity_m_s": list(v_b)},
                "time_increment": {"reference_increment_m": _strings(Fraction(c[0])),
                                   "signed_error_m": _strings(0), "error_squared_m2": "0", "passed": True},
                "raw_states_km_km_s": {"E": [e, 0.0, 0.0, 0.0, 0.0, 0.0],
                                       "B": [e + g, 0.0, 0.0, -0.001, -0.0, 0.0]},
                "reference_states_si": {"hi": {"B": [*_strings(p_hi), "-1", "0", "0"]},
                                        "exact": {"B": [*_strings(p_t), "-1", "0", "0"]}},
                "geocentric_position_km": [g, 0.0, 0.0],
                "static_force": _archived_force(x, d0, d2),
            },
            "captured_state_km_km_s": [nextafter(g, -inf), 0.0, 0.0, 99.0, 1.0, 2.0],
        })
    return {"initial": {"epoch_tdb_s": _T0, "position_m": [r0, 0.0, 0.0], "velocity_m_s": list(v0)},
            "gm_m3_s2": _GM, "radius_m": 1_737_400.0, "rows": rows,
            "identity": {"fixture": "analytic collinear"}}


def _run(bundle: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    analyze(bundle, report, Recorder(report, CAPS, 0.0, 10.0, clock=lambda: 0.0))
    return report


def test_collinear_exact_source_step_and_field() -> None:
    report = _run(paired_bundle())
    assert report["status"] == "passed" and report["outcome"] == "confirmed"
    assert report["unavailable"] == []
    assert tuple(row["observation_ordinal"] for row in report["rows"]) == ORDINALS
    assert report["counts"] == {name: dict.fromkeys(("attempted", "returned", "completed"), cap)
                                for name, cap in CAPS.items()}
    row = report["rows"][0]
    step = -1000 * (Fraction(400_000.0) - Fraction(nextafter(400_000.0, -inf)))
    assert row["signed_source_step_m"] == (step, 0, 0)
    assert row["exact_separations_m"]["measured_d2"] == (_DISTANCE_M + step, 0, 0)
    rounded = float(_DISTANCE_M + step)
    assert row["binary64_m_s2"]["measured"] == (_GM / (rounded * rounded), 0.0, 0.0)
    assert row["signed_delta_acceleration_m_s2"] == (Fraction(_GM / (rounded * rounded)) - 1, 0, 0)
    assert row["attribution_passed"] and row["precision"]["passed"]
    with localcontext() as context:
        context.prec = 100
        exact_distance = Decimal(_DISTANCE_M) + Decimal(step.numerator) / Decimal(step.denominator)
        expected = Decimal.from_float(_GM) / exact_distance**2 - 1
        assert abs(row["attribution"]["100"]["signed_source_m_s2"][0] - expected) <= Decimal("1e-96")
    assert row["source_step_masked_by_rounding"] is False


def test_small_source_step_is_masked_by_the_original_rounding() -> None:
    report = _run(paired_bundle(geocentric_km=1.0))
    assert report["status"] == "passed"
    row = report["rows"][0]
    assert row["signed_source_step_m"][0] != 0
    assert row["same_rounded_separation_bits"] and row["same_acceleration_bits"]
    assert row["source_step_masked_by_rounding"]
    assert row["signed_delta_acceleration_m_s2"] == (0, 0, 0)
    assert row["attribution"]["100"]["signed_source_m_s2"][0] != 0


def test_duplicated_hi_keeps_distinct_motion_and_signs() -> None:
    rows = _run(paired_bundle())["rows"]
    assert rows[0]["hi_tdb_s"] == rows[5]["hi_tdb_s"]
    assert rows[0]["signed_source_step_m"] == rows[5]["signed_source_step_m"]
    assert rows[0]["exact_spacecraft_m"] != rows[5]["exact_spacecraft_m"]
    assert rows[0]["binary64_m_s2"] != rows[5]["binary64_m_s2"]
    assert rows[4]["lo_s"] < 0 < rows[9]["lo_s"]
    assert rows[4]["motion"]["rephasing_m"][0] > 0 > rows[9]["motion"]["rephasing_m"][0]
    assert rows[0]["motion"]["rephasing_m"][0].hex() == "-0x0.0p+0"


def test_near_limit_measured_overall_flips_and_all_other_pairs_remain() -> None:
    report = _run(paired_bundle(near_gate=True))
    assert report["status"] == "failed" and report["outcome"] == "negative"
    assert report["unavailable"] == [] and "stopped" not in report
    row = report["rows"][0]
    assert row["outcome"] == "negative" and row["precision"]["classifications_stable"]
    for precision in ("80", "100"):
        assert row["gate_flips"][precision] == {"overall": True, "returned_geometry": False}
        assert row["gates"][precision]["proxy"]["overall"]["signed_margin_m_s2"] > 0
        assert row["gates"][precision]["measured"]["overall"]["signed_margin_m_s2"] < 0
    assert all(row["outcome"] == "confirmed" for row in report["rows"][1:])


class _PrecisionFault(Recorder):
    def call(self, operation: str, api: str, args: list[Any], invoke: Callable[[], Any],
             validate: Callable[[Any], None] | None = None) -> Any:
        if operation == "decimal_field" and args[:3] == [ORDINALS[0], "measured_d3", 80]:
            def fault() -> tuple[Decimal, ...]:
                x, y, z = invoke()
                return (x + Decimal("0.001"), y, z)
            return super().call(operation, api, args, fault, validate)
        return super().call(operation, api, args, invoke, validate)


def test_precision_instability_is_not_a_gate_verdict() -> None:
    report: dict[str, Any] = {}
    analyze(paired_bundle(), report, _PrecisionFault(report, CAPS, 0.0, 10.0, clock=lambda: 0.0))
    assert report["status"] == "failed" and report["outcome"] == "unresolved"
    assert report["rows"][0]["outcome"] == "unresolved"
    assert report["rows"][0]["precision"]["classifications_stable"] is False
    assert report["unavailable"] == [] and "stopped" not in report


@pytest.mark.parametrize("mutation,problem", [
    ("ordinal", "frozen pair order"), ("coepoch", "frozen exact coepoch"),
    ("zero", "signed binary64 product"), ("drift", "signed binary64 product"),
    ("domain", "exterior"), ("proxy_geometry", "proxy separation replay"),
    ("proxy_bits", "proxy acceleration bit replay"), ("proxy_reference", "proxy reference"),
    ("proxy_gate", "proxy overall gate replay"), ("missing_step", "no geocentric position bit miss"),
    ("nonfinite", "expected finite number"),
])
def test_invalid_prerequisite_preserves_completed_prefix(mutation: str, problem: str) -> None:
    bundle = paired_bundle()
    pair = bundle["rows"][1]
    row = pair["archive"]
    if mutation == "ordinal":
        row["observation_ordinal"] = 999
    elif mutation == "coepoch":
        row["hi_tdb_s"] += 1.0
    elif mutation == "zero":
        row["motion"]["rephasing_m"][0] = 0.0
    elif mutation == "drift":
        row["motion"]["drift_m"][0] += 1.0
    elif mutation == "domain":
        # First pair's radius is larger than the second's.
        bundle["radius_m"] = 1_999_999.5
    elif mutation == "proxy_geometry":
        row["static_force"]["exact_separations_m"]["d2"][0] = "0"
    elif mutation == "proxy_bits":
        row["static_force"]["binary64_m_s2"][1] = -0.0
    elif mutation == "proxy_reference":
        row["static_force"]["reference_m_s2"]["80"]["d0"][0] = "2"
    elif mutation == "proxy_gate":
        row["static_force"]["gates"]["80"]["overall"]["passed"] = False
    elif mutation == "missing_step":
        pair["captured_state_km_km_s"][:3] = row["geocentric_position_km"]
    elif mutation == "nonfinite":
        pair["captured_state_km_km_s"][2] = inf

    report: dict[str, Any] = {}
    with pytest.raises(ValueError, match=problem):
        analyze(bundle, report, Recorder(report, CAPS, 0.0, 10.0, clock=lambda: 0.0))
    assert report["status"] == "failed" and report["outcome"] == "incomplete"
    assert report["unavailable"] == list(ORDINALS[1:])
    assert report["rows"][0]["outcome"] == "confirmed"
    assert report["stopped"]["observation_ordinal"] == ORDINALS[1]
    assert report["error"] == report["stopped"]


def test_failed_call_cap_preserves_partial_pair_and_prefix() -> None:
    report: dict[str, Any] = {}
    caps = {**CAPS, "decimal_field": 11}
    with pytest.raises(ValueError, match="call cap"):
        analyze(paired_bundle(), report, Recorder(report, caps, 0.0, 10.0, clock=lambda: 0.0))
    assert report["counts"]["decimal_field"]["attempted"] == 11
    assert [row["outcome"] for row in report["rows"]] == ["confirmed", "incomplete"]
    assert set(report["rows"][1]["reference_m_s2"]["80"]) == {"d0"}
    assert report["unavailable"] == list(ORDINALS[1:])


def test_later_input_failure_keeps_earliest_numerical_miss() -> None:
    bundle = paired_bundle(near_gate=True)
    bundle["rows"][2]["archive"]["source_mode"] = "measured"
    report: dict[str, Any] = {}
    with pytest.raises(ValueError, match="archived proxy row did not pass"):
        analyze(bundle, report, Recorder(report, CAPS, 0.0, 10.0, clock=lambda: 0.0))
    assert report["outcome"] == "incomplete"
    assert report["error"]["observation_ordinal"] == ORDINALS[0]
    assert report["error"]["message"] == "measured force gate failed: overall"
    assert report["stopped"]["observation_ordinal"] == ORDINALS[2]
    assert report["unavailable"] == list(ORDINALS[2:])


def test_three_axis_field_has_independent_known_norm_and_direction() -> None:
    bundle = paired_bundle()
    archive = bundle["rows"][0]["archive"]
    separation = (600_000, -800_000, 2_400_000)
    radius = 2_600_000
    assert sum(value * value for value in separation) == radius**2
    initial = bundle["initial"]
    centre = int(initial["position_m"][0]) + _DISTANCE_M
    x = (centre - separation[0], -separation[1], -separation[2])
    archive["motion"]["q_m"] = [float(target) - initial["position_m"][i] - archive["motion"]["drift_m"][i]
                                for i, target in enumerate(x)]
    saved = archive["static_force"]
    saved["exact_spacecraft_m"] = saved["exact_spacecraft_with_rounded_drift_m"] = list(map(str, x))
    saved["exact_separations_m"] = {name: list(map(str, separation)) for name in ("d0", "d2", "d3")}
    saved["rounded_separation_m"] = list(map(float, separation))
    saved["binary64_m_s2"] = [_GM * (d / radius) / radius**2 for d in separation]
    for precision in (80, 100):
        with localcontext() as context:
            context.prec = precision
            expected = [str(Decimal.from_float(_GM) * Decimal(d) / Decimal(radius**3)) for d in separation]
            saved["reference_m_s2"][str(precision)] = {"d0": expected, "d3": expected}
    row = _run(bundle)["rows"][0]
    assert row["outcome"] == "confirmed"
    assert row["rho_m"]["proxy"] == radius
    assert tuple(v > 0 for v in row["binary64_m_s2"]["measured"]) == (True, False, True)
    assert row["gates"]["100"]["proxy"]["overall"]["error_norm_m_s2"] < Decimal("1e-15")
