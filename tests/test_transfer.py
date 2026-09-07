from __future__ import annotations

from dataclasses import replace
from collections import Counter
from datetime import UTC, datetime, timedelta
import math
from pathlib import Path
from typing import NoReturn

import pytest

from space_nav.ephemeris import CartesianState
from space_nav.errors import EphemerisError, TransferSearchError
from space_nav.models import ImpulsiveTransferCandidate, Scenario
from space_nav.scenario import load_scenario
from space_nav import transfer


REFERENCE_SCENARIO = Path(__file__).parents[1] / "examples" / "reference_mission.toml"


def _candidate(
    candidate_id: str,
    flight_days: float,
    propellant_mass_kg: float,
    *,
    departure_day: int = 0,
    mass_feasible: bool = True,
) -> ImpulsiveTransferCandidate:
    departure = datetime(2031, 1, 1, tzinfo=UTC) + timedelta(days=departure_day)
    flight_time = flight_days * 86_400.0
    arrival = departure + timedelta(seconds=flight_time)
    departure_tdb = departure_day * 86_400.0
    return ImpulsiveTransferCandidate(
        candidate_id=candidate_id,
        departure_epoch_utc=departure.isoformat().replace("+00:00", "Z"),
        arrival_epoch_utc=arrival.isoformat().replace("+00:00", "Z"),
        departure_epoch_tdb_s=departure_tdb,
        arrival_epoch_tdb_s=departure_tdb + flight_time,
        flight_time_s=flight_time,
        departure_v_infinity_m_s=(1.0, 2.0, 3.0),
        arrival_v_infinity_m_s=(4.0, 5.0, 6.0),
        departure_delta_v_m_s=100.0,
        arrival_delta_v_m_s=200.0,
        total_delta_v_m_s=300.0,
        propellant_mass_kg=propellant_mass_kg,
        final_mass_kg=2000.0 - propellant_mass_kg,
        mass_feasible=mass_feasible,
    )


def _small_scenario(*, budget: int = 4, runtime_seconds: float = 30.0) -> Scenario:
    scenario = load_scenario(REFERENCE_SCENARIO)
    return replace(
        scenario,
        search=replace(
            scenario.search,
            time_of_flight_min_s=10.0,
            time_of_flight_max_s=20.0,
        ),
        limits=replace(
            scenario.limits,
            max_candidates=budget,
            runtime_seconds=runtime_seconds,
        ),
    )


def _utc_at(epoch_tdb_s: float) -> str:
    return (
        datetime(2031, 1, 1, tzinfo=UTC)
        .__add__(timedelta(seconds=epoch_tdb_s))
        .isoformat()
        .replace("+00:00", "Z")
    )


def _fake_state(body: str, epoch_tdb_s: float) -> CartesianState:
    positions = {
        "Sun": (0.0, 0.0, 0.0),
        "Moon": (100_000_000.0, 10_000_000.0, 2_000_000.0),
        "Mars": (200_000_000.0, 100_000_000.0, 20_000_000.0),
    }
    return CartesianState(
        body=body,
        epoch_utc=_utc_at(epoch_tdb_s),
        epoch_tdb_s=epoch_tdb_s,
        origin="SSB",
        orientation="J2000",
        position_m=positions[body],
        velocity_m_s=(0.0, 0.0, 0.0),
    )


def _fake_gm(body: str) -> float:
    return {"Sun": 1.32712440018e20, "Moon": 4.902800118e12, "Mars": 4.282837e13}[
        body
    ]


def _fake_lambert(
    departure_position: transfer.Vector3,
    arrival_position: transfer.Vector3,
    flight_time_s: float,
    gravitational_parameter: float,
) -> tuple[transfer.Vector3, transfer.Vector3]:
    return (1000.0, 20.0, 30.0), (500.0, -10.0, 40.0)


@pytest.mark.parametrize(
    ("budget", "shape", "attempts"),
    [(1, (1, 1), 1), (17, (4, 4), 16), (2000, (44, 45), 1980)],
)
def test_grid_is_bounded_closed_and_departure_major(
    budget: int, shape: tuple[int, int], attempts: int
) -> None:
    grid = list(transfer._candidate_grid(budget, 10.0, 20.0, 100.0, 200.0))

    assert transfer._grid_shape(budget) == shape
    assert len(grid) == attempts <= budget
    assert len({(departure, flight) for _, departure, flight in grid}) == attempts
    assert grid[0][0] == "d0000-t0000"
    assert grid[-1][0] == f"d{shape[0] - 1:04d}-t{shape[1] - 1:04d}"
    if budget == 1:
        assert grid == [("d0000-t0000", 15.0, 150.0)]
    else:
        assert {point[1] for point in grid} >= {10.0, 20.0}
        assert {point[2] for point in grid} >= {100.0, 200.0}


def test_grid_rejects_float_collisions_before_attempting_a_candidate() -> None:
    scenario = _small_scenario(budget=9)
    lower = 1_000_000_000.0
    upper = math.nextafter(lower, math.inf)
    solver_calls = 0

    def solver(*args: object) -> tuple[transfer.Vector3, transfer.Vector3]:
        nonlocal solver_calls
        solver_calls += 1
        return _fake_lambert(*args)  # type: ignore[arg-type]

    with pytest.raises(TransferSearchError, match=r"unique departure epochs.*widen"):
        transfer._search_impulsive_transfers(
            scenario,
            monotonic=lambda: 0.0,
            utc_to_tdb_fn=lambda epoch: (
                lower if epoch == scenario.search.departure_start_utc else upper
            ),
            state_query=_fake_state,
            gm_query=_fake_gm,
            lambert_solver=solver,
        )
    assert solver_calls == 0


def test_patched_conic_matches_energy_equation() -> None:
    scenario = load_scenario(REFERENCE_SCENARIO)
    cases = (
        (
            _fake_gm("Moon"),
            scenario.departure_orbit,
            transfer.MOON_REFERENCE_RADIUS_M,
            900.0,
        ),
        (
            _fake_gm("Mars"),
            scenario.target_orbit,
            transfer.MARS_REFERENCE_RADIUS_M,
            2_500.0,
        ),
    )
    for mu, orbit, radius, excess_speed in cases:
        semi_major_axis, _ = transfer._orbit_geometry(orbit, radius)
        periapsis_radius = radius + orbit.periapsis_altitude_m
        expected = abs(
            math.sqrt(excess_speed**2 + 2.0 * mu / periapsis_radius)
            - math.sqrt(mu * (2.0 / periapsis_radius - 1.0 / semi_major_axis))
        )
        assert transfer._patched_conic_delta_v(
            mu, orbit, radius, excess_speed
        ) == pytest.approx(expected, abs=1e-6)


def test_sequential_mass_accounting_is_exact_and_exposes_infeasibility() -> None:
    total, propellant, final_mass, feasible = transfer._mass_accounting(
        2000.0, 1000.0, 450.0, 1900.0, 1700.0
    )
    after_departure = 2000.0 * math.exp(
        -1900.0 / (transfer.STANDARD_GRAVITY_M_S2 * 450.0)
    )
    expected_final = after_departure * math.exp(
        -1700.0 / (transfer.STANDARD_GRAVITY_M_S2 * 450.0)
    )

    assert total == 3600.0
    assert final_mass == pytest.approx(expected_final, rel=1e-12)
    assert propellant == pytest.approx(2000.0 - expected_final, rel=1e-12)
    assert feasible is False


def test_pareto_is_exact_stable_and_keeps_mass_infeasible_points() -> None:
    candidates = [
        _candidate("d0000-t0000", 180.0, 500.0),
        _candidate("d0000-t0001", 200.0, 450.0),
        _candidate("d0000-t0002", 220.0, 470.0),
        _candidate("d0000-t0003", 240.0, 400.0, mass_feasible=False),
        _candidate("d0000-t0004", 260.0, 550.0),
        _candidate("d0001-t0000", 200.0, 450.0, departure_day=1),
    ]
    expected = ("d0000-t0000", "d0000-t0001", "d0000-t0003")

    assert tuple(item.candidate_id for item in transfer._pareto_front(candidates)) == expected
    assert tuple(
        item.candidate_id for item in transfer._pareto_front(list(reversed(candidates)))
    ) == expected


def test_search_caches_endpoints_counts_lambert_failures_and_ignores_seed() -> None:
    scenario = _small_scenario()
    calls: list[tuple[str, float]] = []
    solver_calls = 0

    def state_query(body: str, epoch: float) -> CartesianState:
        calls.append((body, epoch))
        return _fake_state(body, epoch)

    def lambert(*args: object) -> tuple[transfer.Vector3, transfer.Vector3]:
        nonlocal solver_calls
        solver_calls += 1
        if solver_calls == 1:
            raise transfer._LambertSolutionError("degenerate fixture")
        return _fake_lambert(*args)  # type: ignore[arg-type]

    def run(value: Scenario):
        return transfer._search_impulsive_transfers(
            value,
            monotonic=lambda: 0.0,
            utc_to_tdb_fn=lambda epoch: {
                value.search.departure_start_utc: 0.0,
                value.search.departure_end_utc: 10.0,
            }[epoch],
            state_query=state_query,
            gm_query=_fake_gm,
            lambert_solver=lambert,
        )

    first = run(scenario)
    assert (first.evaluated_candidates, first.solved_candidates, first.failed_candidates) == (
        4,
        3,
        1,
    )
    assert Counter(body for body, _ in calls) == {"Moon": 2, "Mars": 3, "Sun": 5}
    assert len(calls) == 10
    assert first.pareto_front

    calls.clear()
    solver_calls = 1  # The second run has no injected failure.
    second = run(scenario)
    third = run(replace(scenario, limits=replace(scenario.limits, random_seed=999)))
    assert second == third


def test_all_unsolved_and_fatal_ephemeris_failures_are_distinct() -> None:
    scenario = _small_scenario(budget=1)
    common = {
        "monotonic": lambda: 0.0,
        "utc_to_tdb_fn": lambda epoch: 0.0 if "01-01" in epoch else 10.0,
        "gm_query": _fake_gm,
    }

    def unsolved(*args: object) -> NoReturn:
        raise transfer._LambertSolutionError("no solution")

    with pytest.raises(TransferSearchError, match=r"evaluated=1, failed=1"):
        transfer._search_impulsive_transfers(
            scenario,
            state_query=_fake_state,
            lambert_solver=unsolved,
            **common,
        )

    def broken_state(body: str, epoch: float) -> CartesianState:
        if body == "Mars":
            raise EphemerisError("outside coverage")
        return _fake_state(body, epoch)

    with pytest.raises(TransferSearchError, match=r"Mars.*TDB") as caught:
        transfer._search_impulsive_transfers(
            scenario,
            state_query=broken_state,
            lambert_solver=_fake_lambert,
            **common,
        )
    assert isinstance(caught.value.__cause__, EphemerisError)


@pytest.mark.parametrize(
    ("clock_values", "expected_evaluated"),
    [([0.0, 0.0, 0.0, 0.0, 1.0], 2), ([0.0, 0.0, 1.0], 1)],
)
def test_deadline_never_returns_a_partial_result(
    clock_values: list[float], expected_evaluated: int
) -> None:
    scenario = _small_scenario(
        budget=4 if expected_evaluated == 2 else 1, runtime_seconds=1.0
    )
    clock = iter(clock_values)
    solver_calls = 0

    def solver(*args: object) -> tuple[transfer.Vector3, transfer.Vector3]:
        nonlocal solver_calls
        solver_calls += 1
        return _fake_lambert(*args)  # type: ignore[arg-type]

    with pytest.raises(
        TransferSearchError, match=rf"limit 1 s.*{expected_evaluated} candidate"
    ):
        transfer._search_impulsive_transfers(
            scenario,
            monotonic=lambda: next(clock),
            utc_to_tdb_fn=lambda epoch: 0.0 if "01-01" in epoch else 10.0,
            state_query=_fake_state,
            gm_query=_fake_gm,
            lambert_solver=solver,
        )
    assert solver_calls == expected_evaluated


@pytest.mark.parametrize("inherited,stop_s", [(101.0, 101.0), (1000.0, 130.0)])
def test_inherited_deadline_is_not_restarted_or_allowed_to_extend_budget(
    inherited: float, stop_s: float,
) -> None:
    clock = iter([100.0, 100.0, stop_s])
    with pytest.raises(TransferSearchError, match="1 candidate"):
        transfer._search_impulsive_transfers(
            _small_scenario(budget=1, runtime_seconds=30.0),
            monotonic=lambda: next(clock), deadline_monotonic_s=inherited,
            utc_to_tdb_fn=lambda epoch: 0.0 if "01-01" in epoch else 10.0,
            state_query=_fake_state, gm_query=_fake_gm, lambert_solver=_fake_lambert,
        )


@pytest.mark.parametrize("deadline", [99.0, 100.0, math.nan, math.inf, True, "101"])
def test_expired_or_invalid_shared_deadline_starts_no_science(deadline: object) -> None:
    def unexpected_time_conversion(epoch: str) -> NoReturn:
        raise AssertionError("scientific work started after deadline rejection")

    with pytest.raises(TransferSearchError):
        transfer._search_impulsive_transfers(
            _small_scenario(), monotonic=lambda: 100.0,
            deadline_monotonic_s=deadline,  # type: ignore[arg-type]
            utc_to_tdb_fn=unexpected_time_conversion,
        )


def test_lambert_wrapper_matches_direct_tudatpy_in_three_dimensions() -> None:
    pytest.importorskip("tudatpy")
    from tudatpy.astro import two_body_dynamics

    departure = (149_600_000_000.0, 20_000_000_000.0, 3_000_000_000.0)
    arrival = (-100_000_000_000.0, 180_000_000_000.0, -4_000_000_000.0)
    flight_time = 200.0 * 86_400.0
    mu_sun = 1.32712440018e20
    actual_departure, actual_arrival = transfer._solve_lambert(
        departure, arrival, flight_time, mu_sun
    )
    direct = two_body_dynamics.ZeroRevolutionLambertTargeterIzzo(
        departure,
        arrival,
        flight_time,
        mu_sun,
        is_retrograde=False,
        tolerance=1e-9,
        max_iter=50,
    ).get_velocity_vectors()

    for actual, expected in zip((actual_departure, actual_arrival), direct):
        error = math.sqrt(sum((a - float(e)) ** 2 for a, e in zip(actual, expected)))
        assert error <= 1e-6
        assert actual[2] != 0.0


def test_rotated_quarter_circle_lambert_matches_analytic_velocity() -> None:
    pytest.importorskip("tudatpy")
    mu_sun = 1.32712440018e20
    radius = 1.2e11
    rotation = 0.4
    circular_speed = math.sqrt(mu_sun / radius)
    flight_time = math.pi / 2.0 * math.sqrt(radius**3 / mu_sun)
    departure = (radius, 0.0, 0.0)
    arrival = (
        0.0,
        radius * math.cos(rotation),
        radius * math.sin(rotation),
    )
    expected_departure = (
        0.0,
        circular_speed * math.cos(rotation),
        circular_speed * math.sin(rotation),
    )
    expected_arrival = (-circular_speed, 0.0, 0.0)

    actual_departure, actual_arrival = transfer._solve_lambert(
        departure, arrival, flight_time, mu_sun
    )

    assert math.dist(actual_departure, expected_departure) <= 0.001
    assert math.dist(actual_arrival, expected_arrival) <= 0.001
    assert actual_departure[2] != 0.0


def test_all_deferred_scenario_fields_leave_search_science_unchanged() -> None:
    scenario = _small_scenario()
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
            stations=("TEST",),
            cadence_s=123.0,
            range_sigma_m=456.0,
            range_rate_sigma_m_s=0.7,
            angular_sigma_rad=0.8,
            min_elevation_rad=0.9,
        ),
        limits=replace(scenario.limits, random_seed=999),
    )

    def run(value: Scenario):
        return transfer._search_impulsive_transfers(
            value,
            monotonic=lambda: 0.0,
            utc_to_tdb_fn=lambda epoch: {
                value.search.departure_start_utc: 0.0,
                value.search.departure_end_utc: 10.0,
            }[epoch],
            state_query=_fake_state,
            gm_query=_fake_gm,
            lambert_solver=_fake_lambert,
        )

    assert run(changed) == run(scenario)


def test_reduced_real_spice_search_is_complete() -> None:
    pytest.importorskip("tudatpy")
    if not hasattr(transfer.ephemeris, "_query_body_state_tdb"):
        pytest.skip("M2 exact-TDB adapter is not present yet")
    scenario = load_scenario(REFERENCE_SCENARIO)
    scenario = replace(
        scenario,
        limits=replace(scenario.limits, max_candidates=1, runtime_seconds=60.0),
    )

    result = transfer.search_impulsive_transfers(scenario)

    assert result.evaluated_candidates == result.solved_candidates == 1
    assert result.failed_candidates == 0
    assert len(result.pareto_front) == 1
    candidate = result.pareto_front[0]
    assert all(math.isfinite(value) for value in candidate.departure_v_infinity_m_s)
    assert all(math.isfinite(value) for value in candidate.arrival_v_infinity_m_s)
    assert candidate.arrival_epoch_tdb_s - candidate.departure_epoch_tdb_s == pytest.approx(
        candidate.flight_time_s, abs=1e-6
    )
