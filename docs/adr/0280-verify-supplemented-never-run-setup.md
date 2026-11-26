# 0280 — Verify the supplemented never-run setup

Date: 2026-11-27 (Europe/Samara)
Decision status: accepted for retaining bounded diagnostic evidence
Implementation / verification: F18.13 complete; one native setup/refusal and independent saved audit PASS
Scope / milestone: M3 private setup diagnostic, without trajectory integration
Base revision: `fa726f953935e4cdad8e1ee74bcbf5b34fb6dbd4`, clean committed dev at admission
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f1813-supplemented-setup-result-2026-11-27), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture)
Supersedes / Superseded by: none; preserves0275failure and0277/0279contracts

## Context and constraints

[ADR0275](0275-record-failed-never-run-setup.md) stopped before factory return
because the isolated image lacked Earth-orientation resources. That consumed
attempt remains unqualified. [ADR0277](0277-design-supplemented-setup-test.md)
and [ADR0279](0279-qualify-once-only-execution-gate.md) define a distinct, once-only
supplemented diagnostic with fresh independent admission. The user's instruction
permits continued tests and ordinary reversible preparation, with recurring work
paused when a real user decision or action is needed.

## Options considered

- Reuse the consumed attempt or a saved PASS permit: rejected by the existing
  contract; neither is a fresh observed admission.
- Execute the accepted supplemented setup once through the qualified gate:
  selected after artificial checks and independent actual readback, preserving
  the original code, environment, settings, kernel and limits.

## Decision and rationale

Retain this result as qualification of the never-run setup/refusal seam. It
establishes that this fixed supplemented environment constructs the original
model with simulate=False and that the original visitor refuses unavailable
completed results. It does not establish completed-state readback or trajectory
accuracy. No integration or new scientific search was performed.

Before the actual preflight, independent source review found five operator
issues: late completion could retain success, early refusal could skip detach,
outer-session termination could leave nested groups, a failing failure receipt
could skip detach, and new outer records needed aggregate byte accounting.
All were corrected before the first artificial wiring invocation; exact initial
sources and findings remain in the archive. Seven new fabricated wiring cases
passed once, zero failures/errors/skips, externally observed after receipt fsync
0.1569900424219668s<120s,4007B. They cover timely/late completion, failed fsync,
rejected review, nested-session cleanup, aggregate overflow and failure-receipt
cleanup. Separate small helper assertions are retained. The successful prior
30/94/8476 campaigns and Ruff were not repeated on unchanged package/tests/deps.

## Evidence and verification

[Result and member manifest](experiments/0280-supplemented-setup-result.json),
[raw evidence archive](experiments/0280-supplemented-setup-evidence.zip), and
[document verification](experiments/0280-doc-verification.json).

The actual600s preflight clock started before the new episode's first write or
mount. Qualified no-replace provisioning added exactly six pinned local files,
3578887B, with immutable carried precharge500624382B<2GiB. All11resources,
3710549B, were read back and the image was remounted read-only. Independent actual
review checked49source/10native/25oldledger/9control pins, proofs, clean dev and
separate gate/interpreter identities. Review completed after fsync at35.650361s;
consumption occurred at57.157760416623205s<600. The final decision was generated
only after review, without mutating the pinned profile. One direct admit/gate
continuation executed the unchanged collector; no leftover-file-only launch.

The single native episode passed: context53/53/8, one factory('never-run',False),
zero integration attempts, one visitor(True,SCHEMA), and exact RuntimeError
`completed original results unavailable`. All eight ordered markers are retained
in1316B. Final counts are known: zero acceleration callbacks, SPICE queries,
optimizer entries, archive reads and explicit integration; no native function-
evaluation history exists because integration was not run. This is distinct from
0275's unknown partial counts. Producer finalization took3.308783416s; the actual
packet observation after the last recorded fsync was3.36752116587013s<60. Native
45producer/10audit/5finalization limits were unchanged;65s remained failure-only.

A separate guarded stdlib saved audit passed once, with startup and external
receipt fsync observed at0.046423207968473434s<10s. Independent saved review also
verified nested returned statuses, exit0, source/profile/decision/proof hashes,
original600/60 clocks, trace/counters, byte caps and cleanup/preservation records.
Its separate clock does not extend the native episode. Disk prefinal candidates
remain distinguished from actual post-fsync observations. The operator's packet
observation precedes separate post-result preservation/detach and packaging.

Postcheck preserved49source/10native/25oldledger/9control identities, all11resource
hashes, and71459operational environment paths/1646916124regular bytes. All recorded
groups are absent; a filtered process check found no setup/test/mount process.
The image was detached successfully. No repository runtime/test/dependency change,
new downloads, SPICE query or trajectory integration occurred. Protected history
and moon_to_mars.py remain unchanged. Raw UTC receipts are2026-11-26; client date
2026-11-27 Europe/Samara is consistent with them.

## Consequences and revisit conditions

F18.13 is complete and consumed. Do not rerun it, replay consumed F18.3/F18.9,
add resources or execute a full-owner packet by inference from this success.
The minimum next step is source/saved-only design of a completed-owner diagnostic
within600s/2MiB, including independent review, fixed question/inputs/arguments,
counts/clocks/audit and explicit future prerequisites. That step may prepare a
reviewable contract; it does not launch another native episode or relax any gate.
Automation remains ACTIVE every five minutes for that bounded preparation and
pauses if an actual user decision, data, access or action is required.

Completed-owner/carry/concurrency, full-core ABI-FP, prior arithmetic, full-force
seed/derivatives/guards/endpoint bounds and the physical F0/M3 gates remain open.
No admissible command pair,99-percent probability or mission-safety claim follows.
