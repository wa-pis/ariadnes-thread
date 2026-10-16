"""Read-only D16.3 provenance/arithmetic audit; zero spacecraft propagations.

Run with pinned Conda Python, without -O. This independently reconstructs saved
commands and derivatives, not omitted native histories or physical reachability.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, localcontext
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
REVISION = "501516ee52ebef4f85e6d8f4304dc1bc35078270"
HASHES = {
    "0104-lunar-departure-reference.json":
        "bbcfa37e2e259af0f5545aeb12e9784f8826122f1ad5a66c52698aef856b7134",
    "0107-local-finite-burn-study.json":
        "01b653b72fb9a25b00f53d17cd7d88da9e9c8102fbec0f908b27da3cae9a34dc",
    "0110-local-steering-study.json":
        "678287cc7aee2b3d83e89c9fbff1113a96d24c5b8960f047aeadb82d049c4274",
    "0113-bound-aware-local-study.json":
        "417f4a33e6407a37e9a41caff29330557f39d7a3bbfc34e9b908cc1d5589cb89",
}


def finite_tree(value: Any) -> None:
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


def vector(value: list[float], size: int) -> np.ndarray:
    assert len(value) == size
    assert all(type(v) in (int, float) and math.isfinite(v) for v in value)
    return np.asarray(value, dtype=float)


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
    reference, old, steering, report = records
    assert report["measured_revision"] == REVISION
    assert report["worktree_clean_at_launch"] is True
    assert report["study_invocations"] == 1 and report["automatic_retry"] is False
    assert report["reference_paths"] == [f"docs/adr/experiments/{n}" for n in list(HASHES)[:3]]
    assert report["reference_sha256"] == list(HASHES.values())[:3]
    assert report["historical_source_sha256"] == {
        "0107": old["source_sha256"], "0110": steering["source_sha256"],
    }
    for name, digest in report["source_sha256"].items():
        path = f"src/space_nav/{name}"
        assert sha256((ROOT / path).read_bytes()).hexdigest() == digest
        committed = subprocess.check_output(["git", "show", f"{REVISION}:{path}"], cwd=ROOT)
        assert sha256(committed).hexdigest() == digest
    assert len(report["source_sha256"]) == 7
    environment = (ROOT / "environment.yml").read_bytes()
    assert sha256(environment).hexdigest() == report["environment_yml_sha256"]
    assert environment == subprocess.check_output(
        ["git", "show", f"{REVISION}:environment.yml"], cwd=ROOT,
    )
    assert sha256((ROOT / "moon_to_mars.py").read_bytes()).hexdigest() == (
        "4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf"
    )

    # SPICE only converts dates/lists resources; no project or propagation helper.
    import scipy
    import spiceypy
    import tudatpy
    from tudatpy import data
    from tudatpy.interface import spice

    assert sys.version_info[:3] == (3, 12, 14)
    assert report["runtime_versions"] == {
        "numpy": np.__version__, "scipy": scipy.__version__, "tudatpy": tudatpy.__version__,
    } == {"numpy": "1.26.4", "scipy": "1.17.1", "tudatpy": "1.0.0"}
    installed = json.loads((Path(sys.prefix) / "conda-meta/scipy-1.17.1-py312h4519d97_1.json").read_bytes())
    assert installed["build"] == "py312h4519d97_1" and installed["subdir"] == "osx-arm64"
    assert "conda-forge" in installed["channel"]
    spice.load_standard_kernels()
    manifest = report["kernels"]
    assert manifest == old["kernels"] == steering["kernels"]
    assert manifest["kernel_source"] == "tudatpy-standard"
    assert manifest["kernel_list_status"] == "complete"
    assert manifest["spiceypy_version"] == spiceypy.__version__ == "8.2.0"
    assert manifest["loaded_kernel_count"] == spiceypy.ktotal("ALL") == 13
    for index, kernel in enumerate(manifest["kernels"]):
        path_text, kind, source, *_ = spiceypy.kdata(index, "ALL")
        path = Path(path_text)
        assert (path.name, path.stem, kind, source or None) == (
            kernel["name"], kernel["version"], kernel["type"], kernel["source"],
        )
        assert path.stat().st_size == kernel["size_bytes"]
        assert sha256(path.read_bytes()).hexdigest() == kernel["sha256"]
    resource = report["retained_lunar_resource"]
    assert resource == reference["lunar_field_provenance"] == old["retained_lunar_resource"]
    path = Path(data.get_gravity_models_path()) / "Moon" / resource["file_name"]
    assert sha256(path.read_bytes()).hexdigest() == resource["actual_sha256"] == resource["expected_sha256"]
    assert report["candidate_id"] == reference["candidate"]["candidate_id"] == "d0001-t0035"
    assert report["model_id"] == "local-moon-point-mass-steered-burn-v1"
    assert report["algorithm_id"] == "bound-aware-local-trf-v1"
    assert [report[k] for k in ("origin", "orientation", "units", "time_scale")] == [
        "Moon", "J2000", "SI", "TDB seconds since J2000",
    ]
    assert report["profiles"] == old["profiles"] == steering["profiles"]
    bound = report["binding"]
    assert bound == steering["binding"]
    baseline = bound["baseline"]
    assert baseline == old["command"]
    branch = reference["results"]["free"]["branches"][0]
    parking = vector(bound["virtual_parking_state_si"], 6)
    assert parking.tolist() == branch["position_m"] + branch["parking_velocity_m_s"]
    window = [spice.convert_date_string_to_ephemeris_time(reference["scenario"]["search"][key])
              for key in ("departure_start_utc", "departure_end_utc")]
    assert window == bound["launch_window_tdb_s"] == old["launch_window_tdb_s"]
    mu, radius = baseline["mu_m3_s2"], math.hypot(*parking[:3])
    assert mu == resource["gravitational_parameter_m3_s2"]
    assert baseline["shape_radius_m"] == resource["orbit_shape_radius_m"]
    assert radius == reference["results"]["free"]["parking_radius_m"]
    n = math.sqrt(mu / radius**3)
    tau0, ti0 = baseline["cutoff_after_ignition_s"], baseline["ignition_epoch_tdb_s"]
    tm = ti0 + baseline["match_after_ignition_s"]
    assert tm == bound["match_epoch_tdb_s"] == 979002340.6346419
    arrival = bound["arrival_delta_v_m_s"]
    assert arrival == reference["candidate"]["arrival_delta_v_m_s"]
    exhaust = 9.80665 * baseline["isp_s"]
    m0, dry = baseline["initial_state_si"][6], baseline["dry_mass_kg"]
    assert (baseline["thrust_n"], baseline["isp_s"], m0, dry) == (1000, 450, 2000, 500)
    assert bound["delta_bounds_s"] == [max(-math.pi/(2*n), window[0]-ti0), min(
        math.pi/(2*n), window[1]-ti0, baseline["match_after_ignition_s"]-1-.5*tau0,
    )]
    assert bound["duration_bounds_s"] == [.5*tau0, min(
        1.5*tau0, (m0-dry*math.exp(arrival/exhaust))/(baseline["thrust_n"]/exhaust),
    )]
    lower = np.asarray([bound["delta_bounds_s"][0], bound["duration_bounds_s"][0], *[-1.]*4])
    upper = np.asarray([bound["delta_bounds_s"][1], bound["duration_bounds_s"][1], *[1.]*4])
    minimum_coast = tm-(ti0+upper[0])-upper[1]
    assert minimum_coast == report["minimum_box_coast_s"] >= 1

    def feasible(x: np.ndarray) -> bool:
        if np.any(x < lower) or np.any(x > upper):
            return False
        ti, tau = ti0+float(x[0]), float(x[1])
        match = baseline["match_after_ignition_s"] if x[0] == 0 else tm-ti
        mass = m0-baseline["thrust_n"]*tau/exhaust
        return (window[0] <= ti <= window[1] and tau <= match-1 and ti+tau <= tm-1
                and mass > dry and mass*math.exp(-arrival/exhaust) >= dry)

    assert all(feasible(np.asarray([d, t, 0., 0., 0., 0.]))
               for d in bound["delta_bounds_s"] for t in bound["duration_bounds_s"])
    seed = vector(report["seed_controls"], 6)
    assert seed.tolist() == steering["proposals"][52]["controls"]
    assert report["seed_reference"] == {"proposal": 52, "sha256": list(HASHES.values())[2]}
    scales = np.asarray([300., 300., .1, .1, .1, .1])
    residual_scales = np.asarray([10.]*3+[.01]*3)
    assert report["control_scales"] == scales.tolist()
    assert report["residual_scales"] == residual_scales.tolist()
    assert report["solver_bounds"] == [((lower-seed)/scales).tolist(),
                                        ((upper-seed)/scales).tolist()]
    assert report["solver_settings"] == {
        "method": "trf", "tr_solver": "exact", "loss": "linear", "x_scale": 1.,
        "ftol": 1e-10, "xtol": 1e-10, "gtol": 1e-10, "max_nfev": 40,
        "verbose": 0, "workers": None,
    }
    basis = np.asarray(bound["basis"])
    d0, e1, e2 = basis
    assert d0.tolist() == baseline["direction_j2000"]
    np.testing.assert_allclose(basis @ basis.T, np.eye(3), atol=5e-16, rtol=0)
    axis = np.eye(3)[int(np.argmin(np.abs(d0)))]
    tangent = axis-np.dot(axis, d0)*d0
    np.testing.assert_allclose(e1, tangent/np.linalg.norm(tangent), atol=5e-16, rtol=0)
    np.testing.assert_allclose(e2, np.cross(d0, e1), atol=5e-16, rtol=0)
    axis = np.cross(parking[:3], parking[3:])
    axis /= np.linalg.norm(axis)

    proposals = report["proposals"]
    for identifier, item in enumerate(proposals):
        assert item["id"] == identifier and item["profile"] == "nominal"
        assert item["outcome"] == "completed" and item["reason"] is None
        assert item["control_units"] == ["s", "s", "1", "1", "1", "1"]
        x = vector(item["controls"], 6)
        assert feasible(x)
        delta, tau = map(float, x[:2])
        command = item["command"]
        changed = {"initial_state_si", "ignition_epoch_tdb_s", "cutoff_after_ignition_s",
                   "match_after_ignition_s", "target_state_si"}
        assert set(command) == set(baseline)
        assert all(command[key] == baseline[key] for key in set(baseline)-changed)
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
            exhaust_decimal = Decimal("9.80665")*Decimal(str(baseline["isp_s"]))
            mf = Decimal(str(m0))-Decimal(str(baseline["thrust_n"]))*Decimal(str(tau))/exhaust_decimal
            reserve = mf*(-Decimal(str(arrival))/exhaust_decimal).exp()
        assert abs(command["target_state_si"][6]-float(mf)) < 1e-9
        cutoff, final = vector(item["cutoff_state_si"], 7), vector(item["final_state_si"], 7)
        assert abs(cutoff[6]-float(mf)) <= 1e-6 and cutoff[6] == final[6]
        assert item["cutoff_mass_error_kg"] == abs(cutoff[6]-command["target_state_si"][6]) <= 1e-6
        assert item["post_arrival_reserve_kg"] == cutoff[6]*math.exp(-arrival/exhaust) >= dry
        assert abs(item["post_arrival_reserve_kg"]-float(reserve)) <= 1e-6
        assert all(math.hypot(*s[:3]) > command["shape_radius_m"] and s[6] > dry for s in (cutoff, final))
        residual = final[:6]-vector(command["target_state_si"], 7)[:6]
        assert residual.tolist() == item["residual_si"]
        assert math.hypot(*residual[:3]) == item["position_error_m"]
        assert math.hypot(*residual[3:]) == item["velocity_error_m_s"]
        scaled = residual/residual_scales
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
            direction = w/length
            assert abs(math.hypot(*direction)-1) < 5e-16
            derivative = (x[4]-x[2])*e1+(x[5]-x[3])*e2
            speed = np.linalg.norm((derivative-direction*np.dot(direction, derivative))/length)/tau
            assert speed <= rate+1e-18
    replay, initial = proposals[:2]
    assert replay["role"] == "seed-replay" and replay["parent"] is None
    assert replay["controls"] == initial["controls"] == seed.tolist()
    assert replay["final_state_si"] == steering["proposals"][52]["final_state_si"]
    assert report["baseline_replay"] == "pass" and report["baseline_replay_differences_si"] == [0., 0., 0.]
    assert initial["role"] == "objective" and initial["parent"] == initial["cache_source"] == 0
    assert initial["cache_hit"] is True
    ignored = {"id", "role", "parent", "cache_hit", "cache_source", "accepted_iterate"}
    assert all(initial[k] == replay[k] for k in set(replay)-ignored)
    assert [p["id"] for p in proposals if p["cache_hit"]] == [1]

    h = np.asarray([1., 1., .001, .001, .001, .001])
    stencil_counts = {"central": 0, "forward": 0, "backward": 0}
    probe_ids, conditions = [], []
    for item in report["jacobians"]:
        parent = proposals[item["parent"]]
        assert parent["role"] == "objective" and parent["accepted_iterate"] is True
        x, rc = vector(parent["controls"], 6), vector(parent["scaled_residual"], 6)
        assert item["probe_steps"] == h.tolist() and item["control_scales"] == scales.tolist()
        assert item["probe_ids"] == list(range(item["parent"]+1, item["parent"]+13))
        columns = []
        for j, step in enumerate(h):
            for name, offsets in (("central", (step, -step)), ("forward", (step, 2*step)),
                                  ("backward", (-step, -2*step))):
                points = [x+np.eye(6)[j]*offset for offset in offsets]
                if all(feasible(point) for point in points):
                    break
            else:
                raise AssertionError("Saved Jacobian has no complete fixed-step stencil")
            assert item["stencils"][j] == name
            stencil_counts[name] += 1
            pair = [proposals[k] for k in item["probe_ids"][2*j:2*j+2]]
            for probe, expected in zip(pair, points):
                assert probe["role"] == "probe" and probe["parent"] == item["parent"]
                assert probe["accepted_iterate"] is False and probe["controls"] == expected.tolist()
            ra, rb = [vector(probe["scaled_residual"], 6) for probe in pair]
            numerator = ra-rb if name == "central" else -3*rc+4*ra-rb if name == "forward" else 3*rc-4*ra+rb
            columns.append(numerator/(2*step)*scales[j])
        matrix = np.column_stack(columns)
        assert matrix.tolist() == item["matrix"]
        singular = np.linalg.svd(matrix, compute_uv=False)
        eps = np.finfo(float).eps
        np.testing.assert_allclose(item["singular_values"], singular, atol=64*eps*singular[0], rtol=0)
        assert item["rank"] == int(np.count_nonzero(singular > singular[0]*1e-10))
        assert item["rcond"] == 1e-10
        condition = singular[0]/singular[-1]
        assert math.isclose(condition, item["condition_number"], rel_tol=64*eps)
        conditions.append(float(condition))
        probe_ids.extend(item["probe_ids"])
    assert probe_ids == [p["id"] for p in proposals if p["role"] == "probe"]
    parents = [item["parent"] for item in report["jacobians"]]
    assert parents == report["accepted_iterates"] == [p["id"] for p in proposals if p["accepted_iterate"]]
    for item in proposals[2:]:
        if item["role"] == "objective":
            assert item["parent"] == max(p for p in parents if p < item["id"])
    best = min((p for p in proposals if p["role"] in ("seed-replay", "objective")), key=lambda p: p["score"])
    assert report["best_objective"] == best["id"] == 262
    assert best["accepted_iterate"] is False and best["controls"][1] == upper[1]
    assert report["outcome"] == "budget-exhausted"
    assert report["reason"] == "D16 stopped: D16 Jacobian-batch limit 20 reached"
    assert report["solver_result"] is None and report.get("solver_stop") is None
    assert report["selected_objective"] is None and report["mission_qualified"] is False
    assert report["agreement"] == "unavailable" and report["agreement_differences_si"] is None
    assert report["objective_requests"] == sum(p["role"] == "objective" for p in proposals) == 22 <= 40
    assert report["jacobian_batches"] == report["completed_jacobian_batches"] == len(report["jacobians"]) == 20
    assert len(probe_ids) == 12*20 == 240
    assert report["control_attempts"] == len(proposals)-1 == 262
    assert report["nominal_evaluations"] == report["propagation_evaluations"] == 1+21+240 == 262 <= 280
    assert report["tighter_evaluations"] == 0
    assert report["native_arc_propagations"] == report["completed_arcs"] == 524 == 2*262 <= 562
    interval = (datetime.fromisoformat(report["finished_utc"])-datetime.fromisoformat(report["started_utc"])).total_seconds()
    assert 0 < report["elapsed_wall_s"] <= interval < 300
    print(json.dumps({
        "audit": "pass", "native_propagations_in_audit": 0,
        "artifact_sha256": list(HASHES.values())[3], "stencil_counts": stencil_counts,
        "condition_number_range": [min(conditions), max(conditions)],
        "minimum_box_coast_s": minimum_coast, "best_objective": best["id"],
        "best_is_confirmed_accepted_iterate": best["accepted_iterate"],
        "position_improvement_percent": 100*(1-best["position_error_m"]/replay["position_error_m"]),
        "velocity_improvement_percent": 100*(1-best["velocity_error_m_s"]/replay["velocity_error_m_s"]),
        "best_position_error_m": best["position_error_m"], "best_velocity_error_m_s": best["velocity_error_m_s"],
        "largest_cutoff_mass_error_kg": max(p["cutoff_mass_error_kg"] for p in proposals),
        "best_final_mass_kg": best["final_state_si"][6],
        "best_provisional_arrival_reserve_kg": best["post_arrival_reserve_kg"],
        "solver_status_and_projected_gradient": "unavailable after independent batch-cap exception",
        "limitation": "Endpoints/arithmetic/provenance only; saved native histories absent; no reachability proof",
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
