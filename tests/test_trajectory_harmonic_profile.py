"""Bounded isolated arithmetic profiling, never a mission-runtime certificate."""

from cProfile import Profile
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path
from statistics import median
from time import perf_counter

import numpy as np
import pytest

from space_nav import trajectory
from test_trajectory_midpoint import _midpoint_acceleration_l2_bound_m_s2
from test_trajectory_spk import _harmonic_prefix_vector_enclosure_m_s2


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("cutoff", [20, 40, 100])
def test_stored_mars_harmonic_profile(cutoff: int) -> None:
    """Replay pinned SI/J2000 inputs without ephemeris queries or propagation."""
    started_s = perf_counter()
    budget = trajectory._RefinementBudget(f"isolated-mars-degree{cutoff}-profile", 300.0)
    deadline_s = budget.deadline_monotonic_s
    snapshot_bytes = (ROOT / "tests/data/m3_fresh_harmonic_replay.json").read_bytes()
    snapshot = json.loads(snapshot_bytes)
    assert (snapshot["origin"], snapshot["orientation"], snapshot["time_scale"]) == (
        "SSB", "J2000", "TDB seconds since J2000",
    )
    assert snapshot["model_id"] == trajectory.PHYSICAL_MODEL_IDENTIFIER
    assert snapshot["environment_yml_sha256"] == sha256((ROOT / "environment.yml").read_bytes()).hexdigest()
    recorded = snapshot["fields"]["Mars"]
    spec = next(item for item in trajectory._HARMONIC_FIELD_SPECS if item.body == "Mars")
    path = trajectory._default_gravity_models_path() / spec.body / spec.file_name
    assert trajectory._coefficient_sha256(path) == spec.expected_sha256 == recorded["resource"]["actual_sha256"]
    budget.check()
    field = trajectory._load_harmonic_field_settings(trajectory._import_tudat_environment_setup(), spec, path)
    budget.check()
    cosine, sine = field.normalized_cosine_coefficients, field.normalized_sine_coefficients
    assert recorded["coefficient_encoding"] == "IEEE-754 binary64 little-endian, C order"
    assert list(cosine.shape) == list(sine.shape) == recorded["coefficient_shape"] == [121, 121]
    for matrix, key in ((cosine, "cosine_sha256"), (sine, "sine_sha256")):
        assert matrix.dtype == np.float64 and np.all(np.isfinite(matrix))
        assert sha256(matrix.astype("<f8").tobytes()).hexdigest() == recorded[key]
    assert field.gravitational_parameter == spec.gravitational_parameter_m3_s2 == recorded["resource"]["gravitational_parameter_m3_s2"]
    assert field.reference_radius == spec.normalization_radius_m == recorded["resource"]["normalization_radius_m"]
    args = (budget, field.gravitational_parameter, field.reference_radius, cosine, sine,
            np.asarray(recorded["body_position_m"]), np.asarray(snapshot["spacecraft_position_m"]),
            np.asarray(recorded["inertial_to_fixed"]), cutoff)
    setup_elapsed_s = perf_counter()-started_s
    if cutoff == 100:
        run_started_s = perf_counter()
        intervals, tail = _harmonic_prefix_vector_enclosure_m_s2(*args)
        elapsed_s = perf_counter()-run_started_s
        budget.check()
        baseline = json.loads((ROOT / "tests/data/m3_mars_degree40_profile.json").read_text())
        assert baseline["snapshot_sha256"] == sha256(snapshot_bytes).hexdigest()
        assert baseline["prefix_degree"] == 40
        assert math.nextafter(float(tail), math.inf) == 7.827778792894826e-6
        assert 0 < tail < Fraction(baseline["tail_upper_m_s2"])
        outward = [[math.nextafter(float(lo), -math.inf), math.nextafter(float(hi), math.inf)]
                    for lo, hi in intervals]
        assert all(Fraction(a) < lo <= hi < Fraction(b) for (a, b), (lo, hi) in
                   zip(baseline["component_intervals_m_s2"], intervals, strict=True))
        assert all(a < lo <= hi < b for (a, b), (lo, hi) in
                   zip(baseline["component_intervals_m_s2"], outward, strict=True))
        assert all(math.isfinite(a) and math.isfinite(b) and Fraction(a) <= lo <= hi <= Fraction(b)
                   for (a, b), (lo, hi) in zip(outward, intervals, strict=True))
        # Undo only the helper's EXACT Fraction tail expansion, never JSON rounding.
        prefix = tuple((lo + tail, hi - tail) for lo, hi in intervals)
        assert all(lo <= hi for lo, hi in prefix)
        assert tuple((lo - tail, hi + tail) for lo, hi in prefix) == intervals
        midpoint, separate_bound = _midpoint_acceleration_l2_bound_m_s2(prefix, tail)
        prefix_midpoint, prefix_bound = _midpoint_acceleration_l2_bound_m_s2(prefix, Fraction(0))
        box_midpoint, box_bound = _midpoint_acceleration_l2_bound_m_s2(intervals, Fraction(0))
        assert midpoint == prefix_midpoint == box_midpoint
        assert separate_bound == prefix_bound + tail
        assert tail <= separate_bound < box_bound
        directions = ((Fraction(0),) * 3, (Fraction(1), Fraction(0), Fraction(0)),
                      (Fraction(3, 5), Fraction(4, 5), Fraction(0)),
                      (Fraction(-3, 5), Fraction(-4, 5), Fraction(0)))
        for corner, direction in product(product(*prefix), directions):
            assert sum(value**2 for value in direction) <= 1
            error_squared = sum((value + tail * unit - Fraction(mid))**2 for value, unit, mid
                                in zip(corner, direction, midpoint, strict=True))
            assert error_squared <= separate_bound**2
        reported_bounds = [math.nextafter(float(value), math.inf)
                           for value in (prefix_bound, separate_bound, box_bound)]
        assert all(math.isfinite(reported) and Fraction(reported) >= exact for reported, exact
                   in zip(reported_bounds, (prefix_bound, separate_bound, box_bound), strict=True))
        assert budget.deadline_monotonic_s == deadline_s
        assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
        assert math.isfinite(elapsed_s) and elapsed_s >= 0
        print(json.dumps({"isolated_mars_degree100_evaluation": {
            "snapshot_sha256": sha256(snapshot_bytes).hexdigest(), "prefix_degree": 100,
            "setup_elapsed_s": setup_elapsed_s, "unprofiled_elapsed_s": elapsed_s,
            "evaluations": 1, "component_intervals_m_s2": outward,
            "tail_upper_m_s2": math.nextafter(float(tail), math.inf),
            "midpoint_m_s2": midpoint,
            "prefix_midpoint_l2_error_upper_m_s2": reported_bounds[0],
            "separate_tail_l2_error_upper_m_s2": reported_bounds[1],
            "whole_box_l2_error_upper_m_s2": reported_bounds[2],
            "origin": snapshot["origin"], "orientation": snapshot["orientation"],
            "epoch_tdb_s": snapshot["epoch_tdb_s"], "time_scale": snapshot["time_scale"],
            "profiling_deadline_s": 300.0, "native_coefficient_loads": 1, "native_arcs": 0,
            "qualification": "One isolated stored-input evaluation; no profiler/repeats, no shared mission-budget or source/PCK qualification",
        }}, sort_keys=True, allow_nan=False))
        budget.check()
        timings_s = [elapsed_s]
    else:
        timings_s: list[float] = []
        results: list[tuple[tuple[tuple[Fraction, Fraction], ...], Fraction]] = []
        for _ in range(3):
            run_started_s = perf_counter()
            result = _harmonic_prefix_vector_enclosure_m_s2(*args)
            budget.check()
            timings_s.append(perf_counter()-run_started_s)
            results.append(result)
        profiler = Profile()
        run_started_s = perf_counter()
        with profiler:
            profiled_result = _harmonic_prefix_vector_enclosure_m_s2(*args)
        profiled_elapsed_s = perf_counter()-run_started_s
        assert all(profiled_result == earlier for earlier in results)
        intervals, tail = result
        outward = [[math.nextafter(float(lo), -math.inf), math.nextafter(float(hi), math.inf)]
                    for lo, hi in intervals]
        # Recorded native-probe degree20 enclosure at the exact stored handoff.
        degree20_box = [[-3.1644671545870344, -3.1352173491822377],
                        [-0.011340394758140842, 0.01790941064665531],
                        [-0.019929288341151874, 0.00932051706364428]]
        if cutoff == 20:
            assert outward == degree20_box
            assert math.nextafter(float(tail), math.inf) == 0.014624902702398076
        else:
            assert cutoff == 40
            # Outward tail recorded in the existing native cutoff ledger.
            assert math.nextafter(float(tail), math.inf) == 0.0020034676779043326
            assert 0 < tail < Fraction(0.014624902702398076)
            assert all(Fraction(a) < lo <= hi < Fraction(b) for (a, b), (lo, hi) in
                       zip(degree20_box, intervals, strict=True))
            assert all(a < lo <= hi < b for (a, b), (lo, hi) in zip(degree20_box, outward, strict=True))
        rows: list[dict[str, object]] = []
        selected = {"_harmonic_prefix_vector_enclosure_m_s2", "_generic_harmonic_term_intervals_m_s2",
                    "_regular_solid_harmonic_jets", "_stored_harmonic_tail_bound_m_s2", "<built-in method math.gcd>"}
        for entry in profiler.getstats():
            name = entry.code if isinstance(entry.code, str) else entry.code.co_name
            if name in selected:
                rows.append({"function": name, "calls": entry.callcount,
                             "self_s": entry.inlinetime, "inclusive_s": entry.totaltime})
        assert {row["function"] for row in rows} == selected
        budget.check()
        assert budget.deadline_monotonic_s == deadline_s
        assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
        assert all(math.isfinite(value) and value >= 0 for value in (*timings_s, setup_elapsed_s, profiled_elapsed_s))
        print(json.dumps({f"isolated_mars_degree{cutoff}_profile": {
            "snapshot_sha256": sha256(snapshot_bytes).hexdigest(), "prefix_degree": cutoff,
            "setup_elapsed_s": setup_elapsed_s, "unprofiled_elapsed_s": timings_s,
            "profiled_elapsed_s": profiled_elapsed_s,
            "profiled_minus_unprofiled_median_s": profiled_elapsed_s-median(timings_s),
            "profile_rows": sorted(rows, key=lambda row: str(row["function"])),
            "component_intervals_m_s2": outward, "tail_upper_m_s2": math.nextafter(float(tail), math.inf),
            "profiling_deadline_s": 300.0, "native_coefficient_loads": 1, "native_arcs": 0,
            "qualification": "Isolated stored-input timing only; inclusive rows overlap, overhead difference is noisy, no mission deadline or force qualification",
        }}, sort_keys=True, allow_nan=False))
    if cutoff in (20, 40, 100):
        repeats = 1 if cutoff == 100 else 3
        # Reuse this historical handoff and coefficient load, NOT the fourth
        # endpoint. Keep omitted degrees and all repeated work in the budget.
        exact_prefix = tuple((lo+tail, hi-tail) for lo, hi in intervals)
        comparisons = []
        for bits in (53, 80, 120):
            bounded_timings_s = []
            previous_result = None
            for _ in range(repeats):
                run_started_s = perf_counter()
                bounded_intervals, bounded_tail = _harmonic_prefix_vector_enclosure_m_s2(*args, bits=bits)
                bounded_timings_s.append(perf_counter()-run_started_s)
                budget.check()
                assert bounded_tail == tail
                if previous_result is not None:
                    assert (bounded_intervals, bounded_tail) == previous_result
                previous_result = bounded_intervals, bounded_tail
                # Remove EXACT helper expansion; never subtract JSON tail bounds.
                bounded_prefix = tuple((lo+tail, hi-tail) for lo, hi in bounded_intervals)
                assert all(lo <= elo <= ehi <= hi for (lo, hi), (elo, ehi)
                           in zip(bounded_prefix, exact_prefix, strict=True))
                assert all(lo <= elo <= ehi <= hi for (lo, hi), (elo, ehi)
                           in zip(bounded_intervals, intervals, strict=True))
            midpoint, prefix_error = _midpoint_acceleration_l2_bound_m_s2(bounded_prefix, Fraction(0))
            full_midpoint, separate_error = _midpoint_acceleration_l2_bound_m_s2(bounded_prefix, tail)
            assert midpoint == full_midpoint and separate_error == prefix_error+tail
            widths = [math.nextafter(float(hi-lo), math.inf) for lo, hi in bounded_prefix]
            comparisons.append({"bits": bits, "evaluations": repeats, "unprofiled_elapsed_s": bounded_timings_s,
                                "median_elapsed_s": median(bounded_timings_s),
                                "bounded_to_exact_elapsed_ratio": median(bounded_timings_s)/median(timings_s),
                                "midpoint_m_s2": midpoint, "prefix_component_width_upper_m_s2": widths,
                                "prefix_midpoint_l2_error_upper_m_s2": math.nextafter(float(prefix_error), math.inf),
                                "tail_upper_m_s2": math.nextafter(float(tail), math.inf),
                                "separate_tail_l2_error_upper_m_s2": math.nextafter(float(separate_error), math.inf)})
        budget.check()
        assert budget.deadline_monotonic_s == deadline_s
        assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
        print(json.dumps({f"stored_mars_degree{cutoff}_bounded_comparison": {
            "snapshot_sha256": sha256(snapshot_bytes).hexdigest(), "prefix_degree": cutoff, "full_model_degree": 120,
            "epoch_tdb_s": snapshot["epoch_tdb_s"], "origin": snapshot["origin"], "orientation": snapshot["orientation"],
            "time_scale": snapshot["time_scale"], "model_id": snapshot["model_id"],
            "coefficient_sha256": recorded["resource"]["actual_sha256"],
            "cosine_sha256": recorded["cosine_sha256"], "sine_sha256": recorded["sine_sha256"],
            "exact_unprofiled_elapsed_s": timings_s, "exact_median_elapsed_s": median(timings_s),
            "exact_evaluations": 1 if cutoff == 100 else 4,
            "exact_profiled_evaluations": 0 if cutoff == 100 else 1, "bounded_evaluations": 3*repeats,
            "native_coefficient_loads": 1, "native_arcs": 0, "shared_deadline_s": 300.0,
            "shared_elapsed_s": perf_counter()-started_s, "cases": comparisons,
            "qualification": "Historical stored geometry, not fourth endpoint; arithmetic and finite tail only, source/PCK/native inputs and mission runtime unqualified"
                             + ("; one observation per method, not repeated benchmark medians" if cutoff == 100 else ""),
        }}, sort_keys=True, allow_nan=False))
        budget.check()
