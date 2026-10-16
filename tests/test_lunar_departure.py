from __future__ import annotations

from dataclasses import asdict, replace
from decimal import Decimal, localcontext
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from space_nav import lunar_departure as departure
from space_nav.errors import TrajectoryRefinementError
from space_nav.scenario import load_scenario


SCENARIO = load_scenario(Path("examples/m3_feasible_mission.toml"))


def reference(**changes: Any) -> departure._DepartureReference:
    arguments = dict(orbit=replace(SCENARIO.departure_orbit, inclination_rad=0.),
        gravitational_parameter_m3_s2=1e12, parking_radius_m=1e6,
        excess_velocity_m_s=(1000., 0., 0.), epoch_tdb_s=1e9, phase_policy="free",
        spacecraft=SCENARIO.spacecraft, provisional_arrival_delta_v_m_s=1000., flight_time_s=1e6)
    arguments.update(changes)
    return departure._lunar_departure_reference(**arguments)


def test_known_two_branches_and_no_automatic_selection() -> None:
    result = reference()
    assert result.status == "constructed" and len(result.branches) == 2
    assert [b.phase_rad for b in result.branches] == pytest.approx([2*math.pi/3, 4*math.pi/3], abs=1e-12)
    assert [b.delta_v_norm_m_s for b in result.branches] == pytest.approx(
        [math.sqrt(3e6)+1000, math.sqrt(3e6)-1000], abs=1e-9)
    assert result.origin == "Moon" and result.orientation == "J2000" and result.units == "SI"
    assert result.virtual_periapsis_epoch_tdb_s == 1e9
    assert "impulsive" in result.interpretation
    assert reference() == result
    json.dumps(asdict(result), allow_nan=False)


@pytest.mark.parametrize("inc,node", [(0., 0.), (.6, .8), (math.pi/2, 0.), (2.1, -1.4)])
def test_rotated_geometry_independent_eccentricity_and_energy_oracle(inc: float, node: float) -> None:
    p = np.array([math.cos(node), math.sin(node), 0.])
    q = np.array([-math.sin(node)*math.cos(inc), math.cos(node)*math.cos(inc), math.sin(inc)])
    normal = np.cross(p, q)
    excess = 1000*(.8*p+.3*q+math.sqrt(.27)*normal)
    result = reference(orbit=replace(SCENARIO.departure_orbit, inclination_rad=inc, raan_rad=node),
                       excess_velocity_m_s=tuple(excess))
    assert result.status == "constructed"
    for branch in result.branches:
        r, v = np.array(branch.position_m), np.array(branch.hyperbolic_velocity_m_s)
        h = np.cross(r, v)
        evec = np.cross(v, h)/1e12-r/np.linalg.norm(r)
        e = np.linalg.norm(evec)
        ehat, hhat = evec/e, h/np.linalg.norm(h)
        qhat = np.cross(hhat, ehat)
        nu = math.acos(-1/e)
        asymptote = np.linalg.norm(excess)*(math.cos(nu)*ehat+math.sin(nu)*qhat)
        np.testing.assert_allclose(asymptote, excess, atol=1e-6, rtol=0)
        assert np.dot(r, v)/np.linalg.norm(r) == pytest.approx(0, abs=1e-6)
        assert np.dot(v, v)/2-1e12/np.linalg.norm(r) == pytest.approx(np.dot(excess, excess)/2, abs=1e-4)
        assert np.linalg.norm(r) == pytest.approx(1e6, abs=.001)
        assert np.dot(r, normal) == pytest.approx(0, abs=.001)
        np.testing.assert_allclose(branch.delta_v_m_s, v-np.array(branch.parking_velocity_m_s), atol=1e-9)
        assert branch.position_error_m <= .001 and branch.asymptote_error_m_s <= 1e-6


def test_fixed_phase_validates_without_mutating_orbit() -> None:
    original = replace(SCENARIO.departure_orbit, inclination_rad=0.)
    assert reference(orbit=original, phase_policy="fixed").status == "infeasible-fixed-phase"
    phase = reference().branches[0].phase_rad
    orbit = replace(original, true_anomaly_rad=phase-.2, argument_of_periapsis_rad=.2)
    result = reference(orbit=orbit, phase_policy="fixed")
    assert len(result.branches) == 1 and result.branches[0].phase_change_rad == 0
    assert orbit.true_anomaly_rad == phase-.2


@pytest.mark.parametrize("offset,status", [(-1e-9, "infeasible-plane"), (0., "near-degenerate-unresolved"),
                                          (5e-13, "near-degenerate-unresolved")])
def test_plane_infeasibility_and_degeneracy(offset: float, status: str) -> None:
    projection = .5+offset
    result = reference(excess_velocity_m_s=(1000*projection, 0., 1000*math.sqrt(1-projection**2)))
    assert result.status == status and result.branches == ()


def test_normal_asymptote_infeasible() -> None:
    result = reference(excess_velocity_m_s=(0., 0., 1000.))
    assert result.status == "infeasible-plane" and not result.branches


@pytest.mark.parametrize("arrival", [0., 1000., 3000.])
def test_mass_and_duration_against_decimal_oracle(arrival: float) -> None:
    result = reference(provisional_arrival_delta_v_m_s=arrival)
    for b in result.branches:
        with localcontext() as context:
            context.prec = 50
            exhaust = Decimal('9.80665')*Decimal(str(SCENARIO.spacecraft.isp_s))
            initial = Decimal(str(SCENARIO.spacecraft.initial_mass_kg))
            rate = Decimal(str(SCENARIO.spacecraft.max_thrust_n))/exhaust
            after = initial*(-Decimal(str(b.delta_v_norm_m_s))/exhaust).exp()
            final = after*(-Decimal(str(arrival))/exhaust).exp()
        assert b.post_departure_mass_kg == pytest.approx(float(after), abs=1e-9)
        assert b.provisional_final_mass_kg == pytest.approx(float(final), abs=1e-9)
        assert b.departure_duration_s == pytest.approx(float((initial-after)/rate), abs=1e-6)
        assert b.provisional_arrival_duration_s == pytest.approx(float((after-final)/rate), abs=1e-6)


def test_rejected_estimates_not_mission_success() -> None:
    result = reference(spacecraft=replace(SCENARIO.spacecraft, dry_mass_kg=1900.))
    assert all(b.estimate_status == "rejected-dry-mass" for b in result.branches)
    result = reference(flight_time_s=1.)
    assert all(b.estimate_status == "rejected-window" for b in result.branches)


@pytest.mark.parametrize("field", ["gravitational_parameter_m3_s2", "parking_radius_m", "flight_time_s"])
@pytest.mark.parametrize("bad", [True, 0., -1., math.nan, math.inf])
def test_invalid_positive_inputs_rejected(field: str, bad: object) -> None:
    with pytest.raises(TrajectoryRefinementError, match="D13 lunar-departure-geometry"):
        reference(**{field: bad})


@pytest.mark.parametrize("changes", [dict(phase_policy=None), dict(phase_policy="auto"),
    dict(epoch_tdb_s=True), dict(epoch_tdb_s=math.inf), dict(excess_velocity_m_s=(0., 0., 0.)),
    dict(excess_velocity_m_s=(True, 0., 0.)), dict(excess_velocity_m_s=(math.nan, 0., 0.)),
    dict(provisional_arrival_delta_v_m_s=-1.), dict(provisional_arrival_delta_v_m_s=True),
    dict(excess_velocity_m_s=(1e-100, 0., 0.)), dict(excess_velocity_m_s=(1e200, 0., 0.))])
def test_invalid_geometry_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(TrajectoryRefinementError):
        reference(**changes)


@pytest.mark.parametrize("changes", [dict(central_body="Mars"), dict(eccentricity=.1),
    dict(apoapsis_altitude_m=200000.), dict(raan_rad=math.nan)])
def test_unsupported_orbit_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(TrajectoryRefinementError):
        reference(orbit=replace(SCENARIO.departure_orbit, **changes))


@pytest.mark.parametrize("field", ["initial_mass_kg", "dry_mass_kg", "isp_s", "max_thrust_n"])
def test_nonfinite_spacecraft_rejected(field: str) -> None:
    with pytest.raises(TrajectoryRefinementError):
        reference(spacecraft=replace(SCENARIO.spacecraft, **{field: math.inf}))


def test_invariant_failure_is_not_silently_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    original = departure.physical._cross_product
    calls = []
    def corrupt(*args: Any) -> Any:
        calls.append(args)
        result = original(*args)
        return tuple(v*1.01 for v in result) if len(calls) == 1 else result
    monkeypatch.setattr(departure.physical, "_cross_product", corrupt)
    with pytest.raises(TrajectoryRefinementError, match="invariant"):
        reference()
