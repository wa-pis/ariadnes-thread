# 0176 — Prepare the paired lunar force check

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted implementation of [ADR0175](0175-design-paired-lunar-force-check.md).
Implementation: R5.29 complete; R5.30 not run.
Verification: synthetic pairs and saved metadata; guarded regression.
Scope / milestone: M3 R5.29; private offline comparison preparation.
Base revision: `fbdea11ab826494ff1d4ba28ff621041d445242f`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none.

## Context and constraints

[ADR0174](0174-record-geocentric-moon-proxy-misses.md) found a different
source position at 11 linked observations. R5.29 prepares the frozen
comparison without evaluating the archived force rows. The independent
Decimal reference, both original force envelopes, exact sample and
offline scope are unchanged from ADR0175.

## Options considered

- Extend the production force path: unnecessary for a saved-data check.
- Reuse the verified arithmetic and archive helpers in a private runner
  with synthetic verification: chosen, with no new dependency.

## Decision and rationale

The [loader](experiments/0176/ariadna_paired_moon_inputs.py) verifies the
41 bound files, the finalized R5.24 screen and R5.27 capture and analysis
receipts, and each ordinal's exact link to the raw Moon/Earth state.
A complete R5.27 proxy-bit negative is valid input; a broken phase,
mismatched row or changed archive is rejected.

The [pair calculation](experiments/0176/ariadna_paired_moon_math.py)
rebuilds the proxy, changes only the three position words in the second
arm, and retains both gate results and signed acceleration attribution
at 80 and 100 digits. Tests cover an analytic point-mass result, a source
step hidden by separation rounding, a change in an original gate, and an
unresolved precision verdict. Later valid pairs remain available after
a finite numerical miss.

The [runner](experiments/0176/ariadna_paired_moon_run.py) allows one
exclusive future attempt, enforces the ADR0175 caps and preserves the
raw return before validation. The readback verifies both receipts,
journal order and hashes, then rebuilds completed pair verdicts from
the saved field returns. It does not invoke a field evaluator. Tests
exercise successful and negative readbacks, a finalized stopped prefix,
late or missing returns, identity and receipt tampering, and a watchdog
failure. An unfinalized attempt keeps its raw artifacts but cannot
qualify a result.

## Evidence and verification

- [Focused pytest](experiments/0176/pytest-focused.txt): 51 passed
  on synthetic inputs and saved metadata. A metadata-only read from a
  fresh stdlib process bound all 11 observations and 41 retained files.
- [Guarded regression](experiments/0176/pytest-guarded.txt): 6036 passed,
  407 skipped under the unchanged
  [SPICE guard](experiments/0170/pytest-no-spice-guard.py.txt);
  [skip inventory](experiments/0176/pytest-guarded-skips.tsv).
  No unrestricted regression was run.
- Ruff, strict OpenSpec, hashes, links and diff checks passed.
  The [verification manifest](experiments/0176-verification.json) pins
  tested and reused sources and test evidence. All 736 protected files,
  including prior evidence and `moon_to_mars.py`, are unchanged.

## Consequences and revisit conditions

R5.30 needs a separate execution instruction after this verified
preparation. There was no SPICE call, archive record evaluation,
archived force evaluation or propagation. Synthetic results cannot
establish the effect at the actual 11 observations. R5.24 remains
conditional, R5.27 remains a bitwise negative, R5.17 remains failed,
strict M3 and mission safety stay open, and automation stays paused.
