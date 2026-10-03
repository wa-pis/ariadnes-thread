# 0090 — Measure small directional response with paired profiles

Date: 2026-10-03
Decision status: accepted (D9 diagnostic contract).
Implementation: specification complete; implementation and live study pending.
Scope: M3 research D9; private diagnostic only.
Base revision: `a0d5863`, clean before this specification change.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [0089](0089-local-response-diagnosis.md).

## Context and constraints

The retained direction predicts decrease but three propagated finite steps
worsen the score. Their response combines large cancelling effects and
extrapolates beyond the original probe increments. Determine whether a much
smaller response agrees with that direction under both existing profiles.
Preserve original seed, target, model, reference identity and scientific gates.

## Options considered

- Recompute every Jacobian column at multiple scales: deferred; this costs more
  runs than necessary to test the single direction already shown to disagree.
- Test small signed steps in one profile: insufficient to observe sensitivity
  to the integrator profile for the same perturbed commands.
- Pair two signed scales in both profiles: selected; five distinct commands,
  ten evaluations and thirty arcs provide centered slopes, curvature, scale and
  profile comparisons under one 300-second clock.

## Decision and rationale

Use alpha=(0,+2^-14,-2^-14,+2^-15,-2^-15), independently from the seed.
At the larger scale, departure duration changes by 0.03662109375 s, and every
component is smaller than its original derivative probe increment. At the
smaller scale these changes halve. Binary fractions make these choices exact;
their usefulness still requires measured evidence, not an assumption of accuracy.

For each command run nominal then frozen tighter, in fresh matched environments.
Verify each seed baseline against the corresponding retained profile before
perturbations. Cross-profile baseline disagreement is a measured input to the
diagnosis, not grounds to silently relax either within-profile replay gate.

The design defines centered slopes, curvature and their normalized comparisons
with g=J*(retained_step/trust_scales). Twelve consistency checks use <=0.10;
this exploratory threshold is a chosen diagnostic criterion, not a validated
derivative uncertainty bound. Record vectors and actual discrepancies so a
reader can evaluate them independently of the boolean result.

## Consequences and revisit conditions

Reuse the private preparation, composer, guards and installed dependencies.
Keep a distinct diagnostic budget and preserve D4-D8 behavior. A discrepancy,
zero predicted directional norm or native failure produces explicit evidence;
no command is selected, even if a small perturbation improves the score.
Only one live study follows tested implementation. Any larger budget, new
scale, repeated solve or column-wise study requires a revised bounded contract
after this evidence. Strict M3, safety and mission closure remain unresolved.

## Evidence and verification

This decision uses retained D7/D8 evidence and the read-only audit in ADR 0089.
The specified departure-duration increments follow directly from the retained
-600 s direction component divided by 16384 and 32768.
Strict OpenSpec and diff checks pass. No runtime code changed, no native study
ran and runtime tests were not rerun. D9.2 must pass its arithmetic oracles,
orchestration/native regressions and full suite before D9.3's single experiment.
