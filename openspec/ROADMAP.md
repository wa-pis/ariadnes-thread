# Ariadna Space Navigation Roadmap

## Current priority — end-to-end demonstration (2026-09-16)

Deliver one understandable Moon-to-Mars planning example before extending the
numerical-certification investigation. The user approved this planning direction;
it neither declares a trajectory feasible nor weakens existing scientific gates.
Automation is paused. Do not resume it without an explicit user request.

Start with [current state](../CURRENT_STATE.md). Preserve previous results in the
[historical roadmap](../docs/roadmap-history-2026-09-16.md), the
[decision journal](../docs/decisions/README.md), and existing tests.

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
| D4 — Research-only fixed-seed experiment | In progress; scope approved | Active tasks D4.1–D4.5: separate report, bounded three-arc composition and tighter repeat, explicit residuals and comparison. No continuous-safety or strict-M3 completion claim. |

Explorer usability follow-up delivered 2026-09-23: elapsed-day control, visible
budget/grid, Pareto priorities, ideal-fuel filter, Russian help and explicit
unscreened-object warning. 33 focused checks and 3,506 full-suite tests pass;
Ruff, strict OpenSpec and legacy checksum pass. No physical gates changed.

D4 scope is approved in the active research-experiment specification. Complete
its contracts and manufactured checks before its single bounded native experiment.
Any further scope expansion needs a revised contract; strict M3 gates remain open.

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
