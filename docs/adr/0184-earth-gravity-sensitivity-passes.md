# 0184 — Earth-gravity sensitivity passes on the short coast

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted within the [ADR0182](0182-design-earth-gravity-sensitivity.md) contract.
- Implementation: R5.37 complete.
- Verification: one live B-only study and one independent saved-data audit passed.
- Scope: M3 restricted numerical Earth-gravity sensitivity on the frozen 300 s coast.
- Base and measured revision: `72cb05977741d6783eeeb01557e4c4f64aed1bce`, clean synchronized `dev`.
- Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
  [design](../../openspec/changes/refine-physical-trajectory/design.md),
  [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [R5.3](0148-short-coast-oracle-rhs-limit.md) and
  [R5.17](0164-corrected-coast-force-gate-fails.md) retain their failures.

## Context and constraints

[R5.34](0181-split-moon-coast-recheck-passes.md) verified the Sun/Moon
model A at the specified nodes and samples. R5.37 asks how adding
Earth's direct point gravity changes the spacecraft state after
300 s. Both models start at the same stored state and use the same
prescribed moving ephemerides, constants, axes and epochs. Model B
adds only Earth's direct acceleration; there is no burn or retargeting.

## Options considered

- Estimate the displacement by applying Earth gravity to the saved A
  path: omits the feedback of trajectory changes through the fields.
- Reuse the saved A states and calculate B in both engines: selected
  by ADR0182. B samples its own trajectory. No A integration or
  interpolation is needed.

## Decision and rationale

Accept the measured B-minus-A sensitivity at the seven declared
coepochs, conditional on the archived A reference. The native A
h0.5 trajectory comes from R5.3, and the DOP853 tighter A trajectory
from R5.34. The native A final identity remains unavailable. Both
estimates use signed Cartesian position and velocity differences
in inertial SSB/J2000 axes; their agreement is a numerical check.

At t0 + 300 s (978995755.2304223 TDB s since J2000):

| Estimate | Position change norm (m) | Velocity change norm (m/s) |
| --- | ---: | ---: |
| Tudat RK4 h0.5: B minus archived A | 110.393700168 | 0.733202925841 |
| SciPy DOP853 tighter: B minus archived A | 110.393770903 | 0.733202901761 |
| Norm of the signed discrepancy | 0.000112129 | 2.69618e-8 |

The endpoint DOP853 displacement vector is approximately
(48.849762, -93.606918, -32.221581) m. The change includes the effect
of following a different path through the Sun and Moon fields.
Both effect norms exceed the comparison scales at all six noninitial
nodes, and the initial effect is zero. Across all seven nodes, the
largest discrepancy is 0.000173307 m (250 s) and 2.69618e-8 m/s
(300 s), below the unchanged 0.02 m and 2e-5 m/s gates. Those gates
measure agreement between the two estimates.

## Evidence and verification

| Seven B nodes per comparison | Maximum position difference / gate (m) | Maximum velocity difference / gate (m/s) |
| --- | ---: | ---: |
| Native RK4 h1 vs. h0.5 | 1.26058e-4 / 0.01 | 1.72150e-8 / 1e-5 |
| Native RK4 h0.5 vs. DOP853 tighter | 8.96251e-5 / 0.01 | 9.82985e-9 / 1e-5 |
| DOP853 normal vs. tighter | 0 (rounded outputs) / 0.001 | 1.96045e-9 / 1e-6 |

- Both RK4 and both DOP853 B profiles reached 300 s. All 21 B
  trajectory comparisons, seven signed-effect comparisons and 14
  native B node telemetry checks passed. The native histories have
  301 and 601 states; all 2,712 preflight and retained-state
  guard reads passed and were reused by the audit.
- The 28 DOP853 observations passed 112 source-state parity checks
  and 448 acceleration gate outcomes (four fields including total B,
  two gates, two precisions). Worst sampled Earth overall force error
  was 0.6034% of its gate, and worst total B overall force error was
  50.3042% of its gate. All observed high epoch words overlapped
  R5.24; the B motion was evaluated at its own states.
- The B study made 12,828 explicit DOP853 and node state requests
  (3,207 per route) across 3,200 RHS records (790 normal, 2,410
  tighter) and 263 trials, plus the separately counted native guard
  reads. Native simulator internal ephemeris evaluations are outside
  these counters. The audit independently replayed saved arithmetic,
  forces and state comparisons with zero new native calls or solves.
- Both child and parent receipts passed for each phase, with matching
  input, report and receipt hashes and unchanged checkout. Parent
  elapsed times were 6.6092 s of 60 s for the study and 1.8058 s of
  10 s for the audit. The study's before and after identities matched.

The [manifest](experiments/0184/manifest.json) records the signed
vectors at all seven nodes, maxima, gate checks, counters and hashes.
The complete [study](experiments/0184/study.json.gz) and
[audit](experiments/0184/audit.json.gz) are lossless copies of the
original JSON, with the
[study parent receipt](experiments/0184/study.parent-receipt.json) and
[audit parent receipt](experiments/0184/audit.parent-receipt.json)
binding the archived files to the measured revision. Receipt chains,
finite JSON, archive round trips, input hashes, local links, diff and
strict OpenSpec were checked. Runtime tests and Ruff were reused from
[ADR0183](0183-prepare-earth-gravity-comparison.md) on unchanged code
and test bytes (26 focused, 6,152 passed and 407 skipped guarded).

## Consequences and revisit conditions

The once-only R5.37 execution is consumed. This is a measured
difference between two restricted force models on a particular
300 s coast. It does not repair prior results, qualify the full
transfer or finite burns, prove continuous accuracy or safety, or
close strict M3. There was no change to production code or inputs.
Automation remains paused.
