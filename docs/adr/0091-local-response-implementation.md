# 0091 — Reuse targeting preparation for local response diagnostics

Date: 2026-10-04
Decision status: accepted (D9.2 implementation approach).
Implementation: complete and verified; live D9.3 study pending.
Scope: M3 research D9.2, no live D9 experiment.
Base revision: `8f199b5` plus this implementation and tests.
Related OpenSpec: [D9 tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [0090](0090-local-response-study-contract.md).

## Context and constraints

D9 requires five independent seed-based commands, each evaluated with nominal
then frozen tighter settings. Preparation, identity checks, three-arc dynamics
and guard handling already exist in the private targeting driver. The new
experiment must preserve D7/D8 behavior and their independent caps.

## Options considered

- Duplicate preparation and dynamics in a separate driver: rejected because
  resource binding, guards and failure lifecycle would diverge unnecessarily.
- Add an opt-in mode with separate arithmetic and budget: selected; reuse the
  existing composer and reference validation, without an optimizer framework.

## Decision and rationale

Add mutually exclusive `--response-reference` alongside `--damping-reference`.
D9 imports the pinned 0086 direction/Jacobian and historical source identity;
current source hashes are recorded independently. Check a finite nonzero
directional prediction before preparing native environments or perturbations.

The D9 budget enforces five controls, ten evaluations and thirty arcs with one
cooperative 300-second clock. Every nominal command counts before analytic
validation; its frozen tighter repeat adds an evaluation, not a new control.
Completed arc handoff, ordered pairs and fresh environments are required.
Verify both retained nominal baselines and 0079's tighter baseline before any
perturbation. Their cross-profile disagreement remains a reported observation.

Use a small standard-library arithmetic module for the specified signed
predictions, central slopes, curvature, scale and profile differences. Validate
finite inputs/results, reject zero directional norm and retain unavailable ratio
reasons instead of nonfinite JSON. Twelve <=0.10 checks determine diagnostic
consistency only. Residual coordinates in this arithmetic are dimensionless,
using the existing position 1000 m and velocity 0.01 m/s scaling.

No score decrease or already-closed baseline selects a command or skips the
requested response study. Failed propagation retains previous completed runs,
an explicit unavailable summary reason and no partial endpoint. JSON output
remains exclusive. No new library, force model or public navigation API is added.

## Consequences and revisit conditions

The implementation is ready for testing separately from its one D9.3 live study.
Only measured response evidence can support further targeting choices. These
checks do not establish derivative error bounds, absolute accuracy, safety or
strict M3 completion. Additional scales or native runs need the next scoped
decision after D9.3; the automation remains paused.

## Evidence and verification

346 focused tests pass in 11.92 s, including D4-D8 and native adapter regressions.
New tests use independently specified linear/quadratic/cubic responses and
control-column/unit oracles; they check exact threshold acceptance, separate
model/curvature/scale/profile failures, nonfinite/zero handling and finite JSON.
Manufactured orchestration checks cover the full paired schedule, unchanged
target, independent seed-based commands, baseline mismatch, resource/settings
failures, shared deadlines, analytic rejection counting, native/event failures,
exclusive output and no solve/selection. These are not new mission observations.

Full suite: 3,784 tests pass in 598.42 s. Ruff, strict OpenSpec, CLI help, diff
checks and the unchanged legacy SHA-256 pass. On the retained 0086 inputs,
the standard-library directional calculation matches independent NumPy matrix
multiplication within 2.2118911147e-9 per dimensionless component (absolute
check tolerance 1e-7). D9.2 is complete; no live D9 experiment has occurred.

Prepared invocation for D9.3, not executed in D9.2:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment examples/m3_feasible_mission.toml docs/adr/experiments/0079-research-reference.json NEW_EVIDENCE.json --response-reference docs/adr/experiments/0086-targeting-study.json
```
