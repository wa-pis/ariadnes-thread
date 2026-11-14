# 0189 — Prepare the post-cutoff model B study and audit

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted implementation of [ADR0188](0188-design-post-cutoff-lunar-coast.md).
- Implementation: R5.42 complete. R5.43, the once-only live study and offline audit, remains unexecuted.
- Verification: synthetic study, separate saved-data audit and guarded regression pass.
- Scope: conditional 600 s coast from the archived nominal departure cutoff. No burn replay or model A.
- Base revision: `d21ba516a66dc27a93d781772e64e56b576ce3bb`; exact tested and frozen input hashes are in the manifest.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-the-fixed-post-cutoff-lunar-coast),
  [design](../../openspec/changes/refine-physical-trajectory/design.md#r542-prepare-the-post-cutoff-study-and-audit-2026-11-14)
  and [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

ADR0188 selects the exact simulated 0079 departure cutoff reproduced
in 0098. The original target was not closed. R5.42 prepares a new
numerical comparison at that archived input, and a separate check of
whether the spacecraft moves away from the Moon at common nodes.
No live ephemeris data or real force/record evaluations are needed
to test the preparation.

## Options considered

- Alter the archived R5.40 runners to accept either initial state:
  would change historical evidence and risk allowing the parking prefix
  into a different trajectory.
- Keep new private entry points and reuse the immutable, hash-checked
  R5.40 force, guard and integration primitives: selected. This keeps
  one copy of the tested physical and numerical controls and a separate
  evidence chain for the new assumption.

## Decision and rationale

The [input binder](experiments/0189-post-cutoff-inputs.py) binds the
exact cutoff epoch, six state words and burn mass to both historical
records, checks represented burn-time mass arithmetic and validates
the required Type 2 coverage by metadata. The
[study](experiments/0189-post-cutoff-study.py) restarts all four
profiles from the identical state. It checks 39 new comparisons
over 13 coepochs, even when the craft does not move outward. The
mass is an explicit constant label; there is no mass integration
or thrust on this coast.

The [offline audit](experiments/0189-post-cutoff-audit.py) reconstructs
the handoff, sampled forces, adaptive RHS/outputs, native guards and
telemetry, comparisons and counters from saved operands. It does not
import the study or a scientific package. The study measures radius,
radial speed and osculating energy from the shared saved Moon state,
and the [direction verifier](experiments/0189-post-cutoff-direction-audit.py)
independently checks 52 rows and four net ranges using exact Fraction
signs and 80/100-digit Decimal arithmetic. In particular, a rounded
zero speed cannot hide a nonzero exact sign at a classification
boundary. A direction verdict requires numerical acceptance and
finalized study and audit receipts. The audit child records its
verified findings; an audit parent failure still precludes acceptance.

The [launcher](experiments/0189-post-cutoff-launch.py) requires
clean synchronized dev and an externally pinned preparation manifest.
It reserves exclusive attempts and binds results to their receipts,
with the unchanged 60 s study / 10 s audit budgets. Its watchdog and
receipt paths were tested using a mocked child.

## Evidence and verification

Both DOP853 profiles reached 600 s using artificial sources; native
RK4 histories were injected, with 601 and 1,201 guarded states.
The outward and inward fixtures each passed 39 comparisons, 52 force
observations, 26 native telemetry checks, 52 direction rows and four
net-range signs. The tighter adaptive endpoint range changed by about
+60 km and -60 km, respectively, as expected for the artificial
initial speeds of +100 and -100 m/s over 600 s in the weak test fields.
The outward fixture logged 4,424 RHS evaluations, 362 trials, 17,748
adaptive state requests and 5,412 native guard reads, all synthetic.
The audit retained the distinct outward and not-established verdicts
and replayed the outward evidence in a fresh stdlib-only process.

Tests reject shifted or wrong event data, changed mass, force telemetry,
comparison and direction corruption, incomplete preparation pins,
invalid receipts, overruns and reused evidence paths. An injected
telemetry failure stops before any adaptive work; the independent
audit reproduces it and leaves the direction unavailable.

The [manifest](experiments/0189-verification.json) records test counts,
synthetic result hashes, guarded regression and frozen files. All
52 focused tests pass. Guarded regression: 6,141 passed, 494 skipped.
Ruff, strict OpenSpec, links, hashes, diff and protected bytes pass.
The [test guard](experiments/0189/pytest-offline-guard.py.txt) blocked
native SPICE imports or loads and excluded known evaluations on
retained real force or polynomial operands. R5.43 was not started.

## Consequences and revisit conditions

The preparation is ready for separately authorized R5.43. Real
post-cutoff convergence, outward motion and budgets are unmeasured.
No previous result, accepted scientific threshold, mission
qualification or strict M3 status changes. Automation remains paused.
