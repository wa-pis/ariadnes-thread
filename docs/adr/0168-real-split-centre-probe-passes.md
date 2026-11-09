# 0168 — Real split-centre ephemeris probe passes

Date: 2026-11-09 (Europe/Samara)
Decision status: accepted sampled result under [ADR0166](0166-bound-split-centre-ephemeris-probe.md).
Implementation: [ADR0167](0167-prepare-split-centre-probe.md) unchanged.
Verification: one authorized real capture and one offline analysis; both passed.
Scope / milestone: M3 R5.21; numerical behavior of three frozen states and static Moon acceleration.
Measured revision: `bec219dccd0308f366d699f87c2a1f43f0bb83af`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none. The [ADR0164](0164-corrected-coast-force-gate-fails.md) result stands.

## Context and constraints

R5.17 failed the sampled Moon overall force gate at 0.25 s. R5.18 showed
that staged centre rounding could reproduce archived position bits, without
observing the Moon/Earth leg. R5.21 observes that leg and the Earth/SSB
leg at the three agreed coepochs. It tests whether retaining both legs
through relative subtraction is sufficient at the same frozen spacecraft
states and with the same reference, GM, and force tolerances.

## Options considered

- Use the exact archived geocentric proxy alone: cannot verify the actual
  Moon/Earth return.
- Perform the bounded split-centre capture and static comparison: executed
  once using the unchanged ADR0167 files.
- Rerun propagation or extrapolate the three point results to the whole
  coast: outside the contract.

## Decision and rationale

The nine queries reproduce all 36 archived direct Earth/SSB and Moon/SSB
state components bitwise. All nine states meet the same-model parity limits
of 0.001 m and 0.000001 m/s; the largest measured discrepancies are
13.269367 µm and 2.500722E-12 m/s. The rounded
sum of the two position legs matches the direct Moon/SSB return in all
nine comparisons. Velocity closure is a diagnostic and does not contribute
to acceptance. The signed source attribution checks pass.

At all three frozen positions, both the returned-geometry and overall
Moon force gates pass at 80 and 100 Decimal digits. The table uses the
100-digit results. Errors and limits are acceleration norms in m/s².

| Local s | Raw position closure | Archived direct overall error | Split overall error | Overall limit | Returned-geometry error |
|---:|:---:|---:|---:|---:|---:|
| 0.25 | 3/3 | 1.581286303E-11 | 7.348789611E-12 | 1.452234548E-11 | 3.163891587E-16 |
| 0 | 3/3 | 9.131508562E-12 | 3.816954371E-12 | 1.452234548E-11 | 3.436347295E-17 |
| 250 | 3/3 | 1.259202969E-11 | 5.257847636E-12 | 1.452279193E-11 | 1.480897340E-16 |

At 0.25 s, the overall error moved from 108.886% of its
unchanged limit to 50.603%. The original fail/pass/pass
became pass/pass/pass in the fixed-state split diagnostic. This supports
keeping the legs separate through relative subtraction for this sample.
It does not identify internal CSPICE instructions or bound unsampled errors.

## Evidence and verification

- One [capture](experiments/0168/capture.json), 1.392101541 s of 15 s
  ([parent receipt](experiments/0168/capture.parent-receipt.json),
  [child receipt](experiments/0168/capture.receipt.json),
  [raw journal](experiments/0168/capture.ledger.jsonl)).
  All 46 explicit operations completed: one setup, 30 inventory API calls,
  nine state queries and six selectors. Before/after 13-kernel, library,
  runtime and tested-input identities match.
- One [offline analysis](experiments/0168/analysis.json), 0.334476417 s
  of 10 s ([parent receipt](experiments/0168/analysis.parent-receipt.json),
  [child receipt](experiments/0168/analysis.receipt.json),
  [field journal](experiments/0168/analysis.ledger.jsonl)).
  Three binary64 and 18 Decimal fields completed; precision convergence,
  exterior geometry and force telescopes pass. Zero native queries in this
  phase. All requested checks are available; no retry or first failure.
- The [verification manifest](experiments/0168-verification.json) binds both
  attempt markers, raw files, runner, input and tested code hashes, elapsed
  times and document checks. The complete execution evidence is retained
  byte for byte. The 6283 passing tests and Ruff result from ADR0167 apply to
  unchanged code; no runtime regression was rerun for this evidence update.

## Consequences and revisit conditions

R5.21 is complete for these three fixed points. No new propagation, GM
query, Type 2 record read, polynomial evaluation by the diagnostic, or
optimiser run occurred. R5.17 remains failed and consumed. R5.3 causality,
Earth-force sensitivity, full-coast agreement, strict M3 and mission safety
are still open. No production change or new integration is authorized by
this result; automation stays paused.
