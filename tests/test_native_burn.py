"""Isolated Tudat engine qualification, not the production M3 propagator."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, Literal

import pytest


@pytest.mark.parametrize("duration_s", [0.25, 100.25])
@pytest.mark.parametrize("burn_id", ["inertial", "departure", "arrival"])
@pytest.mark.parametrize("integration", ["rk4", "nominal", "tighter"])
def test_native_engine_couples_translation_and_mass(
    duration_s: float, burn_id: Literal["inertial", "departure", "arrival"],
    monkeypatch: pytest.MonkeyPatch,
    integration: Literal["rk4", "nominal", "tighter"],
) -> None:
    import numpy as np
    from tudatpy import dynamics
    from tudatpy.dynamics import environment_setup, propagation_setup
    from space_nav import trajectory

    initial_mass_kg = 2000.0
    thrust_n = 1000.0
    isp_s = 450.0
    g0_m_s2 = 9.80665

    def direction(epoch_tdb_s: float) -> tuple[float, float, float]:
        return (0.0, 1.0, 0.0)

    def thrust(epoch_tdb_s: float) -> float:
        return thrust_n

    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = initial_mass_kg
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
    mass_rates = propagation_setup.create_mass_rate_models(
        bodies,
        {"Spacecraft": [propagation_setup.mass_rate.from_thrust(True)]},
        accelerations,
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
    translation = propagation_setup.propagator.translational(
        ["SSB"], accelerations, ["Spacecraft"], initial_state,
        0.0, integrator, termination,
    )
    mass = propagation_setup.propagator.mass(
        ["Spacecraft"], mass_rates, np.asarray([initial_mass_kg]),
        0.0, integrator, termination,
    )
    coupled = propagation_setup.propagator.multitype(
        [translation, mass], integrator, 0.0, termination,
    )
    simulator = dynamics.simulator.create_dynamics_simulator(bodies, coupled)
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
