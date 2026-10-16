"""D14 implementation qualification; never execute the retained mission study."""

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
from space_nav.errors import TrajectoryRefinementError


REFERENCE = Path("docs/adr/experiments/0104-lunar-departure-reference.json")


@pytest.fixture
def retained() -> dict[str, Any]:
    return json.loads(REFERENCE.read_text())


def prepared(retained: dict[str, Any]) -> local._LocalCommand:
    return local._make_local_command(retained, (978307200., 1009843200.))


def synthetic() -> local._LocalCommand:
    return local._LocalCommand(1e12, 1., 500., 1000., 450., (1., 0., 0.),
        1e9, 20., 40., (1e6, 0., 0., 0., 1000., 0., 2000.),
        (1e7, 0., 0., 0., 1000., 0., 1990.), 1e7)


def budget() -> local._LocalBudget:
    result = local._LocalBudget("D14 test", 300., lambda: 0., max_arcs_per_evaluation=2)
    result.begin_control()
    return result


def test_reference_hash_and_full_branch_binding(retained: dict[str, Any]) -> None:
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == local._REFERENCE_SHA256
    command = prepared(retained)
    branch = retained["results"]["free"]["branches"][0]
    np.testing.assert_allclose(command.direction_j2000,
        np.array(branch["delta_v_m_s"])/branch["delta_v_norm_m_s"], atol=1e-15, rtol=0)
    assert command.match_radius_m == 18374000.
    assert command.match_after_ignition_s-command.cutoff_after_ignition_s > 0
    json.dumps(local.asdict(command), allow_nan=False)


@pytest.mark.parametrize("field", ["position_m", "parking_velocity_m_s", "hyperbolic_velocity_m_s",
    "delta_v_m_s", "phase_rad", "post_departure_mass_kg", "departure_duration_s", "eccentricity"])
def test_modified_branch_rejected(retained: dict[str, Any], field: str) -> None:
    branch = retained["results"]["free"]["branches"][0]
    if isinstance(branch[field], list):
        branch[field][0] += .01
    else:
        branch[field] += .01
    with pytest.raises(ValueError, match="reconstruction"):
        prepared(retained)


@pytest.mark.parametrize("field", ["virtual_periapsis_epoch_tdb_s", "gravitational_parameter_m3_s2", "parking_radius_m"])
def test_modified_reference_rejected(retained: dict[str, Any], field: str) -> None:
    retained["results"]["free"][field] += 1
    with pytest.raises(ValueError, match="reconstruction"):
        prepared(retained)


@pytest.mark.parametrize("window", [(0., 1.), (1e10, 0.), (True, 1e10), (0., math.nan), (0., math.inf)])
def test_ignition_window_rejected(retained: dict[str, Any], window: tuple[float, float]) -> None:
    with pytest.raises(ValueError):
        local._make_local_command(retained, window)


def test_independent_parking_rotation_and_decimal_mass(retained: dict[str, Any]) -> None:
    c = prepared(retained)
    branch = retained["results"]["free"]["branches"][0]
    r, v = np.array(c.initial_state_si[:3]), np.array(c.initial_state_si[3:6])
    h = np.cross(r, v)
    axis = h/np.linalg.norm(h)
    theta = math.sqrt(c.mu_m3_s2/np.linalg.norm(r)**3)*c.cutoff_after_ignition_s/2
    def rotate(vector: np.ndarray) -> np.ndarray:
        return vector*math.cos(theta)+np.cross(axis, vector)*math.sin(theta)+axis*np.dot(axis, vector)*(1-math.cos(theta))
    np.testing.assert_allclose(rotate(r), branch["position_m"], atol=.001, rtol=0)
    np.testing.assert_allclose(rotate(v), branch["parking_velocity_m_s"], atol=1e-6, rtol=0)
    with localcontext() as ctx:
        ctx.prec = 50
        exhaust = Decimal('9.80665')*Decimal('450')
        mass = Decimal(2000)*(-Decimal(str(branch['delta_v_norm_m_s']))/exhaust).exp()
        duration = (Decimal(2000)-mass)*exhaust/Decimal(1000)
        assert abs(c.target_state_si[6]-float(mass)) < 1e-10
        assert abs(c.cutoff_after_ignition_s-float(duration)) < 1e-9


def test_independent_conic_and_gaussian_time_oracle(retained: dict[str, Any]) -> None:
    c = prepared(retained)
    branch = retained["results"]["free"]["branches"][0]
    r, v = np.array(c.target_state_si[:3]), np.array(c.target_state_si[3:6])
    h = np.cross(r, v)
    evec = np.cross(v, h)/c.mu_m3_s2-r/np.linalg.norm(r)
    assert np.linalg.norm(evec) == pytest.approx(branch["eccentricity"], abs=1e-12)
    np.testing.assert_allclose(h, branch["angular_momentum_m2_s"], atol=1e-5, rtol=1e-12)
    assert np.dot(r, v) > 0
    assert np.linalg.norm(r) == pytest.approx(c.match_radius_m, abs=.001)
    assert np.dot(v, v)/2-c.mu_m3_s2/np.linalg.norm(r) == pytest.approx(branch["specific_energy_m2_s2"], rel=1e-10)
    u = np.array(branch["position_m"])/np.linalg.norm(branch["position_m"])
    nu = math.acos(float(np.dot(u, r)/np.linalg.norm(r)))
    nodes, weights = np.polynomial.legendre.leggauss(128)
    angles = (nodes+1)*nu/2
    radii = np.dot(h, h)/c.mu_m3_s2/(1+np.linalg.norm(evec)*np.cos(angles))
    dt = float(np.sum(weights*radii**2/np.linalg.norm(h))*nu/2)
    assert abs(dt-(c.match_after_ignition_s-c.cutoff_after_ignition_s/2)) <= .001


@pytest.mark.parametrize("field", ["mu_m3_s2", "shape_radius_m", "dry_mass_kg", "thrust_n", "isp_s",
                                 "cutoff_after_ignition_s", "match_after_ignition_s", "match_radius_m"])
@pytest.mark.parametrize("value", [0., -1., True, math.nan, math.inf])
def test_command_physical_domain(field: str, value: float) -> None:
    with pytest.raises(ValueError):
        replace(synthetic(), **{field: value})


@pytest.mark.parametrize("state", [(0.,)*7, (math.nan,)*7, (1.,)*6,
                                  (1e6, 0., 0., 0., 1000., 0., 500.)])
def test_state_guards(state: local.State7) -> None:
    with pytest.raises(ValueError):
        local._check_local_state(synthetic(), state)


@pytest.mark.parametrize("position,velocity,passed", [(10., .01, True), (10.00001, 0., False), (0., .010001, False)])
def test_closure_thresholds(position: float, velocity: float, passed: bool) -> None:
    c = synthetic()
    target = list(c.target_state_si)
    target[1] += position
    target[5] += velocity
    assert local._closure(c, tuple(target))["closure"] == ("pass" if passed else "fail")


def test_four_arc_budget_and_no_retry() -> None:
    b = budget()
    for i in range(4):
        b.begin_arc(first_in_evaluation=i % 2 == 0)
        with pytest.raises(TrajectoryRefinementError, match="no retry"):
            b.begin_arc(first_in_evaluation=False)
        b.completed_arcs += 1
    with pytest.raises(TrajectoryRefinementError, match="four ordered"):
        b.begin_arc(first_in_evaluation=True)


def test_shared_deadline_and_backward_clock() -> None:
    for end in (300., -1.):
        ticks = iter((0., end))
        b = local._LocalBudget("test", 300., lambda: next(ticks), max_arcs_per_evaluation=2)
        with pytest.raises(TrajectoryRefinementError):
            b.check()


@pytest.mark.parametrize("tighter", [False, True])
def test_native_circular_orbit_oracle(tighter: bool) -> None:
    c = synthetic()
    b = budget()
    # Exercise an unforced analytic orbit with a fresh, correctly ordered coast.
    b.native_arc_propagations = b.completed_arcs = b._arcs_in_evaluation = 1
    final, count = local._native_local_arc(c, c.initial_state_si, 0., math.tau*1000+100., False, tighter, b)
    angle = .1
    expected = (1e6*math.cos(angle), 1e6*math.sin(angle), 0.,
                -1000*math.sin(angle), 1000*math.cos(angle), 0., 2000.)
    assert math.dist(final[:3], expected[:3]) < .001
    assert math.dist(final[3:6], expected[3:6]) < 1e-6
    assert final[6] == 2000. and count > 2


@pytest.mark.parametrize("tighter", [False, True])
def test_native_thrust_mass_oracle_and_exact_handoff(tighter: bool) -> None:
    c = replace(synthetic(), mu_m3_s2=1e-12)
    b = budget()
    cutoff, _ = local._native_local_arc(c, c.initial_state_si, 0., 20., True, tighter, b)
    coast, _ = local._native_local_arc(c, cutoff, 20., 40., False, tighter, b)
    mf = 2000-1000/(9.80665*450)*20
    speed = 9.80665*450*math.log(2000/mf)
    assert cutoff[6] == pytest.approx(mf, abs=1e-6)
    assert cutoff[3] == pytest.approx(speed, abs=1e-6)
    assert cutoff[4:6] == pytest.approx((1000., 0.), abs=1e-6)
    assert coast[6] == cutoff[6]
    assert coast[:3] == pytest.approx(tuple(x+20*v for x, v in zip(cutoff[:3], cutoff[3:6])), abs=.001)


def mocked_run(monkeypatch: pytest.MonkeyPatch, retained: dict[str, Any], *, fail_at: int = -1,
               delta_m: float = 0., delta_m_s: float = 0., delta_kg: float = 0.,
               cutoff_delta_kg: float = 0.) -> tuple[dict[str, Any], list[tuple[Any, ...]]]:
    c = prepared(retained)
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(local.ephemeris, "utc_to_tdb", lambda text: 978307200. if '01-01' in text else 1009843200.)
    monkeypatch.setattr(local.ephemeris, "kernel_metadata", lambda: {"test": True})
    def arc(command: local._LocalCommand, state: local.State7, start: float, end: float,
            burn: bool, tighter: bool, b: local._LocalBudget) -> tuple[local.State7, int]:
        calls.append((command, state, start, end, burn, tighter))
        b.begin_arc(first_in_evaluation=burn)
        if len(calls)-1 == fail_at:
            raise TrajectoryRefinementError("synthetic native failure")
        b.completed_arcs += 1
        result = list(c.target_state_si)
        if burn:
            result[6] += cutoff_delta_kg
        if tighter and not burn:
            result[1] += delta_m
            result[5] += delta_m_s
            result[6] += delta_kg
        return tuple(result), 2
    monkeypatch.setattr(local, "_native_local_arc", arc)
    return local._run_local_burn(REFERENCE, monotonic=lambda: 0.), calls


def test_frozen_profiles_handoff_and_separate_miss(monkeypatch: pytest.MonkeyPatch, retained: dict[str, Any]) -> None:
    c = prepared(retained)
    actual_closure = local._closure
    monkeypatch.setattr(local, "_closure", lambda command, final: {**actual_closure(command, final), "closure": "fail"})
    result, calls = mocked_run(monkeypatch, retained)
    assert len(calls) == 4 and result["agreement"] == "pass"
    assert all(r["closure"] == "fail" and r["outcome"] == "completed" for r in result["runs"])
    assert calls[0][0] == calls[2][0] == c
    assert calls[1][1] == result["runs"][0]["cutoff_state_si"]
    assert calls[3][1] == result["runs"][1]["cutoff_state_si"]
    assert result["native_arc_propagations"] == result["completed_arcs"] == 4
    assert result["mission_qualified"] is False
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("fail_at", range(4))
def test_failure_stops_without_retry(monkeypatch: pytest.MonkeyPatch, retained: dict[str, Any], fail_at: int) -> None:
    result, calls = mocked_run(monkeypatch, retained, fail_at=fail_at)
    assert len(calls) == fail_at+1
    assert result["agreement"] == "unavailable"
    assert result["native_arc_propagations"] == fail_at+1
    assert result["completed_arcs"] == fail_at
    assert "synthetic native failure" in result["reason"]
    assert result["runs"][int(fail_at >= 2)]["outcome"] == "failed"
    if fail_at < 2:
        assert result["runs"][1]["outcome"] == "skipped"


@pytest.mark.parametrize("kwargs", [{"delta_m": 1.1}, {"delta_m_s": .0011}, {"delta_kg": 1.1e-6}])
def test_agreement_threshold_failures(monkeypatch: pytest.MonkeyPatch, retained: dict[str, Any], kwargs: dict[str, float]) -> None:
    result, calls = mocked_run(monkeypatch, retained, **kwargs)
    assert len(calls) == 4 and result["agreement"] == "fail"


def test_hash_rejection_no_native(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wrong = tmp_path/'wrong.json'
    wrong.write_text('{}')
    monkeypatch.setattr(local, "_native_local_arc", lambda *args: pytest.fail("must not launch"))
    result = local._run_local_burn(wrong, monotonic=lambda: 0.)
    assert result["native_arc_propagations"] == 0
    assert "SHA256" in result["reason"]
    assert all(run["outcome"] == "skipped" for run in result["runs"])


def test_profiles_are_explicit_strictly_tighter_and_fresh() -> None:
    nominal, tighter = local._local_profile(False), local._local_profile(True)
    assert tighter['maximum_step_s'] < nominal['maximum_step_s']
    assert tighter['relative_tolerance'] < nominal['relative_tolerance']
    assert all(a < b for a, b in zip(tighter['absolute_tolerances_si'], nominal['absolute_tolerances_si']))
    assert local._local_profile(False) == nominal and local._local_profile(False) is not nominal
    assert deepcopy(nominal) == nominal


@pytest.mark.parametrize("value", [1, None, 'yes'])
def test_profile_rejects_nonboolean(value: Any) -> None:
    with pytest.raises(ValueError):
        local._local_profile(value)


@pytest.mark.parametrize("updates", [
    {"direction_j2000": (0., 0., 0.)}, {"direction_j2000": (True, 0., 0.)},
    {"initial_state_si": [1.]*7}, {"ignition_epoch_tdb_s": math.nan},
    {"match_after_ignition_s": 10.}, {"match_radius_m": .5},
])
def test_command_additional_domains(updates: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        replace(synthetic(), **updates)


def test_retained_candidate_and_reserve_guards(retained: dict[str, Any]) -> None:
    wrong = deepcopy(retained)
    wrong['candidate']['candidate_id'] = 'other'
    with pytest.raises(ValueError, match='identity'):
        prepared(wrong)
    wrong = deepcopy(retained)
    wrong['results']['free']['branches'][0]['estimate_status'] = 'rejected-dry-mass'
    with pytest.raises(ValueError, match='reconstruction'):
        prepared(wrong)


@pytest.mark.parametrize("end,burn,tighter", [(0., True, False), (math.nan, True, False),
                                           (1., 1, False), (1., True, 1)])
def test_invalid_arc_never_launches(end: float, burn: Any, tighter: Any) -> None:
    b = budget()
    with pytest.raises(ValueError):
        local._native_local_arc(synthetic(), synthetic().initial_state_si, 0., end, burn, tighter, b)
    assert b.native_arc_propagations == 0


@pytest.mark.parametrize("failure", ['exception', 'unsuccessful', 'empty', 'end', 'start', 'reset',
                                    'nonfinite', 'impact', 'dry', 'mass'])
def test_native_failure_history_guards(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    from types import SimpleNamespace
    from tudatpy.dynamics import simulator
    c = synthetic()
    initial = c.initial_state_si
    final = list(initial)
    final[6] -= 1000/(9.80665*450)
    history = {0.: np.array(initial), 1.: np.array(final)}
    if failure == 'empty':
        history = {}
    elif failure == 'end':
        history[.9] = history.pop(1.)
    elif failure == 'start':
        history[.1] = history.pop(0.)
    elif failure == 'reset':
        history[0.][3] += 1.
    elif failure == 'nonfinite':
        history[1.][0] = math.nan
    elif failure == 'impact':
        history[1.][:3] = 0.
    elif failure == 'dry':
        history[1.][6] = 500.
    elif failure == 'mass':
        history[1.][6] += .01
    def native(*args: Any) -> Any:
        if failure == 'exception':
            raise RuntimeError('injected native failure')
        return SimpleNamespace(integration_completed_successfully=failure != 'unsuccessful', state_history=history)
    monkeypatch.setattr(simulator, 'create_dynamics_simulator', native)
    b = budget()
    with pytest.raises(TrajectoryRefinementError):
        local._native_local_arc(c, initial, 0., 1., True, False, b)
    assert b.native_arc_propagations == 1 and b.completed_arcs == 0


def test_actual_derivative_stage_impact_guard() -> None:
    c = replace(synthetic(), initial_state_si=(100., 0., 0., -100., 0., 0., 2000.))
    b = budget()
    with pytest.raises(TrajectoryRefinementError):
        local._native_local_arc(c, c.initial_state_si, 0., 1., True, False, b)
    assert b.completed_arcs == 0


def test_expired_setup_stops_before_native(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = iter((0., 300.))
    monkeypatch.setattr(local, '_native_local_arc', lambda *args: pytest.fail('no launch'))
    result = local._run_local_burn(REFERENCE, monotonic=lambda: next(ticks))
    assert result['native_arc_propagations'] == 0 and result['agreement'] == 'unavailable'
    assert 'deadline' in result['reason']


def test_guard_failure_after_preparation_stops_schedule(monkeypatch: pytest.MonkeyPatch, retained: dict[str, Any]) -> None:
    result, calls = mocked_run(monkeypatch, retained, cutoff_delta_kg=.01)
    # Injected oracle mismatch must stop at the burn, before coast or tighter.
    assert len(calls) == 1 and result['agreement'] == 'unavailable'
    assert 'cutoff mass' in result['reason']


def test_coast_mass_change_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from tudatpy.dynamics import simulator
    c = synthetic()
    final = c.initial_state_si[:-1]+(c.initial_state_si[-1]-1.,)
    monkeypatch.setattr(simulator, 'create_dynamics_simulator', lambda *args:
        SimpleNamespace(integration_completed_successfully=True,
                        state_history={0.: np.array(c.initial_state_si), 1.: np.array(final)}))
    b = budget()
    b.native_arc_propagations = b.completed_arcs = b._arcs_in_evaluation = 1
    with pytest.raises(TrajectoryRefinementError, match='coast mass changed'):
        local._native_local_arc(c, c.initial_state_si, 0., 1., False, False, b)
    assert b.completed_arcs == 1 and b.native_arc_propagations == 2


def test_native_callback_enforces_shared_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    from tudatpy.dynamics import simulator
    native = simulator.create_dynamics_simulator
    b = budget()
    c = synthetic()
    def expired(*args: Any) -> Any:
        b.monotonic = lambda: 300.
        return native(*args)
    monkeypatch.setattr(simulator, 'create_dynamics_simulator', expired)
    with pytest.raises(TrajectoryRefinementError):
        local._native_local_arc(c, c.initial_state_si, 0., 1., True, False, b)
    assert b.native_arc_propagations == 1 and b.completed_arcs == 0


def test_runtime_provenance_failure_never_launches(monkeypatch: pytest.MonkeyPatch, retained: dict[str, Any]) -> None:
    def missing(name: str) -> Any:
        raise ImportError('injected missing native runtime')
    monkeypatch.setattr(local, 'import_module', missing)
    result, calls = mocked_run(monkeypatch, retained)
    assert not calls and result['native_arc_propagations'] == 0
    assert 'runtime provenance unavailable' in result['reason']


def test_overflow_residual_is_rejected_not_serialized() -> None:
    c = synthetic()
    state = (1e308, 0., 0., 0., 0., 0., 2000.)
    target = (-1e308, 0., 0., 0., 0., 0., 2000.)
    with pytest.raises(ValueError, match='residual'):
        local._closure(replace(c, target_state_si=target), state)


@pytest.mark.parametrize('kwargs', [{}, {'delta_m': 1.}, {'delta_m_s': .001}])
def test_agreement_accepts_threshold_equality(monkeypatch: pytest.MonkeyPatch, retained: dict[str, Any], kwargs: dict[str, float]) -> None:
    result, calls = mocked_run(monkeypatch, retained, **kwargs)
    assert len(calls) == 4 and result['agreement'] == 'pass'
    assert result['outcome'] == 'completed'
