## ADDED Requirements

### Requirement: Keep split-Time enclosures conditional on the conversion basis

Split-Time readback preparation SHALL follow ADR0257's conditional adjacent-
binary64 derivation. It SHALL distinguish a valid mathematical enclosure from
qualification of the installed exporter, actual event carry and physical gates.

#### Scenario: Enclose only under an established finite conversion route

- **WHEN** exact native integer-hour export, finite in-range native remainder and the complete single-narrowing/CPython-storage route are independently qualified for the pinned build
- **THEN** the stored epoch is enclosed by exact3600*h plus the rational values of prev64(y) and next64(y), without assuming nearest half-ULP rounding or a long-double mantissa
- **AND** both neighbour endpoints must be finite; unqualified normalization is not used to clip the interval and the original h/y words, signed zero and a rounded3600 are retained

#### Scenario: Keep the actual missing source basis unavailable

- **WHEN** exact caster/build provenance or the lawful finite native-domain premise is missing, even if exported y is finite or reconstruction roundtrip succeeds
- **THEN** actual readback remains unavailable; different Python-ABI recipes, type labels, hashes and flags cannot supply the missing premise
- **AND** failed reconstruction roundtrip forbids exact serialization but does not itself refute a separately qualified conservative enclosure

#### Scenario: Preserve physical obligations and finite preparation limits

- **WHEN** the conditional source-level enclosure design is accepted
- **THEN** requested Fraction events, actual native Time/state/mass carry, signed span errors, commanded/effective ledgers, unchanged floor/matching and independent clock/force/endpoint gates remain separate obligations under ADR0255/0205
- **AND** the stage uses at most600s of scoped source review and zero native imports, tests, SPICE, command/trajectory/oracle evaluations, integration or optimizer calls; no native campaign or physical admission follows

#### Scenario: Preserve a failed exact-build source lookup without promoting its records

- **WHEN** the one ADR0258 source lookup ends incomplete after partial metadata capture
- **THEN** preserve its original failure/partial and resource receipts, verify saved artifact/metadata facts separately, and retain missing caster/build/finite-domain qualification as unavailable
- **AND** recipe/source declarations do not become compiled-header or physical proof; no hidden retry, artifact refetch, controller replay or native campaign follows, and any distinct missing-source continuation requires a finite scoped contract

#### Scenario: Continue only the missing pinned primary-source step

- **WHEN** ADR0259 continues from the saved0258 recipe/Git declarations
- **THEN** one noninteractive source session binds the fixed TudatPy checkout and exact pybind11 tag/immutable header commit, with at most one annotated-tag dereference and no current-HEAD substitution, package refetch or consumed-controller replay
- **AND** outer600s/per-response60s watchdogs,6actual HTTP responses,256KiB per body and separate2MiB aggregate raw-body/decoded-source/retained-evidence ledgers cover errors, partials, logs and finalization; redirects/compression/unsupported chains fail closed with zero new archive members or runtime/scientific work
- **AND** source/dependency declarations stay separate from compiled-header/effective-FP/lawful-domain evidence; missing premises keep actual readback and physical admission unavailable

#### Scenario: Separate pre-export construction facts from propagated readback

- **WHEN** ADR0260 reviews the named retained-source Time construction/copy/export route
- **THEN** record explicit finite/input/FP/selection and integer-range preconditions separately from justified construction/normalization/copy/getter invariants, with pinned hashes/line anchors and source reasoning<=600s
- **AND** finite output/roundtrip cannot supply pre-export safety; any missing primitive remains unavailable and the narrow route cannot qualify arbitrary propagated keys, native carry or physical gates
- **AND** no new HTTP, code, tests, native import, SPICE, numerical/scientific evaluation or integration occurs

#### Scenario: Design admission before original-key copying and narrowing

- **WHEN** ADR0261 traces the existing F7 producer/reader and direct native-history binding
- **THEN** distinguish an available original-key reference/guard from a proposed primitive and a qualified profile, with pinned route/lifetime/key-state-mass association and pre-copy/pre-narrowing finite/range obligations
- **AND** no post-export reconstruction/flag, substitute normalized key or current-field check certifies original provenance or earlier arithmetic; unknown stays unavailable
- **AND** source/design reasoning<=600s adds no HTTP, code, native build/dependency, tests, SPICE/scientific evaluation or integration; a necessary user build/dependency/scientific-contract decision pauses automation before implementation

#### Scenario: Prepare one bounded native build-route decision

- **WHEN** resumed source-only research under ADR0262 compares the two F15 build routes
- **THEN** within600s of first source reading, including independent review, use only the named retained/installed source and packaging facts to recommend one minimal route or report its exact missing prerequisite, expected file/package changes, ownership/ABI constraints and finite future qualification limits
- **AND** source/recipe declarations are not build/runtime qualification; no HTTP, new code, imports/native execution, compiler/build/install, tests, scientific evaluation or integration occurs, and every F0 input/model/tolerance/budget remains fixed
- **AND** reconcile the contract before reading and pause automation with the concrete remaining build/dependency decision; no implementation, campaign or open-ended diagnostic successor follows

#### Scenario: Execute only an admitted isolated native build

- **WHEN** the user's ADR0263 authorization is applied
- **THEN** prepare one distinctly identified in-tree kernel build only after exact source/toolchain/prefix isolation and resource enforcement are qualified, under3600s inclusive/2workers/8GiBaggregate scratch/2GiBaggregate acquisition/16MiBlogs
- **AND** unavailable source/toolchain/isolation/resource preflight prevents compiler launch; record configuration/ABI compiler probes explicitly and preserve setup failures/corrections within the same episode/deadline, with at most one kernel-target attempt, no hidden retry/expanded ceiling or scientific conclusion
- **AND** operational space-nav, historical evidence and all F0 scientific gates remain unchanged; any post-build original-row fixtures retain12calls/60s/64KiBinput/2MiBevidence and zero trajectory launches, without qualification of carry/prior arithmetic/physical feasibility

#### Scenario: Preserve a failed import and its inclusive packet window

- **WHEN** an authorized finite fixture packet aborts during native import before its first visitor call
- **THEN** retain the failed process/log/elapsed time and zero observed calls without claiming native fixture qualification
- **AND** pin any exact local runtime prerequisites separately from fixture-parameter bytes, charge their acquisition/storage, and prepare reversible isolated copies without another import
- **AND** after the original inclusive wall window has passed, a new packet requires explicit authority and a fixed new profile; do not substitute summed active process durations, reset the build episode or repeat the kernel build
- **AND** unchanged operational bytes, owner/carry/prior-arithmetic obligations and all physical F0 gates remain independently required

#### Scenario: Inventory complete import prerequisites without probing the module

- **WHEN** the user authorizes ADR0265's source-only preparation after the preserved import failures
- **THEN** one <=900s retained-core/all81binding/package review including independent source review SHALL produce the source-derived minimal eager resource list, exact local names/sizes/hashes, lazy exclusions, unresolved binary/release premises and one complete offline provisioning preflight proposal, or report the precise missing coverage
- **AND** at most32existing local payloads/16MiB SHALL be hashed with the retained image mounted read-only; new resource payload copies, installer/HTTP/build/dependency changes, native imports/calls, SPICE/simulators/integration and fixture packets SHALL remain zero
- **AND** neither the list nor local hashes SHALL claim successful loading, authenticated upstream release data, native-helper qualification or new execution authority; both failed attempts, unchanged caps and all F0 gates SHALL be preserved, with automation PAUSED before separately authorized provisioning or another packet

#### Scenario: Admit the complete provisioned fixture packet once

- **WHEN** the user explicitly authorizes ADR0266's exact three-file provisioning and one eleven-call packet
- **THEN** <=600s preflight SHALL verify all five pinned local files/131662bytes, precharge58535new bytes while preserving496986960old bytes and closed ledger/clocks, atomically complete the isolated station files, and obtain independent admission/control review before launch
- **AND** one exclusive fresh packet SHALL retain60s inclusive through fsynced completion,5s finalization reserve,11external calls/64KiBparameters/64KiBlogs/2MiB evidence/zero simulator or trajectory, reuse unchanged qualified controller/auditor logic and stop without native retry or new files on any drift/failure
- **AND** an independent saved-word audit and separate resource/time/preservation receipts SHALL distinguish successful manufactured outcomes from production-owner/carry/prior-arithmetic/ABI/physical qualification; no build/install/HTTP/SPICE/integration or operational adoption SHALL occur, historical failed packets SHALL remain unchanged and scheduler SHALL remain PAUSED

### Requirement: Qualify actual-owner readback on a fixed analytic fixture

Actual-owner preparation SHALL follow ADR0267 and retain every existing F0 gate.
Manufactured-helper qualification SHALL NOT be promoted to owner qualification.

#### Scenario: Bind the full-owner controls without adopting a native profile

- **WHEN** F18.23 closes its concrete retained-source binding contract within600s/2MiB including independent review and durable observation
- **THEN** exact eight active controls, separate gate/operators, original two-key input/eight outcomes/two arcs/argv and unchanged53-source/native/resource/history identities SHALL be bound explicitly; NOT_ADMITTED templates SHALL NOT be accepted as runtime proof
- **AND** F18.24 MAY implement only this minimal binding set within1800s static preparation and one reviewed/frozen<=120s cold/durable artificial qualification with the contract-listed positive/refusal/partial/clock/once/pin/group/byte/finalization checks, independent saved review and required repository checks; original scientific/time/byte gates SHALL remain unchanged
- **AND** no native root/resource access, native runtime import, SPICE/integration/mount/build, profile adoption or actual authority SHALL follow from design/artificial success; future actual preflight SHALL start before first namespace write/mount and include preparation/read-only observation/review/admission/consumption in strict<600s, after distinct explicit native choice

#### Scenario: Qualify the corrected artificial slice without transferring native authority

- **WHEN** one frozen/reviewed F18.22 invocation passes the nine blocked methods and focused interpreter refusals within120s including cold start and durable external observation
- **THEN** only the corrected artificial adapter/entry scope MAY be completed after independent saved-evidence review; the three retained0291helper passes SHALL remain separately attributed and the original failed invocation SHALL remain immutable
- **AND** generic2MiB evidence reads, existing16MiB interpreter identity input, all original clocks/oracles/counters/source/byte gates and unchanged repository fixture/run/audit SHALL remain fixed; native/profile/admission and physical qualification SHALL remain unavailable
- **AND** F18.23 MAY specify only a concrete minimal remaining binding/artificial-check contract from the existing map within600s/2MiB including independent review, with no tests, scientific/native execution, profile adoption or repeated general source campaign; any actual native episode SHALL still require distinct explicit choice and fresh independent admission

#### Scenario: Preserve setup failure without changing scientific or evidence gates

- **WHEN** F18.21 reports9setup errors while its generic2MiB read attempts to hash the known6829984B interpreter, before entry/original-worker dispatch
- **THEN** implementation SHALL remain incomplete and only3passed helper methods SHALL be recorded as passed; pure injected fixture generation SHALL remain distinct from zero native/scientific work, and all failed records/consumed namespace SHALL be immutable
- **AND** F18.22 MAY use only a fresh namespace, namespace-only control copies and a dedicated known-interpreter streaming pin under the existing16MiB identity-input bound;2MiBstructured evidence/64KiBlogs and original60/45/10/5/65failure/source/input/oracle/physical gates SHALL remain unchanged
- **AND** one newly frozen/reviewed<=120s cold/durable artificial invocation MAY target9blocked methods plus focused interpreter refusals, reusing3passed helper results; actual return/cleanup evidence and independent offline audit SHALL precede completion, without native/SPICE/integration/profile/admission authority or a repeated unchanged full campaign

#### Scenario: Map full-owner payload onto changed outer controls without transferring authority

- **WHEN** F18.20 completes its pinned source/saved map of0268full-owner runner and0286outer controls within600s including independent review and2MiB evidence
- **THEN** original payload, two-key input, independent literals/eight ordered outcomes/metadata/oracles/gates and3factory/2analytic-attempt/8visitor/100000callback ceilings SHALL remain unchanged; inherited-group delegation SHALL require the isolated entry to lead its session/group, without another controller
- **AND** byte-identical reuse candidates SHALL remain distinct from namespace-only and logic-changed profile/entry/adapter/admission/external-gate/operator bindings; completed ten-marker schema or consumed native authority SHALL NOT be retagged, and original45/10/5 inclusive60s, aggregate bytes and directory-fsync obligations SHALL remain
- **AND** F18.21 MAY execute only ADR0290's separately accepted temporary adapter/entry artificial slice after pinning the existing injected-worker seam with unchanged original independent auditor within600s/2MiB; its one focused invocation SHALL finish<=120s under unchanged packet caps, exercise the named changed-seam positive/refusal/clock/bytes/partial/consumption/fsync/cleanup cases, retain independent review and required checks, and SHALL NOT roll out admission/gate/operator/profile bindings or repeat194unchanged payload cases by default
- **AND** this F18.20 source mapping SHALL run zero tests/native/SPICE/integration/mount/acquisition/build/scientific evaluations and adopt no implementation/profile; F18.21 artificial success SHALL NOT confer actual native authority, which still requires distinct user choice and fresh independent admission

#### Scenario: Separate retained conversion premises from fixed-fixture preparation

- **WHEN** F18.19 checks selected retained compiler/build/artifact/context evidence against0257premises
- **THEN** generated strict-FP commands and source-associated finite original-row checks SHALL remain distinct from qualified end-to-end DOUBLE-export/storage and physical bounds; missing header bodies SHALL remain unavailable without transferring the old LONG-DOUBLE-caster gap or demanding nearest rounding
- **AND** F18.20 MAY only map0268full-runner payload/control/admission to0286outer controls within600s including independent review/2MiB, preserving0267independent literals/eight outcomes/metadata/oracles/gates and3factory/2analytic-attempt/8visitor/100000callback ceilings, with exact source/control pins and changed-versus-unchanged obligations
- **AND** tests/scientific imports/native/SPICE/integration/mount/acquisition/build/scientific-oracle-command-trajectory evaluation SHALL remain zero; no profile/operator/adapter implementation/native authority or physical qualification SHALL follow, and existing successful artificial campaigns SHALL NOT be repeated by this source mapping

#### Scenario: Preserve conditional provenance of the original conversion route

- **WHEN** F18.18 maps the retained original endpoint into existing callers and the realized-clock packet
- **THEN** same-key seven-state association and explicit pre-narrow C++double conversion SHALL remain distinct from qualified native bounds, exact artificial events and physical realized-clock admission; unknown comparison/roundtrip values SHALL NOT become false/zero observations or fabricated certificates
- **AND** F18.19 MAY inspect only retained selected-extension source/build receipts and saved observations within600s including independent review/2MiB to produce one pinned supported/unavailable conversion/domain ledger or precise missing prerequisite; no generic-caster gap SHALL be mechanically transferred to the explicit conversion route and no full core ABI/FP proof SHALL be inferred
- **AND** original0267/0247inputs/gates SHALL remain unchanged, new acquisition/mount/tests/scientific imports/native/SPICE/integration/build/scientific-oracle-command-trajectory evaluation SHALL remain zero, and adapter implementation/new native authority/physical admission SHALL NOT follow

#### Scenario: Distinguish independent readback arcs from production carry

- **WHEN** F18.17 reviews0286single-forward success against0267and existing carry callers
- **THEN** it SHALL retain independent forward/reverse literals, identify the original-key endpoint-to-handoff association separately from already artificial-qualified carry, and preserve all remaining owner/physical gates
- **AND** F18.18 MAY map only source/saved interface premises for key/event association, metadata, completion/upstream safety, owned snapshot/errors and exact seven-word handoff within600s including independent review/2MiB, with pinned source anchors and one interface table or precise missing prerequisite
- **AND** scientific/oracle/command/trajectory evaluations, tests/scientific imports/native/SPICE/integration/mount/acquisition/builds SHALL remain zero; original0267/0247inputs and numerical gates SHALL NOT change, no adapter implementation or new native authority SHALL follow, and unsupported exact-event identity SHALL remain unavailable

#### Scenario: Establish the reachable owner route without native probing

- **WHEN** F18.1 reviews the retained factory, private binding, result settings and F7 source
- **THEN** within900s including independent source/design review it SHALL pin the actual simulator method/type, processed-row meaning and retention/clear route, or record a precise missing prerequisite
- **AND** native imports/tests/builds, scientific/formula evaluations, payload copies, HTTP, SPICE and integration SHALL remain zero; automation SHALL remain PAUSED

#### Scenario: Freeze an independently checkable serial owner packet

- **WHEN** the proposed fixture is prepared for later implementation
- **THEN** two fixed constant-acceleration/constant-mass analytic coast arcs with independent literal starts SHALL retain ADR0267's eight ordered owner calls, successful condition termination, seven-state metadata, exact initial words and own-start rational terminal gates0.001m/1e-6m/s/1e-9kg
- **AND** max/min selectors SHALL be distinguished from propagation direction, retained bound ownership from expiry, performed from successful completion and signed exported zero from native Time identity; no history-map export, native carry or concurrency proof SHALL be inferred

#### Scenario: Separate artificial qualification from a new analytic native attempt

- **WHEN** F18.2 qualifies the private runner/auditor and artificial failure controls
- **THEN** the eight calls, independent oracle, metadata/lifecycle errors, precharged counters and byte/time/watchdog limits SHALL be verified alongside required frozen regressions, Ruff, independent review and strict OpenSpec, without executing the new owner packet
- **AND** only separately explicit F18.3 authority after qualification SHALL permit one pinned <=3factory/2analytic-integration/8visitor/100000acceleration-callback attempt under600s preflight,60s inclusive45/10/5 phases,64KiBinput/log and2MiB structured evidence
- **AND** callback counts SHALL NOT be presented as all native RHS; failed/unavailable attempts SHALL consume authority without retry, added data, changed gates/build/dependencies/operational adoption or reset old clocks/ledgers; all physical obligations and historical F17 failures SHALL remain intact

#### Scenario: Qualify the cold parent and exact metadata without native probing

- **WHEN** F18.2 qualifies ADR0268's private producer/auditor/controller on artificial owners and subprocesses
- **THEN** exact pinned translation/Cowell/mass state labels, typed settings and original initial words SHALL be checked independently of caller schema; the auditor SHALL compare actual source hashes without importing producer/native libraries
- **AND** tests SHALL demonstrate group cleanup after a dead leader, cold-parent receipt-fsync and streaming-I/O stalls with live inherited descendants, bounded reads before native imports, shared64KiB logs,2MiB structured evidence, inherited60s phases and immutable prefinal versus returned post-fsync observations
- **AND** unchanged existing portable/live regression SHALL remain separate from the unexecuted F18.3 packet; no source-only lookup or artificial success SHALL qualify native ownership, concurrency, event carry or physical gates

#### Scenario: Preserve an actual-owner timeout without inventing outcomes

- **WHEN** the once-only F18.3 producer reaches its45s deadline before retaining a valid scientific packet
- **THEN** the attempt SHALL remain consumed, numerical/owner qualification SHALL remain unavailable and unsupported native operation counts SHALL be recorded as unknown rather than zero
- **AND** saved failure/control accounting, bounded logs, process cleanup and distinct prefinal/post-fsync observations SHALL be retained under the unchanged60s inclusive limit; no retry, added data, relaxed limit or causal inference from a warning SHALL follow

#### Scenario: Design the next observation from saved facts without replay

- **WHEN** ADR0270 investigates the consumed F18.3 timeout using saved evidence and named retained sources
- **THEN** source/design review including independent review and read-only detach SHALL complete within600s with zero native imports/probes/SPICE/integration/builds/payload copies; environment differences and a warning shared with a success SHALL NOT be promoted to a causal explanation
- **AND** F18.5 SHALL qualify the minimal private import-only probe/auditor on artificial data and required frozen regressions before separately explicit F18.6 authority can permit one import attempt; no earlier failed packet SHALL be repeated implicitly

#### Scenario: Artificial import-only preparation cannot admit native execution

- **WHEN** F18.5 qualifies ADR0270's private probe/controller and independent stdlib trace auditor
- **THEN** injected imports/identities/processes SHALL verify strict phase order, bounded trace/input/log/clock handling, partial failure retention and a visible complete marker with unsuccessful or stalled fsync; required portable/live regressions SHALL preserve their prior scope and source pins SHALL match the frozen reviewed files
- **AND** only F18.5 preparation MAY be completed; saved child-record parity SHALL NOT replace separate F18.6 source/kernel/resource/environment admission, supervised outer cleanup/finalization or qualify the consumed F18.3/physical trajectory

#### Scenario: Bound an import-only trace without inferring owner success

- **WHEN** separately authorized F18.6 observes the exact0269cold import prefix after F18.5 qualification
- **THEN** at most six ordered <=512B JSONL markers in a <=4KiB trace SHALL remain within unchanged2MiB evidence/64KiB input-log/60s inclusive45-10-5 phases and600s preflight; exact role-specific flags, environment, read-only resources and source/kernel pins SHALL be preserved with zero explicit produce/context/factory/integration/owner/helper calls
- **AND** independent stdlib audit SHALL require marker sequence, bounded times/identity, successful child exit and finalization for import completion; a last enter without return SHALL bracket import and adjacent observer I/O without proving cause, a native instruction, old operation counts or F18.3/physical qualification

#### Scenario: Retain successful import evidence without retrospective causal claims

- **WHEN** the once-only F18.6 probe reaches all six markers with childexit0, independent audit and supervised outer cleanup/post-fsync observations under the admitted unchanged profile and caps
- **THEN** only this import observation MAY be marked complete; durable prefinal receipts SHALL remain distinct from observed post-fsync returns, and saved-only postpacket review SHALL NOT be counted as a new native episode
- **AND** a warning shared with the old failure SHALL NOT establish its cause or earlier import completion; F18.3 remains consumed/unqualified, historical counts unknown, owner/physical gates open and a new native observation requires its own explicit decision

#### Scenario: Prepare only the smallest never-run setup observation

- **WHEN** the user resumes preparation after0272's successful import and ADR0273 reviews the next owner boundary
- **THEN** source/design and independent review SHALL complete within600s without native imports/tests/SPICE/integration/mount/build/acquisition; F18.8 MAY qualify artificial1factory(False)/0integration/1visitor dispatch and exact RuntimeError unavailable refusal under a new fixed private scope
- **AND** the probe SHALL stop before forward/metadata/history/lifecycle work, preserve original functions/settings/context/schema and100000callback ceiling without assuming zero constructor callbacks; strict pre-work1/0/1 limits and exact complete-transcript counts SHALL be enforced beyond the reused Budget maxima3/2/8; eight<=512B durable markers SHALL fit a4KiB trace and require independent saved-record plus outer cleanup/post-fsync admission

#### Scenario: Separate preparation from the new setup attempt

- **WHEN** artificial F18.8 qualification is complete
- **THEN** only a distinct explicit F18.9 decision MAY permit one new setup attempt after<=600s independent source/kernel/resource/environment/control admission under unchanged0269roleflags/read-only profile and60s45/10/5,64KiBinput/logs,2MiBaggregate caps
- **AND** no consumed owner/import packet SHALL be retried; factory markers SHALL bracket imports/settings/constructor and observer I/O without identifying a native cause, and success SHALL NOT close completed-owner or physical gates

#### Scenario: Preserve report durability before setup audit

- **WHEN** F18.8 qualifies the new primitive setup report on artificial data
- **THEN** both report and trace SHALL be fsynced before a successful producer-phase observation and independent audit; failed, late or stalled report fsync SHALL NOT yield observation/audit success even with a complete visible trace
- **AND** strict1/0/1 scope, exact refusal, eight-marker capacities, independent raw-report identity and supervised cleanup/post-fsync SHALL be verified by focused and frozen required regression checks; completing artificial preparation SHALL NOT authorize F18.9 or close owner/physical gates

#### Scenario: Retain a consumed setup failure without supplementing resources

- **WHEN** the once-authorized F18.9 child exits unsuccessfully after factory-enter with a reported missing resource and no completed report
- **THEN** the attempt SHALL remain consumed and full setup qualification SHALL be rejected; partial markers, raw errors, child status, prefinal/post-fsync observations and unchanged time/byte caps SHALL be independently accounted for without inventing internal counters or factory completion
- **AND** resource supplementation, another native attempt or a revised experiment contract SHALL require a new explicit decision; protected prior data SHALL be checked and the read-only image detached, while F18.9 and physical gates remain open

#### Scenario: Resume only bounded setup-resource preparation

- **WHEN** the user resumes automation and continued checks after0275's missing-resource failure
- **THEN** F18.10 MAY trace the fixed never-run setup source/resource path within900s including independent review and read-only detach, classifying source-visible eager/lazy/unused/unresolved readers and pinning existing local payload availability without runtime imports, copies, downloads, SPICE or integration
- **AND** prior600s preflight/60s native caps, consumed attempts and physical gates SHALL remain unchanged; inventory SHALL NOT authorize provisioning or another native episode, and unknown dependency closure SHALL remain explicit

#### Scenario: Prepare one exact supplemented setup profile without executing it

- **WHEN** F18.10 identifies the six locally pinned eager resources and the user continues ordinary diagnostic preparation
- **THEN** F18.11 SHALL define the isolated six-file3578887B transaction/exact11file3710549B readback, carried acquisition500624382B<2GiB, atomic no-replace and symlink/occupied-target guards, ROremount and fresh resource/precharge/profile/source/native/control/ledger admission within600s saved-source/design review without mount/runtime/test/copy/provision
- **AND** F18.12 MAY qualify only temporary transaction/admission logic on fabricated full-volume data within120s/2MiB including failed/racing publication, fsync and stale-proof refusals; four runtime controls SHALL stay byte-identical, exact10-key probe input and old env/settings/600s-preflight/60s45-10-5/64KiB/2MiB gates SHALL remain unchanged
- **AND** a future F18.13 provision/new setup SHALL require its separately recorded decision and independent admission, preserve F18.9consumed failure, stop after original1context/1factoryFalse/0integration/1visitorTrue exact RuntimeError refusal and retain partial failure without retry; this preparation SHALL NOT imply provision/native/physical qualification

#### Scenario: Keep artificial admission separate from native launch authority

- **WHEN** F18.12 tests full six-file fabricated volume with five fake old files and hash-rebound stale/finalization failures
- **THEN** the recorded qualification SHALL require zero failures within120s including child startup/asserts/outer receipt fsync and an observed completion, with retained evidence below2MiB; exact four unchanged controls and three namespace-only controls SHALL be independently checked
- **AND** provision/admission disk candidates SHALL remain pending and SHALL NOT authorize launch; artificial return SHALL explicitly deny native authority, while a future native caller SHALL bind a successfully observed post-fsync admission result to a fresh durable final launch gate before dispatch, rejecting stale leftovers and late/failed finalization
- **AND** artificial positive checks SHALL NOT imply actual read-only image/native-positive qualification or F18.13 execution; the separate decision and independent fresh original preflight SHALL remain required

#### Scenario: Continue one observed admission through a qualified execution gate

- **WHEN** the standing continued-tests instruction is reconciled with a distinct conditional one-F18.13 decision and a temporary outer gate is prepared
- **THEN** the gate SHALL call the qualified admission directly once, bind its observed post-fsync return to the exact pending candidate/profile/contract/proofs and separately pinned outer gate/interpreter, and retain an exclusive start marker that makes every pre-existing candidate/permit/episode/work or second entry refuse dispatch
- **AND** final file and directory fsync plus immediate pin/namespace/original600s-clock checks SHALL precede native process replacement into the unchanged collector; failed or late sealing/drift SHALL dispatch zero times, and a leftover PASS file alone SHALL NOT admit a resume
- **AND** an artificial invocation SHALL complete within120s/2MiB, reach actual fabricated provision/admission and semantic mutations, write only ARTIFICIAL_READY with native authority false, and dispatch its explicit harmless callback once on success or zero times on refusal; native replacement callbacks SHALL be rejected before live reads
- **AND** this qualification SHALL leave actual read-only image/native-positive/exec unverified; the conditional choice SHALL require a fresh independently reviewed actual600s preflight through consumption before one native episode, followed by original60s45/10/5 rather than a reset or additional parent phase, with all other0277caps and physical gates unchanged

#### Scenario: Isolate one completed forward owner without replaying the full packet

- **WHEN** F18.14 reviews saved evidence and original sources within600s/2MiB including independent review without runtime/native imports/tests/mount/SPICE/integration
- **THEN** the contract SHALL preserve original forward(True) elapsed0–1000s synthetic inputs/settings, call original completion/row metadata once and the same owner's chronological-last visitor once, precharging1context/1factory/1integration attempt/1metadata/1visitor with ten bounded fsynced markers
- **AND** the independent stdlib audit SHALL require successful exact termination/seven-state IDs, primitive finite words and specifically hour0/remainder1000, using an independent Fraction(binary64 literal) polynomial with unchanged0.001m/1e-6m/s/1e-9kg gates; callback0..100000 and one nonnegative native function count SHALL remain separate
- **AND** F18.15 SHALL qualify artificial probe/audit arguments, counts, oracle and failure/clock/fsync/byte boundaries with focused300s and frozen required portable/live1800s/Ruff/strict checks; old integration0 schema/admission SHALL NOT be retagged, and changed outer controls SHALL require separately pinned artificial qualification before native use
- **AND** actual F18.16 SHALL require a distinct recorded choice and fresh independent actual600s admission, unchanged60s45/10/5,64KiB input/logs,2MiB structured and4KiB trace caps, retained11resources/no acquisition and no retry; partial counts remain UNKNOWN, prior failures/full-owner/physical gates unchanged

#### Scenario: Qualify exact completed-owner outer controls without native authority

- **WHEN** F18.15a.1 maps saved0280controls and the qualified0282producer/auditor within600s/2MiB including independent review
- **THEN** the mapping SHALL name8activecontrols plus1externalgate, reuse caller/launcher byte-identically and sandbox/preservation by namespace only, classify entry/collector/admission/run-once/gate as changed logic, and retire active provisioning
- **AND** qualification SHALL retain one entry process group with two inherited child processes, whole-group cleanup even after leader exit, ten exact completed markers/schemas/counts, original60s45/10/5 and final enclosing-directory durability; partial failure or pending/saved PASS alone SHALL NOT establish completion
- **AND** only an explicit harmless artificial harness MAY override child commands; its real probe uses all six fake hooks and mode=injected, its actual guarded auditor runs separately, and native CLI/profile SHALL reject replacements before live reads with artificial native authority always false
- **AND** all49old plus4newsource pins,10native,11retained resources,25oldledger and all86saved0280members SHALL be preserved; fresh actual readback/admission cannot inherit historical timestamps, new acquisition SHALL be0, changed-control artificial checks SHALL finish within300s, and F18.16 SHALL remain unadmitted pending its distinct choice and fresh independent actual600s preflight

#### Scenario: Independently witness cleanup refusal without masking it

- **WHEN** an artificial leader-exit cleanup case raises EPERM instead of returning a failure object
- **THEN** qualification SHALL preserve the original failure and SHALL NOT suppress that runtime exception or infer its cause; a revised failure-path oracle MAY accept refusal only after recording the actual first successful group SIGKILL, the exact owned PID/PGID/UID identities and a bounded independent raw process witness proving no running owned member
- **AND** malformed/unknown identity, failed first kill, unexpected exception, live member or failed witness SHALL fail qualification; verified absence or a non-running zombie SHALL NOT imply general reaping, native caller success or physical qualification
- **AND** the revised test/source pins and prior successes SHALL remain separately attributable, passed unchanged cases SHALL NOT be repeated without reason, and raw positive producer/auditor/outer observations SHALL be retained and independently reviewed before F18.15a completion; F18.16 still requires its distinct recorded choice and fresh actual admission

### Requirement: Bound realized-clock evidence without changing commands

Private realized-clock preparation SHALL follow ADR0255's distinct fixed evidence
contract under ADR0205. Structural/interval consistency SHALL remain separate
from qualified native readback and physical trajectory admission. F5/F7 exact
semantics and all F0 data, gates and production budgets SHALL remain unchanged.

#### Scenario: Retain the actual event and seven-state chain

- **WHEN** one fixed three-arc path is represented
- **THEN** it contains exactly four chronological requested events, three arc rows, six native endpoint observations and four seven-state nodes with SI/TDB-J2000/SSB/J2000 metadata and fixed boundary/command/source/model identities
- **AND** each fresh-context native start consumes the prior actual endpoint event and exact state/mass words; independent start-label rounding, matching labels or overlapping intervals cannot establish actual continuity

#### Scenario: Refuse unqualified readback and false exact identity

- **WHEN** native observations are serialized or audited
- **THEN** producer-only Time identity/roundtrip evidence and export types/words remain labelled separately from justified native-value enclosures and exact requested Fractions
- **AND** absent precision/conversion/normalization basis stays unavailable; a hash, caller verified flag, float label or bare half-ULP assumption cannot certify native identity, and no F5 exact ArcResponse is manufactured

#### Scenario: Preserve both ledgers and conservative dry-floor decisions

- **WHEN** clock and mass evidence is assessed
- **THEN** signed epoch/span intervals derive from the same actual event chain, the original binary64 rate and duration words define the commanded ledger, and a distinct effective-span ledger and actual carried mass remain separate
- **AND** a500kg floor passes only when every applicable lower mass bound is>=500kg before rounding; straddling is inconclusive and a definite shortfall fails this command, without repair by the separate1e-9kg matching tolerance

#### Scenario: Keep missing bounds and physical admission explicit

- **WHEN** packet arithmetic is consistent but an applicable readback, clock/mass/force, source/event-branch or endpoint bound is missing or unverified
- **THEN** the scientific gate remains unavailable/inconclusive, never a zero-error pass; the original target epoch/state is retained and physical execution stays unavailable
- **AND** complete justified interval decisions retain1e-6s/0.001m/1e-6m/s/1e-9kg join and1000m/0.01m/s target gates; no packet-only success certifies full-force safety, a physical command pair or endpoint bounds

#### Scenario: Reject malformed artificial declarations before qualification

- **WHEN** a pure fabricated packet is parsed, even with unknown basis or physical-unqualified scope
- **THEN** only UTF-8 JSON with unique fixed fields, canonical finite binary64 words and reduced positive-denominator rationals is accepted; declared mass intervals must contain the actual word and norm intervals must be nonnegative before qualification filtering
- **AND** the artificial checker retains unavailable scientific/physical admission; the isolated qualification uses one outer15s startup-through-finalization supervisor and retains distinct pre-fsync report and post-fsync observation without rewriting history

#### Scenario: Bound pure preparation separately from native execution

- **WHEN** a future pure fabricated checker is qualified
- **THEN** the fixed shape,64KiB-before-decode input,2MiB combined evidence/log cap, first-failure retention and15s inclusive watchdog are verified with zero new native imports, SPICE, integration, real-archive or optimizer work
- **AND** pure consistency cannot accept physical certificates or independently qualify actual native observations; design completion grants no native run, preserves F7's separately admitted6attempt/100000provider/60s ceilings and original73/76/228/300s production limits


### Requirement: Separate requested events from native transport

Native preparation SHALL preserve exact requested event/control meaning separately
from observed native representation and SHALL follow ADR0254's pinned-source
limitation and ADR0205's pre-existing realized-clock allowance. It SHALL NOT
fabricate the artificial F5 exact response, weaken F7 admission or infer physical
infeasibility from unavailable transport.

#### Scenario: Record the limited source conclusion

- **WHEN** F8 source/design review closes
- **THEN** it binds the installed build and source hashes/line anchors for Time, double fixed/custom stops and final-step logic, with source reading<=600s and zero native imports, SPICE, oracle/command/trajectory evaluations or tests
- **AND** no current candidate event is evaluated and no blanket API impossibility, observed native error, physical command rejection or execution authority is claimed

#### Scenario: Preserve exact and realized event scopes

- **WHEN** an event is outside the present exact adapter's representability or observed-equality domain
- **THEN** that adapter remains unavailable without rounding the requested command or manufacturing exact native identity from a1e-6s label tolerance
- **AND** a future distinct realized-clock design retains immutable requested events/durations, actual native representation/readback and signed epoch/span discrepancy enclosures; it does not alter the existing F5/F7 contracts

#### Scenario: Require a bounded physical contract before implementation

- **WHEN** F9 proposes the separate physical packet under ADR0205
- **THEN** its contract names commanded/effective-span dry-floor ledgers before mass rounding, actual propagated-mass checks, native/readback precision provenance, independent clock/mass/force contributions to endpoint error allowances and finite work/time limits
- **AND** missing justified bounds remain unavailable/inconclusive rather than a pass; all original1e-6s/0.001m/1e-6m/s/1e-9kg join and1000m/0.01m/s target gates and73/76/228/300s production caps remain unchanged, with no implementation or run admitted by design completion


### Requirement: Check native arcs on the existing analytic witness

Private native preparation SHALL follow ADR0252's fixed synthetic uniform-field
witness and separate request/observed-endpoint contract. It SHALL NOT imply
physical F0 or F5 native-adapter adoption, change scientific gates or admit a
mission search from interface/CI success.

#### Scenario: Refuse unsupported event transport before native work

- **WHEN** an exact event differs from Fraction of its binary64 label, even with distinct labels
- **THEN** native attempts remain zero, the request is unavailable-transport and no command/duration is quantized or classified physically infeasible
- **AND** admitted requests retain requested Fraction, label word, expected and observed native Time identity and Time-before-float residual separately; native inequality cannot pass as exact identity through a1e-6s tolerance or manufactured F5 response

#### Scenario: Verify the fixed native paths without node resets

- **WHEN** F7 qualifies the ADR0248 known q* fixture in native translation/mass dynamics
- **THEN** three forward arcs and three separately requested reverse arcs use the fixed uniform gravity, explicit burn/coast modes and pinned directional tighter RKDP87 settings; reverse starts from ADR0248's exact-decimal100-digit final seven-state rounded once per component and changes only integration direction
- **AND** actual returned state and mass cross every fresh-context join, native endpoints are selected by direction, and all four events agree with independent Decimal80/100 exact-decimal and binary64-word references within0.001m/1e-6m/s/1e-9kg and1e-6s, with native Time equality checked separately
- **AND** SYNTHETIC_INERTIAL/elapsed_seconds labels, separate constant/target conversion differences, exact mass ledger and finite500kg/TNW domain checks are retained; no real ephemeris or collision-safety claim follows

#### Scenario: Enforce the bounded synthetic fixture honestly

- **WHEN** the cold native fixture runs
- **THEN** native attempts including failures are precharged<=6 and uniform-gravity provider entries<=100000 before provider work; first failure stops without retry/tuning and discards mutable contexts
- **AND** a hard external60s deadline covers producer45s/audit10s/reserve5s including startup/finalization, input<=64KiB and combined evidence/logs<=2MiB; synthetic tests cover counter/deadline/byte/abort and partial-history failures
- **AND** native reported function counts use maximum count values and remain post-run telemetry distinct from provider entries; no total-RHS hard-cap or production admission is inferred, and new SPICE/kernel/real-archive/optimizer counts are zero

#### Scenario: Separate design, native conformance and physical readiness

- **WHEN** F6 design or F7 qualification is marked complete
- **THEN** source/reuse/scientific review, links/anchors/protected bytes/diff and strict OpenSpec verify F6; focused tests, bounded native fixture, both frozen required regression lanes, Ruff and independent review additionally verify F7
- **AND** integer-event synthetic conformance does not qualify fractional/large F0 epochs, arbitrary guidance, full-force seeds/guards, physical derivatives or ADR0205 reverse/endpoint bounds; original solver,73/76/228/300s caps and every physical gate remain binding

### Requirement: Qualify the coupled coordinate bridge before native adoption

Private preparation SHALL follow ADR0250's coordinate/event/arc-request contract
using six physical controls and two auxiliary normalized translation nodes.
It SHALL NOT adopt a physical optimizer, change the production algorithm/caps,
or imply native/full-force/physical qualification from fabricated tests.

#### Scenario: Preserve normalized coordinates and exact event meaning

- **WHEN** the private bridge decodes an artificial18-value input
- **THEN** its two nodes use the fixed1000m/1m/s scales with exact rational accumulation and one binary64 rounding, raw signed defects remain in SI and separate scaled residuals use1000m/0.01m/s, zero offsets preserve anchor words, and t0/tf words stay fixed with exact rational t1/t2 from binary64 duration inputs
- **AND** exact events/ledger, rounded labels/masses and signed conversion differences remain separate; mass uses the existing binary64 rate word, equality at dry mass is admitted and a sub-ULP shortfall is rejected
- **AND** boolean/nonfinite/malformed inputs, collapsed physical perturbations and unsupported native time reduction cannot silently become valid physical trials

#### Scenario: Exercise modes and continuity without native execution

- **WHEN** the evaluator uses the injected artificial arc function
- **THEN** departure/coast/arrival receive the specified starts, derived masses, exact events and Moon-TNW/no-engine/Mars-TNW modes in a fresh mutable context, with signed18translation defects and separate time/mass checks
- **AND** shooting and unreset replay are distinct explicit three-arc evaluation modes; replay carries actual preceding state/mass and is independent of node changes at fixed controls; exact rational endpoint identity is mandatory before the separate1e-6s rounded-label check, and no unsafe/partial/failed arc yields a normal physical result or retry

#### Scenario: Independently verify large-coordinate and finite-capacity cases

- **WHEN** F5 artificial qualification runs
- **THEN** independent rational/affine expectations check unshifted and2^37m/2^14m/s/1e9s shifted inputs within0.001m/1e-6m/s/1e-6s/1e-9kg, and every field is exercised with the declared fixed physical increments without asserting F0 derivative accuracy
- **AND** a full-volume fixture checks73controls+3diagnostics/228injected arc slots and next-work refusal, first failure, shared15s deadline including startup/finalization,10s producer cutoff,64KiB input/128KiB output and zero new SPICE/kernel/real-archive/native/integration/optimizer work, with simulated_arc_slots separated from actual native_propagations=0
- **AND** focused and both frozen required regression lanes, Ruff, independent review and strict OpenSpec pass before F5 is marked complete; ordinary existing live regression remains permitted separately

#### Scenario: Keep native and physical adoption unavailable

- **WHEN** F4 design or later artificial F5 completes
- **THEN** only bridge design or interface qualification is claimed respectively; original boundary/hardware/force/target/join/safety/error-bound gates and production73/76/228/300s ceilings remain binding
- **AND** a complete native seed, exact-event/realized-mass qualification, guards/full-force parity, physical derivatives, independent endpoint bounds and explicit production-method reconciliation remain required before native/physical adoption; no mission experiment or consumed-study replay is authorized

### Requirement: Qualify coupled shooting on an analytic finite-burn benchmark

Before a coupled method is adopted for F0, private preparation SHALL implement
ADR0248's explicit manufactured uniform-gravity two-burn problem and independent
checker, using the pinned stack without changing production controls or limits.
The benchmark SHALL remain synthetic and SHALL NOT claim full-force feasibility,
absolute physical accuracy, mission safety or ADR0205 error-bound admission.

#### Scenario: Admit an independent finite-burn reference

- **WHEN** the artificial fixture is prepared
- **THEN** it uses the exact ADR0248 inputs, SYNTHETIC_INERTIAL/elapsed-second labels, two dynamically rebuilt TNW burns and gravity on all arcs; the known T-only witness target is independently composed with Decimal80/100 using before-arc velocity and sequential mass
- **AND** the precision paths agree within 1e-9 m/1e-12 m/s/1e-15 kg, gravity's total speed contribution is at least half the initial speed, and witness mass loss is at least ten percent of initial mass before the reference is admitted
- **AND** witness propagation agrees with analytic nodes within 0.001 m/1e-6 m/s/1e-9 kg and 1e-6 s without calling the closed form for perturbed steering

#### Scenario: Recover from a genuinely unclosed seed

- **WHEN** the pinned bounded TRF method evaluates ADR0248's perturbed controls and nodes
- **THEN** the initial defects fail a qualification gate, exactly six controls plus two translation nodes are the 18 unknowns, node masses/epochs are derived, and all 18 raw translation defects and independent callback counts are retained
- **AND** all final shooting defects satisfy 0.001 m/1e-6 m/s, mass/time continuity satisfies 1e-9 kg/1e-6 s, and an unreset forward replay meets the independent target within 0.1 m/1e-5 m/s while respecting the 500 kg floor
- **AND** solver status alone, copied witness commands/nodes, a rank assumption or a lower scaled residual cannot pass qualification; invalid/nonfinite/TNW/domain trials stop without penalties or restarts

#### Scenario: Check the recovered command independently

- **WHEN** the separate stdlib auditor verifies a candidate result
- **THEN** it independently rebuilds TNW/RHS, checks the actual recovered command on 4096/8192-step-per-arc RK4 meshes, and uses an explicit arc mode through the final RK stage before switching thrust
- **AND** witness and returned-command paths satisfy all ADR0248 event/analytic/mesh/candidate checks, including 0.001 m/1e-6 m/s/1e-9 kg cross-path differences and the independent final 0.1 m/1e-5 m/s gate
- **AND** mass stage values use its independent linear ledger, no node is injected into a forward history, and cross-method agreement is reported as diagnostic rather than a certified physical bound

#### Scenario: Bound synthetic work without changing mission budgets

- **WHEN** preparation or the fixed artificial qualification runs
- **THEN** the shared parent limit is 300 s including durable finalization, producer<=210 s, auditor<=60 s, with 30 s reserved; hard caps are 400 callback entries including Jacobian calls, 1206 producer synthetic arcs, 1000000 producer RHS, 12 audit arcs and 300000 audit RHS
- **AND** explicit input is <=64 KiB and all evidence/logs <=2 MiB, precharged counters and deadline/watchdog/finalization paths are tested, and no cap or tolerance is raised after failure
- **AND** SPICE/kernel/real-archive/native-propagation counts are zero; production's 73-control/76-evaluation/228-native-call/300-second limits and all F0 scientific requirements remain unchanged

#### Scenario: Separate contract completion from qualification

- **WHEN** F2 is marked complete
- **THEN** source/API facts, independent scientific/reuse review, local links/anchors, protected files, diff and strict OpenSpec pass, with no numerical execution or qualification claim
- **AND** F3 remains unchecked until the implementation, independent checker, focused and both frozen required regression lanes, Ruff/review/strict and the declared artificial gates pass; no retained/mission study follows from an artificial pass

### Requirement: Classify the coupled mission inputs before another search

The M3 research design SHALL maintain ADR0247's source-linked ledger separating
mission requirements, currently fixed boundary/reference data, existing physical
controls, derived quantities, auxiliary transcription unknowns and proposed future
variables. Historical reproduction choices SHALL NOT silently become universal
mission requirements or currently free inputs. Design acceptance SHALL NOT
change the public physical-refinement contract or authorize a scientific run.

#### Scenario: Review the complete variable ledger

- **WHEN** the coupled formulation is reviewed before method selection
- **THEN** it identifies vehicle data, both orbit geometries/phases, date bounds, selected epochs, boundary six-states, all six existing TNW/duration controls, switching epochs, masses, seed data, checkpoint role, dynamics/resources and acceptance gates with their sources and current roles
- **AND** switching epochs and masses are marked derived, while any shooting states are auxiliary unknowns subject to continuity rather than additional maneuvers

#### Scenario: Preserve binding boundaries while exposing proposed freedom

- **WHEN** free dates, departure/arrival phase or orbit-membership targeting are considered
- **THEN** they remain proposed extensions until an explicit changed boundary contract is adopted; the original fixed t0/tf, configured phases, plane/apsides, hardware and tolerances remain binding for F0 and all retained evidence is unchanged
- **AND** an altered phase or date cannot be labelled the original ADR0135/0205 target or reuse an obsolete body state as its new boundary

### Requirement: Formulate one coupled orbit-to-orbit finite-burn problem

F0 SHALL specify one SI/SSB/J2000 seven-component position/velocity/mass history
in TDB seconds since J2000 from the configured lunar ignition state to the
configured Martian cutoff state. It SHALL use the unchanged full M3 force model,
two maximum-thrust TNW burns and the six already specified controls. M2 Lambert
endpoints/excess vectors SHALL be seed information rather than additional
physical endpoint constraints. This is a mathematical design, not a solver.

#### Scenario: Define the physical events and mass constraints

- **WHEN** F0 is expressed as equations and constraints
- **THEN** it includes dr/dt=v, non-thrust plus finite-thrust acceleration, dm/dt=-F/(g0*Isp) on burns and zero coast mass rate, fixed initial/target six-states at their respective epochs, t1=t0+tau_d<t2=tf-tau_a with positive durations, and m(t)>=500 kg for this reference
- **AND** terminal mass is derived rather than fixed equal to 500 kg; any R1 reserve claim retains its additional 550 kg threshold and declared scope

#### Scenario: Give shooting unknowns no unphysical freedom

- **WHEN** multiple shooting is considered as a possible transcription
- **THEN** every auxiliary arc-start state has position, velocity, mass and common-epoch continuity constraints; additional nodes add zero impulses, no force-model switch and no independently assignable checkpoint mass
- **AND** a later acceptance check must use the frozen commands from the original lunar state through arrival without intermediate node resets, with the same independent-validation requirements
- **AND** the saved R5.51 checkpoint is not prescribed as an achieved spacecraft target or a burn event; R5.60 retains its own additional admission and ordering rules

### Requirement: Keep coupled feasibility and numerical evidence distinct

The formulation SHALL preserve separate scientific gates and require a complete
method/benchmark contract before another solver implementation or experiment.
It SHALL NOT treat the consumed P6 no-witness result as continuous refusal,
global optimality, or impossibility of the physical mission. Documentation
checks SHALL NOT be reported as runtime or trajectory verification.

#### Scenario: Preserve closure, join and error-bound gates

- **WHEN** a future coupled candidate is assessed
- **THEN** final Mars-relative position and velocity norms must separately satisfy 1000 m and 0.01 m/s, joins retain 1e-6 s/0.001 m/1e-6 m/s/1e-9 kg, and all original mass/collision/force/resource and strict M3 numerical/model qualifications remain required
- **AND** copied nodes, a small scaled residual, optimizer success or cross-integrator agreement cannot replace ADR0205's independently justified endpoint-error bounds or certify mission safety

#### Scenario: Complete formulation without starting research

- **WHEN** the ADR0247 documentation stage is completed
- **THEN** its table/equations, source facts, local links/anchors, requirement scenarios, protected-file comparison and strict OpenSpec validation are checked, with zero scientific evaluations, kernel reads, SPICE calls, force evaluations, integrations or new benchmark runs
- **AND** no method, node count, command pair, new target or scientific success is selected; automation remains PAUSED and all consumed studies/R5.60 remain unavailable
- **AND** before later implementation, a separate contract must name the exact benchmark, physical inputs/variables, independent oracle, tolerances, pinned method and finite work/time limits without silently increasing the current 300 s M3 deadline

### Requirement: Mission-first demonstration readiness after local research

R1 SHALL prioritize one reproducible research demonstrator with an independently
checked calculation and exportable result, following ADR 0117. It SHALL preserve
the long-term platform vision, historical evidence and all strict M3 gates.

#### Scenario: Stop local targeting continuation without erasing evidence

- **WHEN** next work is selected after the unclosed D17.3 study
- **THEN** the active priority SHALL be R1 readiness, not an automatic D18, second D17 run, new seed, chart extension or larger budget
- **AND** all historical JSON, targets, thresholds, model identities and results SHALL remain unchanged; an unclosed experiment SHALL NOT be relabelled successful or proof of global infeasibility
- **AND** any later local targeting study SHALL require an explicitly accepted problem, user-visible purpose, physical constraints and execution budget; this planning record SHALL authorize zero native launches

#### Scenario: Declare a positive reference at its actual fidelity

- **WHEN** R1.1 specifies the first demonstration problem before selecting its fixture
- **THEN** it SHALL declare the user-visible outcome, model/version and omissions, explicit physical inputs/dates, initial/final conditions, and rationale for every constrained state component and epoch
- **AND** it SHALL distinguish mission boundary requirements from reproduction of an ideal impulsive endpoint, and justify the connection to the outer transfer before a finite-burn lunar departure is used as a mission boundary
- **AND** it SHALL fix a finite numerical reserve strictly greater than zero in kg, the maneuvers/uncertainties covered by that allowance, numerical acceptance tolerances and verification budget before selection; a qualifying reference SHALL satisfy final_mass_kg >= dry_mass_kg + reserve_kg under the declared accounting
- **AND** an M2-only reference SHALL be labelled ideal-model feasible, NOT finite-burn or full-mission feasible; changing a fixture SHALL create an explicit new scenario, not mutate the retained references or silently alter spacecraft defaults
- **AND** missing inputs/reserve coverage or failed checks SHALL leave the reference unverified; simply changing dry mass, lowering a tolerance, optimizer success or lower residual SHALL NOT qualify it

#### Scenario: Check a small physical benchmark independently before expanding optimization

- **WHEN** R1.2 verifies a declared calculation before further optimizer complexity or end-to-end acceptance
- **THEN** its contract SHALL name an independently implemented analytic oracle or external engine, versions/resources, frozen initial state/command/epochs, identical force and mass models, numeric position/velocity/mass/time tolerances in SI and execution limits before any run
- **AND** it SHALL retain raw aligned states, differences, provenance and pass/fail/unavailable outcomes; every declared difference SHALL be within its predeclared tolerance to pass
- **AND** a finite-burn claim SHALL require a benchmark with finite thrust and non-negligible gravity; two profiles sharing the same dynamics adapter or independently reoptimized commands SHALL NOT count as independent physical validation
- **AND** unavailable tooling or a failed comparison SHALL stop the gate unverified or failed without automatic retries, increased budgets or fabricated reference data; agreement SHALL NOT establish mission feasibility, absolute accuracy or continuous safety
- **AND** this small benchmark MAY precede M6, but SHALL NOT be reported as M6 full-mission GMAT/Monte Carlo completion or a waiver of strict M3

#### Scenario: Specify traceable output and a narrow exchange profile before coding

- **WHEN** R1.3 prepares the demonstration's result and OEM exchange specification
- **THEN** it SHALL bind output to normalized actual inputs, model/fidelity, epochs/units/origin/orientation, physical and numerical status, reserve accounting and resource/source provenance
- **AND** it SHALL select the exact OEM edition/corrections, encoding, supported metadata/frames/time scales, conversion tolerances, independent reader and positive/rejection fixtures before exporter implementation
- **AND** exported epochs and physical states SHALL round-trip through that reader within the declared tolerances after explicit unit/frame/time conversion; successful parsing alone SHALL NOT qualify physics or interchange
- **AND** unsupported semantics SHALL fail clearly; stale UI/export results SHALL be invalidated after input changes or failed calculations, and absent covariance/safety/measurement data SHALL NOT become fabricated zeros or success flags

#### Scenario: Complete a usable path without closing the engineering milestone

- **WHEN** R1.4 is separately implemented after the readiness/benchmark/profile gates pass
- **THEN** one new positive reference SHALL traverse input, calculation, display, export and independent decoding, with all declared numerical/reserve checks and negative/stale-result tests passing
- **AND** focused tests, the full pinned regression suite, strict OpenSpec validation and immutable legacy checks SHALL pass before implementation completion
- **AND** the demonstration SHALL retain its declared research/M2 limitations; more private experiment records, passing component-test counts or format compatibility alone SHALL NOT constitute completion
- **AND** strict M3/task 3.9 SHALL remain open until their original gates pass; M4 estimation, M5 corrections, M6 mission validation, ML, generic backend frameworks and automation restart SHALL remain outside R1

### Requirement: Controlled M2 reference and historical evidence readiness

R1 SHALL keep the accepted ADR 0118 reference, empirical mission comparisons and
same-force independent numerical verification as separate claims. The proposal
SHALL NOT authorize execution or change public scientific behavior by itself.

#### Scenario: Accept explicit inputs and reserve before selecting the new reference

- **WHEN** the ADR 0118 R1.1 contract is accepted before a separately instructed verification
- **THEN** the new `r1-m2-reserve-reference` SHALL use model `sun-centered-zero-revolution-patched-conic-v1` and all explicit values from the unchanged hypothetical template `examples/m3_feasible_mission.toml`, SHA256 `2c3b2a140d6e6ea00c2173caab5c51b1c4be87a112d2dec28a40cd1e2a0a9b42`, not a GRAIL/MSL spacecraft or a relabelled D17 result
- **AND** the 2031 UTC window, 180–320 day flight range, 2000/500 kg initial/dry masses, 450 s Isp and all other supplied fields SHALL remain explicit; the model's ignored orientation/thrust/tracking/error fields and body-centre/instantaneous-burn approximations SHALL be disclosed
- **AND** before candidate selection the reserve SHALL be 50 kg, allocated only to aggregate additional ideal delta-v <=100 m/s at constant 450 s Isp, mass <=2000 kg and no staging/mass additions; `2000*(1-exp(-100/(9.80665*450))) < 50 kg` SHALL be independently checked, without claiming uncertainty coverage or scheduling a TCM
- **AND** only a candidate with final_mass_kg >=550.0 and independently recomputed ideal mass within 1e-9 kg SHALL qualify; the returned Pareto front SHALL be filtered by reserve and selected by `(total_delta_v_m_s, flight_time_s, departure_epoch_tdb_s, candidate_id)`, then frozen for replay
- **AND** the absence of a qualifying candidate SHALL leave R1.1 failed/unverified without changing the template, reserve, dates or historical evidence

#### Scenario: Verify reproducibility within the declared M2 budget

- **WHEN** the accepted R1.1 contract is separately executed
- **THEN** it SHALL permit exactly two complete planner calls and two 121-state sampler calls, at most 3960 Lambert attempts and 242 two-body samples, under one cooperative 300 s wall-clock acceptance budget including scientific/resource setup
- **AND** checks before/after every top-level call SHALL prevent further calls after exhaustion; a non-preemptible native-call overrun SHALL be reported with actual time as failure, not bounded success or permission to retry
- **AND** inputs/source/resources/GMs/versions and selection SHALL match, scientific payloads SHALL be identical apart from separately recorded timing, and finite SI/SSB/J2000 samples at TDB epochs SHALL pass existing M2 endpoint checks of 100 m and 0.001 m/s
- **AND** a reserve deficit SHALL NOT be admitted by numerical tolerance; resource mismatch, missing positive reference, error or overrun SHALL stop further calls, leave R1.1 open and SHALL NOT complete R1.2 or qualify finite burns/M3

#### Scenario: Admit a historical arc only with inspected coverage and event evidence

- **WHEN** an MSL or GRAIL historical trajectory is proposed for empirical comparison
- **THEN** readiness SHALL record exact product URLs/versions/hashes, inspected binary body/centre/frame/coverage and time scale, companion kernels/load order, a maneuver-free interval supported by event data, force omissions, epochs, tolerances and execution limits before propagation
- **AND** a directory entry, filename or label alone SHALL NOT certify continuous coverage, absence of thrust or full dynamics; conflicting generic/product-specific metadata SHALL be reconciled or leave readiness unverified
- **AND** missing reconstruction uncertainty SHALL remain unavailable rather than zero; historical residuals SHALL be labelled empirical model discrepancy, not same-force numerical error, reserve feasibility or mission qualification
- **AND** R1.2 SHALL still require its independently accepted frozen same-force oracle/engine contract; data discovery SHALL NOT start a replay, replace the Moon-to-Mars demonstration or bypass R1.1

### Requirement: Independent eccentric coast-component benchmark

R1.2 SHALL follow the frozen ADR 0120 contract only after user acceptance and
separate execution instruction. Its proposal alone SHALL authorize zero native
calls and SHALL NOT change production physics or close R1.2.

#### Scenario: Freeze a noncircular inclined synthetic problem

- **WHEN** the R1.2 coast-component fixture is prepared after contract acceptance
- **THEN** it SHALL use ADR 0120's literal periapsis six-state, a=149597870700m, e=0.2, P=(0.36,0.48,0.8), Q=(-0.8,0.6,0), mu=1.327124400420322e20m^3/s^2 and t0=978995455.2304223 TDB seconds since J2000
- **AND** both paths SHALL use Sun-centred/J2000-oriented SI states, only point-mass acceleration, the same frozen Cartesian input and 17 rounded epochs t0+k*T/16, k=0..16, T=2*pi/sqrt(mu/a^3); actual elapsed seconds SHALL be epoch-t0, not separately rounded nominal durations
- **AND** the scenario SHALL remain synthetic, not a changed R1.1 mission; the six-state adapter's absent mass dynamics/error SHALL be labelled not-modelled/unavailable, not zero or mass validation

#### Scenario: Establish independent analytic state agreement

- **WHEN** the existing coast adapter is compared with oracle `kepler-bisection-cartesian-v1`
- **THEN** the oracle SHALL implement ADR 0120's radian-valued eccentric-anomaly bisection and differentiated Cartesian equations using only standard-library arithmetic, without Tudat/SPICE/production element conversions, native returned states or fitted parameters
- **AND** no more than64 bisections SHALL achieve bracket width and equation residual each <=2e-14rad; pure periapsis/apoapsis/period closed-form checks SHALL pass 0.01m/1e-8m/s before native work
- **AND** all17 aligned finite state pairs SHALL pass Euclidean position <=1m, velocity <=1e-6m/s and exact epoch/elapsed equality, plus relative specific-energy and vector angular-momentum errors <=1e-12 against the shared initial state in each path
- **AND** invariants, repeatability or a circular-only check alone SHALL NOT qualify this comparison; its result SHALL NOT validate full-transfer targeting, Sun-to-SSB translation, finite thrust, mass, navigation uncertainty, continuous safety or M3/M6

#### Scenario: Run one bounded study and preserve failures

- **WHEN** verified private-script preparation is followed by separate user execution approval
- **THEN** at most17 adapter invocations (17 Kepler propagations/34 visible element conversions) SHALL occur in epoch order under one cooperative30s budget including scientific imports, provenance, pure checks and comparisons, with checks before/after calls
- **AND** no planner search, `sample_transfer`, SPICE request, historical download, extra native test/replay or retry SHALL occur; first mismatch/error/missing resource or overrun SHALL stop further calls and leave R1.2 failed/unavailable
- **AND** evidence SHALL bind ADR 0120's R1.1-artifact/adapter hashes and unchanged pinned environment, record actual source/build/import-path/GM/time identity, both raw states/signed differences/norms/root/invariant diagnostics, attempted/completed counts and timings, and preserve partial/returned-overrun data in exclusively created new artifacts
- **AND** only all17 passing pairs and offline evidence checks SHALL permit completion of R1.2; a non-preemptible overrun SHALL report actual time as failure without parameter/tolerance/budget changes

### Requirement: Smooth additional steering freedom after the bound-limited study

D17 SHALL follow ADR 0114 as a separate private experiment, preserving D14/D15/D16
and all historical evidence. It SHALL change only the steering chart/control count
and explicitly separate compute ceiling, not the physical target, fuel, thrust,
force model, timing domain, native profiles or qualification thresholds.

#### Scenario: Diagnose saved response without inventing final stationarity

- **WHEN** D17.1 evaluates retained D16.3 evidence
- **THEN** it SHALL bind 0113 SHA256 417f4a33e6407a37e9a41caff29330557f39d7a3bbfc34e9b908cc1d5589cb89 and distinguish best objective 262 from last accepted/measured parent 249
- **AND** it SHALL independently check the active duration/reserve bound, saved-gradient normalization, five-free-column and bounded linear residual minima against exhaustive face/KKT oracles, without applying those commands or propagating a spacecraft
- **AND** conditional linear minima SHALL NOT become nonlinear impossibility bounds, returned SciPy stationarity or a Jacobian at unmeasured ID 262

#### Scenario: Add smooth curvature inside the unchanged chart envelope

- **WHEN** D17 constructs an eight-control command x=(delta_ti,tau,p0,q0,pc,qc,p1,q1)
- **THEN** for s=t/tau it SHALL use u(s)=(1-s)^2*u0+2*s*(1-s)*uc+s^2*u1 and normalize d0+u_p*e1+u_q*e2 in the original inertial basis; uc SHALL be labelled a Bezier control point, NOT a midpoint-time direction
- **AND** all six slope coefficients SHALL remain in [-1,1], so the convex-hull property bounds the complete physical chart for 0<=s<=1; norm of its unnormalized direction SHALL be >=1
- **AND** uc=(u0+u1)/2 SHALL embed the old linear chart; the same polynomial SHALL extend native trial stages outside the physical interval without clamping, guidance kinks or a new midpoint arc
- **AND** the sampled/state/mass guards SHALL remain authoritative; rate bound 2*max(norm(uc-u0),norm(u1-uc))/tau SHALL be diagnostic, not hardware qualification

#### Scenario: Bind a reproducible interior seed with separate model replay gates

- **WHEN** the separately verified D17 runner starts
- **THEN** it SHALL bind pinned 0104/0107/0110/0113 inputs, candidate d0001-t0035 and its original first free-phase branch, domain/resources/commands/target, explicitly selecting accepted 0113 proposal 158 only
- **AND** a fresh old two-node replay SHALL agree with retained ID 158 within 1 m / 0.001 m/s / 1e-6 kg, then a fresh embedded Bezier seed SHALL agree within the same limits against BOTH that replay and retained ID 158, before derivative work
- **AND** model ID SHALL be local-moon-point-mass-bezier-burn-v1 and algorithm ID bound-aware-bezier-trf-v1, with the old reference model separately identified; the old replay SHALL NOT qualify or become a new-model objective
- **AND** only the embedded seed residual SHALL supply the single exact initial objective cache; its controls SHALL equal the eight values frozen in ADR 0114, with y0=0 unchanged by SciPy; mismatch SHALL stop without clipping, alternate start, epsilon repair or silent cache reuse
- **AND** target six-state and tm=979002340.6346419 TDB s, Moon/J2000/SI, 1000 N / 450 s, 2000/500 kg masses, original reserve/window/ignition/duration bounds and >=1 s full-box coast SHALL remain unchanged; final mass SHALL vary analytically with duration, not become a seventh target

#### Scenario: Correct an underdetermined six-state residual with bounded probes

- **WHEN** the Bezier seed replay passes but the target is unclosed
- **THEN** D17 SHALL use pinned SciPy 1.17.1 TRF/exact/linear, x_scale=1, ftol=xtol=gtol=1e-10, max_nfev=40, verbose=0, workers=None; x=x_seed+T*y with T=(300 s,300 s,0.1,0.1,0.1,0.1,0.1,0.1) and the unchanged six 10 m / 0.01 m/s residual scales
- **AND** its callable 6x8 Jacobian SHALL use fixed h=(1 s,1 s,0.001,0.001,0.001,0.001,0.001,0.001), complete central pairs first, else forward or backward second-order pairs with the formulas of ADR 0111 and column scaling by T
- **AND** all sixteen commands SHALL be preflighted before any probe launch; unavailable pairs SHALL stop derivative-domain-unresolved without smaller h, penalty residual or fallback
- **AND** SVD SHALL retain six singular values and rcond=1e-10 full/free-column row-rank diagnostics; controls/gradients/active masks SHALL have eight components, with no rank-eight requirement, regularization residual, dynamic scale or changed physical merit
- **AND** face-free columns SHALL be identified by strict physical comparisons L[j]<x[j]<U[j] with recorded margins at the matrix parent, not an inferred SciPy active-mask or a full feasible-tangent-cone claim; eight-control and six-residual shape validation SHALL remain distinct

#### Scenario: Qualify only unchanged target closure and frozen tighter agreement

- **WHEN** an eligible Bezier seed or non-probe objective first satisfies norm(dr)<=10 m AND norm(dv)<=0.01 m/s
- **THEN** optimizer control flow SHALL stop before another Jacobian and exactly one fresh tighter burn/coast of that frozen eight-control command SHALL follow
- **AND** local-qualified SHALL require both profiles to close, endpoint agreement<=1 m / 0.001 m/s / 1e-6 kg, analytic cutoff-mass error<=1e-6 kg and exact coast-mass preservation
- **AND** a tighter failure/disagreement SHALL stop unqualified with no resumed correction; old-reference replays, probes, rank, lower score or optimizer success alone SHALL NOT qualify, and unclosed stationarity/stagnation SHALL retain D16's honest labels

#### Scenario: Bound the new study without extending the previous experiment

- **WHEN** D17 prepares or attempts any native work
- **THEN** one shared 300-second cooperative clock SHALL include binding, two nominal replay evaluations, <=40 objective requests including one initial cache hit, <=40 sixteen-probe Jacobian batches, and at most one reserved tighter evaluation
- **AND** own ceilings SHALL be 681 nominal evaluations (2+39+40*16), 682 total evaluations and 1364 native launches, with 1362 nominal launches and two reserved for the tighter check; attempted failures count before entry, and a complete sixteen-probe batch SHALL fit before its first launch
- **AND** all domain/nonfinite/native/guard/limit failures SHALL stop with finite partial evidence and no retry, substituted dynamics or continuation from an incomplete arc; completed cutoff SHALL survive coast failure
- **AND** evidence SHALL retain separate reference/current source provenance, roles/cache/parents/accepted IDs/best objective, eight controls/units, target/epoch/mass/endpoints, 6x8 matrices/stencils/SVD, bound-margin/gradient associations and independent counters; absent solver status/active-mask after interruption SHALL stay unavailable, not be inferred from an earlier matrix
- **AND** verified D17.2 implementation SHALL precede a separately user-authorized single D17.3 native study; no automatic second study, target/fuel/domain relaxation, new force, public API/UI, automation restart or strict M3 qualification SHALL follow

### Requirement: Bound-aware local targeting follow-up

D16 SHALL follow ADR 0111 as a separate private bounded experiment, preserving
D14/D15 behavior and their immutable evidence. It SHALL use the existing six
controls, two-node chart, forces, physical domain and fixed target state/epoch;
only correction orchestration and its explicitly separate budget SHALL change.
SciPy 1.17.1 SHALL be explicitly pinned with Conda before implementation completion.

#### Scenario: Bind and replay the explicitly selected warm start

- **WHEN** D16 is separately invoked after verified implementation
- **THEN** it SHALL bind the pinned 0104/0107 references and 0110 SHA256 678287cc7aee2b3d83e89c9fbff1113a96d24c5b8960f047aeadb82d049c4274, reconstruct their commands/target/domain/resources, and start only from accepted proposal 52
- **AND** a fresh nominal seed replay SHALL agree with that retained endpoint within 1 m / 0.001 m/s / 1e-6 kg before derivative work; target six-state and tm=979002340.6346419 TDB s, Moon-relative J2000/SI, thrust/Isp, all mass/reserve/window bounds and native profiles SHALL remain fixed
- **AND** the complete timing box SHALL imply at least 1 s coast, not just its seed; an unsupported coupled constraint or changed input SHALL stop without clipping, alternate seed or hidden repair

#### Scenario: Select bounded corrections rather than cap an unconstrained direction

- **WHEN** replay passes without physical closure
- **THEN** D16 SHALL use SciPy least_squares with method=trf, tr_solver=exact, loss=linear, x_scale=1, ftol=xtol=gtol=1e-10, max_nfev=40 and serial calls, in coordinates x=x_seed+T*y with y0=0 and T=(300 s,300 s,0.1,0.1,0.1,0.1)
- **AND** physical bounds SHALL be transformed to those coordinates, residuals SHALL retain the 10 m / 0.01 m/s scales, and the initial request SHALL reconstruct the replayed seed exactly; no uniform D15 cap, dynamic scale, penalty residual, target refit, method switch or fallback start SHALL be introduced

#### Scenario: Differentiate inside the admissible domain

- **WHEN** a callable Jacobian is requested at a completed objective command
- **THEN** each coordinate SHALL use fixed physical h=(1 s,1 s,0.001,0.001,0.001,0.001), preferring a feasible central pair, otherwise a feasible forward two-point pair, otherwise a feasible backward pair, with the second-order formulas of ADR 0111
- **AND** all twelve probes SHALL pass domain preflight before any native launch; an unavailable complete pair SHALL stop without changing h, and center residual reuse SHALL launch no new arc
- **AND** columns SHALL be scaled by T into dr/dy; all stencils, matrices and finite SVD rank/conditioning diagnostics SHALL be retained without treating local rank or a closed probe as physical success

#### Scenario: Qualify only the unchanged physical target

- **WHEN** replay or a completed non-probe objective first satisfies position-norm residual<=10 m AND velocity-norm residual<=0.01 m/s
- **THEN** optimizer control flow SHALL stop before another Jacobian and exactly one fresh tighter repeat of that frozen command SHALL follow
- **AND** local-qualified SHALL require both profiles to close, agreement<=1 m / 0.001 m/s / 1e-6 kg, analytic cutoff-mass error<=1e-6 kg and exact coast-mass preservation; tighter failure/disagreement SHALL stop unqualified without resuming correction
- **AND** optimizer gtol success without closure SHALL be stationary-unclosed, ftol/xtol success without closure SHALL be stagnated-unclosed, and neither SHALL be labelled mission feasibility or proof of nonlinear impossibility

#### Scenario: Bound every call and preserve failure evidence

- **WHEN** D16 prepares, evaluates objectives/probes or attempts native launches
- **THEN** one 300-second cooperative clock SHALL cover binding/setup and all work; counters SHALL include one replay, at most 40 objective requests including its single exact initial cache hit, and at most 20 complete twelve-probe Jacobians
- **AND** the independent ceiling SHALL be 280 nominal evaluations plus at most one reserved tighter evaluation, 281 total evaluations / 562 attempted native launches including failures; SciPy nfev alone SHALL NOT stand in for probe/native counts
- **AND** limits SHALL stop as budget-exhausted before excess work or an unaffordable batch; binding/domain/nonfinite/native/guard failure SHALL stop the entire study without substituted residual, retry or continuation after an incomplete arc
- **AND** new finite JSON and ADR SHALL retain all commands/roles/cache/accepted-iterate identities, residuals, masses/epochs, settings, Jacobians, active bounds/status, own counters and reference/source/resource/runtime provenance even on failure, distinguishing best objectives from probes and unavailable agreement
- **AND** implementation verification SHALL precede a separately user-authorized single native study; no automatic second study, relaxed fuel/target/time, new steering node, public API/UI, automation restart or strict M3 qualification SHALL follow

### Requirement: Bounded local steering and ignition targeting

D15 SHALL follow ADR 0108 as a private local experiment, preserving D14 behavior
and immutable 0104/0107 evidence. It SHALL vary only ignition shift, burn duration
and two dimensionless direction slopes at each of two steering nodes, with fixed
thrust/Isp, circular parking history and Moon-point-mass gravity. Target position,
velocity and absolute TDB epoch SHALL remain fixed; final mass SHALL be computed
from duration, not constrained to the D14 target mass.

#### Scenario: Construct an admissible steered command

- **WHEN** the pinned references and initial command pass validation
- **THEN** D15 SHALL use the fixed orthonormal inertial chart and normalized interpolated direction of ADR 0108, with zero slopes reproducing D14, abs(slopes)<=1 and norm(chart vector)>=1
- **AND** ignition shift SHALL satisfy abs(delta_ti)<=P/4 and the original launch window, duration SHALL satisfy the specified 0.5*tau_D14 to mass-reserve-capped 1.5*tau_D14 interval, cutoff SHALL precede the fixed match epoch by at least 1 s, and dry-mass/provisional-reserve checks SHALL pass before native work
- **AND** the circular initial state SHALL be rotated to actual ignition and steering-rate evidence SHALL NOT be labelled hardware qualification

#### Scenario: Perform only the prescribed local correction

- **WHEN** nominal baseline replay agrees with 0107 within 1 m / 0.001 m/s / 1e-6 kg and the target is not closed
- **THEN** D15 SHALL perform at most four iterations with twelve central probes per iteration, fixed h=(1 s,1 s,0.001,0.001,0.001,0.001), residual scaling 10 m / 0.01 m/s and trust scales T=(300 s,300 s,0.1,0.1,0.1,0.1)
- **AND** the scaled least-squares solve SHALL require rank six with rcond=1e-10 and condition number<=1e10, cap the normalized step once to infinity norm<=1 and require a strictly decreasing finite prediction
- **AND** alpha=1,1/2,1/4,1/8 trials SHALL be relative to the same iterate, accepting the first closed trial or score_trial<=(1-1e-4*alpha)*score_current, without clipping, new scales, fallback solve or native retry

#### Scenario: Qualify closure without changing the target

- **WHEN** the baseline or an accepted nominal iterate first achieves position-norm residual<=10 m AND velocity-norm residual<=0.01 m/s at the fixed target epoch
- **THEN** exactly one fresh tighter repeat of that command SHALL run, and local success SHALL require both profiles to close plus agreement<=1 m / 0.001 m/s / 1e-6 kg, analytic cutoff-mass error<=1e-6 kg and unchanged coast mass
- **AND** tighter disagreement or failure SHALL stop unqualified without resuming iteration; iteration exhaustion without closure SHALL report not-converged and SHALL NOT launch a tighter repeat

#### Scenario: Respect bounds, failures and total work

- **WHEN** binding/replay, central-probe feasibility, rank, finite prediction, step acceptance, sampled guards, native integration or the deadline fails
- **THEN** the study SHALL stop with the applicable unresolved/failure status; analytically infeasible line-search proposals alone SHALL be recorded/skipped within their prescribed slots, without native launch
- **AND** the schedule SHALL remain within 65 nominal proposals, 66 total evaluations and 132 native launches under one 300-second clock including setup, counting attempted failed launches and retaining command/residual/matrix/step/provenance evidence with unavailable fields explicit
- **AND** no alternate seed/branch, automatic follow-up, production-optimizer expansion, strict M3 qualification or automation restart SHALL occur

### Requirement: Bounded local finite-burn departure diagnostic

The system SHALL implement D14 only as the private local diagnostic defined in
ADR 0105, explicitly binding the immutable 0104 reference and its first free-phase
branch. It SHALL use Moon-relative J2000 SI states, TDB seconds from J2000,
constant inertial vector-impulse direction, centered rocket-equation duration,
analytically rotated circular ignition state and lunar point gravity with coupled
mass. It SHALL label omitted perturbations and SHALL NOT claim a full-force or
flight-qualified result. Actual ignition SHALL satisfy retained launch bounds.

#### Scenario: Fixed finite-radius state and time

- **WHEN** the bound reference passes validation
- **THEN** the target SHALL be the outgoing analytic hyperbola at explicitly recorded Rmatch=10*rp and its analytic time of flight, with independent state checks at the D13 invariant tolerances and time-of-flight agreement <=0.001 s
- **AND** cutoff SHALL precede the target epoch, and closure SHALL require position-norm residual <=10 m and velocity-norm residual <=0.01 m/s at that exact epoch, without changing the epoch or substituting asymptotic velocity

#### Scenario: Completed miss is distinct from integration agreement

- **WHEN** verified D14 implementation executes one nominal burn/coast command without a guard failure
- **THEN** one frozen tighter burn/coast repeat SHALL follow even if nominal closure fails, within four native launches and one 300-second deadline including setup
- **AND** agreement SHALL require endpoint differences <=1 m, <=0.001 m/s and <=1e-6 kg, with analytic cutoff-mass error <=1e-6 kg for each profile
- **AND** evidence SHALL report closure and agreement separately, including failed gates, explicit settings, hashes, raw residuals and model omissions, without optimizer, command tuning or retry

#### Scenario: Invalid input or propagation failure

- **WHEN** reference binding, physical/domain inputs, launch window, provisional mass reserve, impact/dry-mass guards, finite states, integration or shared budget fails
- **THEN** execution SHALL stop with a contextual reason and skipped/unavailable remaining evidence, never a substituted successful result or a retry
- **AND** D13 evidence SHALL remain immutable, strict M3 gates SHALL remain open and automation SHALL remain paused

### Requirement: Geometrically consistent local lunar departure seed
D13 SHALL construct an explicitly labelled impulsive two-body lunar departure
reference, not an executable finite-burn or qualified interplanetary trajectory.

#### Scenario: Enforce explicit geometry and phase policy
- **WHEN** given finite SI lunar mu, circular parking radius/oriented plane, nonzero outgoing Moon-relative J2000 excess velocity, TDB epoch and mandatory fixed/free phase policy
- **THEN** D13 uses e=1+rp*norm(v_inf)^2/mu and requires dot(u,v_inf/norm(v_inf))=-1/e at periapsis; fixed phase must satisfy this equality within 1e-12, while free phase enumerates the two nondegenerate plane solutions in normalized phase order without hidden state/epoch/plane changes or automatic selection
- **AND** with R the norm of the asymptote's projection into the parking plane, R<1/e-1e-12 is infeasible and abs(R-1/e)<=1e-12 is near-degenerate/unresolved; unsupported eccentric parking, nonfinite/zero inputs and nonrepresentable hyperbolic geometry fail explicitly rather than inventing a branch

#### Scenario: Build and independently verify a vector impulse
- **WHEN** a branch is geometrically admissible
- **THEN** D13 computes t=(s+u/e)/sqrt(1-1/e^2), v_h=sqrt(norm(v_inf)^2+2*mu/rp)*t and delta_v=v_h-v_parking at identical position/epoch, retaining all three SI vectors, phase, eccentricity, angular momentum and energy with units/frame/time metadata
- **AND** an independent angular-momentum/eccentricity-vector reconstruction matches the outgoing asymptote and velocity within 0.000001 m/s, position within 0.001 m and radial periapsis velocity within 0.000001 m/s; energy error is <=1e-10*max(mu/rp,norm(v_inf)^2/2) m^2/s^2, or the branch fails without tolerance relaxation

#### Scenario: Recompute mass without claiming finite-burn feasibility
- **WHEN** translating the branch's vector impulse into ideal propellant/duration estimates
- **THEN** D13 uses norm(delta_v), actual mass, thrust and Isp; any old arrival impulse is explicitly provisional and applied sequentially to the new departure mass, never reusing old arrival duration/final mass or M2 feasibility labels
- **AND** virtual impulse time is not silently treated as ignition; finite-burn timing/guidance and finite-radius state/epoch matching require a later specified contract, as do outer Lambert matching and Mars capture; no native mission run, automatic optimizer, UI change, public scenario mutation or strict M3 qualification occurs

### Requirement: Bounded damping of the retained central correction
D12 SHALL evaluate only alpha=0.5 and conditionally alpha=0.25 of the retained
D11 correction from the original seed, without a new solve, derivative probes,
chained updates or changes to D4–D11 scientific contracts.

#### Scenario: Bind central correction evidence and replay the baseline
- **WHEN** D12 receives pinned 0079 and 0098 with SHA256 17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235 and b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057
- **THEN** it verifies scenario/candidate/seed/target/runtime/resources/settings, historical 0079/0095 identities, completed nominal baseline and alpha=1 trial, not-improving outcome without selection/tighter, and finite rank-six matrix/correction with algebraically consistent cap, trust units and prediction; raw endpoint residuals and recorded improvement are reconstructed without a solver or native probes
- **AND** a fresh nominal baseline matches both retained baselines at four identical epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg; mismatch stops before fractions, and both existing 1000 m and 0.01 m/s closure gates stop as baseline-closed with both fractions skipped

#### Scenario: Test independent fractions and stop at the first improvement
- **WHEN** the baseline replay passes without closure
- **THEN** D12 evaluates seed+0.5*retained_step and only after its completed non-improvement evaluates seed+0.25*retained_step, independently from the seed through existing canonical angle/window/mass gates, with unchanged target/settings and fresh environments
- **AND** empirical improvement requires S_trial <= S_baseline*(1-0.0001*alpha) or both closure gates, with actual thresholds, physical misses, raw/scaled residuals and score ratios recorded; any linear prediction is diagnostic only and cannot select a command
- **AND** the first improvement selects exactly one frozen canonical-command tighter evaluation with identical initial/target states and four-boundary 10 m, 0.0001 m/s and 0.000001 kg agreement gates; remaining fractions are skipped, and disagreement or failure preserves nominal improvement without fallback

#### Scenario: Bound one invocation and retain honest evidence
- **WHEN** D12 completes or a replay/analytic/event/native/nonfinite/deadline failure occurs
- **THEN** one shared cooperative 300-second clock permits at most three nominal control attempts counted before analytic validation, four evaluations and twelve native launches, with no extra control counted for the frozen tighter evaluation
- **AND** finite exclusive-output JSON retains reference/current/imported source provenance, retained matrix/step, exact fraction commands, completed diagnostics, skipped/unavailable reasons, attempted/completed counters and separate wall time, without unfinished endpoints
- **AND** no retry, additional fraction, derivative probe, new solve or budget increase occurs; continuous_safety_verified remains false and improvement, closure and numerical agreement are separate from strict M3 qualification; no further experiment starts automatically

### Requirement: One retained-central-matrix research correction
D11 SHALL test at most one correction computed from the retained D10 central
matrix around the original seed, without re-probes, iterative targeting,
additional fractions, changed settings or modifications to D4–D10 contracts.

#### Scenario: Verify central evidence and replay the baseline
- **WHEN** D11 receives pinned 0079 and 0095 with SHA256 17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235 and 8be4356f4c339eaad9ca30ce2f49786d7e65498ae731fc468d8810836a97fb55
- **THEN** it verifies completed D10 evidence, scenario/candidate/seed/target, reference/runtime/resource/settings identity, thirteen nominal runs, six finite ordered central columns reconstructed from raw endpoint residuals with the original scales, and both passing <=0.10 D10 nominal slope checks before preparing a correction
- **AND** a fresh nominal baseline must match both retained nominal reports at all four identical epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg; mismatch stops before the solve, and a baseline already within 1000 m and 0.01 m/s stops as baseline-closed without a solve or trial

#### Scenario: Solve and cap one new direction
- **WHEN** the baseline replay passes and is not closed
- **THEN** D11 forms J with residual rows and central-control columns, solves J*z=-r once for the fresh scaled residual using NumPy least squares with rcond=0.000000000001, records finite singular values/rank and requires rank six without a fallback
- **AND** it records uncapped z, divisor=max(1,norm_inf(z)), capped z, dx=T*z/divisor with T=(0.25 rad,0.25 rad,600 s) repeated twice, and the signed/scaled prediction r+J*(dx/T); a zero step, nonfinite result or predicted score not strictly below baseline stops before trial propagation

#### Scenario: Evaluate one trial and optionally freeze it for tighter checking
- **WHEN** the capped correction is available
- **THEN** the sole nominal trial uses seed+dx at alpha=1 through existing canonical angle/window/mass gates, with the unchanged target and fresh matched environment
- **AND** empirical improvement requires S_trial <= S_baseline*(1-0.0001) or both unchanged closure gates, with separate position/velocity misses, predicted/observed residual changes, score ratio and threshold; non-improvement stops without tighter propagation
- **AND** only an improving trial receives one tighter evaluation with frozen canonical commands, initial and target states; all four boundaries use the existing 10 m, 0.0001 m/s and 0.000001 kg gates, and failed/unavailable agreement does not erase nominal improvement or trigger another command

#### Scenario: Enforce a single invocation budget and preserve failure evidence
- **WHEN** D11 completes or any replay/analytic/native/event/nonfinite/deadline gate fails
- **THEN** one shared cooperative 300-second clock and limits of two control attempts, three evaluations and nine native launches apply from input verification through reporting, nominal attempts count before analytic validation, and the frozen tighter run adds no control attempt
- **AND** finite exclusive-output JSON retains pinned/current/imported provenance, raw residuals, imported matrix, solve/cap/prediction, exact commands, available comparisons, attempted/completed counters, unavailable reasons and separate wall time; completed earlier diagnostics remain, unfinished endpoints do not
- **AND** no retry, additional fraction, derivative probe, second solve or budget increase occurs, continuous_safety_verified stays false and improvement, closure and numerical agreement remain distinct from strict M3 or mission qualification

### Requirement: Approval-gated central-column research diagnosis
D10's scope in ADR 0093 was explicitly approved by the user on 2026-10-04.
D10 SHALL test a nominal central Jacobian at the
original six D7 probe increments without selecting commands, solving another
correction, changing production settings or modifying D4–D9 contracts.

#### Scenario: Bind retained evidence and replay nominal inputs
- **WHEN** an approved D10 invocation receives 0079, 0086 and 0092
- **THEN** it verifies the pinned SHA256 hashes 17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235, c370c31f4a3dcd1f3ef324d0f2331bb46d707af0eae6d256ee935471a6c9233d and 164760a35451b3e8cf43bf2213e8466a331dbcb85004249e134e9daefa1a7374 respectively, scenario/candidate/seed/target, resource/runtime/settings identity and completed retained diagnostics before perturbation
- **AND** it verifies the finite retained rank-six D7 direction/Jacobian and nonzero predicted norm, replays all four nominal baseline boundaries against all three references at identical epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg, and verifies each positive probe against its matching D7 run with those same gates before the corresponding negative probe
- **AND** any mismatch stops without running later commands, while cross-profile baseline disagreement is retained as context rather than used to relax replay gates

#### Scenario: Evaluate only the prescribed central columns
- **WHEN** the baseline replay passes
- **THEN** D10 forms twelve independent seed-based perturbations, positive then negative per column, in departure then arrival azimuth/elevation/duration order with h=(0.00001 rad,0.00001 rad,1 s) repeated twice, using the existing canonical command gates, fixed target epoch and fresh matched environments
- **AND** the baseline and twelve probes use nominal settings only, with limits of thirteen control attempts counted before analytic validation, thirteen evaluations and thirty-nine native launches under one cooperative 300-second clock from input verification through reporting
- **AND** analytic rejection, sampled event, native failure, nonfinite calculation or deadline terminates the invocation without retries, tighter runs, chained controls, incomplete endpoints or automatically enlarged limits

#### Scenario: Compare central prediction with retained directional response
- **WHEN** all thirteen nominal evaluations complete
- **THEN** with scaled residuals r, original trust scales T and z=retained_step/T it reports columns C_i=(r(+h_i)-r(-h_i))*T_i/(2*h_i), F_i=(r(+h_i)-r(0))*T_i/h_i and E_i=((r(+h_i)-r(0))+(r(-h_i)-r(0)))*T_i/(2*h_i), including signed differences from the retained D7 columns and the arithmetic identity F_i-C_i=E_i
- **AND** it reports each central/forward directional contribution, E_i*z_i, their sums, retained and new predictions and cancellation metrics, with explicit unavailable reasons for zero-denominator or nonfinite ratios
- **AND** the two norm(D9_nominal(a)-sum(C_i*z_i))/norm(g_D7) checks for a=2^-14 and 2^-15 use the exploratory <=0.10 threshold; overall nominal directional consistency requires both checks, zero central direction is not divided by, and no correction solve or command selection occurs even if a probe improves
- **AND** consistency at this one seed/increment/profile does not qualify individual columns, cross-profile sensitivity, derivative error bounds, convergence, accuracy, mission closure or continuous safety

#### Scenario: Retain complete or failed column-study evidence
- **WHEN** D10 completes or aborts
- **THEN** finite exclusive-output JSON retains source/reference/resource/settings identities, historical imported hashes separately from current source hashes, seed and exact commands/column/sign ordering, raw SI and scaled residuals, replay differences, attempted/completed counters, available columns/checks with unavailable reasons and separate wall time
- **AND** earlier evidence is untouched, unavailable summaries are not manufactured from incomplete pairs, continuous_safety_verified remains false and no additional native study is started automatically

### Requirement: Bounded local directional-response diagnosis
D9 SHALL evaluate the retained D7 direction around the original seed using
alpha=(0,+2^-14,-2^-14,+2^-15,-2^-15), with nominal then frozen tighter
propagation for each command. It SHALL preserve the physical model, target,
reference bindings and existing D4-D8 contracts without selecting a command
or performing another correction solve.

#### Scenario: Verify inputs and both baseline profiles
- **WHEN** D9 receives the pinned 0079 and 0086 artifacts
- **THEN** it verifies their hashes, scenario, candidate, seed, finite rank-six direction, Jacobian and resource/runtime/settings identity under the shared deadline
- **AND** the nominal baseline must match the retained 0079/0086 nominal boundaries and the tighter baseline must match 0079 tighter boundaries at identical epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg before perturbations
- **AND** nominal-versus-tighter disagreement is retained as a diagnostic and does not replace within-profile replay checks or prevent the requested sensitivity study

#### Scenario: Execute fixed small perturbations
- **WHEN** both baseline replay checks pass
- **THEN** the four signed perturbations are independently formed as seed+alpha*retained_step in the specified order, validated through the existing command gates, and each receives nominal then tighter propagation with frozen canonical controls and fresh matched environments
- **AND** control attempts count five distinct nominal commands before analytic validation, while all ten profile evaluations and thirty native launches are counted independently; frozen tighter runs add no control attempt
- **AND** one cooperative 300-second clock covers verification through reporting; a command rejection, sampled event, native failure, nonfinite calculation or deadline stops all later runs without retries or partial endpoints

#### Scenario: Quantify response rather than choose a correction
- **WHEN** all ten profile evaluations complete
- **THEN** using scaled signed residuals r and g=J*(retained_step/trust_scales), D9 reports predicted and observed changes at every signed alpha, central slopes D(a)=(r(+a)-r(-a))/(2*a) and curvature C(a)=(r(+a)+r(-a)-2*r(0))/(2*a) for a=2^-14 and 2^-15 in each profile
- **AND** with G=norm(g)>0 it reports norm(D(a)-g)/G, norm(C(a))/G, norm(D(a)-D(a/2))/G and norm(D_nominal(a)-D_tighter(a))/G, including signed vectors and unavailable-ratio reasons rather than NaN or infinity
- **AND** each discrepancy is diagnostically consistent when at most 0.10; overall consistency requires every model, curvature, scale and profile check to pass, and the report records actual thresholds without implying absolute accuracy, a derivative error bound, mission closure or continuous safety
- **AND** zero predicted directional norm prevents perturbations with an explicit unavailable diagnostic; improvement/closure is informational only and no trial is selected even if its score decreases

#### Scenario: Preserve complete or failed diagnostic evidence
- **WHEN** D9 finishes or aborts
- **THEN** finite exclusive-output JSON retains source/reference/resource/settings provenance, original direction/Jacobian, exact commands and alpha/profile ordering, residuals, baseline comparisons, completed discrepancies and attempted/completed counters with contextual reasons
- **AND** missing comparisons remain absent with a reason, historical imported source hashes remain distinct from current hashes, wall time is separate, and continuous_safety_verified remains false

### Requirement: Bounded damping of a retained research correction
D8 SHALL evaluate the retained D7 control direction at alpha=0.5 followed by
alpha=0.25 only if the first completed nominal trial does not improve. It SHALL
reuse the original seed, physical model and integrator settings without new
probes, a new solve, chained updates or changes to D4–D7 contracts.

#### Scenario: Bind evidence and replay the baseline
- **WHEN** D8 receives the pinned Decision 0079 and Decision 0086 artifacts
- **THEN** it verifies hashes, normalized inputs, seed, candidate, runtime/resources/settings and a finite rank-six D7 direction within the existing trust scales before damping
- **AND** a fresh nominal baseline must match both retained baselines at all four boundary epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg; mismatch stops before either fraction, and an already-closed baseline stops without a convergence claim

#### Scenario: Try fractions in deterministic order
- **WHEN** the baseline passes and remains outside target closure
- **THEN** each attempted command is canonicalized from x_seed+alpha*dx_D7 with alpha in (0.5,0.25), never from a previous trial
- **AND** improvement is both unchanged endpoint gates of 1000 m and 0.01 m/s passing or S_trial <= S_baseline*(1-0.0001*alpha), using the existing residual scales of 1000 m and 0.01 m/s
- **AND** the first improving nominal trial is selected, any remaining fraction is explicitly skipped, and no probes, alpha=1 repeat, additional fraction or second iteration runs

#### Scenario: Validate only the selected trial
- **WHEN** a nominal fraction is selected
- **THEN** exactly one tighter run uses its frozen canonical controls, initial state and epochs in a fresh resource-matched environment, with all four boundary differences checked against 10 m / 0.0001 m/s / 0.000001 kg
- **AND** disagreement or unavailable validation remains separate from nominal improvement and cannot trigger another fraction; if neither fraction improves, no tighter run starts

#### Scenario: Bound failures and preserve honest evidence
- **WHEN** validation, a command, a sampled guard, integration or the deadline fails
- **THEN** no subsequent run starts; incomplete endpoints remain absent, previous completed diagnostics and contextual reasons are retained, and no successful mission is inferred
- **AND** one shared 300-second cooperative deadline, three control attempts, four propagation evaluations and 12 native launches bound the invocation with no retries or budget resets
- **AND** exclusive finite JSON records both references, source/resource/settings identity, frozen direction, controls and alpha, residual norms/scores/ratios with explicit unavailable reasons, actual acceptance thresholds, selected/skipped fractions, counters, coverage and separate wall time, always with continuous_safety_verified=false

### Requirement: Bounded research-only command correction
The D7 experiment SHALL test at most one six-control update from the prescribed
reference seed, using the unchanged physical model, target and nominal/tighter
integrator profiles. D4–D6 limits SHALL remain unchanged. D7 SHALL remain separate
from the production corrector and SHALL always disclaim continuous safety.

#### Scenario: Verify baseline before changing commands
- **WHEN** D7 is invoked for the pinned reference fixture and candidate d0001-t0035
- **THEN** it verifies Decision 0079 identity, scenario, candidate, seed and resource provenance and recomputes a nominal baseline with a fresh environment
- **AND** probes start only if all four boundary epochs and controls match and state/mass drift stays within 10 m, 0.0001 m/s and 0.000001 kg; otherwise the report records the mismatch and no probe launches

#### Scenario: Compute one empirical correction
- **WHEN** the baseline completes and does not already meet both target gates
- **THEN** six forward probes run in control order using increments (0.00001 rad, 0.00001 rad, 1 s) for each burn, with separate fresh resource-matched environments
- **AND** the scaled residual uses 1000 m and 0.01 m/s, trust scales use (0.25 rad, 0.25 rad, 600 s) for each burn, and the scaled Jacobian and NumPy least-squares solve use rcond=1e-12 with finite rank six required
- **AND** the update is capped to unit infinity norm in trust coordinates before one alpha=1 trial; no damping retry, alternate finite difference, extra iteration or probe-as-command is permitted

#### Scenario: Distinguish improvement from target closure and validation
- **WHEN** the corrected nominal trial completes
- **THEN** the report stores signed terminal residuals, separate position/velocity norms, scaled score and its ratio to baseline (null with reason for a zero denominator)
- **AND** improvement means both endpoint gates of 1000 m and 0.01 m/s pass or the score is at most 0.9999 times the baseline score; neither improvement nor closure implies mission qualification
- **AND** only an improving trial receives one frozen-command tighter run, whose four boundary differences use the unchanged 10 m / 0.0001 m/s / 0.000001 kg gates and whose failed or unavailable agreement is retained separately

#### Scenario: Preserve bounded failures and evidence
- **WHEN** a control or probe is rejected, the Jacobian loses rank, a native run fails, a sampled guard triggers or the deadline expires
- **THEN** no further trial starts; the reason, prior completed evidence and attempted/completed counts remain, while incomplete endpoints and unavailable comparisons stay absent
- **AND** one shared 300-second cooperative deadline, eight control attempts, nine propagation evaluations and 27 native arcs are hard invocation limits, with no retries or automatically enlarged budget
- **AND** finite exclusive-output JSON records source/reference/resource/settings identity, each run's controls and role, residual changes, Jacobian, rank and singular values when available, sampled-check coverage and separate wall time; the report never marks strict M3 or continuous safety complete

### Requirement: Separate opt-in research experiment
The system SHALL provide an explicitly requested D4 research experiment distinct
from strict M3 refinement. It SHALL NOT return PhysicalTrajectoryResult, claim
converged M3 status, certify continuous safety or complete task 3.9. Existing M3
acceptance gates SHALL remain unchanged. The first experiment SHALL propagate
one fixed seed command, not optimize commands or silently choose a candidate.

#### Scenario: Run the reference experiment
- **WHEN** the user explicitly selects examples/m3_feasible_mission.toml and candidate d0001-t0035 from its default 2000-budget search
- **THEN** the experiment verifies the candidate against that scenario, records the normalized inputs and identifier, and labels all output research-only with continuous_safety_verified=false
- **AND** selecting another budget or scenario does not silently reuse the reference candidate's stored physical data

### Requirement: Fixed-command finite-burn propagation
The experiment SHALL reuse the pinned direct-SPICE M3 force inventory, physical
boundary-state conventions, existing TNW engine adapter and analytic seed
controls. It SHALL propagate departure burn, coast and arrival burn with coupled
mass and exact state handoff, without resetting state or mass between arcs.
It SHALL retain input/resource validation, analytic dry-mass rejection, sampled
mass/collision guards, detected-event handling and native failure checks. Unlike
strict M3, a whole-interval safety enclosure is not a prerequisite for this
separately labelled experiment; its absence SHALL be explicit in every report.

#### Scenario: Complete a nominal seed
- **WHEN** all three nominal arcs complete without a detected invalid state
- **THEN** the report contains four ordered boundary states in SI/SSB/J2000 with TDB epochs, two positive-duration burns, their directions and consumed masses, and position/velocity residual norms against the configured target state at the arrival epoch
- **AND** a miss is reported as a miss rather than silently corrected or called convergence

#### Scenario: Reject detected unsafe or failed propagation
- **WHEN** an initial or evaluated state reaches dry mass or a configured collision boundary, resources are unavailable, or the native integrator fails
- **THEN** the experiment stops with a reason and body/arc/epoch context where available, reports no completed endpoint or target residual from partial history, and never clamps mass or continues from an unsafe state
- **AND** event rejection takes precedence over a final-epoch mismatch caused by that event

#### Scenario: Declare observation limits
- **WHEN** any report is produced
- **THEN** it identifies which states/events were checked and explicitly states that undetected between-check impacts, small bodies and debris are not excluded; minimum sampled separation is not labelled continuous clearance

### Requirement: Independent integration-profile comparison
After nominal completion the experiment SHALL repropagate identical commands and
arc boundaries with the existing tighter profile. It SHALL report all four
boundary differences in metres, metres/second and kilograms. Numerical agreement
SHALL require differences no greater than 10 m, 0.0001 m/s and 0.000001 kg at
every boundary. Agreement SHALL NOT imply target closure or real-world accuracy.

#### Scenario: Compare frozen commands
- **WHEN** both profiles finish within resource limits
- **THEN** numerical_agreement is true only if all stated thresholds pass, target residuals are reported separately, and the commands are identical in both runs

#### Scenario: Comparison fails or cannot complete
- **WHEN** a boundary difference exceeds a threshold or the tighter run fails or times out
- **THEN** numerical_agreement is false or unavailable respectively with its reason; completed nominal diagnostics may be retained only as explicitly unverified research evidence, never a successful strict-M3 result

### Requirement: Bounded reproducible research report
The first experiment SHALL share the scenario's monotonic runtime budget across
candidate verification, resource preparation, nominal propagation and tighter
comparison (default 300 seconds, no reset). It SHALL allow at most six native
arc launches, with no optimizer, retries or hidden background runs. It SHALL
record attempted/completed arc counts, model/resource provenance, commands,
integrator settings, checked-state counts and outcome. Wall-clock diagnostics
SHALL be separated from reproducible scientific values.

#### Scenario: Stop at the budget
- **WHEN** the runtime budget expires or another arc would exceed six launches
- **THEN** no further arc is started, timeout/budget failure is explicit and partial diagnostics are not marked as a completed trajectory

#### Scenario: Repeat identical input
- **WHEN** identical inputs, resources and commands are run twice with sufficient time
- **THEN** scientific report values and classification agree, excluding wall-clock measurements, without modifying existing M2 outputs or strict M3 acceptance

### Requirement: Isolated identical-start coast diagnosis
The research-only D5 follow-up SHALL compare the two existing coast integrator
profiles from the same stored nominal departure-cutoff Cartesian state, mass
and TDB epoch to the same stored arrival-ignition epoch. Its reference SHALL be
the retained Decision 0079 report, whose science was reproduced in Decision 0081.
It SHALL verify the input artifact digest, normalized scenario, reproduced
candidate, epochs, frames and resource/model identity before propagation. A
stored cutoff is an experimental initial condition, not a qualified mission state.
Each profile SHALL use a fresh pinned full-force environment without thrust.
No departure or arrival burn, optimizer, retargeting or changed tolerance is
permitted. This separate experiment SHALL share one 300-second cooperative
deadline from input verification through both profiles and allow at most two
native arc launches, counted before execution, with zero automatic retries.

#### Scenario: Compare profiles with identical inputs
- **WHEN** the verified reference is propagated with nominal and tighter coast settings
- **THEN** both native initial histories match the same seven supplied SI state/mass components and start epoch exactly, both end at the stored arrival-ignition epoch within the existing 1 microsecond completion tolerance, and every saved coast mass equals the initial mass
- **AND** the report records both endpoints and their position, velocity and mass differences using unchanged 10 m, 0.0001 m/s and 0.000001 kg comparison thresholds, without claiming either profile is ground truth

#### Scenario: Distinguish restart drift from inherited differences
- **WHEN** both coast profiles complete
- **THEN** the report separately records the new nominal endpoint minus the stored nominal endpoint, the new nominal endpoint minus the new tighter endpoint, and the new tighter endpoint minus the stored tighter endpoint, as signed Cartesian differences and norms with explicit units
- **AND** it does not subtract norms to attribute errors, interpret restart drift exceeding existing comparison thresholds as isolated integration error, or claim that the new tighter-minus-stored-tighter difference is a mathematically exact sensitivity estimate

#### Scenario: Reject invalid inputs or an incomplete coast
- **WHEN** reference identity fails, a sampled guard rejects a state, the deadline expires or a native arc fails
- **THEN** no subsequent native arc starts, attempted/completed counters and a contextual reason are retained, and the failed arc has no endpoint or comparison derived from partial history
- **AND** complete prior-profile evidence may remain explicitly unqualified; D4 pre-arc/full-step/saved-history guards, dry-mass equality rejection, event-before-epoch-mismatch handling and declared coverage limitations remain in force

#### Scenario: Preserve diagnostic provenance
- **WHEN** a coast diagnostic finishes or aborts
- **THEN** finite machine-readable evidence records the reference digest, source identity, normalized scenario, candidate, resource/model metadata, actual integrator settings, supplied initial state and epochs, guard coverage, counters and outcome separately from wall time
- **AND** it states research-only and continuous_safety_verified=false, does not overwrite prior evidence, and does not qualify target closure, strict M3 or task 3.9

### Requirement: Bounded single-variable coast step study
The research-only D6 study SHALL run at most three coast profiles from the same
nominal departure cutoff used by D5, in order of maximum step 21600, 10800 and
5400 seconds. Each SHALL use the pinned tighter rkdp_87 profile with only its
maximum_step_s changed in a diagnostic-local copy. Relative/absolute tolerances,
initial/minimum step, termination policy, forces, mass, start/end epochs and
reference conventions SHALL remain unchanged. Production profiles and D5's
two-launch limit SHALL remain unchanged. One shared 300-second cooperative
deadline SHALL cover input verification, preparations and all three launches.
No retries, additional profiles, optimizer or automatic production promotion
are permitted. D5 reference/resource verification and sampled guards SHALL apply.

#### Scenario: Bind the step-study baseline
- **WHEN** D6 starts with verified Decision 0079 and Decision 0082 artifact identities
- **THEN** each native initial history matches the same seven supplied state/mass components and epoch exactly, and the first completed endpoint is compared to Decision 0082's tighter endpoint
- **AND** if baseline drift exceeds 10 m, 0.0001 m/s or 0.000001 kg, no smaller-step profile starts and the report states baseline mismatch rather than attributing a difference to step refinement

#### Scenario: Change only the maximum step
- **WHEN** all three diagnostic settings are constructed
- **THEN** their scientific settings differ only in maximum_step_s with exact values 21600, 10800 and 5400, and querying the original production profiles before and after returns identical values
- **AND** each profile uses a fresh resource-matched full-force environment without thrust, preserves constant coast mass and completes under the existing epoch tolerance

#### Scenario: Report empirical refinement without an accuracy claim
- **WHEN** all profiles finish
- **THEN** the report contains signed endpoint differences and position/velocity/mass norms for every pair, plus unchanged-threshold flags for each pair
- **AND** it reports the second adjacent difference divided by the first separately for position and velocity when the denominator is positive; zero denominators produce null ratios with an explicit reason, never NaN, infinity or a fictitious convergence order
- **AND** it distinguishes decreasing, unchanged or increasing adjacent differences without asserting absolute accuracy, an asymptotic order, a global error bound or task-3.9 safety

#### Scenario: Observe whether the step cap changed the calculation
- **WHEN** a profile completes
- **THEN** the report retains a digest of its ordered saved epoch sequence and saved-interval count, minimum, median and maximum in seconds, labelled saved intervals rather than RK stages or all attempted internal steps
- **AND** unchanged saved meshes or unchanged endpoints are reported explicitly and are not by themselves called proof of convergence

#### Scenario: Preserve failures and stop within the study budget
- **WHEN** input verification fails, a sampled event is rejected, a native call fails or the shared deadline expires
- **THEN** no further profile starts, attempted/completed arc counts and contextual reasons are retained, incomplete profiles expose no endpoint, and comparisons requiring missing endpoints are unavailable
- **AND** evidence is finite JSON, records source/reference/resource/settings identity and guard coverage, separates wall time, never overwrites earlier artifacts and always disclaims continuous safety and mission qualification


### Requirement: Review retained finite-radius evidence before a new boundary experiment

The R4 boundary review SHALL preserve R1–R3 and D13–D17 evidence and existing
public M3 ignition/cutoff, orbital-state, force-model and closure contracts.
It SHALL NOT treat equal candidate inputs as connected physical trajectories.

#### Scenario: Reuse identical inputs without conflating models

- **WHEN** the frozen ADR0119 and ADR0104 records are reviewed for R4.1
- **THEN** the review SHALL compare every normalized scenario and selected-candidate field, retain both input digests and report numerical equality separately from model/provenance identity
- **AND** it SHALL distinguish the retained SPICE and harmonic GMs, fixed/free phase, virtual-periapsis versus ignition/cutoff events, provisional mass and unresolved outer-transfer/Mars-capture links without new states, native calls or repeated geometry
- **AND** D13 fixed-phase infeasibility SHALL refer only to its constrained local construction, not general finite-thrust or mission impossibility

#### Scenario: Require a complete contract before new boundary work

- **WHEN** a new finite-radius experiment is proposed after the review
- **THEN** its contract SHALL first bind exact initial/target states and epochs or deterministic construction, explicit phase/event/branch policy, local/outer interface states and models, shared mass history, six-component continuity residuals, numerical gates, independent reference and wall-time/native-call limits
- **AND** unresolved values SHALL remain explicit and SHALL NOT authorize implementation, propagation, changed historical inputs, silent phase/epoch/radius selection, repeated failed studies or relaxed existing local/mission gates


### Requirement: Preserve fixed orbital endpoints and distinguish interface assembly from physics

R4 SHALL use ADR0135's unchanged configured orbital endpoints and exact burn
interfaces; the retained M2 curve and D13/D14 local states SHALL NOT be spliced
into a claimed physical solution. A future mission run requires its own complete
command/reference/budget contract and SHALL NOT be authorized by an endpoint audit.

#### Scenario: Fix endpoints and exact interfaces without selecting new controls

- **WHEN** the R1-specific boundary contract is inspected
- **THEN** complete retained0098 initial/target records and exact R1 scenario/candidate equality SHALL bind departure ignition and arrival cutoff, harmonic GMs, original orbital phases and SSB/J2000/SI/TDB conventions
- **AND** any future explicitly supplied admissible burns SHALL join at t0+tau_d and tf-tau_a with unchanged production forces, positive burn durations and positive coast, preserving existing1e-6s/0.001m/1e-6m/s/1e-9kg join and1000m/0.01m/s target gates
- **AND** shared sequential mass SHALL protect dry mass; a new R1 reserve claim SHALL require actual final mass>=550kg, with no copied M2 or provisional D13 feasibility

#### Scenario: Audit only retained boundary arithmetic

- **WHEN** the once-only R4.3 audit executes after the ADR0135 contract
- **THEN** it SHALL bind unchanged0119/0098 digests and independently compare both retained endpoints against binary64 rotation/vis-viva and80-digit Decimal p-based orbital arithmetic using the stored eccentricity/angles, at0.001m/1e-6m/s Euclidean gates in relative and SSB coordinates
- **AND** a100-digit Decimal repeat SHALL establish oracle agreement<=1e-12m/1e-15m/s; raw inputs, signed residuals, norms, labels/constants/digests/counters and failures SHALL be retained in exclusive new evidence
- **AND** the shared10s read/check/arithmetic/serialization/flush budget SHALL permit zero scientific imports, native reads, propagation, optimization or new observed states; unexpected failure SHALL stop without changed gates/data or retry
- **AND** an arithmetic/assembly pass SHALL NOT claim achieved interior states, independent dynamical validation, full-mission target closure, reserve, safety or strict M3 completion


### Requirement: Check retained lunar-to-Mars interface readiness

The R5.52–R5.54 saved-data check SHALL authenticate one outgoing
R5.51 model B state and assess the retained receiving-side inventory
for `d0001-t0035`. It SHALL preserve the existing finite-burn
interface and target contract from R4.

#### Scenario: Authenticate the fixed outgoing archive packet

- **WHEN** the offline worksheet reads the frozen R5.51 archive
- **THEN** it SHALL verify both bound phase manifests/receipts and the lengths, raw/compressed hashes and counts of the five pinned members, and bind the terminal tighter RK4 state at 979014965.9635216 TDB s bit for bit across raw index 32,000, common sample 320 and both audited direction records
- **AND** it SHALL verify SSB/J2000, SI, TDB seconds since J2000, model B inventory, the common and mesh Moon operands against their respective archived sources, and 1351.7475727997967 kg as unchanged archived cutoff/coast metadata
- **AND** independent exact signs and Decimal80 radius and radial speed SHALL match both audited endpoint operands within 1e-6 m and 1e-9 m/s, respectively, before `source-state-authenticated` is reported

#### Scenario: Keep missing receiving evidence separate from source verification

- **WHEN** the pinned R1/R2 ideal nodes and retained full-model boundary and endpoint records are inspected
- **THEN** the worksheet SHALL check exact epoch words in the 121 audited ideal nodes and the pinned timed boundaries/endpoints, retain neighboring ideal epochs and record per-source eligibility based on exact epoch, event, frame/units, model, independent provenance and mass
- **AND** the frozen archive SHALL report `ideal-reference-coepoch-unavailable` and `physical-join-not-established` with null continuity residuals; shared initial ancestry, identical candidate ID, a mesh digest, interpolation, copied state, re-epoching or an arrival target SHALL NOT supply an incoming state
- **AND** a later compatible physical comparison requires a separately defined same-event, same-epoch independent receiving state and mass, retaining R4 join and target gates with no physical-closure claim from this worksheet

#### Scenario: Bound the offline check and fail on invalid evidence

- **WHEN** a prepared, separately requested worksheet runs once
- **THEN** a monotonic parent deadline SHALL limit the complete process through receipt finalization to 15 s, five members of up to 16 MiB raw each, 80 MiB raw and 25 MiB compressed payload total, 218,972 archived lines, 1 MiB archive metadata, 2 MiB compact input JSON and 128 KiB output
- **AND** it SHALL make zero scientific imports, native/SPICE or kernel calls, force evaluations, propagations or new trajectory states, and SHALL preserve first safe evidence without retry; missing, inconsistent, corrupt or late evidence SHALL yield `invalid-evidence` without certification

### Requirement: Design an independent Mars receiving state

R5.55 SHALL distinguish an analytically generated ideal coepoch
reference from an independently propagated same-model physical
receiver. The fixed checkpoint SHALL be the authenticated R5.51
terminal sample at 979014965.9635216 TDB s since J2000
(`0x1.d2d4a9afb54adp+29`) for `d0001-t0035`.

#### Scenario: Generate and check one ideal coepoch reference

- **WHEN** a synthetically qualified R5.56 worksheet receives a separate authorization for one R5.57 run
- **THEN** it SHALL bind ADR0202's exact source hashes, R5.54 outgoing packet, and the receipt-bound geometric Sun six-state at study shard 0 row 337 (node 320) at the exact checkpoint with matching archived ordered kernel identity, without an ephemeris call
- **AND** it SHALL reconstruct the Sun-only state backward from R1 run 1 node 120 with its pre-impulse spacecraft velocity and separately forward from the R2 departure seed, preserving R2's domain, invariants, root limits and 1 m / 1e-6 m/s Euclidean agreement in both Sun-relative and SI/SSB/J2000 states
- **AND** it SHALL record the root/translation evidence and signed ideal-minus-B position and velocity differences separately from physical continuity; ideal mass and physical residuals SHALL remain null, and the physical status SHALL remain `physical-join-not-established`
- **AND** one isolated process SHALL allow two analytic evaluations at the one epoch, at most 64 root updates each, 42,862 lines, one 16 MiB raw / 5 MiB gzip member, 2 MiB compact inputs, 1 MiB archive metadata and 128 KiB output under 15 s through receipt finalization; failure SHALL retain first safe evidence without retry, and SPICE, kernels, force evaluations, numerical propagation and fitting SHALL have zero budget

#### Scenario: Keep the physical study unavailable until independently testable

- **WHEN** a physical receiver and checkpoint comparison are proposed
- **THEN** readiness SHALL bind the fixed R4 ignition and Mars orbit cutoff target, one independently specified admissible command pair and command-derived mass ledger, full production force/resource identity and coverage, two reverse segments split at exact arrival ignition, independent validation and finite qualified wall/RHS/query/output limits
- **AND** the receiving state SHALL come from the Mars target without using or fitting to outgoing checkpoint operands, and the outgoing operand SHALL be generated separately under the same production model; archived model B SHALL NOT serve as the physical outgoing operand or redefine either R4 burn interface
- **AND** a compatible pair SHALL match the exact epoch and report signed time, six-state and mass residuals under the unchanged 1e-6 s / 0.001 m / 1e-6 m/s / 1e-9 kg join gates; a separate unreset forward check SHALL retain the 1000 m / 0.01 m/s R4 target gates
- **AND** missing compatible evidence SHALL leave physical residuals null; uncertainty too large to resolve a gate SHALL remain inconclusive; this design SHALL authorize no physical execution, default command or optimizer trial

### Requirement: Test one fixed command pair at the physical checkpoint

R5.58 SHALL define a readiness-gated full-production-model checkpoint
comparison at the exact R5.51 terminal epoch for `d0001-t0035`;
the archived model B and R5.57 ideal states SHALL NOT be admitted
as physical operands. The test SHALL preserve R4's orbit states,
burn interface semantics and target gates.

#### Scenario: Reject an unfrozen command or incomplete readiness

- **WHEN** physical readiness is assessed
- **THEN** it SHALL require one independently justified six-value canonical TNW command packet bound by digest to the fixed R4 boundaries and production model, finite positive durations with exact event ordering t0 < t1 < t* < t2 < tf, and the sequential 2,000 kg initial / 500 kg dry mass ledger with 1,000 N thrust and 450 s Isp
- **AND** it SHALL check the declared and effective burn-span floor before mass rounding, preserve the native event representation, and reject stale failed commands, substituted input, incomplete force coverage, unsupported reverse-time semantics, unqualified numerical bounds or unenforceable resource caps; refusal SHALL authorize no physical execution
- **AND** the R5.59 artificial readiness qualification SHALL include no SPICE, kernel access, force evaluation or integration and SHALL verify acceptance and rejection with 15 s through finalization, 2 MiB compact inputs and 128 KiB output per fixture

#### Scenario: Compare independently anchored states and separate numerical uncertainty

- **WHEN** a qualified and separately authorized fixed-command attempt executes
- **THEN** the primary RKDP87 and separately implemented qualified DOP853 paths SHALL each bind the same full model and generate and freeze a reverse receiver from the fixed Mars orbit and ledger mass through t2 to t* before outgoing propagation, preserving the physical-time TNW and mass-rate signs
- **AND** both forward paths SHALL start at the fixed lunar orbit and initial mass, stop at t1, t*, t2 and tf, and continue without resetting the state, model, commands or mass at t*; exact burn interfaces and unreset Mars-relative arrival SHALL be checked separately
- **AND** the incoming-minus-outgoing signed residuals and nonnegative error allowances SHALL be retained, with exact epoch identity and unchanged join ceilings of 1e-6 s, 0.001 m, 1e-6 m/s and 1e-9 kg, and separate target ceilings of 1000 m and 0.01 m/s; each outward-rounded residual interval SHALL pass only with upper edge at or below its ceiling, fail if its lower edge is above it, or stay inconclusive otherwise
- **AND** a missing compatible pair SHALL leave physical residuals null; the two solver paths SHALL support the same verdict or remain inconclusive; missing or unqualified error bounds, solver agreement alone or unresolved safety SHALL NOT certify a match

#### Scenario: Bound the attempt, including failures and final output

- **WHEN** the study limits are qualified and enforced
- **THEN** one fixed pair, two solver paths, at most 12 attempted propagation segments, 1,000,000 attempted RHS calls, 32,000,000 attempted provider state/rotation requests and 64 MiB of evidence SHALL share one 300 s parent deadline including finalization, with 15 s reserved for finalization, explicit before-call accounting and no search, retry or deadline reset
- **AND** before live authorization, instrumentation or conservative charged upper bounds SHALL cover both solvers and all checks; missing accounting or lack of comparable timing and numerical evidence SHALL keep execution unavailable
- **AND** a separate audit SHALL verify first complete or partial evidence within 30 s, at most 64 MiB input and 128 KiB output, with zero SPICE and propagation; a failed gate, deadline, unresolved safety or unaudited result SHALL NOT qualify physical continuity, strict M3 or mission safety

### Requirement: Derive and freeze one fixed command seed

R5.59a SHALL define at most one immutable analytic two-burn proposal
for `d0001-t0035` under ADR0207, without changing ADR0205's physical
readiness, thresholds or authorization.

#### Scenario: Qualify the six-source archive adapter

- **WHEN** the adapter is verified against fabricated forms of the six ADR0207 sources before R5.59c
- **THEN** it SHALL verify each file's fixed name and external hash, aggregate input of at most 512 KiB, cross-file lineage, exact candidate and epoch words, and replay the retained SSB subtraction and R4 bounds without propagation
- **AND** it SHALL retain the original signed excess vectors and historical exclusion words in departure-then-arrival order, reject invalid metadata and deadline violations, and return null commands with no live authorization; artificial pins SHALL NOT be accepted as retained pins

#### Scenario: Qualify the end-to-end offline command invocation

- **WHEN** the complete invocation runs on fabricated archives before the retained attempt
- **THEN** it SHALL exercise both a known proposal and a scientific refusal, admit exactly 512 KiB and refuse 512 KiB plus one byte, and exclude access to sources outside the six explicit pins
- **AND** saved-evidence readback SHALL verify the branch and pair inventory, ranking and both exact mass ledgers without reopening the input archives or solving the conics again; mode mismatch, tampering, incomplete output, an existing destination or a late completion SHALL NOT yield a retained proposal

#### Scenario: Construct local branches at the fixed endpoints

- **WHEN** an offline command generation is separately requested after synthetic qualification
- **THEN** it SHALL verify the six ADR0207 input hashes, exact R1/R4 scenario and candidate equality, body-relative R4 endpoint reconstruction and epoch words; it SHALL use only the two signed R1 excess vectors as asymptote descriptors and SHALL NOT use R5.51 spacecraft states, R5.57 states/differences or failed trial residuals as operands
- **AND** it SHALL enumerate at most two analytic roots at each fixed endpoint, test the physical future outgoing Moon leg and reverse-time Mars leg, reconstruct the signed asymptotes, and require each leg's minimum conic radius to exceed the declared conservative surface by more than 0.001 m; degenerate or unresolved geometry SHALL NOT supply controls
- **AND** the worksheet SHALL project pre-impulse TNW from the lunar parking and Mars incoming states, convert full vector impulse norms to sequential ideal burn durations and require canonical words, exact event ordering and the 500 kg commanded and worksheet-effective dry floor before rounding; a failed input SHALL NOT trigger clipping, phase changes or retries

#### Scenario: Independently verify and freeze at most one proposal

- **WHEN** the two arithmetic paths compare the bounded branch sets
- **THEN** binary64 and independent at-least-80-digit arithmetic SHALL verify the signed excess and impulse vectors at 1e-6 m/s, minimum leg radius at 0.001 m, durations at 1e-6 s and mass at 1e-8 kg; the worksheet SHALL exercise known geometry and rejection cases on synthetic data before using retained inputs
- **AND** each path SHALL examine at most four pairs and exclude previously failed commands; if both paths agree on a unique lowest total vector impulse with a greater-than-4e-6 m/s gap to every alternative, it SHALL seal one proposal containing exact command words, source and boundary hashes, mass ledgers and all branch decisions; zero eligible pairs, ambiguous ranking or failed independent verification SHALL leave commands null
- **AND** one shared 15 s deadline through durable finalization and saved-evidence readback SHALL cap the single generation, with at most 512 KiB input and 128 KiB new output, exclusive artifacts and zero kernel access, SPICE, force evaluation, propagation, fitting, new transfer search or retries

#### Scenario: Keep the analytic proposal separate from physical admission

- **WHEN** the proposal passes its offline checks
- **THEN** it SHALL remain an impulsive surrogate seed without a physical join, Mars closure, safety, reserve or live authorization claim; any live admission SHALL reference its unchanged hash and separately bind the full model and covered resources, qualified reverse/reference solvers and event representation, error bounds, enforceable budgets and explicit separate authorization under ADR0205
- **AND** R5.60 SHALL NOT use the synthetic readiness schema for live evidence, regenerate or adjust the sealed commands, or feed any R5.60 result back into seed selection

### Requirement: Screen a separate Mars capture-phase seed on the fixed reference ellipse

The R5.59d–f research profile SHALL vary only the Mars capture true anomaly as a proposed target boundary change; ADR0205 and the consumed fixed-target R5.59c evidence SHALL retain their scopes.

#### Scenario: Attribute the fixed-target cost from saved evidence

- **WHEN** the R5.59c refusal is analyzed before changing the target phase
- **THEN** the report SHA-256 and receipt chain SHALL bind the retained vectors, whose separately computed norms SHALL sum to the archived pair cost within 1e-9 m/s
- **AND** the diagnosis SHALL distinguish the vector impulse, the collinear speed gap and the ideal dry-mass budget; no new commands or boundary states SHALL be generated during design

#### Scenario: Verify the full artificial workload before retained admission

- **WHEN** the R5.59e runner is qualified with independently pinned artificial archives
- **THEN** it SHALL audit all 360 states and 720 signed root decisions on both a known off-zero-proposal case and a fully empty grid, including reproduction of the zero-phase dry-floor refusal, state/command agreement, exact mass ledgers and selected phase
- **AND** it SHALL accept an aggregate artificial 128 KiB archive, refuse a one-byte excess, bound writes to 4 MiB, reject inconsistent or late evidence, and leave authorization false with zero retained or physical attempts; independently readable output SHALL be bound by exclusive hash-linked receipts

#### Scenario: Qualify and run the isolated phase screen

- **WHEN** independently checked artificial qualification passes and a retained phase screen is separately authorized
- **THEN** both paths SHALL preserve the pinned lunar endpoint/branch, R1 excess vectors, event epochs, Mars orbital shape and orientation, spacecraft, body translation and constants, and SHALL evaluate exactly the 360 uniform true anomalies including zero with at most two signed Mars roots each
- **AND** phase zero SHALL reproduce the archived Mars state and original refusal within the ADR0212 gates; all grid decisions SHALL agree in binary64 and independent at-least-80-digit arithmetic, with the unchanged signed-asymptote, radius, timing, dry-floor, command and ranking gates
- **AND** the run SHALL share one 30 s deadline through exclusive durable output and readback, at most 128 KiB of archive input and 4 MiB new evidence, and SHALL perform zero SPICE access, force evaluation, integration, retries or new interplanetary transfer search

#### Scenario: Bind the retained phase screen to ADR0211 evidence

- **WHEN** the authorized retained screen is dispatched after artificial checks
- **THEN** it SHALL require the exact four ADR0211 file hashes, verify their receipt chain and the frozen scientific operand digest, and write only to its dedicated exclusive evidence directory; fabricated pins or an existing destination SHALL fail before grid evaluation
- **AND** an independent audit SHALL verify the persisted inventory, arithmetic comparisons, root and pair decisions, ranking, time and byte bounds against the completion witness without opening the ADR0211 archive or solving the conics again; partial or late output SHALL NOT qualify as completed evidence

#### Scenario: Verify the saved grid after the exact-zero readback failure

- **WHEN** a separate audit of the three pinned ADR0215 records is authorized
- **THEN** it SHALL verify the original hashes, receipt and frozen operands and apply the original checks for all 360 saved states, 720 root slots, pair decisions, zero-phase replay and analytic disposition
- **AND** only the recorded exact zero `0E-569` in the phase-zero independent velocity X component may be presented as canonical zero in memory; the original files, decimal parser for all other inputs, numerical gates and physical contract SHALL remain unchanged
- **AND** the read-only audit SHALL finish within 30 s, with at most 4 MiB saved evidence input, no ADR0211 reopen, SPICE access, force evaluation, new phase scan, conic solve, propagation or R5.60; no result SHALL create the missing execution completion witness or authorize a physical test

#### Scenario: Report a separate proposal or a bounded refusal

- **WHEN** all decisions are verified and one eligible grid pair is uniquely ranked
- **THEN** the immutable proposal SHALL bind the exact phase word, SI Mars-relative and SSB/J2000 six-states at the original arrival-cutoff epoch, six command words, source identity, branch decisions and both exact mass ledgers
- **AND** a fully checked grid without an eligible pair SHALL report `no-eligible-pair-on-grid` with null commands; ties, incomplete output or disagreement SHALL report an inconclusive or invalid result without commands
- **AND** the proposal SHALL NOT be admitted to the original R5.60; adopting a new Mars boundary and authorizing a later physical test SHALL require a separate reviewed contract with the existing physical readiness gates


### Requirement: Check the continuous neighborhood of the best saved Mars phase

The R5.59g–i profile SHALL conduct a separately authorized, bounded local study of the fixed ADR0217 model without reopening or completing the original R5.59f invocation or changing the physical target.

#### Scenario: Authenticate and bound the local study

- **WHEN** the retained local study is separately authorized after artificial qualification
- **THEN** it SHALL pin the exact ADR0217 audit and three ADR0215 evidence files, verify their receipt and operand identities, and vary only Mars true anomaly in the two closed cells [150°, 151°] and [151°, 152°] at the original cutoff epoch
- **AND** it SHALL check the three saved anchors against the original state, root and pair gates, cover both signed Mars roots, cap the bisection depth at 5, and charge at most 126 cells, 252 signed branch-cell bounds and 129 point evaluations per arithmetic path or verifier, with at most two Mars roots and two pairs per point
- **AND** it SHALL cap the producer, exclusive durable evidence and independent readback at 30 s, allow at most 4 MiB of pinned source per reader and 4 MiB of new evidence, preserve the first attempt and forbid retries, scope expansion, SPICE, force evaluation, trajectory integration or R5.60

#### Scenario: Verify a local existence witness

- **WHEN** the study claims an eligible off-grid phase
- **THEN** a binary64 and independent at-least-80-digit point check SHALL show both costs at or below the unrounded ideal budget and pass all unchanged ADR0212 state, signed-root, impulse, guard, duration, mass, exact event-order, two-ledger and exclusion gates
- **AND** a witness SHALL establish existence only; it SHALL NOT select an executable command pair or establish a unique optimum, physical continuity or R5.60 admission

#### Scenario: Verify a continuous exclusion

- **WHEN** the study claims no eligible pair on [150°, 152°]
- **THEN** an independent verifier SHALL prove gap-free closed interval coverage for both signs and check every exclusion using outward enclosures of an existing geometry gate or a commanded-mass lower bound that includes the independent duration comparison, binary64 rounding and the exact frozen dry-floor ledger
- **AND** unresolved roots or bounds, equality at the mass exclusion boundary, failed authentication, disagreement, missing coverage, incomplete evidence or exhausted budget SHALL give an inconclusive or invalid result; a finer set of samples alone SHALL NOT support a continuous refusal

#### Scenario: Qualify the interval method on artificial data

- **WHEN** the interval procedure is tested before retained execution
- **THEN** artificial evidence SHALL exercise a narrow passing point between failing nodes, a certified two-sign refusal, uncertain root or guard transitions, a mass-bound equality that cannot exclude the branch, a coverage hole, tampering and the full workload and caps
- **AND** focused tests, guarded full pytest, Ruff and strict OpenSpec SHALL pass before the retained study can receive separate authorization


#### Scenario: Qualify the retained archive binding

- **WHEN** the ADR0218 invocation is prepared before any retained execution
- **THEN** it SHALL reject changed hashes, invalid receipt or audit lineage, mixed artificial and retained profiles and mismatched anchor states or signed pair decisions before reporting a verified disposition
- **AND** qualification SHALL use fabricated equivalents of the three ADR0215 files and the ADR0217 audit, exercise the shared time and byte caps and independent saved readback, and leave the retained attempt unspent and the original R5.59f completion witness absent


#### Scenario: Diagnose unresolved enclosures without replay

- **WHEN** a separately authorized local study is preserved as inconclusive and saved-only diagnosis is performed
- **THEN** the diagnosis SHALL authenticate its report, receipt, completion and independent audit, compare recorded exclusion bounds with the unchanged strict thresholds, and distinguish descriptive midpoint samples from a continuous proof
- **AND** it SHALL identify missing intermediate evidence instead of attributing an unrecorded numerical cause; it SHALL NOT recompute retained intervals, conics, phases or an already completed scientific audit
- **AND** a subsequent artificial observational trace SHALL preserve the pinned formulas and gates, reject retained operands and changed outputs, record ordered finite stage endpoints and resource use, and pass traced/untraced parity and failure tests before qualification; no trace SHALL authorize a new retained invocation or change the original inconclusive result


### Requirement: Observe fixed retained phase cells without rescanning

The R5.59l–p profile SHALL observe the unchanged analytical method on a fixed subset of saved cells under ADR0224, without reopening the consumed R5.59i study or claiming a new feasibility proof.

#### Scenario: Freeze the retained observation domain

- **WHEN** a retained observational diagnostic is designed
- **THEN** it SHALL pin ADR0224's nine input artifacts and frozen reference, select saved unresolved depth-5 rows 62, 94 and 125 by index and exact cell/point identities, and fix the three cells plus their saved-midpoint singleton controls before numerical work
- **AND** the fixed matrix SHALL comprise both signs and both existing arithmetic paths, with exactly 24 traces and 24 untraced controls, zero new direct points or point-root constructors outside those bound calls, and no adaptive subdivision or cell replacement
- **AND** all traced results SHALL equal their own controls byte-for-byte, and the six default finite-cell results SHALL additionally equal the authenticated saved bounds; independent and singleton results SHALL NOT be described as historically retained enclosures

#### Scenario: Check retained observations and sampled quantities

- **WHEN** the separately authorized diagnostic and its saved-only verifier run after artificial qualification
- **THEN** a separately qualified retained entry SHALL reject relabeled, mixed or changed operands, preserve historical artificial-entry rejection behavior, pin the unchanged arithmetic sources and record finite canonical stages, exact links and legitimate non-reached stages
- **AND** the three saved midpoint points SHALL provide the matching independent-oracle quantities and designated binary64 duration conversions for all 24 trace records under the unchanged 1 mm / 1 µm/s parity gates; no new point, orbit or point-root construction SHALL supply missing data
- **AND** independent mass arithmetic SHALL be counted and cached: at most 12 oracle-mass calls in the producer including internal readback, and at most six in the separate auditor; the auditor SHALL perform zero new bounds, traces or conic solves and SHALL NOT rerun the old scientific audit
- **AND** exact component/scalar widths and singleton differences SHALL carry units; unlike dimensions SHALL NOT be ranked as causal contributions, and the result SHALL NOT imply a tighter proof, continuous refusal, physical error bound, command admission or mission feasibility

#### Scenario: Qualify and bound the new diagnostic before retained execution

- **WHEN** the retained-observation adapter is prepared or its execution is considered
- **THEN** R5.59m SHALL qualify the complete new matrix and full-volume fabricated archives, identity and historical-parity rejection, canonical zero/singleton containment, early/non-reached stages, mutations, exclusive completion cleanup, scope separation and every exhausted limit using focused and guarded full pytest, Ruff and strict OpenSpec; preparation SHALL NOT evaluate retained operands
- **AND** the producer and separate auditor SHALL each have 30 s through durable finalization, with at most 48 producer bounds, 8,192 total stage entries, 4 MiB authenticated source inventory per process and 4 MiB combined new evidence including a reserved 64 KiB audit allowance
- **AND** R5.59n SHALL require a separate explicit execution instruction after qualification, preserve the first complete or partial result without retry, and fail invalid or inconclusive on disagreement, missing evidence or exhausted caps; no new formula, broader/deeper tree, SPICE, force evaluation, integration or R5.60 SHALL follow automatically


### Requirement: Admit hash-pinned historical JSON encodings without rewriting evidence

The archive adapter SHALL preserve immutable input bytes and scientific gates while admitting the exact historical JSON serialization documented by ADR0226. Compatibility repair SHALL NOT retry the consumed retained dispatch.

#### Scenario: Authenticate the original bytes before decoding

- **WHEN** the versioned compatibility adapter loads any of the nine archival roles
- **THEN** it SHALL enforce the original raw SHA256, source-byte cap, role and lineage/row identities before any bound or mass evaluation
- **AND** it SHALL retain compact sorted and two-space-indented sorted JSON with one final newline, admitting sorted single-line default-spaced JSON with one final newline additionally for `study_audit` only; unapproved whitespace, duplicate keys at any depth, malformed JSON, non-object roots and nonfinite numeric values SHALL be rejected
- **AND** a semantically equivalent reserialization with a changed raw digest SHALL fail the original source pin rather than being normalized on disk or silently repinned

#### Scenario: Qualify the repaired adapter without a new retained experiment

- **WHEN** this compatibility repair is qualified
- **THEN** artificial archives SHALL exercise all nine observed encoding profiles with valid rechained identities, the full fixed 24-trace/24-control matrix and separate saved-only audit, while the historical adapter SHALL continue rejecting the default-spaced fixture
- **AND** new evidence SHALL remain compact canonical JSON, historical adapter/math/contract/evidence bytes SHALL remain unchanged, and every inherited scope, time, source/evidence-byte and work limit SHALL remain in force
- **AND** a read-only preflight on the fixed historical files MAY verify hashes, parsing and post-loop metadata/row identities only, with zero bounds, traces, point/conic constructors, oracle mass, SPICE, integration or old scientific audit; a new retained numerical dispatch SHALL require a separate explicit instruction


#### Scenario: Execute the corrected version under a distinct instruction

- **WHEN** the user separately instructs one retained diagnostic after R5.59o qualification
- **THEN** R5.59p SHALL record that distinct authorization and measured adapter/base identity before its single corrected-version dispatch, preserve the consumed ADR0226 failure, and keep inherited artifact labels/paths without rewriting their provenance
- **AND** the first completed or partial output SHALL be preserved without retry; at most one separate saved-only audit SHALL verify a completed result under the unchanged ADR0224 matrix, numerical gates and all time/work/source/evidence caps
- **AND** successful observations SHALL remain descriptive with attribution unresolved unless independently established; no formula change, new direct point, old scientific replay, SPICE, integration or R5.60 SHALL be implied


### Requirement: Diagnose widening through saved lineage and controlled local comparisons

The R5.59q–s profile SHALL distinguish saved dataflow, conditional local implementation effects and unresolved causal attribution using only ADR0229's pinned archive/source inventory. The design SHALL NOT authorize a new calculation or scientific replay.

#### Scenario: Authenticate and reconstruct saved lineage

- **WHEN** the saved-lineage reader is qualified and separately instructed to inspect the retained archive
- **THEN** it SHALL authenticate all13 contract files, prior completion/audit chain, the fixed24 rows and1248 saved events, and source/method identities before analysing endpoints; all older results and inherited labels SHALL remain immutable
- **AND** it SHALL match stages by semantic parent path and same-stage direct-child ordinal, verify the frozen source-alias links exactly, and record JSON/source references with explicit units rather than treat equal numbers or call IDs as proof of common origin
- **AND** the18 checkpoint fields per trace SHALL support only descriptive exact widths and same-observable cell/singleton comparisons; undefined zero-denominator ratios and legitimate non-reached clearance SHALL remain explicit, while missing required reached fields SHALL invalidate the readback

#### Scenario: Isolate a conditional local norm response

- **WHEN** the reader compares the default and independent records in one of the36 frozen candidate norm-pair slots
- **THEN** it SHALL require the same row/domain/sign/semantic role, identical endpoints for all three saved operands, and the pinned interval implementation with unchanged Decimal96 contexts and sole local square-versus-dot/clamp branch difference, explicitly labeling context equality as a conditional source/provenance assumption rather than a saved runtime observation
- **AND** differing operands SHALL yield input-confounded, identical eligible results no-local-difference-observed, and differing eligible results conditional-local-method-response; ambiguity or a changed source/context SHALL invalidate the comparison, while legitimate earlier exit SHALL be not-reached
- **AND** it SHALL perform zero new norm or interval evaluations, preserve the contract's role-specific dimensions, and SHALL NOT attribute a local response to final arrival-width contribution or a dominant cause

#### Scenario: Preserve causal limits and independently verify the descriptors

- **WHEN** a diagnosis or its separate saved-only verifier produces a claim
- **THEN** it SHALL separate observed lineage/widths, conditional local effects, source-supported dependency risks and information absent from the archive; cell-minus-singleton width SHALL NOT become an overestimation/roundoff bound, and distinct rounded radius expressions SHALL NOT be treated as identical without a separate proof
- **AND** the overall successful status SHALL be lineage-qualified-attribution-unresolved, with explicit inconclusive/invalid/exhausted outcomes; no causal percentage, contracted bound, continuous refusal, eligible command or mission qualification SHALL follow
- **AND** the new independent verifier SHALL check descriptors from pinned raw endpoints without calling the old scientific audit, importing scientific modules or sharing the producer's analysis routine

#### Scenario: Qualify and bound the saved readback before execution

- **WHEN** preparation or execution is considered
- **THEN** R5.59r SHALL require a separate instruction and qualify fabricated full24-row/36-slot archives at the pinned source byte volume, confounding/alias/role/unit/zero/non-reached/tampering cases, independent verification, exclusive output and every cap using focused/guarded full pytest, Ruff and strict OpenSpec; no retained numerical analysis SHALL occur during preparation
- **AND** artificial qualification SHALL use a separate scope with distinct fabricated data/reference/completion pins and output roots, the same immutable source/role map/caps and declared fixture event counts; the retained entry SHALL build its fixed profile internally and reject injected, rehashed, mixed or relabeled qualification inputs
- **AND** each future reader/verifier SHALL have30 s through durable finalization and4 MiB source inventory including the contract and private source files, with1 MiB combined output/64 KiB verifier reserve,8192 input events,32768 event visits/process,1024 descriptors,768 alias links,36 pair slots and bounded numeric parsing under ADR0229
- **AND** R5.59s SHALL require qualified preparation and a separate explicit execution instruction, retain at most one readback and one verifier's first complete/partial evidence without retry, and record zero new bounds/traces/points/roots/norms/mass/native/SPICE/kernel/force/integration/R5.60 calls


### Requirement: Preserve command-shape parity in the versioned saved-reader dispatcher

The R5.59t repair SHALL preserve historical0230 and the consumed ADR0231 failure while qualifying the exact retained/audit command shapes with artificial dependencies only under unchanged ADR0229 scientific rules and limits.

#### Scenario: Admit the exact retained and audit worker forms

- **WHEN** the qualified dispatcher expands retained or audit commands into an isolated worker
- **THEN** a retained worker SHALL admit its four argv items (worker, start, invocation, retained), and an audit worker SHALL admit its five items including the completion pin; the existing CLI SHALL reject truncated, unknown and extra-argument forms without archive access
- **AND** the repair SHALL change only the minimum worker prefix and versioned private self-source identity, not add dummy arguments, weaken profile authentication or expose a production retained-profile override

#### Scenario: Qualify real command shapes with fabricated dependencies

- **WHEN** the dispatcher repair is qualified
- **THEN** a test-only isolated bootstrap SHALL exercise the complete parent/child retained and audit argument forms using explicit content-pinned fabricated archives and isolated outputs, without changing the command argument lists or substituting authentication, guards, analyzer or independent verifier
- **AND** full24-row/1248-event/36-slot analysis and separate verification, malformed arities, existing artificial aliases, exclusivity and inherited clocks/work/input/output limits SHALL pass focused and frozen guarded full pytest, Ruff and strict OpenSpec; complete charged inventory SHALL include bootstrap/configuration source bytes
- **AND** no historical numerical payload, consumed R5.59s dispatch, SPICE, integration, old scientific audit or R5.60 SHALL run; fixed retained outputs and all original evidence/source bytes SHALL remain untouched, with a separate execution decision required for any future retained readback


### Requirement: Record a distinct saved-only readback after qualified dispatch repair

A newly authorized R5.59u readback SHALL use the qualified unchanged0232 dispatcher and unchanged ADR0229 contract, preserving the historical consumed R5.59s failure and all scientific limits.

#### Scenario: Execute the separately authorized retained and audit pair

- **WHEN** a separate explicit user instruction authorizes saved-data readback after R5.59t qualification
- **THEN** exactly one unmodified0232 retained command and, only after successful durable completion, one independent audit command bound to the raw new completion SHA256 SHALL run under the same pinned Conda/isolation/profile/input/source rules and caps; first complete or partial evidence SHALL be preserved without retry
- **AND** the stage record SHALL identify the new authorization separately from historical R5.59s, preserve inherited raw artifact labels, and verify zero new scientific/native/SPICE/kernel/force/integration/old-audit-replay/R5.60 calls

#### Scenario: Verify saved dispositions without a causal overclaim

- **WHEN** the first readback and independent audit complete
- **THEN** the record SHALL verify13 raw pins,24 rows/1248 event visits/648 descriptors/528 aliases/all36 candidate norm dispositions, exact evidence identities and byte/time/work limits, and retain independently verified same-operand, confounded or legitimate non-reached outcomes without changing gates
- **AND** input-confounded outcomes SHALL not establish a local method response, final-width contribution, dominant cause, continuous exclusion, physical join or strict M3 completion; scientific context assumptions and missing causal information SHALL remain explicit


### Requirement: Compare source-defined norm-squared methods on identical saved boxes

The ADR0234 controlled local experiment SHALL isolate the two norm-squared formulas on fixed identical inputs under explicit fresh contexts; R5.59v SHALL remain design only, with separately instructed R5.59w artificial qualification and R5.59x saved execution.

#### Scenario: Freeze a balanced identical-input matrix

- **WHEN** the future local experiment selects inputs from the original authenticated traces
- **THEN** it SHALL retain both saved origins for each of36 fixed row/domain/sign/semantic-role slots, producing exactly72 provenance-preserving vector boxes and144 method evaluations/process, with identical six endpoint strings/hash/units supplied to both methods for every box
- **AND** selectors SHALL bind original call/return structural paths, direct-child ordinal and mode flags; no data-dependent selection, deduplication, hull, reboxing, input quantization, new phase or changed historical operand SHALL be admitted
- **AND** source-defined sum-of-squares and clipped sum-of-self-products SHALL preserve scalar operation grouping, absolute-value rounding and raw/post-clip endpoints, using isolated pinned primitives rather than importing historical modules with mathematical initialization

#### Scenario: Control contexts and require finite saved-call compatibility

- **WHEN** each future method evaluates its fixed input box
- **THEN** it SHALL use and record fresh identical ADR0234 context settings, cleared initial flags and exact string construction, rejecting context drift or unexpected flags rather than inferring a historical runtime snapshot
- **AND** all72 own-origin outputs already included in144 evaluations SHALL exactly match their saved original method returns; any mismatch SHALL retain first evidence with overall inconclusive/compatibility-mismatch, without context tuning, retry or selective causal admission

#### Scenario: Verify independent references and scoped local outcomes

- **WHEN** the new local arithmetic and separate auditor are qualified or explicitly executed
- **THEN** each process SHALL count144 method evaluations plus72 exact-real Cartesian-box oracle evaluations separately; independently implemented integer/rational directed-rounding replay SHALL exactly verify each new method endpoint, and both final enclosures SHALL contain the exact-real box range with zero tolerance
- **AND** the record SHALL retain exact per-box widths, endpoint/excess gaps, inclusion classification, the fixed product-minus-square width difference/product-over-square ratio with explicit zero-denominator status and role-specific squared units; endpoint parity SHALL use exact rational numeric equality while raw signed/scaled zero strings and flags remain diagnostic provenance, without a representation/flag-history recovery claim; it SHALL distinguish a real-box oracle from a rounded historical program and make no downstream speed, final-width contribution, dominant-cause, exclusion, physical-join or strict M3 claim
- **AND** complete source/work/time/output/parse/bit limits in ADR0234 SHALL be precharged/enforced and first evidence finalized exclusively; source inventory SHALL include all original13 files, both contracts, every private source and artificial bootstrap/config, without loading the unnecessary large lineage report or replaying old auditors

#### Scenario: Separate design, artificial preparation and saved execution

- **WHEN** only the current R5.59v design instruction is authorized
- **THEN** only source/AST and metadata/document verification SHALL occur, with zero numerical endpoint extraction, method/oracle evaluations, experimental outputs, SPICE, integration or R5.60
- **AND** R5.59w SHALL require a separate instruction and full-volume artificial qualification including exact retained/audit command shapes, arithmetic/context/compatibility/limit failures, independent review, focused/frozen guarded full pytest, Ruff and strict OpenSpec; limits SHALL not be treated as sufficient until measured
- **AND** only qualified R5.59w and another explicit instruction SHALL permit one R5.59x saved local experiment and one independent audit, without retry or historical/production code changes; its new local norm/oracle work SHALL be nonzero and separately counted while orbital/trig/sqrt/exp/mass/native/SPICE/integration/R5.60 work remains zero

#### Scenario: Admit selected source bindings within sealed historical metadata

- **WHEN** the separately authorized ADR0237/R5.59y versioned adapter and independent auditor qualify on artificial archives
- **THEN** each SHALL independently require exactly6 authenticated source roles and match every selected hash within a well-formed sealed metadata map of the closed6-role or17-role form, rejecting missing/mismatched selected roles, reduced contexts, malformed/unknown/partial extras or scope drift before numerical work
- **AND** the additional11 entries SHALL remain sealed metadata, without claiming their source files were newly authenticated; all original raw/source/AST/private pins and numerical formulas/contexts/caps SHALL remain unchanged
- **AND** full-volume artificial17/6 and legacy6/6 inputs SHALL pass the complete72-box/144-method/72-oracle/72-diagonal comparison and independent audit, with exact parent/worker shapes, caps and exclusive evidence verified; old0234 failure/0235 sources SHALL remain immutable and new0237 fixed outputs absent
- **AND** R5.59x SHALL remain consumed and unchecked; any future saved execution SHALL need a distinct explicit instruction/new output identity, with no SPICE, integration, R5.60 or physical/M3 claim from artificial repair


#### Scenario: Execute the separately authorized versioned saved comparison

- **WHEN** ADR0237/R5.59y is qualified and a new explicit instruction authorizes R5.59z on the fixed 72 saved input boxes
- **THEN** exactly one unchanged 0237 producer and, only after its successful durable completion, one independent audit bound to that raw completion SHALL execute under the original ADR0234 numerical, context, input, work, byte and time limits, using the distinct 0237 fixed output namespace and preserving the consumed unchecked R5.59x failure
- **AND** all 72 own-origin compatibility checks, 144 method evaluations, 72 exact-real box oracles and 72 paired comparisons SHALL be verified; a mismatch SHALL remain inconclusive with first evidence preserved and no tuning, retry or selection
- **AND** final evidence SHALL distinguish the finite same-box local outcome from incoming interval width, correlated-domain range, final arrival-width contribution, general formula equivalence or physical/M3 admission; local norm/oracle work SHALL be counted separately while all prohibited SPICE/kernel/native/force/integration/old-audit/R5.60 counters remain zero

### Requirement: Stop diagnostics at one terminal feasibility decision

The next scientific work objective after ADR0238 SHALL be one terminal analytical
feasibility decision under ADR0239, preserving all existing scientific gates.
This requirement SHALL NOT authorize a new numerical method or execution.

#### Scenario: Select a complete result instead of another diagnostic branch

- **WHEN** follow-up scientific work is proposed after R5.59z
- **THEN** it SHALL target an independently verified witness or a gap-free two-sign refusal on the unchanged ADR0218 closed [150 degrees, 152 degrees] domain, or return inconclusive/invalid and stop
- **AND** a single reviewed method contract SHALL specify a justified different complete method, exact pins, independent verifier and counted artificial qualification within the existing ADR0218 work/time/byte ceilings before implementation or retained evaluation; this planning stage SHALL perform zero new research numerical evaluations
- **AND** equal local enclosures or passing tests SHALL NOT authorize another norm trace, deeper/wider search, consumed-study replay, changed tolerance or automatic diagnostic successor

#### Scenario: Preserve the limit of each feasibility conclusion

- **WHEN** the future complete deliverable reports a witness, refusal or incomplete proof
- **THEN** a witness SHALL pass every original point and exact commanded/effective mass-ledger gate; a refusal SHALL cover every point and both signed roots of the declared closed domain; missing evidence, disagreement or exhausted caps SHALL remain inconclusive/invalid
- **AND** a witness SHALL NOT be an executable command selection or global optimum, and local refusal SHALL NOT become a whole-orbit or physical-infeasibility claim
- **AND** every terminal result SHALL stop automatic continuation; existing unresolved evidence SHALL NOT be rerun merely to restate its status

#### Scenario: Keep analytical existence separate from the physical mission

- **WHEN** an analytical witness uses a different Mars phase
- **THEN** its changed target six-state SHALL require separate boundary and immutable-command selection review before any physical proposal; it SHALL NOT enter the original R5.60
- **AND** all ADR0205/0207 resource, full-model reverse/reference, endpoint-error, event/mass, enforceable-budget and separate-execution gates SHALL remain required; automation SHALL remain PAUSED and strict M3 SHALL remain open


### Requirement: Use bounded scalar search only to propose an analytical witness

The next local method SHALL use ADR0240 bounded Brent as a point proposer under
ADR0239, with all original independent command-admission gates unchanged.

#### Scenario: Propose off-grid points within the fixed analytical family

- **WHEN** a separately implemented and qualified proposer is explicitly authorized
- **THEN** it SHALL verify anchors 150°, 151°, 152° and use pinned SciPy 1.17.1 `minimize_scalar(method="bounded", bounds=(150.0, 152.0))`, with degree `xatol=1e-5`, `maxiter=62`, `disp=0`, separately for positive then negative Mars signs and the fixed positive lunar branch
- **AND** all three anchors SHALL match authenticated saved states, root and pair refusals before search; the frozen comparator SHALL require no eligible anchor, and a new witness contradicting its saved refusal SHALL be invalid; artificial endpoint-witness checks SHALL exercise only the isolated point verifier
- **AND** its objective SHALL be the finite total analytical impulse in m/s for the active sign, including mass-rejected pairs; every proposed phase SHALL inspect both signed point checks first and may stop at any independently passing witness regardless of optimizer status
- **AND** a definitively guard-rejected or agreed-degenerate active branch SHALL end only that sign's scalar search without penalties, nonfinite objectives, subdivision or restart; missing signed inventory, unresolved arithmetic, anchor mismatch or independent disagreement SHALL terminate invalid/inconclusive

#### Scenario: Admit literal commands at the exact proposed phase

- **WHEN** a future candidate is checked for analytical admissibility
- **THEN** a new versioned adapter SHALL retain its binary64 phase hex word and exact degree ratio without grid snapping, and its six original command words with phase/sign/endpoint binding
- **AND** the pinned independent orbit/conic path SHALL verify all ADR0218 state, asymptote, impulse, incoming-leg guard, arrival reversal, TNW, event, historical exclusion, duration/mass, unrounded ideal-budget and both exact commanded/effective 500 kg ledger gates, without replacing commands by newly rounded oracle values
- **AND** unresolved classification of either signed root SHALL prevent admission; a different Mars phase SHALL remain a changed analytical target, with no executable pair, original R5.60 admission or physical/M3 claim

#### Scenario: Bound actual work and audit the saved points independently

- **WHEN** the method is artificially qualified or later explicitly executed
- **THEN** all attempts including duplicates/errors SHALL be precharged within 3 anchors, 62 callbacks per sign and 2 final checks of already-recorded completed-search results: at most 129 direct phases, 258 Mars root slots and 258 pair slots per arithmetic path, with zero interval cells/bounds
- **AND** the separate auditor SHALL independently check only recorded phases and literal commands under its own same caps, without optimizer replay; producer readback SHALL be structural/hash-only without uncounted phase work
- **AND** the original four archive pins SHALL remain fixed, and new source/runtime identities SHALL be frozen after qualification; the producer SHALL declare its pinned SciPy/NumPy runtime instead of weakening the historical stdlib-only guard or claiming zero native-library loads
- **AND** all archive/private/scientific/bootstrap/config/profile and selected solver/wrapper-source authentication reads including rereads SHALL count toward the 4 MiB input ceiling; only preinstalled interpreter/NumPy/SciPy import artifacts SHALL be a runtime exception under an exact qualified path/build/digest allowlist and frozen measured volume, with no general scan or omitted load/authentication time
- **AND** startup/imports through durable producer finalization/readback SHALL fit 30 s, with a separate 30 s audit, 4 MiB pinned input per reader and 4 MiB combined new evidence; SPICE/kernel/force/integration/old-study/R5.60 work SHALL remain zero and first partial/complete evidence exclusive

#### Scenario: Preserve the outcome limit and separate design from execution

- **WHEN** the bounded scalar method ends
- **THEN** it SHALL report only an independently verified analytical witness or inconclusive/invalid; no witness, optimizer success or a reported above-budget minimum SHALL certify continuous refusal or global optimality
- **AND** automatic continuation SHALL stop after either result; a required refusal proof SHALL need a separate reviewed method decision
- **AND** this design stage SHALL perform zero scientific imports, numerical evaluations or experiments; implementation SHALL require a separate instruction and ADR0240 full-volume artificial qualification with both required regression lanes, while saved execution SHALL require another explicit instruction and qualified identities; automation SHALL remain PAUSED


#### Scenario: Deliver artificial preparation without implying forbidden regression or execution

- **WHEN** the P3 instruction authorizes artificial preparation while forbidding saved real-data execution, SPICE and integration
- **THEN** ADR0241 private commands SHALL expose only artificial/profile/audit routes, reject retained or repository-evidence paths before opening, and qualify exact phase/word gates, independent traces and 129-phase limits using fabricated records only
- **AND** a labelled maximum-volume driver SHALL exercise both signed branches and all 129 direct phases on an explicitly artificial fixture, without claiming it is a Brent result, changing real mission inputs or weakening gates
- **AND** runtime profiles SHALL authenticate the explicit interpreter/NumPy/SciPy/native artifact inventory before import and count all source/configuration/rereads, startup/finalization and evidence against unchanged caps; opaque OS shared-cache contents SHALL remain explicitly outside content-hash claims
- **AND** prohibited live/CI execution SHALL not occur or be labelled passing; the required live lane SHALL remain unverified and full P3/retained readiness SHALL stay unavailable, even after the requested artificial and portable checks pass


#### Scenario: Finish regression qualification after explicit SPICE authorization

- **WHEN** the user separately authorizes existing live SPICE regression and CI, while prohibiting a new P3 search on saved real inputs
- **THEN** qualification SHALL require both frozen required regression lanes, unchanged scientific/source identity checks, independent repair review, Ruff and strict OpenSpec; a failed CI run or skipped lane SHALL remain failed or unverified until repaired-current-source evidence passes
- **AND** exact current-process loader metadata normalization and injected artificial test clocks MAY be repaired without widening permissions, changing historical scientific sources, budgets, tolerances, command/mass gates or immutable evidence
- **AND** old no-SPICE qualification evidence SHALL remain historical; new source/profile identities and regression outcomes SHALL be retained separately, distinguishing archive/platform skips from passes
- **AND** successful P3 qualification SHALL authorize no retained binding/search, real witness/refusal, adopted target, physical join, R5.60, M3 closure or automation continuation


#### Scenario: Design one retained attempt without executing it

- **WHEN** the user authorizes ADR0243/P4 planning after P3 qualification while forbidding execution, SPICE and integration
- **THEN** only source/AST, existing metadata, raw hash/size and documentation checks SHALL occur; saved numerical operand extraction/evaluation, scientific imports, new profiles/experimental outputs and retained dispatch SHALL remain zero
- **AND** the completed 0241 artificial invocation, qualified numerical helpers, historical evidence and scientific gates SHALL remain byte-for-byte unchanged; a minimal versioned retained binding SHALL require separate implementation/qualification and later explicit execution authority

#### Scenario: Seal the one-shot scientific and runtime binding

- **WHEN** a future retained P3 adapter is qualified under ADR0243
- **THEN** it SHALL independently require exactly the original 0215 attempt/report/receipt and 0217 audit roles/raw hashes fixed in ADR0243 and 0220 PINS, preserving historical encoding/exact-zero view, lineage/upstream metadata, reference digest, candidate d0001-t0035, original epoch words, fixed positive lunar branch and every other physical operand
- **AND** only Mars anomaly on [150°,152°] SHALL vary under unchanged ADR0240 settings and all point/literal-command/mass gates; no extra scientific archive, endpoint queries, old 360-point numerical replay, source canonicalization or upstream producer/audit execution SHALL be permitted
- **AND** because the 0241 point adapter admits only artificial scope/candidate, a versioned adapter SHALL change only that identity gate, preserving every other validation/numerical/oracle/literal-command operation and the original source; restricted source/AST difference, both point/audit paths and scope/candidate cross-pair rejection SHALL be verified on fabricated inputs
- **AND** new retained dispatcher/point/configuration/source identities SHALL be frozen only after artificial qualification, using the repaired 0242 helper bindings and exact qualified local producer/auditor runtime tables/read caps; artificial-bootstrap identity, opaque shared-cache coverage and native loading SHALL NOT be relabelled or overstated, and any drift SHALL leave execution unavailable

#### Scenario: Consume one bounded retained attempt and audit complete outcomes

- **WHEN** P5 is fully qualified and a separate explicit instruction authorizes P6
- **THEN** one fixed no-argument retained route SHALL atomically reserve only `docs/adr/experiments/0243-p3-retained/` before dispatch, and launch at most one isolated producer plus one separate stdlib independent auditor, with no caller-selected input/profile/phase/output override, overwrite, retry or resume; namespace existence or dispatched failure SHALL consume the whole attempt
- **AND** work SHALL be precharged within the inherited 129-phase/258-root/258-pair caps per arithmetic path, 30 s startup/authentication/finalization-inclusive producer and separate 30 s auditor, 4 MiB charged source/inputs including rereads and producer-evidence reads per reader, exact frozen runtime read caps, zero interval cells/bounds and 4 MiB total new evidence
- **AND** that evidence SHALL include a launcher record <=4096 B and separate canonical four-record producer/auditor chains, with <=64 KiB reserved for audit and producer limited to the remaining (4 MiB - 4096 B - 64 KiB); full-volume artificial verification SHALL demonstrate these allocations before real dispatch without raising caps
- **AND** a complete authenticated producer chain with witness or complete inconclusive exit status SHALL receive the one raw-completion-hash-bound independent audit of every recorded phase, both signed slots, original command words, ledgers, anchors and trace/work/stopping identity, with zero optimizer calls or unrecorded probes; partial/unauthenticated chains SHALL remain failed/consumed without numerical audit
- **AND** only an independently agreed durably complete witness SHALL conclude analytical existence; an audited no-witness transcript SHALL remain inconclusive, and drift/timeout/partial evidence/cap failure SHALL remain invalid/unverified, never continuous refusal, optimality, adopted target, executable pair, R5.60, physical/M3 closure or safety
- **AND** all SPICE/kernel/force/integration/old-study/R5.60 work SHALL remain zero while actual numerical/native runtime work SHALL be counted; every terminal result SHALL stop, with automation PAUSED and no automatic successor


#### Scenario: Continue independent preparation without inventing a success percentage

- **WHEN** the user authorizes autonomous research but requests a percentage whose metric is unresolved and requires automation to stop on needed questions
- **THEN** the existing heartbeat SHALL stay PAUSED while that user decision is pending, without invented normalization, weaker tolerances, test-pass/confidence equivalence or a guaranteed-convergence claim; independent authorized P5 preparation MAY proceed in the current chat
- **AND** ADR0244's versioned point adapter SHALL accept only the correlated fixed artificial/retained scope-candidate identities while preserving every other validation/numerical/oracle/literal-command operation; source/AST checks and both point/audit paths SHALL be verified on fabricated operands with parity and cross-pair rejection
- **AND** passing this isolated unit SHALL NOT complete P5 or permit P6, real witness/refusal, adopted target, physical closure or statistical success; the source/runtime/lineage binding and full retained dispatcher qualification SHALL remain required
- **AND** the 2026-11-24 standing instruction MAY supply conditional execution authority for the single unchanged ADR0243 P6 after full P5 qualification and an agreed objective, without another permission request; it SHALL NOT permit changed scientific contracts, unqualified dispatch or retries
- **AND** autonomous scheduling after an agreed goal SHALL preserve the one-shot scientific contract, document/test/commit/push each verified stage and set automation `ariadna-m3` to PAUSED on success, required user input or a terminal scientific-contract failure, without automatic retries
