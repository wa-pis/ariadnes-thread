# 0275 — Record the failed never-run setup observation

Date: 2026-11-27 (Europe/Samara; raw UTC records begin on November26)
Decision status: accepted for retaining negative evidence only
Implementation / verification: F18.9 permission consumed; setup success unqualified; independent failure accounting passes
Scope / milestone: M3 private setup diagnostic; no physical qualification
Base revision: `ab72085349bfc1a660219b8ed2c0f947e1454e42`, clean dev at launch
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f189-consumed-setup-failure-2026-11-27), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; prior source, evidence and gates preserved

## Context and constraints

The user explicitly answered the concrete F18.9 proposal after [ADR0274](0274-qualify-artificial-owner-setup.md)
with an instruction to proceed. This authorizes one new cold setup observation
under [ADR0273](0273-design-never-run-owner-observation.md), with unchanged0269
role flags, environment and read-only image; no old packet retry, new resources,
build, dependency change, SPICE query or trajectory integration. Automation stays
PAUSED at this terminal result and before any new resource/native decision.

## Options considered

- Execute the one fixed qualified never-run observation after independent admission:
  selected and consumed, with partial failure preserved.
- Supplement resources or repeat after this new refusal: outside the authority;
  not executed. A new inventory/provisioning/execution decision would be needed.
- Infer successful setup or historical0269cause from import/context markers:
  rejected. Partial traces do not establish full outcomes or internal counts.

## Decision and rationale

**F18.9 fails its required setup success gate.** The child exits2 with a RuntimeError
reporting that it cannot open `earth_orientation/eopc04_14_IAU2000.62-now.txt`
in the pinned Tudat resource directory. Saved postchecks confirm that path did
not exist in the read-only image. No file is fetched, copied or provisioned.
The five admitted import-resource files retain their pinned identities; this
observation shows they do not establish complete model-setup resource coverage.
It does not prove every other resource needed by setup or its exact native call stack.

The617B trace retains four ordered markers: bootstrap-ready0.504755250s,
import-ready0.978874917s, context-ready1.004227500s and factory-enter1.004553417s.
No factory-return, visitor-enter, visitor-refused or complete follows. The original
factory was entered with simulateFalse; no completed factory return, visitor
refusal or final counter snapshot exists. Actual partial/internal native counts
remain UNKNOWN. No explicit integration or visitor request was reached.
Markers bracket the whole factory and adjacent observer I/O, not a native
instruction. The64B OpenMP warning is retained alongside the missing-file error;
it still does not explain historical0269's failure.

The failed observation returns after collector post-fsync at **6.641288042s**,
within unchanged60s inclusive45/10/5. The probe child failed before a producer
report or the full eight-marker auditor could run. Nested failed statuses and
immutable prefinal receipts are distinct from returned post-fsync observations.
The collector's final `failed-or-unavailable-after-fsync` status means the complete
success gate failed; it does not alone prove a failed fsync. Its actual post-fsync
return is preserved as a normalized parsed JSON observation, not byte-verbatim
tool stdout. The independent saved-only audit returns PASS_ACCOUNTED_FAILURE
and explicitly REJECTS full setup success. It is not a native/scientific pass.

Admission is at443.030395875s, episode start at450.143164083s
and consumption at450.258074291s on the one original600s clock.
The exclusive permission is consumed even though the native child failed.
All outer/episode records sum to12079structured bytes and213log bytes,
below2MiB/64KiB. Trace617B and all four lines stay below4KiB/512B. There is no
retry, relaxed deadline, changed scientific tolerance or resource supplementation.

## Preparation and verification

The exact0269 caller and0272 launcher are reused byte-for-byte. The new entry
changes only fixed setup dispatch identities; the external adapter copies the
qualified setup run_isolated body with only a keyword parent_command callback
and its call site. Independent review verifies these differences and all pins.
Three artificial actual-entry/adapter cases verify pass, unfinalized refusal and
inherited-clock stall rejection. An independent review found two issues in the
new outer output collector: loss of timeout partials and no explicit final60s
exit gate. Original source/finding are retained; both are fixed before launch.
Four fake-caller cases verify success, pre-episode failure, timeout-partial
retention and late refusal. Only the artificial timeout copy uses0.25s instead
of the external65s failsafe; production60s success criteria remain unchanged.
The65s outer failsafe cannot turn a late or failed outcome into success.

A temporary profile-preparation dict_items union error is corrected before
consumption, preserving its source/failure. Initial profiles are retained before
adding old test pins to the final cumulative49source/test pins. Neither correction
resets the preflight clock or creates a native episode. Final independent
prelaunch and collector reviews finish before the one actual observation.

All49source/test pins,10native pins,5resources and25old-ledger hashes match
afterward. All71459operational-prefix paths/1646916124regular-file bytes match
the protected baseline. Both recorded process groups are absent, the read-only
image is detached, new acquisition is0 and the carried497045495B stays unchanged.
No repository runtime/test/dependency/kernel/baseline or moon_to_mars.py changes.
Successful ADR0274 required8476test passes/Ruff checks are not repeated on
unchanged code. Only temporary artificial wiring and documentary checks run.

## Consequences and revisit conditions

F18.9 stays unchecked and is labelled CONSUMED/UNQUALIFIED; it cannot be rerun
under this permission. F17/F17.1/F18.3, completed-owner/carry/concurrency/ABI-FP/
prior arithmetic and physicalF0/M3/99-percent/safety gates remain open.
No physical trajectory accuracy or admissible command pair follows.

The next proposed decision is to inventory all model-setup resource dependencies
from retained sources/saved evidence before selecting any provisioning and new
execution contract. This proposal authorizes no source inventory, download,
resource modification or native retry by itself. The scheduler remains PAUSED.

## Evidence and verification

[Result](experiments/0275-never-run-setup-result.json) and
[immutable raw evidence](experiments/0275-never-run-setup-evidence.zip) retain
inputs, original/corrected preparation, independent prelaunch reviews, artificial
case evidence, consumed marker, four-marker partial trace, empty failed producer,
error logs, nested receipts, parsed encloser observation, independent saved-only
failure audit, preservation and detach/scheduler readbacks. Empty or incomplete
JSON files are authentic failure artifacts, not successful reports.
Archive:126members,98640compressed/195087expanded bytes;
SHA256 `fc7cb349728ae6304eb3619b291d84fda9da13d69e03e5a519caed9383b8db70`. [Final documentary verification](experiments/0275-doc-verification.json)
checks facts, raw artifact identities, preserved prior blobs, local links/anchors,
diff and strict OpenSpec, with independent documentary review.
