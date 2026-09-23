## MODIFIED Requirements

### Requirement: Bounded deterministic search domain
For a candidate budget `B = scenario.limits.max_candidates`, the system SHALL construct a closed Cartesian grid in TDB seconds with `n_departure = floor(sqrt(B))` and `n_flight_time = floor(B / n_departure)`. Each axis SHALL be evenly spaced and include both configured bounds when its count is greater than one; a singleton axis SHALL use the midpoint of its bounds. The system SHALL attempt each grid pair exactly once in departure-major order, assign the stable identifier `dIIII-tJJJJ` from its zero-based grid indices, and SHALL never attempt more than `B` or 10,000 candidates. `random_seed` SHALL NOT affect M2 candidate generation or scientific results.

#### Scenario: Full reference budget
- **WHEN** a valid scenario has `max_candidates = 2000` and sufficient runtime
- **THEN** the search attempts exactly `44 * 45 = 1980` unique departure/time-of-flight pairs, includes both bounds of both axes, and makes no 1,981st attempt

#### Scenario: Singleton budget
- **WHEN** a valid scenario has `max_candidates = 1`
- **THEN** the only attempted candidate uses the midpoint departure epoch and midpoint time of flight and has identifier `d0000-t0000`

#### Scenario: Repeat a search with a different seed
- **WHEN** the same scenario and dependency versions are searched twice and only `random_seed` changes
- **THEN** the aggregate counts and all ordered Pareto candidate identifiers, epochs, physical values, and membership are identical

#### Scenario: Expanded budget boundary
- **WHEN** max_candidates is 10000 and sufficient runtime is available
- **THEN** the budget is accepted and the search grid is 100 departure dates by 100 durations, while omitted limits retain max_candidates=2000 and runtime_seconds=300

#### Scenario: Above the expanded ceiling
- **WHEN** max_candidates is 10001
- **THEN** the budget is rejected before scientific search
