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

### Requirement: Attribute a synthetic rejection without reintegration

The next R5 diagnosis SHALL follow ADR0151's bounded frozen-stage arithmetic
contract and preserve all reference and synthetic integration histories.

#### Scenario: Separate clock, geometry and field contributions

- **WHEN** the saved first trial of each ADR0150 arm is inspected
- **THEN** exactly39 retained stage operands SHALL be checked at80/100 Decimal digits under5s with zero scientific imports, body queries or integrations
- **AND** signed clock/reference, geometry/clock and actual/geometry field and E5/E3 differences SHALL telescope at fixed states/scales; rebuilt coefficient hashes, abscissae, counters, scales and observed error components SHALL pass the declared arithmetic bounds
- **AND** scalar norm contributions SHALL NOT be added; diagnostic boxes spanning1 or failed1e-40 precision convergence SHALL remain ambiguous/failed without changing scientific gates
- **AND** finite exclusive evidence SHALL distinguish this frozen-stage attribution from corrected-solver behavior, historical R5 causality, continuous crossing, physical fidelity and mission safety

### Requirement: Validate a compensated synthetic solve before real-state changes

The candidate SHALL follow ADR0152's combined compensated-time/relative-assembly
contract, preserving the returned binary64 source-position floor and all R5 data.

#### Scenario: Verify arithmetic and a bounded corrected solve

- **WHEN** the user-authorized candidate is implemented
- **THEN** exact TwoSum/Decimal/sign/invalid-input/source-isolation/candidate tracer-parity/cap/deadline/exclusive-output checks SHALL pass with focused/full pytest, Ruff and strict OpenSpec before one retained execution
- **AND** that execution SHALL use only the unchanged10s synthetic fixture and original settings, at most3000 completed RHS/300 retained trials/shared10s budget, with zero SPICE/Tudat queries or R5 replays and finite partial evidence on failure
- **AND** every retained force SHALL pass the existing envelope, every accepted endpoint and the final retained-control comparison SHALL pass1e-6m/1e-8m/s gates
- **AND** first-trial acceptance and RHS<=241 SHALL be reported as separate predeclared behavioral/efficiency targets, not scientific tolerances
- **AND** returned rounded source states, exact epoch low parts, raw phase residuals and compensated separations SHALL be retained; no successful synthetic result SHALL qualify a real-SPICE fix, historical R5 cause or mission safety


### Requirement: Check real ephemeris compensation independently at the time boundary

The real-source candidate SHALL follow ADR0153 before any new real-force solve.

#### Scenario: Audit fixed source samples without spacecraft propagation

- **WHEN** the user-authorized real boundary study executes after focused/full tests, Ruff and strict OpenSpec
- **THEN** exactly seven frozen elapsed times and Sun/Earth/Moon SHALL use unchanged R5 inputs and13 kernels, SSB/J2000/NONE, under shared60s and21 state/28 selection/6 array-read caps with finite exclusive partial evidence on failure
- **AND** exact rational evaluation of selected Type2 records and derivatives SHALL independently check SPICE rounded-epoch states within0.001m/0.000001m/s, and compensated increments within1e-12m plus the separate exact component Taylor/velocity/product-rounding bounds
- **AND** unsupported types/frames/centres, changed identities, bad layouts or crossed record/segment coverage SHALL fail without fallback, retry, integration or scientific-gate changes
- **AND** returned position floor, signed hi/lo, raw records, counters and correction errors SHALL remain auditable separately; success SHALL NOT imply real-force/solve qualification, independent ephemeris truth, historical R5 cause or mission safety


### Requirement: Check real-source gravity at a frozen spacecraft position

The next force check SHALL follow ADR0156, independently of any new integration.
The retained native source discrepancy SHALL remain included in overall agreement.

#### Scenario: Freeze genuine saved operands without inventing a trajectory

- **WHEN** R5.9's fixed-position check is prepared
- **THEN** it SHALL bind ADR0156's0136/0148/0155 digests, exact0136/0148 endpoint equality and the unchanged saved binary64 X position at all seven ADR0155 source offsets, producing exactly21 source rows and14 A/B model totals on completion
- **AND** the repeated X SHALL be labelled a spatial arithmetic probe, not propagated or interpolated spacecraft states; no nearby native grid epoch SHALL be substituted for an exact hi+lo epoch
- **AND** SI/SSB/J2000/NONE, the saved13-kernel provenance, Type2/frame/centre/coverage checks and R5 Sun/Moon/Earth GMs SHALL remain unchanged; the different ADR0133 SPICE lunar GM SHALL NOT replace the frozen R5 coefficient
- **AND** both models SHALL use direct SSB point gravity only, with A=Sun/Moon and B=Sun/Moon/Earth; omissions, zero native acquisition and unqualified moving-spacecraft drift/correction assembly SHALL be explicit

#### Scenario: Separate error attribution while preserving the overall gate

- **WHEN** the21 real-source rows are evaluated after verified preparation
- **THEN** binary64 source positions and velocity-times-low-time corrections SHALL remain separate through ADR0156's fsum relative assembly and fixed force expression; uncorrected and wrong-sign arms SHALL remain labelled diagnostic controls
- **AND** exact rational Type2 reconstruction and independent80/100-digit Decimal force evaluation SHALL check ADR0156's four geometries, relative1e-60 precision convergence, vector telescoping, unchanged gate classifications and all three exterior-domain guards before fields
- **AND** per-source returned-geometry and overall exact-polynomial force discrepancies SHALL each satisfy max(1e-15m/s^2,1e-11 times their corresponding reference norm); each model-total scale SHALL use the sum of constituent reference norms
- **AND** native source, residual rephasing, relative-assembly and field-evaluation contributions SHALL remain signed and separately auditable; the overall gate SHALL include all four without subtracting a source floor or adding allowances
- **AND** diagnostic false gates SHALL NOT stop required checks; a failed/ambiguous required gate SHALL stop with downstream checks unavailable, without tuning inputs, precision, constants, tolerances or budgets

#### Scenario: Verify preparation and bounded saved-data execution separately

- **WHEN** R5.10 preparation or a later R5.11 retained execution is undertaken
- **THEN** independent analytic3D/zero/cancellation and mutation fixtures, exact-input/epoch/domain/source/GM/hash checks, precision/gate boundaries and partial/count/deadline/exclusive-output paths SHALL pass focused/full pytest, Ruff and strict OpenSpec before the retained study
- **AND** one future offline study SHALL use shared10s from process start through flush/post-flush checks, at most21 source rows/168 Decimal reference fields/63 binary64 source fields, with zero scientific imports, native calls, kernel loads, GM acquisitions, propagations or R5 replays
- **AND** a separate independent saved-data audit SHALL use its own10s/168-reference-field cap and zero native/scientific calls, reconstructing raw operands, signed vectors, model sums, gates and counters without candidate force/assembly imports or trusted passed flags
- **AND** fresh finite exclusive evidence SHALL preserve exact operands/identities, attempted/completed counters and failures; complete success requires all21 rows/14 totals and both required gates plus precision/domain/identity/budget/audit checks, without retry or overwritten history
- **AND** success SHALL NOT qualify an independent ephemeris, moving-spacecraft force adapter, corrected integration, historical R5 cause, omitted-force sensitivity, strict M3 or mission safety; automation SHALL remain PAUSED


### Requirement: Verify controlled moving-coordinate assembly before propagation

R5.12-R5.14 SHALL follow ADR0159 to isolate drift/correction-coordinate arithmetic
using the retained real sources and a labelled controlled kinematic probe.
This contract SHALL preserve previous force gates and SHALL NOT start a solve.

#### Scenario: Bind genuine anchors and explicitly manufacture correction inputs

- **WHEN** the moving-coordinate check is prepared
- **THEN** it SHALL bind ADR0159's six artifact hashes, exact0136/0148 initial r0/v0, seven0155 offsets and exact T=t0+s=hi+lo identities, unchanged SI/SSB/J2000/NONE, saved13-kernel INPOP19a provenance/coverage and R5 GMs
- **AND** one controlled probe SHALL prescribe a_fixture=(-1,1/2,-1/4)m/s^2, exact rational q_ideal=a_fixture*s^2/2 and w_ideal=a_fixture*s, rounded once to binary64 q(m)/w(m/s) with nearest/ties-even, half-ulp and exact-zero checks; fractions/hex/errors and manufactured provenance SHALL be retained
- **AND** assembly targets SHALL be exact(r0)+exact(v0)*exact(s)+exact(q) and exact(v0)+exact(w); fixture quantization SHALL remain separately reported input construction, without claiming accuracy of future solver corrections
- **AND** no nearby0148 native grid state, interpolation, new acquisition or solver-produced correction SHALL be substituted; only elapsed zero is a genuine saved coepoch spacecraft state
- **AND** labels SHALL identify controlled-kinematic-arithmetic-probe, not a physically integrated trajectory or new mission parameter/default; the first six-state and compensated source/model vectors SHALL exactly reproduce saved0158 elapsed-zero values without replay

#### Scenario: Compare split assembly with exact operands and unchanged force gates

- **WHEN** each prescribed six-state and its three body separations are assembled
- **THEN** the candidate SHALL keep Dhat=RN(v0*s), q, Bhat and c=RN(Vhat_body*lo) separate, exporting Xhat=fsum(r0,Dhat,q), Uhat=fsum(v0,w) but using dhat=fsum(Bhat,-r0,-Dhat,-q,c) directly for the unchanged binary64 force expression
- **AND** an independent Fraction oracle SHALL require per-component product error<=ulp(Dhat)/2 m, position error<=ulp(Dhat)/2+ulp(Xhat) m, velocity error<=ulp(Uhat) m/s and relative-sum error<=ulp(dhat) m, with exact rational bounds including subnormals and even-significand tie checks for fixture conversions/RN products; zero results SHALL be required for exact-zero sums of actual fsum operands, not R* before product rounding, and ulp criteria SHALL be predeclared pinned-build acceptance to be tested, not a measured result or universal theorem
- **AND** four exact geometries d0=P(T)-R*, d1=P(T)+eB-R*, d2=exact(Bhat)+exact(c)-exact(r0)-exact(Dhat)-exact(q), d3=exact(dhat), eB=exact(Bhat)-P(hi), SHALL use hash-pinned Type2 reconstruction and independent80/100-digit Decimal forces
- **AND** exact d2-d1 SHALL equal the source-increment error minus the drift-product error; retained signed force terms SHALL distinguish native source, combined rephasing/drift-product, relative assembly and field evaluation, telescoping before norms and model aggregation
- **AND** every source and A/B total SHALL satisfy both original max(1e-15m/s^2,1e-11*Sk) force gates, with source reference norms and model sums of constituent norms; source/drift errors SHALL remain included without allowances or floor subtraction, with relative1e-60 precision convergence and unchanged classifications
- **AND** flattened-craft and omitted-q controls SHALL be compared only with F(d0) under its overall envelope; false diagnostic force gates alone SHALL NOT stop, and universal control failure/improvement SHALL NOT be presumed
- **AND** all reference/candidate/control geometries SHALL satisfy original strict Sun/Moon/Earth exterior guards before fields, including Earth for A; invalid domain, required assembly/force/precision/identity failure SHALL stop without changing operands/gates

#### Scenario: Verify preparation without promoting unimplemented work

- **WHEN** R5.13 prepares private assembly, reference and saved-data audit paths
- **THEN** independent analytic3D/zero/cancellation, nonzero drift/q/w, sign/component/source/time/GM/hash/domain mutations, omitted terms/early flattening, rounding/tie/subnormal and partial/count/deadline/exclusive-output fixtures SHALL pass focused/full pytest, Ruff and strict OpenSpec with frozen checkout/source hashes
- **AND** each required mutation SHALL fail at least one named independent fixture; historical helpers/evidence/production/dependencies SHALL remain unchanged, with tested hashes saved before retained execution
- **AND** design acceptance or prior5630 tests SHALL NOT count as implementation coverage or a measured moving-probe result

#### Scenario: Bound one later study and an independent saved-data audit

- **WHEN** verified R5.13 and execution authorization permit R5.14
- **THEN** one stdlib-only study SHALL use shared10s from an external pre-child-start timestamp through imports/setup/reads/hashes/fixture construction/computation/serialization/flush/post-flush check, with caps seven six-state assemblies/21 source rows/168 Decimal fields/63 binary64 source fields/14 model totals and ordered attempted/completed ledgers
- **AND** a separate saved-data auditor SHALL use its own10s and the same caps, independently rebuilding prescribed inputs, exact sums/geometries, fields/gates and identities without candidate assembly/force imports or trusted flags; sharing the pinned independent reference SHALL NOT be called an independent ephemeris or second reference-force implementation
- **AND** both SHALL make zero scientific-library imports/native calls/kernel loads/GM acquisitions/propagations/optimizer calls/R5 replays, bind tested code/pinned runtime and before/after inputs/helpers, and preserve finite exclusive raw/partial evidence, earliest failure and late-finalization downgrades
- **AND** complete success SHALL require all seven/21/168/63/14 operations and required component/force/domain/precision/identity/budget gates plus the separate audit; incomplete/corrupt records SHALL remain partial/rejected without retry, added profiles or operand/gate/budget changes
- **AND** success SHALL qualify only assembly with the prescribed binary64 inputs; corrected integration, physical correction accuracy, historical R5 cause, trajectory sensitivity, continuous safety and strict M3/mission closure SHALL remain unverified, with automation PAUSED


### Requirement: Bound a corrected real-input integration before force sensitivity

R5.15-R5.17 SHALL follow ADR0162's A-only numerical-verification contract,
preserving the failed R5.3 evidence, original physical inputs and scientific gates.
Design acceptance SHALL NOT count as preparation or execution completion.

#### Scenario: Freeze a genuine correction-coordinate integration

- **WHEN** R5.16 prepares the candidate after R5.15 design acceptance
- **THEN** it SHALL bind ADR0162's saved initial six-state/t0,300s interval, seven exact50s output nodes, retained301/601 native grids,13 ordered kernels, SI/SSB/J2000/TDB/NONE and original Sun/Moon GMs, using Earth only as guard/source-chain input
- **AND** it SHALL use genuine q'=w,w'=a and zero q/w initial state, TwoSum epochs, unchanged live spkezr-to-SI operations and ADR0159's split separation/field order, without manufactured corrections or flattened force inputs
- **AND** normal/tighter DOP853 SHALL retain ADR0162's original rtol/atol/max_step/first_step settings; observer parity SHALL be exact on analytic fixtures, with no extra real solve or change to controller behavior
- **AND** independent arithmetic/force/profile/coepoch/identity/domain/mutation and partial/count/deadline/exclusive-finalization fixtures SHALL pass focused/full pytest, Ruff, strict OpenSpec and frozen-source checks before retained execution

#### Scenario: Compare unchanged trajectory gates and predetermined force samples

- **WHEN** verified preparation and separate execution authorization permit R5.17
- **THEN** at most two A solve attempts SHALL run normal then tighter, with fail-stop before tighter if normal or an already-checkable required gate fails; full success SHALL require both complete profiles and every fixed output comparison: saved h1/h0.5 and saved h0.5/corrected tighter within0.01m/1e-5m/s, corrected normal/tighter within0.001m/1e-6m/s
- **AND** each profile SHALL preselect seven outputs and first seven completed RHS by ordinal, requiring a nonzero-lo RHS sample per profile, without backfill or adaptive source queries; full success SHALL include28 observations/84 body checks/56 included-source rows/448 Decimal fields/28 sampled A totals
- **AND** selected raw returns SHALL pass original0.001m/1e-6m/s Type2 source parity,1e-12m plus explicit Taylor/velocity/product terms, independent Fraction assembly bounds and four-geometry80/100-digit force checks with relative1e-60 convergence/stable classifications/telescoping
- **AND** both returned-geometry and overall source/model force errors SHALL satisfy max(1e-15m/s^2,1e-11*Sk), with source or constituent-norm scales and no source-floor subtraction/allowance; actual q/w accuracy SHALL NOT be inferred from operand bounds
- **AND** the14 native comparison states SHALL pass42 guard-separation checks using the shared node table, and every runtime geometry and every selected independent reference geometry SHALL pass all original Sun/Moon/Earth exterior guards before its fields; deferred reference failures SHALL stop when checked without claiming earlier detection

#### Scenario: Retain one bounded study and independently audit its saved data

- **WHEN** R5.17 executes the frozen tested helpers
- **THEN** one study SHALL share60s through process start/import/setup/identity/two solves/checks/flush, with global caps10000 attempted RHS,3*N_RHS+21<=30021 live state requests,1000 trial descriptors,2*(N_RHS+14)<=20028 binary64 fields andN_RHS+14<=10014 dynamic A totals
- **AND** it SHALL acquire one shared21-call node table, initialize the unchanged13-kernel pool once, inventory it before/after in at most two snapshots with separately counted metadata APIs, and make zero new native spacecraft propagations/GM lookups/selector reads/optimizer calls; the state-request cap SHALL NOT be described as a total native-call count
- **AND** a separate fresh stdlib-only audit SHALL use its own inclusive10s, zero scientific/native queries or solves, at most20028 independently reconstructed binary64 fields and the same28/84/56/448/28 sample caps, rebuilding all RHS arithmetic/epochs/guards/counters, trajectory comparisons, sampled references and required gates without candidate imports or trusted flags
- **AND** exclusive finite raw/partial evidence SHALL retain before/after identities, every returned operand/array before post-call checks, ordered counters/traces, unavailable downstream checks, earliest failure and finalization; no retry, profile/budget/input/gate change or real parity replay SHALL be allowed
- **AND** full success SHALL require both completed solves, all seven outputs, required gates/counts/identities/budgets and both finalizations plus the separate audit; missing historical0148 final identity SHALL remain explicit, with no retroactive provenance repair
- **AND** sampled numerical agreement SHALL NOT qualify unsampled source selection, continuous safety, R5.3 causality, Earth-force sensitivity, astronomical truth or strict M3/mission readiness; automation SHALL remain PAUSED


### Requirement: Observe both lunar ephemeris legs before considering another coast

R5.19–R5.21 SHALL follow ADR0166's fixed-epoch, source-only probe with a separate
static Moon-force analysis. This requirement SHALL NOT modify the ADR0162
contract or reinterpret the failed R5.17 result.

#### Scenario: Freeze a fixed sample and capture two legs plus direct state

- **WHEN** R5.20 preparation is verified and R5.21 is separately authorized
- **THEN** one fresh capture SHALL use normal RHS 6 at local 0.25 s, output 0 at 0 s and output 5 at 250 s in that order, binding exact saved `hi`/`lo=+0`, initial state, motion, archive and reference bytes
- **AND** it SHALL issue exactly Earth/SSB, Moon/Earth and Moon/SSB `spkezr` queries per epoch on success, preserving six raw km/km/s components and finite light time, with TDB/J2000/NONE and no rephasing
- **AND** it SHALL verify the frozen 13-kernel pool and runtime/library/helper/input identities before and after, and after all nine state reads retain two `spksfs` selections per epoch, in the same epoch order for 399 then 301 with `idlen=128`, matching the frozen 399→0 and 301→399 Type 2 descriptors/handle/coverage/record index
- **AND** explicit attempts SHALL be capped at one setup, 30 inventory API calls, nine state queries and six selectors within the inclusive 15 s capture budget; new Type 2 reads/evaluations, GM queries, propagations and optimiser calls SHALL be zero

#### Scenario: Separate position closure from the static force result

- **WHEN** the fresh zero-native offline analyzer processes the retained capture
- **THEN** it SHALL verify the ledger, identity, deadlines and receipts, require all 36 Earth/SSB and Moon/SSB raw components to match the archive bitwise, and check each of the nine states against the saved exact reference within 0.001 m and 1e-6 m/s using squared SI norms
- **AND** it SHALL report all nine bitwise nearest-even position closures and exact signed source/closure/SI attribution; velocity and geocentric nearest-bit diagnostics SHALL NOT substitute for this position gate, and a finite closure miss SHALL NOT suppress static diagnostics whose prerequisites still hold
- **AND** it SHALL construct the four ADR0166 exact geometries at the saved motion operands without rounding either SI leg or a barycentric sum, verify one final nearest-even separation rounding and strictly exterior lunar geometry before fields, and compute at most three new binary64 and 18 new Decimal Moon fields using the original GM and 80/100-digit reference discipline
- **AND** returned-geometry and overall Moon errors SHALL each meet `max(1e-15 m/s^2,1e-11*norm(reference))` on a pass, including all source error, with relative 1e-60 precision convergence, stable classifications and ADR0166 telescoping; no force result SHALL be qualified without valid provenance and state parity
- **AND** full sampled confirmation SHALL require valid finalizations, closure 9/9 and both static gates at all three epochs within the inclusive 10 s offline budget, preserving closure and static outcomes separately, with no native imports or calls and no new polynomial evaluation

#### Scenario: Preserve bounded negative evidence and pending work

- **WHEN** capture or analysis encounters an invalid return, identity, coverage, domain, deadline or numerical gate failure
- **THEN** the exclusive finite evidence SHALL retain the earliest failure, attempted/returned/completed ledger, raw return prefix and unavailable checks, with no retry, substituted epoch, source or tolerance
- **AND** passing or negative diagnostics SHALL leave the R5.17 verdict, R5.3, force sensitivity, full-trajectory qualification and strict M3 unchanged; no continuous or mission safety claim or automation resumption is permitted


### Requirement: Screen the split Moon source on the original frozen sample

The conditional ADR0169 screen SHALL preserve ADR0162's sample and limits
on numerical errors and SHALL leave historical experiment outcomes intact.

#### Scenario: Bind observed and modeled operands to saved motion

- **WHEN** the verified R5.23 preparation is used for R5.24
- **THEN** one fresh offline process SHALL use exactly the normal and tighter profiles' seven saved outputs and first seven completed RHS observations each, in that order, retaining duplicates, actual motion, 19 rounded hi epochs and all ten signed nonzero low words
- **AND** it SHALL use finalized R5.21 measured E/G/B at three hi epochs (seven observations) and clearly label the rounded exact-record G proxy at the other 16 hi epochs (21 observations), without reporting proxy parity or closure as an observed SPICE result
- **AND** it SHALL verify the archived input/record identities, exact hi/lo coepochs, same-model state parity for archived E/B and measured G within 0.001 m and 1e-6 m/s, and record coverage at hi and T

#### Scenario: Preserve rephasing and measure both lunar force errors

- **WHEN** a frozen observation has valid identity, state parity and motion
- **THEN** it SHALL preserve the original rounded SI direct-velocity rephasing and drift products bitwise, verify the 1e-12 m time increment and signed terms, retain the two source position legs through exact relative subtraction, and round the separation once to nearest-even
- **AND** it SHALL independently reconstruct d0–d3 and verify exact and binary64 exterior lunar geometry, signed attribution, both force gates with unchanged Moon GM and envelope, 80/100-digit relative 1e-60 convergence, stable classifications, and the three original measured controls
- **AND** full conditional confirmation SHALL require valid finalization and both Moon gates at all 28 points, with measured and proxy outcomes reported separately; no claim about a continuous arc, changed provider or Earth sensitivity is permitted

#### Scenario: Stop within the saved-data budget and retain negatives

- **WHEN** the offline screen runs or encounters a failure
- **THEN** it SHALL count at most 28 observations, 29 distinct reference epochs, 58 record evaluations, 28 binary64 and 224 Decimal Moon fields under an inclusive 10 s budget, with zero native calls, new record acquisition, trajectory propagation and optimisation
- **AND** it SHALL preserve finite exclusive evidence, ordered counts, earliest failure and unavailable checks; a finite numerical miss may leave other fixed rows available but SHALL NOT authorize new acquisition, retry, a changed gate or R5.17 requalification


### Requirement: Check the geocentric Moon source at the 16 frozen proxy epochs

The ADR0172 holdout SHALL evaluate the Moon position source at the R5.24
rounded epochs without recomputing forces or propagating the spacecraft.

#### Scenario: Bind the one future capture to the previously unmeasured epochs

- **WHEN** R5.26 preparation is verified and R5.27 execution is separately authorized
- **THEN** one capture SHALL use only the 16 exact binary64 hi epochs in the fixed first-occurrence order in the holdout inventory, preserving their mapping to all 21 R5.24 proxy rows and excluding the 3 previously measured hi epochs
- **AND** it SHALL confirm the pinned provider, shared ordered 13-kernel pool and applicable INPOP19a Type 2 Moon 301→Earth 399 segment and record coverage, then capture one raw geometric Moon-relative-to-Earth state (J2000, NONE, km and km/s) at each hi without new Earth/SSB or Moon/SSB queries

#### Scenario: Separate parity, operand equivalence and archived closure

- **WHEN** finalized capture evidence and the frozen references have valid identities
- **THEN** one offline analysis SHALL compare all 16 raw states to the retained exact SI states using position error norm at most 0.001 m and velocity error norm at most 1e-6 m/s, and report each verdict
- **AND** it SHALL report all 48 position components' bit comparisons to the archived rounded proxy, including signed zero, and separately report all 48 round-once Earth/SSB-plus-Moon/Earth component comparisons to the archived Moon/SSB position
- **AND** confirmation SHALL require valid finalization, all 16 state parity checks and all 48 proxy and 48 closure comparisons to pass; a parity pass with a proxy bit miss SHALL remain a distinct result and SHALL NOT establish equivalence or change any historical force verdict

#### Scenario: Preserve the capture and analysis limits on failure

- **WHEN** the holdout executes or encounters a failure
- **THEN** the capture SHALL attempt at most 1 setup, 30 inventory calls, 16 Moon segment selectors and 16 Moon/Earth state calls under an inclusive 15 s deadline, and the offline analysis SHALL attempt at most 16 epoch checks and complete under an inclusive 10 s deadline with zero native calls
- **AND** the capture and analysis SHALL retain finite exclusive evidence, ordered counts, earliest failure and unavailable checks, with a finite numerical miss distinguished from invalid input, identity, domain or budget
- **AND** neither phase SHALL acquire new explicit Type 2 records, evaluate a record polynomial or field in the diagnostic, propagate a trajectory, optimize, retry or authorize R5.17 requalification
