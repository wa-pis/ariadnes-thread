# 0135 — Keep fixed orbital boundaries and exact burn interfaces

Date: 2026-11-01
Decision status: accepted interface design under bounded autonomous M3 continuation.
Implementation: R4.2 interface/boundary-audit contract specified; audit not executed, no mission propagation authorized.
Scope / milestone: M3 research readiness; boundary arithmetic is not trajectory feasibility.
Base revision: `4c3b11fa23ee1da5012a4ed11ce59f4bffb28513`, clean before design.
Related OpenSpec: [research requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [physical requirements](../../openspec/changes/refine-physical-trajectory/specs/physical-trajectory-refinement/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; elaborates [ADR0134](0134-boundary-evidence-reuse.md), preserves public M3 and all failed local/mission studies.

## Context and constraints

Configured physical endpoints already exist in retained0098. Its parsed scenario
and complete selected candidate equal R1, verified offline before this design.
Reconstructing new phase branches or choosing a matching sphere is unnecessary
to specify the physical problem. Failed interior states/commands are not an
achieved mission; their existence must not transfer a feasibility label.

## Options considered

- Splice D14's10*rp hyperbola into the centre-to-centre M2 curve: reject; neither
  defines the required six-component outer connection under the production model.
- Select a new parking phase, encounter epoch or sphere to obtain easier closure:
  defer; changes the problem and lacks a specified physical experiment.
- Keep configured fixed orbital endpoints and join full-model arcs at actual
  burn cutoff/ignition: selected; this reuses the existing public M3 contract.

## Decision and rationale

### Fixed initial and target data

Bind original ADR0119 SHA256
`3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0`
and retained0098 SHA256
`b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057`.
Require exact parsed equality of0098 `science.scenario`/`science.candidate`
to R1 `normalized_scenario`/`runs[0].selected`, including d0001-t0035.

The physical initial reference is0098
`science.runs[0].run.boundaries[0]`, labelled `departure-ignition`, at
978995455.2304223 TDB s; the target reference is
`science.runs[0].run.target_state`, labelled `arrival-cutoff`, at
1004169273.4122404 TDB s. Bind their full stored SI/SSB/J2000 components and UTC
labels, not rounded summaries. These are retained task boundaries, not R1's
body-centre states or D13's virtual-periapsis interpretation of the same number.
Keep initial mass2000kg, dry500kg, thrust1000N, Isp450s and configured phases fixed.

Use harmonic GMs Moon4902800121846.8 and Mars42828375815756.1m^3/s^2 for orbital
conversion, shape radii1737400m/3389500m and explicit scenario altitudes.
Lunar radius is1837400m, circular polar orbit with stored inclination and zero
RAAN/argument/anomaly; Mars periapsis/apocentre radii3689500m/13389500m with
stored inclination0.4363323129985824rad and zero RAAN/argument/anomaly.
The stored normalized eccentricity remains binding; do not recompute a different
input eccentricity from displayed radii or replace harmonic GM with SPICE GM.
Use original R1 departure-Moon/arrival-Mars SSB records as retained translation
references only; no new ephemeris truth or coverage claim.

### Interfaces, dynamics and mass

There is one SSB/J2000 state history, not an automatic switch between local
Kepler and heliocentric arcs. Keep the production force-model identifier and all
specified constants/resources from the existing physical requirement on every
arc. Switching thrust and Moon/Mars-relative TNW steering does not switch the
inertial origin, gravitational model or silently add an impulse.

For any separately supplied admissible two-burn command, define t0 as fixed
ignition, t1=t0+tau_d as departure cutoff/coast entry, t2=tf-tau_a as coast exit /
arrival ignition, and tf as fixed cutoff. Require tau_d>0,tau_a>0,t1<t2.
Both adjacent sides of each interface carry the same position, velocity, mass
and event epoch; interfaces are exact integration boundaries, not chosen radii.
Keep existing join gates1e-6s/0.001m/1e-6m/s/1e-9kg and final target gates
1000m/0.01m/s. Signed six-component residuals precede norms. Equal copied handoffs
check assembly only; they are not independent integration or force validation.

Mass uses mdot=1000/(9.80665*450)kg/s: m1=2000-mdot*tau_d,
m2=m1 during coast, mf=m1-mdot*tau_a. Retain dry-mass protection; a new R1 reserve
claim additionally needs mf>=550kg without deficit tolerance. Scalar M2/D13
arrival allowances do not supply actual tau_a or capture feasibility.
No controls, internal boundary states or achieved mass are selected here.

### Smallest next check: retained endpoint arithmetic only

Question: do the two existing0098 task endpoints reproduce the configured
orbital states at the fixed R1 body epochs using the declared harmonic GMs?
R4.3 is one native-free offline audit, not a new trajectory experiment. Bind the
two digests above, exact endpoint records, normalized inputs and original body
states before arithmetic. No imports of space_nav/TudatPy/SPICE, new kernels,
new state observations, phase search, resampling, integration or optimizer.

Use two independent forms: stdlib binary64 orbital-plane rotation and vis-viva
with the stored e, a=(rp+ra)/2 and r=a*(1-e), versus80-digit Decimal exact-float
inputs, p=a*(1-e*e), r=p/(1+e) at anomaly zero and v=sqrt(mu/p)*(1+e), with independently
implemented sine/cosine Taylor series. For the circular case use the stored e=0.
Do not round the stored polar angle to exact pi/2. Establish Decimal trig accuracy
by separately recomputing at100 digits with a stricter series cutoff; Cartesian
oracle positions/velocities must differ <=1e-12m/1e-15m/s before comparison.
This is arithmetic cross-checking, not independent ephemeris or force truth.

Both constructions must match retained body-relative and SSB endpoint position /
velocity within existing0.001m/1e-6m/s Euclidean gates. Subtraction of large SSB
positions must be done from exact stored binary values, with separate relative
and SSB residuals reported. Check body/epoch/frame/unit labels, positive radii/GM,
finite nonboolean values, equal original inputs and distinct endpoint/body states.
Record signed components, norms, GMs/radii/input digests, counters and pass/fail.
No full-mission mass, target closure, handoff or safety pass may be inferred.

One fresh offline process has a shared10s budget including read/check/arithmetic/
exclusive evidence serialization/flush, zero native queries/launches and zero
spacecraft propagations. Check before/after work and final flush, retain actual
overrun as failure. Stop on the first unexpected missing/invalid input, mismatch
or budget failure without tolerance/data changes or retry; pause automation if
resolution requires user participation or a changed scientific contract.
Implementation, if needed beyond a bounded arithmetic audit, must first satisfy
project preparation/tests; this design does not authorize another mission run.

## Consequences and revisit conditions

The contract fixes endpoints and interface semantics without choosing a new
branch or searching controls. R4.3 can check boundary arithmetic with existing
records; it cannot close the transfer. A future mission experiment still needs
an explicit command or solver contract, independent dynamical reference and
finite native-run budget. Those are unresolved and not delegated to defaults.
Strict M3/task3.9, finite-burn/full-force and continuous safety gates remain open;
no failed D17 study is retried and no existing tolerance or initial input changes.

## Evidence and verification

Source inspection covers existing `_build_boundary_states` and corresponding
handoff tests, plus retained input/candidate equality and digest checks. No new
numeric orbital state was calculated in this design stage. Strict OpenSpec,136 local links, diff and factual/input/epoch checks pass;
all240 previously tracked protected code/test/example/environment/legacy/evidence
files remain byte-for-byte unchanged.
Code/environment/history are unchanged;4936-test/Ruff evidence remains ADR0132,
with no unchanged runtime-suite rerun or R4.3 result claimed.
