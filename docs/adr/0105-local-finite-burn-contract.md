# 0105 — Define a bounded local finite-burn diagnostic

Date: 2026-10-16
Decision status: accepted
Implementation: not started; specification checks only, no native experiment.
Scope / milestone: M3 research D14, local Moon departure only.
Base revision: `54d8e1dc5935dd7af67655c2c58c3bfa4a8625d2`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; extends [0104](0104-lunar-reference-has-two-geometric-branches.md).

## Context and constraints

D13 supplies a consistent impulsive hyperbola, not a finite-thrust solution.
The first branch requires an ideal 4210.2836806489 s burn; replacing an impulse
by a burn of that length can substantially change both position and velocity.
The user requests the finite-burn design for this branch. Selecting it for this
diagnostic is explicit, not a claim that fuel alone selects a mission solution.

## Options considered

- Reuse the old TNW command and its ignition epoch: rejected; that command does
  not encode the new vector impulse or the virtual-periapsis timing semantics.
- Immediately optimize a full-force Moon-to-Mars trajectory: deferred; it mixes
  local finite-thrust mismatch with the unresolved outer boundary problem.
- Test one fixed, centered, inertially directed burn against the analytic local
  hyperbola: selected as the smallest independently checkable diagnostic.

## Decision and rationale

### Immutable input and local model

Bind `experiments/0104-lunar-departure-reference.json` by SHA256
`bbcfa37e2e259af0f5545aeb12e9784f8826122f1ad5a66c52698aef856b7134`,
candidate `d0001-t0035`, and its first free-phase branch (2.814381274616926
degrees). Verify the full retained state, impulse, masses, mu and epoch, not a
rounded display phase or array index alone. Reject mismatches before propagation.
The reference virtual periapsis epoch is 978995455.2304223 TDB s from J2000.
Use Moon-relative J2000 states in SI; this is an explicit private local boundary,
not a silent replacement of the public SSB convention.

Use only lunar point gravity, the recorded mu and constant 1000 N thrust,
Isp 450 s, initial mass 2000 kg and dry mass 500 kg. Use g0=9.80665 m/s^2.
Earth/Sun forces, harmonics, radiation, relativity and Mars are intentionally
absent. Identify the model as `local-moon-point-mass-finite-burn-v1`; never reuse
the full-force model identifier or attach this result to PhysicalTrajectoryResult.
No new dependency, public API, CLI or UI is required.

### Timing, steering and mass

Let t0 be the virtual periapsis epoch, rp the reference parking radius and dv
the reference vector impulse. Fix d=dv/|dv| in J2000 for the entire burn;
this is not a constant TNW direction and not a solved guidance law.
Compute mf=m0*exp(-|dv|/(g0*Isp)) and tau=(m0-mf)*g0*Isp/F.
Set ignition ti=t0-tau/2 and cutoff tc=t0+tau/2. These times are an explicit
initial guess, not an assertion that a centered burn reproduces an impulse.

Construct the circular parking state at ti analytically by rotating the D13
parking position and velocity through n*(ti-t0) in its original oriented plane,
where n=sqrt(mu/rp^3). Start mass at m0 at ti. Do not start from the hyperbolic
velocity, reuse the t0 state at ti or rotate the plane. Record that actual
ignition precedes the candidate's virtual epoch; retain and check the original
launch-window bounds against ti without silently shifting dates. A bound failure
stops before native work. This local check cannot certify arrival-window timing.

During burn integrate r'=v, v'=-mu*r/|r|^3+F*d/m and m'=-F/(g0*Isp).
After cutoff, thrust and mass flow are zero. Handoff preserves epoch, position,
velocity and mass exactly. Positive finite parameters, mf>dry mass and the
provisional arrival allowance must pass before integration; the allowance is
still not validated capture. Detect lunar impact at the retained physical shape
radius, dry-mass violation, nonfinite states and integration failure; stop without
retry. Sampled guards do not establish continuous collision clearance.

### Fixed state and epoch, not asymptotic velocity

The diagnostic explicitly chooses Rmatch=10*rp=18,374,000 m. This is a comparison
surface, not a sphere of influence or a validated force-switch boundary. It is
recorded in the command, not introduced as a hidden scenario default.
Require Rmatch>rp and construct the outgoing reference state there analytically.
Let V=|vInfinity|, a=mu/V^2, e=1+rp/a, p=rp*(1+e),
H=acosh((Rmatch/a+1)/e), and dt=sqrt(a^3/mu)*(e*sinh(H)-H).
Set tm=t0+dt, cos(nu)=(p/Rmatch-1)/e and positive sin(nu).
Using the retained periapsis unit vectors u=r0/rp and q=vHyperbola/|vHyperbola|,
the target is r=Rmatch*(cos(nu)*u+sin(nu)*q),
v=sqrt(mu/p)*(-sin(nu)*u+(e+cos(nu))*q). Reject invalid domains and tm<=tc.
Cross-check energy, angular momentum, radius and outgoing radial sign with the
D13 tolerances; independently check time of flight to <=0.001 s (for example
by quadrature of dt/dnu=r(nu)^2/|h|), not only the same formula.

Propagate the burn and then coast to this fixed tm. Compare all six state
components at the same epoch and in the same frame. Do not terminate at the
actual radius crossing, equate finite-radius speed to V, or adjust tm to reduce
the residual. Local closure requires position-norm error <=10 m and velocity-norm
error <=0.01 m/s. These are diagnostic engineering gates, not a mission accuracy
claim. Constant-direction centered thrust has no guarantee of satisfying them.

### Bounded execution and evidence

D14.2 implements and verifies the private diagnostic. Only after its checks pass,
D14.3 may run one frozen command, nominal then tighter, two arcs each, at most
four native launches under one 300-second wall-clock deadline including setup.
Record the exact integration settings before launch; tighter maximum steps and
error tolerances must be strictly smaller than nominal, with no automatic retry
or profile selection. Unit-aware profile values and native convergence tests
are part of D14.2, not silently inherited interplanetary settings.

Run the tighter repeat even when a completed nominal endpoint misses the target:
numerical disagreement and physical seed mismatch answer different questions.
Any guard failure or timeout stops the schedule and marks remaining work skipped.
Across frozen-command endpoints require <=1 m position difference, <=0.001 m/s
velocity difference and <=1e-6 kg mass difference; each cutoff mass must agree
with the analytic mass to <=1e-6 kg. Numerical agreement is not absolute accuracy.
Report closure and agreement independently as pass/fail/unavailable, together with
raw residuals, epochs, guidance, model omissions, settings, source/resource hashes,
native counters and elapsed time. Save new evidence, never overwrite 0104.
No solver, probes, alternative phase, steering adjustment, second command or
automatic follow-up study is authorized by this contract.

## Consequences and revisit conditions

This isolates finite-thrust departure construction with an analytic oracle.
Lunar point gravity is deliberately insufficient for mission validation. A
miss does not prove this branch impossible. If the fixed seed misses despite
profile agreement, separately design a controllable boundary-value problem;
do not tune by repeated undocumented trials. If profiles disagree, investigate
integration before interpreting the miss. Outer matching must account for actual
epoch/state and restore perturbations before any Moon-to-Mars feasibility claim.
Strict M3/task 3.9 remain unresolved; automation stays paused.

## Evidence and verification

This stage changes documentation only. D13's retained report supplies the input;
no new propagation, convergence result or finite-thrust feasibility is claimed.
Strict OpenSpec, local links, immutable reference/legacy hashes and diff pass.
Algebra gives tm-t0=6885.40421963728 s, later than tc-t0=2105.141840324445 s;
this checks ordering only, not endpoint closure or integration accuracy.
Runtime tests are not rerun for this design stage. Implementation requires
independent circular/time-of-flight/state/mass oracles, guard/budget tests,
focused and full regression checks before any D14.3 study.
