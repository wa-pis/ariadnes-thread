# Architecture Decision Records (ADRs)

Record consequential choices, not every command. OpenSpec remains authoritative
for requirements, milestone order and acceptance gates; these records explain why.
Use English, stable numbered filenames and links to evidence rather than copied logs.

## ADR workflow

This is the canonical ADR directory, migrated from `docs/decisions` on 2026-09-28.
Keep one shared numbering sequence; do not create a parallel decision journal.
An ADR explains a consequential architectural choice: module boundaries,
interfaces, dependencies, data contracts or scientific architecture. Experiments
remain evidence records, not automatically architectural decisions. Routine fixes,
status updates and every individual run do not require an ADR.

1. Search the journal for the affected topic and read relevant decisions before
   changing code. Follow supersession links; do not assume the newest numbered
   experiment supersedes an architectural choice.
2. Copy [the ADR template](ADR_TEMPLATE.md) to the next unused `NNNN-short-title.md`
   in the shared sequence. Record context, actual alternatives and reasons before
   or alongside implementation. Do not reconstruct unknown historical motives.
3. Use decision status `proposed`, `accepted`, `rejected` or `superseded`.
   Track implementation and verification separately. Acceptance does not mean
   the code exists, a hypothesis is proven or a mission is qualified.
4. Link the relevant OpenSpec requirement/change and evidence. OpenSpec defines
   what must hold; ADRs explain why a design was selected. A conflicting ADR must
   not silently relax an acceptance gate or enable deferred work.
5. Commit the record with the relevant change and add an entry below. When a
   choice changes, create a new record with `Supersedes`, then mark the earlier
   one `superseded` with `Superseded by`. Preserve its original rationale/results.

Historical records 0001–0086 retain their original structures and status wording:
they include scientific experiments, not just architectural choices. Paths in
Markdown now reference this directory; retained JSON and experiment scripts are
unchanged. Paths embedded in immutable evidence describe the original run.
Record 0087 and new ADRs use the template's explicit sections. Do not fabricate
missing alternatives or retroactively mark historical experiments accepted.
The list below is a curated entry point,
not a complete catalogue. Find all records with `rg --files docs/adr` and
search topics with `rg -n 'TOPIC' docs/adr --glob '*.md'`.

## Record structure

- Date, milestone, status (proposed, accepted, rejected or superseded), and scope.
- Question and constraints.
- Evidence: measured revision and dirty-state caveats, environment/resource
  identifiers, procedure, results with units, and links to artifacts. State missing
  provenance instead of inventing it. Preserve failures alongside successes.
- Interpretation: distinguish empirical observations, hypotheses and mathematical
  claims with their assumptions. State what the evidence does not establish.
- Decision and alternatives, with reasons.
- Next checks and measurable acceptance criteria; implementation status is separate
  from acceptance of a decision.

Commit a record with its evidence as a small `docs:` commit when appropriate.
Check facts, relative links, JSON syntax and the staged scope. A failed experiment
is legitimate evidence, not a passing implementation gate. Do not bundle unfinished
code merely to save the record. Code completion still requires the project checks.

Link the measured base revision in each record. Git history identifies the commit
introducing the record (`git log --follow -- docs/adr/FILE.md`); a record need
not contain its own future commit hash. For a changed decision, add a new record
linking the old one and mark the old one superseded; do not erase earlier outcomes.

## Records

- [0144 — Independent saved-node arithmetic](0144-independent-saved-node-arithmetic.md):52 new/89 focused and5184 full pass; arithmetic unit verified, file/provenance orchestration still required before R5.

- [0143 — Independent saved-evidence audit contract](0143-independent-saved-evidence-audit-contract.md): independent arithmetic/raw-data/provenance and zero-native10s design verified; implementation pending, no R5 run.

- [0142 — Short-coast orchestration and evidence](0142-short-coast-orchestration-and-evidence.md):37 injected runner tests/81 focused and5132 full pass; orchestration unit verified, offline audit remains required before R5.

- [0141 — R5 frozen inputs and extended runtime identity](0141-short-coast-input-and-runtime-identity.md):44 new/130 focused and5095 full tests pass; input/identity unit verified, runner/audit pending; no R5 run.

- [0140 — Native short-coast adapter preparation](0140-native-short-coast-adapter.md):61 new/115 focused and5051 full tests pass; native unit verified, shared runner/audit pending; no R5 reference run.

- [0139 — Pinned native API readiness](0139-pinned-native-api-readiness.md): explicit constructors/GMs checked without propagation; opaque inventory and failed standalone derivative documented; native parity pending.

- [0138 — Independent short-coast oracle preparation](0138-independent-short-coast-oracle.md):54 new/224 focused and4990 full tests pass; oracle unit verified, R5.2 overall pending remaining adapters.

- [0137 — Short-coast Earth-gravity contract](0137-short-coast-earth-gravity-contract.md): fixed300s/two direct point-mass models, independent Tudat/SciPy profiles and60s/four-arc/four-oracle limits; preparation pending.

- [0136 — Retained boundary arithmetic passes](0136-retained-boundaries-pass-arithmetic.md): both fixed endpoints pass binary64 and80/100-digit Decimal checks, zero native calls; no connecting trajectory claim.

- [0135 — Fixed orbital boundaries and burn interfaces](0135-fixed-orbit-boundary-contract.md): retained task endpoints, exact full-model arc joins and a10s/zero-native independent boundary-arithmetic audit contract; no mission run.

- [0134 — Reuse boundary evidence](0134-boundary-evidence-reuse.md): exact parsed R1/D13 inputs match; retain phase/event/GM/model distinctions, no local-state splice or repeated geometry.

- [0133 — Three-epoch gravity screening](0133-three-epoch-gravity-screening.md): one bounded native study and independent arithmetic audit pass; local Earth departure term is40.2% of solar acceleration, endpoint lunar/Mars fields remain inadmissible.

- [0132 — Gravity-screening preparation](0132-gravity-screening-preparation.md):84 new/170 focused/4936 full tests pass; private binary64/Decimal diagnostic and offline audit, no native R3 study yet.

- [0131 — Screen omitted gravity at fixed epochs](0131-screen-omitted-gravity-at-fixed-epochs.md): body-centre endpoint domain audit and bounded three-epoch differential-force contract; preparation/execution pending.

- [0130 — Full regression after reference verification](0130-full-regression-after-reference-verification.md):4852 tests pass at7b22253; integrated regression only, no new physical-fidelity claim.

- [0129 — Reference-coast verification passes](0129-reference-coast-verification-passes.md): all121 actual reference nodes and independent offline audit pass; ideal coast only, strict M3 remains open.

- [0128 — Reference-coast verifier ready](0128-reference-coast-verifier-ready.md): R2.2 private runner/audit and native-free tests; actual-reference comparison not launched.

- [0127 — Reference-coast verification contract](0127-reference-coast-verification-contract.md): R2 detailed contract accepted for preparation; no native study.
- [0126 — Proposed actual-reference coast verification](0126-propose-reference-coast-verification.md): user-selected R2 priority; detailed contract and implementation tracked separately.
- [0125 — Research export and usable path](0125-research-export-and-usable-path.md): R1.4 implementation; verification recorded in the ADR.
- [0124 — Reader and research profile ready](0124-oem-reader-and-research-profile-ready.md) — R1.3 research readiness: corrected source hash, approved unregistered-originator exception, actual INPOP19a/ICRF admission and independent stdlib reader with 88 native-free tests. No writer/UI or full CCSDS conformity; R1.4 next.
- [0123 — Traceable result and OEM profile](0123-traceable-result-and-oem-profile.md) — superseded draft, original limitations retained. Correction/originator and reader readiness subsequently resolved at explicit research scope in 0124; no exporter or conformance claim.
- [0122 — Independent elliptic coast passes](0122-independent-elliptic-coast-passes.md) — R1.2 passes: 17 pairs in 0.555804 s; max 0.00159834 m / 3.66733e-10 m/s, offline arithmetic/provenance audit passes. Coast component only, no full-transfer/finite-burn/M3 claim.
- [0121 — Elliptic benchmark preparation](0121-elliptic-benchmark-preparation.md) — R1.2b private independent oracle/evidence script verified with 51 native-free tests, closed-form self-checks and fail-stop/provenance/exclusive-output guards. Preparation-stage evidence only; subsequent execution retained in 0122.
- [0120 — Independent elliptic coast benchmark](0120-independent-elliptic-coast-benchmark.md) — accepted R1.2 contract: synthetic inclined e=0.2 Sun-point-mass ellipse, independent standard-library Kepler bisection, 17 epochs/one period, 1 m/1e-6 m/s gates, at most17 adapter calls/shared30s. Preparation in 0121; subsequent execution in 0122; no mass/finite-burn/M3 claim.
- [0119 — Positive ideal M2 reference](0119-positive-ideal-m2-reference.md) — R1.1 passes: two identical 1980-candidate searches/two 121-state samplings in 1.993807 s; deterministic d0001-t0035, final 887.966464 kg, 337.966464 kg above dry + 50 kg reserve. Decimal/endpoint/provenance/offline checks pass. Ideal M2 only; R1.2 and strict M3 remain open.
- [0118 — M2 reference and historical data readiness](0118-m2-reference-and-historical-data-readiness.md) — accepted explicit M2 contract with 50 kg reserve/100 m/s ideal contingency; executed separately in 0119. Original planning/source audit did not run native calculations; MSL/GRAIL metadata is not a same-force oracle.
- [0117 — Mission-first demonstration priority](0117-mission-first-demonstration-priority.md) — user-approved R1 planning reset: explicit problem/positive reference with reserve, small independent benchmark, then a traceable UI/OEM path. Detailed fixture/profile and implementation remain open; no D18/rerun, stack rewrite, M3 waiver or automation restart.
- [0116 — Quadratic steering improves without closure](0116-quadratic-steering-stagnates-at-bounds.md) — D17.3: exactly one study at clean `3434a31`, 503 evaluations / 1006 arcs / 76.61 s; returned `ftol`, best 44.39 km / 185.85 m/s, duration at reserve limit. Independent audits pass; no tighter/retry or stationarity claim. Scope review required, strict M3 open.
- [0115 — Bezier targeting implementation](0115-bezier-targeting-implementation.md) — D17.2 complete: private eight-control chart, dual replay gates, 6x8 correction/diagnostics and independent limits; 258 new / 607 focused / 4,588 full tests pass (626.08 s). No dependency change; subsequent retained study in 0116, strict M3 open.
- [0114 — Smooth additional steering freedom](0114-quadratic-steering-freedom.md) — D17.1: active-duration saved linear response nearly exhausted; independent face/projection/KKT oracles, not nonlinear infeasibility. Design eight-control quadratic Bezier, explicit interior ID-158/two replay gates, same fuel/target, 682 evaluations / 1364 arcs / 300 s. Implementation in 0115; subsequent native study in 0116.
- [0113 — Bound-aware targeting hits its budget](0113-bound-aware-targeting-hits-budget.md) — D16.3: one study, 262 evaluations / 524 arcs / 38.93 s; 20-Jacobian cap, best errors 59.20 km / 246.40 m/s. Duration at reserve limit, no closure/tighter/solver return; scope review required, strict M3 open.
- [0112 — Bound-aware targeting implementation](0112-bound-aware-targeting-implementation.md) — D16.2: 98 new / 366 focused / 4,330 full tests pass (604.70 s); separate TRF/stencil/budget path reuses unchanged D14/D15 physics. SciPy pinned, historical evidence preserved; subsequent D16.3 in 0113, strict M3 open.
- [0111 — Bound-aware local targeting](0111-bound-aware-local-targeting.md) — D16.1: diagnose timing/fuel bounds and uniform caps; independent offline box-fit oracles pass. Design a separate SciPy TRF path from ID 52 with unchanged physics/target and 281 evaluations / 562 arcs / 300 s. Implementation verified in 0112; subsequent bounded study in 0113, strict M3 open.
- [0110 — Local steering improves without closure](0110-local-steering-improves-without-closure.md) — D15.3: 53 evaluations / 106 arcs / 7.94 s, four accepted steps; errors 3868.62 km / 556.75 m/s, not-converged. Independent audit passes; no tighter/retry, strict M3 open.
- [0109 — Local steering targeting implementation](0109-local-steering-targeting-implementation.md) — D15.2 complete: 119 new / 301 focused / 4,231 full tests pass (602.73 s); D14 preserved, D15.3 subsequently retained in 0110, strict M3 open.
- [0108 — Bounded local steering targeting](0108-bounded-local-steering-targeting.md) — D15 design: ignition/duration plus two-node direction, fixed state/epoch, four corrections and 66 evaluations / 132 arcs / 300 seconds; implementation verified in 0109, non-converged reference study in 0110.
- [0107 — Local burn misses analytic target](0107-local-burn-misses-analytic-target.md) — D14.3 complete: four arcs / 3.85 s, nominal/tighter agreement passes; closure fails by 5520.40 km / 780.53 m/s. No tuning or mission qualification.
- [0106 — Local finite-burn implementation](0106-local-finite-burn-implementation.md) — D14.2: 182 focused / 4,112 full tests pass; private coupled native propagation, fixed local profiles and fail-stop evidence; reference experiment pending.
- [0105 — Local finite-burn contract](0105-local-finite-burn-contract.md) — D14 design: explicit first branch, centered inertial burn, fixed analytic local target, four launches / 300 seconds; implementation verified in 0106, reference experiment pending.
- [0104 — Two local departure branches](0104-lunar-reference-has-two-geometric-branches.md) — D13.3: fixed phase fails; free phases 2.81/246.11 degrees, impulses 2.861/4.446 km/s; second branch fails provisional mass budget. Zero native arcs, no selection.
- [0103 — Lunar departure geometry implementation](0103-lunar-departure-geometry-implementation.md) — D13.2: 436 focused / 3,996 full tests pass; no propagation or automatic selection.
- [0102 — Consistent lunar departure design](0102-consistent-lunar-departure-design.md) — D13: explicit phase, outgoing hyperbola/vector impulse and mass; pure geometry first, finite-burn/native contract deferred.
- [0101 — Central fractions do not improve](0101-central-fractions-do-not-improve.md) — D12.3: nine arcs / 7.87 s; scores +5.06%/+1.40%, no selection/tighter; stop automatic research sequence.
- [0100 — Central damping implementation](0100-central-damping-implementation.md) — D12.2: 287 focused / 3,947 full tests pass.
- [0099 — Central-direction damping contract](0099-central-direction-damping-contract.md) — D12 approved: retained half/quarter steps, conditional tighter, 3/4/12 budget.
- [0098 — Central correction does not improve](0098-central-correction-does-not-improve.md) — D11.3: six arcs / 5.59 s; measured score +23.46%, no tighter run or selection; strict M3 open.
- [0097 — Central correction implementation](0097-central-correction-implementation.md) — D11.2 verified: 236 focused / 3,896 full tests.
- [0096 — One central-matrix correction contract](0096-single-central-correction-contract.md) — D11 specified: baseline, one capped solve/trial, conditional tighter repeat, 2/3/9 budget.
- [0095 — Central columns match local response](0095-central-columns-match-local-response.md) — D10.3 complete: 39 arcs / 27.93 s; discrepancies 0.00573/0.01358 pass <=0.10, no solve/selection or mission qualification.
- [0094 — Central-column implementation](0094-central-column-implementation.md) — D10.2 verified: 246 focused / 3,856 full tests; no live D10 study yet.
- [0093 — Central-column study contract](0093-central-column-study-proposal.md) — approved 2026-10-04; thirteen nominal evaluations / 39 arcs, no solve or selection; implementation verified separately.
- [0092 — Local response disagreement](0092-local-response-disagrees-with-jacobian.md) — D9.3 complete: 30 arcs / 95.75 s; eight of twelve checks pass, all four model checks fail; no selection or M3 qualification.
- [0091 — Local response implementation](0091-local-response-implementation.md) — D9.2 verified; one D9.3 live study remains.
- [0090 — Local response study contract](0090-local-response-study-contract.md) — D9 specified; implementation and experiment pending.
- [0089 — Local response diagnosis](0089-local-response-diagnosis.md) — linear prediction disagrees with retained propagation; bounded derivative study recommended.
- [0088 — Damping does not improve](0088-damping-does-not-improve.md) — completed D8 study; neither fraction selected.
- [0087 — Retained-step damping](0087-retained-direction-damping.md) — current ADR; implementation verified, live study pending.

### Historical decision and evidence records

- [0001 — Investigate the inventory deadline before optimization](0001-inventory-runtime-investigation.md)
- [0002 — Exact harmonic input duplication is observed](0002-exact-harmonic-input-duplicate.md)
- [0003 — Reuse exact harmonic errors within one inventory](0003-local-harmonic-reuse.md)
- [0004 — Count the harmonic tail once in the midpoint norm](0004-separate-harmonic-tail.md)
- [0005 — Fresh-handoff full-force evidence ledger](0005-fresh-full-force-ledger.md)
- [0006 — Expose signed point-gravity intervals](0006-point-gravity-intervals.md)
- [0007 — Bind six point forces to the fresh handoff](0007-fresh-point-gravity-binding.md)
- [0008 — Audit source-position allowance coverage](0008-source-allowance-coverage.md)
