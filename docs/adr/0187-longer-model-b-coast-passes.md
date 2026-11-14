# 0187 — The 600 s model B coast passes numerical checks

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted within the [ADR0185](0185-design-longer-model-b-coast.md) contract.
- Implementation: R5.40 complete.
- Verification: one real-ephemeris B study and one independent saved-data audit passed.
- Scope: unpowered parking coast from the fixed state of candidate `d0001-t0035`.
- Measured revision: `fbf0b6083f8c667a7c5220ff38146eeef11d6647`, clean synchronized `dev`.
- Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-independently-check-the-longer-model-b-coast),
  [design result](../../openspec/changes/refine-physical-trajectory/design.md#r540-real-ephemeris-model-b-result-2026-11-14),
  and [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. Historical failures and earlier evidence retain their scope and status.

## Context and constraints

R5.37 checked the first 300 s of model B and measured the effect of
Earth's gravity relative to saved A on that interval. R5.40 asks
whether two independent integrators still agree for B over 600 s,
including the extension, while reproducing the archived B prefix.
The initial position and velocity, kernel set, settings, gravitational
parameters and acceptance gates are unchanged. The sole forces are
direct point-mass gravity from the Sun, Moon and Earth. Output is
geometric, in SSB/J2000, in SI and at TDB seconds since J2000. The
initial epoch is 978995455.2304223 and the final epoch is
978996055.2304223. No burns, new target, optimizer, GM acquisition,
model A propagation or 600 s B-minus-A estimate are included.

## Options considered

- Rerun both A and B over 600 s: answers a different sensitivity
  question and requires an additional integration.
- Extend only B with separate RK4 and DOP853 integrations, and
  audit their saved operands independently: selected by ADR0185.
  This isolates the duration change and uses the saved B prefix as
  a control. The integrators share the force contract and source data.

## Decision and rationale

Accept sampled same-model numerical agreement on this specific
600 s coast. Two Tudat RK4 profiles (1.0 s and 0.5 s fixed steps)
and two SciPy DOP853 profiles (normal and tighter) reached all
13 common nodes from 0 through 600 s at 50 s intervals. The 39
within-study comparisons and 28 same-profile archive comparisons
all passed. The native prefix matched the archived states exactly at
the seven declared nodes. Both DOP853 prefixes matched the rounded
archived positions; the maximum velocities differed by
2.43604e-10 and 4.65977e-12 m/s, respectively.

| Comparison | Max prefix position (m) | Max extension position (m) | Position gate (m) | Max prefix velocity (m/s) | Max extension velocity (m/s) | Velocity gate (m/s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RK4 1 s vs. 0.5 s | 1.26058e-4 | 1.55048e-4 | 0.01 | 1.72150e-8 | 4.15905e-8 | 1e-5 |
| RK4 0.5 s vs. tighter DOP853 | 8.96251e-5 | 7.23788e-5 | 0.01 | 9.82809e-9 | 2.39952e-8 | 1e-5 |
| Normal vs. tighter DOP853 | 0 (rounded) | 0 (rounded) | 0.001 | 1.72239e-9 | 5.12787e-9 | 1e-6 |

The prefix is 0–300 s; the extension nodes are 350–600 s. At
600 s the tight profiles differ by 7.15701e-5 m (0.0716 mm)
and 2.39952e-8 m/s. The signed DOP853-minus-native residual
vectors at every node are retained with their assessments.

## Evidence and verification

- The independent audit reconstructed all 67 comparisons, 52
  adaptive source/force observations and 26 native telemetry rows.
  It made zero native calls, kernel loads or spacecraft integrations
  and imported no scientific packages.
- The 52 observations contain 26 output rows, 14 early RHS rows and
  12 extension RHS rows. All 208 source-state parity checks and 832
  force gate outcomes passed. The worst sampled overall force
  residuals for Moon and summed B used 50.98% and 50.68% of their
  unchanged envelopes, respectively (normal profile at +500 s).
  The corresponding Earth and Sun maxima were 0.6034% and 0.00405%.
- The native histories retain 601 and 1,201 states. Both histories
  passed the discrete guards, with 5,412 explicit preflight and
  retained-state guard reads. The adaptive side logged 5,852 RHS
  evaluations, 481 trials and 23,460 explicit state requests,
  separate from the native reads and Tudat's internal lookups.
- Before/after runtime identities matched. Both child and both parent
  receipts passed with the same measured checkout. Parent elapsed
  times were 7.7121 s of 60 s for the study and 2.9908 s of 10 s for
  the audit. Neither phase was repeated.

The [manifest](experiments/0187/manifest.json) records the exact
state, comparison rows, gate maxima, counts, elapsed times and
hashes. The [study](experiments/0187/study.json.gz) and
[audit](experiments/0187/audit.json.gz) archives are lossless copies
of the original JSON. The [study parent receipt](experiments/0187/study.parent-receipt.json)
and [audit parent receipt](experiments/0187/audit.parent-receipt.json)
bind the evidence and attempt records to the measured revision.
Receipt chains, archive round trips, frozen hashes, links, the diff
and strict OpenSpec validation passed. [R5.39's](0186-prepare-longer-model-b-coast.md)
24 focused tests, guarded regression (6,089 passed, 494 skipped)
and Ruff apply to the unchanged runtime and test files.

## Consequences and revisit conditions

The once-only R5.40 study and audit are consumed. The experiment
checks numerical agreement on a fixed unpowered interval with shared
ephemerides. It does not validate ephemeris truth, continuous clearance,
a finite burn, the departure after a burn, the complete transfer,
mission safety or strict M3 acceptance. The evidence retains
`scientific_verified: false` in the original reports; the accepted
claim is the sampled numerical check. A later post-burn study needs its
own boundary and acceptance contract. Automation remains paused.
