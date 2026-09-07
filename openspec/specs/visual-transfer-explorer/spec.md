# visual-transfer-explorer Specification

## Purpose
TBD - created by archiving change refine-physical-trajectory. Update Purpose after archive.

## Requirements

### Requirement: Explicit interactive input
The explorer SHALL use Streamlit and the existing scenario schema and M2 solver without hidden dates or spacecraft parameters.

#### Scenario: Load and edit
- **WHEN** the user explicitly loads the reference example, edits dates or spacecraft values, and calculates
- **THEN** normalization uses those visible inputs and the candidate summary matches the M2 result

#### Scenario: Reject invalid or stale input
- **WHEN** inputs change or a calculation fails due to invalid input or unavailable resources
- **THEN** prior results are removed and a contextual error replaces them without fabricated data

### Requirement: Consistent approximate trajectory
The explorer SHALL sample the M2 two-body arc using TudatPy and real SPICE, with SI/TDB/SSB/J2000 scientific states and explicitly labelled Sun-relative plot conversions.

#### Scenario: Check endpoints and repeatability
- **WHEN** the reference candidate is sampled at 121 evenly spaced epochs including endpoints
- **THEN** reconstructed endpoint positions and velocities agree within 100 m and 0.001 m/s and repeated scientific states are identical

#### Scenario: Check analytic orbit
- **WHEN** a circular two-body fixture is sampled at quarter-period epochs
- **THEN** states match an independent analytic circle within 0.01 m and 0.000001 m/s

#### Scenario: Explore time
- **WHEN** the time slider changes
- **THEN** the spacecraft marker, UTC epoch, and Sun-relative speed refer to the same sample without repeating candidate search

### Requirement: Honest scope and compatibility
The UI SHALL disclose approximation, ignored fields, and ideal propellant feasibility without claiming finite burns, insertion, or flight readiness. Existing APIs, CLI behavior, scientific pins, and legacy code SHALL remain compatible.

#### Scenario: Inspect reference shortfall
- **WHEN** the original reference candidate is shown
- **THEN** a propellant-shortfall warning and impulse-model limitation are visible, without invented engine durations

#### Scenario: Preserve prior work
- **WHEN** the regression suite and legacy checksum run
- **THEN** all prior tests pass and moon_to_mars.py stays byte-identical and unimported
