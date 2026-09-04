"""Deterministic first-order impulsive Moon-to-Mars transfer search."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

from . import ephemeris
from .ephemeris import CartesianState
from .errors import EphemerisError, TransferSearchError
from .models import (
    ImpulsiveTransferCandidate,
    OrbitSpec,
    Scenario,
    TransferSearchResult,
)


MODEL_IDENTIFIER = "sun-centered-zero-revolution-patched-conic-v1"
MOON_REFERENCE_RADIUS_M = 1_737_400.0
MARS_REFERENCE_RADIUS_M = 3_389_500.0
STANDARD_GRAVITY_M_S2 = 9.80665
LAMBERT_TOLERANCE = 1e-9
LAMBERT_MAX_ITERATIONS = 50

IGNORED_SCENARIO_FIELDS = (
    "departure_orbit.inclination_deg",
    "departure_orbit.raan_deg",
    "departure_orbit.argument_of_periapsis_deg",
    "departure_orbit.true_anomaly_deg",
    "target_orbit.inclination_deg",
    "target_orbit.raan_deg",
    "target_orbit.argument_of_periapsis_deg",
    "target_orbit.true_anomaly_deg",
    "spacecraft.max_thrust_n",
    "spacecraft.srp_area_m2",
    "spacecraft.reflectivity_coefficient",
    "spacecraft.maneuver_magnitude_sigma_fraction",
    "spacecraft.maneuver_pointing_sigma_deg",
    "tracking.stations",
    "tracking.cadence_hours",
    "tracking.range_sigma_m",
    "tracking.range_rate_sigma_m_s",
    "tracking.angular_sigma_arcsec",
    "tracking.min_elevation_deg",
    "limits.random_seed",
)

Vector3 = tuple[float, float, float]
StateQuery = Callable[[str, float], CartesianState]
GmQuery = Callable[[str], float]
LambertSolver = Callable[[Vector3, Vector3, float, float], tuple[Vector3, Vector3]]


class _LambertSolutionError(RuntimeError):
    """An expected numerical failure for one Lambert grid point."""


def _grid_shape(candidate_budget: int) -> tuple[int, int]:
    """Return the largest specified rectangular grid not exceeding the budget."""

    if not isinstance(candidate_budget, int) or isinstance(candidate_budget, bool):
        raise ValueError("candidate_budget must be an integer")
    if not 1 <= candidate_budget <= 2000:
        raise ValueError("candidate_budget must be from 1 through 2000")
    departure_count = math.isqrt(candidate_budget)
    return departure_count, candidate_budget // departure_count


def _inclusive_axis(lower: float, upper: float, count: int) -> tuple[float, ...]:
    """Return a closed evenly spaced axis, or its midpoint for one sample."""

    if count < 1:
        raise ValueError("axis count must be positive")
    if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
        raise ValueError("axis bounds must be finite and ordered")
    if count == 1:
        return ((lower + upper) / 2.0,)
    step = (upper - lower) / (count - 1)
    return (lower,) + tuple(lower + step * index for index in range(1, count - 1)) + (
        upper,
    )


def _candidate_grid(
    candidate_budget: int,
    departure_start_tdb_s: float,
    departure_end_tdb_s: float,
    flight_time_min_s: float,
    flight_time_max_s: float,
) -> Iterator[tuple[str, float, float]]:
    """Yield stable identifiers and grid coordinates in departure-major order."""

    departure_count, flight_time_count = _grid_shape(candidate_budget)
    departures = _inclusive_axis(
        departure_start_tdb_s, departure_end_tdb_s, departure_count
    )
    flight_times = _inclusive_axis(
        flight_time_min_s, flight_time_max_s, flight_time_count
    )
    for axis_name, values in (
        ("departure epochs", departures),
        ("flight times", flight_times),
    ):
        if len(set(values)) != len(values):
            raise TransferSearchError(
                f"Search grid cannot represent {len(values)} unique {axis_name} "
                "with binary64 precision; widen the corresponding bounds or "
                "lower max_candidates"
            )
    for departure_index, departure_epoch in enumerate(departures):
        for flight_time_index, flight_time in enumerate(flight_times):
            yield (
                f"d{departure_index:04d}-t{flight_time_index:04d}",
                departure_epoch,
                flight_time,
            )


def _orbit_geometry(orbit: OrbitSpec, reference_radius_m: float) -> tuple[float, float]:
    """Return semi-major axis and eccentricity from normalized orbit altitudes."""

    periapsis_radius = reference_radius_m + orbit.periapsis_altitude_m
    apoapsis_radius = reference_radius_m + orbit.apoapsis_altitude_m
    semi_major_axis = (periapsis_radius + apoapsis_radius) / 2.0
    eccentricity = (apoapsis_radius - periapsis_radius) / (
        apoapsis_radius + periapsis_radius
    )
    return semi_major_axis, eccentricity


def _two_body_dynamics() -> Any:
    try:
        from tudatpy.astro import two_body_dynamics
    except Exception as exc:
        raise TransferSearchError(
            "TudatPy transfer dynamics is unavailable; install the pinned project "
            "environment"
        ) from exc
    return two_body_dynamics


def _patched_conic_delta_v(
    gravitational_parameter_m3_s2: float,
    orbit: OrbitSpec,
    reference_radius_m: float,
    excess_speed_m_s: float,
) -> float:
    """Return the scalar periapsis escape/capture impulse in meters per second."""

    semi_major_axis, eccentricity = _orbit_geometry(orbit, reference_radius_m)
    try:
        value = abs(
            float(
                _two_body_dynamics().compute_escape_or_capture_delta_v(
                    gravitational_parameter_m3_s2,
                    semi_major_axis,
                    eccentricity,
                    excess_speed_m_s,
                )
            )
        )
    except TransferSearchError:
        raise
    except Exception as exc:
        raise TransferSearchError("Patched-conic burn calculation failed") from exc
    if not math.isfinite(value):
        raise TransferSearchError("Patched-conic burn calculation was non-finite")
    return value


def _mass_accounting(
    initial_mass_kg: float,
    dry_mass_kg: float,
    isp_s: float,
    departure_delta_v_m_s: float,
    arrival_delta_v_m_s: float,
) -> tuple[float, float, float, bool]:
    """Return total delta-v, propellant, final mass, and dry-mass feasibility."""

    exponent_scale = STANDARD_GRAVITY_M_S2 * isp_s
    after_departure = initial_mass_kg * math.exp(
        -departure_delta_v_m_s / exponent_scale
    )
    final_mass = after_departure * math.exp(-arrival_delta_v_m_s / exponent_scale)
    total_delta_v = departure_delta_v_m_s + arrival_delta_v_m_s
    return (
        total_delta_v,
        initial_mass_kg - final_mass,
        final_mass,
        final_mass >= dry_mass_kg,
    )


def _dominates(
    left: ImpulsiveTransferCandidate, right: ImpulsiveTransferCandidate
) -> bool:
    return (
        left.flight_time_s <= right.flight_time_s
        and left.propellant_mass_kg <= right.propellant_mass_kg
        and (
            left.flight_time_s < right.flight_time_s
            or left.propellant_mass_kg < right.propellant_mass_kg
        )
    )


def _pareto_front(
    candidates: list[ImpulsiveTransferCandidate]
    | tuple[ImpulsiveTransferCandidate, ...],
) -> tuple[ImpulsiveTransferCandidate, ...]:
    """Select the exact time/propellant Pareto front with stable duplicate handling."""

    front = []
    for candidate in candidates:
        duplicate_precedes = any(
            other.candidate_id < candidate.candidate_id
            and other.flight_time_s == candidate.flight_time_s
            and other.propellant_mass_kg == candidate.propellant_mass_kg
            for other in candidates
        )
        if duplicate_precedes or any(
            _dominates(other, candidate) for other in candidates if other is not candidate
        ):
            continue
        front.append(candidate)
    return tuple(
        sorted(
            front,
            key=lambda item: (
                item.flight_time_s,
                item.propellant_mass_kg,
                item.departure_epoch_tdb_s,
                item.candidate_id,
            ),
        )
    )


def _finite_vector(values: Any, name: str) -> Vector3:
    try:
        vector = tuple(float(value) for value in values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise _LambertSolutionError(f"{name} is not a numerical vector") from exc
    if len(vector) != 3 or not all(math.isfinite(value) for value in vector):
        raise _LambertSolutionError(f"{name} must contain three finite values")
    return vector  # type: ignore[return-value]


def _solve_lambert(
    departure_position_m: Vector3,
    arrival_position_m: Vector3,
    flight_time_s: float,
    sun_gravitational_parameter_m3_s2: float,
) -> tuple[Vector3, Vector3]:
    """Solve one zero-revolution prograde three-dimensional Lambert problem."""

    dynamics = _two_body_dynamics()
    try:
        targeter = dynamics.ZeroRevolutionLambertTargeterIzzo(
            departure_position_m,
            arrival_position_m,
            flight_time_s,
            sun_gravitational_parameter_m3_s2,
            is_retrograde=False,
            tolerance=LAMBERT_TOLERANCE,
            max_iter=LAMBERT_MAX_ITERATIONS,
        )
        departure_velocity, arrival_velocity = targeter.get_velocity_vectors()
        return (
            _finite_vector(departure_velocity, "Lambert departure velocity"),
            _finite_vector(arrival_velocity, "Lambert arrival velocity"),
        )
    except _LambertSolutionError:
        raise
    except (RuntimeError, ValueError, ArithmeticError) as exc:
        raise _LambertSolutionError(f"Lambert solver failed: {exc}") from exc


def _subtract(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[index] - right[index] for index in range(3))  # type: ignore[return-value]


def _norm(vector: Vector3) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _query_state(
    state_query: StateQuery, body: str, epoch_tdb_s: float
) -> CartesianState:
    try:
        return state_query(body, epoch_tdb_s)
    except EphemerisError as exc:
        raise TransferSearchError(
            f"SPICE state query failed for {body} at TDB {epoch_tdb_s!r}: {exc}"
        ) from exc


def _query_gm(gm_query: GmQuery, body: str) -> float:
    try:
        value = float(gm_query(body))
    except EphemerisError as exc:
        raise TransferSearchError(
            f"SPICE gravitational-parameter query failed for {body}: {exc}"
        ) from exc
    if not math.isfinite(value) or value <= 0.0:
        raise TransferSearchError(
            f"SPICE returned an invalid gravitational parameter for {body}"
        )
    return value


def _load_gravitational_parameters(gm_query: GmQuery) -> dict[str, float]:
    return {body: _query_gm(gm_query, body) for body in ("Sun", "Moon", "Mars")}


def _endpoint_states(
    cache: dict[float, tuple[CartesianState, CartesianState]],
    epoch_tdb_s: float,
    body: str,
    state_query: StateQuery,
) -> tuple[CartesianState, CartesianState]:
    if epoch_tdb_s not in cache:
        cache[epoch_tdb_s] = (
            _query_state(state_query, body, epoch_tdb_s),
            _query_state(state_query, "Sun", epoch_tdb_s),
        )
    return cache[epoch_tdb_s]


def _evaluate_candidate(
    scenario: Scenario,
    candidate_id: str,
    departure_epoch_tdb_s: float,
    flight_time_s: float,
    gravitational_parameters: dict[str, float],
    departure_cache: dict[float, tuple[CartesianState, CartesianState]],
    arrival_cache: dict[float, tuple[CartesianState, CartesianState]],
    state_query: StateQuery,
    lambert_solver: LambertSolver,
) -> ImpulsiveTransferCandidate:
    arrival_epoch_tdb_s = departure_epoch_tdb_s + flight_time_s
    moon, departure_sun = _endpoint_states(
        departure_cache, departure_epoch_tdb_s, "Moon", state_query
    )
    mars, arrival_sun = _endpoint_states(
        arrival_cache, arrival_epoch_tdb_s, "Mars", state_query
    )
    departure_position = _subtract(moon.position_m, departure_sun.position_m)
    arrival_position = _subtract(mars.position_m, arrival_sun.position_m)
    departure_body_velocity = _subtract(
        moon.velocity_m_s, departure_sun.velocity_m_s
    )
    arrival_body_velocity = _subtract(mars.velocity_m_s, arrival_sun.velocity_m_s)
    transfer_departure_velocity, transfer_arrival_velocity = lambert_solver(
        departure_position,
        arrival_position,
        flight_time_s,
        gravitational_parameters["Sun"],
    )
    departure_v_infinity = _subtract(
        transfer_departure_velocity, departure_body_velocity
    )
    arrival_v_infinity = _subtract(transfer_arrival_velocity, arrival_body_velocity)
    departure_delta_v = _patched_conic_delta_v(
        gravitational_parameters["Moon"],
        scenario.departure_orbit,
        MOON_REFERENCE_RADIUS_M,
        _norm(departure_v_infinity),
    )
    arrival_delta_v = _patched_conic_delta_v(
        gravitational_parameters["Mars"],
        scenario.target_orbit,
        MARS_REFERENCE_RADIUS_M,
        _norm(arrival_v_infinity),
    )
    total_delta_v, propellant_mass, final_mass, mass_feasible = _mass_accounting(
        scenario.spacecraft.initial_mass_kg,
        scenario.spacecraft.dry_mass_kg,
        scenario.spacecraft.isp_s,
        departure_delta_v,
        arrival_delta_v,
    )
    return ImpulsiveTransferCandidate(
        candidate_id=candidate_id,
        departure_epoch_utc=moon.epoch_utc,
        arrival_epoch_utc=mars.epoch_utc,
        departure_epoch_tdb_s=departure_epoch_tdb_s,
        arrival_epoch_tdb_s=arrival_epoch_tdb_s,
        flight_time_s=flight_time_s,
        departure_v_infinity_m_s=departure_v_infinity,
        arrival_v_infinity_m_s=arrival_v_infinity,
        departure_delta_v_m_s=departure_delta_v,
        arrival_delta_v_m_s=arrival_delta_v,
        total_delta_v_m_s=total_delta_v,
        propellant_mass_kg=propellant_mass,
        final_mass_kg=final_mass,
        mass_feasible=mass_feasible,
    )


def _deadline_error(runtime_seconds: float, evaluated_candidates: int) -> TransferSearchError:
    return TransferSearchError(
        f"Runtime limit {runtime_seconds:g} s reached after evaluating "
        f"{evaluated_candidates} candidate(s); no partial result is returned"
    )


def _search_impulsive_transfers(
    scenario: Scenario,
    *,
    monotonic: Callable[[], float] | None = None,
    utc_to_tdb_fn: Callable[[str], float] | None = None,
    state_query: StateQuery | None = None,
    gm_query: GmQuery | None = None,
    lambert_solver: LambertSolver | None = None,
) -> TransferSearchResult:
    """Internal injectable implementation used by deterministic failure tests."""

    monotonic = time.monotonic if monotonic is None else monotonic
    utc_to_tdb_fn = ephemeris.utc_to_tdb if utc_to_tdb_fn is None else utc_to_tdb_fn
    state_query = (
        ephemeris._query_body_state_tdb if state_query is None else state_query
    )
    gm_query = (
        ephemeris._get_body_gravitational_parameter
        if gm_query is None
        else gm_query
    )
    lambert_solver = _solve_lambert if lambert_solver is None else lambert_solver

    started = monotonic()
    deadline = started + scenario.limits.runtime_seconds
    try:
        departure_start = float(
            utc_to_tdb_fn(scenario.search.departure_start_utc)
        )
        departure_end = float(utc_to_tdb_fn(scenario.search.departure_end_utc))
    except EphemerisError as exc:
        raise TransferSearchError(
            f"SPICE time conversion failed for the departure window: {exc}"
        ) from exc

    gravitational_parameters = _load_gravitational_parameters(gm_query)
    departures: dict[float, tuple[CartesianState, CartesianState]] = {}
    arrivals: dict[float, tuple[CartesianState, CartesianState]] = {}
    solved: list[ImpulsiveTransferCandidate] = []
    evaluated_candidates = 0
    failed_candidates = 0

    for candidate_id, departure_epoch, flight_time in _candidate_grid(
        scenario.limits.max_candidates,
        departure_start,
        departure_end,
        scenario.search.time_of_flight_min_s,
        scenario.search.time_of_flight_max_s,
    ):
        if monotonic() >= deadline:
            raise _deadline_error(
                scenario.limits.runtime_seconds, evaluated_candidates
            )
        try:
            candidate = _evaluate_candidate(
                scenario,
                candidate_id,
                departure_epoch,
                flight_time,
                gravitational_parameters,
                departures,
                arrivals,
                state_query,
                lambert_solver,
            )
        except _LambertSolutionError:
            failed_candidates += 1
        else:
            solved.append(candidate)
        evaluated_candidates += 1
        if monotonic() >= deadline:
            raise _deadline_error(
                scenario.limits.runtime_seconds, evaluated_candidates
            )

    if not solved:
        raise TransferSearchError(
            "No Lambert solution was found: "
            f"evaluated={evaluated_candidates}, failed={failed_candidates}"
        )
    front = _pareto_front(solved)
    if monotonic() >= deadline:
        raise _deadline_error(scenario.limits.runtime_seconds, evaluated_candidates)
    return TransferSearchResult(
        ephemeris_origin="SSB",
        transfer_central_body="Sun",
        orientation="J2000",
        time_scale="TDB seconds since J2000",
        evaluated_candidates=evaluated_candidates,
        solved_candidates=len(solved),
        failed_candidates=failed_candidates,
        mass_feasible_candidates=sum(candidate.mass_feasible for candidate in solved),
        pareto_front=front,
    )


def search_impulsive_transfers(scenario: Scenario) -> TransferSearchResult:
    """Return the complete deterministic M2 transfer trade-space Pareto front."""

    return _search_impulsive_transfers(scenario)


def _tudat_resources_version() -> str:
    """Read the Conda-only resource package version without importing it."""

    metadata_files = sorted(
        (Path(sys.prefix) / "conda-meta").glob("tudat-resources-*.json")
    )
    for path in metadata_files:
        try:
            version = json.loads(path.read_text(encoding="utf-8"))["version"]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError):
            continue
        if isinstance(version, str) and version:
            return version
    return "unknown"


def _transfer_model_manifest(scenario: Scenario) -> dict[str, Any]:
    """Return exact model settings for inclusion in the CLI provenance manifest."""

    departure_count, flight_time_count = _grid_shape(
        scenario.limits.max_candidates
    )
    gravitational_parameters = _load_gravitational_parameters(
        ephemeris._get_body_gravitational_parameter
    )
    return {
        "identifier": MODEL_IDENTIFIER,
        "tudat_resources_version": _tudat_resources_version(),
        "grid": {
            "candidate_budget": scenario.limits.max_candidates,
            "departure_count": departure_count,
            "flight_time_count": flight_time_count,
            "attempted_candidates": departure_count * flight_time_count,
        },
        "solver": {
            "targeter": "ZeroRevolutionLambertTargeterIzzo",
            "revolutions": 0,
            "branch": "prograde",
            "tolerance": LAMBERT_TOLERANCE,
            "maximum_iterations": LAMBERT_MAX_ITERATIONS,
        },
        "reference_radii_m": {
            "Moon": MOON_REFERENCE_RADIUS_M,
            "Mars": MARS_REFERENCE_RADIUS_M,
        },
        "standard_gravity_m_s2": STANDARD_GRAVITY_M_S2,
        "gravitational_parameters": {
            "units": "m^3/s^2",
            "source": "SPICE",
            "values": gravitational_parameters,
        },
        "ignored_scenario_fields": list(IGNORED_SCENARIO_FIELDS),
    }
