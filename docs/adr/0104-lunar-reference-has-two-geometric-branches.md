# 0104 — Retain the consistent local departure alternatives

Date: 2026-10-16
Decision status: accepted (retain a non-propagating reference, not a mission).
Implementation / verification: D13.3 complete; independent arithmetic passes.
Scope / milestone: M3 research local two-body impulse geometry only.
Measured revision: `34a1541`, committed and pushed before the report.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; completes [0102](0102-consistent-lunar-departure-design.md) and [0103](0103-lunar-departure-geometry-implementation.md).

## Context and constraints

The earlier seed combined a scalar escape impulse with an asymptote-based thrust
direction. D13 constructs a local hyperbola consistent with the same retained
excess vector and an explicitly chosen parking-phase policy. No trajectory
integration, force-model change or native mission experiment is part of this report.

## Options considered

- Keep phase zero and label the old scalar maneuver consistent: rejected;
  the fixed-phase equality fails.
- Automatically select the lower-fuel free-phase branch and start a burn:
  deferred; finite-burn timing/guidance and outer matching are not specified.
- Retain both alternatives with independent invariants and mass estimates:
  selected; exposes the phase and fuel changes without a mission claim.

## Decision and rationale

Retain [the complete JSON](experiments/0104-lunar-departure-reference.json), SHA256
`bbcfa37e2e259af0f5545aeb12e9784f8826122f1ad5a66c52698aef856b7134`.
Inputs bind immutable 0098, the identical normalized scenario/candidate and its
recorded Tudat lunar mu and orbit shape radius. No live SPICE request was needed.
All outputs are Moon-relative J2000, SI and TDB seconds from J2000, with a
virtual periapsis epoch rather than a finite-burn ignition epoch.

Fixed phase zero reports `infeasible-fixed-phase`. Free phase returns both
geometrically consistent alternatives in phase order, without selecting either:

| Quantity | Branch 1 | Branch 2 |
|---|---:|---:|
| Phase, degrees | 2.8143812746 | 246.1053035975 |
| Vector impulse norm, m/s | 2860.6623260732 | 4445.5888309104 |
| Ideal departure duration, s | 4210.2836806489 | 5602.9812533784 |
| Provisional arrival duration, s | 1583.6352279288 | 1105.8042797306 |
| Provisional final mass, kg | 687.0771004986 | 479.7650272216 |
| Estimate status | ideal-estimate-only | rejected-dry-mass |

The departure estimate is recomputed from the full vector impulse, including
plane change, rather than reusing 1728.7850762425 m/s from M2. Arrival uses the
old 1854.4257493965 m/s only as a clearly provisional allowance, applied to each
new post-departure mass. Branch 2 fails the 500 kg dry-mass requirement under
that allowance. Branch 1 retains an ideal mass margin, not proof of capture.
Its approximately 70.17-minute burn estimate is longer than the old seed and
does not validate a finite-thrust implementation of this impulsive geometry.

Reproduction uses the private pure function, not a new public command: load the
normalized example scenario, verify equality with 0098's scenario after JSON
normalization, read its candidate and Moon harmonic-field mu/shape radius, and
call `_lunar_departure_reference` for each explicitly supplied phase policy.
The JSON retains complete inputs, measured revision and relevant source hashes.

## Consequences and revisit conditions

The local impulsive mismatch is now explicit and testable; this does not prove
it alone caused the prior interplanetary miss. No branch is selected or passed
to propagation. Before a physical trial, separately specify virtual impulse
versus ignition/cutoff timing, thrust guidance, explicit finite comparison radius,
local state/epoch matching and a bounded native-run budget. Solar/Earth effects,
outer Lambert matching and Mars capture remain unresolved. Strict M3/task 3.9
stay open, UI unchanged, automation paused. No automatic native experiment.

## Evidence and verification

Independent NumPy cross-product/eccentricity/energy reconstruction verifies
periapsis radius, radial speed, full vector impulse and outgoing asymptote at
the accepted tolerances. Decimal (50 digits) verifies both sequential mass and
duration estimates. Reference/source hashes, exact scenario binding, branch
ordering, fixed-phase failure, finite JSON and no-selection/zero-native flags
pass. There were zero native arcs. The initial tuple/list scenario comparison
was corrected by JSON normalization before arithmetic; scientific values did
not change. 49 D13 tests pass; Ruff, strict OpenSpec, links, diff and legacy pass.
Full-suite evidence is reused from D13.2: 3,996 tests in 598.51 s. No runtime code
changed in this report-only stage.
