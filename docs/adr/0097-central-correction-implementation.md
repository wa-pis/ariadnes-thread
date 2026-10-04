# 0097 — Implement the bounded central correction

Date: 2026-10-04
Decision status: accepted.
Implementation / verification: D11.2 complete; live D11.3 study pending.
Scope / milestone: M3 research D11.2, not production targeting.
Base revision: `63150b76adcacfa52f8118f3b12dd1a53dc93744`.
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
Supersedes / Superseded by: none; implements [0096](0096-single-central-correction-contract.md).

## Context and constraints

D10 retained six central columns at the prescribed seed. D11 needs one
correction without recomputing those columns or introducing iterative targeting.
Keep historical evidence immutable and enforce the accepted 2-control,
3-evaluation, 9-arc, 300-second contract and unchanged scientific gates.

## Options considered

- Duplicate D7's least-squares/cap arithmetic: rejected; risks divergent units
  and behavior between research modes.
- Add a general optimizer: deferred; no iteration is authorized.
- Share the existing matrix solve and reuse the composer: selected; retains
  D7 outputs while adding D11-only prediction and stopping guards.

## Decision and rationale

The private `--central-reference` mode verifies pinned 0079/0095 identities and
reconstructs columns from raw endpoints before native work. It replays the
baseline against both records, solves once, records capped/uncapped values and
linear predictions, then evaluates one seed-plus-step command. Only an
improving nominal trial gets one frozen-command tighter repeat in a fresh
environment. Improvement and numerical agreement remain separate, including
when tighter propagation fails. Existing analytic/native guards and the shared
clock stop failures without retries. No dependency or public API was added.

## Consequences and revisit conditions

This implementation enables one experiment, not a qualified mission. Individual
columns, finite-step model accuracy and whole-interval safety remain unproved.
Strict M3/task 3.9 stay open. No UI change or automation restart. Any subsequent
research must be justified by the separately retained D11.3 evidence.

## Evidence and verification

Independent coupled-matrix tests use `numpy.linalg.solve`, not the implementation's
least-squares routine, to check sign, control order, SI scaling, cap and prediction.
Injected cases cover rank loss, zero/no-decrease steps, nonfinite inputs, closed
baseline, reference reconstruction, trial rejection, conditional tighter behavior,
failure retention, exclusive CLI and counters. Shared native guards are exercised.
236 focused D7–D11/composer tests pass in 5.19 s; Ruff, strict OpenSpec, diff and
unchanged legacy checksum pass. Full suite: 3,896 tests pass in 596.41 s.
No live D11 study was run in this implementation stage.
