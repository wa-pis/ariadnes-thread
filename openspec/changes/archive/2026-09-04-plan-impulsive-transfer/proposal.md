## Why

M1 established trustworthy mission inputs and SPICE reference states, but the planner still cannot turn them into candidate Moon-to-Mars transfers. M2 must add a bounded, reproducible first-order search that lets an engineer compare flight time with ideal propellant use before higher-fidelity trajectory refinement.

## What Changes

- Add a three-dimensional, zero-revolution impulsive transfer search over the scenario's departure window and time-of-flight bounds.
- Evaluate no more than the scenario limit and never more than 2,000 unique departure/time-of-flight pairs using real SPICE endpoint states and TudatPy astrodynamics facilities.
- Convert the three-dimensional Lambert endpoint velocities into Moon-departure and Mars-arrival hyperbolic-excess vectors, then estimate two ideal instantaneous burn magnitudes from the specified parking and target orbit energies.
- Compute ideal propellant consumption with the rocket equation, mark whether each solution respects dry mass, and return a deterministic Pareto front minimizing flight time and required propellant mass. Mass-infeasible solutions remain eligible for the front so the planner can explain when the specified spacecraft cannot perform the mission.
- Add `space-nav plan SCENARIO [--json]` and a public Python planning API with typed candidates, aggregate search results, and actionable planning errors.
- Preserve calculation provenance and explicit candidate counts so complete, empty, and failed search outcomes are diagnosable without returning hardware-dependent partial results.

## Non-goals

- N-body numerical propagation, Moon or Mars gravity harmonics, solar-radiation pressure, eclipses, relativity, finite burns, and propagated variable mass; these belong to M3.
- Tracking simulation, state estimation, covariance, course-correction scheduling, Monte Carlo analysis, mission reports, and GMAT comparison; these belong to M4-M6.
- Multi-revolution Lambert solutions, launch-vehicle ascent, atmospheric flight, operational commanding, or onboard navigation.
- Exact sphere-of-influence crossings, Earth-centered escape between the Moon and heliocentric space, parking-orbit phase or plane compatibility, and burn directions. M2 retains the supplied orbit orientation, but only orbit size and eccentricity affect its scalar patched-conic burn estimates; M3 will resolve executable vector maneuvers.
- Changing the scenario schema or making `random_seed`, thrust, tracking, radiation-pressure, or maneuver-error fields influence M2 calculations.

## Capabilities

### New Capabilities

- `impulsive-transfer-search`: Bounded deterministic generation, solution, ideal mass accounting, aggregate failure counting, and flight-time/propellant Pareto selection for three-dimensional Moon-to-Mars transfer candidates.

### Modified Capabilities

- `diagnostic-cli`: Extend the command-line contract with `space-nav plan SCENARIO [--json]`, including stable complete, mass-infeasible, and error output behavior.

## Impact

- Adds public Python interfaces `search_impulsive_transfers(scenario: Scenario) -> TransferSearchResult`, immutable `ImpulsiveTransferCandidate` and `TransferSearchResult` result types, and `TransferSearchError`.
- Adds transfer-planning modules and tests under the existing `space_nav` package while reusing M1 scenario, reference-state, error-envelope, and provenance behavior.
- Uses the pinned TudatPy/SPICE environment already established by M1; no new third-party dependency is proposed.
- Leaves `moon_to_mars.py` byte-for-byte unchanged and unimported.
- Implements roadmap milestone M2, `plan-impulsive-transfer`; later milestones remain blocked until this change passes its completion gate and is archived.
