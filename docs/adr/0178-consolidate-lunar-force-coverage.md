# 0178 — Consolidate frozen lunar force coverage

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted evidence synthesis.
Verification: 28 saved observations reconciled; no new scientific execution.
Scope / milestone: M3 R5.31; both original lunar point-mass acceleration gates at the R5.24 observations.
Evidence revision: `c8643452088b9ff449ee6939a4597ef9472135ee`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md#r531-combined-frozen-moon-coverage-2026-11-10),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none.

## Context and constraints

[R5.24](0171-frozen-coast-moon-screen-passes.md) checked 28 frozen
observations with split Earth/SSB and Moon/Earth positions. The geocentric
leg was a saved SPICE return in seven rows and a rounded record proxy in 21.
[R5.27](0174-record-geocentric-moon-proxy-misses.md) obtained the missing
Moon/Earth returns: ten proxy rows match the three position words exactly;
eleven differ. [R5.30](0177-paired-lunar-force-gates-pass.md) checked the
eleven differing rows by substituting only those position words, with the
same epochs, spacecraft states, rephasing and force tolerances.

## Options considered

- Retain only the conditional R5.24 verdict: preserves the original run
  but omits the later evidence for the 21 proxy rows.
- Reconcile the evidence by observation ordinal: exact operand identity
  carries the saved force verdict across for ten rows, and the R5.30
  paired verdicts cover the other eleven.
- Repeat the force evaluations for all 28 rows: unnecessary for this
  inference and outside the agreed scope.

## Decision and rationale

Both original gates (overall and returned geometry) are supported at
all 28 frozen observations using the saved Moon/Earth positions, at
80 and 100 digits under the original tolerances. The routes are disjoint:

| Evidence route | Observations | Distinct rounded epochs | R5.24 observation ordinals (zero based) |
| --- | ---: | ---: | --- |
| R5.24 evaluated with saved [R5.21](0168-real-split-centre-probe-passes.md) returns | 7 | 3 | 0, 5, 7, 13, 14, 19, 21 |
| R5.27 returned the same three position words as the R5.24 proxy | 10 | 9 | 3, 8, 9, 10, 12, 17, 22, 23, 24, 26 |
| R5.30 evaluated the R5.27 return in place of the differing proxy | 11 | 7 | 1, 2, 4, 6, 11, 15, 16, 18, 20, 25, 27 |
| **Total** | **28** | **19** | **0–27** |

For the ten bitwise matches, the only operand subject to replacement is
identical, so both saved verdicts carry over. There is no new evaluation
or claim of velocity bit identity. For the eleven differences, both
arms passed both gates with zero flips. The seven directly sourced rows
used the split construction; they are not the direct barycentric
comparisons from R5.17.

## Evidence and verification

The [coverage manifest](experiments/0178-verification.json) links each
R5.24 ordinal to the saved capture ledger and, for the eleven
substitutions, its R5.30 row. The audit checks 48 retained file hashes,
six receipt chains, row identities, position words, and the saved
gate verdicts. A separate read of the stored reports confirms the same
7/10/11 partition and gate coverage. Strict OpenSpec, local links, diff
and protected file checks pass. Runtime tests were not rerun; the
[previously tested code](0176-prepare-paired-lunar-force-check.md) is unchanged.

## Consequences and revisit conditions

This is evidence for the split Moon calculation at the sampled points,
with arithmetic references for the same model. R5.24 retains its
conditional record, R5.27 retains its negative bitwise verdict, and
[R5.17](0164-corrected-coast-force-gate-fails.md) remains failed.
The synthesis does not establish continuous-arc behavior, Earth-force
sensitivity, M3 completion or mission safety. No SPICE queries, record
acquisitions or evaluations, force evaluations, trajectory propagation
or optimization were performed. Automation stays paused.
