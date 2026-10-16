"""Read-only D15.3 evidence audit; never imports or runs the trajectory solver.

Run with the pinned Conda Python, without -O. Native histories are not retained;
this checks provenance and endpoint/solver arithmetic, not independent dynamics.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, localcontext
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
REVISION = "f4aed8f5727034623a9a806ec423f0596bea5c65"
HASHES = {
    "0104-lunar-departure-reference.json":
        "bbcfa37e2e259af0f5545aeb12e9784f8826122f1ad5a66c52698aef856b7134",
    "0107-local-finite-burn-study.json":
        "01b653b72fb9a25b00f53d17cd7d88da9e9c8102fbec0f908b27da3cae9a34dc",
    "0110-local-steering-study.json":
        "678287cc7aee2b3d83e89c9fbff1113a96d24c5b8960f047aeadb82d049c4274",
}


def finite_tree(value: Any) -> None:
    """Validate finite serialized numbers; booleans are metadata, not numbers."""
    if isinstance(value, dict):
        for item in value.values():
            finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            finite_tree(item)
    elif type(value) in (int, float):
        assert math.isfinite(value)
    else:
        assert value is None or isinstance(value, (str, bool))


def vector(values: list[float], size: int) -> np.ndarray:
    assert len(values) == size
    assert all(type(v) in (int, float) and math.isfinite(v) for v in values)
    return np.asarray(values, dtype=float)


def main() -> None:
    if not __debug__:
        raise RuntimeError("Run this assert-based audit without -O")
    records = []
    for name, digest in HASHES.items():
        raw = (EVIDENCE / name).read_bytes()
        assert sha256(raw).hexdigest() == digest
        record = json.loads(raw)
        finite_tree(record)
        records.append(record)
    ref, old, report = records
    assert report["measured_revision"] == REVISION
    assert report["worktree_clean_at_launch"] is True
    assert report["study_invocations"] == 1 and report["automatic_retry"] is False
    assert report["mission_qualified"] is False and report["reason"] is None
    assert report["reference_sha256"] == HASHES["0104-lunar-departure-reference.json"]
    assert report["study_sha256"] == HASHES["0107-local-finite-burn-study.json"]
    assert report["reference_paths"] == [
        f"docs/adr/experiments/{name}" for name in list(HASHES)[:2]
    ]
    assert report["candidate_id"] == ref["candidate"]["candidate_id"] == "d0001-t0035"
    assert report["model_id"] == "local-moon-point-mass-steered-burn-v1"
    assert [report[k] for k in ("origin", "orientation", "units", "time_scale")] == [
        "Moon", "J2000", "SI", "TDB seconds since J2000"
    ]
    assert report["profiles"] == old["profiles"]
    assert report["historical_source_sha256"] == old["source_sha256"]
    for name, digest in report["source_sha256"].items():
        path = f"src/space_nav/{name}"
        assert sha256((ROOT / path).read_bytes()).hexdigest() == digest
        committed = subprocess.check_output(
            ["git", "show", f"{REVISION}:{path}"], cwd=ROOT
        )
        assert sha256(committed).hexdigest() == digest
    assert sha256((ROOT / "moon_to_mars.py").read_bytes()).hexdigest() == (
        "4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf"
    )

    # Only date/resource queries: no environment, propagator or project helpers.
    import spiceypy
    import tudatpy
    from tudatpy import data
    from tudatpy.interface import spice

    assert report["runtime_versions"] == {"numpy": np.__version__, "tudatpy": tudatpy.__version__}
    spice.load_standard_kernels()
    manifest = report["kernels"]
    assert manifest == old["kernels"]
    assert manifest["kernel_source"] == "tudatpy-standard"
    assert manifest["kernel_list_status"] == "complete"
    assert manifest["spiceypy_version"] == spiceypy.__version__
    assert manifest["loaded_kernel_count"] == spiceypy.ktotal("ALL") == 13
    for index, kernel in enumerate(manifest["kernels"]):
        path_text, kind, source, *_ = spiceypy.kdata(index, "ALL")
        path = Path(path_text)
        assert (path.name, path.stem, kind, source or None) == (
            kernel["name"], kernel["version"], kernel["type"], kernel["source"]
        )
        assert path.stat().st_size == kernel["size_bytes"]
        assert sha256(path.read_bytes()).hexdigest() == kernel["sha256"]
    resource = report["retained_lunar_resource"]
    assert resource == ref["lunar_field_provenance"] == old["retained_lunar_resource"]
    path = Path(data.get_gravity_models_path()) / "Moon" / resource["file_name"]
    assert sha256(path.read_bytes()).hexdigest() == resource["actual_sha256"] == resource["expected_sha256"]

    bound = report["binding"]
    baseline = bound["baseline"]
    assert baseline == old["command"]
    branch = ref["results"]["free"]["branches"][0]
    parking = vector(bound["virtual_parking_state_si"], 6)
    assert parking.tolist() == branch["position_m"] + branch["parking_velocity_m_s"]
    assert bound["arrival_delta_v_m_s"] == ref["candidate"]["arrival_delta_v_m_s"]
    window = [spice.convert_date_string_to_ephemeris_time(ref["scenario"]["search"][key])
              for key in ("departure_start_utc", "departure_end_utc")]
    assert window == bound["launch_window_tdb_s"] == old["launch_window_tdb_s"]
    mu, rp = baseline["mu_m3_s2"], math.hypot(*parking[:3])
    assert mu == resource["gravitational_parameter_m3_s2"]
    assert baseline["shape_radius_m"] == resource["orbit_shape_radius_m"]
    assert rp == ref["results"]["free"]["parking_radius_m"]
    n = math.sqrt(mu / rp**3)
    tau0, ti0 = baseline["cutoff_after_ignition_s"], baseline["ignition_epoch_tdb_s"]
    tm = ti0 + baseline["match_after_ignition_s"]
    assert tm == bound["match_epoch_tdb_s"]
    exhaust = 9.80665 * baseline["isp_s"]
    arrival = bound["arrival_delta_v_m_s"]
    m0, dry = baseline["initial_state_si"][6], baseline["dry_mass_kg"]
    assert bound["delta_bounds_s"] == [
        max(-math.pi / (2*n), window[0]-ti0),
        min(math.pi / (2*n), window[1]-ti0, baseline["match_after_ignition_s"]-1-.5*tau0),
    ]
    assert bound["duration_bounds_s"] == [.5*tau0, min(
        1.5*tau0, (m0-dry*math.exp(arrival/exhaust))/(baseline["thrust_n"]/exhaust)
    )]
    basis = np.asarray(bound["basis"])
    d0, e1, e2 = basis
    assert d0.tolist() == baseline["direction_j2000"]
    np.testing.assert_allclose(basis @ basis.T, np.eye(3), atol=5e-16, rtol=0)
    axis = np.eye(3)[int(np.argmin(np.abs(d0)))]
    tangent = axis - np.dot(axis, d0)*d0
    np.testing.assert_allclose(e1, tangent/np.linalg.norm(tangent), atol=5e-16, rtol=0)
    np.testing.assert_allclose(e2, np.cross(d0, e1), atol=5e-16, rtol=0)
    axis = np.cross(parking[:3], parking[3:])
    axis /= np.linalg.norm(axis)

    proposals = report["proposals"]
    accepted = []
    for identifier, item in enumerate(proposals):
        assert item["id"] == identifier and item["profile"] == "nominal"
        assert item["outcome"] == "completed" and item["feasible"] is True
        assert item["reason"] is None and item["control_units"] == ["s", "s", "1", "1", "1", "1"]
        x = vector(item["controls"], 6)
        delta, tau = x[:2]
        assert bound["delta_bounds_s"][0] <= delta <= bound["delta_bounds_s"][1]
        assert bound["duration_bounds_s"][0] <= tau <= bound["duration_bounds_s"][1]
        assert max(abs(x[2:])) <= 1
        command = item["command"]
        fixed = set(baseline) - {"initial_state_si", "ignition_epoch_tdb_s", "cutoff_after_ignition_s", "match_after_ignition_s", "target_state_si"}
        assert set(command) == set(baseline)
        assert all(command[key] == baseline[key] for key in fixed)
        ti = command["ignition_epoch_tdb_s"]
        assert ti == ti0+delta and window[0] <= ti <= window[1]
        assert command["cutoff_after_ignition_s"] == tau
        assert command["match_after_ignition_s"] == (baseline["match_after_ignition_s"] if delta == 0 else tm-ti)
        assert item["match_epoch_tdb_s"] == ti+command["match_after_ignition_s"] == tm
        assert item["cutoff_epoch_tdb_s"] == ti+tau <= tm-1
        angle = -n*tau0/2+n*(ti-ti0)
        for start, stop, tolerance in ((0, 3, 1e-8), (3, 6, 1e-10)):
            v = parking[start:stop]
            rotated = v*math.cos(angle)+np.cross(axis, v)*math.sin(angle)+axis*np.dot(axis, v)*(1-math.cos(angle))
            np.testing.assert_allclose(command["initial_state_si"][start:stop], rotated, atol=tolerance, rtol=0)
        assert command["initial_state_si"][6] == m0
        assert command["target_state_si"][:6] == baseline["target_state_si"][:6]
        with localcontext() as ctx:
            ctx.prec = 50
            mf = Decimal(str(m0))-Decimal(str(baseline["thrust_n"]))*Decimal(str(tau))/(Decimal("9.80665")*Decimal(str(baseline["isp_s"])))
            reserve = mf*(-Decimal(str(arrival))/(Decimal("9.80665")*Decimal(str(baseline["isp_s"])))).exp()
        assert abs(command["target_state_si"][6]-float(mf)) < 1e-9
        assert float(mf) > dry and float(reserve) >= dry
        cutoff, final = vector(item["cutoff_state_si"], 7), vector(item["final_state_si"], 7)
        assert abs(cutoff[6]-float(mf)) <= 1e-6 and cutoff[6] == final[6]
        assert item["cutoff_mass_error_kg"] == abs(cutoff[6]-command["target_state_si"][6])
        assert item["post_arrival_reserve_kg"] == cutoff[6]*math.exp(-arrival/exhaust) >= dry
        assert abs(item["post_arrival_reserve_kg"]-float(reserve)) <= 1e-6
        assert all(math.hypot(*state[:3]) > command["shape_radius_m"] and state[6] > dry for state in (cutoff, final))
        residual = final[:6]-vector(command["target_state_si"], 7)[:6]
        assert residual.tolist() == item["residual_si"]
        assert math.hypot(*residual[:3]) == item["position_error_m"]
        assert math.hypot(*residual[3:]) == item["velocity_error_m_s"]
        scaled = residual/np.asarray([10.]*3+[.01]*3)
        assert scaled.tolist() == item["scaled_residual"]
        assert math.hypot(*scaled) == item["score"]
        closed = item["position_error_m"] <= 10 and item["velocity_error_m_s"] <= .01
        assert item["closure"] == ("pass" if closed else "fail") == "fail"
        assert type(item["checked_saved_states"]) is int and item["checked_saved_states"] > 0
        rate = math.hypot(x[4]-x[2], x[5]-x[3])/tau
        assert rate == item["steering_rate_upper_rad_s"]
        for s in np.linspace(0, 1, 101):
            p, q = (1-s)*x[2:4]+s*x[4:6]
            w = d0+p*e1+q*e2
            length = math.hypot(*w)
            assert length >= 1-5e-16
            d = w/length
            assert abs(math.hypot(*d)-1) < 5e-16
            derivative = (x[4]-x[2])*e1+(x[5]-x[3])*e2
            speed = np.linalg.norm((derivative-d*np.dot(d, derivative))/length)/tau
            assert speed <= rate+1e-18
        if item["accepted"]:
            accepted.append(identifier)
    assert proposals[0]["command"] == baseline
    for key, value in old["runs"][0].items():
        assert proposals[0][key] == value
    assert report["baseline_replay"] == "pass" and report["baseline_replay_differences_si"] == [0., 0., 0.]

    conditions, caps, maximum_svd_error = [], [], 0.
    h, scales = [1., 1., .001, .001, .001, .001], [300., 300., .1, .1, .1, .1]
    for index, iteration in enumerate(report["iterations"]):
        parent_id = 13*index
        assert iteration["iteration"] == index and iteration["parent"] == parent_id
        assert iteration["probe_steps"] == h and iteration["control_scales"] == scales
        assert iteration["probe_ids"] == list(range(parent_id+1, parent_id+13))
        assert iteration["trial_ids"] == [parent_id+13]
        parent = proposals[parent_id]
        x, r = vector(parent["controls"], 6), vector(parent["scaled_residual"], 6)
        columns = []
        for j, step in enumerate(h):
            plus, minus = [proposals[parent_id+1+2*j+k] for k in (0, 1)]
            for sign, probe in ((1, plus), (-1, minus)):
                expected = x.copy()
                expected[j] += sign*step
                assert probe["controls"] == expected.tolist()
                assert probe["role"] == "probe" and probe["parent"] == parent_id
                assert probe["accepted"] is False and probe["fraction"] is None and probe["acceptance_limit"] is None
            columns.append((vector(plus["scaled_residual"], 6)-vector(minus["scaled_residual"], 6))/(2*step/scales[j]))
        matrix = np.column_stack(columns)
        assert matrix.tolist() == iteration["jacobian"]
        solve = iteration["solve"]
        u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
        eps = np.finfo(float).eps
        np.testing.assert_allclose(solve["singular_values"], singular, atol=64*eps*singular[0], rtol=0)
        rank = int(np.count_nonzero(singular > singular[0]*1e-10))
        assert solve["rank"] == rank == 6 and solve["rcond"] == 1e-10
        condition = singular[0]/singular[-1]
        assert condition <= 1e10 and math.isclose(condition, solve["condition_number"], rel_tol=64*eps)
        z = vh.T @ ((u.T @ -r)/singular)
        raw = vector(solve["raw_z"], 6)
        error = float(np.max(np.abs(z-raw)))
        maximum_svd_error = max(maximum_svd_error, error)
        assert error <= 64*eps*condition*max(1., float(np.max(np.abs(z))))
        cap = max(1., max(abs(raw)))
        capped = raw/cap
        assert capped.tolist() == solve["capped_z"] and max(abs(capped)) <= 1
        step = capped*np.asarray(scales)
        assert step.tolist() == solve["step_controls"]
        predicted = [math.fsum([float(r[i])]+[float(v*w) for v, w in zip(matrix[i], capped)]) for i in range(6)]
        for i, value in enumerate(predicted):
            bound_error = 32*eps*(abs(r[i])+sum(abs(matrix[i]*capped)))
            assert abs(value-solve["predicted_residual"][i]) <= bound_error
        assert math.isclose(math.hypot(*predicted), solve["predicted_score"], rel_tol=64*eps)
        assert solve["outcome"] == "ready" and solve["predicted_score"] < parent["score"]
        trial = proposals[parent_id+13]
        assert trial["role"] == "trial" and trial["parent"] == parent_id
        assert trial["fraction"] == 1. and trial["controls"] == (x+step).tolist()
        assert trial["acceptance_limit"] == (1-1e-4)*parent["score"]
        assert trial["score"] <= trial["acceptance_limit"] and trial["accepted"] is True
        conditions.append(condition)
        caps.append(float(cap))
    assert accepted == [0, 13, 26, 39, 52] and report["best_accepted_proposal"] == 52
    assert report["outcome"] == "not-converged" and report["agreement"] == "unavailable"
    assert len(report["iterations"]) == 4
    assert len(proposals) == report["nominal_proposals"] == report["propagation_evaluations"] == 1+4*(12+1) == 53
    assert report["tighter_evaluations"] == 0
    assert report["native_arc_propagations"] == report["completed_arcs"] == 2*53 == 106
    wall_interval = (datetime.fromisoformat(report["execution_finished_utc"])-datetime.fromisoformat(report["execution_started_utc"])).total_seconds()
    assert 0 < report["elapsed_wall_s"] <= wall_interval < 300
    best, first = proposals[52], proposals[0]
    print(json.dumps({
        "audit": "pass", "native_propagations_in_audit": 0,
        "artifact_sha256": HASHES["0110-local-steering-study.json"],
        "condition_numbers": conditions, "cap_divisors": caps,
        "maximum_independent_svd_solution_difference": maximum_svd_error,
        "position_improvement_percent": 100*(1-best["position_error_m"]/first["position_error_m"]),
        "velocity_improvement_percent": 100*(1-best["velocity_error_m_s"]/first["velocity_error_m_s"]),
        "largest_cutoff_mass_error_kg": max(p["cutoff_mass_error_kg"] for p in proposals),
        "best_final_mass_kg": best["final_state_si"][6],
        "best_provisional_arrival_reserve_kg": best["post_arrival_reserve_kg"],
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
