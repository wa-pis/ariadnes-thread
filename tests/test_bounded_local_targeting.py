"""D16.2 synthetic qualification; never execute the retained D16.3 study."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from space_nav import bounded_local_targeting as bounded
from space_nav import local_burn as local, local_targeting as target
from space_nav.errors import TrajectoryRefinementError


REFERENCE = Path("docs/adr/experiments/0104-lunar-departure-reference.json")
STUDY = Path("docs/adr/experiments/0107-local-finite-burn-study.json")
STEERING = Path("docs/adr/experiments/0110-local-steering-study.json")
ROOT = (60., 22., .02, -.03, .04, .01)
Residual = Callable[[target.Controls], target.Controls]


def synthetic(duration_s: float = 20., match_s: float = 10000.) -> target._TargetDomain:
    theta = -.001*duration_s/2
    initial = (1e6*math.cos(theta), 1e6*math.sin(theta), 0.,
               -1000*math.sin(theta), 1000*math.cos(theta), 0., 2000.)
    command = local._LocalCommand(1e12, 1., 500., 1000., 450., (1., 0., 0.),
        1e9, duration_s, match_s, initial, (0., 100., 0., 0., 0., 0., 1990.), 100.)
    return target._TargetDomain(command, (1e6, 0., 0., 0., 1000., 0.),
                               (1e9-2000, 1e9+2000), 1.)


def budget() -> bounded._BoundBudget:
    return bounded._BoundBudget("D16 synthetic", 300., lambda: 0., max_arcs_per_evaluation=2)


def linear(x: target.Controls) -> target.Controls:
    return tuple(100*(a-b)/s for a, b, s in zip(x, ROOT, target._CONTROL_SCALES))


def state_for(domain: target._TargetDomain, x: target.Controls,
              residual: target.Controls) -> local.State7:
    command = domain.command(x)
    return tuple(v+s*r for v, s, r in zip(command.target_state_si[:6],
                 target._RESIDUAL_SCALES, residual))+(command.target_state_si[6],)


def oracle(residual_at: Residual = linear, *, fail_at: int = -1,
           fail_coast: bool = False, corrupt: str | None = None,
           tighter_delta: tuple[float, ...] = (0.,)*7,
           after: Callable[[bounded._BoundBudget], None] | None = None,
           ) -> tuple[target.Evaluator, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []

    def evaluate(domain: target._TargetDomain, x: target.Controls, command: local._LocalCommand,
                 tighter: bool, shared: target._TargetBudget,
                 evidence: dict[str, Any]) -> dict[str, Any]:
        calls.append({"x": x, "command": command, "role": evidence["role"], "tighter": tighter})
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
        final = state_for(domain, x, residual_at(x))
        if tighter:
            final = tuple(a+b for a, b in zip(final, tighter_delta))
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

    return evaluate, calls


def correct(domain: target._TargetDomain | None = None, *, residual_at: Residual = linear,
            seed: target.Controls | None = None, replay_delta: tuple[float, ...] = (0.,)*7,
            **kwargs: Any) -> tuple[dict[str, Any], bounded._BoundBudget, list[dict[str, Any]]]:
    domain = domain or synthetic()
    seed = seed or domain.initial_controls
    evaluate, calls = oracle(residual_at, **kwargs)
    retained = state_for(domain, seed, residual_at(seed))
    retained = tuple(a+b for a, b in zip(retained, replay_delta))
    report: dict[str, Any] = {}
    shared = budget()
    bounded._correct_target(domain, seed, retained, shared, report, evaluate=evaluate)
    json.dumps(report, allow_nan=False)
    return report, shared, calls


def prepared(domain: target._TargetDomain, x: target.Controls,
             residual_at: Residual) -> tuple[bounded._Corrector, bounded._BoundBudget, list[dict[str, Any]]]:
    evaluate, calls = oracle(residual_at)
    shared = budget()
    corrector = bounded._Corrector(domain, x, shared, {}, evaluate)
    corrector.propose(x, "seed-replay", None)
    corrector.objective((0.,)*6)
    return corrector, shared, calls


def complete_evaluation(shared: bounded._BoundBudget, tighter: bool = False) -> None:
    shared.begin_control()
    shared.begin_evaluation(tighter)
    for first in (True, False):
        shared.begin_arc(first_in_evaluation=first)
        shared.completed_arcs += 1


@pytest.fixture
def retained() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return tuple(json.loads(path.read_text()) for path in (REFERENCE, STUDY, STEERING))


@pytest.mark.parametrize("kind", ["linear", "quadratic", "coupled"])
def test_real_scipy_independent_roots_and_frozen_repeat(kind: str) -> None:
    matrix = np.array(((2., 1., 0., 0., 0., 0.), (0., 3., 1., 0., 0., 0.),
                       (0., 0., 4., 1., 0., 0.), (0., 0., 0., 2., 1., 0.),
                       (0., 0., 0., 0., 3., 1.), (1., 0., 0., 0., 0., 4.)))

    def residual(x: target.Controls) -> target.Controls:
        z = np.array([(a-b)/s for a, b, s in zip(x, ROOT, target._CONTROL_SCALES)])
        answer = 100*(z+.02*z*z) if kind == "quadratic" else 100*(matrix@z if kind == "coupled" else z)
        return tuple(float(v) for v in answer)

    report, shared, calls = correct(residual_at=residual)
    assert report["outcome"] == "local-qualified"
    assert report["baseline_replay"] == report["agreement"] == "pass"
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


@pytest.mark.parametrize("location,kind", [("middle", "central"), ("lower", "forward"), ("upper", "backward")])
def test_quadratic_stencil_derivatives_and_units(location: str, kind: str) -> None:
    domain = synthetic()
    lo, hi = bounded._bounds(domain)
    x = domain.initial_controls if location == "middle" else lo if location == "lower" else hi
    coefficients = np.arange(1., 37.).reshape(6, 6)/100

    def residual(control: target.Controls) -> target.Controls:
        z = np.asarray(control)/np.asarray(target._CONTROL_SCALES)
        return tuple(float(v) for v in 100+coefficients@(z*z+2*z))

    corrector, shared, calls = prepared(domain, x, residual)
    actual = corrector.jacobian((0.,)*6)
    z = np.asarray(x)/np.asarray(target._CONTROL_SCALES)
    expected = coefficients*(2*z+2)
    np.testing.assert_allclose(actual, expected, atol=2e-9, rtol=0)
    assert corrector.jacobians[0]["stencils"] == [kind]*6
    assert shared.jacobian_batches == 1 and shared.nominal_evaluations == 13
    assert shared.objective_requests == 1 and len(calls) == 13
    assert all(c["role"] == "probe" for c in calls[1:])
    assert all(e["parent"] == 1 for e in corrector.entries[2:])
    offsets = (1., -1.) if kind == "central" else (1., 2.) if kind == "forward" else (-1., -2.)
    for j, h in enumerate(target._PROBE_STEPS):
        for k, multiplier in enumerate(offsets):
            point = calls[1+2*j+k]["x"]
            assert point == tuple(v+(multiplier*h if i == j else 0.) for i, v in enumerate(x))


def test_full_stencil_preflight_rejects_sixth_coordinate_without_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, domain.initial_controls, linear)
    original = target._TargetDomain.command

    def blocked(self: target._TargetDomain, x: target.Controls) -> local._LocalCommand:
        if self is domain and x[5] != 0:
            raise ValueError("sixth coordinate unavailable")
        return original(self, x)

    monkeypatch.setattr(target._TargetDomain, "command", blocked)
    with pytest.raises(ValueError, match="derivative-domain-unresolved: coordinate 5"):
        corrector.jacobian((0.,)*6)
    assert shared.jacobian_batches == 0 and shared.nominal_evaluations == 1 and len(calls) == 1


def test_full_timing_box_not_seed_only() -> None:
    domain = synthetic(match_s=1000.)
    domain.command(domain.initial_controls)
    report, shared, calls = correct(domain)
    assert report["outcome"] == "domain-unresolved" and "coupled timing box" in report["reason"]
    assert shared.native_arc_propagations == 0 and calls == []


def test_exact_initial_cache_once_and_no_later_cache() -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, domain.initial_controls, linear)
    assert shared.objective_requests == 1 and shared.nominal_evaluations == 1
    assert corrector.entries[1]["cache_hit"] is True and corrector.entries[1]["cache_source"] == 0
    corrector.objective((0.,)*6)
    corrector.objective((0.,)*6)
    assert shared.objective_requests == shared.nominal_evaluations == len(calls) == 3
    assert [e["cache_hit"] for e in corrector.entries] == [False, True, False, False]


def test_initial_adjusted_seed_rejected_before_new_native() -> None:
    domain = synthetic()
    evaluate, calls = oracle()
    shared = budget()
    corrector = bounded._Corrector(domain, domain.initial_controls, shared, {}, evaluate)
    corrector.propose(domain.initial_controls, "seed-replay", None)
    with pytest.raises(ValueError, match="initial solver request changed"):
        corrector.objective((1e-10, 0., 0., 0., 0., 0.))
    assert shared.objective_requests == 1 and len(calls) == 1


def test_real_scipy_boundary_seed_adjustment_cannot_change_seed() -> None:
    report, shared, calls = correct(seed=(0., 20., -1., 0., 0., 0.))
    assert report["outcome"] == "failed" and "initial solver request changed" in report["reason"]
    assert len(calls) == shared.nominal_evaluations == shared.objective_requests == 1
    assert shared.jacobian_batches == shared.tighter_evaluations == 0


def test_first_closed_objective_interrupts_before_fake_solver_jacobian(monkeypatch: pytest.MonkeyPatch) -> None:
    import scipy.optimize

    entered: list[str] = []

    def optimizer(fun: Callable[..., Any], y: tuple[float, ...], **kwargs: Any) -> None:
        fun(y)
        point = tuple((a-b)/s for a, b, s in zip(ROOT, synthetic().initial_controls, target._CONTROL_SCALES))
        entered.append("objective")
        fun(point)
        entered.append("jacobian")
        kwargs["jac"](point)

    monkeypatch.setattr(scipy.optimize, "least_squares", optimizer)
    report, shared, calls = correct()
    assert entered == ["objective"] and report["outcome"] == "local-qualified"
    assert [c["role"] for c in calls] == ["seed-replay", "objective", "frozen-repeat"]
    assert shared.jacobian_batches == 0 and shared.objective_requests == 2


def test_best_objective_is_distinct_from_accepted_iterates_and_probes() -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, domain.initial_controls, linear)
    corrector.jacobian((0.,)*6)
    accepted = list(corrector.accepted)
    halfway = tuple((a-b)/(2*s) for a, b, s in zip(ROOT, domain.initial_controls, target._CONTROL_SCALES))
    corrector.objective(halfway)
    best = corrector.report["best_objective"]
    assert best == corrector.entries[-1]["id"]
    assert corrector.entries[best]["role"] == "objective"
    assert corrector.entries[best]["accepted_iterate"] is False
    assert corrector.accepted == accepted == [1]
    assert corrector.report["selected_objective"] is None
    assert shared.nominal_evaluations == len(calls) == 14


def test_jacobian_requires_exact_completed_objective_center() -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, domain.initial_controls, linear)
    with pytest.raises(ValueError, match="completed objective center"):
        corrector.jacobian((.1, 0., 0., 0., 0., 0.))
    assert shared.jacobian_batches == 0 and len(calls) == 1


@pytest.mark.parametrize("value", [True, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("index", range(6))
def test_nonfinite_or_boolean_solver_coordinate_stops_before_new_native(index: int, value: float) -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, domain.initial_controls, linear)
    point = [0.]*6
    point[index] = value
    with pytest.raises(ValueError):
        corrector.objective(tuple(point))
    assert shared.objective_requests == 2 and shared.nominal_evaluations == len(calls) == 1


def test_wrong_scipy_version_stops_before_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    original = bounded.import_module

    def imported(name: str) -> Any:
        return SimpleNamespace(__version__="1.17.2") if name == "scipy" else original(name)

    monkeypatch.setattr(bounded, "import_module", imported)
    report, shared, calls = correct()
    assert report["outcome"] == "failed" and "pinned Conda SciPy 1.17.1" in report["reason"]
    assert calls == [] and shared.native_arc_propagations == shared.objective_requests == 0


def test_condition_rank_diagnostics_do_not_inject_d15_solver_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = synthetic()
    corrector, shared, _ = prepared(domain, domain.initial_controls, linear)
    monkeypatch.setattr(np.linalg, "svd", lambda *args, **kwargs: np.array((1., .5, .4, .3, .2, 1e-12)))
    matrix = corrector.jacobian((0.,)*6)
    np.testing.assert_allclose(matrix, 100*np.eye(6), atol=1e-9, rtol=0)
    assert corrector.jacobians[0]["rank"] == 5
    assert corrector.jacobians[0]["condition_number"] == 1e12
    assert shared.jacobian_batches == 1


def test_rotated_actual_time_state_and_fixed_endpoint_interface() -> None:
    original = synthetic()
    rotation = np.array(((0., -1., 0.), (0., 0., 1.), (-1., 0., 0.)))

    def rotated(values: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(float(v) for v in rotation@values[:3])+tuple(float(v) for v in rotation@values[3:6])+values[6:]

    baseline = replace(original.baseline, initial_state_si=rotated(original.baseline.initial_state_si),
                       target_state_si=rotated(original.baseline.target_state_si),
                       direction_j2000=tuple(float(v) for v in rotation@original.baseline.direction_j2000))
    domain = target._TargetDomain(baseline, rotated(original.virtual_parking_state_si),
                                original.launch_window_tdb_s, original.arrival_delta_v_m_s)
    controls = (60., 22., .1, -.2, .3, -.4)
    expected = original.command(controls)
    actual = domain.command(controls)
    np.testing.assert_allclose(actual.initial_state_si, rotated(expected.initial_state_si), atol=1e-9, rtol=0)
    assert actual.target_state_si == rotated(expected.target_state_si)
    report, _, calls = correct(domain)
    assert report["outcome"] == "local-qualified"
    for call in calls:
        command = call["command"]
        assert command.target_state_si[:6] == domain.baseline.target_state_si[:6]
        assert command.ignition_epoch_tdb_s+command.match_after_ignition_s == domain.match_epoch_tdb_s


@pytest.mark.parametrize("delta,outcome", [((0.,)*7, "local-qualified"),
    ((1.01, 0., 0., 0., 0., 0., 0.), "tighter-unqualified"),
    ((0., 0., 0., .00101, 0., 0., 0.), "tighter-unqualified"),
    ((11., 0., 0., 0., 0., 0., 0.), "tighter-unqualified")])
def test_replay_closure_precedes_optimizer_and_one_tighter(delta: tuple[float, ...], outcome: str) -> None:
    report, shared, calls = correct(residual_at=lambda x: (0.,)*6, tighter_delta=delta)
    assert report["outcome"] == outcome
    assert [c["role"] for c in calls] == ["seed-replay", "frozen-repeat"]
    assert shared.objective_requests == shared.jacobian_batches == 0
    assert shared.propagation_evaluations == 2 and shared.native_arc_propagations == 4


@pytest.mark.parametrize("coast", [False, True])
def test_tighter_failure_never_resumes_optimizer(coast: bool) -> None:
    report, shared, calls = correct(residual_at=lambda x: (0.,)*6, fail_at=1, fail_coast=coast)
    assert report["outcome"] == "failed" and shared.tighter_evaluations == 1
    assert [c["role"] for c in calls] == ["seed-replay", "frozen-repeat"]
    assert shared.objective_requests == shared.jacobian_batches == 0
    assert shared.native_arc_propagations == shared.completed_arcs+1


def test_tighter_mass_disagreement_is_not_qualified_or_retried() -> None:
    report, shared, calls = correct(residual_at=lambda x: (0.,)*6,
                                   tighter_delta=(0., 0., 0., 0., 0., 0., 1.01e-6))
    assert report["outcome"] == "failed" and shared.tighter_evaluations == 1
    assert len(calls) == 2 and "mass" in report["reason"]
    assert report["proposals"][-1]["final_state_si"] is None


def test_closed_probe_is_not_eligible_or_selected() -> None:
    domain = synthetic()
    seed = domain.initial_controls

    def residual(x: target.Controls) -> target.Controls:
        return (0.,)*6 if x != seed else (100.,)*6

    corrector, shared, calls = prepared(domain, seed, residual)
    corrector.jacobian((0.,)*6)
    assert all(e["closure"] == "pass" for e in corrector.entries[2:])
    assert corrector.report["selected_objective"] is None
    assert corrector.report["best_objective"] == 0 and shared.tighter_evaluations == 0
    assert len(calls) == 13


def test_constant_rank_loss_and_vector_norm_do_not_qualify() -> None:
    report, shared, _ = correct(residual_at=lambda x: (.8, .8, 0., .8, .8, 0.))
    assert report["outcome"] == "stationary-unclosed"
    assert report["proposals"][0]["closure"] == "fail"
    assert report["jacobians"][0]["rank"] == 0
    assert report["jacobians"][0]["condition_number"] is None
    assert report["solver_result"]["status"] == 1 and shared.tighter_evaluations == 0


def test_real_scipy_bound_active_unattainable_target_not_success() -> None:
    upper = synthetic().delta_bounds_s[1]

    def residual(x: target.Controls) -> target.Controls:
        return ((x[0]-upper-300)/3, 0., 0., 0., 0., 0.)

    report, shared, _ = correct(residual_at=residual)
    assert report["outcome"] in ("stationary-unclosed", "stagnated-unclosed")
    assert report["solver_result"]["active_mask"][0] == 1
    assert report["selected_objective"] is None and shared.tighter_evaluations == 0
    assert all(e["closure"] == "fail" for e in report["proposals"])


@pytest.mark.parametrize("status,outcome", [(1, "stationary-unclosed"), (2, "stagnated-unclosed"),
    (3, "stagnated-unclosed"), (4, "stagnated-unclosed"), (0, "budget-exhausted"), (-2, "failed")])
def test_solver_status_never_substitutes_for_physical_closure(
    monkeypatch: pytest.MonkeyPatch, status: int, outcome: str,
) -> None:
    import scipy.optimize

    def optimizer(fun: Callable[..., Any], y: tuple[float, ...], **kwargs: Any) -> SimpleNamespace:
        fun(y)
        return SimpleNamespace(x=y, status=status, message="injected exit", nfev=1, njev=0,
                               active_mask=(0.,)*6, grad=(0.,)*6, optimality=0.)

    monkeypatch.setattr(scipy.optimize, "least_squares", optimizer)
    report, shared, calls = correct()
    assert report["outcome"] == outcome and shared.tighter_evaluations == 0 and len(calls) == 1


@pytest.mark.parametrize("delta", [(1.01, 0., 0., 0., 0., 0., 0.),
    (0., 0., 0., .00101, 0., 0., 0.), (0., 0., 0., 0., 0., 0., 1.01e-6)])
def test_replay_mismatch_stops_before_objective(delta: tuple[float, ...]) -> None:
    report, shared, calls = correct(replay_delta=delta)
    assert report["outcome"] == "baseline-replay-mismatch" and report["baseline_replay"] == "fail"
    assert len(calls) == 1 and shared.objective_requests == shared.jacobian_batches == 0


@pytest.mark.parametrize("corrupt", ["cutoff", "coast", "nonfinite", "short"])
def test_invalid_native_output_has_no_penalty_or_retry(corrupt: str) -> None:
    report, shared, calls = correct(corrupt=corrupt)
    assert report["outcome"] == "failed" and report["proposals"][0]["outcome"] == "failed"
    assert len(calls) == 1 and shared.objective_requests == shared.jacobian_batches == 0
    assert report["proposals"][0]["final_state_si"] is None


@pytest.mark.parametrize("fail_at,coast", [(0, False), (0, True), (1, False), (2, True)])
def test_failed_arc_aborts_without_retry_and_preserves_cutoff(fail_at: int, coast: bool) -> None:
    report, shared, calls = correct(fail_at=fail_at, fail_coast=coast)
    assert report["outcome"] == "failed" and len(calls) == fail_at+1
    assert shared.native_arc_propagations == shared.completed_arcs+1
    failed = report["proposals"][-1]
    assert failed["final_state_si"] is None and shared.tighter_evaluations == 0
    assert (failed["cutoff_state_si"] is not None) == coast


def test_nominal_280_plus_reserved_tighter_281_and_562_launches() -> None:
    shared = budget()
    for _ in range(280):
        complete_evaluation(shared)
    assert shared.nominal_evaluations == shared.propagation_evaluations == 280
    assert shared.native_arc_propagations == shared.completed_arcs == 560
    with pytest.raises(bounded._Limit, match="tighter pair remains reserved"):
        shared.begin_evaluation(False)
    complete_evaluation(shared, True)
    assert shared.nominal_evaluations == 280 and shared.propagation_evaluations == 281
    assert shared.tighter_evaluations == 1 and shared.native_arc_propagations == 562
    with pytest.raises(ValueError, match="no retry"):
        shared.begin_control()


def test_independent_request_and_jacobian_batch_limits() -> None:
    shared = budget()
    for _ in range(40):
        shared.begin_objective()
    with pytest.raises(bounded._Limit, match="objective-request limit 40"):
        shared.begin_objective()
    assert shared.objective_requests == 40 and shared.propagation_evaluations == 0
    shared = budget()
    for _ in range(20):
        shared.begin_batch()
        for _ in range(12):
            complete_evaluation(shared)
    with pytest.raises(bounded._Limit, match="Jacobian-batch limit 20"):
        shared.begin_batch()
    assert shared.jacobian_batches == 20 and shared.nominal_evaluations == 240


@pytest.mark.parametrize("limit", ["objectives", "jacobians"])
def test_solver_callbacks_cannot_bypass_independent_limits(monkeypatch: pytest.MonkeyPatch, limit: str) -> None:
    import scipy.optimize

    def optimizer(fun: Callable[..., Any], y: tuple[float, ...], **kwargs: Any) -> None:
        if limit == "objectives":
            for _ in range(41):
                fun(y)
        else:
            fun(y)
            for _ in range(21):
                kwargs["jac"](y)

    monkeypatch.setattr(scipy.optimize, "least_squares", optimizer)
    report, shared, calls = correct()
    assert report["outcome"] == "budget-exhausted" and shared.tighter_evaluations == 0
    if limit == "objectives":
        assert shared.objective_requests == shared.nominal_evaluations == len(calls) == 40
        assert shared.native_arc_propagations == 80
    else:
        assert shared.jacobian_batches == 20 and shared.nominal_evaluations == len(calls) == 241
        assert shared.native_arc_propagations == 482


def test_unaffordable_batch_launches_zero_of_twelve_probes() -> None:
    domain = synthetic()
    corrector, shared, calls = prepared(domain, domain.initial_controls, linear)
    shared.nominal_evaluations = shared.propagation_evaluations = 269
    shared.native_arc_propagations = shared.completed_arcs = 538
    shared._evaluation_start_arcs = 536
    with pytest.raises(bounded._Limit, match="complete twelve-probe batch cannot fit"):
        corrector.jacobian((0.,)*6)
    assert shared.jacobian_batches == 0 and len(calls) == 1


def test_incomplete_arc_disallows_every_future_work_entry() -> None:
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
def test_late_completed_endpoint_is_budget_exhausted(at: float) -> None:
    def expire(shared: bounded._BoundBudget) -> None:
        shared.monotonic = lambda: at

    report, shared, calls = correct(after=expire)
    assert report["outcome"] == "budget-exhausted" and "deadline" in report["reason"]
    assert len(calls) == 1 and shared.completed_arcs == 2
    assert report["proposals"][0]["final_state_si"] is None


@pytest.mark.parametrize("tighter", [False, True])
def test_new_budget_native_adapter_matches_frozen_d15(tighter: bool) -> None:
    domain = synthetic(match_s=1000.)
    x = (0., 20., .2, -.3, -.1, .4)
    command = domain.command(x)
    shared = budget()
    shared.begin_control()
    shared.begin_evaluation(False)
    actual = target._evaluate_command(domain, x, command, tighter, shared, {})
    old = target._TargetBudget("D15 parity", 300., lambda: 0., max_arcs_per_evaluation=2)
    old.begin_control()
    old.begin_evaluation(False)
    expected = target._evaluate_command(domain, x, command, tighter, old, {})
    assert actual == expected
    assert shared.completed_arcs == shared.native_arc_propagations == 2


def test_actual_native_deadline_wrapping_retains_budget_classification(monkeypatch: pytest.MonkeyPatch) -> None:
    from tudatpy.dynamics import simulator

    native = simulator.create_dynamics_simulator

    def expire(*args: Any) -> Any:
        shared.monotonic = lambda: 300.
        return native(*args)

    domain, shared = synthetic(), budget()
    monkeypatch.setattr(simulator, "create_dynamics_simulator", expire)
    report: dict[str, Any] = {}
    seed = domain.initial_controls
    bounded._correct_target(domain, seed, state_for(domain, seed, linear(seed)), shared, report)
    assert report["outcome"] == "budget-exhausted" and "deadline" in report["reason"]
    assert shared.native_arc_propagations == 1 and shared.completed_arcs == 0
    assert report["proposals"][0]["final_state_si"] is None


def test_retained_binding_and_coast_arithmetic_without_propagation(retained: Any) -> None:
    reference, study, steering = retained
    domain, endpoint = bounded._bind_steering(reference, study, steering, tuple(study["launch_window_tdb_s"]))
    assert endpoint == tuple(steering["proposals"][52]["final_state_si"])
    assert bounded._SEED == tuple(steering["proposals"][52]["controls"])
    lo, hi = bounded._bounds(domain)
    minimum = domain.match_epoch_tdb_s-(domain.baseline.ignition_epoch_tdb_s+hi[0])-hi[1]
    assert minimum == pytest.approx(1756.635988459775, abs=1e-6)
    assert lo[0] < bounded._SEED[0] < hi[0]
    for path, expected in ((REFERENCE, local._REFERENCE_SHA256), (STUDY, target._STUDY_SHA256),
                           (STEERING, bounded._STEERING_SHA256)):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_authoritative_box_corner_rejection_is_never_repaired(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = synthetic()
    original = target._TargetDomain.command
    high_delta, high_tau = domain.delta_bounds_s[1], domain.duration_bounds_s[1]

    def strict_corner(self: target._TargetDomain, x: target.Controls) -> local._LocalCommand:
        if self is domain and x[:2] == (high_delta, high_tau):
            raise ValueError("authoritative floating-point mass reserve")
        return original(self, x)

    monkeypatch.setattr(target._TargetDomain, "command", strict_corner)
    report, shared, calls = correct(domain)
    assert report["outcome"] in ("failed", "domain-unresolved")
    assert "mass reserve" in report["reason"]
    assert calls == [] and shared.native_arc_propagations == 0


@pytest.mark.parametrize("key", ["count", "candidate", "profile", "resource", "endpoint", "residual",
    "mass", "seed", "accepted", "command", "model", "units"])
def test_retained_binding_rejects_inconsistent_evidence(retained: Any, key: str) -> None:
    reference, study, original = retained
    steering = deepcopy(original)
    if key == "count":
        steering["nominal_proposals"] = 52
    elif key == "candidate":
        steering["candidate_id"] = "another"
    elif key == "profile":
        steering["profiles"]["nominal"]["maximum_step_s"] = 99.
    elif key == "resource":
        steering["retained_lunar_resource"]["orbit_shape_radius_m"] += 1
    elif key == "endpoint":
        steering["proposals"][52]["final_state_si"][0] += 1
    elif key == "residual":
        steering["proposals"][52]["scaled_residual"][0] += 1
    elif key == "mass":
        steering["proposals"][52]["cutoff_state_si"][6] += .01
    elif key == "seed":
        steering["best_accepted_proposal"] = 39
    elif key == "accepted":
        steering["proposals"][52]["accepted"] = False
    elif key == "command":
        steering["proposals"][52]["command"]["isp_s"] += 1
    elif key == "model":
        steering["model_id"] = "another"
    elif key == "units":
        steering["units"] = "km"
    with pytest.raises(ValueError):
        bounded._bind_steering(reference, study, steering, tuple(study["launch_window_tdb_s"]))


def test_runner_provenance_with_injected_no_native_study(monkeypatch: pytest.MonkeyPatch, retained: Any) -> None:
    _, study, steering = retained
    window = iter(study["launch_window_tdb_s"])
    monkeypatch.setattr(local.ephemeris, "utc_to_tdb", lambda text: next(window))
    monkeypatch.setattr(local.ephemeris, "kernel_metadata", lambda: {"synthetic": True})
    original = bounded._correct_target

    def injected(domain: target._TargetDomain, seed: target.Controls, endpoint: local.State7,
                 shared: bounded._BoundBudget, report: dict[str, Any]) -> None:
        residual = tuple((a-b)/s for a, b, s in zip(endpoint[:6], domain.baseline.target_state_si[:6],
                                                  target._RESIDUAL_SCALES))
        evaluate, _ = oracle(lambda x: residual)
        original(domain, seed, endpoint, shared, report, evaluate=evaluate)

    monkeypatch.setattr(bounded, "_correct_target", injected)
    report = bounded._run_bounded_local_targeting(REFERENCE, STUDY, STEERING, monotonic=lambda: 0.)
    assert report["outcome"] == "stationary-unclosed" and report["baseline_replay"] == "pass"
    assert report["objective_requests"] == report["jacobian_batches"] == 1
    assert report["nominal_evaluations"] == 13 and report["native_arc_propagations"] == 26
    assert report["completed_arcs"] == 26 and report["tighter_evaluations"] == 0
    assert report["runtime_versions"]["scipy"] == "1.17.1"
    assert report["historical_source_sha256"]["0110"] == steering["source_sha256"]
    assert "bounded_local_targeting.py" in report["source_sha256"]
    assert report["profiles"] == study["profiles"] or json.loads(json.dumps(report["profiles"])) == study["profiles"]
    json.dumps(report, allow_nan=False)


def test_runner_clock_includes_preparation() -> None:
    ticks = iter((0., 300.))
    report = bounded._run_bounded_local_targeting(REFERENCE, STUDY, STEERING, monotonic=lambda: next(ticks))
    assert report["outcome"] == "budget-exhausted" and report["native_arc_propagations"] == 0
    assert report["elapsed_wall_s"] == 300.
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("index", range(3))
def test_runner_hash_failure_precedes_binding_or_native(index: int, tmp_path: Path) -> None:
    paths = [REFERENCE, STUDY, STEERING]
    wrong = tmp_path/"wrong.json"
    wrong.write_text("{}")
    paths[index] = wrong
    report = bounded._run_bounded_local_targeting(*paths, monotonic=lambda: 0.)
    assert report["outcome"] == "failed" and "SHA256 mismatch" in report["reason"]
    assert report["native_arc_propagations"] == report["propagation_evaluations"] == 0
    json.dumps(report, allow_nan=False)
