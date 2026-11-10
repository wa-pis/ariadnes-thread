# 0179 — Design the split Moon integration recheck

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted design; live execution is not authorized by this record.
Implementation: pending R5.33.
Scientific verification: pending the separately authorized R5.34 study and audit.
Scope / milestone: M3 R5.32; a new model A 300 s numerical check.
Base revision: `974d244eed6b542826553c8eade9b9264ce325a4`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md#r532-integrate-the-split-moon-position-2026-11-10),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none. The completed attempt under ADR0162 is preserved.

## Context and constraints

[R5.17](0164-corrected-coast-force-gate-fails.md) completed both 300 s
profiles and all 21 sampled trajectory comparisons. Its Moon overall
force error at normal RHS ordinal 6 exceeded the unchanged limit by
8.8864%; the force audit was incomplete. [R5.31](0178-consolidate-lunar-force-coverage.md)
now supports both Moon force gates at all 28 frozen observations.
Changing the force fed back to the integrator may change its states,
trial steps and callback epochs. Those 28 checks do not qualify that
feedback or the rest of model A.

## Options considered

- Retain the direct Moon position and rerun the same study: repeats
  the path with the recorded negative.
- Use stored or polynomial positions during the new solve: coverage
  is limited to saved epochs or would change the runtime source. Use
  the records for reference checks only.
- Use measured split position legs for the Moon force while keeping
  direct barycentric velocity for rephasing: tests the specific
  assembly change with the original physical and solver controls.
  Selected for the private A integrator.

## Decision and rationale

At each RHS and shared node use raw Earth/SSB and Moon/Earth position
words at the same rounded epoch. Scale and subtract the decomposed
spacecraft state exactly, add the original signed Moon/SSB velocity
rephasing, then round the relative vector once before computing lunar
acceleration. Keep the Sun force, Earth guard, GMs, initial state,
kernel pool, solver profiles and all original gates from
[ADR0162](0162-corrected-real-integration-contract.md). The extra
Moon/Earth return raises the explicit state-attempt cap from 30,021
to 40,028; the 60 s study, 10 s separate audit and 10,000 RHS caps
remain. There is no new native spacecraft propagation.

First prepare offline (R5.33): prove 28/28 fixed-state replays against
saved measured-route results and test the new path with synthetic
inputs. Then, only after separate authorization, run one new
normal/tighter A study and independent offline audit (R5.34). Require
the original 21 trajectory checks and both force gates for Sun, Moon
and A total on the 28 observations selected from the new run by the
original rule. The archived records check the four source states at
those samples. All-RHS audit checks the arithmetic using returned
operands; it cannot verify provider accuracy between samples.

## Consequences and revisit conditions

Extra source queries and exact assembly cost time; deadline and
convergence feasibility remain unmeasured. If a gate, input, identity
or limit fails, retain the earliest failure and unavailable work.
Any change of sample, source, budget or scientific tolerance would
require a new reviewed design. A pass applies to the new numerical
candidate under the conditional native reference, whose historical
final identity is missing. R5.17 stays failed. Earth-force sensitivity,
continuous safety, M3 and mission readiness remain open. Automation
stays paused.

## Evidence and verification

The [design input manifest](experiments/0179-design-inputs.json) pins
the archived native histories, exact records, prepared helpers and
R5.17/R5.24/R5.27/R5.30/R5.31 evidence. The Moon force seam, operation
counts, unchanged acceptance limits, local links, protected files,
diff and strict OpenSpec were checked by static inspection. No SPICE,
record or force evaluation, solver run or runtime tests in R5.32.
