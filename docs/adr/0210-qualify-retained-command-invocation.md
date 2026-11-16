# 0210 — Qualify the retained command invocation

- Date: 2026-11-16 (Europe/Samara)
- Decision status: accepted bounded implementation under [ADR0207](0207-design-fixed-command-seed.md).
- Implementation: complete invocation qualified on fabricated archives; retained generation pending.
- Scope: R5.59c only, no physical integration or admission.
- Measured base revision: `ae5f7709940b9d81e21c6eb7087cbd8017367b4c`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-qualify-the-end-to-end-offline-command-invocation), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559c-qualify-the-bounded-invocation-2026-11-16), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[ADR0208](0208-qualify-fixed-command-seed.md) qualified the binary64
and 96-digit worksheet; [ADR0209](0209-qualify-retained-command-archive-adapter.md)
qualified the six archive selectors. Before using the six real saved
inputs, the composition must pass on the same shapes with an
enforced 15 s shared deadline, 512 KiB input and 128 KiB output,
and immutable complete or partial evidence.

## Options considered

- Relabel the retained inputs as an artificial worksheet fixture:
  rejected because it would erase provenance and eligibility.
- Compose the adapter with the pinned arithmetic functions and
  audit the serialized result independently: selected. The
  arithmetic source, physical inputs, tolerances and failed
  attempts remain unchanged.

## Decision and rationale

The [runner](experiments/0210-retained-runner.py) authenticates its
method bytes and reads each allowed archive at most once in an
isolated standard-library worker. Retained mode fixes the input
paths, hashes, event words and the exclusive evidence directory.
Artificial mode uses a different candidate and cannot write to
or authenticate that directory as a retained attempt.

The worker saves an attempt record before opening scientific
inputs, then writes the report, a bound receipt, and a completion
witness with exclusive durable writes. The parent drops a late
witness from its own run while preserving the first partial
evidence. The [readback](experiments/0210-retained-readback.py)
checks recorded signed operands, Cartesian inventory, exclusions,
cost order and exact event and mass ledgers without running the
geometry or reading input archives again. Invalid evidence and
scientific refusal have separate statuses and null commands.

## Evidence and verification

The [tests](../../tests/test_retained_command_runner.py) recover
known signed Moon/Mars geometry and the selected pair from exactly
524,288 input bytes, refusing 524,289 bytes. They verify scientific
and hash failures, independent source-free readback, tamper and
mode mismatch, repeatable science on separate artificial outputs,
an unchanged first output and rejection of a late completion.

All **15 focused tests** passed in 1.34 s. The guarded
regression passed **6,431 tests with 494 skipped** in
144.78 s; the [offline guard](experiments/0189/pytest-offline-guard.py.txt)
excludes native SPICE, retained-science and live UI cases.
Ruff, source hashes and strict OpenSpec passed. The checkout was
held unchanged during the suite. The
[verification manifest](experiments/0210-verification.json) records
the pinned tested sources. No retained input was evaluated.

## Consequences and revisit conditions

The next step is the single already requested retained run. Its
first complete or partial evidence must be kept regardless of
status. An analytic proposal, if any, remains a surrogate seed;
it does not establish lunar-to-Mars physical continuity, target
closure, safety, reserve or R5.60 readiness.
