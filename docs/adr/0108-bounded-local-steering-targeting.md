# 0108 — Design bounded local steering and ignition targeting

Date: 2026-10-16
Decision status: accepted
Implementation: not started; design verification only, no new propagation.
Scope / milestone: M3 research D15, fixed local departure boundary value problem.
Base revision: `4a8a9be422d5b5062e5fd7ddfb2f70404cf639b1`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; extends the failed fixed-command study [0107](0107-local-burn-misses-analytic-target.md) without rewriting its evidence or relaxing D14.

## Context and constraints

D14 nominal/tighter endpoints agree closely but miss the prescribed state by
5520.40 km and 780.53 m/s. This shows the centered constant-direction command
fails, not that the selected branch is impossible. The user requests a design
that can vary ignition and thrust direction to try to satisfy all six endpoint
conditions. Six parameters do not by themselves prove controllability or promise
convergence. Measure local rank and stop honestly on unresolved cases.

## Options considered

- Change only ignition and duration with fixed direction: too few adjustable
  quantities to generally satisfy six independent state constraints.
- Immediately add throttle schedules, many steering nodes, multiple burns or
  full-force interplanetary optimization: deferred; unnecessary for this bounded
  test of the smallest six-parameter local model.
- Keep thrust magnitude fixed and use ignition, duration and two direction
  nodes with two coordinates each: selected. Smooth direction variation adds
  four controls without adding a dependency or changing the target.

## Decision and rationale

### Binding and immutable target

Pin 0104 SHA256
`bbcfa37e2e259af0f5545aeb12e9784f8826122f1ad5a66c52698aef856b7134`
and 0107 SHA256
`01b653b72fb9a25b00f53d17cd7d88da9e9c8102fbec0f908b27da3cae9a34dc`.
Verify the full retained candidate, scenario, first free-phase branch, command,
model/resources and both D14 runs before native work. Retain historical hashes
separately from current implementation hashes. Reuse Moon-only point gravity,
J2000, SI and TDB seconds from J2000; no planetary perturbations or Mars arc.
The revised thrust model identifier is `local-moon-point-mass-steered-burn-v1`.

Freeze D14 target position, velocity and absolute epoch
tm = ignition_epoch_D14 + match_after_ignition_D14. Do not move that epoch,
select a different radius crossing, change the hyperbola/branch or refit the
target after an update. Exactly six constraints apply: three position and three
velocity components. Final mass is NOT a seventh prescribed endpoint: D14's
target mass was specific to its duration and is provenance only in D15.

### Six controls and smooth inertial steering

Use x=(delta_ti_s, tau_s, p0, q0, p1, q1), initialized to
(0, tau_D14, 0, 0, 0, 0). ti=ti_D14+delta_ti_s and tc=ti+tau_s.
The four p/q values are dimensionless direction slopes, NOT radians.
Let d0 be D14's unit inertial impulse direction. Choose canonical axis a whose
absolute dot with d0 is smallest, breaking ties X then Y then Z.
Set e1=unit(a-dot(a,d0)*d0), e2=cross(d0,e1). Freeze this basis for the study.
For s=(t-ti)/tau on [0,1], define

    p(s)=(1-s)*p0+s*p1
    q(s)=(1-s)*q0+s*q1
    w(s)=d0+p(s)*e1+q(s)*e2
    d(s)=w(s)/norm(w(s))

The coefficient of d0 is always one, so norm(w)>=1: there is no antipodal
interpolation singularity. At zero slopes this exactly recovers D14's direction.
This is a smooth J2000 direction schedule, not a rotating TNW command or an
attitude-controller implementation. Record the steering-rate upper bound
sqrt((p1-p0)^2+(q1-q0)^2)/tau in rad/s; it is not a spacecraft slew qualification.

Keep F=1000 N and Isp=450 s; no throttle variable. Initial mass remains 2000 kg
at each command's ignition, with an unpowered circular parking history before it.
Analytically rotate the same D13 parking state from its virtual epoch to each
actual ti, preserving radius/plane and changing only phase consistently with time.
Never reuse the original ignition state at the new ti or start on the hyperbola.
Integrate variable mass m'= -F/(g0*Isp) during burn, zero during coast, using
g0=9.80665 m/s^2 and native coupled translation/mass as in D14.
The analytic cutoff mass is m0-F*tau/(g0*Isp), recomputed for each command.
Do not enforce the original impulse magnitude through an extra constraint.

### Explicit exploratory bounds, not hardware limits

Let P=2*pi*sqrt(rp^3/mu), rate=F/(g0*Isp), and DVa be the unchanged provisional
arrival allowance from 0104. Require all of:

- abs(delta_ti_s)<=P/4, intersected with the original UTC launch window converted
  by SPICE; no hidden date shift or new launch-date default.
- tau_min=0.5*tau_D14 <= tau <= tau_max, where
  tau_max=min(1.5*tau_D14, (m0-mdry*exp(DVa/(g0*Isp)))/rate).
- abs(p0), abs(q0), abs(p1), abs(q1)<=1, restricting directions to the d0
  hemisphere with cone angle <=atan(sqrt(2)), approximately 54.74 degrees.
- tc<=tm-1 s, positive finite duration/parameters, cutoff mass>dry mass and
  provisional post-arrival mass>=dry mass. Check the mass reserve numerically
  for every command, including at floating-point bound equality.

Reject an empty admissible domain. For the pinned example P/4 is
1766.8649313818 s and duration bounds are approximately
2105.1418403244 to 5467.0451401202 s. These are named research bounds, not
evidence of hardware authority, globally optimal fuel or validated Mars capture.
The target mass field of an internal arc command must carry its newly computed
analytic mass solely for mass checking, without changing target position/velocity.

### Deterministic bounded differential correction

Reuse the D14 nominal/tighter profiles unchanged. Every evaluation uses fresh
native burn/coast resources with exact state/epoch/mass handoff, impact/dry-mass/
finite-state guards, exact fixed final epoch and the shared deadline. Preserve
D14's constant-direction path and its four-arc budget; D15 gets separate private
orchestration/budget. No public API, CLI, UI or new dependency is required.

First replay x0 nominally and compare its endpoint to retained 0107 nominal:
<=1 m, <=0.001 m/s and <=1e-6 kg. Command, physical inputs and target must match.
Mismatch stops before a derivative/solve. This is a baseline-binding gate, not
proof that historical/current source hashes must be equal.

For the current accepted iterate define the dimensionless residual
r=(delta_position/10 m, delta_velocity/0.01 m/s) and score=norm2(r).
Closure is still norm(delta_position)<=10 m AND norm(delta_velocity)<=0.01 m/s,
not independent per-component bounds or merely a smaller score.

If not closed, perform at most four correction iterations. Each iteration:

1. Compute twelve nominal central probes in fixed control order, positive then
   negative for each control, all relative to the same accepted iterate. Use
   h=(1 s, 1 s, 0.001, 0.001, 0.001, 0.001). Every probe must satisfy the full
   command domain before launching. An inadmissible probe stops as
   `derivative-domain-unresolved`: no one-sided substitution or hidden h change.
2. Let T=(300 s, 300 s, 0.1, 0.1, 0.1, 0.1). Form column
   J_i=(r(x+h_i*ei)-r(x-h_i*ei))/(2*h_i/T_i), i.e. derivative with respect to
   normalized controls. Use existing NumPy least squares with rcond=1e-10 to
   solve J*z=-r. Require finite singular values, rank six and sigma_max/sigma_min
   <=1e10. Record the matrix, raw residuals and singular values; rank failure
   means unresolved local parameterization, not physical branch impossibility.
3. Cap once: zc=z/max(1,norm_inf(z)), dx=T*zc. Record raw/capped vectors and
   predicted residual r+J*zc. Stop on zero/unrepresentable physical update or
   no strictly smaller finite predicted score. No regularization fallback,
   changed scales, second solve, automatic trust-radius adjustment or pseudoinverse
   success claim after a rank failure.
4. Try x+alpha*dx for alpha=1, 1/2, 1/4, 1/8, in order, each relative to the
   same current iterate. An analytically out-of-domain trial is recorded/skipped
   without native work; no clipping. A valid trial is accepted only if both
   closure gates pass OR score_trial<=(1-1e-4*alpha)*score_current. Accept the first
   such trial, skip later fractions and recompute J only at that new iterate.
   If none qualifies, stop `no-acceptable-step`. This prescribed search is not
   permission to retry a failed native command or try another initial seed.

Stop iteration immediately on the first nominal closure and run exactly one
fresh tighter burn/coast repeat of that frozen command. This also applies if the
baseline is already closed. Local success requires BOTH profiles to close and
endpoint agreement <=1 m / 0.001 m/s / 1e-6 kg, with each cutoff mass within
1e-6 kg of its own command's analytic value and unchanged coast mass.
On tighter disagreement/failure retain nominal evidence but declare unqualified;
do not resume iterations, select nominal-only success or try a second profile.
If the iteration cap is reached without closure, report `not-converged`, retain
the best accepted iterate and do not run a tighter repeat or claim success.

### Work limits and retained evidence

One wall clock starts before binding/kernel preparation: 300 seconds total.
Maximum work is 65 nominal command proposals/evaluations
(one baseline + four iterations * (12 probes + four trials)), plus one frozen
tighter evaluation, at most 66 evaluations / 132 native launches. Skipped
infeasible proposals still consume their prescribed schedule slot. Count native
launches before entry, including failed launches; never accept a partial arc.
All native failures, sampled guard violations, nonfinite arithmetic and deadline
expiry stop the entire study; no continuation after a failed probe or trial.
The cooperative clock rejects late output but cannot preempt a blocked call.

Record every proposed command and its units, feasibility/skip reason, accepted
iterate and parent, absolute epochs, six raw residuals, mass, profiles, matrix/
solve/prediction/step/fraction, acceptance arithmetic, endpoint agreement, source/
resource/reference hashes, counters and elapsed time. Missing evidence remains
explicitly unavailable. Retain new JSON/ADR even on failure; never overwrite
0104/0107 or turn a best partial iterate into a qualified mission result.

## Consequences and revisit conditions

This is a private bounded local targeting experiment, not a production optimizer,
global search, fuel optimum, flight controller or proof of reachability.
Bounds, rank loss, failed local decrease or exhausted iterations can prevent
convergence even if a different control law is feasible. Investigate the measured
failure under a new scoped decision, not by expanding this schedule automatically.
Finite steering-rate diagnostics do not replace attitude/hardware limits.
Earth/Sun, harmonics, SRP, relativity, outer transfer matching and Mars capture
remain absent. Strict M3/task 3.9 stay open; automation stays paused.

## Evidence and verification

This stage specifies only; it performs no native propagation or spacecraft
targeting solve. Arithmetic checks pass for basis orthogonality, 405 sampled
unit/interpolated directions, zero-control D14 parity, time/mass bounds,
normalized-column units with a synthetic linear solve and the 66-evaluation/
132-launch upper bound. Strict OpenSpec, links, diff and immutable hashes pass.
Runtime tests are not rerun for a documentation-only design.
D15.2 must verify independent steering/rotation/mass and linear/quadratic solver
oracles, rank/condition and boundary failures, fixed target time, deterministic
ordering, acceptance thresholds, skipped proposals, final tighter failure, native
guard/handoff/deadline behavior, D14 regression and full-suite checks. Only then
may D15.3 execute one study and retain independently checked evidence.
