from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tomllib

import numpy as np

from space_nav import trajectory

from space_nav.scenario import load_scenario
from space_nav.transfer import search_impulsive_transfers


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "examples" / "reference_mission.toml"
PROVISIONAL = ROOT / "examples" / "m3_feasible_mission.toml"


def test_provisional_fixture_changes_only_dry_mass() -> None:
    reference_raw = tomllib.loads(REFERENCE.read_text(encoding="utf-8"))
    provisional_raw = tomllib.loads(PROVISIONAL.read_text(encoding="utf-8"))
    assert reference_raw["spacecraft"]["dry_mass_kg"] == 1000.0
    assert provisional_raw["spacecraft"]["dry_mass_kg"] == 500.0
    provisional_raw["spacecraft"]["dry_mass_kg"] = 1000.0
    assert provisional_raw == reference_raw

    reference = load_scenario(REFERENCE)
    provisional = load_scenario(PROVISIONAL)
    assert provisional == replace(
        reference,
        spacecraft=replace(reference.spacecraft, dry_mass_kg=500.0),
    )


def test_provisional_fixture_changes_budget_flag_not_candidate_physics() -> None:
    reference = search_impulsive_transfers(load_scenario(REFERENCE))
    provisional = search_impulsive_transfers(load_scenario(PROVISIONAL))
    reference_candidate = next(
        candidate for candidate in reference.pareto_front
        if candidate.candidate_id == "d0001-t0035"
    )
    provisional_candidate = next(
        candidate for candidate in provisional.pareto_front
        if candidate.candidate_id == "d0001-t0035"
    )

    # Exact equality covers every epoch, vector, delta-v, and ideal mass.
    # This tests the M2 budget filter, not finite-burn convergence.
    assert reference_candidate.mass_feasible is False
    assert provisional_candidate.mass_feasible is True
    assert provisional_candidate == replace(
        reference_candidate, mass_feasible=True,
    )
    assert 500.0 <= provisional_candidate.final_mass_kg < 1000.0

    scenario = load_scenario(PROVISIONAL)
    moon_gm = trajectory.MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2
    mars_gm = trajectory.MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2
    controls = trajectory._build_initial_burn_controls(
        scenario, provisional_candidate, moon_gm, mars_gm,
    )
    assert isinstance(controls, tuple) and len(controls) == 6
    assert controls == trajectory._build_initial_burn_controls(
        scenario, provisional_candidate, moon_gm, mars_gm,
    )
    assert trajectory._build_initial_burn_controls(
        load_scenario(REFERENCE), reference_candidate, moon_gm, mars_gm,
    ) == "rejected-dry-mass"
    # Independent direct native conversion and cross-product reconstruction.
    from tudatpy.astro import element_conversion

    for offset, orbit, radius_m, gm_m3_s2, excess, sign in (
        (0, scenario.departure_orbit, 1737400.0, moon_gm,
         provisional_candidate.departure_v_infinity_m_s, 1.0),
        (3, scenario.target_orbit, 3389500.0, mars_gm,
         provisional_candidate.arrival_v_infinity_m_s, -1.0),
    ):
        state = np.asarray(element_conversion.keplerian_to_cartesian(
            np.asarray([
                radius_m + (orbit.periapsis_altitude_m + orbit.apoapsis_altitude_m) / 2,
                orbit.eccentricity, orbit.inclination_rad, orbit.argument_of_periapsis_rad,
                orbit.raan_rad, orbit.true_anomaly_rad,
            ]), gm_m3_s2,
        )).reshape(6)
        tangent = state[3:] / np.linalg.norm(state[3:])
        normal_axis = np.cross(state[:3], state[3:])
        normal_axis /= np.linalg.norm(normal_axis)
        inward = np.cross(normal_axis, tangent)
        azimuth_rad, elevation_rad = controls[offset:offset + 2]
        actual = (
            np.cos(elevation_rad) * np.cos(azimuth_rad) * tangent
            + np.cos(elevation_rad) * np.sin(azimuth_rad) * inward
            + np.sin(elevation_rad) * normal_axis
        )
        expected = sign * np.asarray(excess) / np.linalg.norm(excess)
        assert np.linalg.norm(actual - expected) <= 1e-12
