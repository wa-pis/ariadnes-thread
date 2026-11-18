# 0214 — Qualify the retained Mars phase binding

- Date: 2026-11-18 (Europe/Samara)
- Decision status: accepted; the retained attempt is pending.
- Scope: R5.59f preparation under [ADR0212](0212-design-mars-capture-phase-seed.md); all executable qualification uses artificial inputs.
- Measured base: `7416b192d5bf766edb8b5cbeb0f57125591eab43` plus the source hashes in the verification manifest.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-bind-the-retained-phase-screen-to-adr0211-evidence), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559f-qualify-the-retained-binding-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0205](0205-design-fixed-command-physical-join.md), [ADR0211](0211-record-fixed-command-seed-refusal.md) and [ADR0213](0213-qualify-mars-capture-phase-screen.md) retain their scopes.

## Context and options

ADR0213 qualified both arithmetic paths and the entire grid on manufactured data. Running on the saved candidate requires a fixed archive identity and a separately reviewable evidence boundary. Accepting caller supplied retained paths or checksums would let an artificial result substitute for the original refusal.

## Decision and rationale

The [binding](experiments/0214-phase-binding.py) accepts retained mode only with the four exact ADR0211 records (13,363 bytes). It verifies their SHA-256 values, candidate, exact epoch words, original null-command refusal, receipt chain and the frozen scientific operand digest `6b845f74881f658d2eeea28bfdde43c9190a283da5bb166644bb845c4f847c5b`. The old archive was read for byte and operand identity only; that read evaluated no grid. Eight previously qualified method files are pinned. The retained worker uses the same ADR0213 orbital state and conic calculations. It runs in an isolated standard-library Python process, allows at most four named archive opens and writes exclusive, hash-linked records to the fixed new destination. An existing destination refuses dispatch. The same 30 s deadline covers the run, durable output and saved readback, with 128 KiB archive and 4 MiB output caps.

The [separate auditor](experiments/0214-phase-audit.py) reads the saved records, checks all phase and root inventories, reconstructs the state comparisons and checks the signed-root, mass, event and ranking evidence. It does not reopen ADR0211 or solve conics. Invalid, incomplete or late evidence cannot supply commands. Both paths have zero authority for a physical launch.

## Evidence and verification

The [13 focused tests](../../tests/test_retained_phase_binding.py) check two complete artificial grids (360 states and 720 root slots each): one uniquely ranked proposal and one grid without an eligible pair. They exercise a fabricated retained-shaped binding, archive and evidence tampering, mode separation, readback after source removal, an existing destination and a late completion. The [verification manifest](experiments/0214-verification.json) records the tested hashes. Focused tests passed in 2.36 s. The full offline guard passed **6,464 tests** in 143.91 s with **494 skipped** for native, live and retained-science cases. Ruff and strict OpenSpec passed. No SPICE, kernel access, force evaluation or integration was used. The retained attempt and R5.60 were unexecuted in this stage.

## Consequences

One user-authorized retained invocation can now screen this exact archive. A passing result can describe a separate phase-tagged analytic proposal or a refusal limited to this discrete grid. It cannot change the original R5.60 arrival state or establish a physical trajectory.
