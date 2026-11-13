# 0180 — Prepare the split Moon integration recheck

Date: 2026-11-14 (Europe/Samara)
Decision status: accepted preparation under [ADR0179](0179-design-split-moon-integration-recheck.md).
Implementation: R5.33 complete in private experiment helpers.
Verification: fixed-state archive replay, synthetic integration and guarded regression passed; R5.34 not executed.
Scope / milestone: M3 R5.33; numerical model A recheck preparation.
Base revision: `f06d51fdc192c5ef7ac8aea1a6f05d049176862a`, clean `dev` at the start of preparation.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none. Historical R5.17 evidence is preserved.

## Context and constraints

[ADR0178](0178-consolidate-lunar-force-coverage.md) established both Moon
force verdicts on 28 frozen observations. To feed that acceleration
into DOP853, the force path must use the actual Moon/Earth return at
each RHS and shared output node, with the original rephasing and
controller. The archive is a fixed-input control; it cannot predict
the trial states or timing of the future real run.

## Options considered

- Change the public propagation path: premature for a bounded research
  check and would change other models.
- Use the private R5.17 harness and freeze a new version with a separate
  raw state leg and independent audit: selected. Reuse the immutable
  input loader, tested DOP853 observer and compatible audit/reference
  helpers while keeping the historical run reproducible.

## Decision and rationale

The [integrator](experiments/0180-split-integrator.py) keeps raw Earth/SSB
and Moon/Earth positions in km through exact scaling and relative
subtraction, then rounds the Moon separation once. It still uses the
direct Moon/SSB velocity for signed rephasing. The [study](experiments/0180-split-study.py)
checks normal-only gates before tighter starts. The [sample reference](experiments/0180-split-reference.py)
uses three distinct records at each required epoch within an observation;
the separate [audit](experiments/0180-split-audit.py) reconstructs the
state requests, geometry, fields and derivative without candidate math.
The [launcher](experiments/0180-split-launch.py) binds the tested source,
exclusive attempts, receipts and external deadlines.

## Evidence and verification

- On all 28 archived rows, the candidate reproduced exact pre-round
  separation and binary64 separation and acceleration bits. The 17
  measured or bit-identical controls use the R5.24 expectations; the
  other 11 use the R5.30 measured arm. Sun and Earth geometry and the
  signed Moon rephasing agree with the saved operands.
- The analytic injected orbit covers both profiles, all 21 trajectory
  comparisons, 28 force observations and the independent audit.
  Observer on/off results agree exactly in both profiles. Tests also
  cover cancellation, nearest-even ties, signed time, bad state
  identity, mixed units, guards, late returns and receipt failures.
- 90 focused tests passed. Full guarded regression: 6126 passed,
  407 skipped in 92.61 s. The
  [existing guard](experiments/0170/pytest-no-spice-guard.py.txt)
  blocks live bindings and direct CSPICE loads; the skipped tests
  require live access. Ruff, strict OpenSpec, links, diff, archive
  hashes and frozen checkout checks passed. The
  [verification manifest](experiments/0180-verification.json)
  pins the source, references and test receipts.

## Consequences and revisit conditions

R5.33 prepares the path; no SPICE queries, retained ephemeris record
evaluations or real trajectory propagation took place. Real
convergence, the 60 s study and 10 s audit budgets, and numerical
acceptance remain unmeasured. R5.34 requires separate authorization.
R5.17 remains failed, M3 remains open and automation stays paused.
