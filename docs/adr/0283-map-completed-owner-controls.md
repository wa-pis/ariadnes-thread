# 0283 — Map the completed-owner outer controls

Date: 2026-11-27
Decision status: accepted
Implementation: mapping complete; changed controls and artificial qualification not started
Scope / milestone: M3, F18.15a.1 source/saved design only
Base revision: 9feb1c12ef9045ce449302bd14b41a27368e61c2
Related OpenSpec: [research requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; refines the separate outer-control prerequisite of [0281](0281-design-single-completed-owner.md) and [0282](0282-qualify-artificial-completed-owner.md)

## Context and constraints

The single completed-owner producer/auditor passed artificial and full required
regressions in0282. Existing0280outer admission instead fixes a never-run owner,
integration0 and provisioning proofs. It cannot authorize integration1 by changing
labels. The question here is which old controls can actually remain unchanged,
not another scientific calculation. Source/saved mapping and independent review
share one600s/2MiB budget; documentary packaging follows separately.

## Options considered

- Retag the old recursive setup parent, supervisor and admission: rejected because
  their scope, inputs, counts and authority differ.
- Keep profile-agnostic caller/launcher, replace only the fixed entry/collector and
  completed admission, and remove the redundant recursive parent: selected. This
  retains established deadlines and process-group cleanup with fewer stages.

## Decision and rationale

The [mapping result](experiments/0283-completed-control-mapping.json) binds the
exact draft and independent source review in its
[immutable evidence](experiments/0283-completed-control-mapping-evidence.zip).
Eight active controls and one separately pinned external gate are proposed:

| Control | Reuse classification |
| --- | --- |
| call-once.py, launch-once.py | Byte-identical, profile-agnostic |
| native.sandbox, check-preservation.py | Exact namespace substitution only |
| run-once.py | Changed logic: namespace/label and bounded final directory durability |
| native-entry.py, supervisor-adapter.py, admission.py | Changed logic; separate qualification required |
| dispatch-once.py | Changed external admission gate, outside the eight-control set |
| provision.py | Historical provenance only; no active provisioning |

The single entry session owns the collector and both subprocesses. Only
supervisor.pgid is recorded; parent.pgid is absent. Producer and independent
saved auditor inherit that group. The inner watcher kills only its direct child;
the unchanged outer launch watcher must kill the entire entry group even after
its leader exits. The changed run-once must sync the enclosing root/work/caller/launch directories
bottom-up after final artifact creation and before terminal original60s
observation; the collector packet-directory sync alone is insufficient.
Qualification must exercise descendant writers/stalls, retained
pipes, errors and opaque fsync stalls under the original clock.

The collector imports no completed producer/scientific runtime. It checks the
exact completed schemas, mode/scope/hash bindings, ten markers and separate
counts, durable report/trace then observation, independent audit and outer
finalization. Original45s producer,10s audit and5s finalization share one60s
inclusive budget;65s is failure cleanup only. Existing byte limits remain.

For connected artificial qualification, an explicit harmless harness invokes the
same entry/collector functions with bounded pinned child-command overrides and
fake resources. Its child calls the real probe with all six fake hooks and
mode=injected; the real guarded auditor runs separately. The outer mode is
artificial. Native CLI/profile accepts no replacement flags/command fields and
rejects supplied overrides before live reads. Fake readonly observations never
establish native-positive qualification or native authority.

Preserve all49old source pins and append the two modules/two tests from0282,
yielding53. Preserve10native pins,11retained resource identities and the25old
ledger entries; additionally bind all86members of0280, including its consumed
marker, profile, proofs and raw result. New acquisition is0; historical carried
acquisition remains500624382B. Fresh actual readonly readback and observed
admission, under a new original600s preflight, must not reuse historical proof
timestamps. Only low-level read/pin/live-observation primitives may be reused;
old admit()/dispatch authority is excluded.

## Evidence and verification

Source review checked the saved control bytes and current49+4source pins, without
reading live mounted payloads. Independent review and observed source-phase
completion remained within the original600s/2MiB; exact measurements are in the
result. One preliminary design-builder assertion mistook profile.resources (a
directory string) for the saved11-entry readback list. It was corrected before
the mapping draft was emitted; both builder versions/correction are retained.
Independent source review caught an enclosing-directory durability gap in the
first mapping. The revised mapping classifies run-once as logic-changed and
requires its bounded final directory sync; both drafts and the initial finding
remain saved. This is a pre-implementation design correction.
No diagnostic, artificial runtime test, mount, native import, SPICE or integration
was executed. Prior212focused/8688required successes were not repeated on
unchanged code. Documentation checks cover protected blobs, evidence syntax/pins,
local links, diff and strict OpenSpec; these are not runtime qualification.

## Consequences and revisit conditions

F18.15a.1 mapping is complete; F18.15a remains open until the changed temporary
controls and connected artificial checks pass within300s with independent review.
Prefer saved fixed controls outside the package. Package/test changes additionally
require frozen full make test1800s and Ruff. Record exact new bytes before tests;
do not add a general orchestration framework.

F18.16 remains unadmitted: distinct recorded execution choice, clean committed dev
and fresh independent actual600s admission are still required. The proposed actual
namespace has not been created. Consumed episodes, original fixture/science,
resources, kernels, numerical gates and moon_to_mars.py remain unchanged. Full0267
owner/lifetime, carry/concurrency/full-core ABI/FP, arithmetic and physicalF0/M3
gates remain open. No admissible command pair,99-percent probability or mission
safety conclusion follows. Revisit for a concrete failing qualification or an
accepted contract change, preserving this design and all prior evidence.
