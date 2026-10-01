# 0088 — Stop after the retained-direction damping study

Date: 2026-10-02
Decision status: accepted (retain the negative result and stop this study).
Implementation: D8.2 experiment complete; target closure remains unresolved.
Scope: M3 research D8, candidate d0001-t0035.
Measured revision: `6f2a06c0bcf4c20415768fc89c7baecc505891fe`, clean before the run.
Related OpenSpec: [D8 tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; completes the study specified in [0087](0087-retained-direction-damping.md).

## Context and constraints

The full D7 correction increased the residual score by 23.84%. D8 tests the
same retained direction at alpha=0.5 and then 0.25, each from the original seed.
Its shared budget is 300 seconds, three controls, four evaluations and 12 arcs.
The first improving trial would receive one frozen tighter run.

## Options considered

- Retain the negative result and stop: selected under the D8 contract.
- Try more fractions or another solve: deferred pending a separate specification
  and a reasoned diagnosis; this evidence does not justify automatic repetition.

## Decision and rationale

Neither fraction meets sufficient decrease or endpoint closure. Neither trial is
selected, so no tighter run is triggered. Smaller steps reduce the worsening
relative to alpha=1, but these samples do not identify the cause of failure or
establish a beneficial direction. Preserve the seed as the comparison baseline.

## Consequences and revisit conditions

D8 is complete as a bounded experiment with a negative targeting result.
Strict M3/task 3.9, target closure and continuous safety remain unresolved.
Before further native runs, review the residual/control mapping and predicted
versus observed local response, then specify a bounded next study with measurable
stop rules. No additional fractions or repeated optimization were executed.

## Evidence and verification

[Retained JSON](experiments/0088-damping-study.json) records current source hashes,
both pinned references, historical source hashes, resource/runtime identity,
commands, residuals, thresholds, counters and sampled-check coverage.

| Run | Position miss (m) | Velocity miss (m/s) | Scaled score | Score/baseline |
|---|---:|---:|---:|---:|
| Baseline | 197851062193.60904 | 31160.14668810916 | 197875598.18874988 | 1 |
| alpha=0.5 | 207757103123.9676 | 32509.829559770198 | 207782537.2562453 | 1.0500665021770161 |
| alpha=0.25 | 200802097615.2207 | 31754.86468375656 | 200827204.63369364 | 1.0149164751589443 |

Score thresholds were 197865704.40884045 and 197870651.29879516. Both misses
increased. All four baseline boundaries match both retained baselines exactly
in position, velocity and mass. Three controls, three evaluations and nine arcs
completed in 10.510074958 s; zero retries. Numerical agreement is null because
neither trial qualified for tighter validation. Sampled guards do not establish
continuous safety or absolute accuracy.

69 focused tests passed in 0.37 s before the single invocation. Independent
readback verified reference/current-source hashes, seed-based commands,
Euclidean miss norms, scores, thresholds, ratios, baseline replay and counters.
Ruff, strict OpenSpec, diff checks and unchanged legacy SHA-256 pass.
Full-suite evidence remains D8.1's 3,739 tests; the full suite was not rerun for
this evidence/documentation-only stage. Runtime code is unchanged.

Invocation (executed once; do not overwrite the retained output):

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment examples/m3_feasible_mission.toml docs/adr/experiments/0079-research-reference.json docs/adr/experiments/0088-damping-study.json --damping-reference docs/adr/experiments/0086-targeting-study.json
```

Exit zero denotes diagnostic completion with outcome `not-improving`. Tudat
emitted its existing `mass_rate.custom` deprecation warning.
