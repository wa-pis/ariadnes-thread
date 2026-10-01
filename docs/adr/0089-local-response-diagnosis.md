# 0089 — Diagnose the local model before further targeting

Date: 2026-10-02
Decision status: accepted (read-only diagnosis and next-study recommendation).
Implementation: diagnosis complete; no correction or new propagation implemented.
Scope: M3 research D7/D8 response at candidate d0001-t0035.
Base revision: `4d7342e`, clean before diagnosis.
Related OpenSpec: [research contract](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
Supersedes / Superseded by: none; interprets [0088](0088-damping-does-not-improve.md).

## Context and constraints

Three retained trials worsen the score. Determine whether the empirical linear
model itself predicts worsening, or whether propagation disagrees with its
prediction. Use retained [D7](experiments/0086-targeting-study.json) and
[D8](experiments/0088-damping-study.json) only; no additional native invocation.

## Options considered

- Reverse the step or loosen acceptance: rejected; no sign error or threshold
  defect is demonstrated by the retained data.
- Continue reducing alpha blindly: deferred; first measure local model validity.
- Audit the retained Jacobian and compare predictions with observations: selected.

## Decision and rationale

Residuals use propagated-minus-target, ordered position then velocity, in SI.
The solve uses the negative scaled residual. The six columns use departure then
arrival azimuth/elevation/duration, consistent with command validation and the
composer. Angles are radians and durations seconds. All six retained probe
increments and scaled Jacobian columns reproduce their specified construction;
targets are unchanged across D7 runs. No sign, unit or column-order defect was
found in this path. This does not validate the physical derivative accuracy.

Let r be the scaled baseline residual, J the retained dimensionless Jacobian,
T=(0.25,0.25,600,0.25,0.25,600) the trust scales, and z=dx/T. Reconstruct the
uncapped solution independently using numpy.linalg.solve(J,-r), rather than
the implementation's least-squares call. Its relative equation defect is
6.30e-15; its infinity norm is 140.0987285236. Dividing by that norm reproduces
the retained physical step within 2.1e-12 per component (rad or s).
Thus the capped linear prediction is r+alpha*J*z, with a score ratio of
approximately 1-alpha/140.0987285236.

| alpha | Predicted score/baseline | Observed score/baseline | Cosine of predicted/observed residual change |
|---|---:|---:|---:|
| 1 | 0.9928621765 | 1.2383658717 | -0.7737064471 |
| 0.5 | 0.9964310882 | 1.0500665022 | -0.9511128720 |
| 0.25 | 0.9982155441 | 1.0149164752 | -0.8190980627 |

These cosines concern six scaled residual components, not thrust directions.
The nominal nonlinear response contradicts the retained model's predicted decrease.
At alpha=0.25, the model error norm is 3885095.3672, versus predicted change
norm 353100.2748; all these norms are dimensionless under the residual scales.

Individual full-step column contributions have summed norms 309954882.9593,
while their vector sum has norm 1412401.0994: cancellation by about a factor
219.45. Small relative errors in the large contributions can dominate the net
predicted decrease. This is a sensitivity observation, not a quantified error bound.

Full-step changes are 2437/13508/600 probe increments for departure and
12789/5698/51 for arrival, in absolute value. Even alpha=0.25 changes departure
duration by 150 s versus the 1 s derivative probe. Arrival angle probes change
terminal position by only 17.15/17.72 m. These are reasons to investigate
derivative stability and nonlinear response, not evidence that either is the
unique cause. Earlier coast-profile differences cannot be used as a derivative
noise bound for these separately perturbed runs.

## Consequences and revisit conditions

Do not reverse signs or tune acceptance from this diagnosis. Before further
optimization, specify a bounded local-response study: preserve seed, model,
target and reference binding; compare directional prediction with small positive
and negative perturbations at two scales; measure derivative consistency and
nominal/tighter response uncertainty. Define scale choices, command/event stops,
shared deadline, arc cap and measurable model-agreement criteria in OpenSpec
before execution. This is a recommendation, not an implemented D9 experiment.
Strict M3, target closure and safety remain unresolved.

## Evidence and verification

Readback reconstructed six Jacobian columns, probe control differences, fixed
targets, the solve/cap, predicted scores and signed observed response. No retained
artifact was modified and no native propagation ran. The calculation uses existing
NumPy and the formulas above; no new library or optimizer was introduced.
15 focused correction tests pass in 0.07 s; strict OpenSpec and diff checks pass.
The full suite was not rerun for this documentation stage; runtime code is unchanged.
