# 0273 — Observe only the never-run owner setup

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted for source/design and artificial preparation only
Implementation / verification: F18.7 design complete; F18.8 not implemented, F18.9 not authorized or run
Scope / milestone: M3 private owner diagnosis; no physical trajectory
Base revision: `7aaf0b2b07e1b9c746febd0448b01cf7a7c48986`, clean dev at source review
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f187-minimal-never-run-owner-observation-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves the consumed0269/0272 episodes

## Context and constraints

The user resumed automation and ordinary project progress after
[ADR0272](0272-record-cold-import-diagnostic.md)'s successful import-only result.
This permits the next bounded design and artificial preparation. It does not
repeat the exhausted import-only or full-owner permission. Source/saved-only
reasoning and independent design review are limited to600s; no native import,
SPICE, integration, test run, image mount, build, acquisition or data change.

[ADR0269](0269-record-owner-producer-timeout.md)'s owner timeout has unknown
native counts and no phase trace. A different import succeeding in0272 does not
locate that old failure. The smallest useful next question is whether the fixed
never-run owner can be created and reject its first read, before any forward or
reverse integration is requested.

## Options considered

- Repeat the complete3factory/2integration/8visitor packet with more markers:
  unnecessary work before identifying the first missing lifecycle fact; deferred.
- Change temp/thread settings, deadline or dependencies: unsupported causal
  hypotheses; not selected.
- A fixed prefix ending immediately after the never-run refusal: selected.
  It reuses existing code and separates setup from later integration/readback.

## Decision and rationale

### Source-backed boundary

The existing producer worker imports fixture guards and SPICE before `produce()`
(`_owner_endpoint_run.py`338–351). `produce()` checks provenance and native context
before `make('never-run', False)`, then requires its exact unavailable-results
refusal before creating the forward integrating owner (`_owner_endpoint_fixture.py`
310–318). Calling `produce()` would automatically continue into the rest of the
packet, so the new diagnostic must not call or monkeypatch it.

Reuse `_provenance()`, `_native_context()`, the unchanged `_native_factory()` and
its `Budget`, plus the existing import/guard helpers and process/evidence controls.
Invoke exactly one `_native_factory('never-run', False, budget)`, validate its
bound method is callable, and invoke `_ariadna_original_endpoint(True, SCHEMA)`
exactly once. Require **type(exc) is RuntimeError** and message exactly
`completed original results unavailable`. Any returned endpoint, wrong exception,
changed identity or other unexpected outcome stops the diagnostic as failed.
Then stop: no metadata/history access, forward/reverse owner, GC/clear/lifetime
sequence or numerical endpoint audit.

The native factory123–173 imports NumPy/dynamics/trajectory, validates versions,
builds the same empty Spacecraft/body/force/translation+mass settings and only
then calls `create_dynamics_simulator(..., simulate_dynamics_on_creation=False)`.
A marker around that function brackets **all this setup**, not just the C++
constructor. The flag suppresses requested integration; source review alone does
not claim absence of internal constructor work or native callbacks.

### Fixed data and finite native proposal

| Item | Fixed rule |
| --- | --- |
| Carrier / domain | Same synthetic native SSB/J2000 settings, labelled SYNTHETIC_INERTIAL / elapsed seconds; not a physical TDB mission |
| Initial row | Original `_INITIAL`: position `(10000000,0,0)` m, velocity `(0,1000,0)` m/s, mass2000kg, literal binary64 words unchanged |
| Settings | Original never-run0→1000s settings, uniform acceleration `(0,float(0.1),0)` m/s², existing tighter coast profile and result-retention flags; no integration requested |
| Native identity | Same private kernel hash; underlying native context tuple `(53,53,8)` is checked, `_native_context()` returns list `[53,53,8]`; source/provenance pins and exact five local resources |
| Calls | At most1context check,1factory attempt withFalse,0integration attempts,1visitor attempt; stop on first unexpected outcome |
| Callbacks | Preserve the100000 precharged uniform-acceleration callback ceiling and record actual count; do not assume zero callbacks or call it a bound on all native RHS |
| Exclusions | Zero explicit SPICE queries, SPICE kernel/data loading, real-archive reads, optimizer or trajectory calls; eager fixed import-resource reads remain permitted |

Precharge factory/visitor attempts through the existing budget before their calls.
The new probe must independently enforce its stricter1/0/1 call-site ceiling
before work and require exactly1/0/1 in a complete transcript: reused Budget
maxima3/2/8 are not sufficient admission for this smaller scope.
A saved precharge is evidence of attempted work, not completed native operations.
Only the final successful return/refusal and independent records establish their
outcomes. Preserve partial/unknown actual native counts after abort or timeout.
No relaxed physical tolerance is needed: this stage has exact context, argument,
flag, exception-class/message and counter gates, not a numerical trajectory gate.
The original endpoint tolerances and all F0 boundaries remain unchanged.

### Eight durable markers and independent admission

One fixed sequence: `bootstrap-ready`, `import-ready`, `context-ready`,
`factory-enter`, `factory-return`, `visitor-enter`, `visitor-refused`, `complete`.
Use one dedicated JSONL trace: each newline-terminated marker<=512bytes and
all8<=4096bytes. Flush and fsync before the next operation; preserve the bounded
partial trace on failure. `import-ready` follows the same fixture guard/import/
SPICE-guard prefix, `context-ready` follows the original provenance/kernel/context
checks, and visitor-refused follows exact exception validation. Complete is not
emitted on any unexpected outcome. Keep stdout for a bounded primitive report,
with trace/stderr separate; never serialize an owner or a Python state history.

Use a new fixed private setup scope/schema and stdlib saved-record auditor. Reuse
qualified `_import_probe` prefix helpers and unchanged `_owner_endpoint_run`
watcher/evidence/JSON primitives; add no generic phase framework or dependency.
Do not modify old pinned runners, replay their commands or translate an injected
outcome into native qualification. Native mode forbids replacement callbacks;
injected factories/imports/files are explicitly labelled artificial.

The independent auditor must not import the new producer, fixture or scientific
runtime. Check exact profile/source/kernel pins, mode, all8marker order/times,
fixed arguments/context/refusal/counters, report and trace hashes, childexit0 and
post-fsync observation. Partial data may support failure accounting only; a
visible complete line alone cannot pass. Outer supervision must cover cold
imports, opaque I/O, all descendants and final fsync on the original clock.
Durable prefinal receipts remain distinct from observed post-fsync returns.

The selected8markers deliberately do not locate a native instruction. An absent
factory-return brackets the whole factory plus adjacent observer I/O; an absent
context-ready may include provenance/hash/context work. A later successful new
packet would not prove where0269stalled or close the full owner fixture.

### Preparation and distinct future execution

F18.8 may implement only this private probe/controller and independent auditor
on artificial inputs. Check fixed dispatch/argument/count order, injected/native
separation, exact refusal versus unexpected return/subclass/message, absent,
duplicate and truncated markers, identity tampering, finite clock and byte caps,
partial traces, unsuccessful/stalled observer I/O, descendant cleanup and distinct
prefinal/post-fsync receipts. Use full8marker/capacity artificial cases.
Reuse the existing comparable interpreter and controls; qualify source/profile
pins and cold outer wiring. At implementation completion run focused tests,
required frozen portable/live `make test`, Ruff, independent review and strict
OpenSpec. Bound a focused invocation by300s and one full required invocation by
1800s; fix ordinary implementation failures within the same preparation scope,
and do not repeat successful suites on unchanged code. Existing live regressions
retain their scope and do not authorize this new native probe.

Only after F18.8 and a separate explicit decision may F18.9 execute this one
new fixed cold **setup** observation. Preserve exact0269role-specific flags,
environment/TMP/HOME/thread settings, read-only image/sandbox, source/kernel/five
resources and no-pending-work admission within600s including independent review.
Use a fresh exclusive namespace/consumption ledger and unchanged60s inclusive
45producer/10audit/5finalization,64KiBinput/combined logs and2MiB aggregate
structured evidence including all outer records and the4KiB trace. Reuse8GiB
scratch/2GiB acquisition ceiling and existing carried497045495B balance; zero
new acquisition/build/install/resource supplementation. Preserve failures without
retry or automatic escalation into the old packet. Verify operational/history
bytes and detached image afterward. These are future ceilings, not measured
performance or current native authority.

## Consequences and revisit conditions

F18.7 completes design only; F18.8 artificial preparation is the next available
work. Automation is ACTIVE every5minutes under the user's resume instruction
and must pause for any necessary user action or the distinct F18.9 decision.
No automatic F18.3/F18.6 replay or changed scientific contract follows. Even a
future passing setup probe would qualify only the never-run rejection seam.
F17/F17.1/F18.3, completed-owner readback, native carry/concurrency/ABI-FP/prior
arithmetic and physical F0/M3/99-percent/safety gates remain open.

## Evidence and verification

[Design evidence](experiments/0273-owner-setup-design.json) retains source pins,
line anchors, independent source/design reviews, the original bounded clock and
scheduler readback. No mounted image, runtime/test/source changes, calculations
or native work occurred. [Final documentary verification](experiments/0273-doc-verification.json)
checks protected historical files, local links/anchors, artifacts, diff and strict
OpenSpec. The unchanged successful ADR0271 regression/Ruff checks are not rerun
for this design-only stage.
