# 0102 — Construct a geometrically consistent lunar departure seed

Date: 2026-10-16
Decision status: accepted (design only, following explicit user request).
Implementation: not started; analytic specification checks only.
Scope / milestone: M3 research D13, local two-body geometry before finite thrust.
Base revision: `73de6b835f09940416f6ada8943efca2dd4bad10`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; preserves D4–D12 and [0101](0101-central-fractions-do-not-improve.md).

## Context and constraints

The audit found a seed-model mismatch, not a proven unique cause of the miss.
The current scalar periapsis impulse and its direction along the asymptotic
velocity do not together construct a matching hyperbola. Constant TNW angles
also rotate inertially. The retained lunar burn lasts 2860.7331 s, about 40.48%
of the original 7067.4597 s circular period; an instantaneous approximation
does not establish finite-burn equivalence. Duration/mass arithmetic and arc
handoff checks passed; 117 focused tests were run in the audit, no mission rerun.

## Options considered

- Further endpoint damping: deferred after unsuccessful D11/D12 trials.
- Point thrust along excess velocity: retain historical behavior only; does not
  enforce the relation between periapsis and outgoing asymptote.
- Construct vector impulsive geometry first, then separately design finite-burn
  continuation: selected; makes the initial approximation's assumptions testable.

## Decision and rationale

Limit D13's implementation to pure local two-body seed construction for a
circular lunar parking orbit. Inputs are explicit mu, radius rp, oriented plane,
outgoing Moon-relative J2000 excess vector, epoch and phase policy. Use SI and
TDB seconds from J2000. Reject nonfinite/nonpositive values, zero excess velocity
and unsupported eccentric parking orbits; never replace SPICE constants.

With V=norm(v_inf), s=v_inf/V, define e=1+rp*V^2/mu and
vp=sqrt(V^2+2*mu/rp). A periapsis radius direction u must satisfy
dot(u,s)=-1/e. For orthonormal parking-plane axes P,Q, u=P*cos(phi)+Q*sin(phi).
Let A=dot(P,s), B=dot(Q,s), R=hypot(A,B). A solution requires R>=1/e.
For nondegenerate cases the two phases are
phi=atan2(B,A) +/- acos(-1/(e*R)), normalized to [0,2*pi).
The outgoing hyperbolic tangent is t=(s+u/e)/sqrt(1-1/e^2), giving
r=rp*u, v_h=vp*t and delta_v=v_h-v_parking at that same position/epoch.
This includes any required instantaneous plane change, not just a speed change.

Phase policy is mandatory: `fixed` validates the scenario's existing phase;
`free` enumerates admissible phases without changing epoch, radius or plane.
It explicitly represents a new initial-state alternative, not a replay of D4–D12.
Return all branches in normalized phase order with no implicit best-branch choice.
The geometric equality/unit-vector checks use absolute dimensionless tolerance
1e-12. If abs(R-1/e)<=1e-12, report near-degenerate/unresolved without forcing
a rounded feasible/infeasible branch; R<1/e-1e-12 is infeasible. Fixed-phase
closure must pass the equality check. Nonrepresentable e>1 or arithmetic fails
with context, not a fabricated solution. Near-degenerate support is deferred.

Independently reconstruct h=r cross v_h, eccentricity vector, specific energy
and the outgoing asymptote. Require position agreement <=1 mm, velocity/asymptote
agreement <=1 micrometer/s, periapsis radial speed <=1 micrometer/s and energy
agreement within 1e-10 relative to max(mu/rp,V^2/2), in m^2/s^2. Fail rather than
silently relaxing tolerances. Report r, parking/hyperbolic velocities, vector
delta_v, phase change, e, h, energy and invariant residuals with frame/epoch/units.

Recompute ideal departure propellant and duration from norm(delta_v), actual
initial mass, Isp and thrust. Any retained arrival delta-v is only an explicitly
labelled provisional mass allowance, applied to the new post-departure mass;
old arrival duration/final mass and M2 mass-feasible status are not transferable.
Reject dry-mass/window infeasibility before any future propagation. No branch
may be labelled a viable mission or selected merely by ideal fuel.

The virtual impulsive epoch is periapsis time, not automatically finite-burn
ignition. Finite-burn work must separately specify ignition/cutoff placement,
guidance and endpoint matching to this reference. A future local departure
experiment must use an explicitly supplied finite comparison radius above rp,
propagate the analytic outgoing branch there, and match position, velocity and
epoch, not demand that finite-radius velocity equal v_inf. Earth/Sun perturbations
and body-centre Lambert versus finite-radius endpoints require a later outer
matching correction. No sphere-of-influence radius, guidance law, homotopy ladder,
optimizer or native-run budget is invented here; they need a subsequent contract.

## Consequences and revisit conditions

D13 can establish a consistent impulsive local seed, not executable finite thrust
or a Moon–Mars transfer. Free phase changes the initial state explicitly; fixed
phase may be infeasible. Mars capture remains unresolved. Preserve old evidence,
public APIs/scenarios and legacy model. Strict M3/task 3.9 remain open, automation
paused, UI unchanged. No native mission experiment is authorized by this design.

## Evidence and verification

Design-stage synthetic algebra checks reconstruct outgoing asymptotes and energy
for two branches, rotated planes and impossible/fixed-phase cases without native
propagation. For the retained reference and its plane axes, admissible phases
are 2.8143812746 and 246.1053035975 degrees; fixed phase zero fails the geometric
equality. These numbers are not a finite-burn or interplanetary solution.
Strict OpenSpec, local links, diff and unchanged legacy checksum
are checked. Runtime tests are not rerun in this documentation-only stage.
Implementation must add independent invariant tests, high-precision mass oracles,
input/phase/degeneracy rejection, unchanged D4–D12 regressions and the full suite.
New physical experiments require their own agreed finite-burn matching contract.
