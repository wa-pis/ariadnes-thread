# 0177 — Paired lunar force gates pass

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted sampled result under [ADR0175](0175-design-paired-lunar-force-check.md).
Implementation: [ADR0176](0176-prepare-paired-lunar-force-check.md) unchanged.
Verification: one authorized R5.30 study and saved-evidence readback passed.
Scope / milestone: M3 R5.30; lunar point-mass acceleration at 11 frozen observations.
Measured revision: `4199e9b2bbd001767a8855a90fa0788ca4209f62`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none. The historical R5.24, R5.27 and R5.17 verdicts are unchanged.

## Context and constraints

[ADR0174](0174-record-geocentric-moon-proxy-misses.md) found one-step
differences in the Moon/Earth source position at seven epochs, affecting
11 rows of the [R5.24 conditional screen](0171-frozen-coast-moon-screen-passes.md).
R5.30 asks whether the measured source changes either original Moon
acceleration verdict at those rows. The reference is arithmetic on the
same model. This is a fixed-state test with no spacecraft propagation.

## Options considered

- Treat archived position closure as evidence of force equivalence:
  closure passes, but it does not check the separation used by the field.
- Evaluate the two frozen arms with the original tolerances: executed
  once after verified preparation.
- Reintegrate the coast or query the provider again: outside this test.

## Decision and rationale

All 11 proxy arms reproduce the archived separations, acceleration
bits, required reference fields and original gate verdicts. Replacing
only the three Moon/Earth position words changes the rounded separation
and the calculated acceleration in all 11 pairs. Both gates pass
in both arms at both precisions (88 checks), with no verdict flips
or unavailable rows. Exact substitution, rephasing, exterior geometry,
80/100-digit convergence and signed attribution checks all pass.

| Gate at 100 digits | Largest proxy error (m/s²) | Largest measured-source error (m/s²) | Largest measured-source fraction of limit |
|---|---:|---:|---:|
| Overall | `6.5787607826e-12` | `6.6121752581e-12` | 45.5310% (ordinal 1) |
| Returned geometry | `3.5145479538e-16` | `4.0579110888e-16` | 0.002794% (ordinal 6) |

The maximum norm of the acceleration change is `4.7384608443e-14 m/s²`
at ordinal 11 (normal RHS 4, local time `0.2816496580927726 s`).
This is 0.3263% of that row's overall envelope; it is the change
between arms, not either arm's error against the reference.
At 100 digits the largest unrounded source contribution is
`4.7423619852e-14 m/s²` (ordinal 27). Across the sample the largest
differential separation rounding and binary64 evaluation contributions
are `6.7258830651e-30 m/s²` and `3.8717994651e-16 m/s²`,
respectively. These maxima need not occur on the same row. Signed
attribution residuals are zero in the saved results at both precisions.

## Evidence and verification

- One [attempt](experiments/0177/pair.attempt.json), with
  [child](experiments/0177/pair.receipt.json) and
  [parent](experiments/0177/pair.parent-receipt.json) receipts finalized.
  The parent records 0.966496792 s before its final receipt flush,
  within the inclusive 10 s budget. The run completes 11 admissions,
  22 binary64 fields and 110 Decimal fields. No retry.
- The [report](experiments/0177/pair.json.gz) and
  [journal](experiments/0177/pair.ledger.jsonl.gz) are compressed without
  changing their uncompressed bytes. The separate
  [readback](experiments/0177/readback.json) validates identities,
  receipts, all 429 journal events and the verdicts from stored fields,
  without another field evaluation. A saved-data cross-check verifies
  the signed differences, both sets of gates and the reported maxima.
- The [verification manifest](experiments/0177-verification.json) binds
  the original digests, archived bytes and row summaries. Strict
  OpenSpec, hashes, local links and diff checks pass. All 752 original
  tracked files were unchanged through execution and readback; the
  747 protected paths remain unchanged in this record. The verified
  R5.29 tests and Ruff apply to unchanged code; runtime tests were not rerun.

## Consequences and revisit conditions

The actual saved position substitution preserves both lunar acceleration
verdicts at these 11 points. This does not turn the historical R5.24
proxy run into a measured run, reverse the R5.27 bitwise negative,
or repair R5.17. No new SPICE queries, explicit record acquisitions,
record evaluations, other-body fields, propagations or optimization.
Continuous-arc behavior, Earth-force sensitivity, strict M3 and mission
safety remain open. Automation stays paused.
