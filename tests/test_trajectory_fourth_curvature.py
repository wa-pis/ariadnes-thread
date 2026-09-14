"""Retained-input conditional reference-family audit, not live qualification."""

from fractions import Fraction as F
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter

from space_nav import trajectory
from test_trajectory_degree_map import _nonmonopole_degree_map_bound_s_inv2
from test_trajectory_error_transport import _recentered_coast_reaches_m_m_s
from test_trajectory_force_derivatives import _point_mass_force_curvature_bound_m_s4


def test_fourth_endpoint_conditional_monopole_curvature() -> None:
    """Every cubic in the stated acceleration family has these remainder bounds."""
    root = Path(__file__).parent / "data"
    budget = trajectory._RefinementBudget("fourth-conditional-rates", 300.0)
    hashes = {}

    def read(name: str, key: str) -> dict:
        raw = (root / name).read_bytes()
        hashes[name] = sha256(raw).hexdigest()
        return json.loads(raw)[key]

    source = read("m3_fourth_endpoint_source_anchor.json", "fourth_endpoint_source_anchor")
    jerk = read("m3_fourth_endpoint_monopole_jerk.json", "fourth_endpoint_monopole_jerk")
    endpoint = read("m3_fresh_endpoint_binding.json", "fresh_endpoint_binding")
    domain = read("m3_quarter_second_initial_domain.json", "quarter_second_initial_domain")
    force = read("m3_fresh_force_context.json", "fresh_force_context")
    assert source["epoch_tdb_s"] == jerk["epoch_tdb_s"] == endpoint["end_epoch_tdb_s"]
    assert source["end_epoch_tdb_s"] == jerk["source_coverage_end_tdb_s"] == domain["end_epoch_tdb_s"]
    assert source["source_spk_context_sha256"] == jerk["source_spk_context_sha256"] == endpoint["source_spk_context_sha256"]
    assert jerk["nominal_state_m_m_s_kg"] == endpoint["terminal_state_m_m_s_kg"]
    assert jerk["gravitational_parameters_m3_s2"] == force["gravitational_parameters_m3_s2"]
    for data in (source, jerk, endpoint, domain, force):
        assert (data["origin"], data["orientation"], data["time_scale"]) == ("SSB", "J2000", "TDB seconds since J2000")
    assert jerk["model_id"] == endpoint["model_id"] == domain["model_id"] == trajectory.PHYSICAL_MODEL_IDENTIFIER
    h = F(source["end_epoch_tdb_s"]) - F(source["epoch_tdb_s"])
    assert h == F(1, 8)
    # Explicit family premise, NOT an inferred acceleration of an existing curve:
    # q''(t)=a0+j0*t, ||a0||_2 <= 4-h*||j0||_1 implies ||q''||_2 <= 4.
    acceleration = F(4)
    jerk_norm = sum(map(abs, map(F, jerk["midpoint_m_s3"])), F(0))
    anchor_norm_cap = acceleration-h*jerk_norm
    gravity_norm = sum(map(F, domain["gravity_upper_m_s2"].values()), F(0))
    assert 0 < gravity_norm < anchor_norm_cap
    # A gravity anchor with error <= this margin would suffice. No such anchor
    # or anchor-error certificate is constructed or assumed here.
    anchor_error_sufficient_cap = anchor_norm_cap-gravity_norm
    state = tuple(map(F, endpoint["terminal_state_m_m_s_kg"]))
    initial = tuple(map(F, domain["initial_state_m_m_s_kg"]))
    offsets = [sum((abs(a-b) for a, b in zip(state[i:i+3], initial[i:i+3], strict=True)), F(0)) for i in (0, 3)]
    reaches = _recentered_coast_reaches_m_m_s(
        float(h), *offsets, sum(map(abs, state[3:6]), F(0)), F(0), F(0), acceleration,
    )
    assert reaches[0] < F(domain["position_domain_radius_m"])
    assert reaches[1] < F(domain["velocity_domain_radius_m_s"])
    # Zero errors describe the reference's exact initial data, not a reset of
    # the true trajectory's carried error. Convex shared domain admits chords.
    names = set(trajectory.PHYSICAL_BODY_NAMES)
    assert set(source["bodies"]) == set(jerk["gravitational_parameters_m3_s2"]) == set(domain["distance_floors_m"]) == names
    rows = {}
    total = F(0)

    def upper(value: F) -> float:
        result = math.nextafter(float(value), math.inf)
        assert math.isfinite(result) and F(result) >= value >= 0
        return result

    for body, data in source["bodies"].items():
        slope = tuple(F(int(n, 16), int(d, 16)) for n, d in data["state_exact_m_m_s"][3:])
        speed0 = sum((abs(a-b) for a, b in zip(state[3:6], slope, strict=True)), F(0))
        relative_acceleration = acceleration + F(data["curvature_l1_upper_m_s2"])
        speed = speed0 + relative_acceleration*h
        curvature = _point_mass_force_curvature_bound_m_s4(
            jerk["gravitational_parameters_m3_s2"][body], domain["distance_floors_m"][body], speed, relative_acceleration,
        )
        total += curvature
        rows[body] = {"relative_speed_upper_m_s": upper(speed),
                      "relative_acceleration_upper_m_s2": upper(relative_acceleration),
                      "force_curvature_upper_m_s4": upper(curvature)}
    print(json.dumps({"fourth_conditional_monopole_curvature": {
        "input_sha256": hashes, "duration_s": float(h), "reference_acceleration_cap_m_s2": float(acceleration),
        "anchor_norm_sufficient_cap_m_s2_approx": float(anchor_norm_cap),
        "anchor_error_sufficient_cap_m_s2_approx": float(anchor_error_sufficient_cap),
        "reference_reach_upper_m_m_s": list(map(upper, reaches)), "bodies": rows,
        "force_curvature_upper_m_s4": upper(total), "taylor_rate_upper_m_s3": upper(h*total/2),
        "jerk_rounding_error_upper_m_s3": jerk["midpoint_l1_error_upper_m_s3"],
        "additional_ephemeris_queries": 0, "additional_native_arcs": 0,
        "scope": "Retained-input conditional cubic family with explicit acceleration premise only; no selected gravity anchor, nonmonopole rates, full J, native residual or mission certificate",
    }}, sort_keys=True, allow_nan=False))
    started = perf_counter()
    translation = {}
    translation_total = F(0)
    for body in ("Moon", "Mars"):
        budget.check()
        spec = next(item for item in trajectory._HARMONIC_FIELD_SPECS if item.body == body)
        path = trajectory._default_gravity_models_path()/body/spec.file_name
        assert trajectory._coefficient_sha256(path) == spec.expected_sha256
        field = trajectory._load_harmonic_field_settings(trajectory._import_tudat_environment_setup(), spec, path)
        assert field.gravitational_parameter == spec.gravitational_parameter_m3_s2 == jerk["gravitational_parameters_m3_s2"][body]
        assert field.reference_radius == spec.normalization_radius_m
        cosine, sine = field.normalized_cosine_coefficients, field.normalized_sine_coefficients
        assert cosine.shape == sine.shape == (spec.degree+1, spec.degree+1)
        assert cosine[0, 0] == 1.0
        nonmonopole = cosine.copy()
        nonmonopole[0, 0] = 0.0  # Keep every other degree/order, including C20.
        jacobian = _nonmonopole_degree_map_bound_s_inv2(
            budget, field.gravitational_parameter, field.reference_radius,
            domain["distance_floors_m"][body], nonmonopole, sine,
        )
        assert cosine[0, 0] == 1.0  # Never mutate the loaded full field.
        data = source["bodies"][body]
        slope = tuple(F(int(n, 16), int(d, 16)) for n, d in data["state_exact_m_m_s"][3:])
        speed0 = sum((abs(a-b) for a, b in zip(state[3:6], slope, strict=True)), F(0))
        relative_acceleration = acceleration+F(data["curvature_l1_upper_m_s2"])
        displacement_rate = speed0+relative_acceleration*h/2
        rate = jacobian*displacement_rate
        translation_total += rate
        translation[body] = {
            "degree": spec.degree, "coefficient_sha256": spec.expected_sha256,
            "gm_m3_s2": field.gravitational_parameter, "normalization_radius_m": field.reference_radius,
            "distance_floor_m": domain["distance_floors_m"][body],
            "nonmonopole_jacobian_upper_s_inv2": upper(jacobian),
            "displacement_rate_upper_m_s": upper(displacement_rate), "translation_rate_upper_m_s3": upper(rate),
        }
    # Optimistic scalar accounting ONLY: omit all other defect channels,
    # feedback and native residuals, but do not reset incoming velocity error.
    velocity_accounting = F(endpoint["outgoing_error_m_m_s"][1])+translation_total*h*h/2
    budget.check()
    assert (budget.control_attempts, budget.propagation_evaluations, budget.native_arc_propagations) == (0, 0, 0)
    print(json.dumps({"fourth_conditional_nonmonopole_translation": {
        "input_sha256": hashes, "bodies": translation, "duration_s": float(h),
        "reference_acceleration_cap_m_s2": float(acceleration),
        "translation_rate_upper_m_s3": upper(translation_total),
        "incoming_velocity_error_m_s": endpoint["outgoing_error_m_m_s"][1],
        "optimistic_velocity_accounting_m_s_approx": float(velocity_accounting),
        "optimistic_accounting_fits_velocity_gate": velocity_accounting <= F("0.000001"),
        "elapsed_s": perf_counter()-started, "additional_ephemeris_queries": 0, "additional_native_arcs": 0,
        "scope": "Conditional-family ideal nonmonopole translation at fixed orthogonal orientation only; not rotation, full J, source/native arithmetic, selected anchor or mission certificate; failed scalar screen is not a lower bound on true error",
    }}, sort_keys=True, allow_nan=False))
