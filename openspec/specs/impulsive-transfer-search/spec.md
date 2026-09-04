# Impulsive Transfer Search Specification

## Purpose

Provide a reproducible first-order Moon-to-Mars transfer screen that exposes the time-versus-propellant trade space and clearly identifies spacecraft mass infeasibility before high-fidelity refinement.

## Requirements

### Requirement: Bounded deterministic search domain
For a candidate budget `B = scenario.limits.max_candidates`, the system SHALL construct a closed Cartesian grid in TDB seconds with `n_departure = floor(sqrt(B))` and `n_flight_time = floor(B / n_departure)`. Each axis SHALL be evenly spaced and include both configured bounds when its count is greater than one; a singleton axis SHALL use the midpoint of its bounds. The system SHALL attempt each grid pair exactly once in departure-major order, assign the stable identifier `dIIII-tJJJJ` from its zero-based grid indices, and SHALL never attempt more than `B` or 2,000 candidates. `random_seed` SHALL NOT affect M2 candidate generation or scientific results.

#### Scenario: Full reference budget
- **WHEN** a valid scenario has `max_candidates = 2000` and sufficient runtime
- **THEN** the search attempts exactly `44 * 45 = 1980` unique departure/time-of-flight pairs, includes both bounds of both axes, and makes no 1,981st attempt

#### Scenario: Singleton budget
- **WHEN** a valid scenario has `max_candidates = 1`
- **THEN** the only attempted candidate uses the midpoint departure epoch and midpoint time of flight and has identifier `d0000-t0000`

#### Scenario: Repeat a search with a different seed
- **WHEN** the same scenario and dependency versions are searched twice and only `random_seed` changes
- **THEN** the aggregate counts and all ordered Pareto candidate identifiers, epochs, physical values, and membership are identical

### Requirement: Three-dimensional patched-conic transfer solution
Each candidate SHALL use geometric SPICE states with no aberration correction and a zero-revolution prograde Lambert solution about the Sun. Moon, Mars, and Sun reference states SHALL originate at `SSB`, use `J2000`, be expressed in meters and meters per second, and use TDB seconds since J2000. The Lambert calculation SHALL subtract the Sun state from the Moon state at departure and from the Mars state at arrival and SHALL NOT project any vector into two dimensions.

For every solved candidate, the system SHALL expose the three-component Moon-departure and Mars-arrival hyperbolic-excess velocity vectors in `J2000` meters per second. It SHALL compute scalar impulsive departure and capture magnitudes at orbit periapsis from the norm of those vectors, the SPICE gravitational parameter of the relevant body, and
`delta_v = abs(sqrt(v_infinity^2 + 2 * mu / r_periapsis) - sqrt(mu * (2 / r_periapsis - 1 / semi_major_axis)))`.
The lunar and Martian reference radii SHALL be `1737400 m` and `3389500 m`, respectively; the departure burn SHALL use the lunar parking orbit and the arrival burn SHALL target the Martian ellipse at periapsis.

#### Scenario: Match direct TudatPy calculations
- **WHEN** a solved candidate is recomputed directly with the pinned SPICE states, gravitational parameters, zero-revolution prograde Lambert targeter, and patched-conic formula
- **THEN** each hyperbolic-excess vector differs by no more than `0.000001 m/s` in Euclidean norm and each scalar burn differs by no more than `0.000001 m/s`

#### Scenario: Preserve three-dimensional geometry
- **WHEN** the direct Lambert solution for a fixture has a nonzero out-of-reference-plane component
- **THEN** the returned hyperbolic-excess vectors each contain three finite `J2000` components and the out-of-plane component is not projected away or forced to zero

#### Scenario: Keep epoch arithmetic consistent
- **WHEN** a candidate is solved
- **THEN** its normalized UTC labels identify the same instants as its TDB values within `0.001 s`, and `arrival_epoch_tdb_s - departure_epoch_tdb_s` differs from `flight_time_s` by no more than `0.000001 s`

### Requirement: Explicit M2 fidelity boundary
M2 SHALL use orbit size and eccentricity only to estimate the two scalar patched-conic burns. It SHALL retain but SHALL NOT use parking-orbit inclination, RAAN, argument of periapsis, or true anomaly to infer an executable burn direction. It also SHALL NOT use maximum thrust, radiation-pressure properties, maneuver-error properties, tracking settings, or random seed in transfer calculations. M2 SHALL NOT model an Earth-centered leg, finite sphere-of-influence crossing, third-body acceleration, finite burn, or propagated mass history.

#### Scenario: Change only deferred parameters
- **WHEN** two otherwise identical scenarios differ only in orbit orientation, maximum thrust, radiation-pressure properties, maneuver-error properties, tracking settings, or random seed
- **THEN** their aggregate counts and all returned Pareto candidate epochs, hyperbolic-excess vectors, scalar burns, mass results, and membership are identical

### Requirement: Ideal mass accounting and feasibility visibility
For every solved candidate, the system SHALL set `total_delta_v_m_s` to the sum of the nonnegative departure and arrival burn magnitudes and SHALL calculate mass sequentially using `m_after = m_before * exp(-delta_v / (g0 * isp_s))` with `g0 = 9.80665 m/s^2`. `propellant_mass_kg` SHALL equal initial mass minus final mass. A candidate SHALL have `mass_feasible = true` exactly when `final_mass_kg >= dry_mass_kg`. Mass-infeasible candidates SHALL remain eligible for the trade-space Pareto front so that an incapable spacecraft produces an informative result rather than a fabricated or empty solution set.

#### Scenario: Verify the rocket equation
- **WHEN** a candidate has two known nonzero scalar burns
- **THEN** its total delta-v, final mass, and propellant mass agree with an independent sequential rocket-equation calculation to relative error no greater than `1e-12`

#### Scenario: Expose an infeasible spacecraft
- **WHEN** every solved candidate would leave less than the configured dry mass
- **THEN** the completed result reports zero mass-feasible candidates, marks every returned Pareto candidate `mass_feasible = false`, and still exposes the nondominated time/required-propellant trade space

### Requirement: Exact and stable Pareto selection
The system SHALL construct one Pareto front over every successfully solved candidate, minimizing `flight_time_s` and `propellant_mass_kg`. Candidate A SHALL dominate candidate B exactly when A is no worse in both objectives and strictly better in at least one. For candidates with identical objective values, only the lexicographically smallest candidate identifier SHALL remain. The returned front SHALL be sorted by `(flight_time_s, propellant_mass_kg, departure_epoch_tdb_s, candidate_id)`.

#### Scenario: Select known nondominated points
- **WHEN** solved candidates have objective pairs `(180 d, 500 kg)`, `(200 d, 450 kg)`, `(220 d, 470 kg)`, `(240 d, 400 kg)`, and `(260 d, 550 kg)` in identifier order
- **THEN** the front contains exactly the first, second, and fourth candidates in the specified stable sort order

#### Scenario: Resolve identical objectives
- **WHEN** two solved candidates have exactly equal flight time and propellant mass
- **THEN** only the candidate with the lexicographically smaller stable identifier appears in the Pareto front

### Requirement: Complete typed planning result
The system SHALL expose `search_impulsive_transfers(scenario: Scenario) -> TransferSearchResult`. `TransferSearchResult` and `ImpulsiveTransferCandidate` SHALL be immutable values. The result SHALL identify `ephemeris_origin = "SSB"`, `transfer_central_body = "Sun"`, `orientation = "J2000"`, and `time_scale = "TDB seconds since J2000"`; `ephemeris_origin` SHALL describe the source Moon/Mars/Sun reference states, while each named hyperbolic-excess vector is relative to its Moon or Mars body and expressed on `J2000` axes. The result SHALL report evaluated, solved, failed, and mass-feasible candidate counts and contain the ordered Pareto front. Each candidate SHALL contain its identifier, departure and arrival UTC and TDB epochs, flight time in seconds, both three-component hyperbolic-excess vectors in meters per second, both scalar burn magnitudes and their total in meters per second, propellant and final mass in kilograms, and mass-feasibility flag. Counts SHALL satisfy `solved_candidates + failed_candidates = evaluated_candidates` and `mass_feasible_candidates <= solved_candidates`.

#### Scenario: Return a complete result
- **WHEN** all grid pairs have been attempted within the runtime limit and at least one Lambert solution succeeds
- **THEN** the function returns a complete `TransferSearchResult` whose finite values, counts, conventions, candidate fields, and stable order satisfy this contract

#### Scenario: Isolate a candidate-level Lambert failure
- **WHEN** one candidate has degenerate geometry or the zero-revolution solver cannot converge while at least one other candidate succeeds
- **THEN** the search counts that candidate as evaluated and failed, omits it from the Pareto front, and continues to a complete result without fabricating values

#### Scenario: Reject an entirely unsolved grid
- **WHEN** every attempted candidate fails to produce a finite Lambert solution
- **THEN** the function raises `TransferSearchError` containing the evaluated and failed counts and returns no partial result

### Requirement: Runtime and fatal failure behavior
The system SHALL use a monotonic deadline derived from `scenario.limits.runtime_seconds` and SHALL check it before beginning and immediately after evaluating each candidate and before returning. If the deadline is reached before a result can be returned, it SHALL raise `TransferSearchError` that states the runtime limit and evaluated count and SHALL return no partial Pareto front, including when a single candidate evaluation crosses the deadline. A SPICE initialization, coverage, state, or gravitational-parameter failure SHALL abort the search with a chained `TransferSearchError` that identifies the failed operation and affected body and epoch when applicable; no analytic, circular, stale, or zero-valued fallback is permitted.

#### Scenario: Reach the runtime deadline
- **WHEN** a controlled monotonic clock reaches the configured deadline after `k` candidates where `k` is less than the grid size
- **THEN** `TransferSearchError` names the runtime limit and `k`, no next candidate begins, and no result is returned

#### Scenario: One evaluation crosses the deadline
- **WHEN** a candidate begins before the deadline but its evaluation finishes at or after the deadline
- **THEN** the search raises `TransferSearchError` with the updated evaluated count and returns no result, even if that candidate completed the grid

#### Scenario: Lose ephemeris coverage
- **WHEN** a required Moon, Mars, or Sun state lies outside loaded SPICE coverage
- **THEN** the search stops with a chained `TransferSearchError` naming the body and epoch and emits no partial or substituted transfer

#### Scenario: Complete the reference search budget
- **WHEN** `examples/reference_mission.toml` is planned in the pinned Conda environment
- **THEN** all 1,980 grid candidates are evaluated in no more than `300 s`, at least one candidate is solved, the Pareto front is nonempty, and the result truthfully reports whether any candidate respects dry mass
