# 0194 — Prepare the short lunar range extension

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted preparation within [ADR0193](0193-design-lunar-range-extension.md).
- Implementation: R5.47 complete; R5.48 unexecuted.
- Verification: artificial source/engine fixtures and independent offline audit passed.
- Scope: the private model B 50 s restart and prospective lunar range marker.
- Base revision: `72e5b989742f387531d2e1da853a14ed481945aa`; exact tested sources in the manifest.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-a-prospective-lunar-range-marker), [design](../../openspec/changes/refine-physical-trajectory/design.md#r547-prepare-the-prospective-lunar-range-extension-2026-11-14), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

The new interval and state are already fixed by ADR0193. The old
600 s reports and scripts remain immutable. Preparation binds the
exact archived restart to the retained node and native history,
keeping model B, mass and source identities, prior force/comparison
gates and the 50 s fixed grid. Archive and kernel coverage checks
use stored reports and metadata only.

## Options considered

- Patch constants in old experiment scripts: would invalidate
  historical bindings and risk audit/study sharing changed policy.
- Reuse their readback, force and clock primitives through new
  private fixed-duration paths and an independent saved-data audit:
  selected. The native adapter already accepts the explicit step and
  duration; the adaptive control and replay use the short fixed grid.

## Decision and rationale

The artificial outward case passes 33 state comparisons, 36
adaptive force/source observations, 22 native telemetry rows, 44
common and 152 native mesh direction rows and 462 explicit native
guard reads. The fixture's common bracket is +30–35 s after restart;
the two native brackets overlap at +31–31.5 s. The inward and
exact-equality fixtures pass the numerical checks while returning
`marker-not-established`. An invalid or incomplete result returns
`unavailable` and keeps the earliest available failure.

The stdlib audit reads saved operands in a fresh isolated process.
It independently rebuilds the geometry and signs, and checks native
histories, adaptive RHS and trial work, sample arithmetic, gate
results, counters and provenance. A parent watchdog limits each
future phase. Exclusive markers prevent replay in the same evidence
directory; bound receipts and late-flush records prevent false
acceptance. The audit does not start native work.

## Evidence and verification

The [manifest](experiments/0194-verification.json) binds the tested
files and design. 21 focused checks passed, including
bad handoff/metadata, corrupted operands and receipt chains, guard
or telemetry failure, exact equality, and the phase deadlines.
The guarded full suite reported 6,186 passed, 494 skipped. Ruff, strict
OpenSpec, links, diff, source hashes and the frozen test-tree check
passed. The [offline guard](experiments/0189/pytest-offline-guard.py.txt)
blocked SPICE imports/loads and excluded live regressions.

## Consequences and revisit conditions

Preparation does not determine the real marker verdict. R5.48 still
needs separate authorization for one 60 s study and one 10 s offline
audit; no new SPICE queries, real force/record evaluations or real
propagation were performed. There is no physical escape, mission
handoff, safety, full-force accuracy or strict M3 claim.
