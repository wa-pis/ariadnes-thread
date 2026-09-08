# Ariadna Space Navigation Roadmap

## Current priority — M3 resumed (2026-09-07)

The user approved resuming M3 after prototype delivery. The prototype is archived
as `2026-09-07-refine-physical-trajectory` and synced to `visual-transfer-explorer`.
The sole active `refine-physical-trajectory` restores unfinished M3 requirements.
Ephemeris qualification (2.7) and analytic subdivision controls (3.8) are complete.
The current prerequisite is the full-force safety-envelope investigation (3.9),
authorized on 2026-09-08 without weakening scientific tolerances or the shared
300-second deadline. Other finite-burn prerequisites remain open before the
targeting spike. Preserve the UI; scheduling state is managed in the app.

Latest 3.9 evidence: new probes at all 73 mapped Saturn record boundaries
fail the position allocation; 71 also fail the velocity allocation. Maximum
errors are `0.182333 m` and `2.138636e-5 m/s` near `997133760 TDB seconds since
J2000`, versus unchanged `0.025 m` and `2.5e-6 m/s` limits. The earlier single
segment-junction counterexample is therefore not the only affected boundary.
The counterexample is retained; task 2.7's original samples are not a uniform
certificate. Investigate source boundaries and query-order behavior before a
reviewed remedy. No tolerance, kernel or production-limit changes are approved
by this observation, and targeting remains gated.

### Historical prototype priority (superseded by resumption above)

The user temporarily paused M3 to deliver the [visible prototype](PROTOTYPE.md).
The prototype reused the change ID for continuity. Original M3 documents and
task states remain in `openspec/deferred/refine-physical-trajectory` as a snapshot;
they were never archived as completed engineering work.

## Engineering roadmap

This roadmap delivers the first Moon-to-Mars reference use case for the
[Ariadna product vision](VISION.md). The broader goal is an open specification,
reference implementation, and interoperability tests, not a new universal or
flight-qualified standard. Existing milestone gates remain unchanged.

The first proposed interoperability slice is a declared trajectory contract,
TudatPy calculation, CCSDS OEM export, and independent-reader verification.
It is not yet scheduled or implemented. Before implementation, assign it to an
accepted change with a pinned standard edition, supported profile, numerical
tolerances, and measurable acceptance scenarios. Do not insert a second active
change or silently extend M3. Reassess placement when reviewing the next change.

The engineering sequence is `M1 -> M2 -> M3 -> M4 -> M5 -> M6`. M1 and M2 are archived; M3 is resumed as `refine-physical-trajectory`. Do not archive incomplete engineering work as completed.

| Milestone / change | Status | Depends on | Verifiable result |
|---|---|---|---|
| **M1 — `establish-navigation-foundation`** | Archived 2026-09-04 | None | Reproducible Python environment, strict TOML scenario, canonical units/time/frame contract, real SPICE ephemerides, and diagnostic CLI. |
| **M2 — `plan-impulsive-transfer`** | Archived 2026-09-04 | M1 archived | Three-dimensional impulsive Moon-to-Mars search evaluates at most 2,000 candidates and returns a flight-time/fuel Pareto front. |
| **M3 — `refine-physical-trajectory`** | Resumed 2026-09-07 | M2 archived | One selected Pareto candidate is refined from the configured lunar orbit to the configured Martian orbit with declared gravity harmonics, radiation pressure and shadows, Sun Schwarzschild relativity, variable mass, finite burns, and honest physical status. |
| **M4 — `estimate-navigation-state`** | Planned | M3 archived | Synthetic observations from three ground stations feed batch least squares and produce an estimated state and covariance. |
| **M5 — `schedule-course-corrections`** | Planned | M4 archived | The planner selects zero to three TCMs using only measurements available before each maneuver. |
| **M6 — `verify-and-report-mission`** | Planned | M5 archived | Twenty Monte Carlo cases produce standalone HTML, CSV, and JSON reports and an independent GMAT comparison. |

## M1 completion gate (historical, at M1 archival)

- `openspec validate establish-navigation-foundation --strict` succeeds.
- A clean environment resolves and installs every pinned dependency and the local package.
- A complete TOML scenario loads to immutable normalized values without hidden launch dates or spacecraft parameters.
- Missing fields, malformed TOML/encoding, unknown keys, nonnumeric values, invalid date order, nonpositive dimensions, invalid mass order, and invalid orbit bounds fail with field-specific diagnostics.
- UTC to TDB to UTC round-trip error is no greater than 1 millisecond.
- The state adapter agrees with a direct TudatPy/SPICE query within 1 millimeter and 1 micrometer per second.
- Public states label SI units, TDB seconds from J2000, SSB origin, and J2000 orientation.
- Successful CLI calls exit `0`; user-input failures exit `2` without a traceback.
- Repeated diagnostics with the same scenario, dependency versions, and seed produce identical scientific values.
- The diagnostic manifest identifies the scenario, software, conventions, seed, and every loaded standard kernel available from TudatPy, including file hashes.
- `moon_to_mars.py` remains byte-for-byte unchanged and is not imported by `space_nav`; no M2–M6 behavior is present.

## M3 completion gate

- `openspec validate refine-physical-trajectory --strict` succeeds before implementation completion and immediately before archival.
- The supplied candidate is reproduced from the same normalized scenario and deterministic M2 Pareto front before any physical propagation.
- Production propagation uses Moon `gggrx1200` degree/order 200, Mars `jgmro120d` degree/order 120, declared point-mass perturbations, current-mass cannonball radiation pressure with Moon/Earth/Mars shadows, and Sun Schwarzschild relativity without gravity double counting.
- Departure ignition and arrival cutoff are the configured physical lunar and Martian orbit states rather than M2 body-centre endpoints.
- Separate departure-burn, coast, and arrival-burn arcs preserve state/mass continuity, follow the declared TNW guidance, obey the thrust mass-flow law, detect impacts, and never cross dry mass.
- `examples/reference_mission.toml` remains unchanged and candidate `d0001-t0035` returns `mass-infeasible` without finite-burn targeting because its ideal M2 final mass is below dry mass.
- The provisional M3 fixture changes only dry mass; candidate geometry and ideal masses remain unchanged but the M2 feasibility flag changes. Physical convergence must be demonstrated for `d0001-t0035` within `1000 m`, `0.01 m/s`, eight iterations, and the shared 300-second cooperative deadline before the fixture is called feasible.
- The exact TNW corrector demonstrates that feasible-fixture gate in a prerequisite spike before production correction proceeds; until then, the iteration/runtime limit is an acceptance hypothesis rather than measured performance and is not weakened silently.
- Frozen-command nominal/tighter propagation agrees within `10 m`, `0.0001 m/s`, and `0.000001 kg`; the isolated ten-orbit fixture keeps relative energy and angular-momentum drift within `1e-11`.
- Moon degree-400 sensitivity stays within `500 m` and `0.0001 m/s`; the finite Mars degree-60-to-120 tail is reported without claiming knowledge beyond the degree-120 model ceiling.
- Repeated canonical JSON results are byte-identical for the same scenario and resources, and the manifest records complete resource, force, numerical, targeting, and deferred-input provenance.
- Qualify ephemeris interpolation against direct SPICE and a denser table before the targeting spike; identical integrator results on the same interpolation table do not qualify ephemeris accuracy. Verify the combined forces and per-arc PPN reset independently.
- Check in the prerequisite spike and its scientific/timing evidence. A failed safe-seed or closure gate requires revising the active change before production correction proceeds. Preserve all existing closure and sensitivity tolerances until evidence supports an explicitly reviewed change.
- The complete pinned Python 3.12 test suite passes, existing M1/M2 behavior remains compatible apart from the planned `0.3.0` version, and `moon_to_mars.py` remains byte-for-byte unchanged and unimported.

## Future milestone completion gates

- **M4:** synthetic observation generation, batch estimation, and covariance output pass reproducible truth-recovery checks defined by its future change.
- **M5:** maneuver count and measurement-causality rules pass tests that prevent use of future observations.
- **M6:** all 20 seeded Monte Carlo cases complete, all three report formats agree, and the GMAT comparison satisfies the future change's documented tolerance.

Completion criteria for M4-M6 remain intentionally high-level until the preceding milestone is archived. Each future change must replace its high-level gate with measurable WHEN/THEN scenarios before implementation.

Twenty M6 cases are a reproducible regression ensemble, not evidence of a rare-event failure probability. Define uncertainty assumptions and the statistical scope in M6 before interpreting success rates.
