# 0282 — Qualify artificial completed-owner observation

Date: 2026-11-27
Decision status: accepted
Implementation: F18.15 complete; artificial/source/regression verification complete, actual native path unqualified
Scope / milestone: M3, private single-forward producer and independent auditor
Base revision: e9fed9caf1c1269b95a9c35327bd8fafa761f967 plus four new uncommitted source/test files pinned in the result; checkout/status frozen during both regression lanes
Related OpenSpec: [research requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; implements the narrow preparation in [0281](0281-design-single-completed-owner.md)

## Context and constraints

The next unresolved seam is reading one completed original forward owner, rather
than the successful never-run/refusal from0280. ADR0281 fixes original numerical
settings, metadata, selected epoch, counts and limits. Its artificial qualification
does not admit a new native episode or qualify the full original lifetime packet.

## Options considered

- Copy the old parent/supervisor and retag setup-only admission: unnecessary
  duplication and invalid inherited integration0 authority; rejected.
- Add only a minimal private producer and saved-only auditor, reuse existing guards,
  evidence/JSON/clock and independent metadata/word validators: selected.

## Decision and rationale

[Producer](../../src/space_nav/_owner_completed_probe.py) retains original
forward(True)→original metadata→same-owner endpoint(True). It checks narrow counts
before native entry, including after marker fsync, and rejects selected epoch0.
[Auditor](../../src/space_nav/_owner_completed_audit.py) independently checks
metadata/finite canonical words/epoch1000, separate callbacks/native count and
original Fraction(binary64 literal) polynomial gates in SI. Its guarded CLI reads
bounded saved files only; it cannot import producer/scientific runtime.

Only two private modules and two test files were added. Original fixture, Budget,
factory, scientific helpers, old tests, environment and dependencies stay unchanged.
No new parent/supervisor/admission framework is supplied. Old setup-only schemas
and0278/0279 admission remain unchanged and cannot authorize integration1.

## Evidence and verification

[Result](experiments/0282-completed-owner-qualification.json) and
[immutable evidence](experiments/0282-completed-owner-qualification-evidence.zip)
retain exact source pins, source review, focused/full JUnit, clocks and frozen status.

- One focused artificial invocation:212passed,0failure/error/skip,
  0.862225042s<300. Real original metadata is exercised on fake
  owners. Tests cover every marker fsync failure, pre-entry counter drift, exact
  selected epoch, malformed primitive words, schema/hash/mode/metadata/clock/byte
  errors and separately guarded producer→saved-auditor wiring.
- Independent numerical tests use Decimal.from_float at adjacent binary64 gate
  boundaries and reject combined-vector norms exceeding the original gates.
- Required `make test`:8275portable+413live=8688passes,42unchanged archival skips,
  0failures/errors, 806.282230s<1800. All previous IDs
  and skip reasons match byte-pinned0274JUnit; all212newcases are portable, the
  lanes are disjoint and focused cases are not counted twice.
- All1592checkout files and Git status remained
  fixed through both lanes; all1588
  prior tracked blobs match the base before documentary packaging.
- Independent connected code review and full Ruff pass. Ruff's first default-cache
  attempt was blocked by sandbox cache permissions; `--no-cache` passed without a
  code change. Documentation checks/strict OpenSpec are separate from runtime tests.

Pre-run review added a counter check between provenance and context. Its retained
pre-edit file is explicitly an inverse reconstruction of the single insertion,
not an originally captured snapshot. This was a source recommendation before the
first test, not a failed scientific experiment. All focused/full tests passed on
the first invocation. Existing required live regressions retain their native/SPICE/
integration scope; the new completed-owner diagnostic was never executed.

## Consequences and revisit conditions

F18.15 artificial probe/audit preparation is complete. The next reversible step
is a separately reviewed/qualified minimal outer profile/control/admission mapping
with exact source pins and bounded artificial checks. It must enforce changed
scope/counts/ten-marker protocol rather than reuse setup-only authority.
ActualF18.16 still needs a distinct recorded execution choice and fresh independent
actual600s admission; original60s45/10/5 and all byte/resource/numerical caps remain.
No mount, resource acquisition, saved real-data replay or new native/SPICE/
integration diagnostic occurred here. Revisit only for a concrete failed check or
accepted contract change; do not repeat passed tests on unchanged sources.
Full0267twoarc/lifetime, carry/concurrency/full-coreABI-FP/prior arithmetic/full-force
seed/derivatives/guards/endpoint bounds and physicalF0/M3 remain open. No admissible
command pair,99-percent probability or mission-safety conclusion follows.
