# 0114 — Diagnose the active fuel bound and add smooth steering freedom

Date: 2026-10-16
Decision status: accepted (D17 design, not demonstrated target closure).
Implementation: D17.1 offline diagnosis/design complete; D17.2 runtime and D17.3 native study not started.
Scope / milestone: M3 research, same local lunar six-state boundary problem.
Base revision: `71d91e4f80cd5c7422cb5fccb3f451bc728db6c4`, clean before this analysis/design stage.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; a separate follow-up to [0111](0111-bound-aware-local-targeting.md)/[0113](0113-bound-aware-targeting-hits-budget.md), not a revision of their experiments.

## Context and constraints

D16 stops at its 20-Jacobian budget, not a returned optimizer success. Best
objective 262 is unclosed at 59.203835 km / 246.398570 m/s and is not a recorded
accepted iterate. The last measured matrix belongs to accepted ID 249. Diagnose
that saved response without a new propagation, a 21st D16 batch or a Jacobian
invented at ID 262. We want the same target, not a lower score alone.

### Evidence: local response exhausted in the available direction

Retain [the offline diagnosis](experiments/0114-steering-freedom-diagnosis.json),
SHA256 `b9ea186692872463dc3482cf2441206044c12dc063525395726a8689348779ec`.
It binds 0113 SHA256
`417f4a33e6407a37e9a41caff29330557f39d7a3bbfc34e9b908cc1d5589cb89`.

- Duration is exactly at 5467.045140120176 s; provisional arrival reserve is
  500.000000000067 kg against the unchanged 500 kg minimum. Ignition and the
  four slope controls are not at their bounds.
- At ID 249, unconstrained Newton predicts zero *linear* residual only by
  requesting ignition shift -2521.12 s and duration 6426.22 s: both outside
  the physical box, with 959.17 s more burn than permitted.
- Hold duration at its ceiling and minimize over the five other controls.
  The rank-five response leaves the following irreducible residual in THAT
  linear model. Full-box and component-step-box fits give the same result:

| Quantity | Saved ID 249 | Best saved ID 262 | Linear box minimum at ID 249 |
|---|---:|---:|---:|
| Scaled residual norm | 25341.142384726 | 25341.142367114 | 25341.142309194 |
| Position error, m | 59204.670723 | 59203.835452 | 59203.833133 |
| Velocity error, m/s | 246.398370 | 246.398570 | 246.398570 |

An independent 729-face enumeration confirms each bounded linear fit; normalized
KKT residual is 1.54e-17 at its solution. The saved center's duration gradient
is negative (increasing duration would reduce the linearized cost), while its
other normalized components are at most 1.21e-6. Normalization is explicitly
J-transpose-r divided by norm(J,2)*norm(r,2), NOT SciPy's gtol test. The best
available linear score reduction from ID 249 is only about 2.98e-9 relative.

These observations motivate changing the steering freedom rather than adding
D16 iterations alone. They do not prove nonlinear stationarity, global fuel
infeasibility or reachability with a new chart. No matrix/active-mask/final
projected gradient at ID 262 exists. Six controls versus six targets is not a
controllability proof; at the active duration face only five first-order free
columns remain. The new chart's response is unmeasured.

## Options considered

- Increase D16 iterations alone: could test behavior beyond the cap, but saved
  feasible linear response predicts almost no remaining reduction. Not the
  selected next attempt and not an authorized D16 continuation.
- Relax the target/time/reserve, increase thrust or add propellant: changes the
  physical question. Keep those options for a separate decision if needed.
- Add a piecewise-linear midpoint direction: introduces a guidance derivative
  kink and breakpoint integration obligations. A quadratic interpolant through
  midpoint-time values can overshoot the slope box between its nodes.
- Add one quadratic Bezier control point in the existing inertial chart:
  selected. Two new scalar controls, no kink, a convex-hull envelope and an
  embedded copy of the previous steering law; no new force, fuel or dependency.

## Decision and rationale

### Eight controls, unchanged physical boundary problem

Introduce a separate private D17 path, leaving D14/D15/D16 entry points and
historical evidence unchanged. Keep candidate d0001-t0035 / first free-phase
branch, pinned 0104/0107/0110/0113 inputs, original launch window/domain/basis,
actual-time circular ignition state, point-Moon gravity, 1000 N / 450 s,
2000/500 kg masses and provisional arrival allowance. Keep the same six target
components and tm=979002340.6346419 TDB s, Moon-relative J2000/SI. Duration and
ignition bounds, analytic mass, reserve and >=1 s coast remain authoritative.
Final mass varies with duration and is not a seventh target component.

Use model ID `local-moon-point-mass-bezier-burn-v1` and algorithm ID
`bound-aware-bezier-trf-v1`: the identifier distinguishes guidance, not new
gravity. Record the old reference model ID separately. Reuse the existing
physical domain constructor for timing, endpoints, mass and endpoint slopes;
validate the additional middle slopes before calling it. Reuse the native
burn/coast adapter through its direction callback; do not duplicate gravity,
mass integration or create a generic optimizer framework.

The control order is x=(delta_ti,tau,p0,q0,pc,qc,p1,q1). Let u0=(p0,q0),
uc=(pc,qc), u1=(p1,q1), s=t/tau during the burn. Define:

    u(s) = (1-s)^2*u0 + 2*s*(1-s)*uc + s^2*u1
    w(s) = d0 + u_p(s)*e1 + u_q(s)*e2
    direction(s) = w(s) / norm(w(s))

`uc` is a Bezier CONTROL POINT, not the direction/chart value at midpoint time;
u(0.5)=(u0+2*uc+u1)/4. All six slope coefficients stay within [-1,1]. Since
the three weights are nonnegative and sum to one for 0<=s<=1, the entire chart
stays in the original slope envelope. Orthonormality gives norm(w)>=1, so
normalization is nonsingular. The law is smooth; use the same two native arcs,
not an extra midpoint event. Native RK trial stages outside the burn interval
continue the same polynomial without clamping, as in the previous chart; the
convex-hull envelope applies only to physical 0<=s<=1. Record the physical
steering-rate upper bound 2*max(norm(uc-u0),norm(u1-uc))/tau, not a hardware gate.

### Explicit interior warm start and two fresh replay gates

Use accepted 0113 proposal 158, NOT the best objective 262 or an automatic seed
search. ID 262 is at a bound; TRF can move bound-valued initial coordinates into
the interior, conflicting with the exact initial replay/cache contract. The
[SciPy API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
documents this behavior; initialization is checked here with installed pinned
1.17.1, not inferred from the newer online documentation. ID 158 is an existing
interior command, not an invented clipped version of 262. It is only 0.000349%
worse in scaled norm, with duration margin 0.003043997508 s and provisional
reserve 500.000453118853 kg. Those are numerical margins, not operational safety.

Freeze the eight-control seed by inserting uc=(u0+u1)/2:

    (-1094.4910010491465, 5467.042096122668,
      0.11712983121190776, 0.03964718570666498,
     -0.24799059467100915, 0.04826945627805249,
     -0.6131110205539261, 0.05689172684944001)

This embeds the old straight chart mathematically, not necessarily bitwise in
floating-point evaluation. Before derivatives, freshly propagate the old
two-node ID-158 command and require agreement with its retained endpoint within
1 m / 0.001 m/s / 1e-6 kg. Then freshly propagate the embedded Bezier seed and
require the same agreement against BOTH the fresh old replay and retained ID
158, with analytic cutoff mass and exact coast-mass preservation. Any failure
stops; no alternate seed, epsilon timing repair or tolerance relaxation.
The reference replay is never an eligible new-model objective or qualification.
Only the Bezier seed can be best/closed; its exact residual supplies the one
initial objective cache hit. Reject any changed initial solver request rather
than silently caching a different command. Check physical closure at this new
seed before asking SciPy for derivatives.

### Bounded correction and closure

Keep pinned Conda SciPy 1.17.1, TRF/exact/linear, x_scale=1,
ftol=xtol=gtol=1e-10, max_nfev=40, verbose=0, workers=None. Use y0=0 and
x=x_seed+T*y, T=(300 s,300 s,0.1,0.1,0.1,0.1,0.1,0.1), transformed bounds,
and the unchanged six residual scales (10 m each position, 0.01 m/s each
velocity). No regularization residual, robust loss, dynamic scaling or fallback.

Use fixed physical h=(1 s,1 s,0.001,0.001,0.001,0.001,0.001,0.001). For each
coordinate prefer a complete central pair, else forward (+h,+2h), else backward
(-h,-2h), with the second-order formulas of 0111 and column multiplication by T.
Preflight ALL sixteen probes before any launch; reuse the completed center.
No pair means derivative-domain-unresolved, not smaller h or penalty residual.
The matrix is 6x8, singular-value array length six, gradient/active-mask length
eight. Record full and free-column row-rank diagnostics with rcond=1e-10, without
requiring an impossible rank eight or treating rank six as successful targeting.
Define the active-face free-column mask by strict physical comparisons
L[j]<x[j]<U[j], recording both margins and this mask at that matrix's parent.
It is an explicitly labelled face diagnostic, not the full feasible tangent
cone or SciPy's tolerance-dependent returned active-mask. Use separate validators
for eight controls and six residuals; do not reuse a six-control shape check.

On the first completed eligible non-probe command with norm(dr)<=10 m AND
norm(dv)<=0.01 m/s, stop optimizer control flow before its next Jacobian. Repeat
that frozen command once with the original tighter profile. Both must close;
agreement must be <=1 m / 0.001 m/s / 1e-6 kg, cutoff mass error<=1e-6 kg and
coast mass unchanged. Failure or disagreement stops unqualified, never resumes
optimization. A closed probe/reference replay, lower score or optimizer success
cannot qualify. Unclosed gtol/ftol/xtol exits retain D16's honest status labels.

### Explicit new budget and retained diagnostics

Use a fresh D17 ceiling: two nominal replays, <=40 objective requests including
the single exact Bezier-seed cache hit, <=40 Jacobian batches of sixteen probes.
Align the batch ceiling with the request ceiling instead of another earlier
20-batch stop. Worst-case nominal evaluations=2+39+40*16=681; reserve one tighter
evaluation, hence 682 total / 1364 native launches (1362 nominal plus two reserved).
This is a new bounded design, NOT a retroactive D16 budget increase or a runtime
promise based on its 38.93 s observation. A shared 300-second cooperative clock
starts before binding and covers both replays, preparation, probes and repeat.
It cannot preempt a blocked native call. Count attempts before native entry,
preflight affordability of a complete sixteen-probe batch, and stop before any
counter excess or continuation from an incomplete arc. No retry or second start.

Record reference hashes/models and historical/current sources separately,
dependency/kernel/resource manifests, eight controls/units and commands, roles,
cache source, parents/accepted IDs/best eligible objective, raw endpoint/mass/
epoch evidence, all 6x8 matrices/stencils/SVD and own counters. Bind each bound
margin/gradient diagnostic to its evaluated objective; if a limit interrupts
SciPy, solver result/status/active-mask stay explicitly unavailable. Do not
mislabel the newest objective as confirmed accepted or reuse an earlier matrix
as its derivative. Preserve completed cutoff on coast failure and finite partial
evidence without substituted dynamics or hidden guard relaxation.

## Consequences and revisit conditions

Two extra steering controls can add missing first-order directions without
more propellant, but their sensitivities and target reachability are unknown.
An active duration leaves seven possible free controls instead of five; this
does not guarantee six independent state directions or finite successful steps.
No guarantee is made that the target is reachable at this thrust/reserve/time.
If D17 remains unclosed, stop and review its measured response before any new
chart, timing, physical-parameter or target change. Do not automatically add
nodes, starts or iterations until something appears successful.

D17.2 must be separately implemented and verified before a separately authorized
single D17.3 study. This stage changes no runtime/tests/dependencies, native
profiles, public API or UI; no native trajectory or new targeting campaign runs.
Earth/Sun, harmonics, SRP, relativity, Mars/outer matching and continuous safety
remain omitted. Strict M3/task 3.9 remain open; automation remains paused.

## Evidence and verification

[The standalone diagnosis](experiments/0114-diagnose-steering-freedom.py) prints
the retained finite JSON with pinned NumPy 1.26.4 / SciPy 1.17.1. Run with the
Conda Python without `-O`. Independent exhaustive face and free-column projection
oracles verify both linear fits; KKT/scaling/budget arithmetic pass. Design
identities are checked with de Casteljau versus Bernstein evaluation on all 64
coefficient-box corners / 33 samples, normalization/rate bounds and the exact
old-chart embedding (maximum coefficient error 2.22e-16 on 1201 samples,
including RK-stage extrapolation). Synthetic 6-residual/8-control initialization
confirms the first solver request stays exactly zero. This checks design algebra,
not the future runtime or native embedded endpoint agreement.

D17.2 must test independent underdetermined coupled roots and bound-active
unclosed targets, all three sixteen-probe stencils/scales, two replay gates and
their failure paths, explicit old/new roles, exact single cache, row-rank versus
eight-control diagnostics, first closure before another Jacobian, closed probes,
frozen tighter commands, nonfinite/domain/native/guard failures and all budget
edges. Native independent acceleration-integral/mass/rotation/time oracles must
include nonzero Bezier curvature in both unchanged profiles; zero curvature must
match the old chart. Retain their independent manufactured-state tolerances:
0.001 m / 1e-6 m/s / 1e-6 kg. Run focused/native/full regression, Ruff and strict OpenSpec
before implementation completion. The real D17.3 study remains separately gated.

This D17.1 stage passes exact finite-JSON reproduction, independent review of
the saved linear response/design, Ruff, strict OpenSpec, 107 local links,
whitespace, unchanged seven runtime sources/environment and immutable input/
legacy hashes. No runtime tests or full suite are rerun: production code,
tests and environment/package files are unchanged. The previous 4,330-test
D16.2 result is historical runtime verification, not verification of an
unimplemented D17 runner. No new native trajectory or spacecraft targeting run.
