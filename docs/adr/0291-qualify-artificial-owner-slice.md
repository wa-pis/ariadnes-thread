# 0291 — Preserve the failed artificial owner-slice qualification

Date: 2026-11-27 (Europe/Samara)
Decision status: accepted (failed evidence and bounded software correction)
Implementation / verification: F18.21 incomplete; one artificial invocation consumed
Scope / milestone: M3, temporary artificial controls only
Base revision: 9d55df2ad416a916c55bb3a26e6b17b2c02d7b12
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture)
Supersedes / Superseded by: none; preserves [0290](0290-map-full-owner-controls.md)

## Context and constraints

ADR0290 permitted exactly two temporary controls and a small artificial harness.
The existing producer-only worker-construction seam and unchanged guarded audit
command were independently source-reviewed. Source closure was170.363677s<600,
with13326B before receipt. Three candidate files were separately reviewed and
frozen before execution; repository fixture/run/audit and all scientific inputs,
oracles, metadata, tolerances and counters remained unchanged.

## Options considered

- Mark the slice complete because static review passed: rejected by actual evidence.
- Delete failed records, enlarge payload caps or repeat the consumed invocation:
  rejected; this would obscure a software failure and change its recorded scope.
- Preserve the failure and correct only the interpreter identity reader in a fresh
  reviewed artificial version: selected, under existing reversible-work authority.

## Decision and rationale

Exactly one focused invocation ran12named methods:3passed,9errored,0assertion
failures. Actual return after external-receipt file+directory fsync was0.674372s
<120. It reported151782B structured evidence and15083B logs across the qualification
root, below2MiB/64KiB. The saved case subtree is24files with57973B structured
evidence and15083B logs; do not confuse it with the reported40-file root inventory.
The original process cleanup, aggregate-limit and directory-fsync helper checks
passed. This is not a pass for the new connected adapter/entry slice.

All9errors occurred in harness setup while hashing the pinned outer interpreter:
path_pin→pin→read used the generic2MiB artifact-read default. The unchanged Python
executable is6829984B, matching saved0286metadata, and already fits the adapter's
separate16MiB interpreter-pin bound. Confusing artifact payload capacity with
interpreter identity input prevented every entry and original worker/audit launch.
Pure injected fixture generation did occur before that setup error; do not call
this zero fixture work or a scientific/native experiment. No new binary hash,
TudatPy/SPICE import or integration was performed by the diagnosis.

Pre-invocation fixes were static code-review revisions, not experimental retries:
role-specific audit source, durable pre-dispatch command witness/readback, actual
original-start binding and corrected refusal/finalization checks. Initial whole
candidate bytes were not saved before those edits; only the observed pins/findings
are retained. Do not reconstruct or claim preservation of missing versions.
Frozen final candidate bytes, the single failed execution and all saved outputs
are immutable. /private/tmp/ariadna-f18-0291 is consumed; no cleanup/relaunch there.

### Accepted correction — F18.22

Prepare one fresh artificial version in /private/tmp/ariadna-f18-0292. Correct only
the harness interpreter-identity path: bounded streaming hashing of the known
6829984B executable against retained SHA
795d8316b7dabff1c64e56d5f5787caf0fe1b1e18580d34fc3a4956d501475c2,
under the adapter's existing16MiB interpreter-input bound. Keep2MiB structured
payload/evidence and64KiB logs, source/input/audit/receipt partitions and all
scientific gates unchanged. Hashing the interpreter does not copy it into evidence.

The two control copies may change only the fixed namespace0291→0292 and derived
self/path pins; verify that transformation byte-for-byte. Keep original repository
fixture/run/audit unchanged. Before execution, freeze the new three candidate
sources, exact input/descriptor/command recipes and new interpreter pin function;
independently review the connected change, including a focused synthetic over-bound/
wrong-hash refusal within the same qualification. No generic framework, source
campaign, API/profile/admission/gate/operator rollout or native authority is added.

Run one reviewed invocation<=120s including cold start and durable finalization,
targeting the9previously blocked methods. Reuse the3already passed helper results;
exercise their ordinary connected positive finalization/cleanup without repeating
those unchanged helper tests. A future9-method pass plus retained3helper passes
must not be called one original all-green12-method run. Retain each packet's
original60s45/10/5,65s failure-
only cleanup, exact original-start binding, unchanged real independent-audit argv,
2MiB/64KiB caps and existing0267counters/oracles. Preserve recipe-before-invocation
versus dynamic clock/packet/argv-before-dispatch observations honestly.

Require independent code/evidence review, actual-return timing, protected history,
links, diff and strict validation, immutable ADR/OpenSpec/CURRENT, commit/push.
Any repository executable/test/dependency diff still requires the project focused/
frozen make test portable+live<=1800s/Ruff checks. No repeated unchanged full suite
for documentary artifacts. This reversible software correction needs no new user
choice; actual native work still needs distinct explicit choice/fresh admission.

## Consequences and revisit conditions

F18.21 remains incomplete. No entry/producer/audit behavior or full0267native
lifecycle was qualified by this run. Native0285authority remains consumed/image
detached; preserve all old native namespaces, failures and resources. General
export/physical chain/endpoint bounds, physicalF0/M3/99-percent/mission safety
remain open; no later milestone or scientific experiment follows.

## Evidence and verification

[Failed result](experiments/0291-artificial-owner-slice.json) and
[immutable evidence](experiments/0291-artificial-owner-slice-evidence.zip) retain
source/candidate reviews, exact three-file freeze, full failed logs/partials,
actual tool stdout, external cleanup and executable-stat/saved-profile diagnosis.
Independent offline evidence review passes the accuracy of this failed record;
it does not convert the execution into a success. No invocation was repeated.

[Documentary verification](experiments/0291-doc-verification.json) checks original
Git blobs/source pins, archive syntax/member hashes, reviews, links/anchors,
CURRENT length, diff and strict OpenSpec. Production code/tests/CI/dependencies
and moon_to_mars.py are unchanged; the full suite/Ruff/native campaigns were not
repeated. Archived unqualified temporary code is evidence, not an installed change.
