# 0171 — Frozen-coast Moon force screen passes

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted conditional sampled result under [ADR0169](0169-screen-split-moon-on-frozen-coast.md).
Implementation: [ADR0170](0170-prepare-frozen-moon-screen.md) unchanged.
Verification: one authorized offline R5.24 attempt passed; retained-evidence audit passed.
Scope / milestone: M3 R5.24; the Moon point-mass acceleration at 28 frozen spacecraft states.
Measured revision: `ab3d0a8247ae84264d6fb43f2de0c680ad804fdf`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none. [ADR0164](0164-corrected-coast-force-gate-fails.md) remains the R5.17 result.

## Context and constraints

[ADR0168](0168-real-split-centre-probe-passes.md) verified splitting the lunar
position into Earth/SSB and Moon/Earth legs at three epochs with zero low time
word. R5.24 asks whether keeping the two position legs through relative
subtraction passes the original Moon force checks at all the frozen
observations, including nonzero low words, while retaining the same spacecraft
motion and direct Moon velocity rephasing. The reference uses exact arithmetic
on the archived INPOP19a records. It is not an independent observation of the
lunar orbit.

## Options considered

- Run the prepared ADR0169 screen on the saved sample: executed once.
- Collect Moon/Earth returns at the 16 remaining rounded epochs: that would
  test a different question and needs separate design and authorization.
- Reintegrate the coast or change a gate: outside the experiment.

## Decision and rationale

All 28 rows pass both Moon force gates at both 80 and 100 Decimal digits,
including the signed rephasing, exterior geometry, precision convergence and
signed attribution checks. There are 19 distinct rounded epochs and 19
distinct exact epochs (29 in their union). Ten rows have a nonzero low time
word (six positive and four negative). The maximum rephasing increment
error is `1.261004005e-17 m` against the `1e-12 m` limit, at tighter RHS 2
(local time 0.0394501139690758 s).

| Geocentric leg at the rounded epoch | Rows passing | Worst overall error (m/s²) | Fraction of its limit | Worst returned-geometry error (m/s²) |
|---|---:|---:|---:|---:|
| Previously measured at 3 epochs | 7/7 | `7.348789611e-12` | 50.6033% | `3.163891587e-16` |
| Rounded exact-record proxy at 16 epochs | 21/21 | `7.191268756e-12` | 49.5186% | `3.514547954e-16` |

Values use the 100-digit gates. The worst measured overall result is normal
RHS 6 at 0.25 s; the worst proxy overall result is normal RHS 3 at
0.1183503419072274 s. The limits are about `1.452234548e-11 m/s²` at
both rows. All archived Earth/SSB and Moon/SSB states and the observed
Moon/Earth states pass the 0.001 m and 1e-6 m/s parity limits. The
reconstructed direct position matches 21/21 measured and 63/63 proxy
components; proxy closure is diagnostic and does not measure a SPICE return.

The three prior measured controls match the exact separations, binary64
separations and accelerations, and reference and gate checks in ADR0168.
There are 14 saved direct overall comparisons: 13 passed and one failed in
R5.17. The other 14 are unavailable and were not reconstructed. At the sole
failed row, 0.25 s, the split error is `7.348789611e-12 m/s²` versus the
saved direct `1.581286303e-11 m/s²`, with the same limit. This explains
the change in the fixed-state verdict; the original trajectory audit stays
failed.

## Evidence and verification

- [Attempt marker](experiments/0171/screen.attempt.json),
  [outer invocation](experiments/0171/execution.json),
  [child receipt](experiments/0171/screen.receipt.json) and
  [parent receipt](experiments/0171/screen.parent-receipt.json).
  Child and parent finalization pass under the 10 s budget. The parent
  receipt records 0.451197167 s before its final flush; the outer process
  records 0.494615125 s through exit, including startup and flush.
- The [raw report](experiments/0171/screen.json.gz) and
  [journal](experiments/0171/screen.ledger.jsonl.gz) are compressed without
  changing their uncompressed bytes. All 367 operations complete (28
  observation admissions, 29 reference epochs, 58 Type 2 record
  evaluations, 28 binary64 and 224 Decimal fields). The 1,101 journal
  events, saved operands, result order, exact row mapping and both sets
  of input hashes pass readback without reevaluating a field.
- The [verification manifest](experiments/0171-verification.json) binds the
  retained bytes, timeline, counts, gate maxima and original hashes.
  Strict OpenSpec, links, artifact and diff checks passed; 697
  protected files are unchanged, including all code, prior evidence and
  `moon_to_mars.py`. The verified preparation's 40 focused and 5,916
  guarded regression passes apply to the unchanged code; no runtime tests
  were rerun.

## Consequences and revisit conditions

The experiment used zero new SPICE queries, record acquisitions or trajectory
propagations. It supports conditional feasibility on these fixed points only.
A separate source-only holdout design could test the 16 unmeasured rounded
epochs; R5.24 does not authorize that live run. The continuous coast, the
Earth-force contribution, strict M3 and mission safety remain unverified.
Automation stays paused.
