# 0087 — Reuse the retained correction with bounded damping

Date: 2026-09-28. Base revision: `6fb0e8c` plus D8.1 implementation and tests.
Decision status: accepted (bounded research implementation only).
Implementation: complete and tested; live D8.2 study not run.
Scope: M3 research D8.1; no production targeting or qualification.
Related OpenSpec: [active D8 tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none. Extends D7; does not replace its evidence.

## Context and constraints

The [D7 study](0086-targeting-step-does-not-improve.md) found that one full
correction increased the target miss. D8 asks whether smaller fractions of that
retained direction improve it. The accepted scope permits alpha=0.5 and 0.25
under one 300-second budget, without a new Jacobian or changed physical gates.

## Options considered

- Reuse the existing private preparation/composition path: selected to preserve
  common dynamics, guards and provenance, while making damping opt-in.
- Duplicate preparation or dynamics: rejected as unnecessary parallel machinery.

These alternatives are explicit in the original implementation record; no
additional historical deliberation is inferred.

## Decision and rationale

Extend the existing private targeting entrypoint with an opt-in
`--damping-reference` argument rather than duplicate preparation or dynamics.
Without that option, D7 retains its seed, probe/solve flow, acceptance rule and
8/9/27 limits. D8 uses the pinned Decision 0086 direction without a new solve.
Existing NumPy/native dependencies, physical settings and public APIs are unchanged.

The new input is bound by its SHA-256 and checked against Decision 0079 for
scenario, candidate, runtime/resources, seed, target, baseline states/epochs and
integration settings. Require a finite rank-six retained correction within the
original trust scales and a not-improving D7 outcome. Imported source hashes
remain historical provenance; new runs record current source hashes separately.

Replay the baseline and compare all four boundaries against both references.
Only then form x_seed+alpha*dx for alpha=0.5 and, if needed, 0.25. Both commands
start from the seed, not from one another or the failed alpha=1 trial. Reuse
canonical angle/window/propellant checks and sampled native guards.

The score threshold is S_base*(1-1e-4*alpha); both existing endpoint gates can
also establish nominal improvement. The comparison helper accepts only 1, 0.5
or 0.25, preserving D7's default alpha=1 behavior. Record each attempted fraction's
actual threshold before propagation. Zero/overflowing score ratios remain null
with a reason. Improvement is neither absolute accuracy nor mission acceptance.

## Consequences and revisit conditions

First improvement selects one frozen-command tighter run. Any remaining fraction
is explicitly skipped; validation failure/disagreement does not enable fallback.
Baseline closure skips both fractions. Failed attempts retain reasons and no
partial endpoint; prior completed observations stay available.

D8's separate budget permits at most three controls, four evaluations and 12
native arcs under one cooperative 300-second clock. It supports tighter
validation after either fraction but refuses further controls/runs afterward.
No retries, changed force model, new Jacobian, UI or production promotion.

Revisit the approach only after the single D8.2 study reports its outcome,
closure and numerical agreement. Any further fractions, iterations or budget
changes require a revised OpenSpec contract, not an automatic retry.

## Evidence and verification

301 focused tests passed in 11.83 s, including unchanged D4–D7/native regressions.
New manufactured checks cover both selection branches, no improvement, skipped
fractions, independent seed-based commands, imported identity failures, exact
acceptance thresholds, zero ratios, analytic/native failures, frozen validation,
fresh environments, one deadline and exclusive output. These verify orchestration,
not physical improvement. The actual retained artifact passes input validation;
no D8 mission propagation has occurred.

Full suite: 3,739 tests pass in 806.13 s. Ruff, strict OpenSpec, diff whitespace
and the unchanged legacy checksum checks pass. D8.2 remains the next step: one bounded live
study, retaining any negative outcome. Strict M3/task 3.9 remain open.

Prepared invocation, not executed in this step:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment examples/m3_feasible_mission.toml docs/adr/experiments/0079-research-reference.json NEW_EVIDENCE.json --damping-reference docs/adr/experiments/0086-targeting-study.json
```
