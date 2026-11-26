# 0279 — Qualify the once-only supplemented execution gate

Date: 2026-11-27 (Europe/Samara)
Decision status: accepted for artificial preparation and one conditional future F18.13
Implementation / verification: F18.12a outer gate qualified artificially,30/30 and independent review PASS; actual F18.13 not admitted or executed
Scope / milestone: M3 private setup diagnostic; no mission calculation
Base revision: `1dcdb85d3654608f65b31247aa93beed9be10091`, clean dev before preparation
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f1812a-once-only-execution-gate-2026-11-27), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture)
Supersedes / Superseded by: none; preserves0275consumed failure and0277/0278contracts

## Context and constraints

The user enabled recurring progress and continued tests. [ADR0278](0278-qualify-artificial-provision-admission.md)
qualifies the fixed-six transaction/admission on fabricated data, not native setup.
The legacy collector checks only a permit's status; a saved pending candidate or
leftover PASS cannot establish observed finalization. The missing piece is a small
outer gate that owns admission, durable sealing and immediate once-only dispatch.

## Options considered

- Dispatch manually from a saved permit: cannot bind it to the current observed
  admission continuation or reliably reject leftovers; rejected.
- Change/regenerate the qualified collector and four runtime controls: unnecessary
  for this fixed path and breaks the agreed reuse boundary; not selected.
- Directly call the qualified admission, seal/recheck and replace the gate process
  with the unchanged collector: selected, with artificial qualification first.

## Decision and rationale

The [concrete conditional contract](experiments/0279-supplemented-execution-gate-contract.json)
records one future F18.13 under the user's standing continued-tests instruction.
This is the separate execution choice required by0277, conditional on completed
gate qualification and fresh independent actual admission. No further question is
needed merely to repeat authorization for this reversible isolated diagnostic.
It is not a live ADMITTED_ONCE proof, successful setup or scientific result.

A new temporary dispatch-once.py calls the exact byte-pinned0278admit() once in
its own process. It never accepts a serialized returned result as authorization.
An exclusive gate-start marker is durable before admission; existing start,
candidate, permit, episode or work paths, including dangling symlinks, refuse entry.
Errors after charging keep partial evidence and cannot resume from a leftover file.
The actual admission's pending disk candidate is checked against its observed
post-fsync return, exact fields/types/profile/contract/proof hashes and inherited
clock. Gate/outer-interpreter identities are pinned separately in profile and
execution decision, preserving the exact nine-control and ten-native-pin groups.

The final permit is written exclusively and fsynced with its directory. Afterward
the gate rechecks unchanged profile/contract/candidate/start/decision, its own and
outer-interpreter/collector/admission identities, namespace and original600s clock.
Only the successful in-memory continuation may dispatch. A native permit contains
legacy-compatible PASS, but remains pending outer dispatch on disk; it is not
self-proving or resumable. This is a controlled workflow, not a tamperproof barrier
against someone manually bypassing it to run a legacy script.

Native mode forbids injected clock/observer/dispatcher, fixes all paths, and uses
os.execv of the pinned outer Python with -I -B and the unchanged collector. It
never prints or returns a native PASS before replacement. The collector is never
imported: its module top level executes. Process replacement adds no parent phase
after the original cold-import60s start. The original600s preflight ends at
consumption; subsequent success/finalization is measured on the original60s
45producer/10audit/5finalization episode, not an erroneously extended600s gate.

Artificial mode calls actual provision/admission on fabricated files, returns only
ARTIFICIAL_READY with native authorization false and invokes an explicit harmless
callback. It cannot execute the collector. Its returned elapsed_s is the dispatch-
entry clock; the external qualification measures callback/asserts/receipt completion.

## Evidence and verification

[Result/member manifest](experiments/0279-once-only-execution-gate-result.json) and
[23-member archive](experiments/0279-once-only-execution-gate-evidence.zip) preserve
sources/helpers, initial harness and findings, corrected source review, raw logs,
prefinal receipts, normalized actual return and independent completion review.
Archive54090B, SHA256 `3f73a181eebd3b98743d1c0011e44e2d3a4db8932777edf1399e3388b5b77f43`;
expanded171540B, result6791B, all retained structured evidence below2MiB.

One invocation passed30/30 cases,0failures/errors/skips, observed after external
file/directory receipt fsync0.9259437923319638s<120s. Saved invocation records10190B.
Timing starts before qualification-child startup and includes assertions/final
receipt; later observation-copy/review/packaging/doc checks are separate. Initial
harness issues were corrected before this first invocation: the mutation wrapper
hid required helper methods, and record pin values included an extra path field.
Exact initial source and review remain saved. Semantic failures now assert that
actual admission and the intended mutation were each reached exactly once.

Connected full3578887B fake provision/11file readback/admission dispatches once;
occupied/dangling/second-entry cases dispatch zero times. Tests cover rejected
pending/unfinalized/wrong/bool/nonfinite/rehash-bound proof values, native replacement
callables before live reads, file and parent-directory fsync failures, post-seal
profile/collector drift and late clocks. A failing fake dispatch stays consumed
without retry. Independent source and saved-result review PASS, no remaining finding.
Native positive, actual mount identity and native exec were explicitly unexercised.

No repository package/test/dependency change. Qualified0278helpers are reused,
its94case campaign and0274's8476passes/42archive skips/Ruff were not repeated.
[Document verification](experiments/0279-doc-verification.json) separately checks
protected history, links/anchors, JSON/AST/member pins, shortCURRENT, diff and strict.

## Consequences and revisit conditions

F18.12a preparation is complete. Next is one actual F18.13, only after a fresh
complete600s preflight beginning before RWmount/first write on clean committed dev.
It includes protected pins, exact six local byte-pinned resources, immutable
carried precharge, no-replace publication, all11resource readbacks, detach/ROremount
and independent admission. Generate its separate concrete native execution proof
there; do not reuse this artificial result or old clocks. Preserve0277's isolated
HOME/environment/kernel/settings,8GiB/2GiB and60s/64KiB/2MiB/count ceilings.

One never-run factory(False), no integration, one original visitor(True,SCHEMA)
must yield the exact original RuntimeError/refusal. Any failure is retained with
actual/unknown counts, cleanup and detach; no extra file, hidden retry, oldF18.9
replay or new full-owner packet. Operational/native/physical qualification remains
open. No real resource payload read/copy, mount/provision, Tudat/kernel import,
SPICE or integration occurred here; future episode namespace remains absent.
Automation remains ACTIVE, pausing for real missing access/data/action or a
scientific choice. Owner/carry/concurrency/ABI-FP/prior-arithmetic and physicalF0/
M3/99-percent/safety gates remain open; no admissible command pair is claimed.
