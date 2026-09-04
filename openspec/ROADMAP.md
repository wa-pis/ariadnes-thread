# Space Navigation Roadmap

Milestones are strictly linear: `M1 -> M2 -> M3 -> M4 -> M5 -> M6`. M1 and M2 are archived; M3 is the next milestone and does not yet have an active change. A later change may be created only after the current milestone passes its completion gate, passes strict OpenSpec validation, and is archived.

| Milestone / change | Status | Depends on | Verifiable result |
|---|---|---|---|
| **M1 — `establish-navigation-foundation`** | Archived 2026-09-04 | None | Reproducible Python environment, strict TOML scenario, canonical units/time/frame contract, real SPICE ephemerides, and diagnostic CLI. |
| **M2 — `plan-impulsive-transfer`** | Archived 2026-09-04 | M1 archived | Three-dimensional impulsive Moon-to-Mars search evaluates at most 2,000 candidates and returns a flight-time/fuel Pareto front. |
| **M3 — `refine-physical-trajectory`** | Planned | M2 archived | Selected trajectories include Moon/Mars gravity harmonics, solar-radiation pressure and shadows, relativistic correction, variable mass, and finite burns. |
| **M4 — `estimate-navigation-state`** | Planned | M3 archived | Synthetic observations from three ground stations feed batch least squares and produce an estimated state and covariance. |
| **M5 — `schedule-course-corrections`** | Planned | M4 archived | The planner selects zero to three TCMs using only measurements available before each maneuver. |
| **M6 — `verify-and-report-mission`** | Planned | M5 archived | Twenty Monte Carlo cases produce standalone HTML, CSV, and JSON reports and an independent GMAT comparison. |

## M1 completion gate

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

## Later milestone completion gates

- **M2:** the bounded three-dimensional search and Pareto-front output pass their acceptance scenarios on fixed inputs.
- **M3:** force-model and finite-burn refinements pass numerical regression and conservation/error-budget checks defined by its future change.
- **M4:** synthetic observation generation, batch estimation, and covariance output pass reproducible truth-recovery checks defined by its future change.
- **M5:** maneuver count and measurement-causality rules pass tests that prevent use of future observations.
- **M6:** all 20 seeded Monte Carlo cases complete, all three report formats agree, and the GMAT comparison satisfies the future change's documented tolerance.

Completion criteria for M2–M6 are intentionally high-level until the preceding milestone is archived. Each future change must replace its high-level gate with measurable WHEN/THEN scenarios before implementation.
