# 0110 — Retain local steering improvement without closure

Date: 2026-10-16
Decision status: accepted (retain evidence, not a successful departure).
Implementation / verification: D15.3 study complete; independent evidence audit passes.
Scope / milestone: M3 research, one bounded local steering/ignition study.
Measured revision: `f4aed8f5727034623a9a806ec423f0596bea5c65`, clean before execution.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [0108](0108-bounded-local-steering-targeting.md) using [0109](0109-local-steering-targeting-implementation.md), preserving the 0104/0107 evidence.

## Context and constraints

D14's constant-direction command misses the fixed local target by 5520.40 km
and 780.53 m/s. D15 varies ignition, duration and four direction-chart slopes
without changing the six-state target or its absolute match epoch. This study
tests the prescribed four-step schedule, not unrestricted reachability or an
interplanetary mission. Implementation verification precedes the single run.

## Options considered

- Treat numerical improvement or rank six as successful departure: rejected;
  neither satisfies the independent position/velocity closure thresholds.
- Continue beyond four iterations, change scales/bounds or choose another seed:
  outside the accepted schedule and not authorized by this result.
- Retain the complete non-converged study, audit it and stop: selected. Any
  follow-up requires a separate evidence-based scope decision.

## Decision and rationale

Retain [the complete finite JSON](experiments/0110-local-steering-study.json),
SHA256 `678287cc7aee2b3d83e89c9fbff1113a96d24c5b8960f047aeadb82d049c4274`.
Exactly one `_run_local_targeting` invocation completed 53 nominal evaluations
(baseline, 48 central probes, four accepted trials): 106 native launches and
106 completed arcs in 7.939209 s including preparation. Four iterations are the
limiting schedule here, not the 300-second deadline or 132-launch ceiling.
No retry, alternate branch, fifth correction or further study occurred.

The baseline endpoint and mass replay 0107 bit for bit. Every iteration uses
twelve central probes at the same accepted parent; the first trial, alpha=1,
passes sufficient decrease. No infeasible/skipped proposal or native failure
occurs. All sampled guards pass according to the recorded native results.
Native histories are not retained, so the audit checks endpoints and arithmetic,
not every interior sample or an independently propagated physical trajectory.

| Accepted command | Ignition shift, s | Duration, s | Position error, km | Velocity error, m/s | Scaled score |
|---|---:|---:|---:|---:|---:|
| Baseline, ID 0 | 0 | 4210.283681 | 5520.402087 | 780.532617 | 557530.899322 |
| Step 1, ID 13 | -300 | 4494.808964 | 5040.702308 | 723.538299 | 509236.560189 |
| Step 2, ID 26 | -600 | 4783.639184 | 4606.669103 | 665.487352 | 465448.962218 |
| Step 3, ID 39 | -900 | 5069.708889 | 4218.935925 | 609.816893 | 426278.042829 |
| Step 4, ID 52 | -1200 | 5349.046146 | 3868.622724 | 556.746073 | 390847.898419 |

Position error decreases 29.9214% and velocity error 28.6710%. Both remain far
above the required 10 m / 0.01 m/s norms. Outcome is `not-converged`, not local
qualification. No proposal closes; therefore the contract correctly launches
no tighter repeat and reports agreement `unavailable`, not passing agreement.
Nominal results alone are not an absolute numerical-error certificate.

The four scaled Jacobians have rank six with condition numbers 178.0818,
187.0511, 240.1412 and 380.3551. Independent SVD reconstruction agrees with
recorded least-squares solutions to at most 1.60e-14 in normalized controls.
The infinity-norm cap is active each time, dividing raw steps by 8.3001, 9.3336,
10.9458 and 13.4649. Each accepted step advances ignition by -300 s. This is
empirical local response of the sampled, scaled finite-difference problem; it
does not prove global controllability, eventual convergence or impossibility.

### Frozen boundary conditions and mass

All states are Moon-relative J2000 in SI; absolute epochs are TDB seconds since
J2000. Match epoch stays `979002340.6346419` for all 53 commands, with the exact
same target position/velocity from 0107. Every ignition stays in the original
2031 launch window and the +/-1766.864931 s domain. Duration bounds remain
2105.141840 to 5467.045140 s; all four dimensionless slopes stay within +/-1.
Initial circular position/velocity follows actual representable ignition time.
Thrust remains 1000 N, Isp 450 s, initial mass 2000 kg and dry mass 500 kg.

Best controls are `(-1200 s, 5349.046145563809 s, -0.23058763173986188,
0.11687483834729254, -0.18303318185548473, -0.0660432629910532)`; the four
trailing numbers are slopes, not angles. Its steering-rate upper bound is
3.5333134e-5 rad/s, not a hardware slew qualification. Analytic mass changes
with duration; mass is not a seventh target component. The best propagated
cutoff/coast mass is 787.886871422654 kg; provisional reserve after the old
1854.425749 m/s arrival estimate is 517.564916235362 kg. This is not demonstrated
Mars capture. Maximum cutoff-mass error across all proposals is 1.012e-10 kg,
below 1e-6 kg; every coast preserves cutoff mass exactly.

## Consequences and revisit conditions

D15.3 is complete as a bounded experiment, not as a successful lunar departure.
The measured direction/timing response is useful, but more iterations are not
automatically justified: the last duration is only 118.0 s below the existing
reserve-derived maximum. A further design must explicitly address the remaining
state error, reserve/domain margin and a new bounded validation schedule; no
such design or execution is bundled here. Preserve the failed command and all
four updates rather than presenting only the best endpoint.

Moon-point-mass-only dynamics omit Earth/Sun, harmonics, SRP, relativity, outer
matching and Mars propagation. This study establishes neither continuous
collision safety nor flight/hardware capability. Strict M3/task 3.9 remain open;
no public interface, UI, dependency, automation state or historical JSON changes.
Standard kernels supply date conversion/resource provenance, not omitted forces;
lunar harmonic-resource metadata does not mean harmonics were propagated.
The existing Tudat `custom` acceleration/mass-rate deprecation warnings appeared
in execution output but did not abort the run; unlike 0107, this JSON does not
retain the warning text. No API migration is included.

## Evidence and verification

The retained [read-only audit](experiments/0110-check-local-steering.py) uses no
project targeting/propagation helper and launches zero native arcs. Run it in the
pinned environment with `conda run --no-capture-output -n space-nav python
docs/adr/experiments/0110-check-local-steering.py` (without Python `-O`). It checks:

- Immutable 0104/0107/0110 and legacy hashes; measured runtime source bytes
  against both disk and the recorded Git revision; historical/current manifests
  kept separate; all 13 loaded kernel identities/hashes and the lunar resource.
- Direct SPICE UTC-window conversion, branch/baseline binding, fixed frames,
  units, profiles, target and match epoch; all command bounds and endpoint guards.
- Independent Rodrigues ignition rotation, 50-digit Decimal cutoff mass/reserve,
  exact coast mass, raw/scaled residuals/norms and both closure classifications.
- Orthonormal chart basis, 101 reconstructed directions per command and analytic
  steering-rate bounds. These are guidance-arithmetic checks, not native histories.
- All 48 probe identities/signs/common parents, central matrices, independent
  SVD rank/condition/solution, single cap, prediction, alpha=1 acceptance and the
  absence of later fractions/repeat/retry in the retained schedule; all counters.

The measured-revision/one-invocation/clean-launch annotations record this run's
execution procedure; source/resource hashes and schedule arithmetic are checked
independently, not an external attestation of process history. Audit arithmetic
tolerances cover floating-point reconstruction only, never relax physical gates.

Before this study, 119 focused D15 tests pass in 1.50 s and strict OpenSpec passes.
After retention the same 119 tests pass again in 0.99 s. The audit, Ruff, strict
OpenSpec, 92 local links, finite JSON, diff and unchanged legacy/reference/source
checks pass. No production or
test source changes: reuse 0109's 4,231-test full regression (602.73 s), whose
runtime/test bytes are unchanged at `f4aed8f`. The full suite was not rerun for
this evidence/documentation stage. No independent second propagation was run.
