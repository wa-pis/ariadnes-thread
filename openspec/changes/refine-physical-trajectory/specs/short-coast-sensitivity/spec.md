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

### Requirement: Independently validate saved operands and audit scope

The private R5 offline auditor SHALL follow ADR0143 without importing the runner,
force adapters, production package or scientific libraries. It SHALL distinguish
complete verification, partial failed-study evidence and rejected inconsistencies.

#### Scenario: Verify complete evidence without trusting passed flags

- **WHEN** complete reference evidence is audited
- **THEN** the auditor SHALL bind the four immutable input files and exact scenario/candidate/initial state, seven epochs, eight profiles,56 node-force rows,14 numerical rows and seven signed-model rows
- **AND** it SHALL independently recalculate direct forces in80/100-digit Decimal from exact saved binary64 operands and check explanatory fields and actual native node telemetry using ADR0143's retained force-arithmetic envelope, separately from the unchanged scientific state gates
- **AND** it SHALL recalculate signed differences and B-minus-A vectors, validate rounded components/norms and independently replay gate booleans at0.01m/1e-5m/s,0.001m/1e-6m/s and0.02m/2e-5m/s as applicable, without enlarging those thresholds for arithmetic agreement
- **AND** native node states/forces SHALL match raw histories and exact1s/0.5s grids with301/601 states; oracle states SHALL match the retained corrections and offsets with zero initial corrections

#### Scenario: Reject corruption and distinguish incomplete evidence

- **WHEN** evidence contains duplicate keys, nonfinite constants, boolean numbers, mismatched vectors/epochs/units/source inventory, altered raw operands/identities/counters, or a falsely successful gate
- **THEN** it SHALL be rejected rather than promoted to a verified study
- **AND** a declared failed study with unavailable downstream results SHALL produce at most a partial audit, retain available false gates/diagnostics and set study_verified=false; injected-test evidence SHALL never verify R5

#### Scenario: Audit provenance and bounded coverage honestly

- **WHEN** the separate offline audit executes
- **THEN** it SHALL make zero native imports/body queries/propagations and use a separate10s cooperative process/import/read/hash/compute/serialization/flush budget with exclusive finite output
- **AND** it SHALL check initial/final snapshots, the original ordered13-kernel manifest, pinned source/runtime/build metadata and declared current source/binary file digests without executing evidence-specified code
- **AND** complete counts SHALL satisfy four native/four oracle, total RHS<=10000, Python state reads=3*RHS+21<=30021 and5424 retained-state native guard reads with matching available call/profile ledgers
- **AND** it SHALL label saved snapshot assertions, current file rehashes and checked-node arithmetic separately, without claiming historical-memory/flush timing proof, a newly queried kernel pool, independent ephemeris truth, unsaved RHS replay or continuous safety

### Requirement: Observe bounded synthetic solver attempts before reference changes

The R5 failure diagnosis SHALL follow ADR0150's independent synthetic translating-body
fixture and preserve the failed reference. It SHALL inspect each recorded RHS, trial
and accepted endpoint without modifying the pinned integration controller.

#### Scenario: Trace a fixed analytic fixture without acquiring mission states

- **WHEN** the user-authorized synthetic diagnosis executes after implementation verification
- **THEN** it SHALL run only the three fixed10s relative/absolute-local/absolute-rounded-time cases with the declared analytic translating-body orbit, original normal solver settings and zero SPICE/Tudat state requests or R5 reference replays
- **AND** each case SHALL preserve at most3000 completed RHS and300 trial rows, with9000 total RHS and a shared10s cooperative process/import/output budget, retaining finite partial traces on failure
- **AND** RHS field consistency SHALL use independent Decimal relative operands and the existing force envelope; each trial SHALL retain h/error/scales/decision, and accepted endpoints SHALL be checked within1e-6m/1e-8m/s of the independent analytic solution
- **AND** a deterministic analytic control SHALL show exact traced-versus-vanilla final t/q/nfev parity before diagnostic use

#### Scenario: Binary search the first observed event with a monotone predicate

- **WHEN** the retained trace is searched for a deviation
- **THEN** separate cumulative prefix-any-failure predicates SHALL locate the first recorded force-envelope failure, controller rejection and accepted analytic-gate failure, with binary probes, record index and adjacent-record or trial interval retained
- **AND** oscillating raw error SHALL NOT be assumed monotone; searching SHALL NOT rerun shortened integrations, claim an exact continuous crossing or infer the historical R5 failure point
- **AND** absent events and incomplete trial decisions SHALL remain explicit rather than fabricated or promoted to mission accuracy
