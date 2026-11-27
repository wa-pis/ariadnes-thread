# 0292 — Qualify the corrected artificial owner slice

Date: 2026-11-27 (Europe/Samara)
Decision status: accepted (software correction and artificial evidence only)
Implementation / verification: F18.22 complete; corrected artificial slice qualified
Scope / milestone: M3, temporary artificial controls only
Base revision: 86c9c68039a3d7b19eb6b5d7942f8d774b96b514
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture)
Supersedes / Superseded by: none; preserves [0291](0291-qualify-artificial-owner-slice.md) and [0290](0290-map-full-owner-controls.md)

## Context and constraints

ADR0291's original invocation failed during setup: three helper methods passed,
nine methods errored before entry dispatch. Its consumed namespace and evidence
remain unchanged. The accepted correction was limited to hashing the known
6829984-byte interpreter under the adapter's existing 16 MiB identity-input bound.
This did not enlarge the generic 2 MiB artifact reader or any scientific gate.

## Options considered

- Increase the generic reader or rerun the consumed namespace: rejected; unnecessary
  scope changes would obscure the recorded failure.
- Repeat all previously successful helpers or the original 194-case campaign:
  rejected; they do not test the changed reader or newly connected slice.
- Stream only the fixed interpreter in a fresh reviewed version and run the nine
  blocked methods plus focused pin refusals: selected and completed.

## Decision and rationale

The dedicated reader streams at most 1 MiB per chunk, checks the fixed resolved
path, exact size and retained SHA256 under the existing 16 MiB bound, and rejects
short reads, extra bytes or identity drift. It retains metadata, not executable
payload. The two control files and external budget wrapper differ from 0291 only
by their fixed namespace. Independent static review passed; the three candidate
sources and command recipes were frozen before execution. Dynamic packet/clock/
argv witnesses were written and read back before dispatch inside the invocation.

Exactly one new artificial invocation passed ten methods: the nine previously
blocked methods and one focused wrong-hash/over-bound refusal method. Failures and
errors were zero. Actual observation after external-receipt file and directory
fsync was 0.6748446668498218 s, below 120 s. The observed pre-final root inventory
was 360843 structured bytes and 1586 log bytes, below 2 MiB / 64 KiB; later review
and publication are recorded separately, not inserted into that success clock.

The positive case reached the unchanged real guarded audit child: eight ordered
injected outcomes, two analytic arcs, 3 factory attempts / 2 integration attempts /
8 visitor calls. The wrong-count case reached that auditor and was refused;
wrong schema stopped before work, and first-failure partials survived without an
audit. Wrong mode/source/interpreter/group, reset/future/expired clock, descriptor
overrun and duplicate entry were also checked. Original 60 s packet partitions,
65 s failure-only cleanup, source/oracle/counter and byte gates were unchanged.
Known owned-group cleanup reported no errors. Independent saved-only review passed.

This qualifies the corrected **artificial** adapter/entry slice. The three helper
passes are retained from 0291, not repeated here: these records are not one
original all-green twelve-method run. ADR0291 remains a failed historical run.
The repository fixture, runner, auditor, runtime, tests, CI and dependencies did
not change. No native owner, SPICE, scientific integration, mount or build ran.

### Next bounded preparation — F18.23

Use ADR0290's existing map and the corrected slice to specify the smallest remaining
native control/profile/admission binding and its focused artificial qualification.
Produce one concrete change list with exact reuse versus changed bytes, original
clock/cleanup/preservation/resource gates, refusal checks, measurable completion
criteria and bounded implementation/test budgets. Limit this design to 600 s and
2 MiB of new evidence, including independent review; no repeated source campaign,
new controller or generic framework. Do not execute tests or scientific work in
this design unit. Ordinary reversible preparation is already authorized.

Do not adopt a native profile or execute an actual native episode under this
record. Such an episode still requires a distinct explicit user choice and fresh
independent actual admission. Existing 0285 authority is consumed and the image
remains detached.

## Consequences and revisit conditions

Artificial seam success is a software result, not full 0267 native lifecycle,
carry/concurrency, physical clock/force/endpoint bounds, physical F0, M3 completion,
an admissible command pair, a 99-percent probability or mission safety. Those
obligations remain open. No later milestone, new optimizer or scientific retry is
authorized. Revisit only the named remaining bindings, without reopening passed
unchanged campaigns or changing scientific inputs and tolerances.

## Evidence and verification

[Result](experiments/0292-correct-artificial-interpreter-pin.json) and
[immutable evidence](experiments/0292-correct-artificial-interpreter-pin-evidence.zip)
retain the exact sources, namespace proof, independent reviews, one actual tool
return, logs, per-case clocks/dispatch/audit/partial/cleanup records and byte counts.
[Documentary verification](experiments/0292-doc-verification.json) checks archive
members/pins, protected prior Git blobs, links, CURRENT length, diff and strict
OpenSpec. The unchanged full suite and Ruff were not rerun.
