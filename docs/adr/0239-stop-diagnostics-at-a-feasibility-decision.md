# 0239 — Stop diagnostics at one feasibility decision

Date: 2026-11-22 (Europe/Samara)
Decision status: accepted
Implementation: planning complete; no new numerical method or execution prepared
Verification: document and scope checks only; no new scientific result
Scope / milestone: next research outcome within the sole active M3 change
Base revision: `e2b82fed61d3795cbe90e5a20a97cc3eaff51086`, clean `dev` before this documentation stage
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-stop-diagnostics-at-one-terminal-feasibility-decision), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md)
Supersedes / Superseded by: none; changes scheduling, not historical scientific contracts

## Context and constraints

The useful goal remains one independently checked research trajectory/export,
as in [ADR0117](0117-mission-first-demonstration-priority.md). Passing tests or
explaining another arithmetic stage does not supply a physical trajectory.
The test/CI repair on the base revision is complete, including successful
[Ubuntu CI](https://github.com/wa-pis/ariadnes-thread/actions/runs/45016544787).
It neither closes M3 nor verifies the 42 explicitly archival checks.

[ADR0217](0217-verify-the-saved-mars-phase-grid.md) rejects all 360 saved samples;
the best built pair is 40.084654 m/s above its ideal dry-mass budget.
[ADR0221](0221-record-retained-inter-node-result.md) leaves 64 unresolved cells
on [150 degrees, 152 degrees]. [ADR0238](0238-record-versioned-saved-norms.md)
finds equal final local enclosures on all 72 identical saved boxes. These facts
do not establish a dominant cause, a continuous refusal, or eligible commands.
No new numerical inference is made in this decision.

## Options considered

- Continue tracing or replacing individual norm operations: no demonstrated
  path from the last local result to a mission decision; not the next priority.
- Increase depth, widen phases or rerun a consumed study: changes the approved
  question/work, and is not authorized by this planning stage.
- Require one terminal feasibility outcome before more physical work: selected.
  It makes a negative or inconclusive result useful without promising success.

## Decision and rationale

The next scientific objective is one independently checked feasibility decision
for the existing ADR0218 analytical family: candidate `d0001-t0035`, the closed
Mars true-anomaly domain [150 degrees, 152 degrees], both signed Mars roots,
the fixed positive lunar branch, original epochs and remaining frozen inputs.
Reuse [ADR0218](0218-design-inter-node-mars-phase-check.md) for point gates,
continuous coverage, binary64 duration conversion and both exact 500 kg ledgers.
Do not replace those checks with the displayed ideal delta-v budget.

The complete deliverable must end in exactly one of these conclusions:

| Conclusion | Required evidence and its limit |
| --- | --- |
| Verified analytical witness | One phase/sign passes every original point gate by the independent path. This is existence in the surrogate, not an executable command selection or global optimum. |
| Verified local refusal | An independently checked, gap-free certificate excludes both signs over the whole closed domain, including boundaries. This says nothing about the rest of the orbit or physical infeasibility. |
| Inconclusive / invalid | Missing proof, disagreement, uncovered cells, failed admission or exhausted limits. Preserve the reason and stop; do not turn absence of a witness into refusal. |

Existing evidence currently supports only the unresolved continuous question.
Do not run another study merely to restate that conclusion. Before implementation,
a single reviewed method contract must identify a materially different, justified
route to a witness or certificate, its independent verifier, exact source/input
pins and counted work. A method explanation or stage-width reduction alone is
not the acceptance result. This decision chooses no new formula and provides no
implementation-ready algorithm or authorization to evaluate retained operands.

Keep the ADR0218 domain and ceilings as the outer envelope: depth 5, 126 cells,
252 signed bounds and 129 direct phases per path; 30 s through durable producer
finalization/readback and 30 s for the separate audit, at most 4 MiB pinned input
per reader and 4 MiB combined new evidence. A future method contract must charge
all additional work, justify it with full-volume artificial qualification and
stay within these ceilings. Qualification must use the current required portable
and live test lanes, Ruff and strict OpenSpec; archival skips remain unverified.
If no complete method fits, report unavailable instead of creating more default
diagnostic tasks or raising a limit. Nothing is launched by these ceiling values.

After any terminal result, automatic continuation stops. A positive witness
changes the Mars target six-state and cannot enter the original R5.60.
[ADR0205](0205-design-fixed-command-physical-join.md) and
[ADR0207](0207-design-fixed-command-seed.md) still require a separately accepted
boundary/command selection, immutable proposal, full-model resources/coverage,
qualified reverse/reference solvers, justified endpoint error bounds, effective
mass/event handling and enforceable work/timing evidence before physical work.
No full-force join, target closure, reserve, continuous safety or strict M3 claim
follows from the analytical decision. Scientific implementation and any saved
execution each need their own explicit instruction under a complete contract.

## Consequences and revisit conditions

Stop the automatic R5.59 diagnostic chain; do not add speculative successor
adapters, outputs, optimizers or experiments. Keep Python/TudatPy/SPICE/Streamlit,
all original scenarios, tolerances, kernels, records and `moon_to_mars.py`.
Automation stays PAUSED and R5.60 unavailable. This is a prerequisite toward the
trajectory goal, not delivery of that goal. If a later result remains inconclusive,
choose a different mission formulation or proof approach explicitly; it does not
justify another automatic diagnostic branch.

## Evidence and verification

Reviewed the named retained decisions and active requirements without importing
scientific modules or reading numerical evidence through its producers/auditors.
Independent scope review confirms the local-domain and changed-target limits.
Local links, changed-document facts, whitespace, strict OpenSpec and the
documentation-only diff pass. Runtime code/tests/dependencies and old evidence
are unchanged; local pytest/Ruff are not rerun for this planning-only stage.
The existing CI workflow is unchanged; this record launches no research study.
