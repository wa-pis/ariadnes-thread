"""Independent-oracle preparation; no frozen R5 scientific experiment."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'docs/adr/experiments/0138-short-coast-oracle.py'
spec = importlib.util.spec_from_file_location('r5_test_independent_oracle', PATH)
assert spec is not None and spec.loader is not None
oracle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = oracle
spec.loader.exec_module(oracle)


def idle() -> None:
    pass


def provider(body: str, epoch: float) -> dict[str, Any]:
    positions = {'Sun': (0., 0., 0.), 'Moon': (2e9, 0., 0.), 'Earth': (3e9, 0., 0.)}
    return {'body': body, 'epoch_tdb_s': epoch, 'origin': 'SSB', 'orientation': 'J2000',
            'aberration_correction': 'NONE', 'position_m': positions[body], 'velocity_m_s': (0.,)*3}


def test_import_without_scientific_modules() -> None:
    code = f"import runpy,sys;runpy.run_path({str(PATH)!r});assert not any(k.startswith(('space_nav','tudatpy','spiceypy','scipy','numpy')) for k in sys.modules)"
    subprocess.run([sys.executable, '-c', code], check=True, capture_output=True)


@pytest.mark.parametrize('value', [True, None, '1', math.inf, -math.inf, math.nan])
def test_numeric_rejection(value: object) -> None:
    with pytest.raises(oracle.OracleError):
        oracle.number(value)


@pytest.mark.parametrize('value', [(), (1, 2), (1, 2, True), (1, math.nan, 3)])
def test_vector_rejection(value: object) -> None:
    with pytest.raises(oracle.OracleError):
        oracle.vector(value, 3)


def test_direct_gravity_closed_form_and_translation() -> None:
    # mu8, x1, body3: direct=2. An incorrect indirect-origin subtraction gives10/9.
    value = oracle.acceleration((1., 0., 0.), {'C': (3., 0., 0.)}, {'C': 8.})
    assert value == (2., 0., 0.)
    assert oracle.acceleration((101., 200., -300.), {'C': (103., 200., -300.)}, {'C': 8.}) == value
    assert oracle.acceleration((0., 1., 0.), {'C': (0., 3., 0.)}, {'C': 8.}) == (0., 2., 0.)


@pytest.mark.parametrize('gm,position', [(-1., (3.,0.,0.)), (0., (3.,0.,0.)), (True, (3.,0.,0.)), (1., (1.,0.,0.))])
def test_force_domain(gm: object, position: tuple) -> None:
    with pytest.raises(oracle.OracleError):
        oracle.acceleration((1.,0.,0.), {'C': position}, {'C': gm})


def test_multiple_sources_signed_sum() -> None:
    assert oracle.acceleration((0.,)*3, {'L': (-2.,0.,0.), 'R': (2.,0.,0.)}, {'L': 8., 'R': 4.}) == (-1.,0.,0.)


@pytest.mark.parametrize('bad', [None, 0, 1, 'normal'])
def test_profile_rejects_hidden_options(bad: object) -> None:
    with pytest.raises(oracle.OracleError):
        oracle.profile(bad)


def test_frozen_profiles() -> None:
    assert oracle.profile(False).atol == (1e-7,)*3+(1e-10,)*3
    assert oracle.profile(False).rtol == 1e-12
    assert oracle.profile(True).atol == (1e-8,)*3+(1e-11,)*3
    assert oracle.profile(True).rtol == 1e-13
    assert oracle.profile(True).max_step_s == 2.5
    assert oracle.profile(True).first_step_s == .5


@pytest.mark.parametrize('field,value', [('body','Mars'), ('epoch_tdb_s',2.), ('epoch_tdb_s',True), ('origin','Sun'), ('orientation','ECLIPJ2000'), ('aberration_correction','LT'), ('position_m',(1.,2.)), ('velocity_m_s',(0.,True,0.))])
def test_query_validates_metadata_and_raw_retention(field: str, value: object) -> None:
    raw = provider('Sun',1.)
    raw[field] = value
    context = oracle.Context(idle)
    with pytest.raises(oracle.OracleError):
        context.query('Sun',1.,lambda *_: raw)
    assert context.last_returned_state is raw
    assert context.states_attempted == context.states_completed == 1


def test_deadline_after_provider_preserves_raw() -> None:
    calls = 0
    def check() -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('deadline')
    context = oracle.Context(check)
    with pytest.raises(RuntimeError, match='deadline'):
        context.query('Sun',0.,provider)
    assert context.last_returned_state['body'] == 'Sun'
    assert context.states_completed == 1


def test_provider_failure_counts_attempt_without_completion() -> None:
    def fail(*_: object) -> dict:
        raise oracle.OracleUnavailable('missing kernel')
    context = oracle.Context(idle)
    with pytest.raises(oracle.OracleUnavailable):
        context.query('Moon',0.,fail)
    assert context.states_attempted == 1 and context.states_completed == 0


def test_state_cap_before_call() -> None:
    context = oracle.Context(idle, states_attempted=30021)
    with pytest.raises(oracle.OracleError, match='cap'):
        context.query('Sun',0.,provider)
    assert context.states_completed == 0


def test_rhs_includes_earth_only_in_model_b() -> None:
    initial = (1e11, 0., 0., 0., 0., 0.)
    q = (0.,0.,0.,2.,3.,4.)
    context = oracle.Context(idle)
    a = oracle.correction_rhs(0.,q,initial,100.,'A',context,provider)
    b = oracle.correction_rhs(0.,q,initial,100.,'B',context,provider)
    assert a[:3] == b[:3] == (2.,3.,4.)
    assert a[3] == pytest.approx(-oracle.GM['Sun']/1e22-oracle.GM['Moon']/(98e9)**2, abs=1e-16, rel=0)
    assert b[3]-a[3] == pytest.approx(-oracle.GM['Earth']/(97e9)**2, abs=1e-16, rel=0)
    assert context.counts() == {'rhs_attempted':2,'rhs_completed':2,'states_attempted':6,'states_completed':6}
    assert tuple(context.minimum_checked_distances_m) == oracle.BODIES


def test_rhs_rejects_cap_and_wrong_interval() -> None:
    context = oracle.Context(idle, rhs_attempted=10000)
    with pytest.raises(oracle.OracleError,match='cap'):
        oracle.correction_rhs(0.,(0.,)*6,(1e9,0.,0.,0.,0.,0.),0.,'A',context,provider)
    assert context.states_attempted == 0
    for offset in (-1.,301.,True):
        with pytest.raises(oracle.OracleError):
            oracle.correction_rhs(offset,(0.,)*6,(1e9,0.,0.,0.,0.,0.),0.,'A',oracle.Context(idle),provider)


def test_adaptive_stage_times_need_not_be_monotonic() -> None:
    context = oracle.Context(idle)
    for offset in (2.,1.,0.):
        oracle.correction_rhs(offset,(0.,)*6,(1e9,0.,0.,0.,0.,0.),0.,'B',context,provider)
    assert context.rhs_completed == 3


@pytest.mark.parametrize('body', oracle.BODIES)
def test_guard_on_and_inside_sphere(body: str) -> None:
    states = {b:provider(b,0.) for b in oracle.BODIES}
    source = states[body]['position_m']
    context = oracle.Context(idle)
    position = (source[0]+oracle.GUARDS[body],source[1],source[2])
    with pytest.raises(oracle.OracleError,match=body):
        context.guard(position, states)


def test_zero_force_correction_solve_exact_linear_motion() -> None:
    initial = (10.,-20.,30.,2.,-1.,.5)
    result = oracle.integrate_corrections(initial,100.,False,lambda _t,q:(*q[3:],0.,0.,0.),idle)
    for offset,row in zip(oracle.OFFSETS,result['samples'],strict=True):
        assert row['epoch_tdb_s'] == 100.+offset
        assert row['state'] == (*tuple(initial[j]+initial[j+3]*offset for j in range(3)),*initial[3:])
    assert result['nfev'] > 0


@pytest.mark.parametrize('tighter',[False,True])
def test_circular_orbit_independent_closed_form(tighter: bool) -> None:
    radius,mu = 7e6,3.986004354682959e14
    speed = math.sqrt(mu/radius)
    initial = (radius,0.,0.,0.,speed,0.)
    omega = math.sqrt(mu/radius**3)
    def rhs(elapsed: float,q: tuple) -> tuple:
        position = tuple(math.fsum((initial[j],initial[j+3]*elapsed,q[j])) for j in range(3))
        return (*q[3:],*oracle.acceleration(position,{'C':(0.,0.,0.)},{'C':mu}))
    result = oracle.integrate_corrections(initial,0.,tighter,rhs,idle)
    for elapsed,row in zip(oracle.OFFSETS,result['samples'],strict=True):
        angle = omega*elapsed
        expected = (radius*math.cos(angle),radius*math.sin(angle),0.,-speed*math.sin(angle),speed*math.cos(angle),0.)
        assert math.dist(row['state'][:3],expected[:3]) <= 1e-6
        assert math.dist(row['state'][3:],expected[3:]) <= 1e-8


def test_solve_after_return_failure_preserves_arrays(monkeypatch: pytest.MonkeyPatch) -> None:
    import numpy as np
    import scipy.integrate
    returned = False
    def fake(*args: object,**kwargs: object) -> object:
        nonlocal returned
        assert kwargs['method'] == 'DOP853'
        assert kwargs['atol'] == (1e-7,)*3+(1e-10,)*3
        assert kwargs['t_eval'] == oracle.OFFSETS
        returned = True
        return SimpleNamespace(success=True,message='ok',t=np.array(oracle.OFFSETS),y=np.zeros((6,7)),nfev=1)
    def check() -> None:
        if returned:
            raise RuntimeError('after solve deadline')
    monkeypatch.setattr(scipy.integrate,'solve_ivp',fake)
    with pytest.raises(oracle.ReturnedOracleFailure) as error:
        oracle.integrate_corrections((0.,)*6,0.,False,lambda *_:(0.,)*6,check)
    assert len(error.value.returned['corrections']) == 7
    assert error.value.returned['success'] is True


def test_spice_provider_matches_actual_tudat_boundary() -> None:
    from space_nav import ephemeris
    from tudatpy.interface import spice
    ephemeris.kernel_metadata()
    expected = tuple(spice.get_body_cartesian_state_at_epoch('Moon','SSB','J2000','NONE',0.))
    actual = oracle.spice_provider('Moon',0.)
    assert math.dist(actual['position_m'],expected[:3]) <= .001
    assert math.dist(actual['velocity_m_s'],expected[3:]) <= 1e-6
    assert actual['epoch_tdb_s'] == 0. and actual['aberration_correction'] == 'NONE'


@pytest.mark.parametrize('corruption', ['failure','epochs','rows','initial','nonfinite'])
def test_solver_result_gates_preserve_raw(monkeypatch: pytest.MonkeyPatch, corruption: str) -> None:
    import numpy as np
    import scipy.integrate
    times = np.array(oracle.OFFSETS)
    values = np.zeros((6,7))
    if corruption == 'epochs':
        times[-1] = 299.
    elif corruption == 'rows':
        values = np.zeros((6,6))
    elif corruption == 'initial':
        values[0,0] = 1.
    elif corruption == 'nonfinite':
        values[0,1] = math.nan
    result = SimpleNamespace(success=corruption!='failure',message='synthetic',t=times,y=values,nfev=1)
    monkeypatch.setattr(scipy.integrate,'solve_ivp',lambda *_,**__:result)
    with pytest.raises(oracle.ReturnedOracleFailure) as error:
        oracle.integrate_corrections((0.,)*6,0.,False,lambda *_:(0.,)*6,idle)
    assert 'corrections' in error.value.returned


def test_spice_boundary_translates_actual_library_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import spiceypy
    def fail(*_: object) -> object:
        raise RuntimeError('synthetic CSPICE failure')
    monkeypatch.setattr(spiceypy,'spkezr',fail)
    with pytest.raises(oracle.OracleUnavailable,match='Moon state unavailable'):
        oracle.spice_provider('Moon',0.)


def test_spice_boundary_passes_exact_epoch_and_si(monkeypatch: pytest.MonkeyPatch) -> None:
    import spiceypy
    calls = []
    def fake(*args: object) -> tuple:
        calls.append(args)
        return [1.,2.,3.,4.,5.,6.],0.
    monkeypatch.setattr(spiceypy,'spkezr',fake)
    result = oracle.spice_provider('Earth',123.125)
    assert calls == [('Earth',123.125,'J2000','NONE','SSB')]
    assert result['position_m'] == (1000.,2000.,3000.)
    assert result['velocity_m_s'] == (4000.,5000.,6000.)


def test_solve_model_only_binds_frozen_rhs(monkeypatch: pytest.MonkeyPatch) -> None:
    called = []
    def fake(initial: tuple,epoch: float,tighter: bool,rhs: object,check: object) -> dict:
        called.append((initial,epoch,tighter))
        rhs(0.,(0.,)*6)
        return {'samples':[]}
    monkeypatch.setattr(oracle,'integrate_corrections',fake)
    context = oracle.Context(idle)
    value = oracle.solve_model((1e9,0.,0.,0.,0.,0.),100.,'B',True,context,provider)
    assert called == [((1e9,0.,0.,0.,0.,0.),100.,True)]
    assert value['model'] == 'B'
    assert value['counts_after']['rhs_completed'] == 1
    with pytest.raises(oracle.OracleError,match='model'):
        oracle.solve_model((1e9,0.,0.,0.,0.,0.),100.,'C',True,context,provider)


def test_force_rejects_unrepresentable_squared_distance() -> None:
    with pytest.raises(oracle.OracleError,match='numeric range'):
        oracle.acceleration((0.,)*3,{'C':(1e200,0.,0.)},{'C':1.})


def test_spice_si_conversion_rejects_overflow(monkeypatch: pytest.MonkeyPatch) -> None:
    import spiceypy
    monkeypatch.setattr(spiceypy,'spkezr',lambda *_:([1e308,0.,0.,0.,0.,0.],0.))
    with pytest.raises(oracle.OracleError,match='finite'):
        oracle.spice_provider('Earth',0.)
