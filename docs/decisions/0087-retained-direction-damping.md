# 0087 — Reuse the retained correction with bounded damping

Date: 2026-09-28. Base revision: `6fb0e8c` plus D8.1 implementation and tests.
Status: verified-path implementation work; no new mission experiment.

## Decision

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

First improvement selects one frozen-command tighter run. Any remaining fraction
is explicitly skipped; validation failure/disagreement does not enable fallback.
Baseline closure skips both fractions. Failed attempts retain reasons and no
partial endpoint; prior completed observations stay available.

D8's separate budget permits at most three controls, four evaluations and 12
native arcs under one cooperative 300-second clock. It supports tighter
validation after either fraction but refuses further controls/runs afterward.
No retries, changed force model, new Jacobian, UI or production promotion.

## Checks and next step

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
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment examples/m3_feasible_mission.toml docs/decisions/experiments/0079-research-reference.json NEW_EVIDENCE.json --damping-reference docs/decisions/experiments/0086-targeting-study.json
```
