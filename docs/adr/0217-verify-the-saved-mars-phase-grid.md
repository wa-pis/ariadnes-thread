# 0217 — Verify the saved Mars phase grid

- Date: 2026-11-18 (Europe/Samara)
- Decision status: accepted bounded refusal in separate saved-data audit; original invocation remains incomplete.
- Scope: the three immutable [ADR0215](0215-record-retained-phase-readback-failure.md) files for `d0001-t0035`, 360 Mars true anomalies on one oriented ellipse, one original epoch and fixed lunar branch.
- Measured audit revision: `e26b37e4a6b59f545d0fc8d0cca1afbb552de0e3`, clean `dev` synchronized with `origin/dev`.
- Related OpenSpec: [scenario](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-verify-the-saved-grid-after-the-exact-zero-readback-failure), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559f-verify-the-saved-grid-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. The original failure in ADR0215, fixed-target result in [ADR0211](0211-record-fixed-command-seed-refusal.md) and physical contract in [ADR0205](0205-design-fixed-command-physical-join.md) remain valid.

## Context and decision

The original run saved a full grid but emitted no completion witness because its readback rejected the exact zero `0E-569`. Editing the report, widening the decimal exponent rule or replaying the scan would discard that boundary. The separate [ADR0216](0216-design-saved-mars-phase-audit.md) auditor confirmed the arithmetic and decisions in the immutable saved evidence using one in-memory canonical zero and the original numerical gates.

## Evidence and verification

The [saved-data audit](experiments/0217-saved-grid-audit.json) verified the byte hashes, receipt chain, frozen operand digest and **360 states, 720 root slots and 408 pair decisions**. The root disposition was negative: 312 guard, 48 passes; positive: 360 passes. Phase zero reproduced the original dry-floor rejection at **11,661.307589 m/s**. All 408 built pairs fail the exact commanded 500 kg floor; the effective ledger cannot admit a pair that already fails the commanded floor. The two stored arithmetic paths agree on the least-cost built pair: **151°** (positive/positive), **6,157.791272 m/s**, **40.084654 m/s above** the **6,117.706618 m/s** ideal dry-mass budget. The audit confirms `no-eligible-pair-on-grid` with null commands.

The maximum audited state-path differences were **7.589e-09 m** and **2.774e-12 m/s** in the Mars-relative frame and **1.663e-05 m** and **3.776e-12 m/s** in SSB/J2000. All are within the original 0.001 m and 1e-6 m/s gates. The audit read **1,062,560 bytes** of saved evidence under 4 MiB, with a measured readback of **0.089871 s** under 30 s; the original 0.318469 s is time through its receipt only. The three original SHA-256 values match the audit, and no completion witness was created.

The isolated process read only the pinned evidence and method files plus the standard library. It did not reopen ADR0211, run a new phase scan, solve new conics, use SPICE or kernels, evaluate forces, integrate a trajectory or start R5.60. Strict OpenSpec, links, diff and the saved byte checks passed. Runtime sources are unchanged since the ADR0216 qualification; pytest was not repeated.

## Consequences and revisit conditions

The discrete saved grid admits no eligible analytic pair for these exact operands. This result does not cover the continuous set of phases, another arrival geometry, the physical join, or mission feasibility. The original invocation remains incomplete and consumed; no R5.60 or later physical test is authorized by this audit.
