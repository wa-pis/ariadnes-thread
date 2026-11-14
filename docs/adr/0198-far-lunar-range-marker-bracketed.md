# 0198 — Bracket the 18,374 km lunar range marker

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted within [ADR0196](0196-design-far-lunar-range-check.md).
- Implementation: R5.51 complete; both once-only phases consumed.
- Verification: real-ephemeris study and independent saved-data audit passed.
- Scope: 16,000 s of unpowered model B from the R5.48 tighter RK4 endpoint for `d0001-t0035`.
- Measured revision: `6dde4be6bd4ba0caaaa1925075862a7bdb0c61d8`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-the-18374-km-lunar-range-marker), [design result](../../openspec/changes/refine-physical-trajectory/design.md#r551-real-ephemeris-far-lunar-range-result-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[ADR0195](0195-prospective-lunar-range-marker-bracketed.md) verified the
3,474.8 km marker and retained the tighter RK4 terminal six-state.
[ADR0196](0196-design-far-lunar-range-check.md) fixed the new diagnostic
radius at 18,374,000 m from the lunar centre. All four profiles restarted
from the same archived state at 978998965.9635216 TDB s since
J2000 with 1351.7475727997967 kg constant mass metadata. The arc ended
at 979014965.9635216 TDB s. It used the pinned Sun/Moon/Earth
point-mass model with geometric ephemerides, SSB/J2000, zero thrust and
zero mass flow. No preceding arc, burn, model A or search was rerun.

## Options considered

- Use the saved R5.48 trajectory: it stops below the new radius.
- Stop propagation when a marker is detected: that would make the
  duration and evidence coverage depend on the result.
- Run the fixed continuation once and audit the sampled brackets:
  selected in ADR0196 after the capacity check in
  [ADR0197](0197-prepare-far-lunar-range-check.md).

## Decision and rationale

Accept `numerical_status=passed` and `marker_status=marker-bracketed`
for this continuation. Each grid contains exactly one strict outward
pair, with positive radial signs at both ends, no inward pair and no
equality. All time offsets below are measured from the restart.

| Grid | Bracket (s) |
| --- | ---: |
| Four common grids at 50 s spacing | +13,250 to +13,300 |
| RK4 1 s mesh | +13,266 to +13,267 |
| RK4 0.5 s mesh | +13,266 to +13,266.5 |

The native brackets overlap at **+13,266 to +13,266.5 s**
(979012231.9635216 to 979012232.4635216 TDB s), within the common bracket.
No exact event time was interpolated.

| State comparison | Max position (m) | Gate (m) | Max velocity (m/s) | Gate (m/s) |
| --- | ---: | ---: | ---: | ---: |
| RK4 1 s vs. 0.5 s | 0.00162025 | 0.01 | 2.96155e-08 | 1e-5 |
| RK4 0.5 s vs. tighter DOP853 | 0.00137771 | 0.01 | 3.0646e-08 | 1e-5 |
| Normal vs. tighter DOP853 | 1.70598e-05 | 0.001 | 2.2521e-10 | 1e-6 |

## Evidence and verification

- The study completed in 31.934245 s of 480 s. Two RK4 arcs and two
  DOP853 solves used 117,200 RHS evaluations and
  9,606 trial attempts, with 470,084
  explicit source reads and 144,012 native
  guard reads (614,096
  total, excluding internal Tudat lookups). Before/after identities
  matched. There was one pool setup, 30 inventory calls and zero new GM
  reads. Each phase used 5,766 sampled SPK
  polynomial evaluations from the retained coefficients.
- The isolated stdlib audit completed in 28.069443 s of 300 s. It
  verified all 963 state comparisons, both native guard histories,
  642 native telemetry rows, 1,284 adaptive force/source observations
  and all 49,286 direction rows. It made zero scientific imports,
  native calls, kernel loads or propagations.
- Both watchdog and receipt chains passed. An additional readback
  verified all 372,967 stored rows and the raw and compressed
  digests of 40 shards. Combined payload:
  653,749,170 raw bytes and 183,462,545 compressed bytes,
  plus 20,353 bytes of manifests and receipts.
  The [verification manifest](experiments/0198-verification.json)
  retains the bindings, work counts and per-grid verdicts. The original
  lossless evidence remains in `/Users/agrudin/dev/my/ariadna-evidence/R5.51`
  outside the checkout.
- Source pins, local links, receipt and shard readback, diff and strict
  OpenSpec passed. The implementation is unchanged from R5.50, whose
  31 focused tests, guarded regression (6,217 passed, 494 skipped) and
  Ruff results are recorded in ADR0197. Runtime regression was not
  rerun for this evidence-only update.

## Consequences and revisit conditions

This is a sampled numerical bracket within model B on the pinned
ephemerides and simulated restart. An exact, first or unique physical
crossing, lunar escape, a mission handoff, continuous clearance and
strict M3 remain unverified. Both authorized phases were used once.
Any further live study needs a distinct bounded question.
