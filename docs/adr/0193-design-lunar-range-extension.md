# 0193 — Design a 50 s lunar range extension

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted for one bounded model B experiment.
- Implementation: R5.46 design complete; R5.47 preparation and R5.48 live verification pending.
- Scope: the unpowered lunar departure of the unchanged research candidate `d0001-t0035`.
- Base revision: `c1a67e1d33717af97e1194459ec501c46c07f8dd`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-a-prospective-lunar-range-marker), [design](../../openspec/changes/refine-physical-trajectory/design.md#r546-design-the-prospective-lunar-range-extension-2026-11-14), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[ADR0192](0192-retained-lunar-range-event-bracketed.md) verified
retrospective sign brackets in the saved 600 s coast. It did not
test a previously unobserved radius. [ADR0135](0135-fixed-orbit-boundary-contract.md)
defines actual mission joins at burn events. The extension keeps
one inertial frame and one model B force law throughout; its range
marker supplies no mission join or force switch.

## Options considered

- Jump straight to [ADR0105](0105-local-finite-burn-contract.md)'s
  18,374 km comparison surface: the archive gives no bracket
  there, and the 600 s resource evidence cannot bound the cost of
  a much longer propagation.
- Repeat all 600 s and extend: unnecessary to test a shared
  initial state at the saved boundary.
- Extend 50 s from one archived B endpoint toward a fixed new
  marker and independently check the samples: selected.

## Decision and rationale

Use exactly twice the pinned lunar shape radius: 3,474,800 m
from the lunar centre. This is a reproducible diagnostic scale
independent of any fitted crossing time. The tighter RK4 endpoint
radius is 3,438,654.733159515 m with radial speed +1,167.0594500326567
m/s. The gap is about 36,145 m; dividing it by the endpoint radial
speed gives roughly 31 s as a planning heuristic only. Fix the
horizon at 50 s, whether the marker is reached or not.

Restart all four profiles from the same archived tighter RK4
six-state at `978998915.9635216` TDB seconds since J2000 (+600 s
after cutoff), with mass metadata `1351.7475727997967 kg`. Bind the
terminal sampled and raw history words and the audited R5.43
operands. Record signed differences between all archived endpoints
and the selected state; only the tighter RK4 branch is continued
from its own endpoint. All four new starts must match the chosen
state and epoch bit for bit. No reset of the original mission
cutoff, mass, burn or target state is implied.

Keep the Sun/Moon/Earth direct point-mass model B, GMs, shape radii,
SSB/J2000/SI/TDB/NONE, exact kernel order and runtime, zero thrust
and zero mass flow. Fixed comparison epochs are restart plus
0, 5, ..., 50 s, ending at `978998965.9635216` TDB seconds. The
pinned record intervals contain the closed extension strictly,
which is a metadata check, not a new SPICE observation. Check the
initial common Moon/SSB state against the archived node words.
No event-only body queries. No new A arc or burn/parking/prefix replay.

Use RK4 at 1 and 0.5 s and the unchanged R5.43 normal/tighter
DOP853 profiles. Compare three pairs at all 11 coepochs: native
step and tighter cross-engine gates 0.01 m / 1e-5 m/s, adaptive
step gate 0.001 m / 1e-6 m/s (33 comparisons). Keep existing force
gates and five kinds of evidence: both native guard histories,
22 native telemetry rows, 22 adaptive output observations, the
first seven completed RHS callback ordinals per adaptive profile
(at least one nonzero low epoch residual per seven), and saved
before/after identities. The 36 adaptive observations include
both output and RHS observations. Replay all saved adaptive RHS
arithmetic and inputs in the independent audit.

Use exact squared-radius and radial dot-product signs and
independent Decimal arithmetic on the 44 coepoch and 152 native
mesh operands, with the existing 1e-6 m / 1e-9 m/s arithmetic
gates. Preserve all raw signs and each adjacent bracket. An
audited `marker-bracketed` requires one strict below-to-above pair
with positive endpoint radial signs on each grid, agreement of
the four coepoch brackets, and positive-width native overlap
with both mesh brackets contained in the common 5 s bracket.
An audited lack of a bracket, exact equality, inward/multiple
pairs or bracket disagreement is `marker-not-established`
with a specific reason. Incomplete evidence, numerical or audit
failure yields `unavailable`. Do not interpolate a crossing
epoch, stop early on a marker or extend the interval.

## Consequences and revisit conditions

First prepare with artificial inputs only, without changing the
frozen R5.43/R5.45 scripts, production settings, dependencies or
archived sources. Verify the exact shared start, caps, signs,
positive and negative classifications, identity and receipt
handling and failure paths with focused tests, guarded full
pytest, Ruff and strict OpenSpec.

R5.48 needs separate authorization after preparation. One study
and one stdlib-only independent audit have inclusive caps of
60 s and 10 s with parent watchdogs and bound phase receipts.
Maximum work: two native arcs, two adaptive solves, 10,000 RHS,
1,000 trials, one pool setup, 30 inventory calls, zero GM
acquisitions, 40,044 explicit adaptive state attempts and 462
native guard reads (40,506 explicit total, excluding internal
Tudat lookups). The [manifest](experiments/0193-design-inputs.json)
fixes the arithmetic and sample caps. A failed gate or incomplete
finalization preserves partial evidence without retry. An
audited `marker-not-established` also consumes the attempt; no
alternate radius, longer window or tolerance change.

Even success is a same-model sampled bracket conditional on a
simulated inherited state. It does not establish first/unique
physical crossing, continuous clearance, escape, arrival
connectivity, full-force accuracy or strict M3. The next farther
comparison requires its own scientific purpose and budget.

## Evidence and verification

Static readback verified the saved restart words, archived
coepoch agreement, the R5.45 provenance, exact time grid and
strict inclusion in all three retained SPK record intervals.
No new ephemerides, force evaluations or trajectories. Links,
frozen hashes, diff and strict OpenSpec passed; no runtime code
changed or tests rerun.
