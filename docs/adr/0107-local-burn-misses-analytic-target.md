# 0107 — Retain the local finite-burn target miss

Date: 2026-10-16
Decision status: accepted (retain evidence, not a successful departure).
Implementation / verification: D14.3 study complete; independent evidence checks pass.
Scope / milestone: M3 research, one local Moon-point-mass finite-burn command.
Measured revision: `53229c3034cc971d6a9708b18c1772e0d32fb0e8`, clean before execution.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; completes the study specified in [0105](0105-local-finite-burn-contract.md) using [0106](0106-local-finite-burn-implementation.md).

## Context and constraints

D13 provides an impulsive hyperbola. D14 asks whether one centered finite burn
with constant inertial direction reproduces its outgoing state at a fixed time.
Only the first explicitly bound free-phase branch is tested; no steering solve,
different command, perturbations, outer matching or Mars propagation is included.

## Options considered

- Label close nominal/tighter agreement as successful departure: rejected;
  integration agreement and target closure are different acceptance gates.
- Tune direction, duration or ignition and run again: not authorized by this
  bounded contract; would obscure the result of the frozen initial command.
- Retain the failed closure and passing agreement, then stop: selected.

## Decision and rationale

Retain [the complete JSON](experiments/0107-local-finite-burn-study.json), SHA256
`01b653b72fb9a25b00f53d17cd7d88da9e9c8102fbec0f908b27da3cae9a34dc`.
The single invocation of `_run_local_burn` completed nominal burn/coast and
frozen tighter burn/coast: four launches, four completed arcs, 3.849491 s under
the shared 300-second deadline including preparation. No retry or tuning ran.
The command binds immutable 0104 by hash and candidate `d0001-t0035`, phase
0.049120219648540075 rad. States are Moon-relative J2000, SI; absolute epochs
are TDB seconds since J2000, native integration uses seconds after ignition.

Ignition is 978993350.0885819 TDB s, within the recorded original launch window.
Burn duration is 4210.28368064889 s at 1000 N / 450 s Isp; initial mass 2000 kg,
analytic cutoff mass 1045.93454880132 kg, dry mass 500 kg. The target is at
18,374,000 m from the point Moon and 8990.546059961725 s after ignition.
The same constant J2000 direction is used for both profiles; it is not TNW.

| Check | Nominal | Tighter | Required |
|---|---:|---:|---:|
| Position residual norm, m | 5520402.0871695 | 5520402.08717237 | <=10 |
| Velocity residual norm, m/s | 780.5326167494123 | 780.5326167499511 | <=0.01 |
| Cutoff mass error, kg | 9.8225e-11 | 4.7999e-10 | <=1e-6 |
| Saved-state checks | 905 | 4502 | Sampled, not continuous safety |

Both target-closure gates fail. Across the two frozen-command endpoints,
position difference is 3.03794e-6 m, velocity difference 5.61120e-10 m/s and
mass difference 3.81760e-10 kg; all pass the 1 m / 0.001 m/s / 1e-6 kg agreement
gates. Coast mass is exactly equal to the respective cutoff mass. No configured
guard rejected the sampled propagation; this is not a continuous safety proof.

This is evidence that the prescribed centered constant-direction seed does not
realize the impulsive reference, despite close profile agreement. It is not an
absolute error bound, proof that every finite-burn control fails, or a measured
Mars-arrival miss. Different physical models would require new validation.

## Consequences and revisit conditions

D14.3 is complete as a diagnostic, not as a successful departure. Stop this
schedule. A useful next scope discussion is a locally controllable boundary-value
design with explicit steering/timing variables and the same fixed state/epoch;
do not begin an optimizer or further trial automatically. Perturbations and outer
matching remain separate prerequisites for mission feasibility. Strict M3/task
3.9 remain open; no UI change, automation restart or historical evidence rewrite.

The pinned Tudat build emits deprecation warnings for the existing `custom`
acceleration/mass-rate names; retain them in `execution_warnings`. They did not
abort integration. No API migration or runtime fix is bundled into this report.
Kernel provenance records the loaded standard set; SPICE was used for date
conversion, not for omitted planetary forces. The retained harmonic-resource
metadata supplies lunar mu/shape provenance, not a claim that harmonics ran.

## Evidence and verification

Independent checks verify the report/reference/source hashes and measured
revision, original-window membership, fixed direction, Rodrigues ignition-state
rotation, 50-digit Decimal mass/duration, conic energy/angular momentum, Gaussian
area-law time of flight within 0.001 s, raw six-component residuals and norms,
both closure classifications, mass/coast invariants, profile agreement and
four-arc/300-second counters. JSON is finite and source files remain unchanged.
The retained record contains commands, profiles, endpoints, residuals and source/
kernel manifests; it does not contain full native histories or continuous
clearance evidence. No independent second propagation was run in this stage.

116 focused D14 tests pass in 1.10 s; these synthetic qualification tests are
separate from the single reference study. Reuse D14.2 full-regression evidence:
4,112 tests in 598.94 s at the unchanged runtime/test revision. The full suite
was not rerun for this evidence/documentation-only stage. Strict OpenSpec,
Ruff, links, diff and immutable reference/legacy checks pass.
