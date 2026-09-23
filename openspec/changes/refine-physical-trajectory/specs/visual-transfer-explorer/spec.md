## ADDED Requirements

### Requirement: Explicit dynamics and collision-screening scope
The explorer SHALL distinguish ephemeris/display objects, forces used to propagate the spacecraft, and objects covered by collision screening. A displayed planetary track, available SPICE state, successful Lambert solution or ideal fuel-feasible candidate SHALL NOT imply gravitational inclusion, collision clearance or a safe flight corridor. Current M2 output SHALL explicitly report that small-body and space-debris screening was not performed.

#### Scenario: Explain the current M2 model
- **WHEN** a candidate trajectory is displayed
- **THEN** adjacent scope text identifies Sun-centred two-body propagation, ephemeris-based Moon/Mars endpoints and ideal impulses, and states that other displayed planetary tracks do not add their gravitational perturbations or collision checks to this arc
- **AND** uncompleted M3 multi-body force and selected-body guard components are not presented as an operational validated mission calculation

#### Scenario: Warn about unscreened objects
- **WHEN** any M2 candidate is displayed, including an ideal fuel-feasible candidate
- **THEN** the visible result area, without opening a help expander, contains "Проверка столкновений с малыми телами и космическим мусором не выполнялась"
- **AND** nearby help explicitly includes asteroids (including belt objects), comets and artificial debris, and states that no collision probability, minimum clearance or all-object safety guarantee was computed

#### Scenario: Preserve the warning across selection
- **WHEN** the user changes candidate, time sample, priority or ideal-fuel filter and a candidate remains visible
- **THEN** the unscreened-object warning remains visible without new scientific calls, changed candidate values or a fabricated safe/zero-risk status

#### Scenario: Explain catalogue limits
- **WHEN** the user reads collision-screening help
- **THEN** it states that any future catalogue-based screening would cover only identified objects and its declared time span and uncertainties, and cannot guarantee absence of unknown or untracked objects

### Requirement: Complete field and result help
The explorer SHALL provide discoverable Russian-language help for every editable scenario field, selection control and displayed scientific result. Help SHALL explain meaning in plain language, displayed units (or that a value is dimensionless), applicable validation constraints and relationships, and the parameter's actual role or lack of use in M2. Help SHALL NOT invent recommended values, silently change inputs, imply ignored fields affect M2, or equate ideal feasibility with flight safety.

#### Scenario: Cover every input and control
- **WHEN** the user inspects any field in search, departure_orbit, target_orbit, spacecraft, tracking or limits, or the elapsed-day, candidate, priority and fuel-filter controls
- **THEN** a labelled tooltip or adjacent help text is available for every rendered field/control, including fields inside collapsed sections
- **AND** automated coverage checks reject a missing or empty help entry for any rendered field/control

#### Scenario: Explain constraints and ignored inputs accurately
- **WHEN** help is opened for dates, masses, Isp, thrust, orbit orientation, tracking, seed or candidate budget
- **THEN** it states the applicable format/units and implemented validation rules, including date ordering, initial mass greater than dry mass and integer budget 1–10000
- **AND** it distinguishes required-but-ignored M2 inputs from active inputs, explains that Isp affects ideal fuel consumption while thrust does not determine burn duration in M2, and introduces no new scientific limits or defaults

#### Scenario: Explain scientific results and provenance
- **WHEN** results and the provenance panel are displayed
- **THEN** labelled help explains flight time, departure/arrival dates, delta-v versus instantaneous speed, propellant versus remaining/dry mass, ideal mass feasibility, Pareto trade-offs, grid/evaluated/solved/failed/visible counts, and the displayed model/version/kernel/input-snapshot/reference-state metadata
- **AND** time help distinguishes UTC date labels, TDB elapsed seconds and 86400-second days; frame help distinguishes scientific SSB/J2000 states from the Sun-relative XY display; units or dimensionless status accompany displayed scientific quantities

#### Scenario: Read help without changing the calculation
- **WHEN** help is opened before or after a calculation, including after a validation error or an empty filtered result
- **THEN** help for currently rendered fields remains available without additional search, sampling or provenance calls and without changing inputs, selection or stored results

### Requirement: Elapsed-day trajectory control
The explorer SHALL label the time control "Дней после старта" and display elapsed days for the existing sampled trajectory rather than sample indices. One day SHALL equal 86400 TDB seconds; the selected UTC date, marker, speed and state SHALL refer to the same sample. Sampling density and scientific tolerances SHALL remain unchanged.

#### Scenario: Explore a long transfer
- **WHEN** a manufactured 3000-day candidate is sampled at 121 evenly spaced epochs and its first, middle and last samples are selected
- **THEN** the control displays 0, 1500 and 3000 days respectively, with the corresponding sample's UTC date and state, and no additional candidate search or provenance collection occurs

#### Scenario: Switch duration
- **WHEN** the selected candidate changes to one with a different flight time
- **THEN** the control resets to that candidate's departure, its upper endpoint equals flight_time_s / 86400, and every selectable value maps to an existing sample without extrapolation or duplicate rounded-value selection

### Requirement: Visible search budget and actual grid
The explorer SHALL expose "Количество вариантов для проверки" in the main input area as the existing integer limits.max_candidates budget from 1 through 10000. It SHALL explain that this is a maximum, display the actual rectangular search grid, and preserve the existing solver and runtime limit. There SHALL be only one editor for this field.

#### Scenario: Explain the default budget
- **WHEN** the requested budget is 2000
- **THEN** the preview shows 44 departure dates × 45 flight durations = 1980 planned candidates, while completed-search evaluated, solved and failed counts retain their distinct meanings

#### Scenario: Validate and invalidate a changed budget
- **WHEN** the budget changes to 1 or 100
- **THEN** previous results and provenance are cleared, previews show 1 × 1 = 1 or 10 × 10 = 100 respectively, and the next explicit calculation receives the selected budget
- **AND** non-integer budgets and values outside 1 through 10000 cannot start a search

### Requirement: Explicit candidate selection preferences
The explorer SHALL offer "Приоритет выбора" with "Меньше топлива", "Быстрее долететь" and "Меньше Δv", plus "Только варианты, которым хватает топлива". These controls SHALL only sort/filter the returned Pareto front, not rerun search, alter scientific data or claim a global optimum. The UI SHALL disclose this scope and label feasibility as the ideal M2 mass budget, not physical safety.

#### Scenario: Sort deterministically
- **WHEN** a priority is selected
- **THEN** displayed candidates are ordered ascending by propellant_mass_kg, flight_time_s or total_delta_v_m_s respectively, with candidate_id as the deterministic tie-break
- **AND** the existing selected candidate is preserved if still visible; otherwise the first visible candidate is explicitly shown as selected, with all summary and trajectory data matching it

#### Scenario: Filter feasible candidates
- **WHEN** the fuel filter is enabled
- **THEN** only candidates whose existing mass_feasible flag is true remain, the visible and total Pareto counts are displayed, and search/provenance builders receive zero additional calls

#### Scenario: Handle no matching candidates
- **WHEN** the active filter leaves zero candidates
- **THEN** the UI shows a clear no-matching-variants message and no selected-candidate metrics or trajectory; search provenance and filter controls remain available, and disabling the filter restores the original candidate set without recalculation

#### Scenario: Honest defaults and interpretation
- **WHEN** a new search result is displayed
- **THEN** the default priority is "Меньше топлива", the feasibility filter is off, and the UI explains that fuel and delta-v rankings coincide for the fixed-spacecraft ideal rocket-equation model; no safety score or weighted multi-criterion score is presented

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
