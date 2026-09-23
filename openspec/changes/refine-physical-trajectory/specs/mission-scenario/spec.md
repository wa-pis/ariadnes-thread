## MODIFIED Requirements

### Requirement: Field-specific validation
The system SHALL reject missing, non-finite, or physically invalid values with `ScenarioValidationError`. The error SHALL identify the full dotted field path and explain the violated constraint. All durations and physical magnitudes SHALL be positive, all spacecraft fields SHALL be positive, `initial_mass_kg` MUST be greater than `dry_mass_kg`, the departure start MUST precede the departure end, minimum time of flight MUST be less than maximum time of flight, and target periapsis altitude MUST be less than target apoapsis altitude. Angular fields SHALL be finite; inclination SHALL be in `[0, 180]` degrees and RAAN, argument of periapsis, and true anomaly SHALL be in `[0, 360)` degrees. `max_candidates` SHALL be an integer from 1 through 10000.

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

#### Scenario: Expanded budget boundary
- **WHEN** max_candidates is 10000 and sufficient runtime is available
- **THEN** the budget is accepted and the search grid is 100 departure dates by 100 durations, while omitted limits retain max_candidates=2000 and runtime_seconds=300

#### Scenario: Above the expanded ceiling
- **WHEN** max_candidates is 10001
- **THEN** the budget is rejected before scientific search

## ADDED Requirements

### Requirement: Candidate-bound orbit-state semantics
For M3 refinement, `departure_orbit` and `target_orbit` SHALL describe central-body-relative osculating Keplerian elements expressed on `J2000` axes. Departure elements SHALL apply at the selected candidate's departure-burn ignition epoch and target elements SHALL apply at its arrival-burn cutoff epoch. Cartesian conversion SHALL use the relevant M3 harmonic gravity field's gravitational parameter. Orbit altitudes SHALL continue to use the established Moon `1737400 m` and Mars `3389500 m` shape radii and SHALL NOT silently use a gravity model's normalization or default SPICE shape radius.

#### Scenario: Match direct element conversion
- **WHEN** either normalized orbit is independently converted with the same body gravitational parameter and added to the body's SSB/J2000 SPICE state at its defined epoch
- **THEN** the resulting public position and velocity differ from the scenario-to-state conversion by no more than `0.001 m` and `0.000001 m/s`

#### Scenario: Preserve circular-orbit equivalence
- **WHEN** the circular lunar orbit's argument of periapsis is increased by an angle `delta` and its true anomaly is decreased by the same angle after normalization
- **THEN** its converted Cartesian position and velocity remain equal within `0.001 m` and `0.000001 m/s` because only argument of latitude is observable

#### Scenario: Keep radii distinct
- **WHEN** the normalized orbit and force-model manifests are inspected
- **THEN** the Moon and Mars orbit-altitude shape radii remain `1737400 m` and `3389500 m`, while any different harmonic normalization radii are separately named and never substitute for them
