"""Stored fourth-endpoint input binding, not a new force or trajectory anchor."""

from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path

from space_nav import trajectory


ROOT = Path(__file__).resolve().parents[1]


def test_fourth_mars_binary64_input_binding() -> None:
    budget = trajectory._RefinementBudget("fourth-mars-input-audit", 300.0)
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
    rotation = rotations["fields"]["Mars"]
    source = sources["bodies"]["Mars"]
    source_force, matrix_force = (item["fields"]["Mars"] for item in (source_bridge, matrix_bridge))
    digest = sha256(json.dumps(rotation, sort_keys=True, allow_nan=False).encode()).hexdigest()
    assert digest == source_force["rotation_input_sha256"] == matrix_force["rotation_input_sha256"]
    assert rotations["pck_sha256"] == matrix_bridge["pck_sha256"] == historical["pck_sha256"]
    assert rotations["pool_sha256"] == matrix_bridge["pool_sha256"]
    spec = next(item for item in trajectory._HARMONIC_FIELD_SPECS if item.body == "Mars")
    path = trajectory._default_gravity_models_path() / spec.body / spec.file_name
    assert trajectory._coefficient_sha256(path) == spec.expected_sha256 == source_force["coefficient_sha256"] == matrix_force["coefficient_sha256"]
    assert source_force["degree"] == matrix_force["degree"] == matrix_force["order"] == 120
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
    print(json.dumps({"fourth_mars_binary64_input_binding": {
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
