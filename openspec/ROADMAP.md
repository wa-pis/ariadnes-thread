# Ariadna Space Navigation Roadmap

## Current priority — end-to-end demonstration (2026-09-16)

Deliver one understandable Moon-to-Mars planning example before extending the
numerical-certification investigation. The user approved this planning direction;
it neither declares a trajectory feasible nor weakens existing scientific gates.
Automation is paused. Do not resume it without an explicit user request.

Start with [current state](../CURRENT_STATE.md). Preserve previous results in the
[historical roadmap](../docs/roadmap-history-2026-09-16.md), the
[decision journal](../docs/adr/README.md), and existing tests.

## Near-term sequence

User-approved research D4 now takes priority: one explicit fixed-seed candidate,
three arcs plus a tighter repeat, at most six native launches and one shared
scenario deadline. Implement active tasks D4.1–D4.5. Report endpoint miss and
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

D4 scope is approved in the active research-experiment specification. Complete
its contracts and manufactured checks before its single bounded native experiment.
Any further scope expansion needs a revised contract; strict M3 gates remain open.

### Next bounded research step

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
Next: one D12.3 study. No automatic subsequent experiment.
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
| M3 — `refine-physical-trajectory` | Open; research D4 prioritized | Accepted physical-refinement requirements and end-to-end checks pass. Task 3.9 remains unresolved; component tests are not mission validation. |
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
- Derive reusable scenario/state/maneuver/result contracts from working examples.
  Exporters, interchangeable backends and ML datasets remain future work.
- This is a ground engineering prototype, not onboard software, an adopted
  industry standard or flight-qualified navigation.
