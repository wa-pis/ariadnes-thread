## ADDED Requirements

### Requirement: Freeze a restricted integrated Earth-force sensitivity question

R5 SHALL follow ADR0137's unpowered300s SSB/J2000 component experiment from the
unchanged audited0098 initial state and R1 identity. It SHALL distinguish numeric
agreement from two-model sensitivity and full-mission physical accuracy.

#### Scenario: Preserve inputs and explicitly restrict force fidelity

- **WHEN** the R5 experiment is prepared
- **THEN** it SHALL bind ADR0137's0119/0098/0133/0136 digests, exact initial six-state, t0=978995455.2304223TDBs, tf=t0+300s and seven nodes t0+50*j for j=0..6 without phase/epoch/candidate/control changes
- **AND** model A SHALL use direct Sun/Moon point masses and B SHALL add Earth only, with fixed GMs Sun1.327124400420322e20, Moon4902800121846.8 and Earth398600435468295.9m^3/s^2 and moving geometric SPICE bodies; SSB dynamics SHALL contain no indirect-origin term
- **AND** restricted identifiers and omissions SHALL be explicit; production M3 forces/identifiers SHALL remain unchanged and constant2000kg metadata SHALL NOT imply integrated mass or reserve feasibility

### Requirement: Independently compare numerical engines before interpreting sensitivity

R5 SHALL use ADR0137's separate native Tudat RK4 and SciPy1.17.1 DOP853 force /
propagation implementations with the same frozen physical inputs and kernel pool.

#### Scenario: Complete verified preparation before one reference execution

- **WHEN** the private R5 implementations are prepared
- **THEN** analytic/Decimal central/zero-force cases, correction-coordinate equivalence, direct versus indirect forcing, exact frame/epoch/SI metadata, frozen identities/profiles/counters and error/deadline/partial-output paths SHALL pass with focused/full pytest, Ruff and strict OpenSpec before native reference execution
- **AND** existing validated input/budget/identity utilities SHALL be reused where applicable without weakening the full-model adapter or sharing force/propagation code between the numerical engines

#### Scenario: Keep profiles, comparison gates and interpretation separate

- **WHEN** one prepared R5 study executes
- **THEN** each model SHALL run independent native RK4 h1s/h0.5s and ADR0137's fixed normal/tighter DOP853 correction-variable profiles, with exact initial states and native seven-node histories, using A's complete sequence before B's
- **AND** native profile and tighter native/oracle discrepancies SHALL satisfy0.01m/1e-5m/s per node, oracle profile discrepancies0.001m/1e-6m/s, and signed B-minus-A discrepancy across tighter engines0.02m/2e-5m/s; all raw vectors/norms SHALL be retained
- **AND** no small/zero model difference SHALL trigger tuning or imply whole-mission accuracy, complete forces, rigorous integration error bounds, escape/capture, finite burns, safety, UI or strict M3/M6 qualification

### Requirement: Bound acquisition, propagation and evidence without hiding internal work

R5 SHALL execute once under ADR0137's shared60s setup/import/check/identity/solve /
comparison/serialization/flush budget, preserving finite exclusive partial evidence.

#### Scenario: Enforce call limits and fail-stop behavior

- **WHEN** the reference study runs
- **THEN** it SHALL attempt at most four native arcs, four oracle solves and10000 total oracle RHS evaluations, with separately counted Python oracle/node-table state reads<=30021 and no retries, resource replacement or changed gates/data/budget
- **AND** native internal ephemeris reads SHALL NOT be claimed included in that Python-visible query count; original ordered13-kernel and extended source/runtime/build identities SHALL agree before/after
- **AND** domain guards SHALL cover retained native states and oracle RHS calls with actual checked coverage reported; returned histories SHALL survive after-call overruns and no continuous-safety claim SHALL be made
- **AND** first unexpected failure SHALL stop with downstream checks unavailable; if resolution needs a changed contract or user action, automation SHALL pause

#### Scenario: Audit saved evidence without repeating propagation

- **WHEN** the single study produces evidence
- **THEN** a separate zero-native offline audit SHALL recompute saved-node forces, signed state/model differences, gate outcomes and identities from retained operands
- **AND** it SHALL NOT claim a replay of unsaved internal stages, independent ephemeris truth or an achieved mission
