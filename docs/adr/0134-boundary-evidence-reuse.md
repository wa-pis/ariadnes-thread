# 0134 — Reuse boundary evidence without splicing incompatible states

Date: 2026-11-01
Decision status: accepted bounded design review under autonomous M3 continuation.
Implementation: R4.1 offline review complete; no new physical state or experiment.
Scope / milestone: M3 finite-radius boundary readiness, preserving R1–R3 scope.
Base revision: `103e8d36d069de78ced4258987d45fe6f75fe286`, initially clean.
Related OpenSpec: [research requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [physical boundaries](../../openspec/changes/refine-physical-trajectory/specs/physical-trajectory-refinement/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; reconciles [D13](0102-consistent-lunar-departure-design.md), [D14](0105-local-finite-burn-contract.md), [R1](0118-m2-reference-and-historical-data-readiness.md) and [R3](0133-three-epoch-gravity-screening.md).

## Context and constraints

The next obstacle is the connection between local finite-radius states and the
outer trajectory, not a need for another D17 optimizer run. R3 quantified local
Earth gravity but did not construct a physical coast or boundary state. Review
existing evidence before creating a new experiment or repeating local geometry.

## Options considered

- Repeat D13 on R1 as if it were a different candidate: unnecessary; the retained
  normalized scenario and complete selected candidate compare numerically equal.
- Attach D13/D14 local states to the M2 centre-to-centre curve: reject; equal
  candidate parameters do not imply equal boundary state, epoch meaning or forces.
- Reuse the proven local evidence with explicit compatibility requirements, then
  specify the missing finite-radius interface: selected; no new solver or data.

## Decision and rationale

[The offline comparison](experiments/0134-boundary-input-audit.json) binds the
original R1 and D13 file digests. Every normalized scenario field and every
selected-candidate field compares equal as parsed JSON numbers/strings/containers,
including all vector components and epochs; this is not byte-identical JSON or
identical model provenance. Both use d0001-t0035. No native imports/queries,
geometry recomputation, branch selection or new spacecraft states occurred.

| Boundary issue | Existing evidence | Reuse limit / missing connection |
|---|---|---|
| Lunar geometry | D13 fixed phase is infeasible for its constrained periapsis/asymptote construction; two free-phase branches retained | Do not select a free phase or alter the configured initial state silently. This is not a proof that general finite-thrust departure is impossible. |
| Epoch meaning | R1 M2 epoch is a body-centre encounter; D13 epoch is virtual periapsis; D14 derives centered ignition; public M3 means ignition/cutoff | Numeric epoch equality does not equate events. Keep public M3 semantics and declare any private mapping. |
| Local comparison | D14 target is10*rp and analytic hyperbolic flight time; local closure10m/0.01m/s | This is not an outer-transfer matching sphere or a Mars arrival interface. Do not promote it automatically. |
| Forces/constants | R1 Moon SPICE GM4902800205346.301; D13 harmonic GM4902800121846.8m^3/s^2 | Preserve each model's value and provenance; never substitute to make states agree. R3 adds point-force evidence only. |
| Public physical states | Existing trajectory boundary builder uses configured orbital elements and harmonic GMs at ignition/cutoff | Reuse its contract; conversion alone does not prove a trajectory connects the states. |
| Mass | R1 final887.9664640409611kg and50kg reserve use scalar ideal impulses; D13 branch1 provisional final687.0771004986456kg | Neither qualifies finite-thrust lunar escape plus physical capture. Recompute sequential mass for actual commands before claiming reserve. |
| Mars | Configured orbit and physical target conversion exist | An incoming finite-radius state, capture command and outer/local continuity remain unverified. |

Existing implementation locations are [the D13 reference](../../src/space_nav/lunar_departure.py)
and [physical boundary conversion](../../src/space_nav/trajectory.py). The latter
already constructs noncentral departure-ignition and arrival-cutoff SSB/J2000
states. A new parallel orbit converter is not justified. Existing requirements
keep lunar parking radius1837400m, Mars target periapsis3689500m and mission
closure1000m/0.01m/s; this review changes none of those values or force-model gates.

### Next specification, before implementation

R4.2 must define the smallest R1-specific finite-radius interface contract:
explicit fixed initial/target orbital states and event semantics, local-exit /
outer-entry and outer-exit/local-entry events, each side's state/epoch/frame/GM
and force model, shared mass history, six-component continuity residuals and
an independent reference. Preserve the original candidate as a seed/identity,
not a demand to pass through body centres. No hidden phase, encounter-time shift,
branch choice, radius selection, interpolation or impulse-to-burn equivalence.

A complete experiment contract must give exact numerical states/epochs or their
fully specified deterministic construction, numeric continuity/target/mass gates,
independent oracle and a wall-time/native-call budget before implementation or
execution. Unspecified values remain explicitly unresolved; they are not defaults.
Existing local and mission tolerances remain separate. The next step is design
only, with zero native queries, propagation or optimization; stop for user input
if a needed mission choice exceeds the already authorized scope. This review
does not authorize a new branch, candidate, kernel, initial state or failed-run retry.

## Consequences and revisit conditions

Reuse avoids repeating a successful pure diagnostic and exposing another local
solver before the mission interface is defined. The review does not solve the
boundary problem or establish feasibility. Full-force/finite-burn/continuous
safety, UI qualification, strict M3/task3.9 and M6 remain open. R1/R2/R3 and
D13–D17 historical evidence remain valid only at their recorded scope.

## Evidence and verification

The input audit retains base revision, two source SHA256 values, exact parsed
input comparisons, separately named GMs and zero native/state counts. Source
inspection confirms existing boundary conversion and local epoch/phase handling;
no production helper was executed. Strict OpenSpec,139 local links, JSON/digests and diff checks pass; all239
previously tracked protected code/test/example/environment/legacy/evidence files
remain byte-for-byte unchanged. Runtime tests are not rerun on unchanged code; ADR0132 retains4936 passes.
