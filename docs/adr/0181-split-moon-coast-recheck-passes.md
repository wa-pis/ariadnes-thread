# 0181 — Split Moon coast recheck passes

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted within the [ADR0179](0179-design-split-moon-integration-recheck.md) contract.
- Implementation: R5.34 complete.
- Verification: one live study and one separate saved-data audit passed.
- Scope / milestone: M3 R5.34; conditional numerical agreement for short-coast model A.
- Base and measured revision: `27dfc6d9182a1a467aa8367349ed215c556745b1`, clean synchronized `dev`.
- Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
  [design](../../openspec/changes/refine-physical-trajectory/design.md),
  [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes / Superseded by: none. The [R5.17 failure](0164-corrected-coast-force-gate-fails.md) remains in effect.

## Context and constraints

R5.17 passed 21 trajectory comparisons but failed the sampled Moon
overall acceleration gate. R5.33 verified the new split-position
arithmetic on fixed saved rows and exercised the study and audit with
synthetic inputs. R5.34 tests whether that path meets the original
numerical gates when used inside two actual model A integrations.

Use the same initial state, force model, kernels, seven output times,
native reference nodes, tolerances and profile settings frozen by
ADR0179. Model A accelerates under the Sun and Moon; Earth supplies
ephemeris and geometry information, with no Earth acceleration.

## Options considered

- Rely on fixed-state replay: useful for the force expression, but does
  not check the states reached by a real adaptive solve.
- Run the frozen two-profile study once and audit its saved data:
  selected to check both the force and the numerical trajectory at
  the specified observations, with no new native reference propagation.

## Decision and rationale

Accept the private split-position integration path as numerically
verified for this specific 300 s coast, conditional on the retained
reference and at the stated nodes and samples. Saved native reference
nodes were reused; the two new solves used live ephemerides. The
independent audit replayed the arithmetic on every saved RHS and
output and reconstructed the sampled source and force checks and
the trajectory comparisons without using the candidate force math.

## Evidence and verification

The two new profiles reached 300 s. All 21 comparisons passed:

| Seven nodes per comparison | Maximum position difference / limit (m) | Maximum velocity difference / limit (m/s) |
| --- | ---: | ---: |
| Saved native h1 vs. h0.5 | 1.93010e-4 / 0.01 | 3.43894e-8 / 1e-5 |
| Saved native h0.5 vs. new tighter | 1.63276e-4 / 0.01 | 2.77280e-8 / 1e-5 |
| New normal vs. new tighter | 0 (rounded outputs) / 0.001 | 1.54095e-9 / 1e-6 |

All 28 observations passed: 112 state parity checks across four state
routes, and 336 acceleration gate outcomes across Sun, Moon and total A,
two gates and two Decimal precisions. Five sampled RHS epochs per
profile used a nonzero low time word. All 28 observed high epoch words
were also present in R5.24; the new motion was evaluated at its own
sampled states. Rounded split/direct Moon position closure was bitwise
equal at all 28 observations; closure is separate from the force gates.

The largest sampled Moon overall error relative to its bound was
7.34879e-12 m/s² against 1.45223e-11 m/s² (50.6033% of the bound).
It occurred at normal RHS index 6, local time 0.25 s, the same sample
label as in R5.17 (108.8864%). This is a comparison of the recorded
gate outcomes at that label, without assuming identical spacecraft
states across the two runs.

Study and audit finalized in 3.5283 s and 1.4023 s respectively
against the 60 s and 10 s limits, including parent verification.
All four child and parent receipts passed and were cross-checked
against the attempt markers and reports. Both runtime snapshots
matched. The study recorded 11,628 explicit state requests
(2,907 per route, including shared output calls), 2,900 RHS records
(790 normal, 2,110 tighter), 238 trials, 42 node guards and 114 retained
record evaluations. The audit made zero SPICE calls or propagations.
There was no new native spacecraft propagation in either phase.

The [manifest](experiments/0181/manifest.json) retains full precision
maxima, counters, receipt times and evidence digests. The
[study](experiments/0181/study.json.gz) and
[audit](experiments/0181/audit.json.gz) archives restore the exact
original report bytes. The
[study receipts](experiments/0181/study.parent-receipt.json) and
[audit receipts](experiments/0181/audit.parent-receipt.json) bind both
phases to the preparation manifest, measured revision and saved reports.
JSON, archive round trips, receipt hashes, frozen input and code hashes,
local links, protected stage scope, diff and strict OpenSpec were checked.
[ADR0180](0180-prepare-split-moon-integration.md) owns the 90 focused and
6,126 guarded passing tests (407 skips) and Ruff result; runtime checks
were not rerun for this evidence-only stage.

## Consequences and revisit conditions

The once-only R5.34 experiment is consumed. All-RHS arithmetic replay
does not qualify unsampled source fidelity or establish continuous
trajectory accuracy. R5.3 and R5.17 retain their failures and missing
historical identity. Earth-force sensitivity, the full transfer and
continuous safety, finite burns, mission readiness and strict M3
remain open. Further science requires its own bounded contract.
Production code is unchanged and automation stays paused.
