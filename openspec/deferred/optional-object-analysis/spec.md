# Optional object analysis — deferred specification

Status: user-requested requirements draft; not an active change, implemented
capability or authorization to modify M2/M3 physics. Promote through the normal
proposal/design/tasks workflow after selecting data sources and numerical gates.
Existing M2 screening-not-performed warnings remain applicable until then.

## Requirements

### Requirement: Independent opt-in operations
The system SHALL separate "Показать объекты", "Учесть гравитацию объектов" and
"Проверить сближения". Each extension SHALL default to off with its own explicit
object selection and status. Existing baseline planet rendering and mandatory
forces/guards SHALL remain unchanged; these options only control extensions.

#### Scenario: No optional operations
- **WHEN** all extension options are off
- **THEN** baseline scientific outputs remain identical and no optional catalogue fetch, added-force propagation or encounter search occurs

#### Scenario: Enable only one operation
- **WHEN** exactly one extension is requested
- **THEN** the other two remain off, and the UI makes no claim that they ran implicitly

### Requirement: Display without changing dynamics
Optional rendering SHALL use identified objects with declared ephemeris coverage
and frame/time conversions. It SHALL NOT change the spacecraft trajectory or
imply force inclusion or collision clearance. Individual asteroid trajectories
SHALL NOT be confused with a schematic belt-region overlay.

#### Scenario: Render an available object
- **WHEN** a selected object's ephemeris covers the requested display epoch
- **THEN** its marker uses the same epoch and display frame as the spacecraft, identifies its source and leaves spacecraft states byte-identical

#### Scenario: Missing display coverage
- **WHEN** the requested object lacks an ephemeris at that epoch
- **THEN** its missing coverage is shown explicitly and no stale or fabricated position replaces it

### Requirement: Explicit additional-gravity recalculation
Additional forces SHALL require a compatible physical propagator, covered
ephemerides and validated gravitational parameters. An ephemeris alone SHALL NOT
imply availability of a usable mass/GM. Unsupported options SHALL be unavailable
with an explanation, not silently ignored. Objects SHALL NOT be counted twice.

#### Scenario: M2 cannot execute the requested extension
- **WHEN** additional object gravity is requested for an M2 result
- **THEN** the operation is reported unavailable for that model and the original result is not relabelled as including the requested forces

#### Scenario: Recalculate using a supported model
- **WHEN** a compatible model has all required inputs and the user explicitly starts recalculation
- **THEN** the new result records the exact added bodies, GM values and sources, model version and resource identity, invalidates dependent screening, and retains all mandatory baseline forces and guards

#### Scenario: Reject missing or duplicate forces
- **WHEN** a requested body's GM or ephemeris coverage is absent, or it duplicates an existing force contribution
- **THEN** no successful extended-force result is published and the specific reason is reported without fallback

### Requirement: Post-calculation close-approach screening
Screening SHALL compare a frozen spacecraft trajectory with explicitly selected
catalogue objects over a declared interval, without altering that trajectory or
automatically scheduling avoidance. Results SHALL identify encounter epochs,
separations in metres, thresholds, coverage and uncertainty assumptions. A
nearest-distance estimate SHALL NOT be presented as a collision probability.

#### Scenario: Detect an encounter between display samples
- **WHEN** a manufactured encounter crosses the configured distance threshold between two display samples
- **THEN** the screening verification detects it within the agreed time/distance tolerance without relying on the 121 display samples as proof of clearance

#### Scenario: Report scope-limited absence of encounters
- **WHEN** the selected catalogue and time interval are fully processed without threshold crossings
- **THEN** the result says no qualifying encounters were found within that declared scope, not that the route is safe or unknown objects are absent

#### Scenario: Keep uncertainty limits visible
- **WHEN** the catalogue lacks uncertainty information needed for a requested risk assessment
- **THEN** that risk assessment is unavailable; any nominal geometric result is explicitly labelled as such and no zero-risk probability is produced

### Requirement: Independent truthful lifecycle and provenance
Each operation SHALL expose off, pending, running, completed, unavailable,
failed or stale status as applicable, plus a reason for non-completion.
Completed SHALL describe execution, not safety. Results SHALL bind to exact
object selection, trajectory/model identity, interval, source versions, coverage,
thresholds and uncertainty policy. Resource/runtime limits SHALL be explicit.

#### Scenario: Data or runtime failure
- **WHEN** required data are missing, stale under the selected policy, outside coverage, or a deadline is exceeded
- **THEN** the operation is unavailable or failed with a reason, incomplete output is not labelled completed, and the independent baseline trajectory remains available with its original limitations

#### Scenario: Invalidate dependent results
- **WHEN** trajectory, force model, catalogue selection/version, interval, thresholds or uncertainty policy changes
- **THEN** affected screening results become stale and cannot retain a current completed status until explicitly recomputed

## Decisions required before implementation

- Catalogue/provider and supported object classes (planets, asteroids, comets,
  artificial debris); access/licensing, selection limits and stale-data policy.
- Source frame/time transformations and reference-oracle test tolerances.
- Encounter algorithm and bounded time/distance accuracy, thresholds, physical
  size and uncertainty handling; no arbitrary scientific defaults in this draft.
- Separate compute/data budgets and reproducibility/cache rules for each option.
- Implement display and post-processing screening first when qualified; additional
  gravity remains a separately qualified physical-model extension. None bypasses
  current M3 safety prerequisites or constitutes flight certification.
