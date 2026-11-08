"""Analytic source polynomials and actual q/w operands; no retained study."""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any

import pytest

PATH = Path(__file__).resolve().parents[1]/"docs/adr/experiments/0163-corrected-reference.py"
spec = importlib.util.spec_from_file_location("corrected_reference_tests", PATH)
assert spec is not None and spec.loader is not None
reference = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reference
spec.loader.exec_module(reference)


def fixture(*, elapsed: float = 0.25, epoch: float = 1000.0,
            q: tuple[float, ...] = (0.01, -0.03, 0.02),
            w: tuple[float, ...] = (-0.1, 0.03, 0.06)) -> tuple[dict[str, Any], ...]:
    initial = {"epoch_tdb_s": epoch, "position_m": [2.0, -1.0, 3.0],
               "velocity_m_s": [0.125, -0.25, 0.5]}
    drift = [v*elapsed for v in initial["velocity_m_s"]]
    motion = {"elapsed_s": elapsed, "q_m": list(q), "w_m_s": list(w), "drift_m": drift,
              "position_m": [math.fsum((initial["position_m"][j], drift[j], q[j])) for j in range(3)],
              "velocity_m_s": [math.fsum((initial["velocity_m_s"][j], w[j])) for j in range(3)]}
    t = Fraction(epoch)+Fraction(elapsed)
    hi = float(t)
    lo = float(t-Fraction(hi))
    body_rows, geometry = {}, {}
    coefficients = {"Sun": (2.0, 3.0, 6.0), "Moon": (-2.0, 3.0, -6.0), "Earth": (4.0, -5.0, 6.0)}
    slope = (0.01, 0.02, -0.03)
    gm = {b: 49_000_000.0 for b in reference.BODIES}
    radii = {b: 1.0 for b in reference.BODIES}
    for body in reference.BODIES:
        segments = []
        total_position, total_velocity = [0.0]*3, [0.0]*3
        for index, (target, centre) in enumerate(reference.BASE.CHAINS[body]):
            coeff = coefficients[body] if index == 0 else coefficients["Earth"]
            ss = slope if index == 0 else (0.0, 0.0, 0.0)
            words = [epoch, 512.0, *[x for pair in zip(coeff, ss, strict=True) for x in pair]]
            segments.append({"body": target, "centre": centre, "frame": 1, "type": 2,
                             "first_tdb_s": epoch-512, "last_tdb_s": epoch+512, "words": words})
            for j in range(3):
                total_position[j] += coeff[j]+ss[j]*((hi-epoch)/512)
                total_velocity[j] += ss[j]/512
        raw = total_position+total_velocity
        state = [x*1000 for x in raw]
        body_rows[body] = {"body": body, "elapsed_s": elapsed, "hi_tdb_s": hi, "lo_s": lo,
                           "state_km_km_s": raw, "state_si": state, "segments": segments,
                           "assessment": {"passed": False, "deliberately_stale": True}}
        c = [x*lo for x in state[3:]]
        d = [math.fsum((state[j], -initial["position_m"][j], -drift[j], -q[j], c[j])) for j in range(3)]
        rho = math.hypot(*d)
        geometry[body] = {"rephasing_m": c, "separation_m": d}
        if body in reference.INCLUDED:
            geometry[body]["acceleration_m_s2"] = [gm[body]*(x/rho)/(rho*rho) for x in d]
    return initial, motion, body_rows, geometry, gm, radii


def assess(data: tuple[dict[str, Any], ...], events: list[tuple[str, str]] | None = None,
           progress: dict[str, Any] | None = None) -> dict[str, Any]:
    events = [] if events is None else events
    return reference.assess_observation(*data, lambda kind, phase: events.append((kind, phase)), progress=progress)


def test_dynamic_operands_and_exact_counts() -> None:
    data = fixture()
    events: list[tuple[str, str]] = []
    result = assess(data, events)
    assert result["passed"] and result["motion"]["passed"] and result["A"]["passed"]
    assert set(result["sources"]) == {"Sun", "Moon"}
    assert "controls" not in result["A"]["gates"]["100"]
    assert Counter(events) == Counter({(k, p): v for k, v in (("body_checks", 3), ("source_rows", 2),
                                  ("reference_fields", 16), ("model_totals", 1)) for p in ("attempt", "complete")})
    assert events.index(("reference_fields", "attempt")) > max(i for i, e in enumerate(events) if e == ("body_checks", "complete"))
    assert all(x["geometry_error_identity"] for x in result["bodies"].values())
    assert all(result["sources"][b]["precision"]["passed"] for b in reference.INCLUDED)
    assert "q_rounding" not in result["motion"]["component_gates"]


@pytest.mark.parametrize("s", [0.0, 2**-25, 0.05260015195876773, 1.0, 150.0, 300.0])
def test_arbitrary_dynamic_operands(s: float) -> None:
    assert assess(fixture(elapsed=s))["passed"]


def test_nonzero_low_source_time_is_checked() -> None:
    data = fixture(elapsed=2**-25, epoch=978995455.2304223)
    assert data[2]["Sun"]["lo_s"] != 0
    assert assess(data)["passed"]


@pytest.mark.parametrize("field", ["drift_m", "position_m", "velocity_m_s"])
def test_motion_mutations_fail_independent_bound(field: str) -> None:
    values, motion, *_ = fixture()
    motion[field][1] += 1e-5
    assert not reference.assess_motion(values, motion)["passed"]


@pytest.mark.parametrize("field", ["q_m", "w_m_s", "drift_m", "position_m", "velocity_m_s"])
@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), "bad", None])
def test_invalid_motion_numbers(field: str, bad: Any) -> None:
    initial, motion, *_ = fixture()
    motion[field][0] = bad
    with pytest.raises(ValueError):
        reference.assess_motion(initial, motion)


@pytest.mark.parametrize("s", [-1.0, 300.0001, float("nan"), True])
def test_invalid_elapsed(s: Any) -> None:
    initial, motion, *_ = fixture()
    motion["elapsed_s"] = s
    with pytest.raises(ValueError):
        reference.assess_motion(initial, motion)


@pytest.mark.parametrize("mutation", ["body", "centre", "frame", "type", "coverage", "record", "epoch", "raw", "velocity", "position", "rephase", "separation", "force", "gm", "radius"])
def test_source_and_force_mutations(mutation: str) -> None:
    data = fixture(elapsed=2**-25, epoch=978995455.2304223)
    initial, motion, rows, geometry, gm, radii = data
    row = rows["Sun"]
    if mutation == "body":
        row["body"] = "Earth"
    elif mutation in ("centre", "frame", "type"):
        row["segments"][0][mutation] = 99
    elif mutation == "coverage":
        row["segments"][0]["first_tdb_s"] = initial["epoch_tdb_s"]+1
    elif mutation == "record":
        row["segments"][0]["words"][1] = 0
    elif mutation == "epoch":
        row["lo_s"] = -row["lo_s"]
    elif mutation == "raw":
        row["state_km_km_s"][0] += 1
    elif mutation == "velocity":
        row["state_si"][3] += 1
        row["state_km_km_s"][3] = row["state_si"][3]/1000
    elif mutation == "position":
        row["state_si"][0] += 1
        row["state_km_km_s"][0] = row["state_si"][0]/1000
    elif mutation == "rephase":
        geometry["Sun"]["rephasing_m"][0] *= -1
    elif mutation == "separation":
        geometry["Sun"]["separation_m"][0] += 1
    elif mutation == "force":
        geometry["Sun"]["acceleration_m_s2"][0] += 1e-5
    elif mutation == "gm":
        gm["Sun"] *= 2
    elif mutation == "radius":
        radii["Earth"] = 1e10
    events: list[tuple[str, str]] = []
    with pytest.raises(ValueError):
        assess(data, events)
    if mutation in ("radius", "body", "centre", "frame", "type", "coverage", "record", "epoch", "raw", "velocity", "position", "rephase", "separation"):
        assert ("reference_fields", "attempt") not in events


def test_earth_domain_checked_before_any_field() -> None:
    data = fixture()
    data[-1]["Earth"] = 1e20
    events: list[tuple[str, str]] = []
    with pytest.raises(ValueError, match="exterior-domain"):
        assess(data, events)
    assert ("reference_fields", "attempt") not in events


def test_ledger_failure_retains_completed_field_prefix() -> None:
    data = fixture()
    events: list[tuple[str, str]] = []
    progress: dict[str, Any] = {}
    def consume(kind: str, phase: str) -> None:
        events.append((kind, phase))
        if Counter(events)[("reference_fields", "attempt")] == 3:
            raise ValueError("test cap")
    with pytest.raises(ValueError, match="test cap"):
        reference.assess_observation(*data, consume, progress=progress)
    assert len(progress["sources"]["Sun"]["raw_reference"]["80"]) == 2
    assert Counter(events)[("reference_fields", "complete")] == 2
    assert "Moon" not in progress["sources"]


def test_deadline_after_field_preserves_raw_return() -> None:
    data = fixture()
    progress: dict[str, Any] = {}
    counter = Counter()
    def consume(kind: str, phase: str) -> None:
        counter[(kind, phase)] += 1
    def check() -> None:
        if counter[("reference_fields", "complete")] == 1:
            raise ValueError("late field")
    with pytest.raises(ValueError, match="late field"):
        reference.assess_observation(*data, consume, check, progress=progress)
    assert "d0" in progress["sources"]["Sun"]["raw_reference"]["80"]


@pytest.mark.parametrize("limit,offset,passed", [(1., 1., True), (1., math.nextafter(1., math.inf), False), (0.01, 0.01, True)])
def test_exact_state_comparison_boundary(limit: float, offset: float, passed: bool) -> None:
    a, b = [0.0]*6, [0.0]*6
    b[0] = offset
    assert reference.compare_states(a, b, limit, 1e-6)["passed"] is passed


def test_cancelling_source_sum_uses_constituent_norm_scales() -> None:
    fields, scales = {}, {}
    for p in ("80", "100"):
        fields[p] = {k: (reference.Decimal(0),)*3 for k in reference.BASE.GEOMETRIES}
        scales[p] = {k: reference.Decimal(10) for k in reference.BASE.GEOMETRIES}
    result = reference._assess_fields(fields, scales, (1e-11, 0., 0.))
    assert result["passed"]
    assert reference.Decimal(result["gates"]["100"]["overall"]["envelope_m_s2"]) == reference.Decimal("1e-10")


def test_force_precision_ambiguity_is_required_failure() -> None:
    fields, scales = {}, {}
    for p in ("80", "100"):
        fields[p] = {k: (reference.Decimal(1), reference.Decimal(0), reference.Decimal(0)) for k in reference.BASE.GEOMETRIES}
        scales[p] = {k: reference.Decimal(1) for k in reference.BASE.GEOMETRIES}
    fields["80"]["d0"] = (reference.Decimal("1.0000000000000000000000000000000000000000000000000000001"), reference.Decimal(0), reference.Decimal(0))
    assert not reference._assess_fields(fields, scales, (1., 0., 0.))["precision"]["passed"]


def test_no_manufactured_constructor_or_candidate_import() -> None:
    text = PATH.read_text()
    assert "prescribed_corrections" not in text
    assert "0160-moving-study" not in text
    assert "0163-corrected-core" not in text


def test_subnormal_tie_uses_even_product_and_exact_zero_sum() -> None:
    tiny = math.ulp(0.0)
    initial = {"epoch_tdb_s": 1000., "position_m": [0., 0., 0.], "velocity_m_s": [tiny, 0., 0.]}
    motion = {"elapsed_s": 0.5, "q_m": [0., 0., 0.], "w_m_s": [0., 0., 0.],
              "drift_m": [0., 0., 0.], "position_m": [0., 0., 0.], "velocity_m_s": [tiny, 0., 0.]}
    good = reference.assess_motion(initial, motion)
    assert good["passed"]
    assert good["component_gates"]["drift_product"][0]["midpoint"]
    motion["drift_m"][0] = tiny
    assert not reference.assess_motion(initial, motion)["component_gates"]["drift_product"][0]["passed"]


def test_exact_cancellation_is_required_from_actual_sum_operands() -> None:
    initial, motion, *_ = fixture()
    motion["q_m"] = [-initial["position_m"][j]-motion["drift_m"][j] for j in range(3)]
    motion["position_m"] = [0.]*3
    motion["w_m_s"] = [-v for v in initial["velocity_m_s"]]
    motion["velocity_m_s"] = [0.]*3
    assert reference.assess_motion(initial, motion)["passed"]
    motion["position_m"][0] = math.ulp(0.)
    assert not reference.assess_motion(initial, motion)["component_gates"]["position_sum"][0]["passed"]


def test_native_source_floor_cannot_be_subtracted_from_overall_force_gate() -> None:
    data = fixture()
    initial, motion, rows, geometry, gm, _radii = data
    raw = rows["Sun"]
    raw["state_km_km_s"][0] += 0.0005/1000
    raw["state_si"][0] = raw["state_km_km_s"][0]*1000
    c = geometry["Sun"]["rephasing_m"]
    d = [math.fsum((raw["state_si"][j], -initial["position_m"][j], -motion["drift_m"][j], -motion["q_m"][j], c[j])) for j in range(3)]
    rho = math.hypot(*d)
    geometry["Sun"].update(separation_m=d, acceleration_m_s2=[gm["Sun"]*(x/rho)/(rho*rho) for x in d])
    progress: dict[str, Any] = {}
    with pytest.raises(ValueError, match="required force"):
        assess(data, progress=progress)
    assert progress["bodies"]["Sun"]["source_assessment"]["passed"]
    assert progress["sources"]["Sun"]["gates"]["100"]["returned_geometry"]["passed"]
    assert not progress["sources"]["Sun"]["gates"]["100"]["overall"]["passed"]


@pytest.mark.parametrize("mutation", ["initial_epoch", "elapsed", "body_order", "geometry_order", "boolean_gm", "negative_gm", "boolean_radius", "nonfinite_force"])
def test_observation_schema_and_identity_boundaries(mutation: str) -> None:
    data = list(fixture())
    if mutation == "initial_epoch":
        data[0]["epoch_tdb_s"] += 1
    elif mutation == "elapsed":
        data[2]["Moon"]["elapsed_s"] = 0.5
    elif mutation == "body_order":
        data[2] = dict(reversed(list(data[2].items())))
    elif mutation == "geometry_order":
        data[3] = dict(reversed(list(data[3].items())))
    elif mutation == "boolean_gm":
        data[4]["Sun"] = True
    elif mutation == "negative_gm":
        data[4]["Sun"] = -1
    elif mutation == "boolean_radius":
        data[5]["Sun"] = True
    elif mutation == "nonfinite_force":
        data[3]["Sun"]["acceleration_m_s2"][0] = float("nan")
    with pytest.raises(ValueError):
        assess(tuple(data))


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), 0., -1.])
def test_state_comparison_rejects_invalid_limits(bad: Any) -> None:
    with pytest.raises(ValueError):
        reference.compare_states([0.]*6, [0.]*6, bad, 1e-6)


def test_failed_preflight_assessments_survive_failure() -> None:
    data = fixture()
    data[-1]["Earth"] = 1e10
    progress: dict[str, Any] = {}
    with pytest.raises(ValueError, match="exterior-domain"):
        assess(data, progress=progress)
    assert not any(progress["bodies"]["Earth"]["domain_guards"].values())
    assert progress["bodies"]["Earth"]["source_assessment"]["passed"]
    assert progress["sources"] == {}
    data = fixture()
    row = data[2]["Sun"]
    row["state_km_km_s"][0] += 1
    row["state_si"][0] = row["state_km_km_s"][0]*1000
    progress = {}
    with pytest.raises(ValueError, match="source parity"):
        assess(data, progress=progress)
    assert not progress["bodies"]["Sun"]["source_assessment"]["passed"]
