"""Strict TOML loading for normalized Moon-to-Mars mission scenarios."""

from __future__ import annotations

import math
import re
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .errors import ScenarioValidationError
from .models import (
    LimitsSpec,
    OrbitSpec,
    Scenario,
    SearchSpec,
    SpacecraftSpec,
    TrackingSpec,
)


SECONDS_PER_DAY = 86_400.0
SECONDS_PER_HOUR = 3_600.0
ARCSECONDS_PER_DEGREE = 3_600.0
MARS_MEAN_RADIUS_M = 3_389_500.0

_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)

_FIELDS = {
    "search": {
        "departure_start_utc",
        "departure_end_utc",
        "time_of_flight_min_days",
        "time_of_flight_max_days",
    },
    "departure_orbit": {
        "central_body",
        "altitude_km",
        "eccentricity",
        "inclination_deg",
        "raan_deg",
        "argument_of_periapsis_deg",
        "true_anomaly_deg",
    },
    "target_orbit": {
        "central_body",
        "periapsis_altitude_km",
        "apoapsis_altitude_km",
        "inclination_deg",
        "raan_deg",
        "argument_of_periapsis_deg",
        "true_anomaly_deg",
    },
    "spacecraft": {
        "initial_mass_kg",
        "dry_mass_kg",
        "max_thrust_n",
        "isp_s",
        "srp_area_m2",
        "reflectivity_coefficient",
        "maneuver_magnitude_sigma_fraction",
        "maneuver_pointing_sigma_deg",
    },
    "tracking": {
        "stations",
        "cadence_hours",
        "range_sigma_m",
        "range_rate_sigma_m_s",
        "angular_sigma_arcsec",
        "min_elevation_deg",
    },
    "limits": {"runtime_seconds", "random_seed", "max_candidates"},
}

_REQUIRED_SECTIONS = ("search", "departure_orbit", "target_orbit", "spacecraft")

_TRACKING_DEFAULTS: dict[str, Any] = {
    "stations": ["DSS-14", "DSS-43", "DSS-63"],
    "cadence_hours": 6.0,
    "range_sigma_m": 10.0,
    "range_rate_sigma_m_s": 0.0001,
    "angular_sigma_arcsec": 1.0,
    "min_elevation_deg": 10.0,
}

_LIMITS_DEFAULTS: dict[str, Any] = {
    "runtime_seconds": 300.0,
    "random_seed": 42,
    "max_candidates": 2000,
}


def _fail(field: str | None, message: str) -> None:
    raise ScenarioValidationError(message, field)


def _reject_unknown(table: Mapping[str, Any], allowed: set[str], prefix: str = "") -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        field = f"{prefix}.{unknown[0]}" if prefix else unknown[0]
        _fail(field, "unknown field")


def _section(data: Mapping[str, Any], name: str, *, required: bool) -> Mapping[str, Any]:
    if name not in data:
        if required:
            _fail(name, "required section is missing")
        return {}
    value = data[name]
    if not isinstance(value, dict):
        _fail(name, "must be a TOML table")
    return value


def _required(table: Mapping[str, Any], section: str, name: str) -> Any:
    if name not in table:
        _fail(f"{section}.{name}", "required field is missing")
    return table[name]


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(field, "must be a non-empty string")
    return value


def _number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(field, "must be a number")
    result = float(value)
    if not math.isfinite(result):
        _fail(field, "must be finite")
    if positive and result <= 0.0:
        _fail(field, "must be greater than 0")
    return result


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(field, "must be an integer")
    return value


def _utc(value: Any, field: str) -> tuple[str, datetime]:
    text = _text(value, field)
    if not _UTC_PATTERN.fullmatch(text):
        _fail(field, "must be an ISO-8601 UTC timestamp ending in Z")
    try:
        instant = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise ScenarioValidationError("must be a valid UTC timestamp", field) from exc
    normalized = instant.isoformat(
        timespec="microseconds" if instant.microsecond else "seconds"
    ).replace("+00:00", "Z")
    return normalized, instant


def _inclination(value: Any, field: str) -> float:
    degrees = _number(value, field)
    if not 0.0 <= degrees <= 180.0:
        _fail(field, "must be in [0, 180] degrees")
    return math.radians(degrees)


def _wrapped_angle(value: Any, field: str) -> float:
    degrees = _number(value, field)
    if not 0.0 <= degrees < 360.0:
        _fail(field, "must be in [0, 360) degrees")
    return math.radians(degrees)


def _parse_search(table: Mapping[str, Any]) -> SearchSpec:
    start, start_dt = _utc(
        _required(table, "search", "departure_start_utc"),
        "search.departure_start_utc",
    )
    end, end_dt = _utc(
        _required(table, "search", "departure_end_utc"),
        "search.departure_end_utc",
    )
    minimum_days = _number(
        _required(table, "search", "time_of_flight_min_days"),
        "search.time_of_flight_min_days",
        positive=True,
    )
    maximum_days = _number(
        _required(table, "search", "time_of_flight_max_days"),
        "search.time_of_flight_max_days",
        positive=True,
    )
    if start_dt >= end_dt:
        _fail("search.departure_end_utc", "must be later than departure_start_utc")
    if minimum_days >= maximum_days:
        _fail(
            "search.time_of_flight_max_days",
            "must be greater than time_of_flight_min_days",
        )
    return SearchSpec(
        departure_start_utc=start,
        departure_end_utc=end,
        time_of_flight_min_s=minimum_days * SECONDS_PER_DAY,
        time_of_flight_max_s=maximum_days * SECONDS_PER_DAY,
    )


def _parse_departure_orbit(table: Mapping[str, Any]) -> OrbitSpec:
    body = _text(
        _required(table, "departure_orbit", "central_body"),
        "departure_orbit.central_body",
    )
    if body != "Moon":
        _fail("departure_orbit.central_body", 'must be "Moon"')
    altitude_km = _number(
        _required(table, "departure_orbit", "altitude_km"),
        "departure_orbit.altitude_km",
        positive=True,
    )
    if altitude_km != 100.0:
        _fail("departure_orbit.altitude_km", "must be 100 km for M1")
    eccentricity = _number(
        _required(table, "departure_orbit", "eccentricity"),
        "departure_orbit.eccentricity",
    )
    if eccentricity != 0.0:
        _fail("departure_orbit.eccentricity", "must be 0 for the circular M1 orbit")
    altitude_m = altitude_km * 1_000.0
    return OrbitSpec(
        central_body=body,
        periapsis_altitude_m=altitude_m,
        apoapsis_altitude_m=altitude_m,
        eccentricity=eccentricity,
        inclination_rad=_inclination(
            _required(table, "departure_orbit", "inclination_deg"),
            "departure_orbit.inclination_deg",
        ),
        raan_rad=_wrapped_angle(
            _required(table, "departure_orbit", "raan_deg"),
            "departure_orbit.raan_deg",
        ),
        argument_of_periapsis_rad=_wrapped_angle(
            _required(table, "departure_orbit", "argument_of_periapsis_deg"),
            "departure_orbit.argument_of_periapsis_deg",
        ),
        true_anomaly_rad=_wrapped_angle(
            _required(table, "departure_orbit", "true_anomaly_deg"),
            "departure_orbit.true_anomaly_deg",
        ),
    )


def _parse_target_orbit(table: Mapping[str, Any]) -> OrbitSpec:
    body = _text(
        _required(table, "target_orbit", "central_body"),
        "target_orbit.central_body",
    )
    if body != "Mars":
        _fail("target_orbit.central_body", 'must be "Mars"')
    periapsis_m = 1_000.0 * _number(
        _required(table, "target_orbit", "periapsis_altitude_km"),
        "target_orbit.periapsis_altitude_km",
        positive=True,
    )
    apoapsis_m = 1_000.0 * _number(
        _required(table, "target_orbit", "apoapsis_altitude_km"),
        "target_orbit.apoapsis_altitude_km",
        positive=True,
    )
    if periapsis_m >= apoapsis_m:
        _fail(
            "target_orbit.apoapsis_altitude_km",
            "must be greater than periapsis_altitude_km",
        )
    if periapsis_m != 300_000.0:
        _fail("target_orbit.periapsis_altitude_km", "must be 300 km for M1")
    if apoapsis_m != 10_000_000.0:
        _fail("target_orbit.apoapsis_altitude_km", "must be 10000 km for M1")
    periapsis_radius = MARS_MEAN_RADIUS_M + periapsis_m
    apoapsis_radius = MARS_MEAN_RADIUS_M + apoapsis_m
    eccentricity = (apoapsis_radius - periapsis_radius) / (
        apoapsis_radius + periapsis_radius
    )
    return OrbitSpec(
        central_body=body,
        periapsis_altitude_m=periapsis_m,
        apoapsis_altitude_m=apoapsis_m,
        eccentricity=eccentricity,
        inclination_rad=_inclination(
            _required(table, "target_orbit", "inclination_deg"),
            "target_orbit.inclination_deg",
        ),
        raan_rad=_wrapped_angle(
            _required(table, "target_orbit", "raan_deg"),
            "target_orbit.raan_deg",
        ),
        argument_of_periapsis_rad=_wrapped_angle(
            _required(table, "target_orbit", "argument_of_periapsis_deg"),
            "target_orbit.argument_of_periapsis_deg",
        ),
        true_anomaly_rad=_wrapped_angle(
            _required(table, "target_orbit", "true_anomaly_deg"),
            "target_orbit.true_anomaly_deg",
        ),
    )


def _parse_spacecraft(table: Mapping[str, Any]) -> SpacecraftSpec:
    values = {
        name: _number(
            _required(table, "spacecraft", name), f"spacecraft.{name}", positive=True
        )
        for name in (
            "initial_mass_kg",
            "dry_mass_kg",
            "max_thrust_n",
            "isp_s",
            "srp_area_m2",
            "reflectivity_coefficient",
            "maneuver_magnitude_sigma_fraction",
            "maneuver_pointing_sigma_deg",
        )
    }
    if values["initial_mass_kg"] <= values["dry_mass_kg"]:
        _fail("spacecraft.initial_mass_kg", "must be greater than dry_mass_kg")
    return SpacecraftSpec(
        initial_mass_kg=values["initial_mass_kg"],
        dry_mass_kg=values["dry_mass_kg"],
        max_thrust_n=values["max_thrust_n"],
        isp_s=values["isp_s"],
        srp_area_m2=values["srp_area_m2"],
        reflectivity_coefficient=values["reflectivity_coefficient"],
        maneuver_magnitude_sigma_fraction=values[
            "maneuver_magnitude_sigma_fraction"
        ],
        maneuver_pointing_sigma_rad=math.radians(
            values["maneuver_pointing_sigma_deg"]
        ),
    )


def _parse_stations(value: Any) -> tuple[str, ...]:
    field = "tracking.stations"
    if not isinstance(value, list) or not value:
        _fail(field, "must be a non-empty array of station names")
    if any(not isinstance(station, str) or not station for station in value):
        _fail(field, "must contain only non-empty station names")
    return tuple(value)


def _parse_tracking(table: Mapping[str, Any]) -> TrackingSpec:
    values = {**_TRACKING_DEFAULTS, **table}
    min_elevation_deg = _number(
        values["min_elevation_deg"], "tracking.min_elevation_deg"
    )
    if not 0.0 <= min_elevation_deg <= 90.0:
        _fail("tracking.min_elevation_deg", "must be in [0, 90] degrees")
    angular_sigma_arcsec = _number(
        values["angular_sigma_arcsec"],
        "tracking.angular_sigma_arcsec",
        positive=True,
    )
    return TrackingSpec(
        stations=_parse_stations(values["stations"]),
        cadence_s=SECONDS_PER_HOUR
        * _number(values["cadence_hours"], "tracking.cadence_hours", positive=True),
        range_sigma_m=_number(
            values["range_sigma_m"], "tracking.range_sigma_m", positive=True
        ),
        range_rate_sigma_m_s=_number(
            values["range_rate_sigma_m_s"],
            "tracking.range_rate_sigma_m_s",
            positive=True,
        ),
        angular_sigma_rad=math.radians(
            angular_sigma_arcsec / ARCSECONDS_PER_DEGREE
        ),
        min_elevation_rad=math.radians(min_elevation_deg),
    )


def _parse_limits(table: Mapping[str, Any]) -> LimitsSpec:
    values = {**_LIMITS_DEFAULTS, **table}
    runtime = _number(
        values["runtime_seconds"], "limits.runtime_seconds", positive=True
    )
    seed = _integer(values["random_seed"], "limits.random_seed")
    if seed < 0:
        _fail("limits.random_seed", "must be greater than or equal to 0")
    candidates = _integer(values["max_candidates"], "limits.max_candidates")
    if not 1 <= candidates <= 2000:
        _fail("limits.max_candidates", "must be an integer from 1 through 2000")
    return LimitsSpec(runtime_seconds=runtime, random_seed=seed, max_candidates=candidates)


def load_scenario(path: str | Path) -> Scenario:
    """Load, validate, and normalize a mission scenario without SPICE side effects."""

    scenario_path = Path(path)
    try:
        with scenario_path.open("rb") as stream:
            data = tomllib.load(stream)
    except FileNotFoundError as exc:
        raise ScenarioValidationError(
            f"scenario file not found: {scenario_path}"
        ) from exc
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ScenarioValidationError(f"invalid TOML: {exc}") from exc
    except OSError as exc:
        raise ScenarioValidationError(
            f"cannot read scenario file {scenario_path}: {exc}"
        ) from exc

    _reject_unknown(data, set(_FIELDS))
    sections = {
        name: _section(data, name, required=name in _REQUIRED_SECTIONS)
        for name in _FIELDS
    }
    for name, table in sections.items():
        _reject_unknown(table, _FIELDS[name], name)

    return Scenario(
        search=_parse_search(sections["search"]),
        departure_orbit=_parse_departure_orbit(sections["departure_orbit"]),
        target_orbit=_parse_target_orbit(sections["target_orbit"]),
        spacecraft=_parse_spacecraft(sections["spacecraft"]),
        tracking=_parse_tracking(sections["tracking"]),
        limits=_parse_limits(sections["limits"]),
    )
