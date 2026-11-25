# 0270 — Design an import-only observation after the owner timeout

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted for saved/source diagnosis and design only
Implementation / verification: F18.4 source/design complete; F18.5 preparation and F18.6 native probe not started
Scope / milestone: M3 preparation; no native retry or physical experiment
Base revision: `203a4f90726d139d970d85cca7be3bdc41770173`, clean dev at source review
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f184-savedsource-timeout-diagnosis-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves all prior choices, failures and evidence

## Context and constraints

The user's continuation follows [ADR0269](0269-record-owner-producer-timeout.md)'s
consumed 45-second producer timeout. It permits this bounded diagnosis and next
plan; it does not establish authority to repeat F18.3. Review saved facts and named
sources on the retained read-only image within 600 seconds, including independent
review. No native/scientific imports, tests, probes, SPICE, integration, builds,
new data or changed limits/physics. Keep automation paused.

## Options considered

- Increase the deadline or make temp/image paths writable and rerun: rejected;
  these are unmeasured hypotheses and would change the failed profile.
- Add broad markers and repeat the whole owner packet: deferred; no existing
  evidence even establishes that its initial import returned.
- First design one cold import-only observation under the unchanged environment:
  selected. It asks a smaller question and excludes owner/trajectory work.

## Decision and rationale

The saved failure's entire 64-byte OpenMP warning exactly matches the prefix of
0266's successful 222-byte log. It does not identify a causal mechanism.
The producer imports the SPICE wrapper, which imports the native kernel, before
calling `produce()`. Its scientific JSON is written only at the end; an empty
file cannot identify the last completed operation.

The never-run native constructor still sets up the environment, derivative and
results objects; `False` skips only integration. If that constructor returns,
the first visitor should reject unperformed results before map access. The
forward constructor combines setup, integration and postprocessing. Named source
review finds no deterministic hang cause; no local locking mechanism is proof
of deadlock or proof that one is impossible.

There are concrete environment differences: 0266 allowed writes to its mounted
volume, while 0269 used a read-only image and allowed writes only to the fresh
execution directory. HOME/temp/cache still point into that image. Python flags,
bootstrap and import entry paths also differ. These are candidates for later
controlled diagnosis, not explanations established by the two observations.

F18.5 will prepare the smallest private import-only probe and separate stdlib
trace auditor using existing qualified controls. No new public API, dependency,
optimizer, scientific formula or modifications to old pinned runners are needed.
Artificial checks must cover fixed sequence, injected imports/guards, missing or
duplicate/truncated markers, identity mismatch, failed or stalled observer I/O,
limits and cleanup. Require focused tests, frozen portable/live `make test`, Ruff,
independent review and strict OpenSpec before completing that implementation.
Existing required live tests retain their old scope; they do not execute the probe.

Only a later separately explicit F18.6 instruction may consume one import attempt.
Preserve 0269's exact role-specific interpreter flags, environment, source/kernel/
resource pins, read-only image and sandbox. Native entry/cold parent use `-B`;
the producer worker uses `-m` without `-I` or `-B` and inherits the fixed bytecode
and source-bootstrap environment. Do not redirect TMP or change thread settings.
Use the same project fixture/guard imports and audit-hook prefix, then exactly
`from tudatpy.interface import spice`, install the SPICE guard, record the loaded
kernel identity through `sys.modules`, and stop. Never call `produce()`,
`_native_context()`, factories, integrators or owner/helper visitors.

At most six JSONL markers identify `bootstrap-ready`, `guards-ready`,
`native-import-enter`, `native-import-return`, `spice-guard-ready` and `complete`.
Each is at most 512 bytes, the dedicated trace at most 4 KiB, inside the existing
2 MiB aggregate. Flush/fsync markers within the inherited clock before moving
on; preserve raw stderr separately and do not mix markers into scientific JSON.
A visible final line alone does not prove its writer's fsync returned: require
successful child exit and finalization as well as the validated complete trace.
A missing return only brackets import and adjacent marker I/O. It proves neither
a native instruction, cause, nor where the consumed 0269 packet stalled.

Keep the existing at-most-600-second comparable-clock preflight and independent
admission, 60-second inclusive 45/10/5 phases, 64 KiB input/combined logs and
2 MiB aggregate evidence including outer records. At most one explicit import;
zero explicit factories, integrations or owner/helper visitor calls. Preserve
first failure/partial trace, process cleanup, old clocks and ledgers. No retries,
acquisition, build, dependency changes or relaxed gates.

## Consequences and revisit conditions

A complete probe would establish only that the selected import profile completed
on that attempt. Failed or incomplete traces remain diagnostic unavailability;
saved failure accounting is separate from import completion. Neither outcome
qualifies native endpoints or retroactively resolves 0269's unknown counters.
Choose a further observation from new evidence only after its own bounded plan.
F18.3, F17/F17.1, native owner/carry/prior arithmetic/concurrency/ABI-FP and all
physical F0/M3/command-feasibility/99-percent/mission-safety gates remain open.
No native execution authority follows from this design. Automation stays PAUSED.

## Evidence and verification

[Diagnosis record](experiments/0270-timeout-diagnosis.json) and
[immutable source/design evidence](experiments/0270-timeout-diagnosis-evidence.zip)
retain both independent source analyses, exact hashes/excerpts, the selected
contract, two independent design reviews and source/clock/detach receipts.
Archive: 10 members, 104862 expanded bytes, 38351 compressed bytes; SHA256 `b07e2fa66c046694f40ba6883e73e104593e3e1f6eed9e22f9bbb1adfeccffc8`.
The root checked 38 named source/evidence files and their retained line excerpts,
10 old native pins, five resources and 10 old clocks/ledgers. Source/design and
independent reviews took 379.127174 seconds; including read-only detach,
396.203576 seconds, below 600. No cause is proved and no probe was executed.
Runtime/tests are unchanged; pytest, Ruff and CI were not repeated for this
source/design stage. No full operational-prefix rescan is claimed here.
[Final documentary verification](experiments/0270-doc-verification.json) records
protected prior bytes, links/anchors, artifact hashes/syntax, diff and strict
OpenSpec validation plus final independent documentary review.
