"""Read-only D17.3 evidence audit; no spacecraft propagations or solver calls.

Run with pinned Conda Python without -O. Native histories are absent: this
checks their retained endpoints, arithmetic, provenance and recorded counters.
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
REVISION = "3434a319d522988013684005b4ffd99576d02089"
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
MODEL = "local-moon-point-mass-bezier-burn-v1"
REFERENCE_MODEL = "local-moon-point-mass-steered-burn-v1"
SEED = [-1094.4910010491465, 5467.042096122668,
        .11712983121190776, .03964718570666498,
        -.24799059467100915, .04826945627805249,
        -.6131110205539261, .05689172684944001]
SCALES = np.asarray([300., 300., .1, .1, .1, .1, .1, .1])
STEPS = np.asarray([1., 1., .001, .001, .001, .001, .001, .001])
RESIDUAL_SCALES = np.asarray([10.]*3+[.01]*3)


def finite_tree(value: Any) -> None:
    if isinstance(value, dict):
        assert all(isinstance(key, str) for key in value)
        for item in value.values():
            finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            finite_tree(item)
    elif type(value) in (int, float):
        assert math.isfinite(value)
    else:
        assert value is None or isinstance(value, (str, bool))


def vector(value: Any, size: int) -> np.ndarray:
    assert isinstance(value, list) and len(value) == size
    assert all(type(v) in (int, float) and math.isfinite(v) for v in value)
    return np.asarray(value, dtype=float)


def agreement(a: list[float], b: list[float]) -> list[float]:
    vector(a, 7)
    vector(b, 7)
    return [math.dist(a[:3], b[:3]), math.dist(a[3:6], b[3:6]), abs(a[6]-b[6])]


def agrees(differences: list[float]) -> bool:
    vector(differences, 3)
    return all(a <= b for a, b in zip(differences, (1., .001, 1e-6)))


def main() -> None:
    if not __debug__:
        raise RuntimeError("Run this assert-based audit without -O")
    records = []
    for name, digest in HASHES.items():
        raw = (EVIDENCE/name).read_bytes()
        assert sha256(raw).hexdigest() == digest
        record = json.loads(raw)
        finite_tree(record)
        records.append(record)
    reference, old, steering, bounded = records
    raw = (EVIDENCE/"0116-bezier-local-study.json").read_bytes()
    assert sha256(raw).hexdigest() == "93e5b224ade1038616e11951d5d45f2ca717e10544c2b67aac2120de6103b566"
    report = json.loads(raw)
    finite_tree(report)
    assert report["measured_revision"] == REVISION
    assert report["worktree_clean_at_launch"] is True
    assert report["study_invocations"] == 1 and report["automatic_retry"] is False
    assert report["reference_paths"] == [f"docs/adr/experiments/{n}" for n in HASHES]
    assert report["reference_sha256"] == list(HASHES.values())
    assert report["historical_source_sha256"] == {
        "0107": old["source_sha256"], "0110": steering["source_sha256"],
        "0113": bounded["source_sha256"],
    }
    expected_sources = {"bezier_local_targeting.py", "bounded_local_targeting.py",
                        "local_targeting.py", "local_burn.py", "lunar_departure.py",
                        "models.py", "trajectory.py", "ephemeris.py"}
    assert set(report["source_sha256"]) == expected_sources
    for name, digest in report["source_sha256"].items():
        path = f"src/space_nav/{name}"
        assert sha256((ROOT/path).read_bytes()).hexdigest() == digest
        committed = subprocess.check_output(["git", "show", f"{REVISION}:{path}"], cwd=ROOT)
        assert sha256(committed).hexdigest() == digest
    assert report["source_sha256"]["bezier_local_targeting.py"] == (
        "88621f68d2efee4d4f456617dd3b169964a813fd6fc713c7143b2cda01d6bd7f")
    for historical in (old, steering, bounded):
        # Historical evidence pins its own source, not today's dictionary.
        assert historical["source_sha256"]
        for name, digest in historical["source_sha256"].items():
            path = f"src/space_nav/{name}"
            committed = subprocess.check_output(
                ["git", "show", f"{historical['measured_revision']}:{path}"], cwd=ROOT)
            assert sha256(committed).hexdigest() == digest
    environment = (ROOT/"environment.yml").read_bytes()
    assert sha256(environment).hexdigest() == report["environment_yml_sha256"]
    assert environment == subprocess.check_output(
        ["git", "show", f"{REVISION}:environment.yml"], cwd=ROOT)
    assert sha256((ROOT/"moon_to_mars.py").read_bytes()).hexdigest() == (
        "4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf")

    # Resource inventory/date conversion only; no space_nav or native propagation.
    import scipy
    import spiceypy
    import tudatpy
    from tudatpy import data
    from tudatpy.interface import spice

    assert sys.version_info[:3] == (3, 12, 14)
    assert report["runtime_versions"] == {
        "numpy": np.__version__, "scipy": scipy.__version__, "tudatpy": tudatpy.__version__,
    } == {"numpy": "1.26.4", "scipy": "1.17.1", "tudatpy": "1.0.0"}
    assert report["runtime_versions"] == bounded["runtime_versions"]
    assert {k: report["runtime_versions"][k] for k in steering["runtime_versions"]} == steering["runtime_versions"]
    installed = json.loads((Path(sys.prefix)/"conda-meta/scipy-1.17.1-py312h4519d97_1.json").read_bytes())
    assert installed["build"] == "py312h4519d97_1" and installed["subdir"] == "osx-arm64"
    assert "conda-forge" in installed["channel"]
    spice.load_standard_kernels()
    manifest = report["kernels"]
    assert manifest == old["kernels"] == steering["kernels"] == bounded["kernels"]
    assert manifest["kernel_source"] == "tudatpy-standard"
    assert manifest["kernel_list_status"] == "complete"
    assert manifest["spiceypy_version"] == spiceypy.__version__ == "8.2.0"
    assert manifest["loaded_kernel_count"] == spiceypy.ktotal("ALL") == len(manifest["kernels"]) == 13
    for index, kernel in enumerate(manifest["kernels"]):
        path_text, kind, source, *_ = spiceypy.kdata(index, "ALL")
        path = Path(path_text)
        assert (path.name, path.stem, kind, source or None) == (
            kernel["name"], kernel["version"], kernel["type"], kernel["source"])
        assert path.stat().st_size == kernel["size_bytes"]
        assert sha256(path.read_bytes()).hexdigest() == kernel["sha256"]
    resource = report["retained_lunar_resource"]
    assert resource == reference["lunar_field_provenance"] == old["retained_lunar_resource"]
    assert resource == steering["retained_lunar_resource"] == bounded["retained_lunar_resource"]
    path = Path(data.get_gravity_models_path())/"Moon"/resource["file_name"]
    assert sha256(path.read_bytes()).hexdigest() == resource["actual_sha256"] == resource["expected_sha256"]
    assert report["candidate_id"] == reference["candidate"]["candidate_id"] == "d0001-t0035"
    assert report["model_id"] == MODEL and report["reference_model_id"] == REFERENCE_MODEL
    assert report["algorithm_id"] == "bound-aware-bezier-trf-v1"
    assert [report[k] for k in ("origin", "orientation", "units", "time_scale")] == [
        "Moon", "J2000", "SI", "TDB seconds since J2000"]
    assert report["profiles"] == old["profiles"] == steering["profiles"] == bounded["profiles"]
    assert report["mission_qualified"] is False
    bound = report["binding"]
    assert bound == steering["binding"] == bounded["binding"]
    baseline = bound["baseline"]
    assert baseline == old["command"]
    branch = reference["results"]["free"]["branches"][0]
    parking = vector(bound["virtual_parking_state_si"], 6)
    assert parking.tolist() == branch["position_m"]+branch["parking_velocity_m_s"]
    window = [spice.convert_date_string_to_ephemeris_time(reference["scenario"]["search"][key])
              for key in ("departure_start_utc", "departure_end_utc")]
    assert window == bound["launch_window_tdb_s"] == old["launch_window_tdb_s"]
    mu, radius = baseline["mu_m3_s2"], math.hypot(*parking[:3])
    assert mu == resource["gravitational_parameter_m3_s2"]
    assert baseline["shape_radius_m"] == resource["orbit_shape_radius_m"]
    assert radius == reference["results"]["free"]["parking_radius_m"]
    n = math.sqrt(mu/radius**3)
    tau0, ti0 = baseline["cutoff_after_ignition_s"], baseline["ignition_epoch_tdb_s"]
    tm = ti0+baseline["match_after_ignition_s"]
    assert tm == bound["match_epoch_tdb_s"] == 979002340.6346419
    arrival = bound["arrival_delta_v_m_s"]
    assert arrival == reference["candidate"]["arrival_delta_v_m_s"]
    exhaust = 9.80665*baseline["isp_s"]
    m0, dry = baseline["initial_state_si"][6], baseline["dry_mass_kg"]
    assert (baseline["thrust_n"], baseline["isp_s"], m0, dry) == (1000, 450, 2000, 500)
    assert bound["delta_bounds_s"] == [max(-math.pi/(2*n), window[0]-ti0), min(
        math.pi/(2*n), window[1]-ti0, baseline["match_after_ignition_s"]-1-.5*tau0)]
    assert bound["duration_bounds_s"] == [.5*tau0, min(
        1.5*tau0, (m0-dry*math.exp(arrival/exhaust))/(baseline["thrust_n"]/exhaust))]
    lower = np.asarray([bound["delta_bounds_s"][0], bound["duration_bounds_s"][0], *[-1.]*6])
    upper = np.asarray([bound["delta_bounds_s"][1], bound["duration_bounds_s"][1], *[1.]*6])
    minimum_coast = tm-(ti0+upper[0])-upper[1]
    assert minimum_coast == report["minimum_box_coast_s"] >= 1

    def feasible(x: np.ndarray) -> bool:
        if x.shape != (8,) or np.any(x < lower) or np.any(x > upper):
            return False
        ti, tau = ti0+float(x[0]), float(x[1])
        match = baseline["match_after_ignition_s"] if x[0] == 0 else tm-ti
        mass = m0-baseline["thrust_n"]*tau/exhaust
        return (window[0] <= ti <= window[1] and tau <= match-1 and ti+tau <= tm-1
                and mass > dry and mass*math.exp(-arrival/exhaust) >= dry)

    assert all(feasible(np.asarray([d, t, *[0.]*6]))
               for d in bound["delta_bounds_s"] for t in bound["duration_bounds_s"])
    seed = vector(report["seed_controls"], 8)
    assert seed.tolist() == SEED
    retained = bounded["proposals"][158]
    assert retained["id"] == 158 and retained["role"] == "objective"
    assert retained["accepted_iterate"] is True and retained["cache_hit"] is False
    assert 158 in bounded["accepted_iterates"]
    assert seed[:4].tolist()+seed[6:].tolist() == retained["controls"]
    assert seed[4:6].tolist() == ((seed[2:4]+seed[6:8])/2).tolist()
    assert np.all(seed > lower) and np.all(seed < upper)
    assert report["seed_reference"] == {"proposal": 158, "sha256": list(HASHES.values())[3]}
    assert report["control_scales"] == SCALES.tolist()
    assert report["residual_scales"] == RESIDUAL_SCALES.tolist()
    assert report["solver_bounds"] == [((lower-seed)/SCALES).tolist(), ((upper-seed)/SCALES).tolist()]
    assert report["solver_settings"] == {
        "method": "trf", "tr_solver": "exact", "loss": "linear", "x_scale": 1.,
        "ftol": 1e-10, "xtol": 1e-10, "gtol": 1e-10, "max_nfev": 40,
        "verbose": 0, "workers": None}
    basis = np.asarray(bound["basis"])
    assert basis.shape == (3, 3)
    d0, e1, e2 = basis
    assert d0.tolist() == baseline["direction_j2000"]
    np.testing.assert_allclose(basis@basis.T, np.eye(3), atol=5e-16, rtol=0)
    least_axis = np.eye(3)[int(np.argmin(np.abs(d0)))]
    tangent = least_axis-np.dot(least_axis, d0)*d0
    np.testing.assert_allclose(e1, tangent/np.linalg.norm(tangent), atol=5e-16, rtol=0)
    np.testing.assert_allclose(e2, np.cross(d0, e1), atol=5e-16, rtol=0)
    axis = np.cross(parking[:3], parking[3:])
    axis /= np.linalg.norm(axis)

    def audit_command(item: dict[str, Any], reference_model: bool) -> None:
        size = 6 if reference_model else 8
        x = vector(item["controls"], size)
        expanded = np.concatenate((x[:4], (x[2:4]+x[4:])/2, x[4:])) if reference_model else x
        assert feasible(expanded)
        assert item["control_units"] == ["s", "s"]+["1"]*(size-2)
        command = item["command"]
        if command is None:
            assert item["outcome"] == "failed"
            return
        delta, tau = map(float, x[:2])
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
            ve = Decimal("9.80665")*Decimal(str(baseline["isp_s"]))
            mf = Decimal(str(m0))-Decimal(str(baseline["thrust_n"]))*Decimal(str(tau))/ve
            reserve = mf*(-Decimal(str(arrival))/ve).exp()
        assert abs(command["target_state_si"][6]-float(mf)) < 1e-9
        if item["cutoff_state_si"] is not None:
            cutoff = vector(item["cutoff_state_si"], 7)
            assert abs(cutoff[6]-float(mf)) <= 1e-6
            assert math.hypot(*cutoff[:3]) > command["shape_radius_m"] and cutoff[6] > dry
        if item["outcome"] != "completed":
            assert item["reason"] and item["final_state_si"] is None
            assert item["closure"] == "unavailable" and item["score"] is None
            return
        assert item["reason"] is None
        cutoff, final = vector(item["cutoff_state_si"], 7), vector(item["final_state_si"], 7)
        assert cutoff[6] == final[6]
        assert item["cutoff_mass_error_kg"] == abs(cutoff[6]-command["target_state_si"][6]) <= 1e-6
        assert item["post_arrival_reserve_kg"] == cutoff[6]*math.exp(-arrival/exhaust) >= dry
        assert abs(item["post_arrival_reserve_kg"]-float(reserve)) <= 1e-6
        assert math.hypot(*final[:3]) > command["shape_radius_m"] and final[6] > dry
        residual = final[:6]-vector(command["target_state_si"], 7)[:6]
        assert residual.tolist() == item["residual_si"]
        assert math.hypot(*residual[:3]) == item["position_error_m"]
        assert math.hypot(*residual[3:]) == item["velocity_error_m_s"]
        scaled = residual/RESIDUAL_SCALES
        assert scaled.tolist() == item["scaled_residual"]
        assert math.hypot(*scaled) == item["score"]
        closed = item["position_error_m"] <= 10 and item["velocity_error_m_s"] <= .01
        assert item["closure"] == ("pass" if closed else "fail")
        assert type(item["checked_saved_states"]) is int and item["checked_saved_states"] > 0
        u0, uc, u1 = expanded[2:4], expanded[4:6], expanded[6:8]
        rate = (math.hypot(*(u1-u0)) if reference_model else
                2*max(math.hypot(*(uc-u0)), math.hypot(*(u1-uc))))/tau
        assert rate == item["steering_rate_upper_rad_s"]
        for s in np.linspace(0, 1, 17):
            u = (1-s)**2*u0+2*s*(1-s)*uc+s*s*u1
            casteljau = (1-s)*((1-s)*u0+s*uc)+s*((1-s)*uc+s*u1)
            np.testing.assert_allclose(u, casteljau, atol=5e-16, rtol=0)
            assert np.all(u >= -1-5e-16) and np.all(u <= 1+5e-16)
            w = d0+u[0]*e1+u[1]*e2
            length = math.hypot(*w)
            assert length >= 1-5e-16
            direction = w/length
            assert abs(math.hypot(*direction)-1) <= 5e-16
            du = 2*((1-s)*(uc-u0)+s*(u1-uc))
            dw = du[0]*e1+du[1]*e2
            speed = np.linalg.norm((dw-direction*np.dot(direction, dw))/length)/tau
            assert speed <= rate+1e-18

    # Every retained D16 command is independently reconstructed as a separate model.
    for identifier, item in enumerate(bounded["proposals"]):
        assert item["id"] == identifier and item["outcome"] == "completed"
        audit_command(item, True)
    proposals = report["proposals"]
    allowed = {"two-node-reference-replay", "bezier-seed-replay", "objective", "probe", "frozen-repeat"}
    for identifier, item in enumerate(proposals):
        assert item["id"] == identifier and item["role"] in allowed
        reference_model = item["role"] == "two-node-reference-replay"
        assert item["model_id"] == (REFERENCE_MODEL if reference_model else MODEL)
        assert item["profile"] == ("tighter" if item["role"] == "frozen-repeat" else "nominal")
        assert type(item["cache_hit"]) is bool and type(item["accepted_iterate"]) is bool
        audit_command(item, reference_model)
    failed = [p for p in proposals if p["outcome"] != "completed"]
    assert len(failed) <= 1
    if failed:
        assert failed[0] is proposals[-1] and failed[0]["cache_hit"] is False
    assert proposals[0]["role"] == "two-node-reference-replay" and proposals[0]["parent"] is None
    assert proposals[0]["controls"] == retained["controls"]
    replays = proposals[:2]
    if replays[0]["outcome"] == "completed":
        differences = agreement(replays[0]["final_state_si"], retained["final_state_si"])
        assert report["baseline_replay_differences_si"] == differences
        assert report["baseline_replay"] == ("pass" if agrees(differences) else "fail")
    if len(replays) == 2:
        assert report["baseline_replay"] == "pass"
        assert replays[1]["role"] == "bezier-seed-replay" and replays[1]["parent"] == 0
        assert replays[1]["controls"] == seed.tolist()
        if replays[1]["outcome"] == "completed":
            differences = {
                "fresh_reference": agreement(replays[1]["final_state_si"], replays[0]["final_state_si"]),
                "retained_reference": agreement(replays[1]["final_state_si"], retained["final_state_si"])}
            assert report["embedding_replay_differences_si"] == differences
            assert report["embedding_replay"] == ("pass" if all(agrees(d) for d in differences.values()) else "fail")
    cached = [p for p in proposals if p["cache_hit"]]
    objectives = [p for p in proposals if p["role"] == "objective"]
    if objectives:
        assert report["baseline_replay"] == report["embedding_replay"] == "pass"
        assert len(cached) == 1 and cached[0] is proposals[2]
        initial = cached[0]
        assert initial["parent"] == initial["cache_source"] == 1
        assert initial["controls"] == seed.tolist() and initial["role"] == "objective"
        ignored = {"id", "role", "parent", "cache_hit", "cache_source", "accepted_iterate"}
        assert all(initial[k] == replays[1][k] for k in set(replays[1])-ignored)
    else:
        assert not cached
    assert all("cache_source" not in p for p in proposals if not p["cache_hit"])

    stencil_counts = {"central": 0, "forward": 0, "backward": 0}
    probe_ids, complete_jacobians = [], []
    for item in report["jacobians"]:
        parent = proposals[item["parent"]]
        assert parent["role"] == "objective" and parent["accepted_iterate"] is True
        assert parent["outcome"] == "completed" and parent["closure"] == "fail"
        x, rc = vector(parent["controls"], 8), vector(parent["scaled_residual"], 6)
        assert item["probe_steps"] == STEPS.tolist() and item["control_scales"] == SCALES.tolist()
        assert item["gradient_parent"] == parent["id"] and item["rcond"] == 1e-10
        free = (lower < x) & (x < upper)
        assert item["face_free_mask"] == free.tolist()
        assert item["bound_margins"] == {"lower": (x-lower).tolist(), "upper": (upper-x).tolist()}
        pairs = []
        for j, step in enumerate(STEPS):
            for name, offsets in (("central", (step, -step)), ("forward", (step, 2*step)),
                                  ("backward", (-step, -2*step))):
                points = [x+np.eye(8)[j]*offset for offset in offsets]
                if all(feasible(point) for point in points):
                    break
            else:
                raise AssertionError("Saved Jacobian has no complete fixed-step stencil")
            assert item["stencils"][j] == name
            pairs.append((name, points))
            stencil_counts[name] += 1
        ids = item["probe_ids"]
        assert 1 <= len(ids) <= 16 and ids == list(range(parent["id"]+1, parent["id"]+1+len(ids)))
        nominal_before = sum(not p["cache_hit"] and p["profile"] == "nominal" for p in proposals[:ids[0]])
        assert nominal_before+16 <= 681 and 2*nominal_before+32 <= 1362
        for offset, identifier in enumerate(ids):
            probe = proposals[identifier]
            assert probe["role"] == "probe" and probe["parent"] == parent["id"]
            assert probe["accepted_iterate"] is False
            assert probe["controls"] == pairs[offset//2][1][offset % 2].tolist()
        probe_ids.extend(ids)
        if item["matrix"] is None:
            assert item is report["jacobians"][-1]
            assert failed and proposals[ids[-1]] is failed[0]
            assert all(item[k] is None for k in ("singular_values", "rank", "condition_number",
                       "gradient", "free_singular_values", "free_rank"))
            continue
        assert len(ids) == 16 and all(proposals[k]["outcome"] == "completed" for k in ids)
        columns = []
        for j, (name, _) in enumerate(pairs):
            ra, rb = [vector(proposals[k]["scaled_residual"], 6) for k in ids[2*j:2*j+2]]
            numerator = ra-rb if name == "central" else -3*rc+4*ra-rb if name == "forward" else 3*rc-4*ra+rb
            columns.append(numerator/(2*STEPS[j])*SCALES[j])
        matrix = np.column_stack(columns)
        assert matrix.shape == (6, 8) and matrix.tolist() == item["matrix"]
        singular = np.linalg.svd(matrix, compute_uv=False)
        free_singular = np.linalg.svd(matrix[:, free], compute_uv=False)
        eps = np.finfo(float).eps
        np.testing.assert_allclose(vector(item["singular_values"], 6), singular, atol=64*eps*singular[0], rtol=0)
        assert len(item["free_singular_values"]) == min(6, int(np.count_nonzero(free)))
        np.testing.assert_allclose(item["free_singular_values"], free_singular,
                                   atol=64*eps*(free_singular[0] if len(free_singular) else 0), rtol=0)
        assert item["rank"] == int(np.count_nonzero(singular > singular[0]*1e-10)) <= 6
        assert item["free_rank"] == (int(np.count_nonzero(free_singular > free_singular[0]*1e-10)) if len(free_singular) else 0)
        condition = singular[0]/singular[-1] if singular[-1] > 0 else None
        if condition is not None and math.isfinite(condition):
            assert math.isclose(condition, item["condition_number"], rel_tol=64*eps)
        else:
            assert item["condition_number"] is None
        gradient = matrix.T@rc
        np.testing.assert_allclose(vector(item["gradient"], 8), gradient, atol=0, rtol=64*eps)
        complete_jacobians.append(item)
    assert probe_ids == [p["id"] for p in proposals if p["role"] == "probe"]
    parents = [j["parent"] for j in report["jacobians"]]
    accepted = report["accepted_iterates"]
    assert accepted == sorted(set(accepted)) == [p["id"] for p in proposals if p["accepted_iterate"]]
    assert accepted[:len(parents)] == parents
    for item in objectives[1:]:
        assert item["parent"] == max([1]+[p for p in parents if p < item["id"]])
    eligible = [p for p in proposals if p["role"] in ("bezier-seed-replay", "objective") and p["outcome"] == "completed"]
    best = min(eligible, key=lambda p: p["score"]) if eligible else None
    assert report["best_objective"] == (best["id"] if best and report["embedding_replay"] != "fail" else None)
    closed = [p for p in eligible if p["closure"] == "pass"]
    repeats = [p for p in proposals if p["role"] == "frozen-repeat"]
    assert len(repeats) <= 1
    if closed:
        selected = closed[0]
        assert report["selected_objective"] == selected["id"]
        assert all(p["id"] < selected["id"] for p in proposals if p["role"] == "probe")
        assert len(repeats) == 1 and repeats[0] is proposals[-1]
        repeat = repeats[0]
        assert repeat["parent"] == selected["id"] and repeat["controls"] == selected["controls"]
        assert repeat["command"] == selected["command"]
        assert report["solver_result"] is None
        if selected["role"] == "objective":
            assert report["solver_stop"] == "physical-closure-before-jacobian"
        if repeat["outcome"] == "completed":
            differences = agreement(selected["final_state_si"], repeat["final_state_si"])
            assert report["agreement_differences_si"] == differences
            assert report["agreement"] == ("pass" if agrees(differences) else "fail")
            qualified = agrees(differences) and repeat["closure"] == "pass"
            assert report["outcome"] == ("local-qualified" if qualified else "tighter-unqualified")
    else:
        assert report["selected_objective"] is None and not repeats
        assert report["agreement"] == "unavailable" and report["agreement_differences_si"] is None
        assert report.get("solver_stop") is None
    result = report["solver_result"]
    if result is None:
        assert accepted == parents
        if not closed:
            assert report["outcome"] in {"budget-exhausted", "failed", "baseline-replay-mismatch",
                                          "embedding-replay-mismatch", "domain-unresolved",
                                          "derivative-domain-unresolved"}
    else:
        assert not closed and not failed
        final = proposals[result["final_objective"]]
        assert final["role"] == "objective" and final["accepted_iterate"] is True
        assert accepted == parents if final["id"] in parents else accepted == parents+[final["id"]]
        y = vector(result["coordinates"], 8)
        assert (seed+SCALES*y).tolist() == final["controls"]
        assert result["nfev"] == report["objective_requests"]
        assert result["njev"] == len(complete_jacobians)
        last = complete_jacobians[-1]
        assert last["parent"] == final["id"]
        gradient = vector(last["gradient"], 8)
        np.testing.assert_allclose(vector(result["gradient"], 8), gradient, atol=0, rtol=64*np.finfo(float).eps)
        lo, hi = np.asarray(report["solver_bounds"])
        distance = np.where(gradient < 0, hi-y, np.where(gradient > 0, y-lo, 1.))
        optimality = float(np.linalg.norm(gradient*distance, ord=np.inf))
        assert math.isclose(result["optimality"], optimality, rel_tol=128*np.finfo(float).eps, abs_tol=1e-20)
        active = np.zeros(8)
        ld, ud = y-lo, hi-y
        active[ld <= np.minimum(ud, 1e-10*np.maximum(1, np.abs(lo)))] = -1
        active[ud <= np.minimum(ld, 1e-10*np.maximum(1, np.abs(hi)))] = 1
        assert vector(result["active_mask"], 8).tolist() == active.tolist()
        messages = {
            0: "The maximum number of function evaluations is exceeded.",
            1: "`gtol` termination condition is satisfied.",
            2: "`ftol` termination condition is satisfied.",
            3: "`xtol` termination condition is satisfied.",
            4: "Both `ftol` and `xtol` termination conditions are satisfied."}
        assert result["status"] in messages and result["message"] == messages[result["status"]]
        if result["status"] != 0:
            assert report["reason"] is None
        if result["status"] == 1:
            assert result["optimality"] < report["solver_settings"]["gtol"]
        expected = "budget-exhausted" if result["status"] == 0 else "stationary-unclosed" if result["status"] == 1 else "stagnated-unclosed"
        assert report["outcome"] == expected

    counters = ("objective_requests", "jacobian_batches", "completed_jacobian_batches", "control_attempts",
                "nominal_evaluations", "propagation_evaluations", "tighter_evaluations",
                "native_arc_propagations", "completed_arcs")
    assert all(type(report[k]) is int and report[k] >= 0 for k in counters)
    assert report["objective_requests"] == len(objectives) <= 40
    assert report["jacobian_batches"] == len(report["jacobians"]) <= 40
    assert report["completed_jacobian_batches"] == len(complete_jacobians)
    assert report["control_attempts"] == len(proposals)-len(cached)
    nominal = [p for p in proposals if p["profile"] == "nominal" and not p["cache_hit"]]
    completed = [p for p in proposals if p["outcome"] == "completed" and not p["cache_hit"]]
    completed_nominal = sum(p["profile"] == "nominal" for p in completed)
    assert completed_nominal <= report["nominal_evaluations"] <= len(nominal) <= 681
    assert len(completed) <= report["propagation_evaluations"] <= len(proposals)-len(cached) <= 682
    assert report["tighter_evaluations"] == len(repeats) <= 1
    assert report["propagation_evaluations"] == report["nominal_evaluations"]+report["tighter_evaluations"]
    assert 2*len(completed) <= report["completed_arcs"] <= report["native_arc_propagations"] <= 1364
    assert report["native_arc_propagations"]-report["completed_arcs"] <= 1
    assert report["completed_arcs"] <= 2*report["propagation_evaluations"]
    if not failed:
        assert report["nominal_evaluations"] == len(nominal)
        assert report["propagation_evaluations"] == len(completed)
        assert report["native_arc_propagations"] == report["completed_arcs"] == 2*len(completed)
    else:
        assert report["native_arc_propagations"] <= 2*len(completed)+2
        if failed[0]["cutoff_state_si"] is not None:
            assert report["completed_arcs"] >= 2*len(completed)+1
    assert report["native_arc_propagations"]-2*report["tighter_evaluations"] <= 1362
    assert 2+39+40*16 == 681 and 681+1 == 682 and 2*682 == 1364
    interval = (datetime.fromisoformat(report["finished_utc"])-datetime.fromisoformat(report["started_utc"])).total_seconds()
    assert 0 < report["elapsed_wall_s"] <= interval
    if report["elapsed_wall_s"] >= 300:
        assert report["outcome"] == "budget-exhausted" and "deadline" in report["reason"]
    else:
        assert report["elapsed_wall_s"] < 300
    if report["outcome"] == "budget-exhausted":
        assert report["reason"] and "D17" in report["reason"]
        if "objective-request limit" in report["reason"]:
            assert report["objective_requests"] == 40
        if "Jacobian-batch limit" in report["reason"]:
            assert report["jacobian_batches"] == 40
    print(json.dumps({
        "audit": "pass", "native_propagations_in_audit": 0,
        "artifact_sha256": sha256(raw).hexdigest(), "outcome": report["outcome"],
        "completed_commands_checked": len(completed)+len(cached)+len(bounded["proposals"]),
        "jacobians_checked": len(complete_jacobians), "stencil_counts": stencil_counts,
        "best_objective": report["best_objective"], "accepted_iterates": accepted,
        "last_jacobian_parent": parents[-1] if parents else None,
        "last_full_rank": complete_jacobians[-1]["rank"] if complete_jacobians else None,
        "last_free_rank": complete_jacobians[-1]["free_rank"] if complete_jacobians else None,
        "last_strict_face_free_mask": complete_jacobians[-1]["face_free_mask"] if complete_jacobians else None,
        "solver_active_mask": result["active_mask"] if result else None,
        "solver_status": result["status"] if result else None,
        "solver_optimality": result["optimality"] if result else None,
        "best_is_confirmed_accepted_iterate": best["accepted_iterate"] if best else None,
        "best_position_error_m": best["position_error_m"] if best else None,
        "best_velocity_error_m_s": best["velocity_error_m_s"] if best else None,
        "best_provisional_arrival_reserve_kg": best["post_arrival_reserve_kg"] if best else None,
        "counters": {k: report[k] for k in counters},
        "elapsed_wall_s": report["elapsed_wall_s"],
        "limitation": "Retained endpoints/arithmetic/provenance/counters only; native histories absent; no reachability or whole-interval safety proof",
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
