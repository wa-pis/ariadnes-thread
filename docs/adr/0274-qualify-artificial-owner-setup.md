# 0274 — Qualify the artificial never-run setup diagnostic

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted for artificial F18.8 preparation only
Implementation / verification: F18.8 artificial implementation qualified; focused/full required regressions, Ruff, independent review and strict validation pass
Scope / milestone: M3 private diagnostic preparation; F18.9 not executed
Base revision: `a1963db7bf7cbf8195d0dd94dababcbba17c6ca1`, dev
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f188-artificial-never-run-setup-qualification-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; retains earlier design and consumed episodes

## Context and constraints

The resumed automation permits [ADR0273](0273-design-never-run-owner-observation.md)'s
F18.8 implementation and artificial checks. It excludes the new F18.9 native setup,
old packet replay, new data/build/dependencies and scientific trajectory work.
Existing required live regressions retain their former scope. Complete the new
private probe/controller and independent auditor using existing helpers, then
focused checks, frozen required `make test`, Ruff, independent review and strict
OpenSpec. No public API or scientific formula changes.

## Options considered

- Repeat the entire owner packet or add generic instrumentation: exceeds the
  diagnosed need; not implemented.
- Modify old pinned runners to share new schemas: unnecessary provenance changes;
  rejected.
- Add a fixed never-run-only branch reusing qualified controls: selected. It can
  observe setup and the first expected refusal without requesting integration.

## Decision and rationale

New private `_owner_setup_probe.py` validates exact profile/source identities,
uses existing guard/import helpers and invokes only context, never-run factory
withFalse and one original-endpoint visitor withTrue and the original schema.
It stops after the exact RuntimeError/message. Native mode forbids injected hooks
and preloaded TudatPy; artificial mode requires all six replacements and remains
explicitly labelled. Source/kernel claims remain conditional on complete future
external runtime admission; matching report hashes alone are insufficient.

The smaller1factory/0integration/1visitor limits are checked before precharge and
entry and after each return/refusal, beyond old Budget maxima3/2/8. Complete
records require those exact counts and one context check. The original100000
uniform-acceleration callback ceiling is retained; actual callback counts need
not be zero and are not total native RHS counts. The underlying context tuple
and helper list are kept distinct. An attempted call is not proof of completion.

Eight durable markers use the fixed4KiB trace/512B line caps. The report records
only primitive scope/identity/arguments/context/refusal/counts. Its raw SHA binds
the complete marker and parent observation. The new stdlib auditor reuses pure
validation helpers, rejects producer/scientific imports in its actual CLI, and
checks exact keys/types/pins/refusal/counts/order, successful child exit and
within-phase post-fsync observations. New parent/supervisor wrappers reuse old
watcher/evidence mechanics with fixed schema/dispatch changes; old files and
globals remain unchanged. Cold outer wiring, descendants and opaque I/O/final
fsync remain externally supervised. Actual role-specific runtime/resource/
bootstrap/PGID-before-import admission still belongs to any future F18.9.

Independent review found a new-report durability gap: the first implementation
fsynced the trace but deferred producer.json fsync until after audit, while the
observation already claimed checked-after-fsync. The outer final fsync prevented
a final false pass, but that intermediate claim was premature. The report is now
fsynced before the45s phase check, observation and audit. Three regressions
verify failed, late and stalled report fsync cannot create a success observation
or launch audit, even with a visible complete trace. The initial finding and
reviewed correction are preserved. A test-only descendant cleanup assertion was
also made portable using an absent/stopped heartbeat rather than immediate PID
reaping; the original successful focused runs are retained.

- Focused: 215 artificial cases pass (74 producer/controller, 141 independent auditor); they are included in the portable lane and not counted twice.
- Required frozen `make test`: 8063 portable and 413 live passes, 42 unchanged opt-in historical skips, zero failures. All old case IDs/skip reasons match0271, with only the new setup cases added; the lanes are disjoint.
- All1555 checkout files and Git status match before/after both lanes. Source/test pins match independent review. Regression 805.672314s<1800s; final focused producer/auditor invocations each<300s.
- Ruff, independent connected-code review and strict OpenSpec pass. Existing live regressions keep their old scope; the new branch uses only fake kernel files, owners, hooks and processes plus a real independent stdlib saved-record audit.
- Archive: 35 members, 215247 compressed / 4563917 expanded bytes; SHA256 `b9eca79bb3b8fc916fe7f2e2c2d137973a3f591f080101880e78ae56479f7be9`.

## Consequences and revisit conditions

F18.8 alone is qualified on artificial inputs. Its new artificial tests do not
execute a native owner, SPICE query, setup packet, integration or physical experiment
and do not mount the private image. Existing required live regressions retain
their previous native/SPICE authority and scope.
The new branch's native factory/default path has not been executed.

Automation pauses now for the distinct F18.9 decision. Its reviewable proposal
is one cold fixed setup observation:1context check,1factory(False),0integration,
1visitor requiring exact unavailable refusal; unchanged600s independent admission,
60s45/10/5,64KiB input/combined logs,2MiB aggregate,4KiB trace, source/kernel/five
resources and exact0269role flags/env/read-only image. No resource supplementation,
retuning or repeat after failure. No old F18.3/F18.6/0266 replay is authorized.
A marker still brackets whole setup plus observer I/O, not a native instruction.
Even native success would qualify only this never-run rejection seam; completed-
owner readback, F17/F17.1/F18.3, carry/concurrency/ABI-FP/prior arithmetic and
physical F0/M3/99-percent/safety gates remain open. Historical0269cause/counts
remain unknown, and `moon_to_mars.py` remains unchanged.

## Evidence and verification

[Qualification](experiments/0274-owner-setup-qualification.json) and
[immutable evidence](experiments/0274-owner-setup-evidence.zip) retain profile and
source pins, all focused attempts, raw required-lane JUnit/logs, frozen checkout
checks, original/final independent review, corrected durability regressions and
Ruff/strict observations. Full validation artifacts are separate from per-packet
native evidence caps. [Final documentary verification](experiments/0274-doc-verification.json)
records artifact/source/protected-history/link/anchor/diff/strict checks and the
scheduler readback. Runtime tests are not repeated for later evidence-only edits.
