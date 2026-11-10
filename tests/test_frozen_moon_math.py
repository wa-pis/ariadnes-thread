"""Synthetic-only arithmetic checks for the frozen split lunar source screen."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
from math import inf, nextafter
from pathlib import Path
import sys
from typing import Any

import pytest

_EXPERIMENTS = Path(__file__).resolve().parents[1] / "docs" / "adr" / "experiments"
sys.path[:0] = [str(_EXPERIMENTS / "0170"), str(_EXPERIMENTS / "0167")]

from ariadna_frozen_moon_math import _exact_record, _rounded_product, analyze  # noqa: E402
from ariadna_split_common import Recorder  # noqa: E402

_CAPS = {"observation": 28, "reference_epoch": 29, "record": 58, "binary64_field": 28, "decimal_field": 224}
_GM = 4902800121846.8
_T0 = float(2**30)
_DISTANCE = 2_000_000


def _record(*blocks: list[float], midpoint: float = _T0, radius: float = 1024.0) -> list[float]:
    return [midpoint, radius, *(value for block in blocks for value in [*block, *[0.0] * (13 - len(block))])]


def _saved_control() -> dict[str, Any]:
    """Independent collinear oracle: the only nonzero acceleration is GM / r²."""
    fields = {}
    for precision in (80, 100):
        with localcontext() as context:
            context.prec = precision
            acceleration = str(Decimal.from_float(_GM) / Decimal(_DISTANCE**2))
            fields[str(precision)] = {key: [acceleration, "0", "0"] for key in ("d0", "d1", "d2", "d3")}
    return {"static_force": {
        "exact_separations_m": {key: [str(_DISTANCE), "0", "0"] for key in ("d0", "d1", "d2", "d3")},
        "rounded_separation_m": [float(_DISTANCE), 0.0, 0.0], "rho_m": float(_DISTANCE),
        "binary64_m_s2": [_GM / _DISTANCE**2, 0.0, 0.0], "reference_m_s2": fields,
        "gates": {p: {key: {"passed": True} for key in ("overall", "returned_geometry")} for p in ("80", "100")},
        "passed": True,
    }}


def frozen_bundle() -> dict[str, Any]:
    """Construct 28 analytic observations with the documented overlap and lo counts."""
    off = 2.0**-24
    e, g = 100_000_000.0, 400_000.0
    v0 = (1.0, -0.0, 0.0)
    controls = {("normal", "output", 0), ("normal", "output", 5), ("normal", "rhs", 6)}
    offsets = {
        "normal": (0.0, 1 + off, 2 + off, 3 - off, 4 - off, 5 - off, 0.25),
        "tighter": (0.0, 6 + off, 7 - off, 8 + off, 9 + off, 10 + off, 0.125),
    }
    rows = []
    for profile, rhs in offsets.items():
        for kind, times in (("output", (0., 50., 100., 150., 200., 250., 300.)), ("rhs", rhs)):
            for index, elapsed in enumerate(times):
                hi = _T0 + elapsed
                lo = float(Fraction(_T0) + Fraction(elapsed) - Fraction(hi))
                mode = "measured" if elapsed in (0., 0.25, 250.) else "proxy"
                states = {"E": [e, 0., 0., 0., 0., 0.], "B": [e + g, 0., 0., 0., 0., 0.]}
                states_si = {label: [1000 * x for x in state] for label, state in states.items()}
                if mode == "measured":
                    states["G"] = [g, 0., 0., 0., 0., 0.]
                rows.append({
                    "profile": profile, "kind": kind, "index": index, "source_mode": mode,
                    "elapsed_s": elapsed, "hi_tdb_s": hi, "lo_s": lo, "states": states, "states_si": states_si,
                    "motion": {"elapsed_s": elapsed, "q_m": [-elapsed, 0., 0.], "w_m_s": [-1., 0., 0.],
                               "drift_m": [v * elapsed for v in v0]},
                    "moon_geometry": {"rephasing_m": [v * lo for v in states_si["B"][3:]]},
                    "control": _saved_control() if (profile, kind, index) in controls else None,
                    "archived_direct": {"passed": False} if profile == "normal" and kind == "output" else None,
                })
    return {"initial": {"epoch_tdb_s": _T0, "position_m": [1000 * (e + g) - _DISTANCE, 0., 0.],
                        "velocity_m_s": v0},
            "gm_m3_s2": _GM, "radius_m": 1_737_400.0,
            "records": {"E": _record([e], [], []), "G": _record([g], [], [])}, "rows": rows}


def _analyze(bundle: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    analyze(bundle, report, Recorder(report, _CAPS, 0.0, 10.0, clock=lambda: 0.0))
    return report


def test_exact_polynomial_and_velocity_use_normalized_time_and_si() -> None:
    words = _record([2., 3., 5., 7.], [0.] * 12 + [11.], [-1.], midpoint=2., radius=4.)
    # x=1/2: T1=1/2, T2=-1/2, T3=-1, T12=1. Their derivatives: 1, 2, 0, 0.
    assert _exact_record(words, Fraction(4)) == (Fraction(-6000), Fraction(11000), Fraction(-1000),
                                                  Fraction(3250), Fraction(0), Fraction(0))
    # Half-open domain and independent derivatives T3'(±1)=9, T12'(±1)=±144.
    assert _exact_record(words, Fraction(-2))[3:5] == (Fraction(11500), Fraction(-396000))
    with pytest.raises(ValueError, match="half-open"):
        _exact_record(words, Fraction(6))


@pytest.mark.parametrize(("left", "right", "expected"), [
    (-0.0, 1.0, "-0x0.0p+0"), (-0.0, -1.0, "0x0.0p+0"),
    (-2.0**-1074, 0.5, "-0x0.0p+0"), (3 * 2.0**-1074, 0.5, (2 * 2.0**-1074).hex()),
])
def test_product_sign_and_ties(left: float, right: float, expected: str) -> None:
    assert _rounded_product(left, right).hex() == expected


def test_screen_keeps_duplicate_observations_and_counts_distinct_epochs() -> None:
    report = _analyze(frozen_bundle())
    assert report["status"] == "passed"
    assert report["epoch_counts"] == {"rounded": 19, "exact": 19, "union": 29}
    assert {op: counts["attempted"] for op, counts in report["counts"].items()} == _CAPS
    assert report["source_counts"] == {
        "measured": {"attempted": 7, "passed": 7, "failed": 0},
        "proxy": {"attempted": 21, "passed": 21, "failed": 0},
    }
    rows = report["rows"]
    assert {row["lo_s"] for row in rows} == {0.0, 2.0**-24, -(2.0**-24)}
    assert len([row for row in rows if row.get("control", {}).get("passed")]) == 3
    assert rows[0]["archived_direct"]["same_verdict"] is False
    assert rows[7]["archived_direct"]["available"] is False
    assert "G" in rows[0]["state_parity"]
    assert "G" not in rows[1]["state_parity"]


def test_closure_and_lunar_force_have_independent_verdicts() -> None:
    bundle = frozen_bundle()
    raw_b = bundle["rows"][1]["states"]["B"]
    raw_b[0] = nextafter(raw_b[0], inf)
    # One ULP of the unused Moon/SSB position changes closure, but not the force.
    report = _analyze(bundle)
    assert report["status"] == "passed"
    assert report["rows"][1]["closure"]["position_passed"] is False
    assert report["rows"][1]["static_force"]["passed"] is True

    # Perturb only the used Earth leg by < 1 mm: preserve parity, miss overall force gate.
    raw_e = bundle["rows"][1]["states"]["E"]
    raw_e[0] += 2.0**-21
    report = _analyze(bundle)
    row = report["rows"][1]
    assert row["state_parity"]["E"]["position_passed"] is True
    assert row["static_force"]["gates"]["100"]["returned_geometry"]["passed"] is True
    assert row["static_force"]["gates"]["100"]["overall"]["passed"] is False
    assert report["error"]["observation_ordinal"] == 1
    assert report["rows"][-1]["status"] == "passed"
    assert report["counts"]["decimal_field"]["attempted"] == 224


def test_signed_rephasing_mutation_stops_before_fields() -> None:
    bundle = frozen_bundle()
    bundle["rows"][0]["moon_geometry"]["rephasing_m"][0] = -0.0
    report: dict[str, Any] = {}
    recorder = Recorder(report, _CAPS, 0.0, 10.0, clock=lambda: 0.0)
    with pytest.raises(ValueError, match="signed binary64 product mismatch"):
        analyze(bundle, report, recorder)
    assert report["error"]["stage"] == "motion"
    assert report["counts"]["binary64_field"]["attempted"] == 0
    assert report["unavailable"][-1]["observation_ordinal"] == 27


def test_boundary_geometry_stops_before_fields_and_preserves_earliest_miss() -> None:
    bundle = frozen_bundle()
    bundle["rows"][1]["states"]["E"][0] += 2.0**-21
    # Geometry at the surface is excluded, even when the reference polynomial is valid.
    bundle["rows"][2]["motion"]["q_m"][0] += _DISTANCE - bundle["radius_m"]
    report: dict[str, Any] = {}
    recorder = Recorder(report, _CAPS, 0.0, 10.0, clock=lambda: 0.0)
    with pytest.raises(ValueError, match="strictly exterior"):
        analyze(bundle, report, recorder)
    assert report["error"]["observation_ordinal"] == 1
    assert report["rows"][2]["error"]["stage"] == "geometry"
    assert report["counts"]["binary64_field"]["attempted"] == 2
    assert report["counts"]["decimal_field"]["attempted"] == 16


def test_deadline_and_missing_record_stop_at_reference_admission() -> None:
    bundle = frozen_bundle()
    bundle["records"]["E"][1] = 0.0
    report: dict[str, Any] = {}
    with pytest.raises(ValueError, match="half-open"):
        analyze(bundle, report, Recorder(report, _CAPS, 0.0, 10.0, clock=lambda: 0.0))
    assert report["counts"]["reference_epoch"]["attempted"] == 1
    assert report["counts"]["record"]["attempted"] == 1
    assert report["counts"]["record"]["returned"] == 0

    times = iter([0.0, 0.0, 0.0, 0.0, 10.1])
    with pytest.raises(ValueError, match="deadline"):
        analyze(frozen_bundle(), report := {}, Recorder(report, _CAPS, 0.0, 10.0, clock=lambda: next(times)))
    assert report["counts"]["observation"]["attempted"] == 1
    assert report["counts"]["reference_epoch"]["attempted"] == 0


def test_control_force_verdict_must_match_saved_evidence() -> None:
    bundle = frozen_bundle()
    wrong = deepcopy(bundle["rows"][0]["control"])
    wrong["static_force"]["gates"]["100"]["overall"]["passed"] = False
    bundle["rows"][0]["control"] = wrong
    report = _analyze(bundle)
    assert report["status"] == "failed"
    assert report["error"]["stage"] == "control"
    assert report["rows"][0]["static_force"]["passed"] is True
    assert report["rows"][0]["control"]["checks"]["gate_verdicts"] is False
    assert report["rows"][-1]["status"] == "passed"


def test_moving_reference_uses_signed_lo_and_original_barycentric_velocity() -> None:
    bundle = frozen_bundle()
    speed_km_s = 1 / 16
    speed_m_s = speed_km_s * 1000
    bundle["records"]["G"][3] = speed_km_s * 1024
    for row in bundle["rows"]:
        geocentric_km = 400_000.0 + speed_km_s * (row["hi_tdb_s"] - _T0)
        row["states"]["B"][0] = 100_000_000.0 + geocentric_km
        row["states"]["B"][3] = speed_km_s
        row["states_si"]["B"] = [1000 * value for value in row["states"]["B"]]
        if row["source_mode"] == "measured":
            row["states"]["G"][0] = geocentric_km
            row["states"]["G"][3] = speed_km_s
        row["motion"]["q_m"][0] = (speed_m_s - 1) * row["elapsed_s"]
        row["moon_geometry"]["rephasing_m"] = [v * row["lo_s"] for v in row["states_si"]["B"][3:]]

    report = _analyze(bundle)
    assert report["status"] == "passed"
    for index, sign in ((8, 1), (10, -1)):
        row = report["rows"][index]
        increment = sign * Fraction(125, 2**25)
        assert row["time_increment"]["reference_increment_m"] == (increment, 0, 0)
        assert row["motion"]["rephasing_m"][0] == float(increment)
        assert row["time_increment"]["signed_error_m"] == (0, 0, 0)
        assert row["static_force"]["exact_separations_m"]["d2"] == (Fraction(_DISTANCE), 0, 0)


def test_state_parity_miss_marks_force_unavailable_and_preserves_other_rows() -> None:
    bundle = frozen_bundle()
    bundle["rows"][1]["states"]["E"][0] += 2.0**-18  # more than 1 mm in SI
    report = _analyze(bundle)
    assert report["status"] == "failed"
    assert report["error"]["stage"] == "state_parity"
    assert report["unavailable"] == [{"observation_ordinal": 1, "stage": "static_force"}]
    assert report["rows"][-1]["status"] == "passed"
    assert report["counts"]["decimal_field"]["attempted"] == 216
