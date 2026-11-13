"""Synthetic sampled Type 2 references and measured split geometry; no SPICE."""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any

import pytest

PATH = Path(__file__).resolve().parents[1] / "docs/adr/experiments/0180-split-reference.py"
spec = importlib.util.spec_from_file_location("split_coast_reference_tests", PATH)
assert spec is not None and spec.loader is not None
reference = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reference
spec.loader.exec_module(reference)


def fixture(*, epoch: float = 978995455.2304223,
            elapsed: float = 2**-25, cancelling_z: bool = False) -> tuple[dict[str, Any], ...]:
    initial = {"epoch_tdb_s": epoch, "position_m": [2.0, -1.0, 0.0],
               "velocity_m_s": [0.125, -0.25, -0.0]}
    q, w = [0.01, -0.03, -0.0 if cancelling_z else 0.02], [-0.1, 0.03, 0.06]
    drift = [v*elapsed for v in initial["velocity_m_s"]]
    motion = {"elapsed_s": elapsed, "q_m": q, "w_m_s": w, "drift_m": drift,
              "position_m": [math.fsum((initial["position_m"][j], drift[j], q[j])) for j in range(3)],
              "velocity_m_s": [math.fsum((initial["velocity_m_s"][j], w[j])) for j in range(3)]}
    exact = Fraction(epoch)+Fraction(elapsed)
    hi = float(exact)
    lo = float(exact-Fraction(hi))
    geocentric_z = -6.0 if cancelling_z else -5.0
    coefficients = {(10, 0): (2.0, 3.0, 6.0), (301, 399): (-2.0, 3.0, geocentric_z), (399, 0): (4.0, -5.0, 6.0)}
    slopes = {(10, 0): (0.01, 0.02, -0.03), (301, 399): (-0.02, 0.01, 0.0), (399, 0): (0.04, 0.02, 0.0)}
    segments, analytic = {}, {}
    for key, midpoint_values in coefficients.items():
        slopes_at_key = slopes[key]
        words = [epoch, 512.0, *[x for pair in zip(midpoint_values, slopes_at_key, strict=True) for x in pair]]
        segments[key] = {"body": key[0], "centre": key[1], "frame": 1, "type": 2,
                         "first_tdb_s": epoch-512, "last_tdb_s": epoch+512, "words": words}
        analytic[key] = tuple(Fraction(v)+Fraction(ss)*(Fraction(hi)-Fraction(epoch))/512
                              for v, ss in zip(midpoint_values, slopes_at_key, strict=True)) + tuple(
                                  Fraction(ss)/512 for ss in slopes_at_key)

    body_rows, geometry = {}, {}
    gm = {b: 49_000_000.0 for b in reference.BODIES}
    radii = {b: 1.0 for b in reference.BODIES}
    lunar_raw = list(map(float, analytic[(301, 399)]))
    for body in reference.BODIES:
        chain = reference.BASE.CHAINS[body]
        raw = [float(sum((analytic[key][i] for key in chain), Fraction())) for i in range(6)]
        state = [x*1000 for x in raw]
        body_rows[body] = {"body": body, "elapsed_s": elapsed, "hi_tdb_s": hi, "lo_s": lo,
                           "state_km_km_s": raw, "state_si": state, "segments": [segments[key] for key in chain]}
        c = [x*lo for x in state[3:]]
        geometry[body] = {"rephasing_m": c}
        if body != "Moon":
            d = [math.fsum((state[j], -initial["position_m"][j], -drift[j], -q[j], c[j])) for j in range(3)]
        else:
            e = list(map(float, analytic[(399, 0)]))
            d2 = [1000*(Fraction(e[j])+Fraction(lunar_raw[j]))+Fraction(c[j])-Fraction(initial["position_m"][j])
                  -Fraction(drift[j])-Fraction(q[j]) for j in range(3)]
            geometry[body]["pre_round_separation_m"] = list(map(str, d2))
            d = list(map(float, d2))
        geometry[body]["separation_m"] = d
        if body in reference.INCLUDED:
            rho = math.hypot(*d)
            geometry[body]["acceleration_m_s2"] = [gm[body]*(x/rho)/(rho*rho) for x in d]
    body_rows["Moon/Earth"] = {"body": "Moon", "observer": "Earth", "frame": "J2000",
                              "aberration": "NONE", "epoch_tdb_s": hi, "state_km_km_s": lunar_raw,
                              "segments": [segments[(301, 399)]]}
    return initial, motion, body_rows, geometry, gm, radii


@pytest.mark.parametrize("elapsed,record_count", [(1., 3), (2**-25, 6), (1.-2**-25, 6)])
def test_counts_and_reuse_pure_type_2_records(elapsed: float, record_count: int,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[str, str]] = []
    real_evaluate = reference.ORACLE.evaluate_chain
    calls = Counter()

    def evaluate(records: Any, epoch: Fraction) -> Any:
        assert len(records) == 1
        assert ("record_evaluations", "attempt") == events[-1]
        calls[records[0], epoch] += 1
        return real_evaluate(records, epoch)

    monkeypatch.setattr(reference.ORACLE, "evaluate_chain", evaluate)
    data = fixture(elapsed=elapsed)
    result = reference.assess_observation(*data, lambda kind, phase: events.append((kind, phase)))
    assert result["passed"] and result["A"]["passed"]
    assert len(calls) == record_count and max(calls.values()) == 1
    assert Counter(events) == Counter({(kind, phase): count for kind, count in (
        ("record_evaluations", record_count), ("body_checks", 3), ("moon_earth_checks", 1),
        ("source_rows", 2), ("reference_fields", 16), ("model_totals", 1),
    ) for phase in ("attempt", "complete")})
    assert events.index(("moon_earth_checks", "complete")) < events.index(("reference_fields", "attempt"))
    assert result["moon_earth"]["source_assessment"]["passed"]
    assert list(result["bodies"]) == ["Sun", "Moon", "Earth"]


def test_exact_raw_km_scaling_of_moon_earth() -> None:
    data = fixture(elapsed=1.)
    geo = data[2]["Moon/Earth"]
    geo["state_km_km_s"][0] = math.nextafter(geo["state_km_km_s"][0], -math.inf)
    # Independently restore expected candidate geometry for the changed source.
    moon = data[3]["Moon"]
    prior = Fraction(moon["pre_round_separation_m"][0])
    expected_km = Fraction(-2) + Fraction(-0.02)/512
    pre_mutation = float(expected_km)
    raw = geo["state_km_km_s"][0]
    moon["pre_round_separation_m"][0] = str(prior + 1000*(Fraction(raw)-Fraction(pre_mutation)))
    moon["separation_m"][0] = float(Fraction(moon["pre_round_separation_m"][0]))
    rho = math.hypot(*moon["separation_m"])
    moon["acceleration_m_s2"] = [data[4]["Moon"]*(x/rho)/(rho*rho) for x in moon["separation_m"]]
    result = reference.assess_observation(*data, lambda *_: None)
    parity = result["moon_earth"]["source_assessment"]
    observed = parity["signed_position_error_m"][0]
    assert Fraction(int(observed["numerator"]), int(observed["denominator"])) == 1000*(Fraction(raw)-expected_km)
    assert parity["passed"] and result["passed"]


def test_moon_direct_velocity_rephase_preserves_increment_and_signed_lo() -> None:
    for elapsed in (2**-25, 1.-2**-25):
        data = fixture(elapsed=elapsed)
        assessment = reference.assess_observation(*data, lambda *_: None)["bodies"]["Moon"]["source_assessment"]
        lo = data[2]["Moon"]["lo_s"]
        assert lo == (2**-25 if elapsed < 0.5 else -2**-25)
        assert assessment["checks"]["increment"] and assessment["checks"]["taylor"]
        assert assessment["correction_m"] == data[3]["Moon"]["rephasing_m"]
        assert assessment["correction_m"][0] != data[2]["Moon/Earth"]["state_km_km_s"][3]*1000*lo


@pytest.mark.parametrize("mutation,error", [
    ("observer", "observer/frame/correction"), ("frame", "observer/frame/correction"),
    ("aberration", "observer/frame/correction"), ("epoch", "query epoch"), ("body", "body/order"),
    ("shared_record", "shared centre chain"), ("coverage", "record coverage"),
    ("si", "SI conversion"), ("velocity", "Moon/Earth state parity"), ("nonfinite", "finite number"),
    ("rephasing", "signed rephasing"), ("drift", "signed drift"),
    ("pre_round", "pre-round separation"), ("fraction", "noncanonical fraction"),
    ("rounded", "relative assembly"), ("domain", "exterior-domain"),
])
def test_failed_inputs_do_not_reach_reference_fields(mutation: str, error: str) -> None:
    initial, motion, rows, geometry, gm, radii = fixture()
    geo = rows["Moon/Earth"]
    if mutation in ("observer", "frame", "aberration", "body"):
        geo[mutation] = "changed"
    elif mutation == "epoch":
        geo["epoch_tdb_s"] = math.nextafter(geo["epoch_tdb_s"], math.inf)
    elif mutation == "shared_record":
        geo["segments"] = [{**geo["segments"][0], "words": [0.0]*8}]
    elif mutation == "coverage":
        rows["Sun"]["segments"][0]["words"][1] = 2**-26
    elif mutation == "si":
        rows["Moon"]["state_si"][0] *= 1000
    elif mutation == "velocity":
        geo["state_km_km_s"][3] += 1
    elif mutation == "nonfinite":
        geo["state_km_km_s"][4] = math.inf
    elif mutation == "rephasing":
        geometry["Moon"]["rephasing_m"][0] = geo["state_km_km_s"][3]*1000*rows["Moon"]["lo_s"]
    elif mutation == "drift":
        motion["drift_m"][2] = 0.0
    elif mutation == "pre_round":
        geometry["Moon"]["pre_round_separation_m"][0] = "1"
    elif mutation == "fraction":
        geometry["Moon"]["pre_round_separation_m"][0] = "2/2"
    elif mutation == "rounded":
        d = geometry["Moon"]["separation_m"]
        d[0] = math.nextafter(d[0], math.inf)
    else:
        radii["Moon"] = 1e10
    events: list[tuple[str, str]] = []
    with pytest.raises(ValueError, match=error):
        reference.assess_observation(initial, motion, rows, geometry, gm, radii, lambda *event: events.append(event))
    assert ("reference_fields", "attempt") not in events


def test_closure_difference_is_reported_without_becoming_a_force_gate() -> None:
    data = fixture()
    raw, si = data[2]["Moon"]["state_km_km_s"], data[2]["Moon"]["state_si"]
    raw[0] = math.nextafter(raw[0], math.inf)
    si[0] = raw[0]*1000
    result = reference.assess_observation(*data, lambda *_: None)
    assert result["passed"] and not result["moon_earth"]["rounded_closure"]["position_passed"]


def test_exact_cancellation_uses_canonical_positive_zero() -> None:
    data = fixture(cancelling_z=True)
    geometry = data[3]["Moon"]
    assert geometry["pre_round_separation_m"][2] == "0"
    assert geometry["separation_m"][2].hex() == "0x0.0p+0"
    assert reference.assess_observation(*data, lambda *_: None)["passed"]
    geometry["separation_m"][2] = -0.0
    with pytest.raises(ValueError, match="relative assembly"):
        reference.assess_observation(*data, lambda *_: None)


def test_record_cap_counts_attempts_before_polynomial_work(monkeypatch: pytest.MonkeyPatch) -> None:
    events = Counter()
    evaluate = reference.ORACLE.evaluate_chain
    record_calls = 0

    def counted(*args: Any) -> Any:
        nonlocal record_calls
        record_calls += 1
        return evaluate(*args)

    def stop(kind: str, phase: str) -> None:
        events[(kind, phase)] += 1
        if events[("record_evaluations", "attempt")] == 4:
            raise ValueError("synthetic record cap")

    monkeypatch.setattr(reference.ORACLE, "evaluate_chain", counted)
    with pytest.raises(ValueError, match="synthetic record cap"):
        reference.assess_observation(*fixture(), stop)
    assert record_calls == events[("record_evaluations", "complete")] == 3
    assert not events[("reference_fields", "attempt")]
