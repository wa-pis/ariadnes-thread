# 0281 — Design one completed forward-owner observation

Date: 2026-11-27
Decision status: accepted
Implementation: not started; source/design review complete, runtime qualification pending
Scope / milestone: M3, F18.14; private synthetic native seam
Base revision: f39b2f6ec85dd1fa7ba3d06c034ea998a09b89f2 (clean source review)
Related OpenSpec: [research requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; earlier results and consumed episodes remain intact

## Context and constraints

[0280](0280-verify-supplemented-never-run-setup.md) establishes only never-run
construction and the expected unavailable-results refusal. It does not exercise a
completed simulator. [0269](0269-record-owner-producer-timeout.md) retained no
trace or scientific packet; its cause and internal native counts remain unknown.
Repeating the full two-arc/lifetime packet would confound the next observation.

## Options considered

- Repeat the full original packet: too many unresolved operations; not selected.
- Read a tuple without original metadata: cannot establish successful exact
  completion or the meaning of its seven components; not selected.
- One original forward construction, one metadata observation and one same-owner
  chronological-last visitor: selected as the smallest useful completed-owner test.

## Decision and rationale

The [machine contract](experiments/0281-completed-owner-design.json) is the exact
reviewed draft, retained unchanged. Its draft label records review chronology;
this ADR accepts its design without granting execution authority.
Use unchanged `_native_factory("forward", True, budget)`, `_metadata(owner)` and
`owner._ariadna_original_endpoint(True, "cartesian-position-m_velocity-m-s_mass-kg")`
in that order. Never call the broader `produce()` routine.

Freeze the existing synthetic seven-state `(10000000,0,0,0,1000,0,2000)` in SI,
constant acceleration `(0,float(0.1),0)` m/s², zero mass rate and elapsed0–1000s.
This is synthetic elapsed time, not mission TDB ephemerides. Preserve the tighter
coast RKDP87 settings, exact final time and retained original results from0267.
No physical force, state, kernel, tolerance or dependency changes follow.

Precharge exactly1context/1factory/1integration attempt/1metadata helper/1visitor.
An attempted integration is not a completed integration; partial native getter
counts remain UNKNOWN. Record actual callbacks0..100000 separately from the one
nonnegative native function-evaluation report. Ten ordered fsynced markers bracket
factory, metadata and visitor; each<=512B and all<=4096B. Markers bracket whole
operations and observer I/O, not a native instruction or the old failure cause.

The independent stdlib-only auditor requires original successful exact termination,
seven-state row IDs/descriptions, finite primitive binary64 tuple and specifically
hour0/remainder1000 for selectorTrue. Original decoder acceptance of0or1000 alone
is insufficient. Its independent polynomial uses Fraction of the actual binary64
literals, including `float(0.1)`, rather than decimal1/10 or a producer reference.
Unchanged Euclidean gates are0.001m position,1e-6m/s velocity and1e-9kg mass.
No formula or numerical result was evaluated during this design.

F18.15 may prepare and artificially qualify the two minimal private probe/audit
modules, reusing existing guard/evidence/watchdog primitives. Keep original
fixtures/settings/helpers intact. Old setup schemas and0278/0279 admission enforce
integration0; they cannot simply be retagged. Any changed outer controls need
new explicit pins, an artificial qualification and independent review before use.
Avoid a general orchestration framework. Future admission preparation remains
separate from actual F18.16 execution.

Retain future600s fresh preflight and60s inclusive producer45/audit10/finalization5,
65s failure-only outer failsafe,64KiB input/combined logs,2MiB aggregate structured
outer/inner evidence,8GiB scratch and2GiB carried acquisition ceiling. Retained
11resources require identity verification; new acquisition is zero. The successful
setup timing does not predict completed-arc runtime. Artificial focused checks have
300s; required frozen portable/live regression has1800s plus Ruff/strict validation.
Existing required live regressions, including their SPICE/integration fixtures,
remain permitted; the prohibition concerns a new diagnostic/scientific episode.
Actual execution needs a distinct recorded choice, new qualified sources/control
matrix, clean committed dev and independently observed fresh actual admission.
Neither this design nor artificial PASS admits F18.16.

## Consequences and revisit conditions

This isolates completion and endpoint meaning while preserving original numerical
semantics. Native success is still unobserved. A timeout or metadata/endpoint failure
must retain its first failure and counts/unknowns without retry or clock reset.
Revisit only from retained evidence and a separately justified changed contract.
Full0267 two-arc/eight-call/lifetime qualification, carry/concurrency/full-core ABI-FP,
prior arithmetic/full-force seed/derivatives/guards/endpoint bounds and physicalF0/M3
remain open. No admissible command pair,99-percent probability or safety claim.

## Evidence and verification

[Immutable evidence](experiments/0281-completed-owner-design-evidence.zip) retains
the original clock, draft,49source/5reference pins,9literal source excerpts and
independent source/design PASS with no findings. Review receipt was durably
observed at405.557187s; accepted source phase completed at428.921197375s<600,
72754B of temporary evidence<2MiB. Documentary packaging/checks occur afterward,
not as a restarted source-review clock. No mounts/live resource reads/native
imports/tests/SPICE/integration/acquisition/build or scientific calculations occurred.
Documentation verification checks links, artifact/source/protected-history identity,
diff and strict OpenSpec; runtime/Ruff campaigns on unchanged code are not repeated.
