"""D15.2 synthetic qualifications; never run the D15.3 reference campaign."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from space_nav import local_burn as local
from space_nav import local_targeting as target
from space_nav.errors import TrajectoryRefinementError


REFERENCE = Path("docs/adr/experiments/0104-lunar-departure-reference.json")
STUDY = Path("docs/adr/experiments/0107-local-finite-burn-study.json")
ROOT = (60., 22., .02, -.03, .04, .01)


def synthetic(duration_s: float = 20.) -> target._TargetDomain:
    theta = -.001*duration_s/2
    initial = (1e6*math.cos(theta), 1e6*math.sin(theta), 0.,
               -1000*math.sin(theta), 1000*math.cos(theta), 0., 2000.)
    c = local._LocalCommand(1e12, 1., 500., 1000., 450., (1., 0., 0.),
        1e9, duration_s, 1000., initial, (0., 100., 0., 0., 0., 0., 1990.), 100.)
    return target._TargetDomain(c, (1e6, 0., 0., 0., 1000., 0.), (1e9-2000, 1e9+2000), 1.)


@pytest.fixture
def retained() -> tuple[dict[str, Any], dict[str, Any], target._TargetDomain]:
    reference, study = json.loads(REFERENCE.read_text()), json.loads(STUDY.read_text())
    domain = target._bind_references(reference, study, tuple(study["launch_window_tdb_s"]))
    return reference, study, domain


def budget() -> target._TargetBudget:
    return target._TargetBudget("D15 test", 300., lambda: 0., max_arcs_per_evaluation=2)


def linear(x: target.Controls) -> target.Controls:
    return tuple(100*(a-b)/s for a, b, s in zip(x, ROOT, target._CONTROL_SCALES))


def state_for(d: target._TargetDomain, x: target.Controls, residual: target.Controls) -> local.State7:
    c = d.command(x)
    return tuple(v+s*r for v, s, r in zip(c.target_state_si[:6], target._RESIDUAL_SCALES, residual))+(c.target_state_si[6],)


def oracle(
    residual_at: Any = linear, *, trial_at: Any = None, tighter_delta: tuple[float, ...] = (0.,)*7,
    fail_at: int = -1, corrupt: str | None = None,
) -> tuple[target.Evaluator, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []
    def evaluate(d: target._TargetDomain, x: target.Controls, c: local._LocalCommand,
                 tighter: bool, b: target._TargetBudget, evidence: dict[str, Any]) -> dict[str, Any]:
        calls.append({"x": x, "command": c, "tighter": tighter, "role": evidence["role"]})
        b.begin_arc(first_in_evaluation=True)
        if len(calls)-1 == fail_at:
            raise TrajectoryRefinementError("injected propagation failure")
        b.completed_arcs += 1
        b.begin_arc(first_in_evaluation=False)
        b.completed_arcs += 1
        residual = (trial_at(evidence) if trial_at is not None and evidence['role'] == 'trial'
                    else residual_at(x))
        final = state_for(d, x, tuple(residual))
        if tighter:
            final = tuple(a+b for a, b in zip(final, tighter_delta))
        cutoff = c.target_state_si
        if corrupt == 'cutoff':
            cutoff = cutoff[:-1]+(cutoff[6]+.01,)
        elif corrupt == 'coast':
            final = final[:-1]+(final[6]+.01,)
        elif corrupt == 'nonfinite':
            final = (math.nan,)+final[1:]
        return {"cutoff_state_si": cutoff, "final_state_si": final, "checked_saved_states": 4}
    return evaluate, calls


def correct(d: target._TargetDomain | None = None, *, residual_at: Any = linear,
            replay_delta: tuple[float, ...] = (0.,)*7, **kwargs: Any) -> tuple[dict[str, Any], target._TargetBudget, list[dict[str, Any]]]:
    d = d or synthetic()
    evaluate, calls = oracle(residual_at, **kwargs)
    retained_state = state_for(d, d.initial_controls, residual_at(d.initial_controls))
    retained_state = tuple(a+b for a, b in zip(retained_state, replay_delta))
    report: dict[str, Any] = {}
    b = budget()
    target._correct_target(d, retained_state, b, report, evaluate=evaluate)
    json.dumps(report, allow_nan=False)
    return report, b, calls


@pytest.mark.parametrize("direction,axis", [((1., 0., 0.), 1), ((0., 1., 0.), 0),
    ((0., 0., 1.), 0), ((1/math.sqrt(3),)*3, 0)])
def test_basis_ties_and_independent_orthonormality(direction: target.Vector3, axis: int) -> None:
    basis = target._steering_basis(direction)
    np.testing.assert_allclose(np.array(basis)@np.array(basis).T, np.eye(3), atol=1e-15, rtol=0)
    expected = np.eye(3)[axis]-np.dot(np.eye(3)[axis], direction)*np.array(direction)
    expected /= np.linalg.norm(expected)
    np.testing.assert_allclose(basis[1], expected, atol=1e-15, rtol=0)
    assert np.linalg.det(basis) == pytest.approx(1., abs=1e-15)


@pytest.mark.parametrize("slopes", [(0., 0., 0., 0.), (1., 1., -1., -1.), (.3, -.8, .9, .1)])
def test_chart_direction_units_and_rate_oracle(slopes: tuple[float, ...]) -> None:
    d = synthetic()
    x = (0., 20.)+slopes
    previous = None
    bound = math.hypot(slopes[2]-slopes[0], slopes[3]-slopes[1])/20
    for at in np.linspace(0, 20, 101):
        actual = target._steering_direction(d.basis, x, float(at))
        s = at/20
        raw = np.array((1., (1-s)*slopes[0]+s*slopes[2], (1-s)*slopes[1]+s*slopes[3]))
        assert np.linalg.norm(raw) >= 1
        np.testing.assert_allclose(actual, raw/np.linalg.norm(raw), atol=1e-15, rtol=0)
        assert math.hypot(*actual) == pytest.approx(1., abs=1e-15)
        assert math.acos(min(1., actual[0])) <= math.atan(math.sqrt(2))+1e-15
        if previous is not None:
            # Chord <= arc length <= steering-rate upper bound * dt.
            assert math.dist(actual, previous) <= bound*.2+1e-14
        previous = actual


@pytest.mark.parametrize("value", [True, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("index", range(6))
def test_nonfinite_or_boolean_controls_stop(index: int, value: float) -> None:
    x = list(synthetic().initial_controls)
    x[index] = value
    with pytest.raises(ValueError):
        synthetic().command(tuple(x))


def test_retained_bounds_mass_rotation_and_fixed_target_oracles(retained: Any) -> None:
    reference, study, d = retained
    assert hashlib.sha256(STUDY.read_bytes()).hexdigest() == target._STUDY_SHA256
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == local._REFERENCE_SHA256
    assert d.delta_bounds_s == pytest.approx((-1766.8649313817746, 1766.8649313817746), abs=1e-9)
    assert d.duration_bounds_s == pytest.approx((2105.141840324445, 5467.045140120176), abs=1e-9)
    c0 = d.command(d.initial_controls)
    assert c0.initial_state_si == d.baseline.initial_state_si
    assert c0.target_state_si == d.baseline.target_state_si
    for delta, tau in ((-300., 3000.), (300., 5000.)):
        c = d.command((delta, tau, .2, -.3, .4, .5))
        assert c.target_state_si[:6] == d.baseline.target_state_si[:6]
        assert c.ignition_epoch_tdb_s+c.match_after_ignition_s == d.match_epoch_tdb_s
        with localcontext() as ctx:
            ctx.prec = 50
            mass = Decimal(2000)-Decimal(1000)*Decimal(str(tau))/(Decimal('9.80665')*Decimal(450))
            assert abs(c.target_state_si[6]-float(mass)) < 1e-10
        r0, v0 = np.array(c0.initial_state_si[:3]), np.array(c0.initial_state_si[3:6])
        axis = np.cross(r0, v0)
        axis /= np.linalg.norm(axis)
        theta = math.sqrt(c.mu_m3_s2/np.linalg.norm(r0)**3)*delta
        for original, actual in ((r0, c.initial_state_si[:3]), (v0, c.initial_state_si[3:6])):
            rotated = original*math.cos(theta)+np.cross(axis, original)*math.sin(theta)
            np.testing.assert_allclose(actual, rotated, atol=1e-8, rtol=0)
        assert np.linalg.norm(c.initial_state_si[:3]) == pytest.approx(1837400., abs=1e-8)
        assert c.initial_state_si[6] == 2000
    assert reference['candidate']['candidate_id'] == study['candidate_id']


@pytest.mark.parametrize("index,value", [(0, -2000.), (0, 2000.), (1, 9.), (1, 31.),
    (2, -1.000000001), (3, 1.000000001), (4, -2.), (5, 2.)])
def test_analytic_command_bounds(index: int, value: float) -> None:
    d = synthetic()
    x = list(d.initial_controls)
    x[index] = value
    with pytest.raises(ValueError, match='domain'):
        d.command(tuple(x))


def test_domain_equalities_window_cutoff_and_empty_domains() -> None:
    d = synthetic()
    for delta in d.delta_bounds_s:
        d.command((delta, 10., -1., 1., -1., 1.))
    for duration in d.duration_bounds_s:
        d.command((0., duration, 0., 0., 0., 0.))
    constrained = replace(d, launch_window_tdb_s=(1e9-1, 1e9+1))
    constrained.command((1., 20., 0., 0., 0., 0.))
    with pytest.raises(ValueError):
        constrained.command((1.00001, 20., 0., 0., 0., 0.))
    # Exactly one second of coast is allowed; crossing it is not.
    short = replace(d, baseline=replace(d.baseline, match_after_ignition_s=31.))
    short.command((0., 30., 0., 0., 0., 0.))
    with pytest.raises(ValueError, match='cutoff'):
        short.command((.01, 30., 0., 0., 0., 0.))
    with pytest.raises(ValueError, match='empty'):
        replace(d, arrival_delta_v_m_s=10000.)
    with pytest.raises(ValueError, match='empty'):
        replace(d, launch_window_tdb_s=(1e9+3000, 1e9+4000))


@pytest.mark.parametrize("updates", [
    {'arrival_delta_v_m_s': True}, {'arrival_delta_v_m_s': math.nan},
    {'virtual_parking_state_si': (1.,)*5}, {'virtual_parking_state_si': (1e6, 0., 0., 1., 1000., 0.)},
    {'launch_window_tdb_s': (1e9, 1e9)}, {'launch_window_tdb_s': (math.nan, 1e9)},
])
def test_domain_input_guards(updates: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(synthetic(), **updates)


def test_mass_reserve_roundoff_at_upper_bound_checked_again(retained: Any) -> None:
    _, _, d = retained
    x = (0., d.duration_bounds_s[1], 0., 0., 0., 0.)
    # No tolerance is added to make a boundary pass: check floating mass itself.
    mf = 2000-1000*x[1]/(9.80665*450)
    reserve = mf*math.exp(-d.arrival_delta_v_m_s/(9.80665*450))
    if reserve >= 500:
        assert d.command(x).target_state_si[6] == mf
    else:
        with pytest.raises(ValueError, match='mass reserve'):
            d.command(x)


def test_linear_correction_central_units_order_and_frozen_repeat() -> None:
    report, b, calls = correct()
    assert report['outcome'] == 'local-qualified' and report['agreement'] == 'pass'
    assert len(calls) == 15 and b.control_attempts == 14 and b.propagation_evaluations == 15
    assert b.native_arc_propagations == b.completed_arcs == 30
    parent = report['proposals'][0]
    for i in range(6):
        plus, minus = report['proposals'][2*i+1:2*i+3]
        assert plus['parent'] == minus['parent'] == parent['id']
        for sign, item in ((1, plus), (-1, minus)):
            expected = list(parent['controls'])
            expected[i] += sign*target._PROBE_STEPS[i]
            assert item['controls'] == tuple(expected)
    np.testing.assert_allclose(report['iterations'][0]['jacobian'], np.eye(6)*100, atol=2e-10, rtol=0)
    np.testing.assert_allclose(calls[-2]['x'], ROOT, atol=1e-10, rtol=0)
    assert calls[-1]['x'] == calls[-2]['x'] and calls[-1]['command'] == calls[-2]['command']
    assert calls[-1]['tighter'] is True and not any(c['tighter'] for c in calls[:-1])
    assert all(c['command'].target_state_si[:6] == synthetic().baseline.target_state_si[:6] for c in calls)
    assert all(c['command'].ignition_epoch_tdb_s+c['command'].match_after_ignition_s == synthetic().match_epoch_tdb_s for c in calls)


def test_quadratic_oracle_recomputes_at_accepted_iterate() -> None:
    def quadratic(x: target.Controls) -> target.Controls:
        return tuple(v+.1*v*v for v in linear(x))
    report, _, calls = correct(residual_at=quadratic)
    assert report['outcome'] == 'local-qualified'
    assert 1 < len(report['iterations']) <= 4
    for record in report['iterations']:
        parent = report['proposals'][record['parent']]
        z = np.array(linear(parent['controls']))
        np.testing.assert_allclose(record['jacobian'], np.diag(100*(1+.2*z)), atol=1e-8, rtol=0)
        assert all(report['proposals'][i]['parent'] == parent['id'] for i in record['probe_ids']+record['trial_ids'])
    assert sum(c['tighter'] for c in calls) == 1


@pytest.mark.parametrize("delta", [(1.0001, 0., 0., 0., 0., 0., 0.),
    (0., 0., 0., .001001, 0., 0., 0.), (0.,)*6+(1.01e-6,)])
def test_replay_mismatch_stops_before_probes(delta: tuple[float, ...]) -> None:
    report, _, calls = correct(replay_delta=delta)
    assert len(calls) == 1 and report['outcome'] == 'baseline-replay-mismatch'
    assert not report['iterations'] and report['best_accepted_proposal'] is None


@pytest.mark.parametrize("delta", [(1., 0., 0., 0., 0., 0., 0.), (0., 0., 0., .001, 0., 0., 0.)])
def test_replay_tolerance_equalities(delta: tuple[float, ...]) -> None:
    # Put the compared velocity at zero, so 0.001 is the actual representable
    # difference rather than subtraction of two rounded nonzero velocities.
    report, _, _ = correct(replay_delta=delta, residual_at=lambda x: (100., 0., 0., 0., 0., 0.))
    assert report['baseline_replay'] == 'pass'


@pytest.mark.parametrize("delta,outcome", [((0.,)*7, 'local-qualified'),
    ((2., 0., 0., 0., 0., 0., 0.), 'tighter-unqualified'),
    ((11., 0., 0., 0., 0., 0., 0.), 'tighter-unqualified'),
    ((0., 0., 0., .002, 0., 0., 0.), 'tighter-unqualified')])
def test_first_baseline_closure_gets_exactly_one_tighter(delta: tuple[float, ...], outcome: str) -> None:
    report, b, calls = correct(residual_at=lambda x: (0.,)*6, tighter_delta=delta)
    assert report['outcome'] == outcome and len(calls) == 2
    assert b.tighter_evaluations == 1 and not report['iterations']


def test_closure_is_vector_norm_not_componentwise() -> None:
    report, _, _ = correct(residual_at=lambda x: (.8, .8, 0., 0., 0., 0.))
    assert report['proposals'][0]['closure'] == 'fail'
    assert report['outcome'] == 'rank-condition-unresolved'


@pytest.mark.parametrize("rank,condition,ready", [(6, 1e10, True), (6, 1e10+1, False), (5, 1., False)])
def test_rank_and_condition_exact_gates(monkeypatch: pytest.MonkeyPatch, rank: int, condition: float, ready: bool) -> None:
    monkeypatch.setattr(np.linalg, 'lstsq', lambda j, r, rcond:
        (np.array((-.5, 0., 0., 0., 0., 0.)), np.array([]), rank, np.array((1., 1., 1., 1., 1., 1/condition))))
    result = target._solve_step((1., 0., 0., 0., 0., 0.), tuple(map(tuple, np.eye(6))))
    assert (result['outcome'] == 'ready') is ready


def test_cap_once_and_prediction_from_capped_normalized_step() -> None:
    result = target._solve_step((10., 2., 0., 0., 0., 0.), tuple(map(tuple, np.eye(6))))
    assert result['raw_z'] == [-10., -2., 0., 0., 0., 0.]
    assert result['capped_z'] == [-1., -.2, 0., 0., 0., 0.]
    assert result['step_controls'] == [-300., -60., 0., 0., 0., 0.]
    np.testing.assert_allclose(result['predicted_residual'], (9., 1.8, 0., 0., 0., 0.), atol=1e-15, rtol=0)


@pytest.mark.parametrize("z,outcome", [((0.,)*6, 'no-predicted-decrease'),
    ((1., 0., 0., 0., 0., 0.), 'no-predicted-decrease')])
def test_zero_or_non_decreasing_prediction(monkeypatch: pytest.MonkeyPatch, z: target.Controls, outcome: str) -> None:
    monkeypatch.setattr(np.linalg, 'lstsq', lambda *args, **kwargs: (np.array(z), [], 6, np.ones(6)))
    assert target._solve_step((1., 0., 0., 0., 0., 0.), tuple(map(tuple, np.eye(6))))['outcome'] == outcome


@pytest.mark.parametrize("failure", ['nan-z', 'nan-singular', 'exception', 'nan-matrix'])
def test_bad_solve_stops_not_serialized(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    matrix = np.eye(6)
    if failure == 'nan-matrix':
        matrix[0, 0] = math.nan
    else:
        def bad(*args: Any, **kwargs: Any) -> Any:
            if failure == 'exception':
                raise np.linalg.LinAlgError('injected failure')
            return (np.full(6, math.nan) if failure == 'nan-z' else np.ones(6), [], 6,
                    np.full(6, math.nan) if failure == 'nan-singular' else np.ones(6))
        monkeypatch.setattr(np.linalg, 'lstsq', bad)
    with pytest.raises(ValueError):
        target._solve_step((1.,)*6, tuple(map(tuple, matrix)))


def test_derivative_domain_preflight_launches_no_partial_stencil() -> None:
    d = replace(synthetic(), launch_window_tdb_s=(1e9, 1e9+100))
    report, b, calls = correct(d)
    assert report['outcome'] == 'derivative-domain-unresolved' and len(calls) == 1
    assert b.control_attempts == 13 and b.propagation_evaluations == 1
    assert len(report['iterations'][0]['probe_ids']) == 12
    assert sum(p['feasible'] is False for p in report['proposals']) == 1


@pytest.mark.parametrize("offset", [0., 1e-6])
def test_armijo_equality_and_rejection_all_common_parent(offset: float) -> None:
    def residual(x: target.Controls) -> target.Controls:
        return tuple(100*(a-b)/s for a, b, s in zip(x, (300., 20., 0., 0., 0., 0.), target._CONTROL_SCALES))
    def trial(entry: dict[str, Any]) -> target.Controls:
        alpha = entry['fraction']
        return (100*(1-1e-4*alpha)+offset, 0., 0., 0., 0., 0.)
    report, _, _ = correct(residual_at=residual, trial_at=trial)
    first = report['iterations'][0]
    trials = [report['proposals'][i] for i in first['trial_ids']]
    if offset == 0:
        assert trials[0]['accepted'] is True and len(trials) == 1
    else:
        assert report['outcome'] == 'no-acceptable-step'
        assert [p['fraction'] for p in trials] == list(target._FRACTIONS)
        assert all(p['parent'] == 0 and not p['accepted'] for p in trials)
        for p in trials:
            assert p['controls'][0] == 300*p['fraction']


def test_infeasible_trials_count_but_never_launch_or_clip() -> None:
    d = replace(synthetic(), launch_window_tdb_s=(1e9-100, 1e9+100))
    def residual(x: target.Controls) -> target.Controls:
        return tuple(100*(a-b)/s for a, b, s in zip(x, (300., 20., 0., 0., 0., 0.), target._CONTROL_SCALES))
    report, b, calls = correct(d, residual_at=residual)
    trials = [report['proposals'][i] for i in report['iterations'][0]['trial_ids']]
    assert [p['controls'][0] for p in trials[:3]] == pytest.approx([300., 150., 75.])
    assert [p['outcome'] for p in trials[:2]] == ['skipped', 'skipped']
    assert trials[2]['accepted'] is True
    assert b.control_attempts > len(calls) and all(abs(c['x'][0]) <= 100 for c in calls)


def test_iteration_cap_no_tighter_best_accepted_retained() -> None:
    d = synthetic()
    report: dict[str, Any] = {}
    b = budget()
    # A slowly decaying full-rank residual, with duration scale matching its domain.
    def slow(x: target.Controls) -> target.Controls:
        scales = (300., 1., .1, .1, .1, .1)
        return tuple(1000*math.exp((a-v)/s) for a, v, s in zip(x, d.initial_controls, scales))
    evaluate, calls = oracle(slow)
    target._correct_target(d, state_for(d, d.initial_controls, slow(d.initial_controls)), b, report, evaluate=evaluate)
    assert report['outcome'] == 'not-converged' and len(report['iterations']) == 4
    assert not any(c['tighter'] for c in calls)
    best = report['proposals'][report['best_accepted_proposal']]
    assert best['accepted'] and best['score'] < report['proposals'][0]['score']


@pytest.mark.parametrize("fail_at", [0, 1, 12, 13, 14])
def test_native_failure_aborts_whole_schedule(fail_at: int) -> None:
    d = synthetic()
    evaluate, calls = oracle(fail_at=fail_at)
    b, report = budget(), {}
    with pytest.raises(TrajectoryRefinementError, match='injected'):
        target._correct_target(d, state_for(d, d.initial_controls, linear(d.initial_controls)), b, report, evaluate=evaluate)
    assert len(calls) == fail_at+1 and b.propagation_evaluations == fail_at+1
    assert b.native_arc_propagations == b.completed_arcs+1
    assert report['proposals'][-1]['outcome'] == 'failed'
    assert report['agreement'] == 'unavailable'
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("corrupt", ['cutoff', 'coast', 'nonfinite'])
def test_mass_and_nonfinite_output_stops_before_probes(corrupt: str) -> None:
    with pytest.raises(ValueError):
        correct(corrupt=corrupt)


def test_maximum_budget_and_failed_arc_no_retry() -> None:
    b = budget()
    for _ in range(65):
        b.begin_control()
        b.begin_evaluation(False)
        for first in (True, False):
            b.begin_arc(first_in_evaluation=first)
            with pytest.raises(TrajectoryRefinementError):
                b.begin_arc(first_in_evaluation=not first)
            b.completed_arcs += 1
    with pytest.raises(TrajectoryRefinementError):
        b.begin_control()
    b.begin_evaluation(True)
    for first in (True, False):
        b.begin_arc(first_in_evaluation=first)
        b.completed_arcs += 1
    assert b.propagation_evaluations == 66 and b.native_arc_propagations == 132
    with pytest.raises(TrajectoryRefinementError):
        b.begin_evaluation(True)


def test_four_full_damping_schedules_respect_65_proposal_cap() -> None:
    parent_score = math.hypot(*linear(synthetic().initial_controls))
    accepts = 0
    def trial(entry: dict[str, Any]) -> target.Controls:
        nonlocal accepts
        if entry['fraction'] == .125:
            accepts += 1
            return (parent_score*.99**accepts, 0., 0., 0., 0., 0.)
        return (parent_score*1.1, 0., 0., 0., 0., 0.)
    report, b, calls = correct(trial_at=trial)
    assert report['outcome'] == 'not-converged' and accepts == 4
    assert len(report['proposals']) == len(calls) == b.control_attempts == 65
    assert b.propagation_evaluations == 65 and b.native_arc_propagations == 130
    assert b.tighter_evaluations == 0 and report['agreement'] == 'unavailable'


def test_closed_probe_is_never_an_accepted_command() -> None:
    root = (1., 20., 0., 0., 0., 0.)
    def residual_at(x: target.Controls) -> target.Controls:
        return tuple(1000*(a-b)/s for a, b, s in zip(x, root, target._CONTROL_SCALES))
    report, _, calls = correct(residual_at=residual_at)
    assert report['proposals'][1]['closure'] == 'pass'
    assert report['proposals'][1]['accepted'] is False
    assert report['outcome'] == 'local-qualified' and len(calls) == 15


@pytest.mark.parametrize("end", [300., -1., math.nan])
def test_shared_clock_starts_before_preparation(monkeypatch: pytest.MonkeyPatch, end: float) -> None:
    ticks = iter((0., end))
    monkeypatch.setattr(target, '_bind_references', lambda *args: pytest.fail('must not bind'))
    report = target._run_local_targeting(REFERENCE, STUDY, monotonic=lambda: next(ticks))
    assert report['outcome'] == 'failed' and report['native_arc_propagations'] == 0
    assert 'deadline' in report['reason']


@pytest.mark.parametrize("key", ['command', 'candidate', 'resource', 'profile', 'endpoint', 'closure', 'mass', 'agreement', 'window'])
def test_full_retained_binding_rejects_mismatch(retained: Any, key: str) -> None:
    reference, original, d = retained
    study = deepcopy(original)
    if key == 'command':
        study['command']['thrust_n'] += 1
    elif key == 'candidate':
        reference['candidate']['candidate_id'] = 'other'
    elif key == 'resource':
        study['retained_lunar_resource']['orbit_shape_radius_m'] += 1
    elif key == 'profile':
        study['profiles']['tighter']['relative_tolerance'] *= 2
    elif key == 'endpoint':
        study['runs'][1]['final_state_si'][0] += 1
    elif key == 'closure':
        study['runs'][0]['closure'] = 'pass'
    elif key == 'mass':
        study['runs'][1]['cutoff_state_si'][6] += 1
    elif key == 'agreement':
        study['agreement_differences_si'][0] += 1
    else:
        study['launch_window_tdb_s'][0] += 1
    with pytest.raises(ValueError):
        target._bind_references(reference, study, d.launch_window_tdb_s)


def test_binding_failure_zero_launches(tmp_path: Path) -> None:
    wrong = tmp_path/'wrong.json'
    wrong.write_text('{}')
    report = target._run_local_targeting(REFERENCE, wrong, monotonic=lambda: 0.)
    assert report['outcome'] == 'failed' and report['propagation_evaluations'] == 0
    assert 'SHA256' in report['reason']


@pytest.mark.parametrize("tighter", [False, True])
def test_native_smooth_thrust_independent_gaussian_integral(tighter: bool) -> None:
    # Resolve steering on a 200 s scale, closer to the retained multi-thousand-
    # second burn than a 20 s near-discontinuity at the unchanged 10 s max step.
    d = synthetic(200.)
    x = (0., 200., .3, -.8, -.4, .6)
    c = replace(d.command(x), mu_m3_s2=1e-12)
    b = budget()
    b.begin_control()
    b.begin_evaluation(False)  # Adapter profile check, not solver repeat ordering.
    evidence: dict[str, Any] = {}
    result = target._evaluate_command(d, x, c, tighter, b, evidence)
    nodes, weights = np.polynomial.legendre.leggauss(128)
    at = (nodes+1)*100
    # Independent explicit chart in the synthetic X/Y/Z basis; no production
    # guidance function used by the quadrature oracle.
    w = np.stack((np.ones(128), .3+(-.4-.3)*at/200, -.8+(.6+.8)*at/200), axis=1)
    direction = w/np.linalg.norm(w, axis=1)[:, None]
    mass = 2000-1000*at/(9.80665*450)
    accel = direction*1000/mass[:, None]
    dv = np.sum(weights[:, None]*accel, axis=0)*100
    dr = np.sum(weights[:, None]*(200-at[:, None])*accel, axis=0)*100
    cutoff = result['cutoff_state_si']
    np.testing.assert_allclose(cutoff[3:6], np.array(c.initial_state_si[3:6])+dv, atol=1e-6, rtol=0)
    np.testing.assert_allclose(cutoff[:3], np.array(c.initial_state_si[:3])+200*np.array(c.initial_state_si[3:6])+dr, atol=.001, rtol=0)
    coast = result['final_state_si']
    np.testing.assert_allclose(coast[:3], np.array(cutoff[:3])+800*np.array(cutoff[3:6]), atol=.001, rtol=0)
    assert cutoff[6] == pytest.approx(2000-200000/(9.80665*450), abs=1e-6)
    assert coast[6] == cutoff[6] and b.native_arc_propagations == b.completed_arcs == 2
    assert evidence['cutoff_state_si'] == cutoff


@pytest.mark.parametrize("tighter", [False, True])
def test_zero_steering_native_equals_unchanged_d14(tighter: bool) -> None:
    d = synthetic()
    c = d.command(d.initial_controls)
    b = budget()
    b.begin_control()
    b.begin_evaluation(False)  # Adapter profile check, not solver repeat ordering.
    actual = target._evaluate_command(d, d.initial_controls, c, tighter, b, {})
    old = local._LocalBudget('D14 parity', 300., lambda: 0., max_arcs_per_evaluation=2)
    old.begin_control()
    cutoff, _ = local._native_local_arc(c, c.initial_state_si, 0., 20., True, tighter, old)
    final, _ = local._native_local_arc(c, cutoff, 20., 1000., False, tighter, old)
    assert actual['cutoff_state_si'] == cutoff and actual['final_state_si'] == final


@pytest.mark.parametrize("direction", [(math.nan, 0., 0.), (2., 0., 0.), (True, 0., 0.)])
def test_native_invalid_guidance_stops_counted_launch(direction: target.Vector3) -> None:
    d = synthetic()
    c = d.command(d.initial_controls)
    b = budget()
    b.begin_control()
    b.begin_evaluation(False)
    with pytest.raises(TrajectoryRefinementError):
        local._native_local_arc(c, c.initial_state_si, 0., 20., True, False, b, direction_at_s=lambda at: direction)
    assert b.native_arc_propagations == 1 and b.completed_arcs == 0


@pytest.mark.parametrize('delta', [0., 60.])
def test_unrepresentable_update_stops_without_trial(monkeypatch: pytest.MonkeyPatch, delta: float) -> None:
    tiny = (1e-20, 1e-20, 0., 0., 0., 0.)
    monkeypatch.setattr(target, '_solve_step', lambda r, j: {'outcome': 'ready', 'step_controls': tiny})
    # At zero the raw control changes, but the actual 1e9-second epoch does not.
    monkeypatch.setattr(target._TargetDomain, 'initial_controls', property(lambda d: (delta, 20., 0., 0., 0., 0.)))
    report, _, calls = correct(residual_at=lambda x: (100.,)*6)
    assert report['outcome'] == 'unrepresentable-update' and len(calls) == 13
    assert not report['iterations'][0]['trial_ids']


def test_sub_ulp_ignition_shift_does_not_rotate_physical_state() -> None:
    d = synthetic()
    base = d.command(d.initial_controls)
    shifted = d.command((1e-20, 20., 0., 0., 0., 0.))
    assert shifted.ignition_epoch_tdb_s == base.ignition_epoch_tdb_s
    assert shifted.initial_state_si == base.initial_state_si
    assert shifted.ignition_epoch_tdb_s+shifted.match_after_ignition_s == d.match_epoch_tdb_s


def test_no_predicted_decrease_stops_before_trials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(target, '_solve_step', lambda r, j: {'outcome': 'no-predicted-decrease'})
    report, _, calls = correct()
    assert len(calls) == 13 and report['outcome'] == 'no-predicted-decrease'


def test_nonfinite_prediction_raises_without_unsafe_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    matrix = tuple(map(tuple, np.eye(6)*1e308))
    monkeypatch.setattr(np.linalg, 'lstsq', lambda *args, **kwargs: (np.ones(6), [], 6, np.ones(6)))
    with pytest.raises(ValueError, match='predicted'):
        target._solve_step((1e308,)*6, matrix)


@pytest.mark.parametrize('phase', ['setup', 'late-evaluation', 'coast'])
def test_deadline_stops_d15_without_retry(monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    if phase == 'setup':
        monkeypatch.setattr(local.ephemeris, 'utc_to_tdb', lambda text: 0.)
        report = target._run_local_targeting(REFERENCE, STUDY, monotonic=lambda: 0.)
        assert report['outcome'] == 'failed' and report['propagation_evaluations'] == 0
        return
    d, b, report = synthetic(), budget(), {}
    base, calls = oracle()
    def late(domain: target._TargetDomain, x: target.Controls, command: local._LocalCommand,
             tighter: bool, shared: target._TargetBudget, entry: dict[str, Any]) -> dict[str, Any]:
        if phase == 'coast':
            shared.begin_arc(first_in_evaluation=True)
            shared.completed_arcs += 1
            shared.monotonic = lambda: 300.
            shared.begin_arc(first_in_evaluation=False)
        result = base(domain, x, command, tighter, shared, entry)
        shared.monotonic = lambda: 300.
        return result
    with pytest.raises(TrajectoryRefinementError, match='deadline'):
        target._correct_target(d, state_for(d, d.initial_controls, linear(d.initial_controls)), b, report, evaluate=late)
    assert b.propagation_evaluations == 1
    assert b.native_arc_propagations == (1 if phase == 'coast' else 2)
    assert len(calls) <= 1 and report['agreement'] == 'unavailable'


def test_runner_records_current_and_historical_provenance_without_live_study(monkeypatch: pytest.MonkeyPatch, retained: Any) -> None:
    _, study, _ = retained
    window = iter(study['launch_window_tdb_s'])
    monkeypatch.setattr(local.ephemeris, 'utc_to_tdb', lambda text: next(window))
    monkeypatch.setattr(local.ephemeris, 'kernel_metadata', lambda: {'synthetic': True})
    actual_correct = target._correct_target
    def injected(d: target._TargetDomain, old: local.State7, b: target._TargetBudget, report: dict[str, Any]) -> None:
        residual = tuple((v-t)/s for v, t, s in zip(old[:6], d.baseline.target_state_si[:6], target._RESIDUAL_SCALES))
        evaluate, _ = oracle(lambda x: residual)
        actual_correct(d, old, b, report, evaluate=evaluate)
    monkeypatch.setattr(target, '_correct_target', injected)
    report = target._run_local_targeting(REFERENCE, STUDY, monotonic=lambda: 0.)
    assert report['outcome'] == 'rank-condition-unresolved' and report['baseline_replay'] == 'pass'
    assert report['nominal_proposals'] == report['propagation_evaluations'] == 13
    assert report['native_arc_propagations'] == report['completed_arcs'] == 26
    assert report['mission_qualified'] is False and report['tighter_evaluations'] == 0
    assert report['source_sha256']['local_burn.py'] != report['historical_source_sha256']['local_burn.py']
    assert report['profiles'] == study['profiles'] or json.loads(json.dumps(report['profiles'])) == study['profiles']
    json.dumps(report, allow_nan=False)


def test_native_coast_failure_retains_completed_cutoff(monkeypatch: pytest.MonkeyPatch) -> None:
    d = synthetic()
    c = d.command(d.initial_controls)
    b = budget()
    b.begin_control()
    b.begin_evaluation(False)
    evidence: dict[str, Any] = {}
    real_arc = local._native_local_arc
    def fail_coast(command: local._LocalCommand, initial: local.State7, start: float, end: float,
                   burn: bool, tighter: bool, shared: target._TargetBudget, **kwargs: Any) -> tuple[local.State7, int]:
        if not burn:
            shared.begin_arc(first_in_evaluation=False)
            raise TrajectoryRefinementError('coast failure')
        return real_arc(command, initial, start, end, burn, tighter, shared, **kwargs)
    monkeypatch.setattr(local, '_native_local_arc', fail_coast)
    with pytest.raises(TrajectoryRefinementError, match='coast failure'):
        target._evaluate_command(d, d.initial_controls, c, False, b, evidence)
    assert evidence['cutoff_state_si'][6] == pytest.approx(c.target_state_si[6], abs=1e-6)
    assert b.native_arc_propagations == 2 and b.completed_arcs == 1


@pytest.mark.parametrize('failure', ['impact', 'dry', 'deadline'])
def test_actual_steered_native_stage_guards(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    from tudatpy.dynamics import simulator
    d, b = synthetic(), budget()
    c = d.command(d.initial_controls)
    if failure == 'impact':
        c = replace(c, initial_state_si=(100., 0., 0., -100., 0., 0., 2000.))
    elif failure == 'dry':
        c = replace(c, initial_state_si=c.initial_state_si[:-1]+(500.001,))
    else:
        native = simulator.create_dynamics_simulator
        def expired(*args: Any) -> Any:
            b.monotonic = lambda: 300.
            return native(*args)
        monkeypatch.setattr(simulator, 'create_dynamics_simulator', expired)
    b.begin_control()
    b.begin_evaluation(False)
    with pytest.raises(TrajectoryRefinementError):
        local._native_local_arc(c, c.initial_state_si, 0., 20., True, False, b,
            direction_at_s=lambda at: target._steering_direction(d.basis, d.initial_controls, at))
    assert b.native_arc_propagations == 1 and b.completed_arcs == 0
