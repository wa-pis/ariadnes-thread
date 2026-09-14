"""Signed Schwarzschild controls and fixed-nominal source bridge, not mission accuracy."""

from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path

import numpy as np
import pytest

from space_nav import trajectory
from test_trajectory_midpoint import _midpoint_acceleration_l2_bound_m_s2
from test_trajectory_spk import _schwarzschild_intervals_m_s2, _schwarzschild_state_variation_bound_m_s2


@pytest.mark.parametrize("offset", [0.0, 1e12])
@pytest.mark.parametrize("velocity,expected", [
    ((0.0, 0.0, 0.0), (300, 400, 0)),
    ((3.0, 4.0, 0.0), (525, 700, 0)),
    ((-4.0, 3.0, 0.0), (225, 300, 0)),
    ((1.0, -2.0, 3.0), (238, 384, -60)),
])
def test_signed_schwarzschild_exact_components(offset: float, velocity: tuple, expected: tuple) -> None:
    sun = np.full(6, offset)
    intervals = _schwarzschild_intervals_m_s2(125.0, sun, sun+np.asarray([3.0, 4.0, 0.0, *velocity]))
    assert intervals == tuple((Fraction(value, 299792458**2),)*2 for value in expected)


@pytest.mark.parametrize("axis", range(6))
@pytest.mark.parametrize("shift", [-0.125, 0.125])
def test_signed_schwarzschild_source_bridge(axis: int, shift: float) -> None:
    budget = trajectory._RefinementBudget("schwarzschild-source-control", 300.0)
    ship = np.asarray([3.0, 4.0, 0.0, 1.0, -2.0, 3.0])
    sun, changed = np.zeros(6), np.zeros(6)
    changed[axis] = shift
    epsilon_p = abs(shift) if axis < 3 else 0.0
    epsilon_v = Fraction(abs(shift)) if axis >= 3 else Fraction(0)
    floor = trajectory._relative_distance_lower_bound(budget, tuple(ship[:3]), tuple(sun[:3]), 0.0, epsilon_p)
    speed = sum(map(abs, map(Fraction, ship[3:])), epsilon_v)
    bound = _schwarzschild_state_variation_bound_m_s2(125.0, floor, speed, Fraction(epsilon_p), epsilon_v)
    original = _schwarzschild_intervals_m_s2(125.0, sun, ship)
    perturbed = _schwarzschild_intervals_m_s2(125.0, changed, ship)
    # Retain both irrational-radius interval widths in the vector comparison.
    assert sum((max(abs(a-d), abs(b-c))**2 for (a, b), (c, d) in zip(original, perturbed, strict=True)), Fraction(0)) <= bound**2


@pytest.mark.parametrize("invalid", [True, 0.0, -1.0, math.nan, math.inf])
def test_signed_schwarzschild_rejects_invalid_gm(invalid: float) -> None:
    with pytest.raises(AssertionError):
        _schwarzschild_intervals_m_s2(invalid, np.zeros(6), np.ones(6))


def test_retained_fresh_schwarzschild_vector() -> None:
    budget = trajectory._RefinementBudget("fresh-schwarzschild-vector", 300.0)
    data = Path(__file__).parent / "data"
    documents = []
    for name, expected in (
        ("m3_fresh_light_inputs.json", "78228d371cf23325aaf7ad10559157513d95fa24f7d7a5703e5ed495cd12b7e4"),
        ("m3_fresh_point_source_errors.json", "3b27db7ecb608b2d92bc23829971e5a0d33ca13ba44bc810a07e0f54b693ab9e"),
        ("m3_fresh_sun_velocity_binding.json", "e56c7ac5c31edc16b11bac74df4d76428cf1e3b71f74d780592b39a4c3f53836"),
    ):
        raw = (data / name).read_bytes()
        assert sha256(raw).hexdigest() == expected
        documents.append(json.loads(raw))
        budget.check()
    light = documents[0]["fresh_light_inputs"]
    points = documents[1]["fresh_point_source_errors"]
    velocity, record = documents[2]["fresh_sun_velocity_binding"], documents[2]["fresh_sun_velocity_record"]
    assert light["epoch_tdb_s"] == points["epoch_tdb_s"] == velocity["epoch_tdb_s"] == record["epoch_tdb_s"] == 978995455.2929223
    assert light["origin"] == points["origin"] == velocity["origin"] == "SSB"
    assert light["orientation"] == points["orientation"] == velocity["orientation"] == "J2000"
    assert light["model_id"] == velocity["model"] == trajectory.PHYSICAL_MODEL_IDENTIFIER
    assert (record["target"], record["center"], record["frame"], record["spk_type"]) == (10, 0, 1, 2)
    assert record["velocity_convention"] == velocity["velocity_convention"] == "exact derivative of type-2 position polynomials"
    assert velocity["exact_cached_readback_match"] is True
    assert record["conditional_l1_allowance_m_s"] == velocity["conditional_l1_allowance_m_s"]
    assert light["sun_state_m_m_s"] == velocity["sun_state_m_m_s"]
    sun, ship = np.asarray(light["sun_state_m_m_s"]), np.asarray(light["spacecraft_state_m_m_s"])
    gm = points["sources"]["Sun"]["gm_m3_s2"]
    epsilon_p = light["source_position_allowances_m"]["Sun"]
    epsilon_v = Fraction(velocity["conditional_l1_allowance_m_s"])
    floor = trajectory._relative_distance_lower_bound(budget, tuple(ship[:3]), tuple(sun[:3]), 0.0, epsilon_p)
    relative = tuple(Fraction(a)-Fraction(b) for a, b in zip(ship, sun, strict=True))
    # Every point of the source-state chord has |r|>=floor and |v|<=speed.
    assert floor > 0 and (Fraction(floor)+Fraction(epsilon_p))**2 <= sum((r*r for r in relative[:3]), Fraction(0))
    speed = sum(map(abs, relative[3:]), epsilon_v)
    source_error = _schwarzschild_state_variation_bound_m_s2(gm, floor, speed, Fraction(epsilon_p), epsilon_v)
    intervals = _schwarzschild_intervals_m_s2(gm, sun, ship)
    midpoint, midpoint_error = _midpoint_acceleration_l2_bound_m_s2(intervals, Fraction(0))
    total = midpoint_error+source_error  # Each channel once; L1 source balls also bound L2.
    reported = [math.nextafter(float(value), math.inf) for value in (midpoint_error, source_error, total)]
    assert all(math.isfinite(out) and Fraction(out) >= exact > 0
               for out, exact in zip(reported, (midpoint_error, source_error, total), strict=True))
    budget.check()
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({"fresh_schwarzschild_vector": {
        "epoch_tdb_s": light["epoch_tdb_s"], "origin": "SSB", "orientation": "J2000",
        "midpoint_m_s2": midpoint, "midpoint_l2_allowance_m_s2": reported[0],
        "source_state_l2_allowance_m_s2": reported[1], "acceleration_l2_allowance_m_s2": reported[2],
        "source_position_allowance_m": epsilon_p, "source_velocity_allowance_m_s": float(epsilon_v),
        "source_chord_distance_floor_m": floor,
        "source_chord_speed_upper_m_s": math.nextafter(float(speed), math.inf),
        "source_convention": "exact Sun type-2 position polynomials and their derivatives",
        "additional_native_queries": 0, "additional_native_arcs": 0,
        "scope": "PPN=1 Sun Schwarzschild at fixed nominal spacecraft state; no native arithmetic, state/time domain or full-force certificate",
    }}, sort_keys=True, allow_nan=False))
