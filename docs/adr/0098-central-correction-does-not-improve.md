# 0098 — Retain the unsuccessful central correction

Date: 2026-10-04
Decision status: accepted (retain negative evidence, not a qualified correction).
Implementation / verification: D11.3 complete; nominal trial does not improve.
Scope / milestone: one M3 research study; evidence and documentation only.
Measured revision: `b6d4513`, locally committed; push blocked pending destination approval.
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
Supersedes / Superseded by: none; completes [0096](0096-single-central-correction-contract.md) and [0097](0097-central-correction-implementation.md).

## Context and constraints

D10's central matrix agreed with small measured changes along the old direction.
That does not guarantee agreement for a new direction or a full capped step.
D11 tests one such correction without new probes, iterative solves or retries.

## Options considered

- Select the correction from its linear prediction: rejected; native evidence
  contradicts the predicted improvement.
- Immediately add smaller steps or iterations: deferred; outside this study's
  accepted one-trial scope.
- Preserve the failed trial and stop: selected; keeps empirical evidence and
  scientific limitations explicit.

## Decision and rationale

Retain [finite evidence](experiments/0098-central-correction-study.json), SHA256
`b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057`.
One invocation completed **2 controls, 2 nominal evaluations and 6 native arcs
in 5.585132209 s**, under the 300-second/nine-arc cap. The fresh baseline's four
boundaries and masses replay exactly against 0079 and 0095. A single rank-six
solve used the reconstructed central matrix and rcond=1e-12. The cap divisor is
118.21292074520588, with physical step (rad, rad, s, rad, rad, s):

`(0.022012600962900038, -0.134358343400506, -600.0, 0.12860841045380733, 0.05855471774691064, -64.16958848195155)`.

| Quantity | Baseline | One central trial |
|---|---:|---:|
| Position miss, m | 197851062193.60904 | 244257638670.8264 |
| Velocity miss, m/s | 31160.14668810916 | 40440.44292042029 |
| Scaled residual score | 197875598.18874988 | 244291113.9261598 |

The linear predicted score ratio is **0.9915406878** (about 0.85% improvement),
but the measured ratio is **1.2345691746** (about 23.46% worse). Neither closure
gate passes. No command was selected; no tighter repeat was launched. Numerical
agreement is therefore unavailable, not false and not assumed. No retry,
additional fraction, derivative probe or second solve occurred.

Invocation from the repository root in the pinned Conda environment:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment \
  examples/m3_feasible_mission.toml \
  docs/adr/experiments/0079-research-reference.json \
  docs/adr/experiments/0098-central-correction-study.json \
  --central-reference docs/adr/experiments/0095-central-column-study.json
```

## Consequences and revisit conditions

D11's bounded question is answered negatively. Good local directional agreement
does not justify the full correction; this study does not isolate whether the
failure comes from finite-step nonlinearity, other matrix directions, or both.
Strict M3/task 3.9 remain open. No accuracy, safety or mission qualification.
Any further research requires a separately justified scope; no automatic extra
study. UI unchanged and automation remains paused.

## Evidence and verification

Independent `numpy.linalg.solve` checks the retained matrix, solution, rank,
cap, unit conversion and prediction. Raw terminal-minus-target residuals,
scores, command sum, exact replays, reference/current-source hashes, historical
source separation, counters and finite JSON were checked without native reruns.
The implementation stage passed 236 focused / 3,896 full tests (596.41 s).
This evidence-only stage reuses that full suite; no runtime code changed.
Focused D11 tests, Ruff, strict OpenSpec, local links and legacy checksum pass.
Local commits are retained; external push needs explicit destination approval.
