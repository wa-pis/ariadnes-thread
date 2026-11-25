# 0272 — Record the once-only cold import diagnostic

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted for retaining the authorized import-only result
Implementation / verification: F18.6 import-only observation complete; independent trace/control audits pass
Scope / milestone: M3 diagnostic preparation; no owner or physical qualification
Base revision: `2566fb4c72a3c316f8f5ac11a2a18cdd88196027`, clean dev at launch
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f186-cold-import-only-result-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves all earlier evidence and gates

## Context and constraints

After [ADR0271](0271-qualify-artificial-import-probe.md)'s artificial qualification,
the user explicitly permitted exactly one real F18.6 diagnostic import with the
previous limits and independent audit, without SPICE queries or trajectory work.
This consumes only that permission, not a retry of [ADR0269](0269-record-owner-producer-timeout.md)'s
failed owner packet. [ADR0270](0270-design-import-only-timeout-observation.md)'s
question is whether the same cold SPICE-wrapper/kernel import completes on this
attempt, before any explicit produce/context/factory/integration/owner/helper call.

## Options considered

- Repeat the owner packet or change TMP, thread settings, permissions or deadline:
  outside the selected observation; not executed.
- Retain one separately authorized fixed import-only observation with complete
  admission, durable markers, independent audit and outer supervision: selected.
- Infer the previous failure's cause from a warning or a new successful import:
  rejected; neither observation identifies the old stalled operation.

## Decision and rationale

The single cold import succeeds. Six ordered markers reach `complete`, the child
exits zero, the separate stdlib saved-trace auditor passes, and observed parent,
supervisor, launcher and caller returns all pass cleanup/finalization. The caller
observes its final receipt after fsync at **0.847950292 seconds**, below the
unchanged 60-second inclusive 45/10/5 phases. `native-import-enter` is at
0.393123500 seconds, `native-import-return` at 0.764731250 and `complete` at
0.780139625. These marker times include observer boundaries; their differences
are not a measurement of native CPU time.

The trace is 1009 bytes; its six markers each satisfy 512 bytes. Fixed probe input
is 355 bytes. Independently summed execution/caller episode records are 10270
structured bytes and 64 log bytes, below 2 MiB and 64 KiB. The parent records its
successful probe observation at 0.795184792 seconds. Its internal auditor takes
0.033978792 seconds and exits zero. Durable parent/supervisor receipts describe
pending finalization by design; their successful post-fsync observations are
retained separately in the enclosing returned records. Do not rewrite receipts
or infer successful fsync merely from a visible marker.

Root launch admission is at 394.802256 seconds; the exclusive caller episode
starts at preflight 413.894826 seconds and its native-consumed marker is
413.944815 seconds, all below the same original 600-second clock. Independent
file and final-profile reviews complete at 226.503 and 362.658 seconds. All45
project-source pins, 10 retained native pins, five exact resource files and old
episode records are checked. The exact0269 environment, role-specific flags,
read-only image and sandbox restrictions are preserved. Prefix/source pinning
and local resource identity are not whole linked-library or upstream-payload
authentication.

The existing caller is reused byte-for-byte. The launcher adds only the new
adapter hash check and the sandbox changes only the fresh output namespace.
A private external adapter copies the qualified old `run_isolated` controls;
only fixed input validation, report schemas and explicit cold-parent dispatch
change. Independent AST/source review verifies these differences without changing
old runners or monkeypatching their globals. Artificial pass, unfinalized-report
rejection and cold-stall rejection qualify this wiring. The stalled fake correctly
fails at inherited 60.026 seconds, rather than claiming a timely success. These
checks concern orchestration, not native or scientific correctness; ADR0271's
124 cases remain the probe/auditor qualification.

Three preflight setup issues are preserved: duplicate same-hash kernel/artifact
selection, a sandbox-denied artificial PID postcheck, and an overly narrow root
assertion about the static review's pending status. Corrections affect temporary
profile/harness/admission preparation only, before the one native consumption;
no clock reset, production-control change, retry or relaxed criterion follows.

The identical 64-byte OpenMP warning occurs here and in0269's failure. Thus it is
not sufficient evidence of import failure. This successful new attempt does not
establish that0269 passed its import, identify its later phase or prove a cause.
There is exactly one explicit import attempt and zero explicit SPICE queries,
produce/context/factory/integration/owner/helper calls in this probe. Native
internal initialization actions are not instrumented;0269's actual native
operation counts remain unknown.

## Consequences and revisit conditions

F18.6 alone is complete. F18.3 remains consumed and unqualified; F17/F17.1,
actual-owner readback, carry/concurrency/ABI-FP/prior arithmetic and physical
F0/M3/command-feasibility/99-percent/safety gates remain open. A next owner-stage
observation needs its own bounded design and explicit execution decision;
this success supplies no retry authority. Automation remains PAUSED after the
authorized observation; its prompt is updated through the official action.

No Ariadna runtime/test source, dependency, kernel, resource, scientific baseline
or `moon_to_mars.py` changes. No new acquisition, SPICE query, integration,
trajectory search or physical experiment occurs. Both recorded native process
groups are absent; all71459 operational-prefix paths and1646916124 regular-file
bytes match the protected baseline. Native/source/resource/old-ledger hashes are
unchanged after execution, and the read-only image is detached.

## Evidence and verification

[Result](experiments/0272-cold-import-result.json) and
[immutable raw evidence](experiments/0272-cold-import-evidence.zip) retain fixed
inputs, source/resource admission, artificial wiring and its preserved setup
failure, launch controls, raw trace/logs, nested prefinal/post-fsync receipts,
independent saved-only audit, preservation and detach/scheduler observations.
The postpacket independent review is separate from the auditor already included
in the 60-second episode; it performs only stdlib reads of saved records.

Archive: 105 members, 88264 compressed / 192245 expanded bytes; SHA256 `921986d43c79fd919ffe80292dfef80a8a21ad40656c25e6d5b69d12fea2dcde`.

No runtime source changes, so successful ADR0271 focused/frozen `make test`/Ruff
checks are not repeated. Temporary wiring checks pass; documentary facts, local
links/anchors, artifact syntax/hashes, protected prior blobs, diff and strict
OpenSpec are checked. [Final verification](experiments/0272-doc-verification.json)
retains those checks and independent documentary review. This record qualifies
the import observation only, not mission accuracy or owner behavior.
