"""Retained-input conditional reference-family audit, not live qualification."""

from fractions import Fraction as F
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter

import pytest

from space_nav import trajectory
from test_trajectory_c20 import _c20_spatial_jacobian_bound_s_inv2
from test_trajectory_degree_map import _degree_hessian_operator_bound_s_inv2, _nonmonopole_degree_map_bound_s_inv2
from test_trajectory_error_transport import _recentered_coast_reaches_m_m_s
from test_trajectory_force_derivatives import _point_mass_force_curvature_bound_m_s4
from test_trajectory_spk import _dyadic_sqrt_bounds, _harmonic_spatial_jacobian_bound_s_inv2
from test_trajectory_tracefree import _tracefree_operator_bound_s_inv2


@pytest.mark.parametrize("degree", [0, 2, 60, 120])
def test_isotropic_degree_accounting_monotone_floor(degree: int) -> None:
    """Exact square-root oracle for the method-output inequality, not force error."""
    # (2n+1)*Q=1; r(0)=5 and ||v(0)||=2 are exact oracle values.
    q = F(1, 2*degree+1)
    exact_floor = F(7, 5**(degree+3))*(degree+1)*(degree+2)*2
    for distance in (2.5, 5.0):
        for speed in (F(2), F(3)):
            result = _degree_hessian_operator_bound_s_inv2(degree, q, 7.0, 1.0, distance)*speed
            assert result >= exact_floor
            assert (result == exact_floor) == (distance == 5.0 and speed == 2)


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
    degree_report = None
    method_report = None
    local_geometry = {}
    local_total = F(0)
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
        local_started = perf_counter()
        source_position = tuple(F(int(n, 16), int(d, 16)) for n, d in data["state_exact_m_m_s"][:3])
        relative_position = tuple(a-b for a, b in zip(state[:3], source_position, strict=True))
        radius_squared = sum((x*x for x in relative_position), F(0))
        radius_lower = _dyadic_sqrt_bounds(radius_squared)[0]
        # Every r(t) and chord [r(0), r(t)] is in this convex relative ball.
        # This covers the conditional reference, NOT a true-state error tube.
        displacement = h*displacement_rate
        local_floor = math.nextafter(float(radius_lower-displacement), -math.inf)
        assert math.isfinite(local_floor) and 0 < F(local_floor) <= radius_lower-displacement
        assert (F(local_floor)+displacement)**2 <= radius_squared
        assert local_floor > domain["distance_floors_m"][body] > domain["collision_guards_m"][body]
        local_jacobian = _nonmonopole_degree_map_bound_s_inv2(
            budget, field.gravitational_parameter, field.reference_radius, local_floor, nonmonopole, sine,
        )
        assert 0 <= local_jacobian <= jacobian
        local_total += local_jacobian*displacement_rate
        local_geometry[body] = {
            "local_distance_floor_m": local_floor, "relative_displacement_upper_m": upper(displacement),
            "broad_distance_floor_m": domain["distance_floors_m"][body],
            "local_nonmonopole_jacobian_upper_s_inv2": upper(local_jacobian),
            "local_translation_rate_upper_m_s3": upper(local_jacobian*displacement_rate),
            "elapsed_s": perf_counter()-local_started,
        }
        if body == "Mars":
            degree_started = perf_counter()
            degree_bounds = []
            degree_norm_squares = []
            for n, (c_row, s_row) in enumerate(zip(nonmonopole, sine, strict=True)):
                budget.check()
                squared = sum((F(float(c))**2+F(float(s))**2 for c, s in zip(c_row[:n+1], s_row[:n+1], strict=True)), F(0))
                degree_norm_squares.append(squared)
                degree_bounds.append(_degree_hessian_operator_bound_s_inv2(
                    n, squared, field.gravitational_parameter, field.reference_radius, domain["distance_floors_m"][body],
                ))
            assert sum(degree_bounds, F(0)) == jacobian
            method_started = perf_counter()
            # Any uniform distance floor is <= ||r(0)||; any initial-speed
            # upper bound is >= ||r'(0)||. These opposite-sided enclosures
            # deliberately LOWER-bound this accounting method, not true error.
            radius_ceiling = _dyadic_sqrt_bounds(radius_squared)[1]
            velocity_squared = sum(((a-b)**2 for a, b in zip(state[3:6], slope, strict=True)), F(0))
            speed_lower = _dyadic_sqrt_bounds(velocity_squared)[0]
            assert radius_ceiling**2 >= radius_squared and 0 <= speed_lower**2 <= velocity_squared
            gm, normalization_radius = F(field.gravitational_parameter), F(field.reference_radius)
            formula_lower = sum((gm/radius_ceiling**3*(normalization_radius/radius_ceiling)**n
                                 * (n+1)*(n+2)*_dyadic_sqrt_bounds((2*n+1)*q)[0]
                                 for n, q in enumerate(degree_norm_squares) if q), F(0))
            assert 0 < formula_lower <= local_jacobian and 0 < speed_lower <= speed0
            rate_lower = formula_lower*speed_lower
            value_lower = F(endpoint["outgoing_error_m_m_s"][1])+rate_lower*h*h/2
            assert value_lower <= F(endpoint["outgoing_error_m_m_s"][1])+local_jacobian*displacement_rate*h*h/2

            def lower(value: F) -> float:
                result = math.nextafter(float(value), -math.inf)
                assert math.isfinite(result) and 0 <= F(result) <= value
                return result

            method_report = {
                "input_sha256": hashes, "coefficient_sha256": spec.expected_sha256, "body": body,
                "duration_s": float(h), "anchor_radius_upper_m": upper(radius_ceiling),
                "initial_relative_speed_lower_m_s": lower(speed_lower),
                "degree_formula_lower_s_inv2": lower(formula_lower), "translation_formula_lower_m_s3": lower(rate_lower),
                "velocity_accounting_lower_m_s": lower(value_lower),
                "geometry_and_speed_tightening_cannot_pass": F("0.000001") < F(lower(value_lower)),
                "elapsed_s": perf_counter()-method_started, "additional_ephemeris_queries": 0, "additional_native_arcs": 0,
                "scope": "Lower bound on fixed full-degree isotropic translation accounting with the same state, fields, horizon and incoming error ONLY; not a lower bound on actual force change or trajectory error, nor an obstruction to directional bounds, richer references or other horizons",
            }
            # Degree n scales exactly as d^(-n-3); check against a separate
            # complete helper evaluation at the new floor before using tails.
            local_degrees = [value*(F(domain["distance_floors_m"][body])/F(local_floor))**(n+3)
                             for n, value in enumerate(degree_bounds)]
            assert sum(local_degrees, F(0)) == local_jacobian
            local_values = [F(endpoint["outgoing_error_m_m_s"][1])
                            + sum(local_degrees[cutoff+1:], F(0))*displacement_rate*h*h/2
                            for cutoff in range(spec.degree+1)]
            assert all(a >= b for a, b in zip(local_values, local_values[1:]))
            first = next(n for n, value in enumerate(local_values) if value <= F("0.000001"))
            local_geometry[body]["first_fitting_omitted_prefix_counterfactual"] = first
            local_geometry[body]["counterfactual_velocity_m_s_approx"] = float(local_values[first])
            if first:
                assert local_values[first-1] > F("0.000001")
                local_geometry[body]["preceding_counterfactual_velocity_m_s_approx"] = float(local_values[first-1])
            c20 = _c20_spatial_jacobian_bound_s_inv2(
                field.gravitational_parameter, field.reference_radius, domain["distance_floors_m"][body], float(nonmonopole[2, 0]),
            )
            remainder = nonmonopole.copy()
            remainder[2, 0] = 0.0
            remaining_degree = _nonmonopole_degree_map_bound_s_inv2(
                budget, field.gravitational_parameter, field.reference_radius, domain["distance_floors_m"][body], remainder, sine,
            )
            # Ideal exterior harmonic Hessian is symmetric and trace-free;
            # apply the factor to a Frobenius bound, never to an operator bound.
            remaining_frobenius = _harmonic_spatial_jacobian_bound_s_inv2(
                budget, field.gravitational_parameter, field.reference_radius, domain["distance_floors_m"][body], remainder, sine,
            )
            remaining = min(remaining_degree, _tracefree_operator_bound_s_inv2(remaining_frobenius))
            selected = min(jacobian, c20+remaining)
            incoming = F(endpoint["outgoing_error_m_m_s"][1])
            gate = F("0.000001")
            prefix_rows = []
            for cutoff in range(spec.degree+1):
                # Subtract only from this EXACT additive degree ledger, not
                # unrelated upper bounds; omitted degrees are hypothetical.
                tail = sum(degree_bounds[cutoff+1:], F(0))
                value = incoming+tail*displacement_rate*h*h/2
                prefix_rows.append({"cutoff": cutoff, "tail_jacobian_upper_s_inv2": upper(tail),
                                    "optimistic_velocity_m_s_approx": float(value), "fits": value <= gate})
            assert all(a["tail_jacobian_upper_s_inv2"] >= b["tail_jacobian_upper_s_inv2"] for a, b in zip(prefix_rows, prefix_rows[1:]))
            assert prefix_rows[-1]["fits"] and sum(degree_bounds[spec.degree+1:], F(0)) == 0
            degree_report = {
                "input_sha256": hashes, "coefficient_sha256": spec.expected_sha256,
                "body": body, "degree": spec.degree, "distance_floor_m": domain["distance_floors_m"][body],
                "degree_jacobian_upper_s_inv2": list(map(upper, degree_bounds)),
                "degree2_share_of_additive_bound_approx": float(degree_bounds[2]/jacobian),
                "c20_operator_upper_s_inv2": upper(c20), "without_c20_operator_upper_s_inv2": upper(remaining),
                "selected_full_nonmonopole_operator_upper_s_inv2": upper(selected),
                "selected_translation_rate_upper_m_s3": upper(selected*displacement_rate),
                "selected_optimistic_velocity_m_s_approx": float(incoming+selected*displacement_rate*h*h/2),
                "without_c20_optimistic_velocity_m_s_approx": float(incoming+remaining*displacement_rate*h*h/2),
                "selected_fits": incoming+selected*displacement_rate*h*h/2 <= gate,
                "without_c20_fits": incoming+remaining*displacement_rate*h*h/2 <= gate,
                "prefix_counterfactuals": prefix_rows, "elapsed_s": perf_counter()-degree_started,
                "scope": "Mars-only conditional bound attribution; omitted C20/prefixes are counterfactual accounting, not force removal, a selected reference, true-error lower bounds or complete residual/rotation qualification",
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
    assert degree_report is not None
    print(json.dumps({"fourth_mars_translation_degree_audit": degree_report}, sort_keys=True, allow_nan=False))
    local_velocity = F(endpoint["outgoing_error_m_m_s"][1])+local_total*h*h/2
    budget.check()
    print(json.dumps({"fourth_conditional_local_translation": {
        "input_sha256": hashes, "bodies": local_geometry, "duration_s": float(h),
        "reference_acceleration_cap_m_s2": float(acceleration),
        "translation_rate_upper_m_s3": upper(local_total),
        "optimistic_velocity_m_s_approx": float(local_velocity), "fits": local_velocity <= F("0.000001"),
        "additional_ephemeris_queries": 0, "additional_native_arcs": 0,
        "scope": "Conditional reference-relative balls and translation chords only; not true-state tubes, full-force sensitivities, source/native arithmetic, rotation, selected reference or actual-error lower bounds; omitted prefixes remain counterfactual",
    }}, sort_keys=True, allow_nan=False))
    assert method_report is not None
    print(json.dumps({"fourth_isotropic_translation_method_limit": method_report}, sort_keys=True, allow_nan=False))
