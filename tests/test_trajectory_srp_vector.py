"""Fully lit SRP intervals at ideal source positions, not a full-force bound."""

from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path

import numpy as np
import pytest

from space_nav import trajectory
from test_trajectory_gravity_assembly import _load_gravity_assembly
from test_trajectory_midpoint import _midpoint_acceleration_l2_bound_m_s2
from test_trajectory_spk import (
    _apparent_spheres_strictly_disjoint, _fully_lit_srp_anchor_error_bound_m_s2,
    _pi_rational_bounds, _point_gravity_intervals_m_s2,
)


def _fully_lit_srp_intervals_m_s2(
    budget: trajectory._RefinementBudget, solar_gravity: tuple[tuple[Fraction, Fraction], ...],
    gm_m3_s2: float, luminosity_w: float, area_m2: float, cr: float, mass_kg: float,
) -> tuple[tuple[Fraction, Fraction], ...]:
    """Scale a Sun gravity enclosure by -L*A*Cr/(4*pi*c*m*GM).

    Caller proves full illumination and binds the common source/state convention.
    """
    budget.check()
    assert all(type(value) is float and math.isfinite(value) and value > 0
               for value in (gm_m3_s2, luminosity_w, area_m2, cr, mass_kg))
    assert len(solar_gravity) == 3 and all(len(pair) == 2 and all(isinstance(value, Fraction) for value in pair)
                                          and pair[0] <= pair[1] for pair in solar_gravity)
    coefficient = Fraction(luminosity_w)*Fraction(area_m2)*Fraction(cr)/(4*299792458*Fraction(mass_kg)*Fraction(gm_m3_s2))
    factors = tuple(-coefficient/pi for pi in _pi_rational_bounds())
    result = []
    for pair in solar_gravity:
        values = [value*factor for value in pair for factor in factors]
        result.append((min(values), max(values)))
    budget.check()
    return tuple(result)


@pytest.mark.parametrize("relative", [(3.0, -4.0, 0.0), (-3.0, 4.0, -12.0), (1.0, -1.0, 0.0)])
@pytest.mark.parametrize("observed", [(0.0, 0.0, 0.0), (0.125, -0.25, 0.5)])
def test_srp_scaling_matches_independent_direct_geometry(relative: tuple, observed: tuple) -> None:
    luminosity = float(4*299792458*125)
    solar = _point_gravity_intervals_m_s2(125.0, tuple(-Fraction(value) for value in relative))
    actual = _fully_lit_srp_intervals_m_s2(trajectory._RefinementBudget("srp-geometry", 300.0), solar, 125.0, luminosity, 1.0, 1.0, 1.0)
    # Direct radius/pi formula does not use the solar-gravity scaling helper.
    direct = _fully_lit_srp_anchor_error_bound_m_s2(np.zeros(3), np.asarray(relative), luminosity, 1.0, 1.0, 1.0, np.asarray(observed))
    reduction = sum((max(abs(Fraction(value)-lo), abs(Fraction(value)-hi))
                     for value, (lo, hi) in zip(observed, actual, strict=True)), Fraction(0))
    assert reduction == direct
    for coordinate, (lo, hi) in zip(relative, actual, strict=True):
        assert (lo > 0 if coordinate > 0 else hi < 0 if coordinate < 0 else lo == hi == 0)


@pytest.mark.parametrize("parameter", range(5))
def test_srp_parameter_scaling(parameter: int) -> None:
    box = ((Fraction(-3), Fraction(-2)), (Fraction(-1), Fraction(1)), (Fraction(0), Fraction(0)))
    values = [1.0]*5
    baseline = _fully_lit_srp_intervals_m_s2(trajectory._RefinementBudget("srp-base", 300.0), box, *values)
    values[parameter] = 2.0
    changed = _fully_lit_srp_intervals_m_s2(trajectory._RefinementBudget("srp-scale", 300.0), box, *values)
    factor = Fraction(1, 2) if parameter in (0, 4) else Fraction(2)
    assert changed == tuple(tuple(factor*value for value in pair) for pair in baseline)


def test_srp_crossing_zero_and_gm_cancellation() -> None:
    box = ((Fraction(-2), Fraction(3)), (Fraction(0), Fraction(0)), (Fraction(1), Fraction(2)))
    args = (float(4*299792458), 1.0, 1.0, 1.0)
    actual = _fully_lit_srp_intervals_m_s2(trajectory._RefinementBudget("srp-signed", 300.0), box, 1.0, *args)
    pi_lower, pi_upper = _pi_rational_bounds()
    assert actual == ((-3/pi_lower, 2/pi_lower), (Fraction(0), Fraction(0)), (-2/pi_lower, -1/pi_upper))
    doubled = tuple(tuple(2*value for value in pair) for pair in box)
    assert _fully_lit_srp_intervals_m_s2(trajectory._RefinementBudget("srp-gm", 300.0), doubled, 2.0, *args) == actual


@pytest.mark.parametrize("parameter", range(5))
@pytest.mark.parametrize("invalid", [True, 0.0, -1.0, math.nan, math.inf])
def test_srp_scaling_rejects_invalid_parameters(parameter: int, invalid: float) -> None:
    values = [1.0]*5
    values[parameter] = invalid
    with pytest.raises(AssertionError):
        _fully_lit_srp_intervals_m_s2(trajectory._RefinementBudget("srp-invalid", 300.0), ((Fraction(0), Fraction(1)),)*3, *values)


@pytest.mark.parametrize("box", [(), ((Fraction(1), Fraction(0)),)*3, ((0.0, 1.0),)*3, ((Fraction(1),),)*3])
def test_srp_scaling_rejects_invalid_intervals(box: tuple) -> None:
    with pytest.raises(AssertionError):
        _fully_lit_srp_intervals_m_s2(trajectory._RefinementBudget("srp-box", 300.0), box, 1.0, 1.0, 1.0, 1.0, 1.0)


@pytest.mark.parametrize("expiry_check", [1, 2])
def test_srp_scaling_preserves_deadline(expiry_check: int) -> None:
    clock = iter([0.0]*expiry_check+[301.0])
    with pytest.raises(trajectory.TrajectoryRefinementError, match="shared deadline"):
        _fully_lit_srp_intervals_m_s2(trajectory._RefinementBudget("srp-expired", 300.0, lambda: next(clock)),
                                    ((Fraction(0), Fraction(1)),)*3, 1.0, 1.0, 1.0, 1.0, 1.0)


def test_retained_fresh_srp_vector() -> None:
    budget = trajectory._RefinementBudget("fresh-srp-vector", 300.0)
    data = Path(__file__).parent / "data"
    boxes, _ = _load_gravity_assembly(data, budget)
    documents = []
    for name, expected in (
        ("m3_fresh_light_inputs.json", "78228d371cf23325aaf7ad10559157513d95fa24f7d7a5703e5ed495cd12b7e4"),
        ("m3_fresh_point_source_errors.json", "3b27db7ecb608b2d92bc23829971e5a0d33ca13ba44bc810a07e0f54b693ab9e"),
    ):
        raw = (data / name).read_bytes()
        assert sha256(raw).hexdigest() == expected
        documents.append(json.loads(raw))
        budget.check()
    light, point_sources = documents[0]["fresh_light_inputs"], documents[1]["fresh_point_source_errors"]
    assert light["model_id"] == trajectory.PHYSICAL_MODEL_IDENTIFIER
    assert light["epoch_tdb_s"] == point_sources["epoch_tdb_s"] == 978995455.2929223
    assert light["origin"] == point_sources["origin"] == "SSB"
    assert light["orientation"] == point_sources["orientation"] == "J2000"
    replay = json.loads((data / "m3_fresh_harmonic_replay.json").read_text())  # Hash checked by assembly loader.
    assert light["spacecraft_state_m_m_s"] == replay["spacecraft_position_m"]+replay["spacecraft_velocity_m_s"]
    assert light["pck_sha256"] == replay["pck_sha256"]
    resource = light["srp_resource"]
    assert resource["luminosity_w"] == trajectory.SUN_LUMINOSITY_W
    assert resource["initial_mass_kg"] == light["spacecraft_mass_kg"] == replay["spacecraft_mass_kg"]
    assert set(light["full_light_by_occultor"]) == set(resource["occulting_bodies"]) == {"Moon", "Earth", "Mars"}
    for body in resource["occulting_bodies"]:
        assert light["full_light_by_occultor"][body] is True
        assert _apparent_spheres_strictly_disjoint(
            np.asarray(light["source_positions_m"]["Sun"]), light["optical_radii_m"]["Sun"],
            np.asarray(light["source_positions_m"][body]), light["optical_radii_m"][body], np.asarray(replay["spacecraft_position_m"]),
            source_position_error_m=light["source_position_allowances_m"]["Sun"],
            occultor_position_error_m=light["source_position_allowances_m"][body],
        )
    intervals = _fully_lit_srp_intervals_m_s2(budget, boxes["Sun"], point_sources["sources"]["Sun"]["gm_m3_s2"],
                                             resource["luminosity_w"], resource["reference_area_m2"], resource["reflectivity_coefficient"], light["spacecraft_mass_kg"])
    midpoint, error = _midpoint_acceleration_l2_bound_m_s2(intervals, Fraction(0))
    outward = [[math.nextafter(float(lo), -math.inf) if lo else 0.0, math.nextafter(float(hi), math.inf) if hi else 0.0] for lo, hi in intervals]
    assert all(math.isfinite(a) and math.isfinite(b) and Fraction(a) <= lo <= hi <= Fraction(b)
               for (a, b), (lo, hi) in zip(outward, intervals, strict=True))
    reported_error = math.nextafter(float(error), math.inf)
    assert math.isfinite(reported_error) and Fraction(reported_error) >= error > 0
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    budget.check()
    print(json.dumps({"fresh_srp_vector": {
        "epoch_tdb_s": light["epoch_tdb_s"], "origin": "SSB", "orientation": "J2000",
        "component_intervals_m_s2": outward, "midpoint_m_s2": midpoint, "acceleration_l2_allowance_m_s2": reported_error,
        "source_convention": "exact position polynomials", "full_light_by_occultor": light["full_light_by_occultor"],
        "scope": "Fully lit SRP at fixed nominal state and parameters; no native arithmetic, state/time domain or full-force certificate",
        "additional_native_queries": 0, "additional_native_arcs": 0,
    }}, sort_keys=True, allow_nan=False))
