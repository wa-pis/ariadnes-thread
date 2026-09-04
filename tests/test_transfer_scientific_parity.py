from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from typing import Any

import pytest

from space_nav.models import OrbitSpec, Scenario
from space_nav.scenario import load_scenario
from space_nav import transfer


REFERENCE_SCENARIO = Path(__file__).parents[1] / "examples" / "reference_mission.toml"


def _real_scenario(candidate_budget: int) -> Scenario:
    scenario = load_scenario(REFERENCE_SCENARIO)
    return replace(
        scenario,
        limits=replace(
            scenario.limits,
            max_candidates=candidate_budget,
            runtime_seconds=60.0,
        ),
    )


def _explicit_patched_conic_burn(
    gravitational_parameter_m3_s2: float,
    reference_radius_m: float,
    orbit: OrbitSpec,
    excess_speed_m_s: float,
) -> float:
    periapsis_radius_m = reference_radius_m + orbit.periapsis_altitude_m
    apoapsis_radius_m = reference_radius_m + orbit.apoapsis_altitude_m
    semi_major_axis_m = (periapsis_radius_m + apoapsis_radius_m) / 2.0
    hyperbolic_speed_m_s = math.sqrt(
        excess_speed_m_s**2
        + 2.0 * gravitational_parameter_m3_s2 / periapsis_radius_m
    )
    orbital_speed_m_s = math.sqrt(
        gravitational_parameter_m3_s2
        * (2.0 / periapsis_radius_m - 1.0 / semi_major_axis_m)
    )
    return abs(hyperbolic_speed_m_s - orbital_speed_m_s)


def test_one_candidate_matches_direct_pinned_tudatpy_and_spice() -> None:
    pytest.importorskip("tudatpy")
    import numpy as np
    from tudatpy.astro import two_body_dynamics
    from tudatpy.interface import spice

    scenario = _real_scenario(candidate_budget=1)

    # Production search performs normal lazy initialization. The direct oracle
    # then reuses that process-global kernel pool without forcing a reload.
    result = transfer.search_impulsive_transfers(scenario)
    assert result.evaluated_candidates == result.solved_candidates == 1
    assert result.failed_candidates == 0
    candidate = result.pareto_front[0]

    departure_start_tdb_s = float(
        spice.convert_date_string_to_ephemeris_time(
            scenario.search.departure_start_utc
        )
    )
    departure_end_tdb_s = float(
        spice.convert_date_string_to_ephemeris_time(scenario.search.departure_end_utc)
    )
    departure_tdb_s = (departure_start_tdb_s + departure_end_tdb_s) / 2.0
    flight_time_s = (
        scenario.search.time_of_flight_min_s
        + scenario.search.time_of_flight_max_s
    ) / 2.0
    arrival_tdb_s = departure_tdb_s + flight_time_s

    def direct_state(body: str, epoch_tdb_s: float) -> Any:
        return np.asarray(
            spice.get_body_cartesian_state_at_epoch(
                target_body_name=body,
                observer_body_name="SSB",
                reference_frame_name="J2000",
                aberration_corrections="NONE",
                ephemeris_time=epoch_tdb_s,
            ),
            dtype=float,
        )

    moon = direct_state("Moon", departure_tdb_s)
    departure_sun = direct_state("Sun", departure_tdb_s)
    mars = direct_state("Mars", arrival_tdb_s)
    arrival_sun = direct_state("Sun", arrival_tdb_s)
    moon_heliocentric = moon - departure_sun
    mars_heliocentric = mars - arrival_sun

    mu_sun = float(spice.get_body_gravitational_parameter("Sun"))
    direct_departure_velocity, direct_arrival_velocity = (
        two_body_dynamics.ZeroRevolutionLambertTargeterIzzo(
            moon_heliocentric[:3],
            mars_heliocentric[:3],
            flight_time_s,
            mu_sun,
            is_retrograde=False,
            tolerance=1e-9,
            max_iter=50,
        ).get_velocity_vectors()
    )
    expected_departure_v_infinity = np.asarray(direct_departure_velocity) - (
        moon_heliocentric[3:]
    )
    expected_arrival_v_infinity = np.asarray(direct_arrival_velocity) - (
        mars_heliocentric[3:]
    )

    assert candidate.candidate_id == "d0000-t0000"
    assert candidate.departure_epoch_tdb_s == departure_tdb_s
    assert candidate.arrival_epoch_tdb_s == arrival_tdb_s
    assert candidate.flight_time_s == flight_time_s
    assert (
        np.linalg.norm(
            np.asarray(candidate.departure_v_infinity_m_s)
            - expected_departure_v_infinity
        )
        <= 1e-6
    )
    assert (
        np.linalg.norm(
            np.asarray(candidate.arrival_v_infinity_m_s)
            - expected_arrival_v_infinity
        )
        <= 1e-6
    )

    expected_departure_burn = _explicit_patched_conic_burn(
        float(spice.get_body_gravitational_parameter("Moon")),
        1_737_400.0,
        scenario.departure_orbit,
        float(np.linalg.norm(expected_departure_v_infinity)),
    )
    expected_arrival_burn = _explicit_patched_conic_burn(
        float(spice.get_body_gravitational_parameter("Mars")),
        3_389_500.0,
        scenario.target_orbit,
        float(np.linalg.norm(expected_arrival_v_infinity)),
    )
    assert candidate.departure_delta_v_m_s == pytest.approx(
        expected_departure_burn, abs=1e-6
    )
    assert candidate.arrival_delta_v_m_s == pytest.approx(
        expected_arrival_burn, abs=1e-6
    )


def test_small_real_search_is_reproducible_and_ignores_deferred_fields() -> None:
    pytest.importorskip("tudatpy")
    scenario = _real_scenario(candidate_budget=4)
    changed = replace(
        scenario,
        departure_orbit=replace(
            scenario.departure_orbit,
            inclination_rad=0.1,
            raan_rad=0.2,
            argument_of_periapsis_rad=0.3,
            true_anomaly_rad=0.4,
        ),
        target_orbit=replace(
            scenario.target_orbit,
            inclination_rad=0.5,
            raan_rad=0.6,
            argument_of_periapsis_rad=0.7,
            true_anomaly_rad=0.8,
        ),
        spacecraft=replace(
            scenario.spacecraft,
            max_thrust_n=2.0,
            srp_area_m2=3.0,
            reflectivity_coefficient=4.0,
            maneuver_magnitude_sigma_fraction=0.02,
            maneuver_pointing_sigma_rad=0.03,
        ),
        tracking=replace(
            scenario.tracking,
            stations=("IGNORED",),
            cadence_s=123.0,
            range_sigma_m=456.0,
            range_rate_sigma_m_s=0.7,
            angular_sigma_rad=0.8,
            min_elevation_rad=0.9,
        ),
        limits=replace(scenario.limits, random_seed=999),
    )

    first = transfer.search_impulsive_transfers(scenario)
    repeated = transfer.search_impulsive_transfers(scenario)
    deferred_changed = transfer.search_impulsive_transfers(changed)

    assert first.evaluated_candidates == first.solved_candidates == 4
    assert first.failed_candidates == 0
    assert first.pareto_front
    assert first == repeated == deferred_changed
