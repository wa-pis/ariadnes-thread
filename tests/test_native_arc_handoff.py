"""Isolated three-arc qualification, not a safe full-force mission executor."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
import pytest

from space_nav import trajectory
from space_nav.models import SpacecraftSpec


@pytest.mark.parametrize("tighter", [False, True])
@pytest.mark.parametrize("coast_duration_s", [0.25, 1000.5])
def test_three_native_arcs_preserve_state_and_mass_handoff(
    tighter: bool, coast_duration_s: float,
) -> None:
    from tudatpy.dynamics import environment_setup, propagation_setup

    candidate_id = "three-arc-control"
    spacecraft = SpacecraftSpec(
        initial_mass_kg=2000.0, dry_mass_kg=1000.0, max_thrust_n=1000.0,
        isp_s=450.0, srp_area_m2=20.0, reflectivity_coefficient=1.3,
        maneuver_magnitude_sigma_fraction=0.001, maneuver_pointing_sigma_rad=0.001,
    )
    budget = trajectory._RefinementBudget(candidate_id, 300.0)
    budget.begin_control()
    settings = environment_setup.BodyListSettings("SSB", "J2000")
    settings.add_empty_settings("Spacecraft")
    settings.get("Spacecraft").constant_mass = spacecraft.initial_mass_kg
    # Test-only stationary references, never replacements for mission SPICE.
    # GM=1 forces native central-state updates. At r >= 1.8e6 m, the two
    # sources perturb velocity by < 1e-9 m/s over this < 1200 s fixture.
    for name, position_m in (("Moon", 4e7), ("Mars", -8e7)):
        settings.add_empty_settings(name)
        settings.get(name).ephemeris_settings = environment_setup.ephemeris.constant(
            np.asarray([position_m, 0.0, 0.0, 0.0, 0.0, 0.0]), "SSB", "J2000",
        )
        settings.get(name).gravity_field_settings = (
            environment_setup.gravity_field.central(1.0)
        )

    state = (4e7 + 1.8e6, 0.0, 0.0, 0.0, 1500.0, 0.0)
    mass_kg = 1500.0  # Deliberately different from each fresh body's 2000 kg.
    epoch_tdb_s = 1_000_000_000.0
    expected_mass_kg, expected_y_m, expected_vy_m_s = mass_kg, 0.0, 1500.0
    exhaust_m_s = 9.80665 * spacecraft.isp_s
    mass_rate_kg_s = spacecraft.max_thrust_n / exhaust_m_s
    arcs: tuple[
        tuple[Literal["departure-burn", "coast", "arrival-burn"],
              Literal["departure", "arrival"] | None, float], ...
    ] = (
        ("departure-burn", "departure", 100.25),
        ("coast", None, coast_duration_s),
        ("arrival-burn", "arrival", 50.25),
    )
    for index, (arc, burn_id, duration_s) in enumerate(arcs):
        bodies = environment_setup.create_system_of_bodies(settings)
        assert bodies.get("Spacecraft").mass == 2000.0
        force_settings = {
            name: [propagation_setup.acceleration.point_mass_gravity()]
            for name in ("Moon", "Mars")
        }
        if burn_id is not None:
            engine = trajectory._install_tnw_engine(
                candidate_id, bodies, spacecraft, burn_id,
                0.0 if burn_id == "departure" else -math.pi, 0.0,
            )
            force_settings["Spacecraft"] = [
                propagation_setup.acceleration.thrust_from_engine(engine),
            ]
        accelerations = propagation_setup.create_acceleration_models(
            bodies, {"Spacecraft": force_settings}, ["Spacecraft"], ["SSB"],
        )
        final_epoch_tdb_s = epoch_tdb_s + duration_s
        coupled = trajectory._build_coupled_arc_settings(
            candidate_id, bodies, accelerations, state, mass_kg, epoch_tdb_s,
            trajectory._build_arc_integrator(candidate_id, arc, tighter=tighter),
            propagation_setup.propagator.time_termination(
                final_epoch_tdb_s, terminate_exactly_on_final_condition=True,
            ),
            thrust_enabled=burn_id is not None,
        )
        simulator = trajectory._run_native_arc(
            budget, bodies, coupled, first_in_evaluation=index == 0,
        )
        final_state, final_mass_kg = trajectory._read_completed_arc_state(
            candidate_id, arc, simulator, final_epoch_tdb_s,
        )
        history = simulator.state_history
        initial = np.asarray(history[min(history)]).reshape(7)
        assert abs(min(history) - epoch_tdb_s) <= 1e-6
        assert np.linalg.norm(initial[:3] - state[:3]) <= 1e-3
        assert np.linalg.norm(initial[3:6] - state[3:]) <= 1e-6
        assert abs(initial[6] - mass_kg) <= 1e-9

        # Independent closed-form position integral and signed rocket equation.
        expected_y_m += expected_vy_m_s * duration_s
        if burn_id is None:
            assert all(float(np.asarray(value).reshape(7)[6]) == mass_kg
                       for value in history.values())
        else:
            sign = 1.0 if burn_id == "departure" else -1.0
            new_mass_kg = expected_mass_kg - mass_rate_kg_s * duration_s
            log_ratio = math.log(expected_mass_kg / new_mass_kg)
            expected_y_m += sign * exhaust_m_s * (
                duration_s - new_mass_kg / mass_rate_kg_s * log_ratio
            )
            expected_vy_m_s += sign * exhaust_m_s * log_ratio
            expected_mass_kg = new_mass_kg
        assert np.linalg.norm(
            np.asarray(final_state[:3]) - [4e7 + 1.8e6, expected_y_m, 0.0],
        ) <= 1e-3
        assert np.linalg.norm(
            np.asarray(final_state[3:]) - [0.0, expected_vy_m_s, 0.0],
        ) <= 1e-6
        assert abs(final_mass_kg - expected_mass_kg) <= 1e-8
        assert all(float(np.asarray(value).reshape(7)[6]) > spacecraft.dry_mass_kg
                   for value in history.values())
        assert budget.propagation_evaluations == 1
        assert budget.native_arc_propagations == index + 1
        state, mass_kg, epoch_tdb_s = final_state, final_mass_kg, final_epoch_tdb_s
    assert budget.control_attempts == 1
