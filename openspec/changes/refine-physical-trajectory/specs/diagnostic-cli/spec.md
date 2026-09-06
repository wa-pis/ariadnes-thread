## ADDED Requirements

### Requirement: Physical trajectory refinement command
The application SHALL provide `space-nav refine SCENARIO --candidate-id dIIII-tJJJJ [--json]`. It SHALL validate the scenario and reproduce the requested M2 Pareto candidate before physical propagation. A completed `converged`, `mass-infeasible`, or `targeting-failed` classification SHALL exit `0`; argument, scenario, candidate, resource, deadline, integration, and scientific-validation errors SHALL exit `2`, emit no normal result, use the existing selected-format error contract, and expose no traceback.

#### Scenario: Refine a candidate in JSON mode
- **WHEN** a valid candidate completes classification with `space-nav refine mission.toml --candidate-id d0001-t0035 --json`
- **THEN** the command exits `0`, writes nothing to standard error, and writes one finite JSON object with `ok: true`, the resolved scenario, candidate identifier, explicit status and reason, result data, and manifest

#### Scenario: Render a converged result for a person
- **WHEN** a feasible refinement converges without `--json`
- **THEN** output labels the candidate, status, boundary UTC/TDB epochs, `SSB/J2000`, positions in `m`, velocities in `m/s`, thrust in `N`, durations in `s`, TNW burn directions, masses in `kg`, target residuals, numerical diagnostics, and force-model identifier

#### Scenario: Render a physical non-success
- **WHEN** a completed result is `mass-infeasible` or `targeting-failed`
- **THEN** the command exits `0`, names the status and reason prominently, includes every available mass or residual diagnostic, and does not print missing burns or states as zero-valued physical data

#### Scenario: Validate before refinement
- **WHEN** the scenario or candidate identifier is invalid
- **THEN** no physical propagation begins, stdout is empty, and the command exits `2` with one `ScenarioValidationError` or `TrajectoryRefinementError` in the selected error format

### Requirement: Physical refinement provenance manifest
Every completed JSON refinement SHALL extend the existing manifest with the verified M2 seed; literal production force-model identifier; gravitating bodies and acceleration types; Moon/Mars coefficient model names, expected and actual file hashes, degree/order, associated and rotation frames, gravitational parameters, and normalization radii; distinct orbit-altitude radii; the eight SPICE collision-radius vectors and selected maxima; the explicit `3.828e26 W` solar source and occultors; enabled and disabled relativistic terms; exact TNW seed/guidance and mass law; nominal/tighter integrator settings; finite-difference, trust, damping, acceptance, tie-break, iteration, 73-control-attempt, 76-propagation-evaluation, and 228-native-arc bounds; target and numerical thresholds; actual counters under their declared increment rules; ordered boundary diagnostics; and the scenario fields intentionally ignored by M3.

#### Scenario: Inspect complete refinement provenance
- **WHEN** a JSON refinement completes in any status
- **THEN** its manifest identifies every input, dependency, kernel, gravity resource, convention, model setting, threshold, and bounded algorithm setting needed to reproduce or interpret that status

#### Scenario: Repeat canonical JSON
- **WHEN** the same scenario, candidate, pinned environment, and identical initial loaded-kernel inventory are refined twice without reaching the runtime deadline
- **THEN** both invocations produce byte-identical canonical JSON

The raw kernel manifest SHALL continue to report the actual loaded pool, including duplicate entries. A changed pool inventory is a changed provenance input even when effective dynamics agree. Deferred input changes SHALL preserve scientific results, but need not preserve the whole JSON because scenario hashes, seeds, and input provenance legitimately differ.

#### Scenario: Render a seed-budget rejection accurately
- **WHEN** the result is `mass-infeasible` with reason `preflight-m2-propellant-shortfall`
- **THEN** human and JSON output identify the budget as the ideal M2 seed estimate and the rejection as preflight policy, without claiming a demonstrated lower bound on all physical transfer fuel costs

### Requirement: M1 and M2 command compatibility after refinement
Adding physical refinement SHALL NOT remove, rename, or change the meaning of existing public Python names or the `validate`, `ephemeris`, and `plan` command schemas, scientific values, exit statuses, error behavior, and import-time kernel laziness. Version fields SHALL report `0.3.0` after M3 is complete, and `space_nav` SHALL continue not to import `moon_to_mars.py`.

#### Scenario: Re-run prior milestone compatibility checks
- **WHEN** the complete M1 and M2 API, CLI, numerical, provenance, laziness, and legacy-isolation suites run after M3 is added
- **THEN** their prior behavior and tolerances still pass unchanged except that documented version fields report `0.3.0`
