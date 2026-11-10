# 0170 — Prepare the frozen-coast Moon force screen

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted implementation of the ADR0169 design.
Implementation: R5.23 complete; R5.24 not run.
Verification: synthetic arithmetic and runner tests, archive metadata checks,
and guarded regression. No scientific screen result.
Scope / milestone: M3 R5.23; private offline preparation.
Base revision: `497600585673ef27c6ece2a979f526d245d0df2e`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none.

## Context and constraints

[ADR0169](0169-screen-split-moon-on-frozen-coast.md) fixed the sample, archived
inputs, original Moon point-force gates and one future offline attempt. Prepare
the code and verify it without running that attempt or issuing new SPICE
queries. The historical R5.17 negative result and incomplete identity are
inputs to the evidence, not targets to rewrite.

## Options considered

- Patch the production provider or coast solver: would change the system under
  study before the frozen-state calculation could isolate the Moon source.
- Use a private, standard-library runner with the tested R5.20 evidence
  primitives and a separate archived input loader: chosen. It adds no runtime
  dependencies or production behavior.

## Decision and rationale

The [loader](experiments/0170/ariadna_frozen_moon_inputs.py) verifies the saved
R5.17 and finalized R5.21 evidence, original constants, exact time words and
record coverage. The [arithmetic](experiments/0170/ariadna_frozen_moon_math.py)
evaluates exact rational Type 2 positions and velocities and preserves
separate E/G source terms, signed direct-Moon rephasing and the saved spacecraft
motion. It compares each returned and ideal geometry at 80 and 100 Decimal
digits using the original gates. It keeps measured and proxy inputs distinct
and checks the three measured controls separately from the archived direct
verdicts. None of these arithmetic checks were run on the archived sample
during preparation.

The [runner](experiments/0170/ariadna_frozen_moon_run.py) records each attempt
and raw return, keeps per-row outcomes and the first failure, and rechecks
source and archive hashes before accepting finalization. Admission ledger
entries count rows and unique epochs before work; per-row verdicts and the
record, binary64 and Decimal entries show which evaluations completed. The
future run remains exclusive, with the 10 s inclusive deadline and 15 s
watchdog. Tests simulated late return, finalization at and after the deadline,
changed identity, existing evidence and watchdog expiry. This is not a
measurement of the archive calculation's runtime.

## Consequences and revisit conditions

The prepared runner may be used for the one R5.24 offline screen when
requested. A later positive screen is conditional for the 28 frozen
observations; it cannot certify real G at the 16 unmeasured hi epochs, new
propagation, R5.17, strict M3 or mission safety. Automation remains paused.

## Evidence and verification

- [Manifest](experiments/0170-verification.json): original inventory and
  unchanged baseline, tested helper hashes, evidence hashes and scope.
- [Focused pytest](experiments/0170/pytest-focused.txt): 40 passed on analytic
  fixtures, archive metadata and failure paths. Synthetic cases exercise the
  full 28-row shape, 29 reference epochs, all caps and both signs of the low
  word. Metadata checks evaluate no archived polynomial or force.
- [Guarded regression](experiments/0170/pytest-guarded.txt): 5916 passed,
  407 skipped. The [guard](experiments/0170/pytest-no-spice-guard.py.txt)
  rejects installed TudatPy/SpiceyPy imports and direct CSPICE loading;
  [skip inventory](experiments/0170/pytest-guarded-skips.tsv) records exclusions.
  No unrestricted pytest run was performed for this revision.
- Ruff, strict OpenSpec, local links, hash and diff checks passed. The
  remaining 685 baseline files, including
  production sources, previous evidence and `moon_to_mars.py`, were unchanged.
  Zero new SPICE requests, record acquisitions or trajectory propagations;
  the R5.24 attempt was not created.
