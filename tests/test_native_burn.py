"""Isolated Tudat engine qualification, not the production M3 propagator."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from fractions import Fraction
from typing import Any, Literal

import pytest


@pytest.mark.parametrize("duration_s", [0.25, 100.25])
@pytest.mark.parametrize("burn_id", ["inertial", "departure", "arrival"])
@pytest.mark.parametrize("integration", ["rk4", "nominal", "tighter"])
@pytest.mark.parametrize("initial_mass_kg", [2000.0, 1500.0])
def test_native_engine_couples_translation_and_mass(
    duration_s: float, burn_id: Literal["inertial", "departure", "arrival"],
    monkeypatch: pytest.MonkeyPatch,
    integration: Literal["rk4", "nominal", "tighter"],
    initial_mass_kg: float,
) -> None:
    import numpy as np
    from tudatpy.dynamics import environment_setup, propagation_setup
    from space_nav import trajectory

    thrust_n = 1000.0
    isp_s = 450.0
    g0_m_s2 = 9.80665

    def direction(epoch_tdb_s: float) -> tuple[float, float, float]:
        return (0.0, 1.0, 0.0)

    def thrust(epoch_tdb_s: float) -> float:
        return thrust_n

    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    # The propagated handoff mass must override the body's original mass.
    settings.get("Spacecraft").constant_mass = 2000.0
    initial_state = np.zeros(6)
    central_body = "Moon" if burn_id == "departure" else "Mars"
    if burn_id != "inertial":
        # Synthetic inertial reference, not a substitute for mission ephemerides.
        # Tiny gravity forces native central-state updates; its integrated speed
        # effect is below 4e-11 m/s for these <=101 s, >=1.8e6 m fixtures.
        for name in ("Moon", "Mars"):
            settings.add_empty_settings(name)
            position_m = 4e7 if name == central_body else -8e7
            settings.get(name).ephemeris_settings = (
                environment_setup.ephemeris.constant(
                    np.asarray([position_m, 0.0, 0.0, 0.0, 0.0, 0.0]),
                    "SSB", "J2000",
                )
            )
            settings.get(name).gravity_field_settings = (
                environment_setup.gravity_field.central(1.0)
            )
        initial_state = np.asarray([4e7 + 1.8e6, 0.0, 0.0, 0.0, 1500.0, 0.0])
    settings.get("Spacecraft").rotation_model_settings = (
        environment_setup.rotation_model.custom_inertial_direction_based(
            direction, "J2000", "VehicleFixed",
        )
    )
    bodies = environment_setup.create_system_of_bodies(settings)
    directions: list[tuple[float, float, float]] = []
    direction_errors: list[float] = []
    if burn_id != "inertial":
        guidance = trajectory._build_tnw_direction_callback(
            "native-burn-control", bodies, burn_id, 0.4, 0.2,
        )

        def record_direction(epoch_tdb_s: float) -> tuple[float, float, float]:
            value = guidance(epoch_tdb_s)
            directions.append(value)
            relative = np.asarray(
                bodies.get("Spacecraft").state - bodies.get(central_body).state,
            ).reshape(6)
            tangent = relative[3:] / np.linalg.norm(relative[3:])
            normal_axis = np.cross(relative[:3], relative[3:])
            normal_axis /= np.linalg.norm(normal_axis)
            inward = np.cross(normal_axis, tangent)
            expected = (
                math.cos(0.2) * math.cos(0.4) * tangent
                + math.cos(0.2) * math.sin(0.4) * inward
                + math.sin(0.2) * normal_axis
            )
            direction_errors.append(float(np.linalg.norm(value - expected)))
            return value

        # Record the real guidance callback while exercising production setup.
        def record_factory(
            candidate_id: object, supplied_bodies: Any,
            supplied_burn: Literal["departure", "arrival"],
            azimuth_rad: object, elevation_rad: object,
        ) -> Callable[[float], tuple[float, float, float]]:
            assert candidate_id == "native-burn-control"
            assert supplied_bodies is bodies and supplied_burn == burn_id
            assert (azimuth_rad, elevation_rad) == (0.4, 0.2)
            return record_direction

        monkeypatch.setattr(
            trajectory, "_build_tnw_direction_callback", record_factory,
        )
        from space_nav.models import SpacecraftSpec

        spacecraft = SpacecraftSpec(
            initial_mass_kg=initial_mass_kg, dry_mass_kg=1000.0,
            max_thrust_n=thrust_n, isp_s=isp_s, srp_area_m2=20.0,
            reflectivity_coefficient=1.3, maneuver_magnitude_sigma_fraction=0.001,
            maneuver_pointing_sigma_rad=0.001,
        )
        engine_name = trajectory._install_tnw_engine(
            "native-burn-control", bodies, spacecraft, burn_id, 0.4, 0.2,
        )
        assert engine_name == f"{burn_id}-main"
    else:
        engine_name = "main"
        environment_setup.add_engine_model(
            "Spacecraft", engine_name,
            propagation_setup.thrust.custom_thrust_magnitude_fixed_isp(thrust, isp_s),
            bodies, np.asarray([1.0, 0.0, 0.0]),
        )
    acceleration_settings = {
        "Spacecraft": {
            "Spacecraft": [
                propagation_setup.acceleration.thrust_from_engine(engine_name),
            ],
        },
    }
    if burn_id != "inertial":
        acceleration_settings["Spacecraft"][central_body] = [
            propagation_setup.acceleration.point_mass_gravity(),
        ]
    accelerations = propagation_setup.create_acceleration_models(
        bodies, acceleration_settings,
        ["Spacecraft"], ["SSB"],
    )
    if integration == "rk4":
        integrator = propagation_setup.integrator.runge_kutta_fixed_step(
            0.1, propagation_setup.integrator.CoefficientSets.rk_4,
        )
    else:
        integrator = trajectory._build_arc_integrator(
            "native-burn-control",
            "arrival-burn" if burn_id == "arrival" else "departure-burn",
            tighter=integration == "tighter",
        )
    termination = propagation_setup.propagator.time_termination(
        duration_s, terminate_exactly_on_final_condition=True,
    )
    coupled = trajectory._build_coupled_arc_settings(
        "native-burn-control", bodies, accelerations, initial_state,
        initial_mass_kg, 0.0, integrator, termination, thrust_enabled=True,
    )
    budget = trajectory._RefinementBudget("native-burn-control", 300.0)
    budget.begin_control()
    simulator = trajectory._run_native_arc(
        budget, bodies, coupled, first_in_evaluation=True,
    )
    assert (budget.control_attempts, budget.propagation_evaluations,
            budget.native_arc_propagations) == (1, 1, 1)
    assert simulator.integration_completed_successfully
    history = simulator.state_history
    final_epoch_tdb_s = max(history)
    assert abs(float(final_epoch_tdb_s) - duration_s) <= 1e-6
    cartesian, mass_kg = trajectory._read_completed_arc_state(
        "native-burn-control",
        "arrival-burn" if burn_id == "arrival" else "departure-burn",
        simulator, duration_s,
    )
    final = np.asarray((*cartesian, mass_kg))
    assert final.shape == (7,)
    assert np.all(np.isfinite(final))

    consumed_mass_kg = thrust_n * duration_s / (g0_m_s2 * isp_s)
    expected_mass_kg = initial_mass_kg - consumed_mass_kg
    assert abs(final[6] - expected_mass_kg) <= max(
        1e-8, 1e-11 * consumed_mass_kg,
    )
    expected_delta_v_m_s = g0_m_s2 * isp_s * math.log(
        initial_mass_kg / expected_mass_kg,
    )
    if burn_id == "inertial":
        assert np.linalg.norm(
            final[3:6] - np.asarray([0.0, expected_delta_v_m_s, 0.0]),
        ) <= 1e-6
    else:
        # Independent invariant: d|v|/dt = T/m * cos(e)cos(a).
        expected_speed_m_s = (
            1500.0 + math.cos(0.2) * math.cos(0.4) * expected_delta_v_m_s
        )
        assert abs(np.linalg.norm(final[3:6]) - expected_speed_m_s) <= 1e-6
        assert directions and np.all(np.isfinite(directions))
        assert np.linalg.norm(
            np.asarray(directions[-1]) - directions[0],
        ) > 1e-6
        assert np.max(np.abs(
            np.linalg.norm(directions, axis=1) - 1.0,
        )) <= 1e-12
        assert max(direction_errors) <= 1e-12
    assert all(float(np.asarray(state).reshape(-1)[6]) > 1000.0
               for state in history.values())

    # Use exact stored-input arithmetic at each saved epoch, not a rounded
    # final-mass oracle. These are samples, not an inter-step enclosure.
    exact_rate_kg_s = Fraction(thrust_n) / (Fraction(g0_m_s2) * Fraction(isp_s))
    unit_roundoff = Fraction(1, 2**53)
    relative_rate_bound = 2 * unit_roundoff / (1 - unit_roundoff)
    largest_error_kg = Fraction(0)
    outside_rate_only_bound = 0
    previous_mass_kg = initial_mass_kg
    for epoch_tdb_s, state in sorted(history.items()):
        elapsed_s = Fraction(float(epoch_tdb_s))  # This fixture ignites at TDB 0 s.
        assert 0 <= elapsed_s <= Fraction(duration_s) + Fraction(1e-6)
        sample = np.asarray(state).reshape(-1)
        assert sample.shape == (7,) and np.all(np.isfinite(sample))
        sample_mass_kg = float(sample[6])
        assert sample_mass_kg <= previous_mass_kg
        previous_mass_kg = sample_mass_kg
        exact_consumed_kg = exact_rate_kg_s * elapsed_s
        exact_mass_kg = Fraction(initial_mass_kg) - exact_consumed_kg
        error_kg = abs(Fraction(sample_mass_kg) - exact_mass_kg)
        assert error_kg <= max(Fraction(1e-8), Fraction(1e-11) * exact_consumed_kg)
        largest_error_kg = max(largest_error_kg, error_kg)
        rate_only_bound_kg = exact_consumed_kg * relative_rate_bound
        outside_rate_only_bound += error_kg > rate_only_bound_kg
    # Preserve a counterexample to using the Python rate bound as a bound on
    # native propagated mass (which also includes other arithmetic errors).
    assert outside_rate_only_bound > 0
    print(json.dumps({
        "burn_id": burn_id,
        "duration_s": duration_s,
        "initial_mass_kg": initial_mass_kg,
        "integration": integration,
        "saved_states": len(history),
        "maximum_sampled_mass_error_kg": float(largest_error_kg),
        "samples_outside_python_rate_only_bound": outside_rate_only_bound,
        "scope": "isolated saved-state mass evidence, not interval safety",
    }, sort_keys=True, allow_nan=False))
