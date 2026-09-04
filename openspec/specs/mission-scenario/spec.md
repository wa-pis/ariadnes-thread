# Mission Scenario Specification

## Purpose

Define a strict, reproducible mission-scenario contract that every later planning and navigation milestone can consume without guessing units, defaults, or validation behavior.

## Requirements

### Requirement: Complete TOML scenario contract
The system SHALL expose `load_scenario(path) -> Scenario`. `Scenario` SHALL contain `SearchSpec`, two normalized `OrbitSpec` values, `SpacecraftSpec`, `TrackingSpec`, and `LimitsSpec` values loaded from the following TOML sections and fields:

- `[search]`: required `departure_start_utc`, `departure_end_utc`, `time_of_flight_min_days`, and `time_of_flight_max_days`.
- `[departure_orbit]`: required `central_body`, `altitude_km`, `eccentricity`, `inclination_deg`, `raan_deg`, `argument_of_periapsis_deg`, and `true_anomaly_deg`; `central_body` MUST be `Moon` and M1 scenarios MUST describe a 100 km circular orbit.
- `[target_orbit]`: required `central_body`, `periapsis_altitude_km`, `apoapsis_altitude_km`, `inclination_deg`, `raan_deg`, `argument_of_periapsis_deg`, and `true_anomaly_deg`; `central_body` MUST be `Mars`, M1 periapsis altitude MUST be `300 km`, M1 apoapsis altitude MUST be `10000 km`, and the angular orientation MUST be supplied by the user.
- `[spacecraft]`: required `initial_mass_kg`, `dry_mass_kg`, `max_thrust_n`, `isp_s`, `srp_area_m2`, `reflectivity_coefficient`, `maneuver_magnitude_sigma_fraction`, and `maneuver_pointing_sigma_deg`.
- Optional `[tracking]` and `[limits]` sections as defined by their defaults.

Every field whose name ends in `_km`, `_kg`, `_n`, `_s`, `_days`, `_hours`, `_m`, `_m_s`, `_arcsec`, `_deg`, or `_fraction` SHALL use the unit stated by that suffix. UTC fields SHALL use an ISO-8601 UTC value ending in `Z`.

#### Scenario: Load a complete scenario
- **WHEN** a TOML file supplies all required sections and valid values, including a 100 km circular lunar departure orbit and a valid Martian target ellipse
- **THEN** `load_scenario` returns a typed `Scenario` with the values preserved or normalized without changing their physical meaning

#### Scenario: Reject an unknown field
- **WHEN** a scenario contains an unknown section or field
- **THEN** `load_scenario` raises `ScenarioValidationError` naming the full dotted path of the unknown value

### Requirement: Stable tracking and execution defaults
When `[tracking]` is absent or a tracking field is omitted, the system SHALL use stations `DSS-14`, `DSS-43`, and `DSS-63`, `cadence_hours = 6`, `range_sigma_m = 10`, `range_rate_sigma_m_s = 0.0001`, `angular_sigma_arcsec = 1`, and `min_elevation_deg = 10`. When `[limits]` is absent or a limits field is omitted, the system SHALL use `runtime_seconds = 300`, `random_seed = 42`, and `max_candidates = 2000`.

#### Scenario: Apply all defaults
- **WHEN** a valid scenario omits both `[tracking]` and `[limits]`
- **THEN** the returned `TrackingSpec` and `LimitsSpec` contain exactly the documented defaults

#### Scenario: Override one default
- **WHEN** a valid scenario supplies one supported tracking or limits field
- **THEN** the supplied value replaces only that default and all other defaults remain unchanged

### Requirement: Field-specific validation
The system SHALL reject missing, non-finite, or physically invalid values with `ScenarioValidationError`. The error SHALL identify the full dotted field path and explain the violated constraint. All durations and physical magnitudes SHALL be positive, all spacecraft fields SHALL be positive, `initial_mass_kg` MUST be greater than `dry_mass_kg`, the departure start MUST precede the departure end, minimum time of flight MUST be less than maximum time of flight, and target periapsis altitude MUST be less than target apoapsis altitude. Angular fields SHALL be finite; inclination SHALL be in `[0, 180]` degrees and RAAN, argument of periapsis, and true anomaly SHALL be in `[0, 360)` degrees. `max_candidates` SHALL be an integer from 1 through 2000.

#### Scenario: Missing required value
- **WHEN** `spacecraft.max_thrust_n` is absent
- **THEN** validation fails with an error that identifies `spacecraft.max_thrust_n`

#### Scenario: Non-finite numeric value
- **WHEN** any numeric field contains a NaN or infinity value
- **THEN** validation fails with an error that identifies that field

#### Scenario: Invalid spacecraft masses
- **WHEN** `spacecraft.initial_mass_kg` is less than or equal to `spacecraft.dry_mass_kg`
- **THEN** validation fails and identifies `spacecraft.initial_mass_kg`

#### Scenario: Invalid search order
- **WHEN** the departure start is not earlier than the departure end or minimum time of flight is not less than maximum time of flight
- **THEN** validation fails and identifies the later or upper-bound field responsible for the invalid ordering

#### Scenario: Invalid target ellipse
- **WHEN** target periapsis altitude is greater than or equal to target apoapsis altitude
- **THEN** validation fails and identifies `target_orbit.apoapsis_altitude_km`

#### Scenario: Target orbit differs from the M1 contract
- **WHEN** an otherwise valid target orbit does not use a 300 km periapsis and 10000 km apoapsis
- **THEN** validation fails and identifies the altitude field that differs from the M1 value

### Requirement: Deterministic typed result
For unchanged file contents and software versions, repeated calls to `load_scenario` SHALL return equal immutable values. The loader SHALL perform no ephemeris query, network request, trajectory calculation, or mutation of global mission state.

#### Scenario: Repeated load
- **WHEN** the same valid scenario is loaded twice in one process
- **THEN** the two `Scenario` values compare equal and no SPICE kernels are loaded as a side effect
