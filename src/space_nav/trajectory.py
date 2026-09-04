"""Verified M2 handoff for physical trajectory refinement."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
import math
from numbers import Real
from typing import NoReturn, cast

from . import ephemeris
from .ephemeris import CartesianState
from .errors import EphemerisError, TrajectoryRefinementError, TransferSearchError
from .models import (
    ImpulsiveTransferCandidate,
    OrbitSpec,
    Scenario,
    TrajectoryBoundaryState,
)
from .transfer import (
    MARS_REFERENCE_RADIUS_M,
    MOON_REFERENCE_RADIUS_M,
    search_impulsive_transfers,
)


_TIME_TOLERANCE_S = 1e-6
_VELOCITY_TOLERANCE_M_S = 1e-6
_MASS_RELATIVE_TOLERANCE = 1e-12

MOON_ORBIT_SHAPE_RADIUS_M = MOON_REFERENCE_RADIUS_M
MARS_ORBIT_SHAPE_RADIUS_M = MARS_REFERENCE_RADIUS_M
MOON_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2 = 4_902_800_121_846.8
MARS_HARMONIC_GRAVITATIONAL_PARAMETER_M3_S2 = 42_828_375_815_756.1

Cartesian6 = tuple[float, float, float, float, float, float]
StateQuery = Callable[[str, float], CartesianState]
ElementConverter = Callable[
    [float, float, float, float, float, float, float], object
]


def _raise_refinement_error(
    candidate_id: object,
    operation: str,
    detail: str,
    cause: Exception,
) -> NoReturn:
    raise TrajectoryRefinementError(
        f"Candidate {candidate_id!r} failed during {operation}: {detail}"
    ) from cause


def _raise_handoff_error(
    candidate_id: object,
    detail: str,
    cause: Exception,
) -> NoReturn:
    _raise_refinement_error(
        candidate_id,
        "candidate-verification",
        detail,
        cause,
    )


def _tudat_keplerian_to_cartesian(
    semi_major_axis_m: float,
    eccentricity: float,
    inclination_rad: float,
    argument_of_periapsis_rad: float,
    raan_rad: float,
    true_anomaly_rad: float,
    gravitational_parameter_m3_s2: float,
) -> object:
    """Call TudatPy lazily so importing the M3 API has no kernel side effects."""

    try:
        from tudatpy.astro import element_conversion

        return element_conversion.keplerian_to_cartesian_elementwise(
            semi_major_axis_m,
            eccentricity,
            inclination_rad,
            argument_of_periapsis_rad,
            raan_rad,
            true_anomaly_rad,
            gravitational_parameter_m3_s2,
        )
    except Exception as exc:
        raise RuntimeError("TudatPy Keplerian conversion failed") from exc


def _cartesian_values(raw_state: object) -> Cartesian6:
    try:
        flatten = getattr(raw_state, "reshape", None)
        flat_state = flatten(-1) if callable(flatten) else raw_state
        if not isinstance(flat_state, Iterable):
            raise TypeError("state is not iterable")
        raw_values = tuple(flat_state)
    except Exception as exc:
        raise ValueError("element conversion must return six numeric values") from exc
    if len(raw_values) != 6 or any(
        not isinstance(value, Real) or isinstance(value, bool)
        for value in raw_values
    ):
        raise ValueError("element conversion must return six numeric values")
    try:
        values = tuple(float(value) for value in raw_values)
    except (OverflowError, ValueError) as exc:
        raise ValueError("element conversion must return six numeric values") from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError("element conversion must return six finite values")
    return cast(Cartesian6, values)


def _positive_finite(name: str, value: object) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive finite number") from exc
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return number


def _orbit_to_body_relative_state(
    orbit: OrbitSpec,
    shape_radius_m: float,
    gravitational_parameter_m3_s2: float,
    *,
    element_converter: ElementConverter | None = None,
) -> Cartesian6:
    """Convert body-relative J2000 osculating elements to an SI state."""

    shape_radius_m = _positive_finite("shape_radius_m", shape_radius_m)
    gravitational_parameter_m3_s2 = _positive_finite(
        "gravitational_parameter_m3_s2",
        gravitational_parameter_m3_s2,
    )
    periapsis_radius_m = shape_radius_m + orbit.periapsis_altitude_m
    apoapsis_radius_m = shape_radius_m + orbit.apoapsis_altitude_m
    semi_major_axis_m = (periapsis_radius_m + apoapsis_radius_m) / 2.0

    argument_of_periapsis_rad = orbit.argument_of_periapsis_rad
    true_anomaly_rad = orbit.true_anomaly_rad
    if orbit.eccentricity == 0.0:
        true_anomaly_rad = (argument_of_periapsis_rad + true_anomaly_rad) % math.tau
        argument_of_periapsis_rad = 0.0

    converter = element_converter or _tudat_keplerian_to_cartesian
    try:
        raw_state = converter(
            semi_major_axis_m,
            orbit.eccentricity,
            orbit.inclination_rad,
            argument_of_periapsis_rad,
            orbit.raan_rad,
            true_anomaly_rad,
            gravitational_parameter_m3_s2,
        )
    except Exception as exc:
        raise RuntimeError("Keplerian element conversion failed") from exc
    state = _cartesian_values(raw_state)
    if math.hypot(*state[:3]) == 0.0:
        raise ValueError("element conversion produced a body-centre position")
    return state


def _build_boundary_state(
    *,
    label: str,
    expected_body: str,
    orbit: OrbitSpec,
    epoch_utc: str,
    epoch_tdb_s: float,
    shape_radius_m: float,
    gravitational_parameter_m3_s2: float,
    state_query: StateQuery,
    element_converter: ElementConverter | None,
) -> TrajectoryBoundaryState:
    if orbit.central_body != expected_body:
        raise ValueError(
            f"{label} orbit central_body must be {expected_body!r}, "
            f"got {orbit.central_body!r}"
        )
    relative_state = _orbit_to_body_relative_state(
        orbit,
        shape_radius_m,
        gravitational_parameter_m3_s2,
        element_converter=element_converter,
    )
    body_state = state_query(expected_body, epoch_tdb_s)
    if not isinstance(body_state, CartesianState):
        raise TypeError("state query must return CartesianState")
    if (
        body_state.body != expected_body
        or body_state.epoch_utc != epoch_utc
        or body_state.epoch_tdb_s != epoch_tdb_s
    ):
        raise ValueError(
            "state query returned the wrong body or exact UTC/TDB epoch"
        )
    return TrajectoryBoundaryState(
        label=label,
        epoch_utc=epoch_utc,
        epoch_tdb_s=epoch_tdb_s,
        origin="SSB",
        orientation="J2000",
        position_m=(
            body_state.position_m[0] + relative_state[0],
            body_state.position_m[1] + relative_state[1],
            body_state.position_m[2] + relative_state[2],
        ),
        velocity_m_s=(
            body_state.velocity_m_s[0] + relative_state[3],
            body_state.velocity_m_s[1] + relative_state[4],
            body_state.velocity_m_s[2] + relative_state[5],
        ),
    )


def _build_boundary_states(
    scenario: Scenario,
    candidate: ImpulsiveTransferCandidate,
    moon_gravitational_parameter_m3_s2: float,
    mars_gravitational_parameter_m3_s2: float,
    *,
    state_query: StateQuery | None = None,
    element_converter: ElementConverter | None = None,
) -> tuple[TrajectoryBoundaryState, TrajectoryBoundaryState]:
    """Build departure-ignition and arrival-cutoff SSB/J2000 states."""

    query = state_query or ephemeris._query_body_state_tdb
    definitions = (
        (
            "departure-ignition",
            "Moon",
            scenario.departure_orbit,
            candidate.departure_epoch_utc,
            candidate.departure_epoch_tdb_s,
            MOON_ORBIT_SHAPE_RADIUS_M,
            moon_gravitational_parameter_m3_s2,
        ),
        (
            "arrival-cutoff",
            "Mars",
            scenario.target_orbit,
            candidate.arrival_epoch_utc,
            candidate.arrival_epoch_tdb_s,
            MARS_ORBIT_SHAPE_RADIUS_M,
            mars_gravitational_parameter_m3_s2,
        ),
    )
    boundaries = []
    for label, body, orbit, epoch_utc, epoch_tdb_s, shape_radius_m, gm in definitions:
        try:
            boundaries.append(
                _build_boundary_state(
                    label=label,
                    expected_body=body,
                    orbit=orbit,
                    epoch_utc=epoch_utc,
                    epoch_tdb_s=epoch_tdb_s,
                    shape_radius_m=shape_radius_m,
                    gravitational_parameter_m3_s2=gm,
                    state_query=query,
                    element_converter=element_converter,
                )
            )
        except (EphemerisError, RuntimeError, TypeError, ValueError) as exc:
            _raise_refinement_error(
                candidate.candidate_id,
                "boundary-state-construction",
                f"{label} for {body!r} at TDB epoch {epoch_tdb_s!r}: {exc}",
                exc,
            )
    return boundaries[0], boundaries[1]


def _require_match(
    matches: bool,
    candidate_id: str,
    field: str,
) -> None:
    if not matches:
        cause = ValueError(f"{field} differs from the reproduced Pareto candidate")
        _raise_handoff_error(candidate_id, str(cause), cause)


def _utc_difference_s(left: str, right: str) -> float:
    left_utc = datetime.fromisoformat(left.removesuffix("Z") + "+00:00")
    right_utc = datetime.fromisoformat(right.removesuffix("Z") + "+00:00")
    return abs((left_utc - right_utc).total_seconds())


def _verify_candidate_values(
    supplied: ImpulsiveTransferCandidate,
    reproduced: ImpulsiveTransferCandidate,
) -> None:
    candidate_id = supplied.candidate_id
    _require_match(
        supplied.candidate_id == reproduced.candidate_id,
        candidate_id,
        "candidate_id",
    )
    for field in ("departure_epoch_utc", "arrival_epoch_utc"):
        _require_match(
            _utc_difference_s(
                getattr(supplied, field),
                getattr(reproduced, field),
            )
            <= _TIME_TOLERANCE_S,
            candidate_id,
            field,
        )
    _require_match(
        supplied.mass_feasible == reproduced.mass_feasible,
        candidate_id,
        "mass_feasible",
    )
    for field in (
        "departure_epoch_tdb_s",
        "arrival_epoch_tdb_s",
        "flight_time_s",
    ):
        _require_match(
            math.isclose(
                getattr(supplied, field),
                getattr(reproduced, field),
                rel_tol=0.0,
                abs_tol=_TIME_TOLERANCE_S,
            ),
            candidate_id,
            field,
        )
    for field in (
        "departure_delta_v_m_s",
        "arrival_delta_v_m_s",
        "total_delta_v_m_s",
    ):
        _require_match(
            math.isclose(
                getattr(supplied, field),
                getattr(reproduced, field),
                rel_tol=0.0,
                abs_tol=_VELOCITY_TOLERANCE_M_S,
            ),
            candidate_id,
            field,
        )
    for field in ("departure_v_infinity_m_s", "arrival_v_infinity_m_s"):
        _require_match(
            math.dist(getattr(supplied, field), getattr(reproduced, field))
            <= _VELOCITY_TOLERANCE_M_S,
            candidate_id,
            field,
        )
    for field in ("propellant_mass_kg", "final_mass_kg"):
        supplied_mass = getattr(supplied, field)
        reproduced_mass = getattr(reproduced, field)
        _require_match(
            abs(supplied_mass - reproduced_mass)
            <= abs(reproduced_mass) * _MASS_RELATIVE_TOLERANCE,
            candidate_id,
            field,
        )


def _verify_candidate_handoff(
    scenario: Scenario,
    candidate: ImpulsiveTransferCandidate,
) -> ImpulsiveTransferCandidate:
    """Return the authoritative reproduced candidate after exact M2 comparison."""

    if not isinstance(candidate, ImpulsiveTransferCandidate):
        cause = TypeError("candidate must be an ImpulsiveTransferCandidate")
        _raise_handoff_error(
            getattr(candidate, "candidate_id", "<invalid>"),
            str(cause),
            cause,
        )
    try:
        result = search_impulsive_transfers(scenario)
    except TransferSearchError as exc:
        _raise_handoff_error(candidate.candidate_id, str(exc), exc)

    reproduced = next(
        (
            item
            for item in result.pareto_front
            if item.candidate_id == candidate.candidate_id
        ),
        None,
    )
    if reproduced is None:
        cause = LookupError("candidate is not on the reproduced Pareto front")
        _raise_handoff_error(candidate.candidate_id, str(cause), cause)
    _verify_candidate_values(candidate, reproduced)
    return reproduced
