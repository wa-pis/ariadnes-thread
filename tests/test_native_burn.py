"""Isolated Tudat engine qualification, not the production M3 propagator."""

from __future__ import annotations

import math

import pytest


@pytest.mark.parametrize("duration_s", [0.25, 100.25])
def test_native_engine_couples_translation_and_mass(duration_s: float) -> None:
    import numpy as np
    from tudatpy import dynamics
    from tudatpy.dynamics import environment_setup, propagation_setup

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
    settings.get("Spacecraft").rotation_model_settings = (
        environment_setup.rotation_model.custom_inertial_direction_based(
            direction, "J2000", "VehicleFixed",
        )
    )
    bodies = environment_setup.create_system_of_bodies(settings)
    environment_setup.add_engine_model(
        "Spacecraft", "main",
        propagation_setup.thrust.custom_thrust_magnitude_fixed_isp(thrust, isp_s),
        bodies, np.asarray([1.0, 0.0, 0.0]),
    )
    accelerations = propagation_setup.create_acceleration_models(
        bodies,
        {"Spacecraft": {"Spacecraft": [
            propagation_setup.acceleration.thrust_from_engine("main"),
        ]}},
        ["Spacecraft"], ["SSB"],
    )
    mass_rates = propagation_setup.create_mass_rate_models(
        bodies,
        {"Spacecraft": [propagation_setup.mass_rate.from_thrust(True)]},
        accelerations,
    )
    # Fixed-step RK4 isolates the engine API; M3 adaptive settings are task 3.3.
    integrator = propagation_setup.integrator.runge_kutta_fixed_step(
        0.1, propagation_setup.integrator.CoefficientSets.rk_4,
    )
    termination = propagation_setup.propagator.time_termination(
        duration_s, terminate_exactly_on_final_condition=True,
    )
    translation = propagation_setup.propagator.translational(
        ["SSB"], accelerations, ["Spacecraft"], np.zeros(6),
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
    final = np.asarray(history[final_epoch_tdb_s]).reshape(-1)
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
    assert np.linalg.norm(
        final[3:6] - np.asarray([0.0, expected_delta_v_m_s, 0.0]),
    ) <= 1e-6
    assert all(float(np.asarray(state).reshape(-1)[6]) > 1000.0
               for state in history.values())
