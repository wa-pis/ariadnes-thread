# 0191 — Verify a lunar range event from saved states

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted for an offline research diagnostic.
- Implementation: R5.44 design complete; R5.45 worksheet, tests and result pending.
- Scope: retained R5.43 model B coast of candidate `d0001-t0035`.
- Base revision: `3ca3f7bed36b4e1ab77e66c0199b8e42783fa02a`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-a-retained-lunar-range-event), [design](../../openspec/changes/refine-physical-trajectory/design.md#r544-design-the-retained-lunar-range-event-2026-11-14), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[ADR0190](0190-post-cutoff-coast-outbound-at-samples.md) shows that
all four B profiles were outbound at the samples. It leaves the
maximum reach, any continuous outward motion, and the mission
handoff unverified. [ADR0135](0135-fixed-orbit-boundary-contract.md)
defines the real interfaces as exact burn cutoff and ignition
states with unchanged full-model dynamics on either side. A range
marker is an observation of the coast, without a switch in forces
or a new arrival target. Model B stays the Sun/Moon/Earth point-mass
model in SI, SSB/J2000, TDB seconds since J2000 and NONE.

[ADR0105](0105-local-finite-burn-contract.md) used 18,374,000 m
(ten times the declared parking-orbit radius) as a diagnostic
comparison surface. The largest saved R5.43 common-node radius is
about 3,438,655 m. The data do not bracket the ADR0105 surface.
Do not use an inferred velocity or energy to extrapolate to it.

## Options considered

- Extend the coast now to a larger radius or change frames at a sphere:
  requires a new covered horizon, work budget, and separate live-run
  authorization; a force switch would also change the mission contract.
- Fit a root to the saved points and report a crossing epoch: this
  introduces an interpolation model with no bound on event-time error.
- Verify a fixed retrospective marker from saved operands in both
  engines: selected. It tests range-event evidence and bracket
  resolution with zero new integrations, and can be reused when a
  meaningful farther comparison is designed.

## Decision and rationale

Use 3,000,000 m from the lunar centre as a named research marker
inside the retained span. It is a round-number software check
selected after seeing R5.43, so even a pass is not a prospective
prediction or a substitute for the 18,374,000 m comparison.
Bind the [R5.43 manifest](experiments/0190/manifest.json), its
compressed and original report digests, receipt chains, and
[design input](experiments/0188-design-inputs.json). Preserve the
exact archived cutoff and constant mass metadata, kernels, time
grid and original before/after attestations. No new SPICE/kernel
access, record evaluation, solver, model A, control or burn replay.

Use the four 13-node profiles with their shared Moon states and
the 601 and 1,201 raw RK4 state records with their corresponding
Moon guard six-states. Exclude the single Moon preflight row in
each RK4 history. Join by the expected epoch and group; reject
gaps, duplicates (including alternate spellings of one epoch),
mismatched state and frame identities, or nonfinite values. Use
both archived raw solver operands and the audited node records
for the 13-node grids; do not use a rounded radius as a sign.
Check the original 0.01 m / 1e-5 m/s native and tighter
cross-engine coepoch gates and 0.001 m / 1e-6 m/s DOP853 gate as
retained prerequisites, without requalifying the numerical study.

For each row derive Moon-relative range and radial speed in two
ways: exact dyadic squared-radius and radial dot-product
comparisons with binary64 metrics, and a separately implemented
80-digit Decimal calculation from the original binary values.
The two sign paths must agree exactly; the continuous-valued
metrics must agree within the existing direction arithmetic
gates of 1e-6 m and 1e-9 m/s. At overlapping native/coepoch
records require equal spacecraft state words and consistent Moon
operands; require equal signs and metric agreement within these
gates, allowing identical-epoch Moon operands to follow the saved
paths. Only matching `below, above` signs in adjacent retained
rows with positive endpoint radial signs support a bracket.
Treat exact equality, an inward pair or more than one strict
outward pair as distinct unresolved evidence for that profile.

Require exactly one strict outward pair on each of the six
grids; the four 50 s brackets must coincide. The 1 s and 0.5 s
native brackets must overlap and each must lie inside the common
bracket. Report the signed endpoint operands, both geometries,
individual brackets and the common interval. The overlap is an
agreement diagnostic, not a substitute for the valid bracket of
either individual trajectory. No root interpolation or finer
DOP853 bracket is required. The sign change brackets at least
one crossing for each continuous trajectory represented by its
endpoints. The evidence does not prove first or unique physical
crossing, exactly timed state, continuous clearance or escape.

## Consequences and revisit conditions

The one offline evidence run is limited to 10 s through saved
evidence finalization, exactly 52 coepoch and 1,802 retained
native rows, zero native calls/imports of scientific packages,
zero kernel loads and zero integrations. Synthetic tests must
exercise exact zero, below/above and inward signs, multiple
brackets, overlapping and disjoint brackets, epoch/digest
mismatches and late finalization before use of retained data.
Keep the first failure and partial report; no retry with a changed
marker or gate. No user decision is needed for this offline step.

For a later farther-range experiment, first pin a covered horizon
from the same verified B boundary, compare independently detected
strict sign brackets and event states at common epochs using the
unchanged profile gates, and bound the cost before seeking a
single authorization. An event-time error bound needs independent
trajectory-error evidence and a lower radial-speed bound in the
interval; arithmetic root convergence alone cannot supply it.
The diagnostic comparison surface does not replace the exact
interfaces and fixed Mars target of ADR0135. Full-force accuracy,
strict M3 and mission safety remain open.

## Evidence and verification

R5.44 inspected saved metadata, raw record layouts and stored
metrics only. There are four saved 13-node profiles and 601/1,201
native positions with matching Moon guard inputs, plus one
preflight entry per native history. The retained common nodes at
+200 s are near 2,990,376 m and the +250 s nodes near 3,043,942 m.
No R5.45 sign audit or crossing result is asserted by this design.
Checks: source and archive digests, local links, diff and strict
OpenSpec. No runtime or test code changed; the full suite was not
rerun.
