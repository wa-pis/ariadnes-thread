"""Stored nominal gravity sum, not a full-force or interval certificate."""

from fractions import Fraction
from hashlib import sha256
from itertools import permutations
import json
import math
from pathlib import Path
from time import perf_counter

import pytest

from space_nav import trajectory
from test_trajectory_midpoint import _midpoint_acceleration_l2_bound_m_s2


ROOT = Path(__file__).resolve().parents[1]


def _sum_acceleration_balls(terms: tuple[tuple[tuple[float, ...], Fraction], ...]) -> tuple[tuple[float, ...], Fraction]:
    """Sum binary64 centres exactly; round once and retain all L2 radii."""
    assert terms
    assert all(len(vector) == 3 and all(type(x) is float and math.isfinite(x) for x in vector)
               and isinstance(radius, Fraction) and radius >= 0 for vector, radius in terms)
    centre = tuple(sum((Fraction(vector[axis]) for vector, _ in terms), Fraction(0)) for axis in range(3))
    return _midpoint_acceleration_l2_bound_m_s2(tuple((x, x) for x in centre), sum((r for _, r in terms), Fraction(0)))


@pytest.mark.parametrize("values", [(2.0**60, 1.0, -2.0**60), (2.0**60, 1.0), (0.0, 0.0)])
def test_acceleration_ball_sum_rounds_once(values: tuple[float, ...]) -> None:
    terms = tuple(((value, 0.0, 0.0), Fraction(1, 10)) for value in values)
    midpoint, radius = _sum_acceleration_balls(terms)
    exact = sum(map(Fraction, values))
    input_radius = Fraction(len(values), 10)
    assert midpoint == (float(exact), 0.0, 0.0)
    assert radius == input_radius+abs(Fraction(midpoint[0])-exact)
    for ordering in permutations(terms):
        assert _sum_acceleration_balls(ordering) == (midpoint, radius)
    for direction in ((Fraction(1), Fraction(0), Fraction(0)),
                      (Fraction(-1), Fraction(0), Fraction(0)),
                      (Fraction(3, 5), Fraction(4, 5), Fraction(0))):
        truth = (exact+input_radius*direction[0], input_radius*direction[1], input_radius*direction[2])
        assert sum((value-Fraction(mid))**2 for value, mid in zip(truth, midpoint, strict=True)) <= radius**2
    if len(values) == 3:
        assert (values[0]+values[1])+values[2] == 0.0 and midpoint[0] == 1.0  # Sequential addition loses the unit.


@pytest.mark.parametrize("terms", [(), (((0.0, 0.0), Fraction(0)),),
    (((math.nan, 0.0, 0.0), Fraction(0)),), (((0.0, 0.0, 0.0), Fraction(-1)),),
    (((0.0, 0.0, 0.0), 0.0),)])
def test_acceleration_ball_sum_rejects_invalid_inputs(terms: tuple) -> None:
    with pytest.raises(AssertionError):
        _sum_acceleration_balls(terms)


def test_fourth_endpoint_gravity_sum() -> None:
    started_s = perf_counter()
    budget = trajectory._RefinementBudget("fourth-gravity-sum", 300.0)
    names = ("fresh_endpoint_binding", "fourth_endpoint_point_gravity", "fourth_endpoint_point_source_bridge",
             "fourth_mars_bounded_force", "fourth_moon_bounded_force")
    raw = {name: (ROOT / f"tests/data/m3_{name}.json").read_bytes() for name in names}
    data = {name: json.loads(value) for name, value in raw.items()}
    binding = data["fresh_endpoint_binding"]["fresh_endpoint_binding"]
    points = data["fourth_endpoint_point_gravity"]["fourth_endpoint_point_gravity"]
    sources = data["fourth_endpoint_point_source_bridge"]["fourth_endpoint_point_source_bridge"]
    harmonics = {"Mars": data["fourth_mars_bounded_force"],
                 "Moon": data["fourth_moon_bounded_force"]["fourth_moon_bounded_force"]}
    for record in (points, sources, *harmonics.values()):
        assert record["epoch_tdb_s"] == binding["end_epoch_tdb_s"] == 978995455.3554223
        assert record["nominal_state_m_m_s_kg"] == binding["terminal_state_m_m_s_kg"]
        assert record["source_spk_context_sha256"] == binding["source_spk_context_sha256"]
        assert record["model_id"] == binding["model_id"] == trajectory.PHYSICAL_MODEL_IDENTIFIER
        assert (record["origin"], record["orientation"], record["time_scale"]) == ("SSB", "J2000", "TDB seconds since J2000")
    for record in (points, *harmonics.values()):
        assert record["carried_error_m_m_s"] == binding["outgoing_error_m_m_s"]
    input_names = {"fresh_endpoint_binding", "fourth_endpoint_source_anchor", "fourth_endpoint_rotation_bridge",
                   "fourth_endpoint_harmonic_source_bridge", "fourth_endpoint_rotation_force_bridge"}
    for record in harmonics.values():
        assert set(record["input_sha256"]) == input_names
        for name in input_names:
            assert sha256((ROOT / f"tests/data/m3_{name}.json").read_bytes()).hexdigest() == record["input_sha256"][name]
    point_names = set(trajectory.PHYSICAL_BODY_NAMES)-set(harmonics)
    assert len(point_names) == 6 and set(harmonics) == {"Moon", "Mars"}
    assert set(points["body_intervals_m_s2"]) == set(sources["fields"]) == point_names
    assert set(points["gravitational_parameters_m3_s2"]) == point_names
    terms = {}
    point_source_total = Fraction(0)
    for body in point_names:
        record = sources["fields"][body]
        assert record["gm_m3_s2"] == points["gravitational_parameters_m3_s2"][body] > 0
        box = tuple(tuple(map(Fraction, pair)) for pair in points["body_intervals_m_s2"][body])
        source_error = Fraction(record["acceleration_l2_allowance_m_s2"])
        assert source_error >= 0
        point_source_total += source_error
        terms[body] = _midpoint_acceleration_l2_bound_m_s2(box, source_error)
    for body, record in harmonics.items():
        terms[body] = (tuple(record["midpoint_m_s2"]), Fraction(record["ideal_finite_field_l2_error_upper_m_s2"]))
    assert set(terms) == set(trajectory.PHYSICAL_BODY_NAMES) and len(terms) == 8
    ordered = tuple(terms[body] for body in trajectory.PHYSICAL_BODY_NAMES)
    midpoint, error = _sum_acceleration_balls(ordered)
    assert _sum_acceleration_balls(tuple(reversed(ordered))) == (midpoint, error)
    input_error = sum((radius for _, radius in ordered), Fraction(0))
    rounding_error = error-input_error
    assert rounding_error >= 0
    values = (input_error, rounding_error, point_source_total, error)
    reported = [math.nextafter(float(value), math.inf) if value else 0.0 for value in values]
    assert all(math.isfinite(value) and Fraction(value) >= exact for value, exact in zip(reported, values, strict=True))
    budget.check()
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({"fourth_endpoint_gravity_sum": {
        "epoch_tdb_s": points["epoch_tdb_s"], "origin": points["origin"], "orientation": points["orientation"],
        "time_scale": points["time_scale"], "model_id": points["model_id"],
        "source_spk_context_sha256": binding["source_spk_context_sha256"],
        "force_context_sha256": binding["force_context_sha256"],
        "input_sha256": {name: sha256(value).hexdigest() for name, value in raw.items()},
        "nominal_state_m_m_s_kg": points["nominal_state_m_m_s_kg"], "carried_error_m_m_s": binding["outgoing_error_m_m_s"],
        "point_bodies": sorted(point_names), "harmonic_bodies": sorted(harmonics), "source_count": len(terms),
        "body_midpoints_m_s2": {body: value[0] for body, value in terms.items()},
        "body_l2_error_upper_m_s2": {body: math.nextafter(float(value[1]), math.inf) for body, value in terms.items()},
        "midpoint_m_s2": midpoint, "input_l2_error_upper_m_s2": reported[0],
        "summation_rounding_l2_error_upper_m_s2": reported[1], "retained_point_source_allowance_m_s2": reported[2],
        "ideal_gravity_l2_error_upper_m_s2": reported[3],
        "shared_elapsed_s": perf_counter()-started_s, "shared_deadline_s": 300.0,
        "force_evaluations": 0, "additional_native_queries": 0, "additional_native_arcs": 0,
        "qualification": "Stored eight-source ideal nominal gravity sum only; point-source margins retained conservatively, harmonic tails/input allowances already included once. No native-force arithmetic, SRP, relativity, carried-state, interval or mission-runtime qualification; not a selected reference",
    }}, sort_keys=True, allow_nan=False))
    budget.check()
