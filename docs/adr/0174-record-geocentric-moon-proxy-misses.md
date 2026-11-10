# 0174 — Record geocentric Moon proxy misses

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted measured result under [ADR0172](0172-design-geocentric-moon-holdout.md).
Implementation: [ADR0173](0173-prepare-geocentric-moon-holdout.md) unchanged.
Verification: R5.27 executed once and finalized; same-model parity and archived closure passed, strict proxy equivalence failed.
Scope / milestone: M3 R5.27; 16 rounded Moon/Earth epochs mapped to 21 frozen R5.24 observations.
Measured revision: `e997d36cbc2d15f49ab1d6571de5d7ccd4b2d848`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none. [ADR0171](0171-frozen-coast-moon-screen-passes.md) remains conditional on its operands.

## Context and constraints

R5.24 filled 16 missing Moon/Earth states with a rounded exact-record
position proxy. R5.27 tests whether the pinned provider returns the same
position bits at those epochs. The native call and exact reference use
the same INPOP19a model. The Earth/SSB and Moon/SSB states used for closure
were saved earlier; the test does not compare independent observations.

## Options considered

- Accept same-model parity alone: verifies the stated accuracy limits but
  does not show that the frozen force calculation would see identical inputs.
- Run the prepared one-shot capture and retain all three verdicts separately:
  executed as authorized, with the original epochs and budgets.
- Reevaluate the forces or recompute the trajectory: outside this check.

## Decision and rationale

| Comparison | Result | Interpretation |
|---|---:|---|
| Moon/Earth state versus exact same-model reference | 16/16 states pass | Maximum position norm `3.1723548746e-8 m` (limit `0.001 m`); maximum velocity norm `1.3269139264e-13 m/s` (limit `1e-6 m/s`). |
| Captured position bits versus rounded proxy | 39/48 components match | Nine components differ at seven epochs, linked to 11 of the 21 proxy observations. Nine epochs (10 observations) match in all three components. |
| One rounded Earth/SSB + captured Moon/Earth position versus archived Moon/SSB | 48/48 components match | Maximum absolute component residual before final rounding is `6.1700120568e-6 m`; the rounded result matches the archive. |

All nine proxy mismatches are one adjacent binary64 step: six in X
(`2.9103830457e-8 m` in magnitude) and three in Z (`1.4551915228e-8 m`).
Y matches at every epoch. The first miss, in acquisition order, is X
at `978995505.2304223` TDB s from J2000
(`0x1.d2d24989d7e7ap+29`, observations 1 and 15), with a signed
captured-minus-proxy delta of `-125/4294967296 m`. All later comparisons
completed; none are unavailable. The verification manifest lists all
affected epochs, observation ordinals, signed differences and raw words.

The full confirmation gate fails on proxy bit equivalence. The
differences do not invalidate the passing same-model parity or archived
closure checks. Closure can match even when the small geocentric operand
difference does not survive rounding of the much larger barycentric sum.

## Evidence and verification

- One [capture report](experiments/0174/capture.json) and
  [journal](experiments/0174/capture.ledger.jsonl): 63 explicit completed
  calls (1 setup, 30 inventory, 16 segment selectors, 16 states).
  The [parent receipt](experiments/0174/capture.parent-receipt.json)
  records 1.907383250 s within the 15 s budget; both finalizations pass.
  The selector and before/after identities match the pinned Moon segment,
  13 kernels and native environment. No Earth/SSB or Moon/SSB state calls.
- One [offline analysis report](experiments/0174/analysis.json) and
  [journal](experiments/0174/analysis.ledger.jsonl): 16 completed epoch
  comparisons and zero native calls. The
  [parent receipt](experiments/0174/analysis.parent-receipt.json) records
  0.654965834 s within the 10 s budget. Child and parent finalizations
  pass; exit 2 records the numerical negative, with no execution stop.
- The [verification manifest](experiments/0174-verification.json) binds
  the ten original attempt, report, journal and receipt files. A
  standard-library readback checked the hashes, ordering, 237 journal
  events, phase identities, exact signed residuals and classifications
  using only saved operands. All 726 original tracked files were
  unchanged across the run. All 721 protected paths, including code,
  prior evidence and `moon_to_mars.py`, remain unchanged in this record.
  Strict OpenSpec, artifact, local link and diff checks pass.
  ADR0173's 69 focused passes and guarded regression (5985 passed,
  407 skipped) apply to the unchanged code; runtime tests were not rerun.

## Consequences and revisit conditions

R5.27's one attempt is consumed. Do not retry, change the epochs or
relax the bit gate. R5.24 remains a conditional force result: the
live operand differs at 11 linked rows, and any effect on the lunar
force at those rows was not measured. A separate, explicitly scoped
saved-data design could assess that effect without a new query or
propagation. This check acquired no new explicit Type 2 records,
evaluated no force, propagated no trajectory and leaves R5.17 failed.
Earth-force sensitivity, strict M3 and mission safety remain open.
Automation stays paused.
