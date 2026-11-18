# 0216 — Qualify the saved Mars phase audit

- Date: 2026-11-18 (Europe/Samara)
- Decision status: accepted; artificial qualification complete, saved-grid verification pending.
- Scope: read-only audit of the three original R5.59f records.
- Measured base: `1790bd171651a0abdacaf31d15c5774a77142af2`.
- Related OpenSpec: [scenario](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-verify-the-saved-grid-after-the-exact-zero-readback-failure), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559f-qualify-the-saved-exact-zero-audit-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0215](0215-record-retained-phase-readback-failure.md) remains the record of the incomplete execution.

## Context and options

The original attempt saved the whole grid but its reader rejected a far-exponent representation of the exact numerical zero. Changing the general decimal parser would change the historical method; modifying the report would break its byte identity. Replaying the grid would consume another attempt. A separate state view can make the stored zero readable without any of those changes.

## Decision

The [saved auditor](experiments/0216-saved-phase-readback.py) requires the three exact file hashes, original receipt chain, frozen scientific operands and exact historical method identities. It accepts absence of the completion witness as part of this evidence type. Only the exact stored word `0E-569`, at phase 0° and independent Mars-relative velocity X, is presented as decimal `0` to the unchanged state comparison. All other values and the original decimal parser, science, ranking and event gates remain unchanged. The process isolates standard-library imports and permits only named evidence and method reads. It has a 30 s deadline and 4 MiB bound for saved evidence. There is no archive reopen, phase scan, conic solve, SPICE, propagation or physical authorization.

## Evidence and verification

[Focused tests](../../tests/test_saved_phase_readback.py) protect the data and the exact coordinate/word scope and check a full fabricated saved grid. All **11 focused tests** passed in 0.72 s. The offline regression passed **6,475 tests** in 134.20 s with **494 skipped** for native, live and retained-science cases. Ruff and strict OpenSpec passed. [Verification manifest](experiments/0216-verification.json) binds the measured files. The original saved grid was not audited in this qualification stage.

## Consequences

A separate verified result may confirm or reject the saved analytic disposition. It cannot create the missing completion witness or satisfy physical readiness. The original R5.59f invocation must not be replayed and R5.60 remains unavailable.
