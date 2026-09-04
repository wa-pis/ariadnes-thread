## Purpose

Provide trustworthy, deterministic celestial-body states from real SPICE ephemerides under one explicit time, frame, origin, and unit convention.

## ADDED Requirements

### Requirement: Canonical Cartesian reference state
The system SHALL expose `query_body_state(body, epoch) -> CartesianState`, where `body` is a SPICE body name and `epoch` is an ISO-8601 UTC string ending in `Z`. `CartesianState` SHALL report the normalized UTC epoch, TDB seconds since J2000, origin `SSB`, orientation `J2000`, a three-element position in meters, and a three-element velocity in meters per second. All numeric components SHALL be finite.

#### Scenario: Query a supported body
- **WHEN** a caller requests the state of `Mars` at a covered UTC epoch
- **THEN** the result identifies `SSB/J2000`, contains the corresponding TDB epoch, and returns position in meters and velocity in meters per second

### Requirement: Accurate UTC and TDB conversion
Conversion from accepted UTC text to the internal TDB epoch and back to normalized UTC SHALL round-trip within 1 millisecond over the supported standard-kernel coverage.

#### Scenario: Round-trip an epoch
- **WHEN** an accepted UTC epoch is converted to TDB seconds since J2000 and converted back
- **THEN** the absolute difference from the original instant is no greater than 1 millisecond

### Requirement: Direct SPICE parity
For the same body, epoch, origin, and orientation, `query_body_state` SHALL agree with a direct TudatPy SPICE query to within 1 millimeter in position norm and 1 micrometer per second in velocity norm.

#### Scenario: Compare adapter and direct query
- **WHEN** the adapter and TudatPy SPICE are queried for `Moon` at the same covered epoch using `SSB/J2000`
- **THEN** position disagreement is at most `0.001 m` and velocity disagreement is at most `0.000001 m/s`

### Requirement: Lazy and deterministic kernel use
The reference-state capability SHALL load TudatPy standard kernels only when the first ephemeris or time-conversion request needs them and SHALL reuse that initialized kernel set for later requests in the process. Repeated queries with identical inputs and dependency versions SHALL return identical state values.

#### Scenario: Import without querying
- **WHEN** the package and scenario loader are imported without an ephemeris request
- **THEN** SPICE standard-kernel loading has not occurred

#### Scenario: Repeat a state query
- **WHEN** the same body and epoch are queried twice in one process
- **THEN** both `CartesianState` values compare equal and standard kernels are not loaded a second time

### Requirement: Explicit ephemeris failure
The system MUST NOT substitute circular, analytic, stale, or zero-valued states when SPICE initialization, body lookup, time conversion, or coverage fails. It SHALL raise `EphemerisError` with an actionable message containing the requested body and epoch and, for coverage failures, stating that the requested epoch is outside available kernel coverage.

#### Scenario: Unsupported body
- **WHEN** a caller requests a body unavailable from the loaded kernels
- **THEN** `EphemerisError` names the body and no fallback state is returned

#### Scenario: Epoch outside coverage
- **WHEN** a caller requests a supported body outside the available kernel coverage
- **THEN** `EphemerisError` names the body and epoch and explains the coverage problem

#### Scenario: Kernel initialization failure
- **WHEN** TudatPy standard kernels cannot be initialized
- **THEN** `EphemerisError` explains that kernel initialization failed and preserves the original failure as diagnostic context
