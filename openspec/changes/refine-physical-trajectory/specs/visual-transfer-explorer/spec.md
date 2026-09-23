## ADDED Requirements

### Requirement: Calculation-bound provenance panel
The explorer SHALL display read-only provenance for each successful M2 search using the normalized scenario actually supplied to the solver, existing CLI-compatible model/resource fields, and explicit scientific conventions. It SHALL NOT label edited inputs with the source example's file hash or claim M3 qualification.

#### Scenario: Inspect a completed calculation
- **WHEN** an explicitly loaded and validated scenario completes search and provenance collection
- **THEN** the "О расчёте" panel displays the normalized input snapshot, M2 model identifier, Python/space-nav/TudatPy and resource versions, loaded kernel metadata, evaluated/solved/failed candidate counts, and SI units with SSB origin, J2000 orientation and TDB seconds since J2000
- **AND** shared model/resource/reference/version fields equal the CLI conventions for the same inputs and resources, and ignored-field and ideal-propellant limitations remain visible

#### Scenario: Bind edited input rather than the source file
- **WHEN** the user changes dry mass to 500 kg and successfully recalculates
- **THEN** the panel's detached normalized snapshot contains dry_mass_kg equal to 500, matches the scenario passed to search, and does not present the unchanged example file hash or path as the edited scenario identity

#### Scenario: Reuse the completed snapshot
- **WHEN** the slider moves or another Pareto candidate is selected without input changes
- **THEN** the search and provenance builders receive zero additional calls, the stored snapshot remains unchanged, and the selected candidate belongs to that search result

### Requirement: Atomic provenance lifecycle
The explorer SHALL publish a search result and its provenance together and SHALL invalidate them together, without fabricated resource information or stale successful output.

#### Scenario: Invalidate on edits and reload
- **WHEN** any scenario input changes or the example is reloaded after a successful calculation
- **THEN** the previous result, trajectory sample and provenance are absent until a new calculation succeeds

#### Scenario: Reject incomplete or failed calculations
- **WHEN** validation, search, provenance resource collection or trajectory sampling raises an expected domain error
- **THEN** a contextual error is shown with no previous or partial result, trajectory or provenance panel remaining

#### Scenario: Preserve existing scientific contracts
- **WHEN** the panel's regression checks execute
- **THEN** CLI payload compatibility, lazy imports, existing 100 m / 0.001 m/s sampling endpoint checks, analytic-orbit checks and unchanged legacy checksum all pass without modified tolerances or additional search calls for metadata
