# Ariadna Space Navigation Roadmap

## Current priority — R1 mission-first demonstration (2026-10-29)

The user approved [ADR 0117](../docs/adr/0117-mission-first-demonstration-priority.md):
deliver one reproducible research demonstrator with an independently checked
calculation and exportable result before adding more private optimizer complexity.
Keep the long-term platform vision and existing Python/TudatPy/SPICE/Streamlit.
Explicitly select the demo's fidelity; an ideal M2 result is not a finite-burn
mission solution. No automatic D18, second D17 study or automation restart.

Start with [current state](../CURRENT_STATE.md). Preserve previous results in the
[historical roadmap](../docs/roadmap-history-2026-09-16.md), the
[decision journal](../docs/adr/README.md), and existing tests.

| Gate | Status | Required result / verification |
|---|---|---|
| R1.0 — Record the priority reset | Planning complete | ADR, measurable OpenSpec requirements and consistent current context; strict validation, links and immutable checks. No new implementation or native work. |
| R1.1 — Problem and positive reference | Verified ideal M2 only, ADR 0119 | Two identical 1980-attempt searches/two 121-state samplings in shared 1.993807459 s; d0001-t0035, final 887.966464 kg >=550 kg. Decimal mass/reserve, endpoints and provenance checks pass; no finite-burn claim. |
| R1.2 — Small independent physical benchmark | Passed, ADR 0122 | One 17-call study in 0.555804s; maximum 0.00159834m/3.66733e-10m/s, conservation/root/identity and offline checks pass. Synthetic coast component, not full-transfer/finite-burn validation. |
| R1.3 — Minimal result and OEM profile | Research readiness verified, ADR 0124 | Corrected source hash, approved unregistered ARIADNA exception, actual INPOP19a/ICRF mapping; private independent decoder/fixtures pass 88 native-free tests. Not full CCSDS conformity or writer acceptance. |
| R1.4 — One usable path | Verified research delivery, ADR0125 | Input → calculation → display → verified JSON/OEM; all121 nodes within1microsecond/1mm/1e-9m/s wire gates, explicit50kg reserve, 151 focused and4766 full tests/630.19s, Ruff/strict validation/immutable checks. |

The accepted sequence has one ideal positive reference, a passed synthetic coast
benchmark and a narrow research OEM implementation (ADR0125). Early independent
checking is a small research benchmark, not M6 full-mission GMAT/Monte Carlo
verification. Strict M3/task 3.9 remain open
and unchanged; R1 completion cannot archive M3 or start M4–M6. No old target,
fuel model, scientific gate or retained artifact is weakened to make a demo pass.
The sole active change remains `refine-physical-trajectory`.

[ADR 0118](../docs/adr/0118-m2-reference-and-historical-data-readiness.md)
also records the MSL/GRAIL metadata audit. Historical residuals would measure
empirical model discrepancy, not replace the same-force R1.2 oracle. No arc,
historical native run or change to the mission-first order is implied. The separate
[R1.1 result](../docs/adr/0119-positive-ideal-m2-reference.md) does not close R1.2.

## Current priority R2 — verify the actual reference coast (selected2026-10-31)

The user selected [ADR0126](../docs/adr/0126-propose-reference-coast-verification.md)'s
reference-coast verification. [ADR0127](../docs/adr/0127-reference-coast-verification-contract.md)
freezes the preparation contract: original121 nodes, independent Cartesian
initial phase, exact Sun/SSB/TDB alignment, 1m/1e-6m/s numerical gates, relative
invariants<=1e-12, at most121 Sun reads/shared30s and zero native spacecraft
propagations. Eight offline initial algebra checks pass; actual reference coverage,
domain membership and numerical accuracy remain unverified.
R2.1 contract is accepted for preparation; [ADR0128](../docs/adr/0128-reference-coast-verifier-ready.md)
records R2.2's private independent runner, separate offline audit and86 new/225
combined native-free tests. No actual-reference Sun query/comparison has run.
Next: separately instructed R2.3 single comparison and audit, under the same gates.
No new force model/optimizer or automation; R1 and all strict M3 gates are unchanged.

## Retained research history — not the current schedule

The work packages below preserve completed evidence and earlier scope. They do
not override R1 or authorize another native run; their original scientific gates
and measured outcomes remain in force.

D14.2 implements the [local finite-burn contract](../docs/adr/0105-local-finite-burn-contract.md):
[ADR 0106](../docs/adr/0106-local-finite-burn-implementation.md) records 182 focused /
4,112 full tests passing (598.94 s), Ruff, strict OpenSpec and immutable hashes.
D14.3 completed at `53229c3`: [ADR 0107](../docs/adr/0107-local-burn-misses-analytic-target.md)
retains four arcs / 3.849491 s. Frozen profiles agree (position difference
3.038e-6 m), but target closure fails by 5520.40 km and 780.53 m/s.
Independent evidence checks and 116 focused tests pass; full suite reused.
D15.2 implements the [bounded local steering design](../docs/adr/0108-bounded-local-steering-targeting.md):
[ADR 0109](../docs/adr/0109-local-steering-targeting-implementation.md) records
119 new / 301 focused / 4,231 full tests passing (602.73 s), Ruff, strict OpenSpec,
links and immutable hashes. Six controls, fixed target state/epoch, at most four
corrections / 66 evaluations / 132 arcs / 300 seconds; D14 behavior is preserved.
D15.3 completed once at `f4aed8f`:
[ADR 0110](../docs/adr/0110-local-steering-improves-without-closure.md) retains
53 evaluations / 106 completed arcs / 7.939209 s and four accepted alpha=1 steps.
Errors decrease to 3868.62 km / 556.75 m/s, but closure fails; no tighter repeat.
Independent evidence audit and 119 focused tests pass; full suite reused from
unchanged D15.2. Stop for a separate scope review, not another automatic study.
Measured local rank six is not proven global controllability/convergence,
hardware qualification, a production optimizer or Mars feasibility; strict M3 stays open.

D16.1 is specified in [ADR 0111](../docs/adr/0111-bound-aware-local-targeting.md):
all four unconstrained commands violate ignition/duration bounds; uniform caps
are not constrained least-squares steps. Independent offline 729-face/KKT checks
confirm better linear box directions, not nonlinear closure. D16.2 is verified in
[ADR 0112](../docs/adr/0112-bound-aware-targeting-implementation.md): a
separate private bound-aware TRF path with explicit Conda SciPy 1.17.1 pin,
same six controls/fuel/target/epoch/profiles and in-domain second-order probes.
Separate ceiling: 280 nominal / 281 total evaluations, 562 native launches,
300 seconds; all probes counted. 98 new / 366 focused / 4,330 full tests pass
(604.70 s); Ruff, strict OpenSpec, links, dependency/source/immutable checks pass.
D14/D15 and historical evidence are preserved. D16.3 subsequently ran once at
`501516e`: [ADR 0113](../docs/adr/0113-bound-aware-targeting-hits-budget.md) retains
262 nominal evaluations / 524 completed arcs / 38.927206 s, with exact seed replay.
The independent 20-Jacobian cap stops the study as budget-exhausted; best eligible
objective errors are 59.203835 km / 246.398570 m/s, not closure. Duration reaches
the reserve-derived bound; no tighter repeat, returned solver status or proof of
infeasibility. Best objective 262 is not the last recorded accepted iterate 249.
Audit/verification status is recorded in ADR 0113. Stop for separate scope review;
no automatic repeat, budget increase, new node, automation restart or strict M3 completion.

D17.1 diagnosis/design is recorded in
[ADR 0114](../docs/adr/0114-quadratic-steering-freedom.md). At the last measured
ID 249 the fuel-bound five-free-control and full-box linear minima nearly equal
the retained score; this is not a nonlinear impossibility bound. Next is a
separate smooth quadratic-Bezier steering chart, adding two shape controls with
unchanged target/time/fuel/thrust/forces. Explicit accepted interior ID 158 and
two fresh replay gates preserve the old chart without hidden seed adjustment.
New bounded contract: 6x8 Jacobian / sixteen probes, 40 objective requests and
40 batches, 681 nominal / 682 total evaluations / 1364 arcs / 300 seconds.
D17.2 is implemented/verified in
[ADR 0115](../docs/adr/0115-bezier-targeting-implementation.md): 258 new / 607
focused / 4,588 full tests pass (626.08 s); source/resource/immutable and strict
checks pass, with D14/D15/D16 and dependencies unchanged. D17.3 subsequently ran
exactly once at clean `3434a31`, retained in
[ADR 0116](../docs/adr/0116-quadratic-steering-stagnates-at-bounds.md): exact dual
replay, 503 nominal evaluations / 1006 completed arcs / 76.614638 s. Returned
SciPy status 2 (`ftol`), not budget exhaustion; best/accepted/final objective and
last measured Jacobian parent are ID 487, unclosed at 44.386790 km /
185.850963 m/s. Duration reaches the reserve ceiling; near-bound middle slope,
full/free rank six and lower score do not prove stationarity or infeasibility.
No selected objective or tighter repeat. Independent offline evidence/physical
audits and 607 fresh focused tests pass (7.17 s); full suite reused from unchanged
D17.2. Strict/static/provenance checks pass. Stop for separate scope review
before more native work; no automatic retry, changed seed/target/fuel/budget,
API/UI change, research/automation restart or strict M3 completion.

Historical user-approved D4 scope used one explicit fixed-seed candidate,
three arcs plus a tighter repeat, at most six native launches and one shared
scenario deadline. Tasks D4.1–D4.5 and their results are retained below. Report endpoint miss and
numerical agreement separately; never claim continuous safety or M3 completion.
The strict M3 enclosure prerequisite is waived only for this isolated research
experiment, not for production refinement. Optimizer and UI integration follow
only after a separate evidence-based scope decision.
These are work packages, not additional OpenSpec changes. The sole active change
remains `refine-physical-trajectory`; its accepted requirements remain in force
until explicitly revised. This planning edit changes no implementation checkbox.

| Step | Status | Completion evidence |
|---|---|---|
| D1 — Audit the existing demonstration | Complete 2026-09-22 | Existing path inspected at `f132d8a`; 14 explorer/UI tests pass. See [audit](../docs/demo-audit.md) for available outputs, provenance gap and limitations. |
| D2 — Agree the smallest missing slice | Specified 2026-09-23 | Active proposal/design/tasks and visual-explorer delta specify the read-only provenance panel, edited-input binding, failure lifecycle and regression checks. No scientific gate or runtime limit changes. Strict validation required before implementation. |
| D3 — Deliver one reproducible demonstration | Complete 2026-09-23 | Existing M2 explorer plus calculation-bound provenance panel. 29 focused checks and 3,502 full-suite tests pass; scientific limitations and reference mass shortfall remain visible. This does not qualify finite burns or complete M3. |
| D4 — Research-only fixed-seed experiment | Research complete; numerical qualification failed | Authorized replay completed six arcs in 22.11 s with exactly matching science/provenance. Agreement still fails (1751.29 m); target miss remains. See [Decision 0081](../docs/adr/0081-research-reproducibility.md). No continuous-safety or strict-M3 completion claim. |
| D5 — Identical-start coast diagnosis | Diagnostic complete; position agreement failed | Two arcs in 7.62 s; zero nominal restart drift, same-input separation 115.67 m exceeds 10 m. 3,631 tests pass. See [Decision 0082](../docs/adr/0082-identical-start-coast.md). No accuracy or strict-M3 qualification. |
| D6 — Maximum-step sensitivity | Diagnostic complete; no convergence claim | Three arcs in 30.63 s, exact baseline replay, changed saved meshes; pair differences 0.47–1.97 m pass diagnostic thresholds but adjacent differences increase. 3,655 tests pass. See [Decision 0083](../docs/adr/0083-coast-step-study.md). Production settings and strict M3 remain unchanged. |
| D7 — One target-correction attempt | Experiment complete; correction did not improve | [Decision 0086](../docs/adr/0086-targeting-step-does-not-improve.md): 24 arcs in 19.11 s, exact baseline replay; position miss 197.85M to 245.01M km, score ratio 1.23837. No tighter run, retry or mission qualification. 49 focused / 3,704 full tests pass. Next scope decision required before another experiment. |

Explorer usability follow-up delivered 2026-09-23: elapsed-day control, visible
budget/grid, Pareto priorities, ideal-fuel filter, Russian help and explicit
unscreened-object warning. 33 focused checks and 3,506 full-suite tests pass;
Ruff, strict OpenSpec and legacy checksum pass. No physical gates changed.

D4 scope/results are retained in the active research-experiment specification;
its contracts and manufactured checks preceded its single bounded experiment.
Any further scope expansion needs a revised contract; strict M3 gates remain open.

### Earlier bounded research sequence

D8.2 completed one live study: [ADR 0088](../docs/adr/0088-damping-does-not-improve.md).
Nine arcs completed in 10.51 s; alpha=0.5/0.25 increased scores by 5.01%/1.49%.
Neither trial was selected; no tighter run. [ADR 0089](../docs/adr/0089-local-response-diagnosis.md)
checks signs/order and shows local prediction disagreement, large cancellation
and extrapolation beyond probe sizes. D9.1 is specified in [ADR 0090](../docs/adr/0090-local-response-study-contract.md):
alpha=+/-2^-14 and +/-2^-15, each paired nominal/tighter, at most five controls,
ten evaluations and thirty arcs under 300 s. Twelve response consistency checks
use an explicit exploratory 0.10 threshold. D9.2 is implemented and verified in
[ADR 0091](../docs/adr/0091-local-response-implementation.md): 346 focused / 3,784
full tests pass (598.42 s), Ruff/strict OpenSpec/legacy pass. D9.3 completed at
`1db4706`: [ADR 0092](../docs/adr/0092-local-response-disagrees-with-jacobian.md)
retains thirty arcs / 95.75 s, exact baseline replays and eight of twelve passing
checks. All four model checks fail (0.303–0.312 versus <=0.10); scale/profile and
curvature checks pass. No command selected or mission qualification. 45 focused
tests and independent hashes/controls/residuals/arithmetic checks pass; D9.2 full
suite reused. D10 contract: [ADR 0093](../docs/adr/0093-central-column-study-proposal.md)
specifies six central columns at original D7 increments, nominal only, thirteen
evaluations / 39 arcs under 300 s. Compare their prediction with the two retained
D9 nominal slopes; no new solve or selection. The user approved the scope on
2026-10-04. D10.2 is verified in
[ADR 0094](../docs/adr/0094-central-column-implementation.md): 246 focused / 3,856
full tests pass (578.59 s), Ruff/strict OpenSpec/legacy pass. D10.3 completed at
`812ebeb`: [ADR 0095](../docs/adr/0095-central-columns-match-local-response.md)
retains 39 arcs / 27.93 s, exact baseline/positive replays and two passing central
response discrepancies (0.00573/0.01358 versus <=0.10). No solve or selection;
individual columns and strict M3 remain unqualified. 72 D10 checks and independent
evidence verification pass; D10.2 full suite reused. D11.1 is specified in
[ADR 0096](../docs/adr/0096-single-central-correction-contract.md): one baseline,
one central-matrix capped solve/trial, conditional frozen tighter repeat,
two controls / three evaluations / nine arcs under 300 s. D11.2 is verified in
[ADR 0097](../docs/adr/0097-central-correction-implementation.md): 236 focused /
3,896 full tests pass (596.41 s), Ruff/strict OpenSpec/legacy pass. D11.3 at local
`b6d4513`: [ADR 0098](../docs/adr/0098-central-correction-does-not-improve.md)
retains six arcs / 5.59 s, exact baseline replays, score ratio 1.23457 despite
linear prediction 0.99154; no selection/tighter. Code/evidence pushed as
`b6d4513` / `00a5802` after explicit user approval. D12 is approved in
[ADR 0099](../docs/adr/0099-central-direction-damping-contract.md): half/quarter
of the retained central step, first improvement gets one frozen tighter repeat,
3 controls / 4 evaluations / 12 arcs / 300 s. D12.2 verified in
[ADR 0100](../docs/adr/0100-central-damping-implementation.md): 287 focused /
3,947 full tests pass (609.93 s), Ruff/strict OpenSpec/legacy pass.
D12.3 at `08a2ce4`: [ADR 0101](../docs/adr/0101-central-fractions-do-not-improve.md)
retains nine arcs / 7.87 s, exact replays, score ratios 1.05056/1.01401;
neither fraction improves, no selection/tighter. Independent evidence checks and
51 D12 tests pass; full suite reused from D12.2. Stop automatic research and
review the targeting approach before agreeing further scope.
The user requested a consistent lunar-departure design on 2026-10-16:
[ADR 0102](../docs/adr/0102-consistent-lunar-departure-design.md) and D13 tasks
specify pure local hyperbolic geometry, explicit fixed/free parking phase,
vector impulse and recomputed mass with independent invariants. Synthetic
algebra passes; reference phases are approximately 2.81/246.11 degrees, not
verified finite-burn solutions. D13.2 verified in
[ADR 0103](../docs/adr/0103-lunar-departure-geometry-implementation.md): 436 focused /
3,996 full tests pass (598.51 s), Ruff/strict OpenSpec/legacy pass.
D13.3 report at `34a1541` is retained in
[ADR 0104](../docs/adr/0104-lunar-reference-has-two-geometric-branches.md): fixed
phase zero fails; free phases 2.81/246.11 degrees require 2.861/4.446 km/s.
Second branch fails the provisional mass budget; neither is selected. Independent
geometry/mass/provenance checks and 49 D13 tests pass; zero native arcs, D13.2 full
suite reused. The subsequent finite-burn timing/guidance, comparison-radius
matching and native-run budget are specified in ADR 0105 and implemented in
ADR 0106; D14.3 subsequently completed in ADR 0107, recorded above. D13 itself made no branch selection.
No extra fractions, probes, repeated solves,
automatic retries or production optimizer expansion.
The completed D8 contract was to replay the baseline, then test the
retained D7 direction at alpha=0.5 and, only if needed, 0.25. Stop at the first
improvement and validate it once with tighter settings. One shared 300 s budget,
at most 3 control attempts / 4 evaluations / 12 arcs. No new probes or solve,
no retry after failure and no change to strict M3 gates. Active D8 tasks govern
implementation and the single subsequent experiment (D8.2). [Decision 0087](../docs/adr/0087-retained-direction-damping.md):
301 focused / 3,739 full tests pass (806.13 s); Ruff, strict OpenSpec and legacy checks pass.

## Engineering milestones

| Milestone | Status | Exit criterion |
|---|---|---|
| M1 — `establish-navigation-foundation` | Archived 2026-09-04 | Reproducible environment, scenarios, SI/time/frame contract and SPICE diagnostics. |
| M2 — `plan-impulsive-transfer` | Archived 2026-09-04 | Bounded 3D impulsive search and time/fuel Pareto front. |
| Visual transfer explorer | Archived 2026-09-07 | Delivered Streamlit prototype with explicitly labelled simplified model. |
| M3 — `refine-physical-trajectory` | Open; R1 readiness/demonstration prioritized | Original physical-refinement requirements and end-to-end checks must pass. Task 3.9 remains unresolved; R1, component tests and exchange compatibility are not M3/mission validation. |
| M4 — `estimate-navigation-state` | Deferred until M3 archival | Ground-station observations, batch estimation and state covariance. |
| M5 — `schedule-course-corrections` | Deferred until M4 archival | Zero to three corrections using only observations available at maneuver time. |
| M6 — `verify-and-report-mission` | Deferred until M5 archival | Monte Carlo reporting and independent GMAT comparison under agreed criteria. |

Keep at most one active change. Never archive an incomplete milestone to bypass
its gates. Review future detailed numerical targets before specification.

## Research and extensions

Search-budget extension delivered 2026-09-23: ceiling 10000, default 2000,
unchanged deadline behavior. UI.7 records real-run and 3,507-test verification.
This increases search density, not the fidelity of the physical model.

- [Optional object analysis draft](deferred/optional-object-analysis/spec.md):
  independent opt-in display, additional gravity and post-calculation encounter
  screening, each with explicit coverage, status and provenance. Requirements
  are recorded; provider choices and numerical gates remain open. No active
  change or current scientific acceptance gate is replaced by this draft.
- Deferred: catalogue-based close-approach screening for asteroids, comets and
  artificial debris, separate from gravitational perturbation modelling. Before
  implementation, agree object selection, data sources/versions and coverage,
  reference/time conventions, position uncertainty and encounter thresholds.
  Define missing/stale-data behavior and measurable validation cases; lack of
  coverage must not be reported as clearance. Catalogue screening cannot certify
  absence of unknown objects. No new milestone/change or implementation is
  authorized here; current UI work only discloses that screening was not done.
- Pause rigorous full-force error-bound work until a demonstrated need and bounded
  research question justify it. Preserve code, tests and evidence; no separate
  Git branch is created by this planning change.
- Keep task-specific convergence checks, independent oracles and regressions.
  Nominal/tighter agreement is empirical evidence, not a rigorous error bound.
- Derive minimal reusable results from the working example through R1.3/R1.4;
  the accepted research profile and frozen reader bound the R1.4 implementation.
  Interchangeable backend frameworks and ML datasets remain future work.
- This is a ground engineering prototype, not onboard software, an adopted
  industry standard or flight-qualified navigation.
