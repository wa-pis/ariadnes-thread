"""Offline D17 design evidence; never imports the spacecraft/native propagator.

Print reproducible finite JSON. Linear minima are not nonlinear reachability
bounds; the Bezier checks qualify design identities, not an implementation.
"""

from __future__ import annotations

from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import least_squares, lsq_linear


INPUT_SHA256 = "417f4a33e6407a37e9a41caff29330557f39d7a3bbfc34e9b908cc1d5589cb89"
BASE_REVISION = "71d91e4f80cd5c7422cb5fccb3f451bc728db6c4"


def face_minimum(j: np.ndarray, r: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> float:
    """Independent exhaustive face oracle for this six-dimensional linear box."""
    best = math.inf
    slack = 64*np.finfo(float).eps*np.maximum(1., np.maximum(abs(lo), abs(hi)))
    for status in product((-1, 0, 1), repeat=6):
        face = np.asarray(status)
        fixed, free = face != 0, face == 0
        z = np.where(face == -1, lo, np.where(face == 1, hi, 0.))
        if np.any(free):
            z[free] = np.linalg.lstsq(j[:, free], -r-j[:, fixed] @ z[fixed], rcond=1e-10)[0]
        # Algebraic roundoff only: no native command uses these box fits.
        if np.all(z >= lo-slack) and np.all(z <= hi+slack):
            best = min(best, float(np.linalg.norm(r+j @ z)))
    assert math.isfinite(best)
    return best


def main() -> None:
    if not __debug__:
        raise RuntimeError("Run this assert-based diagnosis without -O")
    raw = Path(__file__).with_name("0113-bound-aware-local-study.json").read_bytes()
    assert sha256(raw).hexdigest() == INPUT_SHA256
    assert np.__version__ == "1.26.4" and scipy.__version__ == "1.17.1"
    report = json.loads(raw)
    assert report["outcome"] == "budget-exhausted" and report["solver_result"] is None
    assert report["reason"] == "D16 stopped: D16 Jacobian-batch limit 20 reached"
    assert report["jacobian_batches"] == report["completed_jacobian_batches"] == 20
    assert report["native_arc_propagations"] == report["completed_arcs"] == 524
    assert report["study_invocations"] == 1 and report["automatic_retry"] is False
    proposals, bound = report["proposals"], report["binding"]
    last = report["jacobians"][-1]
    assert last["parent"] == report["accepted_iterates"][-1] == 249
    best = proposals[report["best_objective"]]
    assert best["id"] == 262 and best["accepted_iterate"] is False
    parent = proposals[249]
    j, r = np.asarray(last["matrix"]), np.asarray(parent["scaled_residual"])
    x, t = np.asarray(parent["controls"]), np.asarray(report["control_scales"])
    physical = np.asarray([bound["delta_bounds_s"], bound["duration_bounds_s"], *[[-1., 1.]]*4])
    lo, hi = (physical[:, 0]-x)/t, (physical[:, 1]-x)/t
    assert hi[1] == 0.
    gradient = j.T @ r
    gradient_scale = float(np.linalg.norm(j, 2)*np.linalg.norm(r))
    free = np.asarray([0, 2, 3, 4, 5])
    free_z = np.linalg.lstsq(j[:, free], -r, rcond=1e-10)[0]
    free_residual = r+j[:, free] @ free_z
    assert np.linalg.matrix_rank(j) == 6 and np.linalg.matrix_rank(j[:, free]) == 5
    raw_z = np.linalg.lstsq(j, -r, rcond=1e-10)[0]
    raw_x = x+t*raw_z
    assert np.linalg.norm(r+j @ raw_z) < 1e-7
    labels = ["ignition_shift_s", "duration_s", "p0", "q0", "p1", "q1"]
    violations = [labels[k] for k in range(6) if not physical[k, 0] <= raw_x[k] <= physical[k, 1]]
    assert violations == ["ignition_shift_s", "duration_s"]
    fits = {}
    for name, lower, upper in (
        ("physical_box", lo, hi),
        ("physical_and_unit_step_box", np.maximum(lo, -1.), np.minimum(hi, 1.)),
    ):
        fit = lsq_linear(j, -r, bounds=(lower, upper), method="bvls", tol=1e-12,
                         max_iter=100, lsq_solver="exact")
        assert fit.success and np.all(fit.x >= lower) and np.all(fit.x <= upper)
        predicted = r+j @ fit.x
        score = float(np.linalg.norm(predicted))
        oracle = face_minimum(j, r, lower, upper)
        assert math.isclose(score, oracle, rel_tol=1e-10, abs_tol=1e-7)
        assert math.isclose(score, float(np.linalg.norm(free_residual)), rel_tol=1e-10)
        g = j.T @ predicted
        projected = np.where(fit.active_mask == -1, np.minimum(g, 0), np.where(
            fit.active_mask == 1, np.maximum(g, 0), g))
        kkt = float(np.max(abs(projected))/max(1., np.linalg.norm(j, 2)*np.linalg.norm(predicted)))
        assert kkt < 1e-10
        assert fit.active_mask.astype(int).tolist() == [0, 1, 0, 0, 0, 0]
        fits[name] = {"predicted_score": score, "face_oracle_score": oracle,
            "predicted_position_error_m": float(np.linalg.norm(predicted[:3])*10.),
            "predicted_velocity_error_m_s": float(np.linalg.norm(predicted[3:])*.01),
            "linear_model_controls": (x+t*fit.x).tolist(),
            "active_mask": fit.active_mask.astype(int).tolist(), "scaled_kkt_inf": kkt}

    seed = proposals[158]
    assert seed["accepted_iterate"] is True and seed["role"] == "objective"
    u0, u1 = np.asarray(seed["controls"][2:4]), np.asarray(seed["controls"][4:6])
    center = (u0+u1)/2
    seed8 = np.asarray([*seed["controls"][:2], *u0, *center, *u1])
    scales8 = np.asarray([300., 300., *[.1]*6])
    bounds8 = np.asarray([bound["delta_bounds_s"], bound["duration_bounds_s"], *[[-1., 1.]]*6])
    first_requests: list[list[float]] = []

    def synthetic_objective(y: np.ndarray) -> np.ndarray:
        first_requests.append(y.tolist())
        return y[:6]  # Initialization check only, no spacecraft or root search.

    least_squares(synthetic_objective, np.zeros(8), jac=lambda y: np.eye(6, 8),
        bounds=((bounds8[:, 0]-seed8)/scales8, (bounds8[:, 1]-seed8)/scales8),
        method="trf", tr_solver="exact", loss="linear", x_scale=1.,
        ftol=1e-10, xtol=1e-10, gtol=1e-10, max_nfev=40, verbose=0, workers=None)
    assert first_requests == [[0.]*8]
    maximum_embedding_error = 0.
    for s in np.linspace(-.1, 1.1, 1201):
        linear = (1-s)*u0+s*u1
        bezier = (1-s)**2*u0+2*s*(1-s)*center+s*s*u1
        maximum_embedding_error = max(maximum_embedding_error, float(np.max(abs(bezier-linear))))
    assert maximum_embedding_error < 5e-16
    basis = np.asarray(bound["basis"])
    largest_rate_ratio = 0.
    for corner in product((-1., 1.), repeat=6):
        a, c, b = np.asarray(corner).reshape(3, 2)
        rate_numerator = 2*max(np.linalg.norm(c-a), np.linalg.norm(b-c))
        for s in np.linspace(0, 1, 33):
            chart = (1-s)**2*a+2*s*(1-s)*c+s*s*b
            casteljau = (1-s)*((1-s)*a+s*c)+s*((1-s)*c+s*b)
            np.testing.assert_allclose(chart, casteljau, atol=5e-16, rtol=0)
            assert np.max(abs(chart)) <= 1.
            w = basis[0]+chart @ basis[1:]
            norm = np.linalg.norm(w)
            direction = w/norm
            assert norm >= 1-5e-16 and abs(np.linalg.norm(direction)-1) < 5e-16
            chart_derivative = 2*((1-s)*(c-a)+s*(b-c))
            dw = chart_derivative @ basis[1:]
            angular = float(np.linalg.norm((dw-direction*np.dot(direction, dw))/norm))
            assert angular <= rate_numerator+5e-15
            if rate_numerator:
                largest_rate_ratio = max(largest_rate_ratio, angular/rate_numerator)
    budget = {"reference_replays": 1, "bezier_seed_replays": 1,
        "objective_requests_including_initial_cache": 40, "jacobian_batches": 40,
        "probes_per_batch": 16, "maximum_nominal_evaluations": 2+39+40*16,
        "maximum_total_evaluations": 2+39+40*16+1,
        "maximum_native_arcs": 2*(2+39+40*16+1), "deadline_s": 300}
    assert budget["maximum_nominal_evaluations"] == 681
    assert budget["maximum_total_evaluations"] == 682 and budget["maximum_native_arcs"] == 1364
    print(json.dumps({"analysis": "saved-linear-response-and-design-identities-only",
        "base_revision": BASE_REVISION, "input_sha256": INPUT_SHA256,
        "runtime_versions": {"numpy": np.__version__, "scipy": scipy.__version__},
        "native_arc_propagations": 0, "spacecraft_targeting_runs": 0,
        "linear_commands_applied": False, "last_measured_jacobian_parent": 249,
        "jacobian_at_best_262_available": False, "returned_scipy_result_available": False,
        "last_parent_score": parent["score"], "best_objective_score": best["score"],
        "last_objective_relative_score_improvement": 1-best["score"]/parent["score"],
        "normalized_gradient_definition": "J.T @ r / (norm(J,2)*norm(r,2)); not SciPy gtol",
        "gradient": gradient.tolist(), "normalized_gradient": (gradient/gradient_scale).tolist(),
        "maximum_free_normalized_gradient": float(np.max(abs(gradient[free]))/gradient_scale),
        "raw_newton_controls": raw_x.tolist(), "raw_violated_bounds": violations,
        "raw_extra_duration_s": float(raw_x[1]-physical[1, 1]),
        "free_five_control_score_floor": float(np.linalg.norm(free_residual)),
        "free_five_control_linear_rank": 5, "linear_counterfactuals": fits,
        "best_duration_margin_s": float(physical[1, 1]-best["controls"][1]),
        "best_provisional_reserve_margin_kg": best["post_arrival_reserve_kg"]-500.,
        "planned_seed": {"retained_proposal": 158, "controls8": seed8.tolist(),
            "duration_margin_s": float(physical[1, 1]-seed8[1]),
            "provisional_reserve_kg": seed["post_arrival_reserve_kg"],
            "relative_score_above_best": seed["score"]/best["score"]-1,
            "first_synthetic_solver_request": first_requests[0],
            "maximum_chart_embedding_error": maximum_embedding_error},
        "bezier_oracles": {"coefficient_box_corners": 64, "samples_per_corner": 33,
            "largest_angular_rate_to_bound_ratio": largest_rate_ratio,
            "native_endpoint_embedding_verified": False},
        "proposed_d17_budget": budget,
        "limitation": "Conditional linear minima, not nonlinear impossibility; new guidance columns and native closure unmeasured",
    }, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
