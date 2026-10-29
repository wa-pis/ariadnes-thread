# 0116 — Retain quadratic-steering improvement without closure

Date: 2026-10-29
Decision status: accepted (retain evidence, not a successful departure).
Implementation / verification: D17.3 single study complete; independent offline audits pass.
Scope / milestone: M3 research, one eight-control local lunar targeting study.
Measured revision: `3434a319d522988013684005b4ffd99576d02089`, clean immediately before invocation.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [0114](0114-quadratic-steering-freedom.md) using verified [0115](0115-bezier-targeting-implementation.md), preserving all historical evidence.

## Context and constraints

D16 improved the six-state residual but exhausted its Jacobian budget with
duration at the fuel/reserve bound. Its saved linear-response diagnosis motivated
two additional steering-shape controls, not more fuel or a different target.
D17 tests the approved smooth quadratic-Bezier chart in the same physical box.
This remains a Moon-point-mass-only local experiment, not a Moon-to-Mars flight.

The candidate is `d0001-t0035`, original first free-phase branch. Keep its target
six-state and absolute `tm=979002340.6346419` TDB seconds since J2000, Moon-relative
origin / J2000 orientation / SI units, 1000 N thrust, 450 s Isp and 2000/500 kg
initial/dry mass. Ignition shift remains within +/-1766.8649313817743 s,
duration within [2105.141840324445, 5467.045140120176] s, and all six chart slopes
within [-1, 1]. Both native integration profiles, provisional arrival reserve,
10 m / 0.01 m/s closure and 1 m / 0.001 m/s / 1e-6 kg agreement gates are unchanged.

## Options considered

- Interpret the lower score, rank-six response or returned SciPy success flag
  as physical closure or a constrained optimum: rejected; none establishes it.
- Spend unused time/evaluations on another seed, wider bounds or a second run:
  outside this study's approved scope; not performed.
- Retain the complete returned study and stop for a separate review of its
  limitations: selected. A negative result is evidence, not a relaxed gate.

## Decision and rationale

Retain [the finite JSON](experiments/0116-bezier-local-study.json), SHA256
`93e5b224ade1038616e11951d5d45f2ca717e10544c2b67aac2120de6103b566`.
Exactly one `_run_bezier_local_targeting` call used the pinned 0104/0107/0110/0113
inputs. The inline invocation asserted the measured revision, a clean worktree
and an absent output path immediately before launch, recorded UTC timestamps,
then saved with exclusive creation after return. No previous evidence, runtime,
tests, dependencies, native profiles or physical parameters were changed.

Fresh old-chart replay reproduces retained accepted D16 proposal 158 exactly;
the fresh embedded Bezier seed reproduces both saved and fresh old endpoints
exactly. All three position/velocity/mass difference triples are zero. This is
the explicitly approved interior seed, not D16's best objective 262 or a repaired
bound point. The old replay cannot qualify or supply the new-model cache.

The actual outcome is `stagnated-unclosed`. SciPy returned status 2 with
`ftol` termination, not a budget interruption or physical success. Elapsed time
including preparation was 76.61463791597635 s, below the shared 300-second limit.

| Endpoint | Position error, km | Velocity error, m/s | Scaled norm |
|---|---:|---:|---:|
| Retained D16 best objective, ID 262 | 59.203835 | 246.398570 | 25341.142367 |
| Fresh embedded D17 seed, ID 1 | 59.209145 | 246.398204 | 25341.230736 |
| Best / returned accepted D17 objective, ID 487 | 44.386790 | 185.850963 | 19107.791001 |

Relative to the fresh seed, the scaled norm decreases 24.5980%, position error
25.0339% and velocity error 24.5729%. No objective or probe meets the unchanged
closure gates. No tighter repeat is authorized: agreement is `unavailable`,
selected objective is null and mission-qualified is false. Lower residuals are
not an endpoint-accuracy, feasibility or mission-qualification certificate.

Best controls `(delta_ti, tau, p0, q0, pc, qc, p1, q1)` are
`(-1219.1747758584374 s, 5467.045140120176 s, 0.5451660676434787,
-0.06548051012451667, -0.9999999999984438, 0.39096409412543537,
-0.258376558199023, -0.10023200889085067)`.
The last six are dimensionless slopes, not angles; the middle pair is a Bezier
control point, not a direction specified at midpoint time.

Duration equals the original reserve-derived upper bound. Cutoff/coast mass is
761.1478741194937 kg, and provisional post-arrival mass is
500.00000000006673 kg. Independent 50-digit Decimal arithmetic gives
500.000000000000312709 kg from the analytic cutoff: effectively no usable margin
above the unchanged 500 kg dry mass, not validated Mars capture or operational
reserve. Maximum recorded analytic cutoff-mass error is 1.0141e-10 kg;
every coast preserves cutoff mass exactly. The full timing box still guarantees
1756.6359885009251 s minimum coast; evaluated commands have at least
4602.439030576301 s coast.

### Counters and measured solver diagnostics

There are 504 evidence entries: two fresh replays, 38 objective requests
including one exact initial cache hit, and 464 probes. Thus 503 fresh nominal
evaluations (2 + 37 + 464) complete 1006/1006 attempted native burn/coast arcs.
All 29 sixteen-probe Jacobian batches finish: 181 central, 22 forward and
29 backward columns, with no shrunken steps, substituted dynamics, failures,
partial batches, tighter evaluation, retry or second study. The independent
40-objective / 40-batch / 681-nominal / 682-total / 1364-launch limits are not hit.

Twenty-nine recorded accepted iterates include the initial cached objective,
hence 28 updates; nine objective requests are not accepted. Unlike D16's
interruption, D17 best objective 487 is the returned final objective, a confirmed
accepted iterate AND the parent of the last measured Jacobian. The last entry
503 is a derivative probe, not a selected trajectory.

All 29 scaled 6x8 matrices have full and strict-face-free row rank six;
condition numbers range from 114.8390305 to 132.7132367. Rank six is appropriate
for six residuals, not proof of nonlinear reachability, a full feasible tangent
cone or eight independent state constraints. The final returned gradient agrees
with the measured matrix at ID 487. Returned optimality is 4649.181476828528,
far above `gtol=1e-10`; the `ftol` stop is not a stationarity certificate.

The strict physical free mask is `(true, false, true, true, true, true, true,
true)`: only duration equals a physical bound. The middle `pc` exceeds -1 by
1.5562e-12 and remains strictly interior. SciPy's tolerance-based returned active
mask `(0, 1, 0, 0, -1, 0, 0, 0)` labels both duration and `pc` active. Preserve
these distinct definitions; proximity to a steering face and a fuel ceiling do
not establish a constrained minimum or impossibility of another valid solution.

## Consequences and revisit conditions

D17.3 is complete as one bounded experiment, not a successful departure. Added
curvature improves the retained joint residual but does not close the target.
Before further native work, separately review the actual `ftol` stop, measured
gradient, bound margins, residual trade-off and feasible steering response.
Do not infer which change would work from this run alone. New commands, seeds,
nodes, bounds, target/fuel/force changes or budgets require new explicit scope;
unused time is not permission to retry. No automatic continuation follows.

Earth/Sun, harmonics, SRP, relativity, outer matching and Mars propagation remain
omitted. Kernel/lunar-resource identity is provenance, not inclusion of those
forces. Native histories are not retained: endpoint audits cannot independently
certify every interior guard sample, continuous safety, hardware slew or absolute
trajectory error. Strict M3/task 3.9 stay open; automation stays paused. No public
API, CLI, Streamlit UI, dependency or physical-model change is bundled here.

## Evidence and verification

The independent [read-only audit](experiments/0116-check-bezier-local-targeting.py)
passes from raw saved endpoints and residuals, without importing project dynamics,
calling a solver or propagating a spacecraft. Run it with pinned Conda Python,
without `-O`. It pins this artifact, four input hashes, all eight measured source
hashes and their Git revisions, historical provenance, environment, legacy file,
installed versions/builds, all 13 actual SPICE kernels and the lunar resource.
It checks 767 D16/D17 command records, Rodrigues circular-state rotation,
50-digit Decimal masses, all replay/cache/eligibility/closure identities, chart
embedding, every stencil/scale/Jacobian/SVD/gradient/bound margin, final solver
diagnostics and accepted-iterate/native counters. It launches zero native arcs.

A separate read-only physical audit also passes for all 504 fresh evidence
entries. It compares independent de Casteljau/Bernstein charts at 32,760 physical
samples, all 64 slope-box corners (2112 samples) and 4536 extrapolated samples:
maximum component difference 3.331e-16, unit-norm error 2.220e-16 and old-chart
embedding error 2.220e-16. Circular initial states match exactly using the
representable ignition epoch; requested/actual ignition shifts differ by at most
5.881e-8 s. Analytic target-mass error is at most 4.547e-13 kg. These offline
checks validate retained arithmetic, not unsaved native integration histories.

Before the sole retained study, 607 focused D17/D16/D15/D14/native/environment
tests pass in 7.17 s; Ruff and strict OpenSpec pass. Full-suite evidence is reused
from unchanged D17.2 at the measured revision: 4588 tests pass in 626.08 s.
The complete suite is NOT rerun for this evidence/documentation-only stage;
runtime, tests and environment remain byte-for-byte unchanged. Both independent
audits, final Ruff, strict OpenSpec, local documentation links, artifact syntax,
immutable hashes and whitespace checks pass. No new runtime implementation or
scientific qualification is claimed.
