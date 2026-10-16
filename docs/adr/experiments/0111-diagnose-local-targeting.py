"""Recompute D15 diagnosis from retained matrices, without native propagation.

Print finite JSON. Box fits are linear counterfactuals, never flight commands.
An exhaustive face oracle checks SciPy's algebra, not nonlinear reachability.
"""

from __future__ import annotations

from hashlib import sha256
from itertools import product
import json
import math
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import lsq_linear


INPUT_HASH = "678287cc7aee2b3d83e89c9fbff1113a96d24c5b8960f047aeadb82d049c4274"
BASE_REVISION = "74dbeb15c93060e0cd7ccfbbc8e770c5c6d2f144"


def face_oracle(
    matrix: np.ndarray, residual: np.ndarray, lower: np.ndarray, upper: np.ndarray,
) -> float:
    """Enumerate all 3**6 box faces, solving free coordinates with NumPy."""
    best = math.inf
    slack = 64*np.finfo(float).eps*np.maximum(1., np.maximum(abs(lower), abs(upper)))
    for face in product((-1, 0, 1), repeat=6):
        status = np.asarray(face)
        fixed, free = status != 0, status == 0
        z = np.where(status == -1, lower, np.where(status == 1, upper, 0.))
        if any(free):
            z[free] = np.linalg.lstsq(
                matrix[:, free], -residual-matrix[:, fixed] @ z[fixed], rcond=1e-10,
            )[0]
        # Algebra-only roundoff allowance, not a relaxed physical command gate.
        if np.all(z >= lower-slack) and np.all(z <= upper+slack):
            best = min(best, float(np.linalg.norm(residual+matrix @ z)))
    assert math.isfinite(best)
    return best


def main() -> None:
    if not __debug__:
        raise RuntimeError("Run this assert-based diagnosis without -O")
    raw = Path(__file__).with_name("0110-local-steering-study.json").read_bytes()
    assert sha256(raw).hexdigest() == INPUT_HASH
    assert scipy.__version__ == "1.17.1" and np.__version__ == "1.26.4"
    study = json.loads(raw)
    binding, proposals = study["binding"], study["proposals"]
    physical_bounds = np.asarray([
        binding["delta_bounds_s"], binding["duration_bounds_s"],
        *[[-1., 1.]]*4,
    ])
    labels = ["ignition_shift_s", "duration_s", "p0", "q0", "p1", "q1"]
    rows = []
    for item in study["iterations"]:
        parent = proposals[item["parent"]]
        trial = proposals[item["trial_ids"][0]]
        x, r = np.asarray(parent["controls"]), np.asarray(parent["scaled_residual"])
        matrix, scales = np.asarray(item["jacobian"]), np.asarray(item["control_scales"])
        z = np.asarray(item["solve"]["raw_z"])
        raw_x = x+scales*z
        predicted_score = item["solve"]["predicted_score"]
        actual_ratio = (parent["score"]**2-trial["score"]**2)/(
            parent["score"]**2-predicted_score**2
        )
        assert math.isfinite(actual_ratio) and actual_ratio > 0
        linear_zero_error = float(np.linalg.norm(r+matrix @ z))
        assert linear_zero_error < 1e-7
        even_ratios = []
        for j in range(6):
            plus, minus = [np.asarray(proposals[k]["scaled_residual"])
                           for k in item["probe_ids"][2*j:2*j+2]]
            even_ratios.append(float(np.linalg.norm(plus+minus-2*r)/np.linalg.norm(plus-minus)))
        lower = (physical_bounds[:, 0]-x)/scales
        upper = (physical_bounds[:, 1]-x)/scales
        fits = {}
        for name, lo, hi in (
            ("physical_box", lower, upper),
            ("physical_and_unit_step_box", np.maximum(lower, -1), np.minimum(upper, 1)),
        ):
            fit = lsq_linear(matrix, -r, bounds=(lo, hi), method="bvls",
                             tol=1e-12, max_iter=100, lsq_solver="exact")
            assert fit.success and np.all(fit.x >= lo) and np.all(fit.x <= hi)
            predicted = r+matrix @ fit.x
            score = float(np.linalg.norm(predicted))
            oracle = face_oracle(matrix, r, lo, hi)
            assert math.isclose(score, oracle, rel_tol=1e-10, abs_tol=1e-7)
            gradient = matrix.T @ predicted
            kkt = np.where(fit.active_mask == -1, np.minimum(gradient, 0), np.where(
                fit.active_mask == 1, np.maximum(gradient, 0), gradient,
            ))
            kkt_scale = max(1., np.linalg.norm(matrix, 2)*np.linalg.norm(predicted))
            scaled_kkt = float(max(abs(kkt))/kkt_scale)
            assert scaled_kkt < 1e-10
            fits[name] = {
                "predicted_scaled_score": score,
                "predicted_position_error_m": float(np.linalg.norm(predicted[:3])*10),
                "predicted_velocity_error_m_s": float(np.linalg.norm(predicted[3:])*.01),
                "linear_model_controls": (x+scales*fit.x).tolist(),
                "active_mask": fit.active_mask.astype(int).tolist(),
                "scaled_kkt_inf": scaled_kkt,
                "face_oracle_score": oracle,
            }
        rows.append({
            "iteration": item["iteration"]+1, "parent": parent["id"],
            "raw_newton_controls": raw_x.tolist(),
            "raw_violated_bounds": [labels[j] for j in range(6)
                                    if not physical_bounds[j, 0] <= raw_x[j] <= physical_bounds[j, 1]],
            "raw_linear_residual_norm": linear_zero_error,
            "uniform_cap_divisor": float(max(1., max(abs(z)))),
            "condition_number": item["solve"]["condition_number"],
            "predicted_capped_score": predicted_score,
            "observed_trial_score": trial["score"],
            "squared_reduction_ratio": actual_ratio,
            "maximum_even_to_odd_probe_ratio": max(even_ratios),
            "linear_counterfactuals": fits,
        })
    best = proposals[52]
    coast_box_minimum = (binding["baseline"]["match_after_ignition_s"]
                         -physical_bounds[0, 1]-physical_bounds[1, 1])
    assert coast_box_minimum > 1
    assert all(row["raw_violated_bounds"] == ["ignition_shift_s", "duration_s"] for row in rows)
    assert all(row["linear_counterfactuals"]["physical_and_unit_step_box"]["predicted_scaled_score"]
               < row["predicted_capped_score"] for row in rows)
    print(json.dumps({
        "analysis": "retained-linear-model-only", "base_revision": BASE_REVISION,
        "input_sha256": INPUT_HASH, "runtime_versions": {"numpy": np.__version__, "scipy": scipy.__version__},
        "native_arc_propagations": 0, "nonlinear_targeting_runs": 0,
        "linear_commands_applied": False, "jacobian_at_final_proposal_available": False,
        "coast_minimum_over_original_box_s": coast_box_minimum,
        "final_margins": {
            "lower_ignition_bound_s": best["controls"][0]-physical_bounds[0, 0],
            "upper_duration_bound_s": physical_bounds[1, 1]-best["controls"][1],
            "provisional_arrival_reserve_kg": best["post_arrival_reserve_kg"]-500,
        },
        "iterations": rows,
        "d16_worst_case_budget": {
            "objective_calls_including_cached_initial": 40, "jacobian_batches": 20,
            "probes_per_batch": 12, "maximum_nominal_evaluations": 1+39+20*12,
            "maximum_total_evaluations": 1+39+20*12+1,
            "maximum_native_arcs": 2*(1+39+20*12+1), "deadline_s": 300,
        },
    }, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
