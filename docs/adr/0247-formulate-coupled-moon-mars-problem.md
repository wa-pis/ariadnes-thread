# 0247 — Formulate the coupled Moon-to-Mars problem

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (documentation and problem classification only)
Implementation: formulation documented; no new solver or benchmark implemented
Verification: documentation checks only; feasibility and numerical qualification remain open
Scope / milestone: M3 research planning in the sole active change
Base revision: `671522c86416b58158b66a74e486a5798eecbdf0`, clean `dev` before this stage
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-classify-the-coupled-mission-inputs-before-another-search), [formulation and table](../../openspec/changes/refine-physical-trajectory/design.md#coupled-moon-to-mars-formulation-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; prior methods, consumed attempts and boundary contracts remain preserved

## Context and constraints

The user requested a requirements/fixed-parameter/free-variable table and a
coupled Moon-to-Mars formulation, without calculations, followed by commit/push.
The [R1 reference](0119-positive-ideal-m2-reference.md) is a body-centre Lambert
coast with scalar escape/capture estimates; actual parking/insertion planes and
finite thrust did not constrain that search. The existing
[physical M3 requirements](../../openspec/changes/refine-physical-trajectory/specs/physical-trajectory-refinement/spec.md)
already specify full orbital boundary states and six finite-burn controls.
These are different problem fidelities, not interchangeable feasibility claims.

[ADR0212](0212-design-mars-capture-phase-seed.md) restricted the later analytical
surrogate to one Mars phase, retaining the historical dates, lunar impulse and
both excess-velocity vectors. [ADR0246](0246-record-bounded-retained-inconclusive.md)
retains an independently audited no-witness outcome, not a continuous refusal or
proof that the physical mission is impossible. Its authority is consumed.
The interpretation that the narrow design space limits this search is a
formulation diagnosis, not a new numerical result or proof of reachability.

## Options considered

- Substitute another scalar optimizer in the same analytical family: it could
  propose different samples, but would not establish a continuous physical
  transfer or reconcile the different boundary meanings. Defer method selection.
- Immediately free dates, orbit phases, planes or vehicle data: could change
  feasibility, but would alter the currently binding problem. Do not adopt it
  implicitly; identify the choices explicitly for a future contract.
- First formulate the coupled existing-boundary problem and classify each
  quantity: selected. Reuse the six existing controls, distinguish historical
  fixture choices from general requirements, and retain numerical gates.

## Decision and rationale

The linked OpenSpec design is the single table/formulation source. It defines
F0, a feasibility problem with the existing fixed initial/final orbital states
and epochs, two maximum-thrust TNW burns and one continuous full-force
position/velocity/mass history. M2 states and excess vectors supply a seed,
not additional physical endpoint equalities. Final mass is constrained below
by dry mass; it is not prescribed equal to that floor. R1 reserve claims retain
their separate 550 kg threshold and limited ideal-model scope.

A multiple-shooting transcription is a method candidate: auxiliary arc-start
states would be constrained by complete state/time continuity, without adding
impulses or physical control freedom. This stage selects no solver, number of
nodes, derivative scheme, integration profile or executable command pair.
Moving dates within the scenario window, freeing departure/arrival phase or
changing from an exact six-state target to orbit membership remains a proposed
mission-design extension. The current fixed phases and geometry stay binding.

Scientific motivation is scoped to the inspected primary sources:

- [NASA Trajectory Browser user guide](https://trajbrowser.arc.nasa.gov/user_guide.php),
  Overview and Trajectory solver: coarse Lambert surveys provide initial guesses
  for higher-fidelity design. This supports a staged workflow, not validation of
  our lunar departure or our candidate.
- [Vavrina, Englander and Ellison, AAS 16-272](https://ntrs.nasa.gov/api/citations/20160001644/downloads/20160001644.pdf),
  Mission Modeling, pp. 3–5: direct multiple shooting constrains match-point
  position, velocity, mass and time. Its demonstrated impulsive patched-conic
  formulation is precedent for a transcription, not an already qualified
  finite-burn/full-force solver for Ariadna.

No new library, stack migration, optimizer extension or scientific execution is
selected. Before implementation, a separate method/benchmark contract must name
explicit inputs and variables, an independent reference, tolerances and finite
work/time limits, using the pinned stack and preserving the current requirements.

## Consequences and revisit conditions

This makes the next design review checkable without silently changing a target.
F0 can be assessed as currently specified; its feasibility remains unknown.
Any proposed variable enlargement must identify the exact changed boundary,
user choice and affected requirement before becoming an executable problem.
Do not free orbit planes/apsides, enlarge mass or thrust, alter kernels or loosen
accuracy merely to obtain a pass. Any benchmark or future solver must distinguish
search convergence, physical closure, numerical qualification and mission safety.

[ADR0135](0135-fixed-orbit-boundary-contract.md) and
[ADR0205](0205-design-fixed-command-physical-join.md) retain their boundary,
error-bound and execution prerequisites. Shooting continuity cannot bypass them.
R5.60, all consumed studies, strict M3/task 3.9 and later milestones remain closed
or unresolved as before. Automation stays PAUSED; this docs-only instruction
provides no new execution authority. Revisit the formulation when a changed
mission constraint is explicitly adopted or a bounded independent benchmark
justifies a specific method; a lower surrogate cost alone is insufficient.

## Evidence and verification

Read the current scenario and authoritative boundary/force/control requirements,
ADR0119/0135/0205/0212/0246, and the two primary sources above. Values in the table
are transcribed from existing records; no new scientific arithmetic, saved-phase
evaluation, kernel access, SPICE query, force evaluation or integration occurred.
Verification passes: strict OpenSpec, 533 local links and four anchors across
the eight changed Markdown files, three new requirements/six WHEN-THEN scenarios,
CURRENT_STATE under 60 lines, factual/diff checks and a separate read-only
scientific review. All 1081 previously tracked non-Markdown files, including
code, legacy and retained evidence, remain byte-for-byte unchanged. Runtime
tests are not rerun for this documentation-only stage; prior test/CI evidence is in
[ADR0245](0245-qualify-retained-dispatch-lifecycle.md), without a fresh test claim.
