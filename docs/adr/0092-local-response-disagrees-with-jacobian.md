# 0092 — Retain local response disagreement without selecting a maneuver

Date: 2026-10-04
Decision status: accepted (retain diagnostic evidence; not derivative qualification).
Implementation / verification: D9.3 complete; overall consistency failed.
Scope: one M3 research local directional-response study; evidence and documentation only.
Measured revision: `1db47066f52d04d07292134370728fff606c9d43`, clean before execution.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; completes the study specified in [0090](0090-local-response-study-contract.md) and implemented in [0091](0091-local-response-implementation.md).

## Context and constraints

The retained D7 Jacobian predicted improvement, but D7/D8 finite steps worsened
the score. D9 tests much smaller signed changes in that same direction, at two
scales and with both existing integration profiles. The study is diagnostic:
its 0.10 threshold is exploratory, not a derivative uncertainty or accuracy bound.
The original candidate, seed, target, model, resources and strict M3 gates remain.

## Options considered

- Select a small positive perturbation because its endpoint miss decreases:
  rejected; the accepted contract forbids selection and consistency fails.
- Repeat runs, add scales or recompute Jacobian columns immediately: deferred;
  this exceeds the single bounded study and needs a new scoped contract.
- Preserve all results and isolate the observed model disagreement: selected;
  it completes D9 without treating a failed scientific criterion as success.

## Decision and rationale

Retain [the finite JSON evidence](experiments/0092-local-response-study.json).
The one invocation completed five controls, ten paired evaluations and thirty
native arcs in **95.750778209 s**, under the shared 300-second limit. There were
no retries, new correction solve, selected alpha or production setting changes.
All four boundaries and masses replay exactly against both retained nominal
references and the retained tighter reference. Cross-profile baseline position
disagreement remains 1751.286621 m; it is not a within-profile replay failure.

Eight of twelve consistency checks pass. All four comparisons with the retained
Jacobian fail; curvature, scale and profile comparisons all pass. Values below
are discrepancy norms divided by the predicted directional norm G, not percent
errors in physical endpoint position. G = 1412401.0993820347 in scaled residual
coordinates (1000 m position and 0.01 m/s velocity scales).

| Check | Nominal, alpha=2^-14 | Nominal, alpha=2^-15 | Tighter, alpha=2^-14 | Tighter, alpha=2^-15 |
|---|---:|---:|---:|---:|
| Model: norm(D-g)/G | 0.310219 | 0.302750 | 0.312391 | 0.309232 |
| Curvature: norm(C)/G | 0.025331 | 0.047539 | 0.005557 | 0.005426 |

Scale discrepancy is 0.007875 nominal and 0.003326 tighter. Profile discrepancy
is 0.002286 at 2^-14 and 0.006835 at 2^-15. All use the unchanged <=0.10 criterion.

Small positive commands reduce nominal position miss by approximately 70.914 km
and 36.558 km respectively, from a baseline miss of **197.851 million km**.
These are observations, not mission closure or an accepted corrective command.
The evidence supports disagreement between the retained local model and measured
directional response at these two scales. It does not uniquely establish its
cause, a trustworthy new Jacobian, convergence or an absolute error bound.

## Consequences and revisit conditions

D9 is complete as a bounded diagnostic, with failed overall consistency.
Strict M3 and task 3.9 remain open; continuous safety is not verified. The UI,
force model and optimizer are unchanged, and automation remains paused.
Before another native study, agree a bounded next question: how to obtain a
reliable local sensitivity model without expanding into an unrestricted research
loop. Column-wise derivative checks or a revised targeting approach are options,
not authorized implementations. Do not repeat D9 automatically.

## Evidence and verification

Invocation from the repository root in the pinned Conda environment:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment \
  examples/m3_feasible_mission.toml \
  docs/adr/experiments/0079-research-reference.json \
  docs/adr/experiments/0092-local-response-study.json \
  --response-reference docs/adr/experiments/0086-targeting-study.json
```

Exit code 0 means the diagnostic completed, not that its consistency passed.
Evidence SHA256: `164760a35451b3e8cf43bf2213e8466a331dbcb85004249e134e9daefa1a7374`.
The native runtime emitted a TudatPy mass-rate API deprecation warning; no runtime
or dependency change was made in this evidence-only stage.

45 focused response tests pass in 0.16 s. Independent inline verification using
JSON, hashlib, NumPy and math (without importing diagnostic implementation)
checks finite serialization, both pinned reference hashes, every current source
hash, historical source identity, scenario/candidate/resources/runtime binding,
all ten seed-based commands, frozen paired settings and target, raw SI residuals,
scores, exact baseline states/masses, direction, predictions, central slopes,
curvature, all twelve vectors/ratios/booleans and overall consistency. Independent
NumPy matrix multiplication agrees with recorded g within 1e-7 absolute scaled
units; centered formulas and stored check vectors agree exactly. It also checks
5/10/30 counters, the deadline, absence of selection/solve/retry and the unchanged
legacy checksum. Previous evidence files remain untouched.

Ruff, strict OpenSpec, local documentation links and diff checks pass. The full
suite was not rerun: this stage changes no runtime code and reuses D9.2's 3,784
passing tests in 598.42 s. Scientific consistency and strict M3 remain unqualified.
