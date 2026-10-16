# 0111 — Diagnose capped corrections and design bound-aware targeting

Date: 2026-10-16
Decision status: accepted
Implementation: D16.1 diagnosis/design complete; D16.2 subsequently verified in [0112](0112-bound-aware-targeting-implementation.md); D16.3 native study pending.
Scope / milestone: M3 research D16, same local lunar departure boundary problem.
Base revision: `74dbeb15c93060e0cd7ccfbbc8e770c5c6d2f144`, clean before this documentation/analysis stage.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; adds a separate follow-up to [0108](0108-bounded-local-steering-targeting.md)/[0110](0110-local-steering-improves-without-closure.md), preserving their contracts and evidence.

## Context and constraints

The objective is still the fixed six-state target at the fixed absolute epoch,
not a smaller score or a successful optimizer status. D15 completed its four
permitted corrections, reducing position/velocity error to 3868.62 km / 556.75 m/s.
This stage diagnoses its saved algebra and specifies a next attempt. No new
spacecraft propagation, fifth D15 correction or nonlinear targeting run is made.

### Observations, not a reachability proof

Retain [the offline diagnosis](experiments/0111-local-targeting-diagnosis.json),
SHA256 `b48c627f98efedc0e11f50a5eecc5db87cbb2099ab51bd00c354e4c527cb39f1`.
It binds immutable 0110 SHA256
`678287cc7aee2b3d83e89c9fbff1113a96d24c5b8960f047aeadb82d049c4274`.

- The actual stop was the four-iteration cap: no timeout, failed propagation,
  rejected trial, rank failure or tighter-profile failure occurred.
- Every unconstrained Newton command violates BOTH the ignition and duration
  bounds. Raw ignition shifts range from -2490.02 to -4939.47 s, outside
  +/-1766.86 s. Raw durations range from 6571.87 to 8830.96 s, above 5467.05 s.
  A full Newton step is therefore not an admissible answer, even in its linear model.
- Dividing the entire Newton vector by 8.30–13.46 makes all four ignition changes
  exactly -300 s and suppresses the steering changes together with timing. It
  preserves the unconstrained direction; it does not minimize residual inside
  the available control box. Step scales were exploratory choices, not hardware limits.
- Rank-six matrices have condition numbers 178–380. Actual/predicted squared
  cost-reduction ratios are 0.732, 0.812, 0.925 and 1.114. Maximum probe
  even/odd ratios are 0.000863–0.001142. These observations do not indicate a
  gross sign error or failed local response, but do not bound derivative error
  or prove that a much larger nonlinear step works.
- Final duration margin is 117.998995 s and provisional arrival reserve margin
  17.564916 kg; ignition margin to its lower bound is 566.864931 s. Continuing
  the same capped direction is likely to become bound-limited. The Jacobian at
  the final accepted ID 52 was NOT measured; the last matrix belongs to ID 39.

For a controlled comparison, minimize the saved *linear* residual inside both
the original physical box and the same component-wise step box abs(z)<=1.
At each measured parent this beats uniform scaling of the Newton vector:

| Parent ID | D15 predicted score | Box-fit predicted score |
|---|---:|---:|
| 0 | 490359.16 | 294386.66 |
| 13 | 454677.08 | 206288.91 |
| 26 | 422926.08 | 114215.52 |
| 39 | 394619.56 | 41674.67 |

The last box-fit command shifts ignition from -900 to -600 s, in the opposite
direction to D15's -1200 s trial, while changing steering. Its predicted errors
are still 320.72 km / 266.11 m/s, not closure. With the full physical box the
last linear fit reaches the duration ceiling and still predicts 42.06 km /
219.18 m/s. Neither fit was applied to native dynamics. These are conditional
linear minima, NOT lower bounds on the nonlinear problem or usable burn commands.
They motivate solving with bounds, not removing the fuel reserve or declaring
the six-control chart physically infeasible.

## Options considered

- Add more D15 iterations or enlarge its uniform step: does not address the
  constrained direction; the raw solves already request unavailable timing/fuel.
- Relax fuel/dates/target time, increase thrust or add steering nodes/multiple
  burns: would change the physical question before testing the existing domain.
  Defer until a bounded constrained attempt supplies evidence.
- Write a new active-set/trust-region optimizer: unnecessary implementation
  and validation burden. The exhaustive face enumeration here is an independent
  six-dimensional *linear* oracle, not a proposed flight-targeting algorithm.
- Use SciPy's existing bounded nonlinear least-squares TRF implementation with
  the existing dynamics: selected, with explicit scaling, probes, budgets and
  physical success gates. SciPy 1.17.1 is already installed by Conda on this
  machine but is not explicitly pinned in environment.yml; D16.2 must pin it.

## Decision and rationale

### Frozen problem and separate path

Implement a private D16 runner, not a replacement for the frozen D15 schedule.
Bind the 0104/0107 hashes of 0108 and the complete 0110 report above, including
candidate `d0001-t0035`, original free-phase branch, profiles, target, resources,
commands and raw residual/mass evidence. Keep historical and current source
manifests separate. Explicitly start from 0110 accepted command ID 52, not a
linear-fit command, another branch or an automatically chosen seed.

Reuse Moon-point-mass gravity, the six controls/two-node direction chart, actual-
time circular initial state, variable mass, F=1000 N / Isp=450 s, 2000/500 kg
initial/dry masses, original launch window, all original physical bounds and
arrival allowance. Keep target six-state and tm=979002340.6346419 TDB s fixed,
Moon-relative J2000/SI. Reuse both native profiles and sampled guards unchanged.
Retain physical model ID `local-moon-point-mass-steered-burn-v1`; distinguish
algorithm ID `bound-aware-local-trf-v1`. No new throttle/steering node or force.

Fresh nominal seed replay must agree with 0110 ID 52 within 1 m / 0.001 m/s /
1e-6 kg before any derivative work. Failure stops. For this reference, the
minimum coast over the complete timing box is 1756.635988 s, exceeding 1 s;
thus the coupled cutoff constraint is redundant over this box. Verify this
analytically, not just at the seed. An unsupported box/window intersection stops
as domain-unresolved; do not ignore a coupled constraint for another scenario.
The existing physical command checks remain authoritative for every evaluation:
no clipping, hidden bound widening, invalid-state penalty or relaxed mass gate.

### Mature bounded solver, explicit scientific boundary

Use `scipy.optimize.least_squares(method='trf', tr_solver='exact', loss='linear')`.
TRF incorporates bounds into its step selection instead of uniformly shrinking
one unconstrained Newton direction. Optimizer termination is not equivalent to
our physical closure. See the [official SciPy API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html).
Pin `scipy=1.17.1` with Conda during D16.2, keeping Python/NumPy/Tudat pins;
verify the installed implementation and full regression. No installation,
environment change or runtime import is introduced by this design stage.

Solve in y coordinates with x=x_seed+T*y, y0=0,
T=(300 s,300 s,0.1,0.1,0.1,0.1). Bounds are (L-x_seed)/T and (U-x_seed)/T.
Use x_scale=1, ftol=xtol=gtol=1e-10, max_nfev=40, verbose=0 and serial calls;
do not select dynamic Jacobian scaling, robust loss, a different method or a
second start. T now defines coordinates, not a rigid per-step uniform cap.
Residual remains (dr/10 m, dv/0.01 m/s); retain both vector-norm closure tests.
The initial solver request must reconstruct the replayed seed exactly; otherwise
stop instead of silently accepting an adjusted initial command.

Provide a callable Jacobian with the existing physical h=(1 s,1 s,0.001,0.001,
0.001,0.001). For each control, deterministically choose central x+/-h if both
are admissible, otherwise forward x+h,x+2h, otherwise backward x-h,x-2h. If no
complete pair is admissible, stop derivative-domain-unresolved, without shrinking h.
Preflight all twelve probes before any launches. Form physical derivatives:

    central: (r(x+h)-r(x-h))/(2*h)
    forward: (-3*r(x)+4*r(x+h)-r(x+2*h))/(2*h)
    backward: (3*r(x)-4*r(x-h)+r(x-2*h))/(2*h)

Multiply column j by T[j] to obtain dr/dy. Reuse the completed center residual,
not another propagation. Record stencil choices, raw residuals, matrix and SVD
diagnostics with rcond=1e-10; rank/conditioning diagnose local response, not
physical impossibility or a success certificate. Do not require central probes
outside a bound or inject an additional undocumented rank-recovery solver.

### Closure, failure and bounded work

Check closure after replay and every completed non-probe objective evaluation.
On the first admissible objective with norm(dr)<=10 m AND norm(dv)<=0.01 m/s,
stop optimizer control flow immediately using a dedicated internal completion
signal, before another Jacobian. Do not depend on a callback that runs only
after derivative work. A closed derivative probe is not eligible. Run exactly
one fresh tighter burn/coast of that frozen objective command. Require both
profiles to close, endpoint agreement <=1 m / 0.001 m/s / 1e-6 kg, cutoff mass
error <=1e-6 kg and unchanged coast mass. Only then report `local-qualified`.
After tighter failure/disagreement stop unqualified; never resume TRF.

An optimizer success flag without physical closure is `stationary-unclosed`
(gtol) or `stagnated-unclosed` (ftol/xtol), not feasible or globally impossible.
Limits produce `budget-exhausted` with the specific counter/deadline reason.
Invalid binding, nonfinite data, domain/probe/native/guard failure stops the
whole study with contextual evidence, never a large penalty residual or retry.
Retain best eligible objective separately from accepted solver iterates; a
best probe or small gradient must not become a successful result.

The 300-second cooperative clock starts before binding/preparation. Own counters,
not SciPy's nfev alone, cover every probe and attempted native launch. Allow:

- One nominal seed replay; its exact residual is reused for the first objective
  request only. That cache hit counts as an objective request, not a propagation.
- At most 40 total objective requests including that hit, and 20 complete
  Jacobian batches with twelve probes each. No cache for subsequent objective
  or probe evaluations; Jacobian centers reuse their completed residual as above.
- At most 280 nominal evaluations (1+39+20*12), plus one reserved tighter
  evaluation: 281 total / 562 native launches, counting failures before entry.

Stop before a batch that cannot fit the remaining probe/counter/deadline budget;
reserve the final tighter pair, with no native work after an incomplete arc.
This is an explicitly larger D16 ceiling, not a retroactive D15 limit change;
7.94 s observed for D15 does not guarantee D16 runtime. A cooperative deadline
does not preempt a blocked native call. Record every objective/cache/probe role,
commands, parent/accepted-iterate identities, physical epochs/masses, residuals,
Jacobians, optimizer settings/status/active bounds, source/resources/versions,
all own counters and optional tighter agreement. Unavailable fields stay explicit.

## Consequences and revisit conditions

This tests whether bound-aware step selection can close the current local
problem; it does not promise closure or prove reachability. If it stops on an
unclosed constrained point, review active bounds, projected gradient and model
response before deciding whether to change the steering chart, thrust, timing
or mission reserve. Those would each change the question and need new scope;
do not launch automatic sweeps or relax the target to manufacture success.

Implement and independently test D16.2 first; D16.3 requires a separate user
instruction for exactly one native study. Preserve D14/D15 behavior and all
retained evidence. No public API/UI, full-force trajectory, Mars capture,
continuous-safety/hardware qualification or strict M3/task-3.9 completion.
Automation remains paused. A third steering node is deliberately deferred.

## Evidence and verification

[The read-only script](experiments/0111-diagnose-local-targeting.py) reproduces
the retained diagnosis using NumPy 1.26.4 and installed Conda SciPy 1.17.1.
Run `conda run --no-capture-output -n space-nav python
docs/adr/experiments/0111-diagnose-local-targeting.py` without `-O`.
Eight bounded linear fits pass independent exhaustive 729-face enumeration and
scaled KKT residual <1e-10. The final matrix is explicitly labelled ID 39, not
ID 52. Formula/counter checks and finite JSON pass. Zero native arcs and zero
nonlinear spacecraft targeting runs are performed in this stage.

D16.2 verification must cover independent linear/quadratic bounded roots,
bound-active unattainable targets without false success, rotated/unit/mass/time
oracles, all three derivative stencils and full-batch preflight, scaling,
exact replay/cache accounting, first-closure stop before Jacobian, closed probes,
rank loss/solver stationary exits, native failures/nonfinite penalties forbidden,
fixed tighter commands, the 280/281/562/300 boundaries and preserved D14/D15.
Pin/verify SciPy, run focused/native and full tests before implementation completion.
This design stage checks exact offline JSON reproduction, independent quadratic
stencil/unit identities, coast/budget arithmetic, strict OpenSpec, Ruff, 91 local
links, immutable hashes and diff; runtime tests/full suite are not rerun because runtime,
tests and environment files are unchanged in D16.1. D16.2 is subsequently verified
in [0112](0112-bound-aware-targeting-implementation.md); D16.3 remains unchecked.
