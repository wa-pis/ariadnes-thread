from __future__ import annotations

import math

import numpy as np
import pytest

from space_nav import ephemeris, trajectory


@pytest.mark.parametrize("tighter", [False, True])
@pytest.mark.parametrize("eccentricity", [0.0, 0.2])
def test_ten_orbit_point_mass_conservation(
    tighter: bool, eccentricity: float,
) -> None:
    """Test-only fixed Sun at SSB; not a conservation claim for the mission."""
    from tudatpy import dynamics
    from tudatpy.dynamics import environment_setup, propagation_setup

    mu_m3_s2 = ephemeris._get_body_gravitational_parameter("Sun")
    semimajor_axis_m = 149_597_870_700.0
    periapsis_m = semimajor_axis_m * (1.0 - eccentricity)
    speed_m_s = math.sqrt(mu_m3_s2 * (2.0 / periapsis_m - 1.0 / semimajor_axis_m))
    period_s = 2.0 * math.pi * math.sqrt(semimajor_axis_m**3 / mu_m3_s2)
    final_epoch_tdb_s = 10.0 * period_s
    inclination_rad = math.pi / 6.0
    initial_state = np.asarray([
        periapsis_m, 0.0, 0.0, 0.0,
        speed_m_s * math.cos(inclination_rad),
        speed_m_s * math.sin(inclination_rad),
    ])
    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Sun")
    settings.get("Sun").ephemeris_settings = environment_setup.ephemeris.constant(
        np.zeros(6), "SSB", "J2000",
    )
    settings.get("Sun").gravity_field_settings = environment_setup.gravity_field.central(
        mu_m3_s2,
    )
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = 2000.0
    bodies = environment_setup.create_system_of_bodies(settings)

    accelerations = propagation_setup.create_acceleration_models(
        bodies, {"Spacecraft": {"Sun": [
            propagation_setup.acceleration.point_mass_gravity(),
        ]}}, ["Spacecraft"], ["SSB"],
    )
    integrator = trajectory._build_arc_integrator(
        "conservative-control", "coast", tighter=tighter,
    )
    termination = propagation_setup.propagator.time_termination(
        final_epoch_tdb_s, terminate_exactly_on_final_condition=True,
    )
    coupled = trajectory._build_coupled_arc_settings(
        "conservative-control", bodies, accelerations, initial_state,
        2000.0, 0.0, integrator, termination, thrust_enabled=False,
    )
    simulator = dynamics.simulator.create_dynamics_simulator(bodies, coupled)
    trajectory._read_completed_arc_state(
        "conservative-control", "coast", simulator, final_epoch_tdb_s,
    )
    history = simulator.state_history
    epochs = np.asarray(sorted(history))
    states = np.asarray([history[epoch] for epoch in epochs]).reshape(-1, 7)
    assert epochs[0] == 0.0
    assert abs(epochs[-1] - final_epoch_tdb_s) <= 1e-6
    assert np.all(np.isfinite(states))
    assert np.all(states[:, 6] == 2000.0)
    positions_m = states[:, :3]
    velocities_m_s = states[:, 3:6]
    energy_m2_s2 = (
        np.sum(velocities_m_s**2, axis=1) / 2.0
        - mu_m3_s2 / np.linalg.norm(positions_m, axis=1)
    )
    momentum_m2_s = np.linalg.norm(np.cross(positions_m, velocities_m_s), axis=1)
    expected_energy_m2_s2 = -mu_m3_s2 / (2.0 * semimajor_axis_m)
    expected_momentum_m2_s = math.sqrt(
        mu_m3_s2 * semimajor_axis_m * (1.0 - eccentricity**2),
    )
    energy_drift = float(np.max(np.abs(energy_m2_s2 / expected_energy_m2_s2 - 1.0)))
    momentum_drift = float(np.max(np.abs(momentum_m2_s / expected_momentum_m2_s - 1.0)))
    assert energy_drift <= 1e-11, energy_drift
    assert momentum_drift <= 1e-11, momentum_drift
