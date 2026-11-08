"""Analytic-only corrected integration; no live mission or SPICE requests."""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/adr/experiments/0163-corrected-integrator.py"
SPEC = importlib.util.spec_from_file_location("corrected_integrator_tests", PATH)
assert SPEC and SPEC.loader
core = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = core
SPEC.loader.exec_module(core)


def bundle() -> dict[str, Any]:
    return {"initial": {"epoch_tdb_s": 978995455.2304223,
        "position_m": [1e6, 0., 0.], "velocity_m_s": [0., math.sqrt(2e6), 0.]},
        "gm_m3_s2": {"Sun": 1e12, "Moon": 1e12, "Earth": 1.},
        "radii_m": dict.fromkeys(core.BODIES, 1.)}


def provider(body: str, hi: float) -> list[float]:
    return [0., 0., 1e6 if body == "Earth" else 0., 0., 0., 0.]


def report_and_budget() -> tuple[dict[str, Any], Any]:
    b = core.Budget(lambda: 0., 0.)
    report = {"rhs": [], "trials": [], "profiles": [], "node_table": []}
    for s in core.OFFSETS:
        row: dict[str, Any] = {}
        report["node_table"].append(row)
        core.query_bodies(s, bundle()["initial"], provider, b, row)
    return report, b


@pytest.mark.parametrize("s", [0., 2**-25, .05260015195876773, .1, 150.00000008940697, 300.])
def test_two_sum_exact_identity(s: float) -> None:
    t0 = 978995455.2304223
    hi, lo = core.split_epoch(t0, s)
    assert Fraction(hi)+Fraction(lo) == Fraction(t0)+Fraction(s)
    assert abs(lo) <= math.ulp(hi)/2


@pytest.mark.parametrize("bad", [True, False, "1", None, float("nan"), float("inf")])
def test_invalid_epoch_operand(bad: Any) -> None:
    with pytest.raises(ValueError):
        core.split_epoch(bad, 0.)


@pytest.mark.parametrize("name", ["normal", "tighter"])
def test_genuine_circular_correction_and_exact_observer_parity(name: str) -> None:
    traces = []
    for observed in (False, True):
        report, budget = report_and_budget()
        result = core.solve_profile(bundle(), name, report, provider, budget, observed=observed)
        traces.append((report, result))
        assert result["raw_returned"]["success"] is True
        assert result["raw_returned"]["t"] == list(core.OFFSETS)
        assert any(abs(x) > 1 for x in result["raw_returned"]["y"][0][1:])
        omega = math.sqrt(2e12/1e18)
        for row in result["outputs"]:
            theta = omega*row["elapsed_s"]
            truth = [1e6*math.cos(theta), 1e6*math.sin(theta), 0.,
                     -1e6*omega*math.sin(theta), 1e6*omega*math.cos(theta), 0.]
            actual = row["motion"]["position_m"]+row["motion"]["velocity_m_s"]
            assert math.dist(actual[:3], truth[:3]) <= 1e-6
            assert math.dist(actual[3:], truth[3:]) <= 1e-8
        n = len(report["rhs"])
        assert budget.counts["rhs"]["completed"] == n == result["raw_returned"]["nfev"]
        assert budget.counts["states"]["attempted"] == 3*n+21
        assert budget.counts["binary64_fields"]["completed"] == 2*(n+7)
        assert all(r["completed"] is True for r in report["rhs"])
        assert any(r["lo_s"] for r in report["rhs"][:7])
        if observed:
            assert report["trials"]
            assert all(t["accepted"] == (t["error_norm"] < 1) for t in report["trials"])
            assert all(len(t["scale"]) == 6 for t in report["trials"])
            assert result["solver_state"]["t_s"] == 300.
    assert traces[0][1]["raw_returned"] == traces[1][1]["raw_returned"]


@pytest.mark.parametrize("body", core.BODIES)
def test_all_three_guards_precede_any_force(body: str) -> None:
    b = bundle()
    b["radii_m"][body] = 2e12
    report, budget = report_and_budget()
    row: dict[str, Any] = {}
    with pytest.raises(ValueError, match="guard"):
        core.build_row(b["initial"], 0., [0.]*6, report["node_table"][0]["bodies"],
                       b["gm_m3_s2"], b["radii_m"], budget, row)
    assert "binary64_fields" not in budget.counts
    assert not any("acceleration_m_s2" in g for g in row["geometry"].values())


def test_split_assembly_preserves_small_terms_and_decimal_force() -> None:
    initial = {"epoch_tdb_s": 978995455.2304223, "position_m": [1e12, -1e12, 1e12],
               "velocity_m_s": [123., -456., 789.]}
    s, correction = 2**-25, [1e-8, -2e-8, 3e-8, 1e-4, -1e-4, 1e-4]
    hi, lo = core.split_epoch(initial["epoch_tdb_s"], s)
    bodies = {}
    for i, body in enumerate(core.BODIES):
        state = [initial["position_m"][j]+(i+1)*1e6 for j in range(3)]+[1e3, -2e3, 3e3]
        raw = [v/1000 for v in state]
        bodies[body] = {"body": body, "epoch_tdb_s": hi, "state_km_km_s": raw,
                        "state_si": [v*1000 for v in raw]}
    row: dict[str, Any] = {}
    core.build_row(initial, s, correction, bodies, dict.fromkeys(core.BODIES, 1e12),
                   dict.fromkeys(core.BODIES, 1.), core.Budget(lambda: 0., 0.), row)
    for body in core.BODIES:
        for j, value in enumerate(row["geometry"][body]["separation_m"]):
            exact = Fraction(bodies[body]["state_si"][j])-Fraction(initial["position_m"][j])
            exact -= Fraction(row["motion"]["drift_m"][j])+Fraction(correction[j])
            exact += Fraction(bodies[body]["state_si"][j+3]*lo)
            assert abs(Fraction(value)-exact) <= Fraction(math.ulp(value))
    with localcontext() as ctx:
        ctx.prec = 80
        for body in core.BODIES[:2]:
            d = [Decimal.from_float(x) for x in row["geometry"][body]["separation_m"]]
            square = sum(x*x for x in d)
            truth = [Decimal('1e12')*x/(square*square.sqrt()) for x in d]
            error = sum((Decimal.from_float(a)-t)**2 for a, t in zip(row["geometry"][body]["acceleration_m_s2"], truth, strict=True)).sqrt()
            assert error < Decimal('1e-15')
    assert "acceleration_m_s2" not in row["geometry"]["Earth"]


def test_late_native_return_is_retained_before_deadline() -> None:
    now = [0.]
    b = core.Budget(lambda: now[0], 0.)
    row: dict[str, Any] = {}
    def late(body: str, epoch: float) -> list[float]:
        now[0] = 60.
        return [1., 2., 3., 4., 5., 6.]
    with pytest.raises(ValueError, match="deadline"):
        core.query_bodies(0., bundle()["initial"], late, b, row)
    assert row["bodies"]["Sun"]["state_km_km_s"] == [1., 2., 3., 4., 5., 6.]
    assert b.counts["states"] == {"attempted": 1, "returned": 1, "completed": 0}


@pytest.mark.parametrize("operation", list(core.LIMITS))
def test_each_cap_is_enforced_before_next_operation(operation: str) -> None:
    b = core.Budget(lambda: 0., 0.)
    b.counts[operation] = {"attempted": core.LIMITS[operation], "returned": 0, "completed": 0}
    with pytest.raises(ValueError, match="cap"):
        b.event(operation, "attempt")
    assert b.counts[operation]["attempted"] == core.LIMITS[operation]


def test_interrupted_rhs_keeps_partial_raw_and_prevents_second_solve(monkeypatch: Any) -> None:
    report, budget = report_and_budget()
    monkeypatch.setitem(core.LIMITS, "rhs", 3)
    with pytest.raises(ValueError, match="cap"):
        core.solve_profile(bundle(), "normal", report, provider, budget)
    assert len(report["profiles"]) == 1
    assert len(report["rhs"]) == 3
    assert budget.counts["solves"]["attempted"] == 1
    assert budget.counts["solves"]["returned"] == 0
    assert all(r["completed"] for r in report["rhs"])
    assert report["trials"][-1]["decision"] == "unavailable"
    assert report["trials"][-1]["accepted"] is None
    assert budget.counts["trials"]["attempted"] == 1
    assert budget.counts["trials"]["completed"] == 0


@pytest.mark.parametrize("s", [-1., 301., float("nan"), True])
def test_motion_rejects_invalid_time(s: Any) -> None:
    with pytest.raises(ValueError):
        core.assemble_motion(bundle()["initial"], s, [0.]*6)


def test_invalid_si_source_rejected_before_fields() -> None:
    report, budget = report_and_budget()
    bodies = deepcopy(report["node_table"][0]["bodies"])
    bodies["Moon"]["state_si"][0] = 1.
    with pytest.raises(ValueError, match="SI mismatch"):
        core.build_row(bundle()["initial"], 0., [0.]*6, bodies, bundle()["gm_m3_s2"],
                       bundle()["radii_m"], budget, {})
    assert "binary64_fields" not in budget.counts


@pytest.mark.parametrize(("name", "expected"), [
    ("normal", {"rtol": 1e-12, "atol": [1e-7]*3+[1e-10]*3, "max_step": 5., "first_step": 1.}),
    ("tighter", {"rtol": 1e-13, "atol": [1e-8]*3+[1e-11]*3, "max_step": 2.5, "first_step": .5}),
])
def test_original_profiles_are_literal_contract_values(name: str, expected: Any) -> None:
    assert core.settings(name) == expected


def test_pinned_controller_and_coefficients_without_native_setup() -> None:
    from hashlib import sha256
    import json
    from scipy.integrate import solve_ivp
    from scipy.integrate._ivp import rk, dop853_coefficients as coeff
    path = ROOT/"docs/adr/experiments/0141-short-coast-inputs.py"
    spec = importlib.util.spec_from_file_location("corrected_preparation_identity", path)
    assert spec and spec.loader
    identity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(identity)
    frozen = json.loads((ROOT/"docs/adr/experiments/0148-short-coast-study.json").read_text())["identity"]["r5_runtime"]
    for name, function in (("solve_ivp", solve_ivp), ("rk_step", rk.rk_step),
        ("DOP853_step", rk.DOP853._step_impl), ("DOP853_error", rk.DOP853._estimate_error_norm),
        ("DOP853_dense", rk.DOP853._dense_output_impl)):
        assert identity.callable_identity(function) == frozen["callables"][name]
    for name, expected in frozen["coefficients"].items():
        array = getattr(coeff, name)
        assert list(array.shape) == expected["shape"]
        assert sha256(array.tobytes(order="C")).hexdigest() == expected["sha256"]


def test_trial_cap_stops_before_next_stage_rhs(monkeypatch: Any) -> None:
    report, budget = report_and_budget()
    monkeypatch.setitem(core.LIMITS, "trials", 0)
    with pytest.raises(ValueError, match="trials attempt cap"):
        core.solve_profile(bundle(), "normal", report, provider, budget)
    assert len(report["rhs"]) == 1  # The initial derivative is not a trial.
    assert report["trials"] == []


def test_repeated_and_backward_callbacks_each_consume_state_budget() -> None:
    b = core.Budget(lambda: 0., 0.)
    for s in (.5, .1, .1):
        row: dict[str, Any] = {}
        core.query_bodies(s, bundle()["initial"], provider, b, row)
        assert row["elapsed_s"] == s
    assert b.counts["states"]["attempted"] == 9
