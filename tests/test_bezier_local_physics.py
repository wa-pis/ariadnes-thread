"""Independent D17 guidance/native oracles; no retained targeting campaign."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal, localcontext
import itertools
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from space_nav import bezier_local_targeting as bezier
from space_nav import local_burn as local, local_targeting as target
from space_nav.errors import TrajectoryRefinementError


Controls8 = tuple[float, ...]
REFERENCE = Path("docs/adr/experiments/0104-lunar-departure-reference.json")
STUDY = Path("docs/adr/experiments/0107-local-finite-burn-study.json")


def synthetic(duration_s: float = 20.) -> target._TargetDomain:
    theta = -.001*duration_s/2
    initial = (1e6*math.cos(theta), 1e6*math.sin(theta), 0.,
               -1000*math.sin(theta), 1000*math.cos(theta), 0., 2000.)
    command = local._LocalCommand(
        1e12, 1., 500., 1000., 450., (1., 0., 0.), 1e9, duration_s,
        1000., initial, (0., 100., 0., 0., 0., 0., 1990.), 100.)
    return target._TargetDomain(command, (1e6, 0., 0., 0., 1000., 0.),
                               (1e9-2000, 1e9+2000), 1.)


def shared_budget() -> bezier._BezierBudget:
    budget = bezier._BezierBudget("D17 manufactured native", 300., lambda: 0.,
                                  max_arcs_per_evaluation=2)
    budget.begin_control()
    budget.begin_evaluation(False)
    return budget


def de_casteljau(x: Controls8, fraction: float) -> np.ndarray:
    """Independent affine interpolation, not the production Bernstein formula."""
    start, middle, end = np.asarray(x[2:]).reshape(3, 2)
    first = start+fraction*(middle-start)
    second = middle+fraction*(end-middle)
    return first+fraction*(second-first)


def independent_direction(basis: target.Basis, x: Controls8, at_s: float) -> np.ndarray:
    slopes = de_casteljau(x, at_s/x[1])
    raw = np.asarray(basis[0])+slopes[0]*np.asarray(basis[1])+slopes[1]*np.asarray(basis[2])
    return raw/np.linalg.norm(raw)


@pytest.mark.parametrize("slopes", list(itertools.product((-1., 1.), repeat=6)))
def test_all_chart_corners_de_casteljau_convex_hull_and_nonsingularity(
    slopes: tuple[float, ...],
) -> None:
    domain = synthetic()
    x = (0., 20.)+slopes
    nodes = np.asarray(slopes).reshape(3, 2)
    for fraction in np.linspace(0., 1., 33):
        point = de_casteljau(x, float(fraction))
        assert np.all(point >= nodes.min(axis=0)-1e-15)
        assert np.all(point <= nodes.max(axis=0)+1e-15)
        raw = np.asarray(domain.basis[0])+point[0]*np.asarray(domain.basis[1])+point[1]*np.asarray(domain.basis[2])
        assert np.linalg.norm(raw) >= 1.
        actual = bezier._bezier_direction(domain.basis, x, float(fraction)*20)
        np.testing.assert_allclose(actual, independent_direction(domain.basis, x, float(fraction)*20),
                                   atol=5e-16, rtol=0)
        assert math.hypot(*actual) == pytest.approx(1., abs=3e-16)


@pytest.mark.parametrize("reference", [(1., 0., 0.), (0., 1., 0.),
                                      (0., 0., 1.), (1/math.sqrt(3),)*3])
def test_smooth_chart_rate_in_rotated_orthonormal_basis(reference: target.Vector3) -> None:
    basis = target._steering_basis(reference)
    x = (0., 200., .3, -.8, .9, .7, -.4, .6)
    points = np.asarray(x[2:]).reshape(3, 2)
    bound_rad_s = 2*max(np.linalg.norm(points[1]-points[0]),
                         np.linalg.norm(points[2]-points[1]))/x[1]
    previous: np.ndarray | None = None
    for fraction in np.linspace(0., 1., 201):
        slopes = de_casteljau(x, float(fraction))
        derivative = 2*((1-fraction)*(points[1]-points[0])+fraction*(points[2]-points[1]))/x[1]
        raw = np.asarray(basis[0])+slopes@np.asarray(basis[1:])
        raw_derivative = derivative@np.asarray(basis[1:])
        direction = raw/np.linalg.norm(raw)
        rate = (raw_derivative-direction*np.dot(direction, raw_derivative))/np.linalg.norm(raw)
        assert np.linalg.norm(rate) <= bound_rad_s+1e-15
        actual = np.asarray(bezier._bezier_direction(basis, x, float(fraction)*x[1]))
        np.testing.assert_allclose(actual, direction, atol=5e-16, rtol=0)
        if previous is not None:
            assert np.linalg.norm(actual-previous) <= bound_rad_s+1e-15
        previous = actual


def test_bezier_control_point_is_not_midpoint_time_value() -> None:
    domain = synthetic()
    x = (0., 20., -.8, .7, .9, -.9, .2, .3)
    actual = bezier._bezier_direction(domain.basis, x, 10.)
    midpoint = (np.asarray(x[2:4])+2*np.asarray(x[4:6])+np.asarray(x[6:8]))/4
    expected = np.asarray((1., *midpoint))
    expected /= np.linalg.norm(expected)
    np.testing.assert_allclose(actual, expected, atol=1e-15, rtol=0)
    control_point = np.asarray((1., x[4], x[5]))
    control_point /= np.linalg.norm(control_point)
    assert np.linalg.norm(np.asarray(actual)-control_point) > .1


@pytest.mark.parametrize("fraction", [-1., -.25, -.001, 0., .5, 1., 1.001, 1.25, 2.])
def test_rk_stage_extension_is_same_polynomial_not_clamped(fraction: float) -> None:
    domain = synthetic()
    x = (0., 20., -.8, .7, .9, -.9, .2, .3)
    actual = bezier._bezier_direction(domain.basis, x, fraction*20)
    np.testing.assert_allclose(actual, independent_direction(domain.basis, x, fraction*20),
                               atol=1e-15, rtol=0)
    if fraction < 0. or fraction > 1.:
        boundary = bezier._bezier_direction(domain.basis, x, min(1., max(0., fraction))*20)
        assert math.dist(actual, boundary) > 1e-5


@pytest.mark.parametrize("slopes", [(0., 0., 0., 0.), (.3, -.8, -.4, .6), (1., -1., -1., 1.)])
def test_embedded_old_linear_chart_including_stage_extrapolation(slopes: tuple[float, ...]) -> None:
    domain = synthetic()
    old = (0., 20.)+slopes
    x = old[:4]+((slopes[0]+slopes[2])/2, (slopes[1]+slopes[3])/2)+old[4:]
    assert bezier._linear_controls(x) == old
    for at_s in np.linspace(-5., 25., 301):
        actual = bezier._bezier_direction(domain.basis, x, float(at_s))
        expected = target._steering_direction(domain.basis, old, float(at_s))
        np.testing.assert_allclose(actual, expected, atol=1e-15, rtol=0)


@pytest.mark.parametrize("value", [True, math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("index", range(8))
def test_eight_component_controls_reject_nonfinite_or_boolean(index: int, value: float) -> None:
    controls = [0., 20., .1, -.2, .3, -.4, .5, -.6]
    controls[index] = value
    with pytest.raises(ValueError):
        bezier._command(synthetic(), tuple(controls))


@pytest.mark.parametrize("controls", [(0.,)*6, (0.,)*7, (0.,)*9, [0., 20.]+[0.]*6])
def test_control_shape_is_immutable_eight_not_six(controls: Any) -> None:
    with pytest.raises(ValueError):
        bezier._eight(controls, "D17 controls")


@pytest.mark.parametrize("relative_s", [True, math.nan, math.inf, -math.inf])
def test_nonfinite_or_boolean_stage_time_is_not_a_direction(relative_s: float) -> None:
    domain = synthetic()
    with pytest.raises(ValueError):
        bezier._bezier_direction(domain.basis, (0., 20., .1, -.2, .3, -.4, .5, -.6),
                                 relative_s)


@pytest.mark.parametrize("index", range(2, 8))
@pytest.mark.parametrize("value", [-1.000000001, 1.000000001])
def test_all_six_slope_bounds_authoritative(index: int, value: float) -> None:
    controls = [0., 20., 0., 0., 0., 0., 0., 0.]
    controls[index] = value
    with pytest.raises(ValueError):
        bezier._command(synthetic(), tuple(controls))


def test_retained_domain_circular_rotation_decimal_mass_fixed_state_and_epoch() -> None:
    reference, study = json.loads(REFERENCE.read_text()), json.loads(STUDY.read_text())
    domain = target._bind_references(reference, study, tuple(study["launch_window_tdb_s"]))
    lower, upper = bezier._bounds(domain)
    assert len(lower) == len(upper) == 8
    assert lower[:2] == (domain.delta_bounds_s[0], domain.duration_bounds_s[0])
    assert upper[:2] == (domain.delta_bounds_s[1], domain.duration_bounds_s[1])
    assert lower[2:] == (-1.,)*6 and upper[2:] == (1.,)*6
    baseline = domain.command(domain.initial_controls)
    for delta_s, duration_s in ((-300., 3000.), (300., 5000.)):
        x = (delta_s, duration_s, .2, -.3, .9, -.8, .4, .5)
        command = bezier._command(domain, x)
        assert command == domain.command((delta_s, duration_s, .2, -.3, .4, .5))
        assert command.target_state_si[:6] == baseline.target_state_si[:6]
        assert command.ignition_epoch_tdb_s+command.match_after_ignition_s == domain.match_epoch_tdb_s
        assert domain.match_epoch_tdb_s == 979002340.6346419
        assert command.match_after_ignition_s-command.cutoff_after_ignition_s >= 1.
        with localcontext() as context:
            context.prec = 50
            exhaust = Decimal("9.80665")*Decimal("450")
            mass = Decimal(2000)-Decimal(1000)*Decimal(str(duration_s))/exhaust
            assert abs(command.target_state_si[6]-float(mass)) < 1e-10
        axis = np.cross(baseline.initial_state_si[:3], baseline.initial_state_si[3:6])
        axis /= np.linalg.norm(axis)
        radius_m = np.linalg.norm(baseline.initial_state_si[:3])
        actual_delta_s = command.ignition_epoch_tdb_s-baseline.ignition_epoch_tdb_s
        angle = math.sqrt(command.mu_m3_s2/radius_m**3)*actual_delta_s
        for original, actual in ((baseline.initial_state_si[:3], command.initial_state_si[:3]),
                                 (baseline.initial_state_si[3:6], command.initial_state_si[3:6])):
            vector = np.asarray(original)
            rotated = (vector*math.cos(angle)+np.cross(axis, vector)*math.sin(angle)
                       +axis*np.dot(axis, vector)*(1-math.cos(angle)))
            np.testing.assert_allclose(actual, rotated, atol=1e-8, rtol=0)
        assert command.initial_state_si[6] == 2000.


def test_curvature_changes_guidance_not_mass_epoch_initial_state_or_target() -> None:
    domain = synthetic()
    first = (0., 20., .3, -.8, -.9, .7, -.4, .6)
    second = first[:4]+(.8, -.9)+first[6:]
    assert bezier._command(domain, first) == bezier._command(domain, second)
    assert math.dist(bezier._bezier_direction(domain.basis, first, 10.),
                     bezier._bezier_direction(domain.basis, second, 10.)) > .5
    shifted = (1e-20,)+first[1:]
    original, tiny = bezier._command(domain, first), bezier._command(domain, shifted)
    assert tiny.ignition_epoch_tdb_s == original.ignition_epoch_tdb_s
    assert tiny.initial_state_si == original.initial_state_si
    assert tiny.ignition_epoch_tdb_s+tiny.match_after_ignition_s == domain.match_epoch_tdb_s


@pytest.mark.parametrize("tighter", [False, True])
def test_native_nonzero_curvature_independent_variable_mass_integral(tighter: bool) -> None:
    domain = synthetic(200.)
    x = (0., 200., .3, -.8, .9, .7, -.4, .6)
    command = replace(bezier._command(domain, x), mu_m3_s2=1e-12)
    budget, evidence = shared_budget(), {}
    result = bezier._evaluate_command(domain, x, command, tighter, budget, evidence)
    nodes, weights = np.polynomial.legendre.leggauss(256)
    times_s = (nodes+1)*100
    # Explicit two-stage affine interpolation in X/Y/Z; no production guidance.
    first = np.column_stack((.3+(.9-.3)*times_s/200, -.8+(.7+.8)*times_s/200))
    second = np.column_stack((.9+(-.4-.9)*times_s/200, .7+(.6-.7)*times_s/200))
    slopes = first+(times_s/200)[:, None]*(second-first)
    raw = np.column_stack((np.ones(256), slopes))
    direction = raw/np.linalg.norm(raw, axis=1)[:, None]
    mass_kg = 2000-1000*times_s/(9.80665*450)
    acceleration_m_s2 = 1000*direction/mass_kg[:, None]
    delta_v_m_s = np.sum(weights[:, None]*acceleration_m_s2, axis=0)*100
    delta_r_m = np.sum(weights[:, None]*(200-times_s[:, None])*acceleration_m_s2, axis=0)*100
    cutoff = result["cutoff_state_si"]
    np.testing.assert_allclose(cutoff[3:6], np.asarray(command.initial_state_si[3:6])+delta_v_m_s,
                               atol=1e-6, rtol=0)
    np.testing.assert_allclose(cutoff[:3], np.asarray(command.initial_state_si[:3])
                               +200*np.asarray(command.initial_state_si[3:6])+delta_r_m,
                               atol=.001, rtol=0)
    coast = result["final_state_si"]
    np.testing.assert_allclose(coast[:3], np.asarray(cutoff[:3])+800*np.asarray(cutoff[3:6]),
                               atol=.001, rtol=0)
    np.testing.assert_allclose(coast[3:6], cutoff[3:6], atol=1e-6, rtol=0)
    with localcontext() as context:
        context.prec = 50
        mass = Decimal(2000)-Decimal(200000)/(Decimal("9.80665")*Decimal(450))
        assert abs(cutoff[6]-float(mass)) <= 1e-6
    assert coast[6] == cutoff[6]
    assert evidence["cutoff_state_si"] == cutoff
    assert budget.native_arc_propagations == budget.completed_arcs == 2


@pytest.mark.parametrize("tighter", [False, True])
def test_native_zero_curvature_embeds_old_nonzero_linear_guidance(tighter: bool) -> None:
    domain = synthetic(200.)
    old = (0., 200., .3, -.8, -.4, .6)
    x = old[:4]+((old[2]+old[4])/2, (old[3]+old[5])/2)+old[4:]
    command = bezier._command(domain, x)
    actual = bezier._evaluate_command(domain, x, command, tighter, shared_budget(), {})
    previous = target._evaluate_command(domain, old, command, tighter, shared_budget(), {})
    for key in ("cutoff_state_si", "final_state_si"):
        np.testing.assert_allclose(actual[key][:3], previous[key][:3], atol=.001, rtol=0)
        np.testing.assert_allclose(actual[key][3:6], previous[key][3:6], atol=1e-6, rtol=0)
        assert abs(actual[key][6]-previous[key][6]) <= 1e-6


@pytest.mark.parametrize("failure", ["impact", "dry", "deadline"])
def test_actual_bezier_native_guard_counts_attempt_and_stops(
    monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    from tudatpy.dynamics import simulator

    domain, budget = synthetic(), shared_budget()
    x = (0., 20., .3, -.8, .9, .7, -.4, .6)
    command = bezier._command(domain, x)
    if failure == "impact":
        command = replace(command, initial_state_si=(100., 0., 0., -100., 0., 0., 2000.))
    elif failure == "dry":
        command = replace(command, initial_state_si=command.initial_state_si[:-1]+(500.001,))
    else:
        original = simulator.create_dynamics_simulator

        def expired(*args: Any) -> Any:
            budget.monotonic = lambda: 300.
            return original(*args)

        monkeypatch.setattr(simulator, "create_dynamics_simulator", expired)
    with pytest.raises(TrajectoryRefinementError):
        bezier._evaluate_command(domain, x, command, False, budget, {})
    assert budget.native_arc_propagations == 1 and budget.completed_arcs == 0


def test_native_coast_failure_preserves_completed_bezier_cutoff(monkeypatch: pytest.MonkeyPatch) -> None:
    domain, budget = synthetic(), shared_budget()
    x = (0., 20., .3, -.8, .9, .7, -.4, .6)
    command, evidence = bezier._command(domain, x), {}
    original = local._native_local_arc

    def fail_coast(command: local._LocalCommand, initial: local.State7, start: float, end: float,
                   burn: bool, tighter: bool, shared: target._TargetBudget,
                   **kwargs: Any) -> tuple[local.State7, int]:
        if not burn:
            shared.begin_arc(first_in_evaluation=False)
            raise TrajectoryRefinementError("D17 injected coast failure")
        return original(command, initial, start, end, burn, tighter, shared, **kwargs)

    monkeypatch.setattr(local, "_native_local_arc", fail_coast)
    with pytest.raises(TrajectoryRefinementError, match="coast failure"):
        bezier._evaluate_command(domain, x, command, False, budget, evidence)
    assert evidence["cutoff_state_si"][6] == pytest.approx(command.target_state_si[6], abs=1e-6)
    assert budget.native_arc_propagations == 2 and budget.completed_arcs == 1
    assert "final_state_si" not in evidence
    with pytest.raises(ValueError, match="retry|complete"):
        budget.begin_control()
