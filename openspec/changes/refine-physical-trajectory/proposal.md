## Why

Resumed by explicit user approval on 2026-09-07 after delivery and archival of
the Streamlit prototype as `2026-09-07-refine-physical-trajectory`. This active
change restores unfinished M3 work; the deferred directory remains a historical
snapshot. Checked components are retained, not evidence of M3 completion.

M2 finds useful time/propellant trade points, but its body-centre Lambert endpoints and scalar instantaneous burns are not executable trajectories. M3 must turn one explicitly selected M2 candidate into an honestly classified finite-burn propagation before navigation estimation can use it.

## What Changes

- Add deterministic boundary-value refinement from the configured lunar parking-orbit state to the configured Martian target-orbit state, using the M2 candidate only as the initial targeting seed.
- Propagate separate departure-burn, coast, and arrival-burn arcs with TudatPy, coupled spacecraft mass, dry-mass protection, impact detection, and bounded targeting failure.
- Use the pinned Moon `gggrx1200` degree/order 200 and Mars `jgmro120d` degree/order 120 gravity fields, point-mass perturbations, cannonball solar-radiation pressure with Moon/Earth/Mars occultation, and the Sun Schwarzschild correction.
- Define the previously implicit orbit-element frame and epoch semantics needed to create physical endpoint states while preserving the established orbit-altitude radii separately from gravity-field normalization radii.
- Add `refine_physical_trajectory(...)`, immutable result records, `TrajectoryRefinementError`, and `space-nav refine SCENARIO --candidate-id ID [--json]` with reproducibility provenance.
- Preserve the existing M2 reference as a seed-budget rejection under the documented preflight policy, and qualify a separate provisional M3 fixture through a reproducible safe-seed and targeting experiment before claiming finite-burn feasibility.
- Bump the package minor version to `0.3.0` when the capability is complete.

## Non-goals

- Tracking observations, orbit determination, covariance, or state estimation; these belong to M4.
- TCM selection, closed-loop guidance, or use of measurements available during flight; these belong to M5.
- Monte Carlo dispersion, stochastic maneuver-error application, mission reports, or GMAT comparison; these belong to M6.
- Optimizing the launch window, choosing a candidate implicitly, globally optimal thrust steering, atmospheric flight, aerocapture, attitude dynamics, or flight-qualified/onboard operation.
- Claiming that numerical convergence bounds represent real-world ephemeris, gravity-field, optical-property, or maneuver uncertainty.

## Capabilities

### New Capabilities

- `physical-trajectory-refinement`: Deterministic candidate handoff, physical endpoint targeting, high-fidelity force propagation, finite burns, coupled mass, feasibility classification, numerical error budgets, and reproducible result records.

### Modified Capabilities

- `mission-scenario`: Define body-centred osculating orbit elements on J2000 axes at the selected candidate boundary epochs, including circular-orbit equivalence and distinct shape/gravity radii.
- `diagnostic-cli`: Add the refinement command, status rendering, error behavior, and complete dynamics provenance without changing existing commands.

## Impact

- Adds trajectory-refinement code and tests under the existing `space_nav` package and one M3-only feasible example scenario.
- Reuses the pinned TudatPy, Tudat resources, SPICE, NumPy, standard-library CLI, and existing M2 search; no new third-party dependency is proposed.
- Adds public `TrajectoryBoundaryState`, `FiniteBurnRecord`, `TrajectoryBoundaryDifference`, `PhysicalTrajectoryResult`, `TrajectoryRefinementError`, and `refine_physical_trajectory` interfaces.
- Keeps `moon_to_mars.py` byte-for-byte unchanged and unimported.
- Implements roadmap milestone M3, `refine-physical-trajectory`; M4-M6 remain out of scope until this change is complete and archived.

## Plan review — 2026-09-06

The review adds missing interpolation, combined-force, per-arc PPN, safety-termination, and shared-deadline checks. It corrects the dry-mass fixture comparison and limits the preflight status to an M2 seed-budget decision. Earlier exploratory timing/accuracy numbers require checked-in reproduction before use as acceptance evidence. No production constant, dependency, target tolerance, or archived specification changes in this review; unfinished implementation work remains explicitly unchecked.
