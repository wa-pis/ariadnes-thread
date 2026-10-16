"""Independent D17.2 solver qualification; no retained-reference propagation."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from space_nav import bezier_local_targeting as bez
from space_nav import bounded_local_targeting as bounded
from space_nav import local_burn as local, local_targeting as target
from space_nav.errors import TrajectoryRefinementError


REFERENCE = Path("docs/adr/experiments/0104-lunar-departure-reference.json")
STUDY = Path("docs/adr/experiments/0107-local-finite-burn-study.json")
STEERING = Path("docs/adr/experiments/0110-local-steering-study.json")
BOUNDED = Path("docs/adr/experiments/0113-bound-aware-local-study.json")
SCALES = (300., 300., .1, .1, .1, .1, .1, .1)
STEPS = (1., 1., .001, .001, .001, .001, .001, .001)
ROOT = (60., 22., .02, -.03, .015, .025, .04, .01)
MATRIX = np.array(((2., 1., 0., 0., 0., 0., 1., .2),
                   (0., 3., 1., 0., 0., .3, 0., 1.),
                   (0., 0., 4., 1., .4, 0., 1., 0.),
                   (0., 0., 0., 2., 1., 0., .5, 1.),
                   (0., 0., 0., 0., 3., 1., .2, 0.),
                   (1., 0., 0., 0., 0., 4., 0., .7)))
Controls = tuple[float, ...]
Residual = Callable[[Controls], Controls]


def synthetic(duration_s: float = 20., match_s: float = 10000.) -> target._TargetDomain:
    theta = -.001*duration_s/2
    initial = (1e6*math.cos(theta), 1e6*math.sin(theta), 0.,
               -1000*math.sin(theta), 1000*math.cos(theta), 0., 2000.)
    command = local._LocalCommand(1e12, 1., 500., 1000., 450., (1., 0., 0.),
        1e9, duration_s, match_s, initial, (0., 100., 0., 0., 0., 0., 1990.), 100.)
    return target._TargetDomain(command, (1e6, 0., 0., 0., 1000., 0.),
                               (1e9-2000, 1e9+2000), 1.)


def embedded(x: Controls) -> Controls:
    return x[:4]+((x[2]+x[4])/2, (x[3]+x[5])/2)+x[4:]


def initial(domain: target._TargetDomain) -> Controls:
    return embedded(domain.initial_controls)


def budget() -> bez._BezierBudget:
    return bez._BezierBudget("D17 synthetic", 300., lambda: 0., max_arcs_per_evaluation=2)


def linear(x: Controls) -> Controls:
    return tuple(float(v) for v in 100*MATRIX@((np.asarray(x)-ROOT)/SCALES))


def state_for(domain: target._TargetDomain, x: Controls, residual: Controls) -> local.State7:
    command = domain.command(x[:4]+x[6:])
    return tuple(v+s*r for v, s, r in zip(command.target_state_si[:6],
                 target._RESIDUAL_SCALES, residual))+(command.target_state_si[6],)


def oracle(residual_at: Residual = linear, *, fail_at: int = -1,
           fail_coast: bool = False, corrupt: str | None = None,
           reference_delta: Controls = (0.,)*7, bezier_delta: Controls = (0.,)*7,
           tighter_delta: Controls = (0.,)*7,
           after: Callable[[bez._BezierBudget], None] | None = None,
           ) -> tuple[Any, Any, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []

    def evaluate(domain: target._TargetDomain, x: Controls, command: local._LocalCommand,
                 tighter: bool, shared: bez._BezierBudget,
                 evidence: dict[str, Any]) -> dict[str, Any]:
        controls = embedded(x) if len(x) == 6 else x
        role = evidence["role"]
        calls.append({"x": controls, "command": command, "role": role, "tighter": tighter})
        shared.begin_arc(first_in_evaluation=True)
        if len(calls)-1 == fail_at and not fail_coast:
            raise TrajectoryRefinementError("injected burn failure")
        shared.completed_arcs += 1
        cutoff = command.target_state_si
        evidence["cutoff_state_si"] = cutoff
        shared.begin_arc(first_in_evaluation=False)
        if len(calls)-1 == fail_at:
            raise TrajectoryRefinementError("injected coast failure")
        shared.completed_arcs += 1
        final = state_for(domain, controls, residual_at(controls))
        delta = (tighter_delta if tighter else reference_delta if role == "two-node-reference-replay"
                 else bezier_delta if role == "bezier-seed-replay" else (0.,)*7)
        final = tuple(a+b for a, b in zip(final, delta))
        if corrupt == "cutoff":
            cutoff = cutoff[:-1]+(cutoff[6]+.01,)
        elif corrupt == "coast":
            final = final[:-1]+(final[6]+.01,)
        elif corrupt == "nonfinite":
            final = (math.nan,)+final[1:]
        elif corrupt == "short":
            final = final[:-1]
        if after is not None:
            after(shared)
        return {"cutoff_state_si": cutoff, "final_state_si": final, "checked_saved_states": 4}

    return evaluate, evaluate, calls


def correct(domain: target._TargetDomain | None = None, *, residual_at: Residual = linear,
            seed: Controls | None = None, replay_delta: Controls = (0.,)*7,
            **kwargs: Any) -> tuple[dict[str, Any], bez._BezierBudget, list[dict[str, Any]]]:
    domain = domain or synthetic()
    seed = seed or initial(domain)
    evaluate, reference_evaluate, calls = oracle(residual_at, **kwargs)
    retained = state_for(domain, seed, residual_at(seed))
    retained = tuple(a+b for a, b in zip(retained, replay_delta))
    report: dict[str, Any] = {}
    shared = budget()
    bez._correct_target(domain, seed, retained, shared, report, evaluate=evaluate,
                        reference_evaluate=reference_evaluate)
    json.dumps(report, allow_nan=False)
    return report, shared, calls


def prepared(domain: target._TargetDomain, x: Controls,
             residual_at: Residual) -> tuple[Any, bez._BezierBudget, list[dict[str, Any]]]:
    evaluate, _, calls = oracle(residual_at)
    shared = budget()
    corrector = bez._Corrector(domain, x, shared, {}, evaluate)
    corrector.propose(x[:4]+x[6:], "two-node-reference-replay", None,
                      reference_evaluate=evaluate)
    corrector.propose(x, "bezier-seed-replay", None)
    corrector.objective((0.,)*8)
    return corrector, shared, calls


def complete_evaluation(shared: bez._BezierBudget, tighter: bool = False) -> None:
    shared.begin_control()
    shared.begin_evaluation(tighter)
    for first in (True, False):
        shared.begin_arc(first_in_evaluation=first)
        shared.completed_arcs += 1


@pytest.fixture
def retained() -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(path.read_text()) for path in (REFERENCE, STUDY, STEERING, BOUNDED))


@pytest.mark.parametrize("kind", ["coupled-linear", "coupled-quadratic"])
def test_real_scipy_six_by_eight_independent_roots_and_frozen_repeat(kind: str) -> None:
    assert np.linalg.matrix_rank(MATRIX) == 6

    def residual(x: Controls) -> Controls:
        z = (np.asarray(x)-ROOT)/SCALES
        response = MATRIX@(z+.02*z*z) if kind == "coupled-quadratic" else MATRIX@z
        return tuple(float(v) for v in 100*response)

    report, shared, calls = correct(residual_at=residual)
    assert report["outcome"] == "local-qualified" and report["agreement"] == "pass"
    assert report["mission_qualified"] is False
    selected = report["proposals"][report["selected_objective"]]
    repeated = report["proposals"][-1]
    assert selected["role"] == "objective" and selected["closure"] == repeated["closure"] == "pass"
    assert repeated["role"] == "frozen-repeat" and repeated["controls"] == selected["controls"]
    assert repeated["parent"] == selected["id"]
    assert report["solver_stop"] == "physical-closure-before-jacobian"
    assert report["jacobians"][-1]["parent"] < selected["id"]
    assert shared.objective_requests == sum(e["role"] == "objective" for e in report["proposals"])
    assert shared.nominal_evaluations == len(calls)-1
    assert shared.native_arc_propagations == shared.completed_arcs == 2*len(calls)
    assert shared.tighter_evaluations == 1 and sum(c["tighter"] for c in calls) == 1
    assert report["solver_settings"] == bounded._SETTINGS
    assert [c["role"] for c in calls[:2]] == ["two-node-reference-replay", "bezier-seed-replay"]
    assert report["baseline_replay"] == report["embedding_replay"] == "pass"
    assert report["embedding_replay_differences_si"] == {
        "fresh_reference": (0., 0., 0.), "retained_reference": (0., 0., 0.)}
    assert report["proposals"][0]["model_id"] == "local-moon-point-mass-steered-burn-v1"
    assert all(e["model_id"] == "local-moon-point-mass-bezier-burn-v1" for e in report["proposals"][1:])
    domain = synthetic()
    for call in calls:
        command = call["command"]
        assert command.target_state_si[:6] == domain.baseline.target_state_si[:6]
        assert command.ignition_epoch_tdb_s+command.match_after_ignition_s == domain.match_epoch_tdb_s
        expected_mass_kg = 2000.-1000.*call["x"][1]/(9.80665*450.)
        assert abs(command.target_state_si[6]-expected_mass_kg) <= 1e-10


@pytest.mark.parametrize("location,kind", [("middle", "central"), ("lower", "forward"), ("upper", "backward")])
def test_all_sixteen_quadratic_stencils_scaling_and_free_face(location: str, kind: str) -> None:
    domain = synthetic()
    lo, hi = bez._bounds(domain)
    x = initial(domain) if location == "middle" else lo if location == "lower" else hi
    coefficients = np.arange(1., 49.).reshape(6, 8)/100

    def residual(control: Controls) -> Controls:
        z = np.asarray(control)/SCALES
        return tuple(float(v) for v in 100+coefficients@(z*z+2*z))

    corrector, shared, calls = prepared(domain, x, residual)
    actual = corrector.jacobian((0.,)*8)
    expected = coefficients*(2*np.asarray(x)/SCALES+2)
    np.testing.assert_allclose(actual, expected, atol=3e-9, rtol=0)
    record = corrector.jacobians[0]
    assert record["stencils"] == [kind]*8 and len(record["probe_ids"]) == 16
    assert len(record["matrix"]) == 6 and all(len(row) == 8 for row in record["matrix"])
    assert len(record["singular_values"]) == 6 and record["rank"] <= 6
    assert tuple(record["face_free_mask"]) == (location == "middle",)*8
    assert shared.jacobian_batches == 1 and shared.nominal_evaluations == len(calls) == 18
    assert shared.objective_requests == 1 and all(c["role"] == "probe" for c in calls[2:])
    assert all(e["parent"] == 2 for e in corrector.entries[3:])
    offsets = (1., -1.) if kind == "central" else (1., 2.) if kind == "forward" else (-1., -2.)
    for j, h in enumerate(STEPS):
        for k, multiplier in enumerate(offsets):
            assert calls[2+2*j+k]["x"] == tuple(v+(multiplier*h if i == j else 0.)
                                                  for i, v in enumerate(x))


def test_full_stencil_preflight_rejects_eighth_control_without_any_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, initial(domain), linear)
    original = bez._command

    def blocked(d: target._TargetDomain, x: Controls) -> local._LocalCommand:
        if d is domain and x[7] != 0:
            raise ValueError("eighth coordinate unavailable")
        return original(d, x)

    monkeypatch.setattr(bez, "_command", blocked)
    with pytest.raises(ValueError, match="derivative-domain-unresolved: D17 coordinate 7"):
        corrector.jacobian((0.,)*8)
    assert shared.jacobian_batches == 0 and shared.nominal_evaluations == len(calls) == 2


def test_full_timing_box_not_just_seed() -> None:
    domain = synthetic(match_s=1000.)
    domain.command(domain.initial_controls)
    report, shared, calls = correct(domain)
    assert report["outcome"] == "domain-unresolved" and "coupled timing box" in report["reason"]
    assert shared.native_arc_propagations == 0 and calls == []


def test_exact_single_seed_cache_excludes_old_model_and_later_requests() -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, initial(domain), linear)
    assert shared.objective_requests == 1 and shared.nominal_evaluations == 2
    cached = corrector.entries[2]
    assert cached["cache_hit"] is True and cached["cache_source"] == cached["parent"] == 1
    assert corrector.report["best_objective"] == 1
    corrector.objective((0.,)*8)
    corrector.objective((0.,)*8)
    assert shared.objective_requests == 3 and shared.nominal_evaluations == len(calls) == 4
    assert [e["cache_hit"] for e in corrector.entries] == [False, False, True, False, False]


def test_initial_solver_adjustment_stops_without_new_native() -> None:
    domain = synthetic()
    evaluate, reference_evaluate, calls = oracle()
    shared = budget()
    seed = initial(domain)
    corrector = bez._Corrector(domain, seed, shared, {}, evaluate)
    corrector.propose(seed[:4]+seed[6:], "two-node-reference-replay", None,
                      reference_evaluate=reference_evaluate)
    corrector.propose(seed, "bezier-seed-replay", 0)
    with pytest.raises(ValueError, match="initial solver request changed"):
        corrector.objective((1e-10, 0., 0., 0., 0., 0., 0., 0.))
    assert shared.objective_requests == 1 and len(calls) == 2


def test_real_scipy_boundary_seed_adjustment_is_never_silently_repaired() -> None:
    report, shared, calls = correct(seed=(0., 20., -1., 0., -.5, 0., 0., 0.))
    assert report["outcome"] == "failed" and "initial solver request changed" in report["reason"]
    assert len(calls) == shared.nominal_evaluations == 2 and shared.objective_requests == 1
    assert shared.jacobian_batches == shared.tighter_evaluations == 0


def test_first_closed_objective_unwinds_before_next_jacobian(monkeypatch: pytest.MonkeyPatch) -> None:
    import scipy.optimize

    entered: list[str] = []

    def optimizer(fun: Callable[..., Any], y: Controls, **kwargs: Any) -> None:
        fun(y)
        point = tuple((a-b)/s for a, b, s in zip(ROOT, initial(synthetic()), SCALES))
        entered.append("objective")
        fun(point)
        entered.append("jacobian")
        kwargs["jac"](point)

    monkeypatch.setattr(scipy.optimize, "least_squares", optimizer)
    report, shared, calls = correct()
    assert entered == ["objective"] and report["outcome"] == "local-qualified"
    assert [c["role"] for c in calls] == ["two-node-reference-replay", "bezier-seed-replay",
                                         "objective", "frozen-repeat"]
    assert shared.jacobian_batches == 0 and shared.objective_requests == 2


def test_best_objective_not_necessarily_accepted_or_selected() -> None:
    domain = synthetic()
    corrector, _, _ = prepared(domain, initial(domain), linear)
    corrector.jacobian((0.,)*8)
    corrector.objective(tuple((a-b)/(2*s) for a, b, s in zip(ROOT, initial(domain), SCALES)))
    best = corrector.report["best_objective"]
    assert best == corrector.entries[-1]["id"] and corrector.entries[best]["role"] == "objective"
    assert corrector.entries[best]["accepted_iterate"] is False and corrector.accepted == [2]
    assert corrector.report["selected_objective"] is None


def test_jacobian_requires_exact_completed_center() -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, initial(domain), linear)
    with pytest.raises(ValueError, match="completed objective center"):
        corrector.jacobian((.1, 0., 0., 0., 0., 0., 0., 0.))
    assert shared.jacobian_batches == 0 and len(calls) == 2


@pytest.mark.parametrize("value", [True, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("index", range(8))
def test_nonfinite_or_boolean_solver_coordinates_stop_before_native(index: int, value: float) -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, initial(domain), linear)
    point = [0.]*8
    point[index] = value
    with pytest.raises(ValueError):
        corrector.objective(tuple(point))
    assert shared.objective_requests == 2 and shared.nominal_evaluations == len(calls) == 2


@pytest.mark.parametrize("size", [0, 6, 7, 9])
def test_eight_control_shape_is_distinct_from_six_residuals(size: int) -> None:
    with pytest.raises(ValueError):
        bez._eight((0.,)*size, "controls")
    assert target._six((0.,)*6, "residual") == (0.,)*6


def test_wrong_scipy_version_fails_before_either_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    original = bez.import_module

    def imported(name: str) -> Any:
        return SimpleNamespace(__version__="1.17.2") if name == "scipy" else original(name)

    monkeypatch.setattr(bez, "import_module", imported)
    report, shared, calls = correct()
    assert report["outcome"] == "failed" and "pinned Conda SciPy 1.17.1" in report["reason"]
    assert calls == [] and shared.native_arc_propagations == shared.objective_requests == 0


@pytest.mark.parametrize("delta,outcome", [((0.,)*7, "local-qualified"),
    ((1.01, 0., 0., 0., 0., 0., 0.), "tighter-unqualified"),
    ((0., 0., 0., .00101, 0., 0., 0.), "tighter-unqualified"),
    ((11., 0., 0., 0., 0., 0., 0.), "tighter-unqualified")])
def test_closed_new_seed_precedes_optimizer_and_gets_one_tighter(delta: Controls, outcome: str) -> None:
    report, shared, calls = correct(residual_at=lambda x: (0.,)*6, tighter_delta=delta)
    assert report["outcome"] == outcome
    assert [c["role"] for c in calls] == ["two-node-reference-replay", "bezier-seed-replay", "frozen-repeat"]
    assert report["selected_objective"] == 1 and report["best_objective"] == 1
    assert shared.objective_requests == shared.jacobian_batches == 0
    assert shared.propagation_evaluations == 3 and shared.native_arc_propagations == 6


def test_closed_old_reference_alone_is_never_eligible() -> None:
    # Reference can close but the embedded chart may differ within the replay gate.
    report, shared, _ = correct(residual_at=lambda x: (1.01, 0., 0., 0., 0., 0.),
                                reference_delta=(-.2, 0., 0., 0., 0., 0., 0.))
    assert report["proposals"][0]["closure"] == "pass"
    assert report["proposals"][1]["closure"] == "fail"
    assert report["outcome"] == "stationary-unclosed" and report["best_objective"] == 1
    assert report["selected_objective"] is None and shared.tighter_evaluations == 0


def test_closed_probes_do_not_qualify() -> None:
    domain = synthetic()
    seed = initial(domain)

    def residual(x: Controls) -> Controls:
        return (100.,)*6 if x == seed else (0.,)*6

    corrector, shared, calls = prepared(domain, seed, residual)
    corrector.jacobian((0.,)*8)
    assert all(e["closure"] == "pass" for e in corrector.entries[3:])
    assert corrector.report["selected_objective"] is None and corrector.report["best_objective"] == 1
    assert shared.tighter_evaluations == 0 and len(calls) == 18


def test_constant_rank_loss_and_vector_norm_are_not_qualification() -> None:
    report, shared, _ = correct(residual_at=lambda x: (.8, .8, 0., .8, .8, 0.))
    assert report["outcome"] == "stationary-unclosed" and report["proposals"][1]["closure"] == "fail"
    record = report["jacobians"][0]
    assert record["rank"] == 0 and record["condition_number"] is None
    assert len(record["singular_values"]) == 6 and record["free_rank"] == 0
    assert report["solver_result"]["status"] == 1 and shared.tighter_evaluations == 0
    assert len(report["solver_result"]["gradient"]) == len(report["solver_result"]["active_mask"]) == 8


def test_rank_six_succeeds_without_impossible_rank_eight_gate() -> None:
    domain = synthetic()
    corrector, shared, _ = prepared(domain, initial(domain), linear)
    actual = corrector.jacobian((0.,)*8)
    np.testing.assert_allclose(actual, 100*MATRIX, atol=2e-9, rtol=0)
    record = corrector.jacobians[0]
    assert record["rank"] == record["free_rank"] == 6 and shared.completed_jacobian_batches == 1
    expected_gradient = np.asarray(actual).T@linear(initial(domain))
    np.testing.assert_allclose(record["gradient"], expected_gradient, atol=2e-7, rtol=0)
    assert record["gradient_parent"] == record["parent"] == 2
    lower, upper = bez._bounds(domain)
    np.testing.assert_array_equal(record["bound_margins"]["lower"], np.subtract(initial(domain), lower))
    np.testing.assert_array_equal(record["bound_margins"]["upper"], np.subtract(upper, initial(domain)))


def test_free_column_rank_at_active_face_is_distinct_from_full_row_rank() -> None:
    domain = synthetic()
    seed = list(initial(domain))
    seed[2], seed[4], seed[7] = -1., 1., -1.
    corrector, _, _ = prepared(domain, tuple(seed), linear)
    corrector.jacobian((0.,)*8)
    record = corrector.jacobians[0]
    assert record["rank"] == 6 and record["free_rank"] == 5
    assert tuple(record["face_free_mask"]) == (True, True, False, True, False, True, True, False)
    assert record["parent"] == 2


def test_real_scipy_bound_active_unattainable_target_stays_unqualified() -> None:
    upper = synthetic().delta_bounds_s[1]

    def residual(x: Controls) -> Controls:
        return ((x[0]-upper-300)/3, 0., 0., 0., 0., 0.)

    report, shared, _ = correct(residual_at=residual)
    assert report["outcome"] in ("stationary-unclosed", "stagnated-unclosed")
    assert report["solver_result"]["active_mask"][0] == 1
    assert report["selected_objective"] is None and shared.tighter_evaluations == 0
    assert all(e["closure"] == "fail" for e in report["proposals"])


@pytest.mark.parametrize("status,outcome", [(1, "stationary-unclosed"), (2, "stagnated-unclosed"),
    (3, "stagnated-unclosed"), (4, "stagnated-unclosed"), (0, "budget-exhausted"), (-2, "failed")])
def test_solver_success_never_replaces_physical_closure(
    monkeypatch: pytest.MonkeyPatch, status: int, outcome: str,
) -> None:
    import scipy.optimize

    def optimizer(fun: Callable[..., Any], y: Controls, **kwargs: Any) -> SimpleNamespace:
        fun(y)
        return SimpleNamespace(x=y, status=status, message="injected exit", nfev=1, njev=0,
                               active_mask=(0.,)*8, grad=(0.,)*8, optimality=0.)

    monkeypatch.setattr(scipy.optimize, "least_squares", optimizer)
    report, shared, calls = correct()
    assert report["outcome"] == outcome and shared.tighter_evaluations == 0 and len(calls) == 2


@pytest.mark.parametrize("delta", [(1.01, 0., 0., 0., 0., 0., 0.),
    (0., 0., 0., .00101, 0., 0., 0.), (0., 0., 0., 0., 0., 0., 1.01e-6)])
def test_reference_replay_mismatch_stops_before_bezier(delta: Controls) -> None:
    report, shared, calls = correct(replay_delta=delta)
    assert report["outcome"] in ("baseline-replay-mismatch", "reference-replay-mismatch")
    assert len(calls) == 1 and shared.objective_requests == shared.jacobian_batches == 0


@pytest.mark.parametrize("delta", [(1.01, 0., 0., 0., 0., 0., 0.),
    (0., 0., 0., .00101, 0., 0., 0.), (0., 0., 0., 0., 0., 0., 1.01e-6)])
def test_bezier_seed_mismatch_stops_before_derivatives(delta: Controls) -> None:
    report, shared, calls = correct(bezier_delta=delta)
    assert report["outcome"] in ("baseline-replay-mismatch", "embedding-replay-mismatch", "failed")
    assert len(calls) == 2 and shared.objective_requests == shared.jacobian_batches == 0


def test_both_seed_comparisons_are_required_not_just_retained_endpoint() -> None:
    report, shared, calls = correct(reference_delta=(.8, 0., 0., 0., 0., 0., 0.),
                                   bezier_delta=(-.8, 0., 0., 0., 0., 0., 0.))
    assert report["outcome"] in ("baseline-replay-mismatch", "embedding-replay-mismatch")
    assert len(calls) == 2 and shared.objective_requests == shared.jacobian_batches == 0


@pytest.mark.parametrize("coast", [False, True])
def test_tighter_failure_never_resumes_or_retries(coast: bool) -> None:
    report, shared, calls = correct(residual_at=lambda x: (0.,)*6, fail_at=2, fail_coast=coast)
    assert report["outcome"] == "failed" and shared.tighter_evaluations == 1
    assert [c["role"] for c in calls] == ["two-node-reference-replay", "bezier-seed-replay", "frozen-repeat"]
    assert shared.objective_requests == shared.jacobian_batches == 0
    assert shared.native_arc_propagations == shared.completed_arcs+1


@pytest.mark.parametrize("corrupt", ["cutoff", "coast", "nonfinite", "short"])
def test_invalid_endpoint_has_no_penalty_or_retry(corrupt: str) -> None:
    report, shared, calls = correct(corrupt=corrupt)
    assert report["outcome"] == "failed" and report["proposals"][0]["outcome"] == "failed"
    assert len(calls) == 1 and shared.objective_requests == shared.jacobian_batches == 0
    assert report["proposals"][0]["final_state_si"] is None


@pytest.mark.parametrize("fail_at,coast", [(0, False), (0, True), (1, False), (1, True), (2, True)])
def test_failed_arc_aborts_and_preserves_completed_cutoff(fail_at: int, coast: bool) -> None:
    report, shared, calls = correct(fail_at=fail_at, fail_coast=coast)
    assert report["outcome"] == "failed" and len(calls) == fail_at+1
    assert shared.native_arc_propagations == shared.completed_arcs+1
    failed = report["proposals"][-1]
    assert failed["final_state_si"] is None and shared.tighter_evaluations == 0
    assert (failed["cutoff_state_si"] is not None) == coast


def test_681_nominal_plus_one_reserved_tighter_and_1364_native_launches() -> None:
    shared = budget()
    for _ in range(681):
        complete_evaluation(shared)
    assert shared.nominal_evaluations == shared.propagation_evaluations == 681
    assert shared.native_arc_propagations == shared.completed_arcs == 1362
    with pytest.raises(ValueError, match="tighter pair remains reserved"):
        shared.begin_evaluation(False)
    complete_evaluation(shared, True)
    assert shared.nominal_evaluations == 681 and shared.propagation_evaluations == 682
    assert shared.tighter_evaluations == 1 and shared.native_arc_propagations == 1364
    with pytest.raises(ValueError, match="no retry"):
        shared.begin_control()


def test_independent_objective_and_batch_ceilings_are_both_40() -> None:
    shared = budget()
    for _ in range(40):
        shared.begin_objective()
    with pytest.raises(ValueError, match="objective-request limit 40"):
        shared.begin_objective()
    assert shared.objective_requests == 40 and shared.propagation_evaluations == 0
    shared = budget()
    for _ in range(40):
        shared.begin_batch()
        for _ in range(16):
            complete_evaluation(shared)
    with pytest.raises(ValueError, match="Jacobian-batch limit 40"):
        shared.begin_batch()
    assert shared.jacobian_batches == 40 and shared.nominal_evaluations == 640


@pytest.mark.parametrize("limit", ["objectives", "jacobians"])
def test_solver_callbacks_cannot_bypass_independently_counted_limits(monkeypatch: pytest.MonkeyPatch, limit: str) -> None:
    import scipy.optimize

    def optimizer(fun: Callable[..., Any], y: Controls, **kwargs: Any) -> None:
        if limit == "objectives":
            for _ in range(41):
                fun(y)
        else:
            fun(y)
            for _ in range(41):
                kwargs["jac"](y)

    monkeypatch.setattr(scipy.optimize, "least_squares", optimizer)
    report, shared, calls = correct()
    assert report["outcome"] == "budget-exhausted" and shared.tighter_evaluations == 0
    assert report["solver_result"] is None
    if limit == "objectives":
        assert shared.objective_requests == 40 and shared.nominal_evaluations == len(calls) == 41
        assert shared.native_arc_propagations == 82
    else:
        assert shared.jacobian_batches == 40 and shared.nominal_evaluations == len(calls) == 642
        assert shared.native_arc_propagations == 1284


def test_unaffordable_full_batch_launches_none_of_sixteen_probes() -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, initial(domain), linear)
    shared.nominal_evaluations = shared.propagation_evaluations = 666
    shared.native_arc_propagations = shared.completed_arcs = 1332
    shared._evaluation_start_arcs = 1330
    with pytest.raises(ValueError, match="complete sixteen-probe batch cannot fit"):
        corrector.jacobian((0.,)*8)
    assert shared.jacobian_batches == 0 and len(calls) == 2


def test_incomplete_arc_rejects_all_further_work_entries() -> None:
    shared = budget()
    shared.begin_control()
    shared.begin_evaluation(False)
    shared.begin_arc(first_in_evaluation=True)
    for operation in (shared.begin_control, shared.begin_objective, shared.begin_batch):
        with pytest.raises(ValueError, match="no retry"):
            operation()
    with pytest.raises(ValueError, match="no retry"):
        shared.begin_evaluation(False)
    with pytest.raises(ValueError, match="no retry"):
        shared.begin_arc(first_in_evaluation=False)
    assert shared.native_arc_propagations == 1 and shared.completed_arcs == 0


@pytest.mark.parametrize("at", [300., 301.])
def test_late_completed_endpoint_keeps_budget_failure_classification(at: float) -> None:
    def expire(shared: bez._BezierBudget) -> None:
        shared.monotonic = lambda: at

    report, shared, calls = correct(after=expire)
    assert report["outcome"] == "budget-exhausted" and "deadline" in report["reason"]
    assert len(calls) == 1 and shared.completed_arcs == 2
    assert report["proposals"][0]["final_state_si"] is None


def test_retained_pinned_binding_selects_accepted_158_without_native_work(retained: Any) -> None:
    reference, study, steering, old = retained
    domain, endpoint = bez._bind_references(reference, study, steering, old,
                                            tuple(study["launch_window_tdb_s"]))
    assert endpoint == tuple(old["proposals"][158]["final_state_si"])
    assert old["proposals"][158]["accepted_iterate"] is True
    assert bez._SEED == embedded(tuple(old["proposals"][158]["controls"]))
    assert bez._SEED != embedded(tuple(old["proposals"][262]["controls"]))
    lower, upper = bez._bounds(domain)
    assert all(lo < x < hi for lo, x, hi in zip(lower, bez._SEED, upper))
    assert upper[1]-bez._SEED[1] == pytest.approx(.003043997508, abs=1e-10)
    assert domain.match_epoch_tdb_s == 979002340.6346419
    for path, expected in ((REFERENCE, local._REFERENCE_SHA256), (STUDY, target._STUDY_SHA256),
                           (STEERING, bounded._STEERING_SHA256),
                           (BOUNDED, "417f4a33e6407a37e9a41caff29330557f39d7a3bbfc34e9b908cc1d5589cb89")):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


@pytest.mark.parametrize("key", ["candidate", "model", "algorithm", "profile", "resource", "endpoint", "residual",
    "mass", "seed", "accepted", "command", "units", "counter", "target", "numpy-version", "scipy-version"])
def test_pure_binder_rejects_inconsistent_retained_evidence(retained: Any, key: str) -> None:
    reference, study, steering, saved = retained
    old = deepcopy(saved)
    if key == "candidate":
        old["candidate_id"] = "other"
    elif key == "model":
        old["model_id"] = "other"
    elif key == "algorithm":
        old["algorithm_id"] = "other"
    elif key == "profile":
        old["profiles"]["nominal"]["maximum_step_s"] = 99.
    elif key == "resource":
        old["retained_lunar_resource"]["orbit_shape_radius_m"] += 1
    elif key == "endpoint":
        old["proposals"][158]["final_state_si"][0] += 1
    elif key == "residual":
        old["proposals"][158]["scaled_residual"][0] += 1
    elif key == "mass":
        old["proposals"][158]["cutoff_state_si"][6] += .01
    elif key == "seed":
        old["proposals"][158]["controls"][0] += 1
    elif key == "accepted":
        old["proposals"][158]["accepted_iterate"] = False
    elif key == "command":
        old["proposals"][158]["command"]["isp_s"] += 1
    elif key == "units":
        old["units"] = "km"
    elif key == "counter":
        old["nominal_evaluations"] -= 1
    elif key == "target":
        old["binding"]["baseline"]["target_state_si"][0] += 1
    elif key == "numpy-version":
        old["runtime_versions"]["numpy"] = "changed"
    elif key == "scipy-version":
        old["runtime_versions"]["scipy"] = "1.17.2"
    with pytest.raises(ValueError):
        bez._bind_references(reference, study, steering, old, tuple(study["launch_window_tdb_s"]))


def test_runner_clock_includes_binding_before_both_replays() -> None:
    ticks = iter((0., 300.))
    report = bez._run_bezier_local_targeting(REFERENCE, STUDY, STEERING, BOUNDED,
                                             monotonic=lambda: next(ticks))
    assert report["outcome"] == "budget-exhausted" and report["native_arc_propagations"] == 0
    assert report["elapsed_wall_s"] == 300.
    json.dumps(report, allow_nan=False)


def test_runner_provenance_and_counts_with_pure_injected_campaign(monkeypatch: pytest.MonkeyPatch, retained: Any) -> None:
    _, study, steering, old = retained
    window = iter(study["launch_window_tdb_s"])
    monkeypatch.setattr(local.ephemeris, "utc_to_tdb", lambda text: next(window))
    monkeypatch.setattr(local.ephemeris, "kernel_metadata", lambda: {"synthetic": True})
    original = bez._correct_target

    def injected(domain: target._TargetDomain, seed: Controls, endpoint: local.State7,
                 shared: bez._BezierBudget, report: dict[str, Any]) -> None:
        residual = tuple((a-b)/s for a, b, s in zip(endpoint[:6], domain.baseline.target_state_si[:6],
                                                  target._RESIDUAL_SCALES))
        evaluate, reference_evaluate, _ = oracle(lambda x: residual)
        original(domain, seed, endpoint, shared, report, evaluate=evaluate,
                 reference_evaluate=reference_evaluate)

    monkeypatch.setattr(bez, "_correct_target", injected)
    report = bez._run_bezier_local_targeting(REFERENCE, STUDY, STEERING, BOUNDED, monotonic=lambda: 0.)
    status = report["solver_result"]["status"]
    assert report["outcome"] == ("stationary-unclosed" if status == 1 else "stagnated-unclosed")
    assert status in (1, 2, 3, 4)
    assert report["baseline_replay"] == report["embedding_replay"] == "pass"
    assert report["jacobian_batches"] >= 1 and report["tighter_evaluations"] == 0
    assert report["nominal_evaluations"] == 1+report["objective_requests"]+16*report["jacobian_batches"]
    assert report["native_arc_propagations"] == report["completed_arcs"] == 2*report["nominal_evaluations"]
    assert sum(entry["cache_hit"] for entry in report["proposals"]) == 1
    assert report["model_id"] == "local-moon-point-mass-bezier-burn-v1"
    assert report["algorithm_id"] == "bound-aware-bezier-trf-v1"
    assert report["runtime_versions"]["scipy"] == "1.17.1"
    assert report["historical_source_sha256"]["0110"] == steering["source_sha256"]
    assert report["historical_source_sha256"]["0113"] == old["source_sha256"]
    assert "bezier_local_targeting.py" in report["source_sha256"]
    assert json.loads(json.dumps(report["profiles"])) == study["profiles"]
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("index", range(4))
def test_runner_hash_error_precedes_binding_or_native(index: int, tmp_path: Path) -> None:
    paths = [REFERENCE, STUDY, STEERING, BOUNDED]
    wrong = tmp_path/"wrong.json"
    wrong.write_text("{}")
    paths[index] = wrong
    report = bez._run_bezier_local_targeting(*paths, monotonic=lambda: 0.)
    assert report["outcome"] == "failed" and "SHA256 mismatch" in report["reason"]
    assert report["native_arc_propagations"] == report["propagation_evaluations"] == 0
    json.dumps(report, allow_nan=False)
