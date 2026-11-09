"""Analytic ADR0166 fixtures; neither archived nor live ephemerides are evaluated."""

from __future__ import annotations

from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from importlib import import_module
from math import inf, nextafter
from pathlib import Path
from typing import Any

import pytest

with pytest.MonkeyPatch.context() as patch:
    patch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "docs/adr/experiments/0167"))
    analysis = import_module("ariadna_split_analysis")
    common = import_module("ariadna_split_common")


def fixture(
    *,
    radial_shift_m: Fraction = Fraction(),
    velocity_shift_m_s: Fraction = Fraction(),
    closure_miss: bool = False,
) -> tuple[dict[str, Any], list[dict[str, list[float]]]]:
    """Use a 3:4:5 direction with independently known radius and field norm."""
    bary_km = float(2**30)
    r0_m = [1000.0 * bary_km, -1000.0 * bary_km, 0.0]
    v0_m_s = [0.125, -0.1875, 0.5]
    e = [bary_km, -bary_km, 1.5, 0.0, 0.0, 0.0]
    g = [3000.0, 4000.0, -1.5, 0.0, 0.0, 0.0]
    b = [bary_km + 3000.0, -bary_km + 4000.0, 0.0, 0.0, 0.0, 0.0]
    exact_e_si = [1000 * Fraction(x) for x in e]
    exact_e_si[0] += 3 * radial_shift_m / 5
    exact_e_si[1] += 4 * radial_shift_m / 5
    exact_e_si[3] += velocity_shift_m_s
    exact_b_si = [x + 1000 * Fraction(y) for x, y in zip(exact_e_si, g, strict=True)]
    r_m = Fraction(5_000_000) + radial_shift_m
    gm_m3_s2 = 4902800121846.8
    accel_norm = Fraction(gm_m3_s2) / (r_m * r_m)
    fields, norms = {}, {}
    for p in (80, 100):
        with localcontext(Context(prec=p, rounding=ROUND_HALF_EVEN)):
            axes = [accel_norm * Fraction(3, 5), accel_norm * Fraction(4, 5), Fraction()]
            fields[p] = [Decimal(x.numerator) / Decimal(x.denominator) for x in axes]
            norms[p] = Decimal(accel_norm.numerator) / Decimal(accel_norm.denominator)
    inputs = {
        "samples_in_probe_order": [],
        "references": [],
        "frozen_initial": {"epoch_tdb_s": 1024.0, "position_m": r0_m, "velocity_m_s": v0_m_s},
        "moon_gm_m3_s2": gm_m3_s2,
        "moon_radius_m": 1737400.0,
    }
    states = []
    for ordinal, elapsed_s in ((13, 0.25), (0, 0.0), (5, 250.0)):
        direct = b[:]
        if ordinal == 13 and closure_miss:
            direct[0] = nextafter(direct[0], inf)
        drift_m = [v * elapsed_s for v in v0_m_s]
        hi = 1024.0 + elapsed_s
        saved_moon_m = [x * 1000 for x in direct[:3]]
        inputs["samples_in_probe_order"].append({
            "observation_ordinal": ordinal,
            "elapsed_s": elapsed_s,
            "hi_tdb_s": hi,
            "hi_hex": hi.hex(),
            "lo_hex": 0.0.hex(),
            "raw_hex": {"Earth": [x.hex() for x in e], "Moon": [x.hex() for x in direct]},
            "frozen_q_m": [-x for x in drift_m],
            "frozen_drift_m": drift_m,
            "retained_moon_overall_gate_passed": ordinal != 13,
        })
        inputs["references"].append({
            "earth_state_si": exact_e_si[:],
            "moon_state_si": exact_b_si[:],
            "saved_moon_m": saved_moon_m,
            "saved_moon_source_residual_m": [Fraction(saved) - ref for saved, ref in zip(
                saved_moon_m, exact_b_si[:3], strict=True)],
            "d0_m": [3 * r_m / 5, 4 * r_m / 5, Fraction()],
            "a0": {p: f[:] for p, f in fields.items()},
            "a0_norm": norms.copy(),
        })
        states.append({"E": e[:], "G": g[:], "B": direct})
    return inputs, states


def examine(bundle: dict[str, Any], states: list[dict[str, list[float]]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    recorder = common.Recorder(report, common.ANALYSIS_CAPS, 0.0, 10.0, clock=lambda: 0.0)
    analysis.analyze(bundle, states, report, recorder)
    return report


def test_analytic_field_and_exact_work_caps() -> None:
    report = examine(*fixture())
    assert report["status"] == "passed" and report["numerical_passed"]
    assert report["position_closure_matches"] == 9 and not report["unavailable"]
    assert report["counts"] == {
        "binary64_field": {"attempted": 3, "returned": 3, "completed": 3},
        "decimal_field": {"attempted": 18, "returned": 18, "completed": 18},
    }
    expected_norm_m_s2 = 4902800121846.8 / 25e12
    for row in report["rows"]:
        result = row["static_force"]
        assert result["binary64_m_s2"] == pytest.approx(
            (0.6 * expected_norm_m_s2, 0.8 * expected_norm_m_s2, 0.0), abs=2e-16)
        assert result["reference_m_s2"]["100"]["d1"][2] == 0
        assert result["precision"]["passed"]
        assert all(item["passed"] for item in result["telescope"].values())
    assert sum(sum(row["states"][body]["historical_bit_matches"])
               for row in report["rows"] for body in ("E", "B")) == 36
    assert all(item["args"][1] != "d0" for item in report["ledger"])
    assert common.parse_json(common.encode(common.wire(report)))["numerical_passed"]


def test_position_closure_failure_does_not_suppress_static_force() -> None:
    report = examine(*fixture(closure_miss=True))
    assert report["state_prerequisites_passed"]
    assert report["position_closure_matches"] == 8 and not report["position_closure_passed"]
    assert report["static_force_passed"] and not report["numerical_passed"]
    closure = report["rows"][0]["closure"]
    assert closure["b_minus_legs_position_km"] == (Fraction(1, 2**22), 0, 0)
    assert closure["direct_position_raw_ulp_offsets"] == [1, 0, 0]
    assert closure["source_telescope_passed"]
    assert report["error"]["stage"] == "position_closure"


def test_source_error_can_fail_force_with_perfect_closure() -> None:
    report = examine(*fixture(radial_shift_m=Fraction(1, 2000)))
    assert report["position_closure_passed"] and report["state_prerequisites_passed"]
    assert not report["static_force_passed"] and not report["numerical_passed"]
    force = report["rows"][0]["static_force"]
    assert force["gates"]["100"]["returned_geometry"]["passed"]
    assert not force["gates"]["100"]["overall"]["passed"]
    assert force["signed_field_contributions_m_s2"]["100"]["source"][0] > 0
    assert report["error"]["stage"] == "static_force"


def test_velocity_closure_is_only_diagnostic() -> None:
    bundle, states = fixture()
    states[0]["G"][3] = 5e-10  # km/s; under 1 µm/s parity, despite a bit mismatch.
    report = examine(bundle, states)
    assert report["numerical_passed"]
    assert report["rows"][0]["closure"]["velocity_diagnostic_matches"] == [False, True, True]


def test_single_relative_round_retains_part_of_a_leg_lost_at_barycentre() -> None:
    bundle, states = fixture()
    states[0]["G"][0] = nextafter(3000.0, inf)
    report = examine(bundle, states)
    result = report["rows"][0]["static_force"]
    assert report["numerical_passed"]  # B still closes after one raw km rounding.
    exact_m = Fraction(3_000_000) + Fraction(1000, 2**41)
    assert result["exact_separations_m"]["d2"][0] == exact_m
    assert result["rounded_separation_m"][0] == nextafter(3_000_000.0, inf)
    assert result["rounded_separation_m"][2].hex() == "0x0.0p+0"
    assert result["exact_separation_deltas_m"]["source"][0] == Fraction(1000, 2**41)


@pytest.mark.parametrize(("exact", "expected"), [
    (Fraction(1) + Fraction(1, 2**53), 1.0),
    (Fraction(1) + Fraction(3, 2**53), 1.0 + 2**-51),
    (-Fraction(1, 2**1075), -0.0),
    (Fraction(), 0.0),
])
def test_nearest_even_ties_and_zero(exact: Fraction, expected: float) -> None:
    assert analysis._round_exact(exact).hex() == expected.hex()


@pytest.mark.parametrize(("shift", "passed"), [
    (Fraction(1, 1000), True), (Fraction(1, 1000) + Fraction(1, 10**9), False),
])
def test_position_parity_is_exact_inclusive_norm(shift: Fraction, passed: bool) -> None:
    report = examine(*fixture(radial_shift_m=shift))
    assert report["state_prerequisites_passed"] is passed
    assert report["rows"][0]["states"]["B"]["position_error_squared_m2"] == shift**2
    if not passed:
        assert report["static_force_passed"] is None
        assert report["ledger"] == []


@pytest.mark.parametrize(("shift", "passed"), [
    (Fraction(1, 10**6), True), (Fraction(1, 10**6) + Fraction(1, 10**9), False),
])
def test_velocity_parity_is_exact_inclusive_norm(shift: Fraction, passed: bool) -> None:
    report = examine(*fixture(velocity_shift_m_s=shift))
    assert report["state_prerequisites_passed"] is passed
    assert report["rows"][0]["states"]["E"]["velocity_error_squared_m2_s2"] == shift**2


def test_archive_reproduction_includes_velocity_and_signed_zero() -> None:
    bundle, states = fixture()
    states[0]["E"][3] = -0.0
    report = examine(bundle, states)
    earth = report["rows"][0]["states"]["E"]
    assert earth["velocity_parity_passed"]
    assert earth["historical_bit_matches"] == [True, True, True, False, True, True]
    assert report["static_force_passed"] is None and report["ledger"] == []
    assert report["error"]["stage"] == "state_prerequisites"


@pytest.mark.parametrize(("field", "bad", "message"), [
    ("lo_hex", "-0x0.0p+0", "coepoch"),
    ("hi_hex", 1024.0.hex(), "coepoch"),
    ("elapsed_s", 0.5, "coepoch"),
    ("frozen_drift_m", [0.0, 0.0, 0.0], "frozen drift"),
    ("frozen_q_m", [0.0, 0.0, 0.0], "d0 geometry mismatch"),
])
def test_frozen_epoch_and_motion_mutations(field: str, bad: Any, message: str) -> None:
    bundle, states = fixture()
    bundle["samples_in_probe_order"][0][field] = bad
    with pytest.raises(ValueError, match=message):
        examine(bundle, states)


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), "0", None])
def test_raw_components_reject_nonfinite_or_non_numeric_operands(bad: Any) -> None:
    bundle, states = fixture()
    states[0]["G"][0] = bad
    with pytest.raises(ValueError, match="G raw state"):
        examine(bundle, states)


@pytest.mark.parametrize(("field", "bad", "message"), [
    ("d0_m", [Fraction(1), Fraction(2), Fraction(3)], "d0 geometry mismatch"),
    ("saved_moon_source_residual_m", [Fraction(1), Fraction(2), Fraction(3)], "source telescope"),
    ("a0_norm", {80: Decimal(1), 100: Decimal(1)}, "norm does not match"),
])
def test_retained_reference_mutations(field: str, bad: Any, message: str) -> None:
    bundle, states = fixture()
    bundle["references"][0][field] = bad
    with pytest.raises(ValueError, match=message):
        examine(bundle, states)


def test_domain_guard_checks_exact_surface_before_any_field() -> None:
    bundle, states = fixture()
    bundle["moon_radius_m"] = 5_000_000.0
    report: dict[str, Any] = {}
    recorder = common.Recorder(report, common.ANALYSIS_CAPS, 0.0, 10.0, clock=lambda: 0.0)
    with pytest.raises(ValueError, match="strictly exterior"):
        analysis.analyze(bundle, states, report, recorder)
    assert report["ledger"] == []
    assert report["position_closure_passed"]
    assert not any(report["rows"][0]["static_force"]["exact_exterior"].values())
    assert report["unavailable"] == ["static_force"]


@pytest.mark.parametrize(("scale", "delta", "passed"), [
    ("1", "1e-11", True), ("1", "1.0001e-11", False),
    ("1e-6", "1e-15", True), ("1e-6", "1.0001e-15", False),
])
def test_force_gate_includes_both_absolute_and_relative_envelopes(scale: str, delta: str, passed: bool) -> None:
    with localcontext(Context(prec=100, rounding=ROUND_HALF_EVEN)):
        r, zero = Decimal(scale), Decimal()
        gate = analysis._gate((r + Decimal(delta), zero, zero), (r, zero, zero), r)
        assert gate["passed"] is passed


def test_late_field_return_is_saved_without_qualification(monkeypatch: pytest.MonkeyPatch) -> None:
    bundle, states = fixture()
    report: dict[str, Any] = {}
    now = 0.0
    original = analysis._binary64_field

    def delayed_field(separation_m: tuple[float, ...], gm_m3_s2: float, rho_m: float) -> tuple[float, ...]:
        nonlocal now
        value = original(separation_m, gm_m3_s2, rho_m)
        now = 10.001
        return value

    monkeypatch.setattr(analysis, "_binary64_field", delayed_field)
    recorder = common.Recorder(report, common.ANALYSIS_CAPS, 0.0, 10.0, clock=lambda: now)
    with pytest.raises(ValueError, match="deadline"):
        analysis.analyze(bundle, states, report, recorder)
    assert report["counts"]["binary64_field"] == {"attempted": 1, "returned": 1, "completed": 0}
    assert len(report["ledger"][0]["raw"]) == 3
    assert report["static_force_passed"] is None
