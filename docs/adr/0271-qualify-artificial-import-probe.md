# 0271 — Qualify the artificial import-only diagnostic

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted for F18.5 artificial preparation only
Implementation / verification: complete for artificial preparation; focused/full regressions, independent review, Ruff and strict validation pass
Scope / milestone: F18.5 / M3 diagnostic preparation; no F18.6 execution
Base revision: `6195fe41cd1806eed484503e8ecbc6a78fbd30a6`; four new source/test files measured in the frozen working tree
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f185-artificial-import-only-qualification-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; retains ADR0270 and every consumed native episode

## Context and constraints

The user's continuation permits implementation and artificial qualification of
[ADR0270](0270-design-import-only-timeout-observation.md)'s import-only observation.
The previous F18.3 attempt remains consumed and unqualified. The next diagnostic
must stop before `produce()`, native context, factories, integration or visitors.
F18.6 still needs separate explicit authority and exact runtime/resource/control
admission. Existing required live regressions retain their authorized old scope;
they do not execute the new probe's native branch.

## Options considered

- Repeat the complete owner packet or alter its deadlines/temp permissions:
  rejected; neither follows from the saved evidence or this preparation.
- Extend the old pinned owner runner's schemas: rejected; it would change an
  immutable scientific/control baseline and broaden a diagnostic-only change.
- Reuse its watcher/evidence/JSON primitives unchanged, add one small private
  probe/controller and a separate stdlib auditor: selected. No dependency,
  public CLI, optimizer or new scientific formula is needed.

## Decision and rationale

[Probe/controller](../../src/space_nav/_import_probe.py) records the six fixed
JSONL phases in a dedicated exclusive file. Each marker is at most512bytes,
trace at most4KiB; writes are flushed/fsynced before the next operation.
Injected mode requires all three artificial hooks; native mode forbids them.
Parent and child check the actual probe source SHA256 against input. Loaded
kernel identity comes only from `sys.modules['tudatpy.kernel'].__file__` and a
file hash; there is no second explicit native import or native-context access.
The native prefix uses the same fixture Budget/source audit hook and exactly
one `from tudatpy.interface import spice`, then the existing SPICE guard.
No native branch was exercised in this qualification.

The controller uses the unchanged owner process-group watcher and fixed inherited
45/10/5 phases. Probe stdout must be empty; raw stderr is separate from markers.
It requires successful child exit, retains/fsyncs the bounded trace, saves child
facts, then runs the auditor in its own process. It accounts partial failed
traces too; oversized artificial trace output retains only its4KiB prefix and
fails. First failure is preserved, no retry or evidence namespace reuse occurs.
Returned post-fsync status is distinct from the durable pending receipt.

[Auditor](../../src/space_nav/_import_probe_audit.py) imports only stdlib and
rejects producer/owner/scientific imports in its CLI. It checks exact keys/types,
sequence, newline/size caps, finite monotonic elapsed times, childexit0, durable
child observation and profile/trace/kernel digest parity. Its result explicitly
requires outer finalization. It compares pinned saved records; it does not prove
runtime provenance or rehash every imported module, resource or original binary.
Those remain the separate F18.6 preflight's responsibility.

Caps remain64KiB input,64KiB combined logs,2MiB aggregate structured evidence,
with4KiB trace and64KiB audit/observation/receipt partitions. Native entry/cold
parent flags, environment and read-only resources remain a future fixed profile;
the producer command uses `-m` without adding `-I` or `-B`. Parent inherited-group
logs reserve2048B for the outer supervisor as before. No thread/temp setting or
physical tolerance changes. Existing external same-clock controls must supervise
cold parent imports, descendants and opaque I/O through final fsync; this module
adds no standalone authority or replacement supervisor.

## Consequences and revisit conditions

A saved last marker may precede a failed or stalled fsync. Even a visible
`complete` is insufficient without childexit0, valid independent audit, bounded
cleanup and successful finalization. A missing return brackets the import and
adjacent observer I/O, not a native instruction, a cause, or the old stall.
F18.5 qualifies artificial diagnostic plumbing only. F18.6 is not run or admitted;
F18.3 stays consumed/unqualified and historical native counts stay unknown.
Owner/carry/concurrency/ABI-FP/prior arithmetic, physical F0/M3/command-feasibility,
99-percent and safety obligations remain open. Automation remains PAUSED.
After separately admitted evidence, choose the next bounded observation from
what it actually establishes; do not automatically repeat the owner packet.

## Evidence and verification

[Qualification](experiments/0271-qualification.json) and
[immutable raw evidence](experiments/0271-validation-evidence.zip) retain source
pins, independent connected-code review, focused/full logs and JUnit, the frozen
checkout manifests, unchanged Conda environment metadata and invocation profile.
The regression archive is separate from the2MiB per-diagnostic packet cap.

Archive:21members,207551compressed/3973653expanded bytes; SHA256 `84a0f6a832d43def20befd1e40863431ffaa975cf5996a26ad2b7c5688039a63`.

- Focused:124artificial cases pass in2.11s and are included in the full portable
  lane, not counted twice. Tests cover phase/import/guard order, exact keys,
  identity and malformed records, full input/marker/log capacity, partial trace
  accounting, truncated/oversized output, inherited clocks, unsuccessful child,
  and a visible complete marker with observer fsync stalled under the reused
  external group watcher. Kernel files/hooks/processes are artificial.
- Required `make test`:7848portable passed,42unchanged opt-in historical skips;
  413live passed. Combined8261passes,0failures. Portable/live IDs are disjoint;
  all prior test identities and skip reasons match0268, plus the124new cases.
  Existing live tests retain their old SPICE/native scope.
- All1540tracked/untracked files and Git status match
  before/after both lanes. Source/test pins match the reviewed profile. Docs and
  evidence were written only after both lanes exited; runtime tests were not
  repeated for later documentation-only edits. Regression elapsed
  814.908220s<1800s qualification ceiling.
- Full Ruff and strict OpenSpec pass; original logs/JUnit and environment pins
  are retained. Independent connected-code review passes. Its original wording
  correction is preserved: pure controls import eagerly, native/scientific
  imports stay lazy. No code or scientific gate changed for that correction.

[Final documentary verification](experiments/0271-doc-verification.json) records
protected historical bytes, current qualified source hashes, working local links
and anchors, artifact hashes/syntax, final diff/strict OpenSpec checks and separate
independent documentary review. Only F18.5 is completed; no native/physical gate
is inferred and the scheduler remains PAUSED before separately authorized F18.6.
