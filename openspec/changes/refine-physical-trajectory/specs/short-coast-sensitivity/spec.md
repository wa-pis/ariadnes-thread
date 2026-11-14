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


### Requirement: Measure the effect of saved Moon/Earth position differences at 11 fixed observations

The ADR0175 paired check SHALL isolate the change in lunar point-mass
acceleration caused by substituting the saved measured position for the
R5.24 proxy, with original motion and force tolerances.

#### Scenario: Admit only the affected frozen observations

- **WHEN** R5.29 preparation is verified and R5.30 is separately authorized
- **THEN** one fresh offline run SHALL bind the finalized R5.24 and R5.27 reports, ledgers and receipts to the fixed inventory and admit only observation ordinals 1, 2, 4, 6, 11, 15, 16, 18, 20, 25 and 27 in that order
- **AND** it SHALL join by exact hi bits and ordinal across the seven saved acquisition epochs, keeping each row's own hi, lo, exact reference, motion, Earth/SSB position, direct Moon/SSB velocity, signed drift and rephasing unchanged
- **AND** the only substitution SHALL be the three Moon/Earth position words from the saved raw return; the exact separation difference before rounding SHALL equal 1000 times the exact measured-minus-proxy position in km

#### Scenario: Reproduce the proxy and test both force gates

- **WHEN** a pair has valid identity, coepoch, rephasing and exterior geometry
- **THEN** the proxy arm SHALL reproduce its archived exact separation, rounded separation and binary64 acceleration bits, reference fields at the original precision tolerance and both original gate classifications before attribution
- **AND** both arms SHALL independently check returned-geometry and overall acceleration using the unchanged Moon GM, radius, 80/100-digit independent references and inclusive envelope max(1e-15 m/s², 1e-11 times reference norm), with stable classifications and relative 1e-60 reference convergence including component zero agreement
- **AND** the report SHALL record signed measured-minus-proxy acceleration, norms, rounding and evaluation contributions, per-arm gate margins and any flips, keeping arithmetic closure distinct from the force verdicts
- **AND** sampled confirmation SHALL require all 11 pairs, valid precision and attribution checks, both measured-arm gates at both precisions, and successful finalization; a finite negative or an unresolved pair SHALL be reported separately

#### Scenario: Bound the offline study and preserve evidence

- **WHEN** the paired study runs or encounters a failure
- **THEN** it SHALL count at most 11 observation admissions, 22 binary64 and 110 Decimal Moon field evaluations within an inclusive 10 s budget including finalization, with zero SPICE or other native calls, record acquisitions, polynomial evaluations, other-body forces, propagation and optimization
- **AND** it SHALL retain exclusive finite evidence, raw pair identities, ordered counts, receipts, earliest failure and unavailable work; continue valid pairs after a finite numerical miss and stop on invalid input, identity, proxy replay, geometry or budget
- **AND** neither a pass nor a failure SHALL authorize a retry, changed sample or tolerance, R5.17 requalification, a new trajectory, strict M3 closure or a mission safety claim


### Requirement: Recheck the A coast with split lunar position assembly

R5.32–R5.34 SHALL assess a separate candidate under ADR0179 using
ADR0162's inputs, physical model, solver profiles and acceptance gates.
This SHALL NOT reopen the consumed R5.17 attempt or modify its record.

#### Scenario: Prepare the split force path without live inputs

- **WHEN** R5.33 prepares the private integrator and independent audit
- **THEN** the measured input route for all 28 frozen R5.24 observations SHALL reproduce the saved exact pre-round separation and the rounded separation and acceleration bits; the 11 differing rows SHALL use the measured R5.30 arm, and the other 17 SHALL use R5.24
- **AND** synthetic fixtures SHALL verify genuinely integrated q/w on synthetic inputs, exact controller-observation parity, nearest-even assembly, signed rephasing and fail-closed provenance, geometry, counters and finalization; focused/full no-SPICE-guarded pytest, Ruff, strict OpenSpec and frozen tested hashes SHALL pass with no live queries or retained coast solve

#### Scenario: Use the actual geocentric position at every new force evaluation

- **WHEN** verified preparation and separate authorization permit the single R5.34 study
- **THEN** each actual RHS and each shared output node SHALL acquire four geometric J2000 states at its exact binary64 hi in Sun/SSB, Moon/SSB, Earth/SSB, Moon/Earth order, without a proxy, cross-RHS cache or fallback
- **AND** the Moon path SHALL scale the two raw position legs exactly by 1000, subtract the separate spacecraft terms and add the signed rephasing from direct Moon/SSB velocity before a single nearest-even rounding of the relative vector; both pre-round and returned Moon geometries and the unchanged Sun/Earth geometries SHALL be strictly exterior before evaluating either included force
- **AND** the normal profile and all available normal-only gates SHALL pass before tighter is attempted; both profiles SHALL use the original settings, compare at the original seven coepochs with all 21 original trajectory comparisons, and assess seven outputs plus RHS ordinals 0–6 per profile, with at least one nonzero-lo RHS each, no substitution or additional callback

#### Scenario: Bound the study and check the new evidence independently

- **WHEN** the study and separate saved-data audit execute
- **THEN** the study SHALL retain the inclusive 60 s, two solves, 10,000 RHS and 1,000 trials caps, with at most 30,021 SSB and 10,007 Moon/Earth state attempts (40,028 total; 28 shared node calls), one setup, two 15-call inventories and no new native propagation, GM lookup, record acquisition, selector or optimization
- **AND** the audit SHALL use an inclusive 10 s and no native or solver work, independently reconstruct every retained RHS and output without candidate imports, and rebuild the 21 trajectory comparisons and sampled checks; both phases SHALL cap sampled work at 28 observations, 112 state checks, 56 source-force rows, 448 Decimal fields, 28 A totals and 168 retained record evaluations
- **AND** full success SHALL require the original exterior, source-parity, increment, assembly, 80/100-digit precision and force tolerances including both original force gates for Sun, Moon and A total, with additional Moon/Earth parity at 0.001 m and 1e-6 m/s and no source allowance; both processes SHALL retain exclusive finite evidence, final identity and finalized child and parent receipts
- **AND** missing inputs, a failed gate, limit or incomplete finalization SHALL preserve partial evidence and unavailable work, without retry or widening any gate; even success SHALL leave historical failures, incomplete native provenance, Earth-force sensitivity, continuous safety and strict M3/mission acceptance unchanged


### Requirement: Compare Earth gravity against the retained A coast

R5.35–R5.37 SHALL define, prepare and separately run the B-only
follow-up in ADR0182. The original R5.3 requirements and results
SHALL remain unchanged.

#### Scenario: Isolate the Earth acceleration on the same arc

- **WHEN** verified R5.36 preparation and separate authorization permit R5.37
- **THEN** the study SHALL bind the saved A native h1/h0.5 and R5.34 normal/tighter profiles, their available identities and R5.34 receipts, and SHALL reuse the frozen initial six-state, 300 s span, seven exact epochs, SI/SSB/J2000/NONE, body tracks, GMs and guards
- **AND** it SHALL run B only, using native 1 s/0.5 s RK4 and the original normal/tighter DOP853 profiles, with only direct Earth gravity added to Sun/Moon and the R5.34 split Moon retained in DOP853; it SHALL neither propagate A nor infer B by applying a field to A's saved path
- **AND** both B DOP853 profiles SHALL pass four-source parity, increment, assembly and exterior checks at the defined 28 observations and both unchanged force gates for Sun, Moon, Earth and their total at 80/100 Decimal digits; the independent audit SHALL also check retained native grids and guards, and actual native telemetry against 80/100-digit fields at all 14 native B output rows

#### Scenario: Gate signed model differences after numerical convergence

- **WHEN** B trajectories reach all seven coepochs and pass current and archived identity and source gates
- **THEN** B native profile and tighter cross-engine agreements SHALL satisfy 0.01 m / 1e-5 m/s and B DOP853 profile agreement SHALL satisfy 0.001 m / 1e-6 m/s at every node
- **AND** the study and audit SHALL independently verify both signed B-minus-A vectors and their staged vector discrepancy at each node with zero initial difference and a discrepancy no greater than 0.02 m / 2e-5 m/s
- **AND** evidence SHALL report both estimates, their discrepancy, the 300 s endpoint and comparison scale without treating small or zero effect as failure or those scales as rigorous uncertainty bounds

#### Scenario: Preserve bounded execution and conditional scope

- **WHEN** the new study and separate saved-data audit execute
- **THEN** the study SHALL have at most two native B arcs, two B DOP853 solves, 10,000 RHS, 1,000 trials, 40,028 explicit DOP853 state attempts and separate 2,712 native guard-read attempts within 60 s including finalization; native internal state reads SHALL be outside those counters
- **AND** the separate audit SHALL complete within 10 s including finalization, with no native or solver work, independently recomputing all recorded B DOP853 RHS/output arithmetic, native retained-state guards and node telemetry, the sampled force/source and signed effect checks, and verifying immutable inputs and child/parent receipts
- **AND** a missing prerequisite, failed gate, limit or missing receipt SHALL retain partial evidence and unavailable work without replay or threshold change; even a pass SHALL remain conditional on the archived native A histories with missing historical final identity, and SHALL NOT qualify continuous accuracy, safety, the full transfer or strict M3

### Requirement: Independently check the longer model B coast

R5.38–R5.40 SHALL extend only the restricted model B numerical
check under ADR0185. R5.37 and all earlier results SHALL remain
unchanged. A 600 s parking coast SHALL NOT be represented as
post-burn lunar departure or a new A/B sensitivity measurement.

#### Scenario: Prepare the longer private check offline

- **WHEN** R5.39 prepares the study and audit
- **THEN** the implementation SHALL bind the R5.37 B study and audit receipt chains and raw 0098 ignition state, preserve the original kernel order, model, GMs, guards and profile settings, and verify synthetic success, sample selection and missing coverage, profile and prefix tolerances, corrupted inputs/evidence, exclusive output, caps and timeouts
- **AND** verification SHALL include focused and full no-SPICE-guarded pytest, Ruff, strict OpenSpec and frozen input/source hashes, with zero live queries, record or force evaluations on retained inputs, or real runs

#### Scenario: Verify B states on the original and extended segments

- **WHEN** verified preparation and separate execution authorization permit the single R5.40 study
- **THEN** two RK4 profiles at 1 and 0.5 s and two independently implemented DOP853 profiles SHALL run B only from the exact original state and t0 to t0+600 s using the R5.37 force contract, without chaining from 300 s or any A solve
- **AND** all 39 prescribed profile comparisons at the 13 exact coepochs SHALL satisfy the original 0.01 m / 1e-5 m/s native and cross-engine gates and 0.001 m / 1e-6 m/s DOP853 gate, and all 28 same-profile B prefix comparisons SHALL satisfy the respective native or DOP853 limits
- **AND** both adaptive profiles SHALL pass the unchanged source, assembly, exterior, precision and force gates at 52 total observations: 13 outputs, seven initial RHS ordinals, and the first completed RHS by ordinal in each of the six subsequent 50 s intervals after 300 s, per profile
- **AND** native B SHALL retain 601 and 1,201 state/force rows and SHALL pass 26 native node telemetry comparisons and all retained guards; no required check SHALL be backfilled from another epoch or trajectory

#### Scenario: Independently audit the evidence and stop within the budget

- **WHEN** the study and independent saved-data audit execute
- **THEN** the study SHALL enforce inclusive 60 s, two native arcs, two adaptive solves, 10,000 RHS, 1,000 trials, 40,052 explicit adaptive state attempts and 5,412 native guard reads through finalization, excluding unobserved native internal requests
- **AND** the separate audit SHALL enforce an inclusive 10 s limit and zero native calls, scientific imports or solves while reconstructing all retained adaptive RHS and output arithmetic, sampled checks, native guards and telemetry, 67 trajectory comparisons and counters from saved evidence
- **AND** only complete required gates, matching current identities and all four phase receipts SHALL allow a pass; a missing input, failed gate, exhausted cap or incomplete finalization SHALL retain partial evidence without retry, changing controls or upgrading any M3 or mission qualification

### Requirement: Check the fixed post-cutoff lunar coast

R5.41–R5.43 SHALL separately test same-model numerical agreement and
sampled outward motion during 600 s of unpowered model B motion
from the archived nominal departure cutoff. The diagnostic SHALL NOT
substitute a parking or target state, qualify the burn or alter
the configured production M3 interface.

#### Scenario: Bind the archived boundary and prepare offline

- **WHEN** R5.42 prepares the private study and audit
- **THEN** they SHALL bind the exact 0079 nominal cutoff (state slot 1, mass 1351.7475727997967 kg, epoch 978998315.9635216 TDB s since J2000) to the matching 0098 completed baseline departure-cutoff, departure burn and R1 scenario/candidate; they SHALL independently check stored mass-law arithmetic at the represented burn interval within the existing mass gate and reject a label, identity, frame, epoch or mass mismatch
- **AND** the verification SHALL cover outward, zero and inward samples, invalid/altered input and evidence, arithmetic and partial/finalization/cap failures, with focused and full no-SPICE-guarded pytest, Ruff, strict OpenSpec and frozen hashes; no real query, propagation or retained force or polynomial evaluation SHALL occur

#### Scenario: Compare the same unpowered model from the same cutoff

- **WHEN** verified preparation and separate authorization permit the single R5.43 study
- **THEN** from that exact epoch and six-state the study SHALL run RK4 at 1 and 0.5 s and independently implemented DOP853 normal and tighter with the R5.40 profiles, source and force contract, geometric SI/SSB/J2000/TDB/NONE and constant cutoff mass as metadata, stopping at cutoff plus 600 s with zero thrust or mass flow and no burn or model A propagation
- **AND** all 39 comparisons at the 13 exact coepochs SHALL use the original 0.01 m / 1e-5 m/s native and tighter cross-engine gates and 0.001 m / 1e-6 m/s DOP853 gate; all 52 adaptive observations, 26 native telemetry rows and both retained guard histories SHALL pass the unchanged R5.40 criteria, without using parking-coast samples or obtaining additional states for direction

#### Scenario: Distinguish numerical agreement from outward direction

- **WHEN** all numerical evidence and the independent audit are complete and pass
- **THEN** evidence SHALL report the Moon-relative radius in m, signed radial speed in m/s and osculating specific energy in m²/s² for all 52 profile nodes, using the common saved Moon/SSB states; the audit SHALL reproduce the values within 1e-6 m, 1e-9 m/s and 1e-6 m²/s² and each net range change within 1e-6 m, and derive radial and net range signs independently from exact raw operands
- **AND** `outbound-at-samples` SHALL require strictly positive radial signs at every node and strictly positive end-minus-start range in all four profiles; an audited zero or negative sign SHALL be retained as `outbound-not-established` even when the numerical comparison passes; missing or failed required evidence SHALL give `unavailable`
- **AND** neither agreement nor positive direction or osculating energy SHALL qualify continuous outward motion, escape, burn accuracy, safety, transfer closure or strict M3

#### Scenario: Audit one bounded attempt and preserve partial evidence

- **WHEN** R5.43 runs the authorized study and offline audit
- **THEN** the study SHALL enforce the unchanged R5.40 propagation, RHS, trial, source operation and 60 s finalization ceilings; the audit SHALL enforce a 10 s finalization limit with zero native calls, scientific imports and solves and independently reconstruct the handoff, checks, guards, diagnostics and ledgers from saved operands
- **AND** only matching frozen identities and four bound phase receipts with all required gates SHALL allow numerical acceptance; a missing or failed input, guard, limit or receipt SHALL retain partial or unavailable evidence without changing the cutoff, horizon, model or gates and without retry

### Requirement: Check a retained lunar range event

R5.44–R5.45 SHALL verify whether the retained model B histories
bracket the explicitly retrospective lunar-centred 3,000,000 m
diagnostic marker using the saved R5.43 states only.

#### Scenario: Check both numerical engines from retained operands

- **WHEN** the offline worksheet is verified on artificial boundary and failure cases and reads the pinned R5.43 study and audit
- **THEN** it SHALL bind the exact archived cutoff, frame, time scale, units, force model, mass, grids, hashes and passed numerical evidence; process exactly 52 coepoch and 1,802 retained native rows, excluding two preflight Moon records; independently compute signs from exact dyadic and 80-digit Decimal operands with exact sign agreement and range and radial-speed agreement within 1e-6 m and 1e-9 m/s
- **AND** one strict below-to-above pair with positive endpoint radial signs SHALL be present per grid; the four coepoch brackets SHALL coincide, the 1 s and 0.5 s brackets SHALL overlap and each SHALL be contained in the common 50 s bracket; preserve individual brackets and report exact zero, inward or multiple pairs, missing inputs and disagreement as distinct evidence

#### Scenario: Preserve the boundary between diagnostics and mission verification

- **WHEN** the worksheet runs once under its 10 s inclusive offline cap
- **THEN** it SHALL make no new SPICE calls, scientific imports, kernel loads, record evaluations or integrations and SHALL retain actual counts, signed endpoints, source hashes, budget and complete or partial evidence without replacing the marker, relaxing gates or retrying
- **AND** a pass SHALL describe a retrospective sampled bracket for each saved continuous model trajectory, with no interpolated crossing time or first-crossing, escape, continuous safety, force-switch, mission handoff or M3 qualification claim
