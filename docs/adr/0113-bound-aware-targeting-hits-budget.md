# 0113 — Retain bound-aware improvement at the Jacobian budget

Date: 2026-10-16
Decision status: accepted (retain evidence, not a successful departure).
Implementation / verification: D16.3 single study complete; independent read-only audit passes.
Scope / milestone: M3 research, one bound-aware local lunar targeting study.
Measured revision: `501516ee52ebef4f85e6d8f4304dc1bc35078270`, clean immediately before invocation.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [0111](0111-bound-aware-local-targeting.md) using verified [0112](0112-bound-aware-targeting-implementation.md), preserving all historical evidence.

## Context and constraints

D15 ended after four corrections with position/velocity errors 3868.62 km /
556.75 m/s. Its uniformly capped Newton directions requested unavailable timing
and fuel. D16 tests bound-aware TRF steps in the same six-control chart and
physical box, starting only from retained 0110 accepted proposal 52. This is a
local Moon-only experiment, not a full-force Moon-to-Mars solution.

## Options considered

- Treat a lower weighted residual, duration at a bound or locally full rank as
  convergence or proof of infeasibility: rejected; none establishes either.
- Add Jacobian batches, change the chart/reserve/target or retry from another
  command: outside this study's frozen contract; not performed.
- Retain the complete budget-limited study and stop for scope review: selected.

## Decision and rationale

Retain [the finite JSON](experiments/0113-bound-aware-local-study.json), SHA256
`417f4a33e6407a37e9a41caff29330557f39d7a3bbfc34e9b908cc1d5589cb89`.
Exactly one `_run_bounded_local_targeting` call used the pinned 0104/0107/0110
inputs. An inline invocation asserted the measured revision, a clean worktree
and an absent output path immediately before launch, recorded UTC timestamps,
and saved with exclusive creation after return. No existing evidence was
overwritten. Runtime, tests, dependencies and native profiles were not changed.

The seed endpoint and mass replay 0110 proposal 52 bit for bit. The study used
38.927206 s including preparation, 262 nominal evaluations and 524 completed
native arcs. Its actual stop is `budget-exhausted`, specifically the attempt to
request a 21st Jacobian after the permitted 20 complete batches. It did not hit
the 300-second deadline, 40-objective-request or 280-nominal-evaluation ceiling.
These limits are independent; spare time/evaluations do not authorize a batch.

| Completed objective | Ignition shift, s | Burn duration, s | Position error, km | Velocity error, m/s | Scaled norm |
|---|---:|---:|---:|---:|---:|
| Seed replay, ID 0; cached objective 1 | -1200.000000 | 5349.046146 | 3868.622724 | 556.746073 | 390847.898419 |
| First update, ID 14 | -989.245178 | 5379.079889 | 1443.733871 | 38.128117 | 144423.725353 |
| Last recorded accepted iterate, ID 249 | -1094.293694 | 5467.045140 | 59.204671 | 246.398370 | 25341.142385 |
| Best eligible objective, ID 262 | -1094.331195 | 5467.045140 | 59.203835 | 246.398570 | 25341.142367 |

The best joint scaled norm decreases 93.5164% relative to the warm start;
position/velocity errors decrease 98.4696% / 55.7431%. Neither error is monotonic
individually: the solver minimizes the combined scaled residual, not each
component separately. ID 262 remains far outside the unchanged 10 m / 0.01 m/s
closure gates. No objective or probe closes. No tighter repeat is authorized;
agreement is `unavailable`, selected objective is null, mission-qualified false.

Best controls are `(-1094.331194805718 s, 5467.045140120176 s,
0.11677321262499005, 0.03939747832675783, -0.6129019118775823,
0.057074175942243816)`; the last four are dimensionless chart slopes, not angles.
Duration reaches the original reserve-derived upper bound. Cutoff/coast mass is
761.147874119494 kg and provisional post-arrival reserve 500.000000000067 kg:
effectively zero margin above the unchanged 500 kg dry-mass gate, not validated
Mars capture or usable operational reserve. Maximum recorded analytic cutoff
mass error is 1.0141e-10 kg; every coast preserves cutoff mass exactly.

### Counters, derivatives and unavailable solver result

There are 263 evidence entries: one fresh replay, 22 objective requests including
one exact initial cache hit, and 240 probes. Thus native evaluations are
1 + 21 + 240 = 262, with two complete arcs each. Twenty Jacobians use 111
central columns and nine inward backward duration columns; no step shrinking,
outside-box penalty, native failure, incomplete batch or retry is recorded.
All twenty measured matrices have rank six, with condition numbers 147.24 to
678.95. These are finite-difference diagnostics, not controllability or accuracy
certificates. The full timing box retains 1756.6359885 s minimum coast.

Twenty recorded accepted iterates include the initial cached objective, hence
19 recorded updates. Objective 92 is rejected before 93 is accepted. ID 262
is the best eligible completed objective but is NOT marked an accepted iterate:
the next Jacobian hits the independent cap before that mark or a SciPy return.
The last measured matrix belongs to ID 249, not ID 262. `solver_result` is null;
there is no returned SciPy termination status, active-mask or final projected
gradient. Do not invent a gtol/xtol success, stationary point or final Jacobian
from this interruption. A flat recent score and an active duration bound alone
do not prove a constrained minimum or nonlinear impossibility.

## Consequences and revisit conditions

D16.3 is complete as one bounded experiment, not as a successful departure.
Bound-aware steps substantially improve the retained joint residual, but the
fixed target remains unclosed. Before any further native work, separately review
the residual trade-off, duration/reserve limit and available steering freedom;
changing the domain, chart, thrust, target or budget requires new explicit scope.
No automatic continuation, alternate seed or second study follows this result.

Moon-point-mass-only dynamics omit Earth/Sun, harmonics, SRP, relativity, outer
matching and Mars propagation. Retained kernel/lunar-resource identity is
provenance, not evidence that those missing forces were included. Native
histories are not retained: endpoint audits cannot independently certify every
interior guard sample, continuous safety, hardware slew or absolute trajectory
error. Strict M3/task 3.9 stay open; automation stays paused. No UI/public API,
dependency or physical-model change is bundled here.

## Evidence and verification

The [read-only audit](experiments/0113-check-bounded-local-targeting.py) passes
independently from saved endpoints and raw residuals, with zero spacecraft
propagations. It checks references/revision/seven source files/environment,
installed versions including Conda SciPy build `py312h4519d97_1`, all 13 kernel
hashes and the retained lunar resource. Independent Rodrigues rotation, 50-digit
Decimal mass, 101 direction-chart samples per command, every residual/closure,
all probe choices/scales/Jacobians/SVD and complete cache/iterate/native counters
pass. Run the audit with the pinned Conda Python, without `-O`.

Focused D16/D15/D14/native/environment regression: 366 tests pass in 3.05 s.
Full-suite evidence is reused from unchanged D16.2: 4,330 tests pass in 604.70 s;
the complete suite is not rerun for this evidence/documentation-only stage.
Strict OpenSpec, Ruff, local links, immutable hashes and whitespace checks pass.
No new runtime implementation is introduced. No independent native dynamics or
interior-history verification is claimed by this offline audit.
