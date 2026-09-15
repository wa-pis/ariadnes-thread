"""Fourth-point harmonic diagnostics, not a full-force or trajectory anchor."""

from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter

import numpy as np
import pytest

from space_nav import trajectory
from test_trajectory_midpoint import _midpoint_acceleration_l2_bound_m_s2
from test_trajectory_spk import _harmonic_prefix_vector_enclosure_m_s2


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("body_name,model_degree,coarse_degree,evaluation_degree,bits", [
    pytest.param("Mars", 120, 100, 120, 120, id="Mars"),
    pytest.param("Moon", 200, 2, 4, None, id="Moon"),
])
def test_fourth_harmonic_binary64_input_binding(
    body_name: str, model_degree: int, coarse_degree: int, evaluation_degree: int, bits: int | None,
) -> None:
    started_s = perf_counter()
    budget = trajectory._RefinementBudget(f"fourth-{body_name.lower()}-input-audit", 300.0)
    deadline_s = budget.deadline_monotonic_s
    names = ("fresh_endpoint_binding", "fourth_endpoint_source_anchor", "fourth_endpoint_rotation_bridge",
             "fourth_endpoint_harmonic_source_bridge", "fourth_endpoint_rotation_force_bridge")
    raw = {name: (ROOT / f"tests/data/m3_{name}.json").read_bytes() for name in names}
    binding, sources, rotations, source_bridge, matrix_bridge = (
        json.loads(raw[name])[name] for name in names
    )
    historical = json.loads((ROOT / "tests/data/m3_fresh_harmonic_replay.json").read_text())
    epoch = binding["end_epoch_tdb_s"]
    assert epoch == 978995455.3554223 and epoch != historical["epoch_tdb_s"]
    assert Fraction(epoch)-Fraction(historical["epoch_tdb_s"]) == Fraction(1, 16)
    for record in (sources, rotations, source_bridge, matrix_bridge):
        assert record["epoch_tdb_s"] == epoch
        for key in ("origin", "orientation", "time_scale"):
            assert record[key] == binding[key] == historical[key]
    for record in (binding, rotations, source_bridge, matrix_bridge, historical):
        assert record["model_id"] == trajectory.PHYSICAL_MODEL_IDENTIFIER
    for record in (sources, source_bridge, matrix_bridge):
        assert record["source_spk_context_sha256"] == binding["source_spk_context_sha256"]
    state = binding["terminal_state_m_m_s_kg"]
    assert state == source_bridge["nominal_state_m_m_s_kg"] == matrix_bridge["nominal_state_m_m_s_kg"]
    assert state[:3] != historical["spacecraft_position_m"]
    rotation = rotations["fields"][body_name]
    source = sources["bodies"][body_name]
    source_force, matrix_force = (item["fields"][body_name] for item in (source_bridge, matrix_bridge))
    digest = sha256(json.dumps(rotation, sort_keys=True, allow_nan=False).encode()).hexdigest()
    assert digest == source_force["rotation_input_sha256"] == matrix_force["rotation_input_sha256"]
    assert rotations["pck_sha256"] == matrix_bridge["pck_sha256"] == historical["pck_sha256"]
    assert rotations["pool_sha256"] == matrix_bridge["pool_sha256"]
    spec = next(item for item in trajectory._HARMONIC_FIELD_SPECS if item.body == body_name)
    path = trajectory._default_gravity_models_path() / spec.body / spec.file_name
    assert trajectory._coefficient_sha256(path) == spec.expected_sha256 == source_force["coefficient_sha256"] == matrix_force["coefficient_sha256"]
    assert source_force["degree"] == matrix_force["degree"] == matrix_force["order"] == model_degree
    assert source_force["includes_c00"] and matrix_force["includes_c00"]
    assert matrix_force["gm_m3_s2"] == spec.gravitational_parameter_m3_s2
    assert matrix_force["reference_radius_m"] == spec.normalization_radius_m
    ideal = tuple(Fraction(int(n, 16), int(d, 16)) for n, d in source["state_exact_m_m_s"][:3])
    relative = tuple(Fraction(ship)-body for ship, body in zip(state[:3], ideal, strict=True))
    assert relative == tuple(Fraction(int(n, 16), int(d, 16)) for n, d in source_force["relative_centre_m_exact"])
    n, d = matrix_force["ideal_radius_squared_m2_exact"]
    assert sum(x*x for x in relative) == Fraction(int(n, 16), int(d, 16))
    rounded = tuple(map(float, ideal))
    assert all(math.isfinite(value) for value in rounded)
    rounding = sum((abs(Fraction(value)-exact) for value, exact in zip(rounded, ideal, strict=True)), Fraction(0))
    allowance = source_force["source_position_l1_allowance_m"]
    assert allowance == source["native_position_l1_allowance_m"]
    assert 0 < rounding <= Fraction(allowance)
    reported = math.nextafter(float(rounding), math.inf)
    assert math.isfinite(reported) and rounding <= Fraction(reported) <= Fraction(allowance)
    budget.check()
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({f"fourth_{body_name.lower()}_binary64_input_binding": {
        "epoch_tdb_s": epoch, "origin": binding["origin"], "orientation": binding["orientation"],
        "time_scale": binding["time_scale"], "model_id": binding["model_id"],
        "input_sha256": {name: sha256(data).hexdigest() for name, data in raw.items()},
        "source_spk_context_sha256": binding["source_spk_context_sha256"],
        "force_context_sha256": binding["force_context_sha256"],
        "coefficient_sha256": spec.expected_sha256, "rotation_input_sha256": digest,
        "nominal_state_m_m_s_kg": state, "carried_error_m_m_s": binding["outgoing_error_m_m_s"],
        "rounded_ideal_source_position_m": rounded, "source_rounding_l1_upper_m": reported,
        "existing_source_position_l1_allowance_m": allowance,
        "existing_source_force_l2_allowance_m_s2": source_force["acceleration_l2_allowance_m_s2"],
        "existing_matrix_force_l2_allowance_m_s2": matrix_force["acceleration_l2_allowance_m_s2"],
        "force_evaluations": 0, "additional_native_queries": 0, "additional_native_arcs": 0,
        "qualification": "Rounded ideal SPK polynomial point, NOT a retained native readback; inside existing source ball at the actual fourth nominal state. Input audit only; no force arithmetic, carried-state or interval certificate; no allowance reduction",
    }}, sort_keys=True, allow_nan=False))
    budget.check()
    # Reuse the audited source ball: rounding is already inside it, not an
    # extra force-error channel. This diagnostic is not the native evaluator.
    field = trajectory._load_harmonic_field_settings(trajectory._import_tudat_environment_setup(), spec, path)
    budget.check()
    cosine, sine = field.normalized_cosine_coefficients, field.normalized_sine_coefficients
    assert cosine.shape == sine.shape == (model_degree+1, model_degree+1)
    coefficient_hashes = {}
    for matrix, key in ((cosine, "cosine_sha256"), (sine, "sine_sha256")):
        assert matrix.dtype == np.float64 and np.all(np.isfinite(matrix))
        coefficient_hashes[key] = sha256(matrix.astype("<f8").tobytes()).hexdigest()
        assert coefficient_hashes[key] == historical["fields"][body_name][key]
    assert field.gravitational_parameter == spec.gravitational_parameter_m3_s2
    assert field.reference_radius == spec.normalization_radius_m
    args = (budget, field.gravitational_parameter, field.reference_radius, cosine, sine,
            np.asarray(rounded), np.asarray(state[:3]), np.asarray(rotation["inertial_to_fixed"]))
    run_started_s = perf_counter()
    coarse_box, tail = _harmonic_prefix_vector_enclosure_m_s2(*args, coarse_degree)
    coarse_elapsed_s = perf_counter()-run_started_s
    budget.check()
    coarse_prefix = tuple((lo+tail, hi-tail) for lo, hi in coarse_box)
    coarse_midpoint, coarse_error = _midpoint_acceleration_l2_bound_m_s2(coarse_prefix, tail)
    run_started_s = perf_counter()
    full_box, full_tail = _harmonic_prefix_vector_enclosure_m_s2(*args, evaluation_degree, bits=bits)
    full_elapsed_s = perf_counter()-run_started_s
    budget.check()
    assert 0 <= full_tail < tail
    assert (full_tail == 0) == (evaluation_degree == model_degree)
    assert all(max(lo, clo) <= min(hi, chi) for (lo, hi), (clo, chi)
               in zip(full_box, coarse_box, strict=True))
    prefix = tuple((lo+full_tail, hi-full_tail) for lo, hi in full_box)
    midpoint, arithmetic_error = _midpoint_acceleration_l2_bound_m_s2(prefix, Fraction(0))
    assert sum((Fraction(a)-Fraction(b))**2 for a, b in zip(midpoint, coarse_midpoint, strict=True)) <= (arithmetic_error+full_tail+coarse_error)**2
    errors = (arithmetic_error, Fraction(source_force["acceleration_l2_allowance_m_s2"]),
              Fraction(matrix_force["acceleration_l2_allowance_m_s2"]))
    total = sum(errors, full_tail)
    reported_errors = [math.nextafter(float(value), math.inf) for value in (*errors, total)]
    assert all(math.isfinite(value) and Fraction(value) >= exact for value, exact
               in zip(reported_errors, (*errors, total), strict=True))
    outward = [[math.nextafter(float(lo), -math.inf), math.nextafter(float(hi), math.inf)] for lo, hi in full_box]
    assert all(math.isfinite(a) and math.isfinite(b) and Fraction(a) <= lo <= hi <= Fraction(b)
               for (a, b), (lo, hi) in zip(outward, full_box, strict=True))
    budget.check()
    assert budget.deadline_monotonic_s == deadline_s
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({f"fourth_{body_name.lower()}_bounded_force": {
        "epoch_tdb_s": epoch, "origin": binding["origin"], "orientation": binding["orientation"],
        "time_scale": binding["time_scale"], "model_id": binding["model_id"],
        "input_sha256": {name: sha256(data).hexdigest() for name, data in raw.items()},
        "source_spk_context_sha256": binding["source_spk_context_sha256"],
        "coefficient_sha256": spec.expected_sha256, **coefficient_hashes, "rotation_input_sha256": digest,
        "nominal_state_m_m_s_kg": state, "rounded_ideal_source_position_m": rounded,
        "carried_error_m_m_s": binding["outgoing_error_m_m_s"],
        "degree": evaluation_degree, "bits": bits, "midpoint_m_s2": midpoint,
        "stored_input_component_intervals_m_s2": outward, "finite_model_tail_m_s2": math.nextafter(float(full_tail), math.inf) if full_tail else 0.0,
        "arithmetic_l2_error_upper_m_s2": reported_errors[0],
        "source_l2_allowance_upper_m_s2": reported_errors[1],
        "matrix_l2_allowance_upper_m_s2": reported_errors[2],
        "ideal_finite_field_l2_error_upper_m_s2": reported_errors[3],
        f"coarse_degree{coarse_degree}_l2_error_upper_m_s2": math.nextafter(float(coarse_error), math.inf),
        f"inside_coarse_degree{coarse_degree}_box": all(clo <= lo <= hi <= chi for (lo, hi), (clo, chi)
                                          in zip(full_box, coarse_box, strict=True)),
        **({"exact_degree100_evaluations": 1, "exact_degree120_evaluations": 0, "bounded_degree120_evaluations": 1}
           if body_name == "Mars" else
           {"exact_degree2_evaluations": 1, "exact_degree4_evaluations": 1,
            "exact_degree200_evaluations": 0, "full_model_degree": model_degree}),
        "coarse_elapsed_s": coarse_elapsed_s, "full_elapsed_s": full_elapsed_s,
        "shared_elapsed_s": perf_counter()-started_s, "shared_deadline_s": 300.0,
        "native_coefficient_loads": 1, "additional_native_queries": 0, "additional_native_arcs": 0,
        "qualification": f"Stored fourth-point {body_name}-only diagnostic with source/PCK allowances once each; coarse consistency is not an exact full-vector oracle. No native harmonic arithmetic, other forces, carried-state, interval or beyond-degree{model_degree} model-error qualification; not a production anchor",
    }}, sort_keys=True, allow_nan=False))
    budget.check()
