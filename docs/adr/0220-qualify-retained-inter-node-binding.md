# 0220 — Qualify the retained inter-node binding

- Date: 2026-11-18 (Europe/Samara)
- Decision status: accepted preparation; retained execution requires separate authorization.
- Implementation: pinned archive adapter, historical anchor comparison, isolated, bounded invocation and saved-certificate audit. Verification used artificial evidence only.
- Scope: [ADR0218](0218-design-inter-node-mars-phase-check.md), [150°, 152°], candidate `d0001-t0035` for the future retained invocation.
- Measured base: `1558717a924f5925c1bc9a4bcb4e75ab67f09966` plus the tested source hashes in the [verification manifest](experiments/0220-verification.json).
- Related OpenSpec: [scenario](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-qualify-the-retained-archive-binding), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559i-qualify-the-retained-inter-node-binding-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0215](0215-record-retained-phase-readback-failure.md), [ADR0217](0217-verify-the-saved-mars-phase-grid.md), [ADR0219](0219-qualify-inter-node-mars-phase-check.md) and [ADR0205](0205-design-fixed-command-physical-join.md) keep their scopes.

## Context and options

ADR0219 exercised the interval method on fabricated operands. A retained invocation needs to prove that its operating conditions come from the exact archived reference. Caller-supplied retained filenames or re-pinning changed evidence would allow a quietly changed scientific question. Repeating the original 360-point screen would spend unnecessary work and conflict with the consumed-attempt boundary.

## Decision

The [invocation](experiments/0220-phase-invocation.py) pins the three ADR0215 files and the ADR0217 audit, the qualified numerical methods, and the two new loaders. The [archive adapter](experiments/0220-phase-archive.py) checks the original attempt, report and receipt chain, the separate audit's source and method lineage, exact epochs, spacecraft, counters, and digest of the frozen operands. Original grid inventory and rank metadata are checked from the saved rows. No new 360-point scan or original completion witness is involved. Only the frozen reference and the saved 150°, 151° and 152° rows go into the local study.

The [anchor comparator](experiments/0220-phase-anchors.py) requires the original angle words, state and signed-root agreement to the unchanged SI tolerances, ordered pair inventory and commanded dry-floor decisions. The numerical point, bounds, bisection and coverage logic remain the exact ADR0219 code. A separate artificial profile cannot use retained paths or hashes and reports zero retained attempts. The fixed retained destination is `experiments/0221-r559i`; an existing directory blocks a new dispatch. Limits remain 30 s through durable output and readback, 4 MiB archive per reader, 4 MiB new evidence and unchanged ADR0218 work counters. Certificate replay authenticates the same four inputs and uses the pinned local checker. No commands are admitted.

After separate authorization the single retained entry is `conda run --no-capture-output -n space-nav python -I -S -B docs/adr/experiments/0220-phase-invocation.py retained`. A separate saved audit takes the externally captured completion digest through the same script's `audit` entry. A missing or late completion cannot yield verified success.

## Evidence and verification

The fabricated refusal archived 1,038,821 input bytes and wrote 19,423 evidence bytes. The guarded invocation reached the saved certificate in 209.3 ms; a separate readback took 120.2 ms. It verified all 4 terminal cells on [150°, 152°] (6 evaluated cells, 12 signed bounds and 5 direct phases) with zero unresolved cells. These are synthetic measurements; they give no result for the retained candidate.

The [tests](../../tests/test_retained_inter_node_binding.py) use fabricated archival files, including a full synthetic upstream refusal and separate synthetic readback. They check cross-file provenance beyond the SHA-256 comparison, anchor identity, artificial/retained separation, byte limits, output reuse and late completion. Focused pytest: 9 passed. Full suite with native SPICE blocked: 6495 passed, 494 skipped. Ruff and strict OpenSpec passed. No retained phase evaluation, SPICE query, force evaluation, propagation or R5.60 run took place.

## Consequences and revisit conditions

Preparation does not answer the 40.085 m/s question for the retained candidate. One separately authorized local attempt may use only the pinned archive and unchanged interval. An unresolved proof remains inconclusive. No outcome from this adapter can establish physical continuity or authorize R5.60.
