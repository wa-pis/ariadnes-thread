# 0103 — Implement an isolated local lunar departure reference

Date: 2026-10-16
Decision status: accepted.
Implementation / verification: D13.2 complete; reference-case report pending.
Scope / milestone: M3 research pure two-body geometry; no finite-burn wiring.
Base revision: `0343852e323e518f056504be5b2d1d4dd4851a2b`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [0102](0102-consistent-lunar-departure-design.md).

## Context and constraints

D13 requires a locally consistent impulsive reference before attempting another
finite-burn correction. Changing the old seed in place would invalidate earlier
studies and silently change initial phase. The new calculation must remain pure
and explicit, without SPICE calls, propagation or automatic branch selection.

## Options considered

- Alter the production seed or existing research pipeline: rejected; would mix
  a new impulse model with an unapproved finite-burn mapping.
- Build a generic maneuver/optimizer framework: rejected; unnecessary for the
  single circular lunar parking geometry in the accepted scope.
- Isolated private pure module: selected; uses existing orbit/spacecraft records,
  validation, vector helpers and sequential rocket-equation duration arithmetic.

## Decision and rationale

`lunar_departure._lunar_departure_reference` accepts explicit orbit, lunar mu,
parking radius, outgoing excess velocity, epoch, phase policy, spacecraft,
provisional arrival impulse and available interval. The caller supplies trusted
physical constants; there is no manufactured ephemeris or implicit launch date.
The result is immutable, deterministic and labelled Moon-relative/J2000/SI/TDB,
with a virtual periapsis epoch rather than ignition. It enumerates both free
phases in ascending order or checks the fixed phase. Infeasible/near-degenerate
cases have explicit statuses and no fabricated branches.

Each branch constructs the hyperbolic periapsis state and full vector impulse,
then independently reconstructs the conic via angular momentum/eccentricity
vector and checks asymptote, radial speed, position/velocity and energy at the
unchanged ADR 0102 tolerances. Recompute sequential mass and duration estimates
from the vector impulse norm. Dry-mass or duration-window failures remain
rejected diagnostics, not usable commands or mission-feasible states. Retain
both branches even when ideal fuel differs; no automatic best-branch selection.

## Consequences and revisit conditions

No new dependency, public export/CLI, scenario mutation, guidance change or
integration with live propagation. Preserve all historical source/evidence and
the legacy model. A later contract must map virtual impulse time to ignition
and cutoff and define finite-radius matching before any native departure trial.
Strict M3/task 3.9 stay open; UI unchanged and automation paused.

## Evidence and verification

49 new tests cover a closed-form e=2 example with two known phases and impulse
norms, rotated planes, eccentricity-vector/asymptote/energy reconstruction,
fixed phase, infeasibility/near-degeneracy, unsupported/nonfinite inputs,
invariant corruption, metadata/determinism and rejected mass/window estimates.
Decimal (50 digits) independently verifies sequential mass and duration.
436 focused D7–D13/guidance/controls/composer tests pass in 2.80 s.
Ruff, strict OpenSpec and unchanged legacy checksum pass. Full suite: 3,996 tests
pass in 598.51 s. No change to native dynamics, earlier contracts or public APIs;
no non-propagating reference-case report or native mission study in this stage.
