# 0244 — Start bounded autonomous preparation without inventing a percentage

Date: 2026-11-24 (Europe/Samara)
Decision status: accepted
Implementation: P5a point-identity unit complete; complete retained dispatcher/qualification pending
Verification: 161 focused / 6998 portable / 412 live passes; Ruff, review and strict OpenSpec pass; CI pending; no retained scientific result
Scope / milestone: independent P5 preparation and scheduling within active M3
Base revision: `7251265ddd22de3dc0e644e4d78392fe4519cb1b`, clean `dev` before this stage
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-use-bounded-scalar-search-only-to-propose-an-analytical-witness), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md)
Supersedes / Superseded by: none; supplements ADR0243 with the latest user instruction, preserving its scientific and one-shot contract

## Context and constraints

After [ADR0243](0243-design-one-retained-bounded-attempt.md), the user requested
continued autonomous research, ponytail working solutions/hypotheses, documentation,
commits and pushes, and automation until approximately 99% accuracy/target match.
They also explicitly required disabling automation on success or any needed
user decision. The latest instruction authorizes useful P5 work, its ordinary
required verification, and conditionally the single unchanged ADR0243 P6 after
full P5 qualification and agreement of the objective. That standing instruction
supplies the later execution authority. The metric choice was the pending decision,
not another run-approval question; it has now been resolved below. It does not authorize a changed scientific
contract or retry. Do not ask again for already authorized routine work.

The original percentage request had no agreed metric or denominator. Analytical command existence,
physical endpoint agreement and probability of mission success are different
claims. The existing endpoint, guard and mass thresholds remain fixed; neither
test-pass counts, agreement of two numerical codes nor errors normalized by huge
SSB/interplanetary distances establish a mission success percentage.

The user answered the choice explicitly: one admissible pair under the existing
strict criteria, with independent audit. The success goal is therefore one
verified analytical witness on the fixed saved real inputs, not a probability
or physical mission closure claim. The original question pause was observed;
automation `ariadna-m3` is now ACTIVE with the same five-minute heartbeat/thread.
The standing instruction already authorizes the unchanged P5-to-P6 path after
full qualification; no additional run-approval question remains for that path.

## Options considered

- Treat 99% as tests passed, optimizer success, arbitrarily normalized residual
  or confidence inferred from a few trials: rejected; it creates a misleading goal.
- Stop all preparation until the percentage is defined: unnecessary; the P5
  identity boundary is required independently of the final scientific objective.
- Initially qualify the smallest isolated P5 unit while the scheduler is paused:
  selected. Preserve the strict scientific gates and stop before dependent work.

## Decision and rationale

Create [0244-phase-points.py](experiments/0244-phase-points.py) as a version of the
completed 0241 point adapter. Only the `_reference` scope/candidate admission
changes: accept exactly the correlated pairs artificial/artificial-moon-mars or
retained/d0001-t0035; reject crossed or unknown identities. Preserve every other
reference validation, numerical operation, literal-command check and independent
point audit. Keep original 0241 bytes unchanged. Source/AST comparison must confirm
the restricted change; do not introduce dynamic scope monkeypatching or a new
scientific implementation.

Use fabricated operands only in the unit tests, explicitly including fabricated
values labelled with the retained identity solely to exercise the identity gate.
Those unit fixtures are not authenticated real inputs or execution authority.
Check both `point` and `audit_point`, output parity, cross-scope refusal and the
unchanged spacecraft/frame/authority checks. No retained dispatcher, profile,
scientific archive binding, search, SPICE or integration is introduced by this unit.
Ordinary required regression tests remain distinct from mission experiments.

The automation prompt uses current state files rather than replaying obsolete
R5.59z instructions. After the user defines the objective, update the same
heartbeat; do not create a duplicate or request already granted routine authority.
Remain within ADR0240/0243 inputs, domain, strict gates and work/time/byte budgets.
P5 must fully qualify before P6; do not consume the saved attempt while preparation
or the objective is unresolved. Once those conditions hold, the latest standing
instruction authorizes the one unchanged P6 without another permission request.
The user's autonomous instruction is not permission
to change a target, formula, input or proof criterion to obtain a desired result.

Each future step has one falsifiable hypothesis, a predeclared limit, the simplest
existing implementation and independent verification. Preserve failed/partial
outcomes and stop, without retries or an automatic diagnostic chain. At agreed
success, a scientific-contract change, missing access/data or a needed user choice,
set the exact automation id `ariadna-m3` to PAUSED and report the concrete reason.

## Consequences and revisit conditions

This unit removes one necessary artificial-only restriction; it does not complete
P5, provide a valid retained profile or admit an executable command pair. The new
point scope/candidate gate cannot replace the fixed four-archive, lineage,
reference/epoch and source/runtime binding still required by the dispatcher.
A witness remains analytical existence only; physical closure and statistical
success claims need their own agreed criteria and independent evidence.

The completion criterion is now resolved and automation is active. Pause it on
an independently audited retained witness, a terminal bounded failure/inconclusive
result requiring another scientific decision, or any necessary user involvement.
Do not promise convergence or label an inconclusive result 99% success.

## Evidence and verification

The [preparation evidence](experiments/0244-preparation.json) binds the new point
and test sources, immutable original source and separate logs. New identity unit:
33 synthetic cases pass; combined P3/P5a focused lane:161 pass. Full portable:
6998 pass/42 exact historical-environment skips; live:412 pass. The two full lanes
have7452 unique disjoint case IDs,7410 passes and42 archive skips. Every one of
1347 Git-visible files, HEAD and status stayed unchanged through both lanes;
all1043 previous non-Markdown files remain byte-identical. Ruff, independent
review and strict OpenSpec pass. CI is pending at this recording stage.

The unit's scientific arithmetic and independent audit match the original source
under restricted AST comparison and fabricated parity checks. These checks do not
qualify the missing retained dispatcher/profile. Ordinary live regression loaded
SPICE/native resources; no new retained P3 search or mission experiment occurred.
The active automation prompt records the selected analytical goal and stops on
a terminal outcome or needed user decision. No physical or99%probability result
is claimed.
