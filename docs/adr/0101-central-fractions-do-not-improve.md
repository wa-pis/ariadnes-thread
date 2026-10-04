# 0101 — Retain two unsuccessful central-direction fractions

Date: 2026-10-04
Decision status: accepted (negative evidence, not a qualified trajectory).
Implementation / verification: D12.3 complete; neither fraction improves.
Scope / milestone: one M3 research study; evidence/documentation only.
Measured revision: `08a2ce4`, committed and pushed before the experiment.
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
Supersedes / Superseded by: none; completes [0099](0099-central-direction-damping-contract.md) and [0100](0100-central-damping-implementation.md).

## Context and constraints

D11's full central-matrix step worsened the endpoint score. D12 asks whether
one half or one quarter of that same retained direction improves the original
seed, without new derivatives, solve, chained updates or changed dynamics.

## Options considered

- Select a fraction because it is less bad than the full step: rejected;
  acceptance compares against the original baseline, not the failed full step.
- Automatically shrink further or iterate: deferred; outside the accepted
  two-fraction study, and no measured improvement justifies promotion.
- Preserve both failed trials and stop: selected; records the bounded question's
  answer without implying that all smaller steps or targeting methods fail.

## Decision and rationale

Retain [finite JSON evidence](experiments/0101-central-damping-study.json), SHA256
`70bd01122433fea421d27b44edd9bc1f5324e834aa80f8979af4e2d3b6af9c07`.
One invocation completed **3 controls, 3 nominal evaluations and 9 native arcs
in 7.868361334 s**, below the 300-second/twelve-arc limits. Baseline boundaries
and masses replay exactly against 0079 and 0098. Both commands were independently
formed from the original seed plus the prescribed fraction of D11's retained
step; no new correction solve or derivative probes occurred.

| Quantity | Baseline | Half step | Quarter step |
|---|---:|---:|---:|
| Position miss, m | 197851062193.60904 | 207854853610.09958 | 200622425125.34784 |
| Velocity miss, m/s | 31160.14668810916 | 32616.166421787882 | 31717.905726284785 |
| Scaled score | 197875598.18874988 | 207880442.35183948 | 200647496.1683111 |
| Score / baseline | 1 | 1.0505612832237463 | 1.0140082860389745 |
| Sufficient-decrease threshold | — | 197865704.40884045 | 197870651.29879516 |

Both scores exceed their alpha-dependent thresholds and neither closure gate
passes. No fraction is selected; tighter evaluation is skipped and numerical
agreement is unavailable. The smaller quarter trial is closer to baseline than
the half trial, but still worse than baseline. No retry or extra fraction.

Invocation from the repository root in the pinned Conda environment:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment \
  examples/m3_feasible_mission.toml \
  docs/adr/experiments/0079-research-reference.json \
  docs/adr/experiments/0101-central-damping-study.json \
  --central-damping-reference docs/adr/experiments/0098-central-correction-study.json
```

## Consequences and revisit conditions

D12 is complete with a negative outcome. These two finite steps do not establish
that the direction is never locally useful, nor isolate the cause of failure.
Stop the automatic sequence and review the targeting approach before specifying
further work. Strict M3/task 3.9, continuous safety and mission closure remain
unresolved; no production optimizer, UI change or automation restart.

## Evidence and verification

Independent checks reconstructed raw SI/scaled residuals, norms and scores,
seed-based commands, thresholds/ratios, exact baseline replays, retained step
and matrix, current/imported/reference hashes, counters and finite JSON. No native
rerun was used. 51 D12 focused checks pass; Ruff, strict OpenSpec, local links,
diff and unchanged legacy checksum pass. This evidence-only stage reuses D12.2's
287 focused / 3,947 full tests (609.93 s); runtime code is unchanged.
