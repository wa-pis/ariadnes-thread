# 0278 — Qualify artificial six-file provision and admission

Date: 2026-11-27 (Europe/Samara)
Decision status: accepted for F18.12 artificial preparation only
Implementation / verification: temporary transaction/admission complete;94/94 artificial cases and independent source/reuse review PASS
Scope / milestone: F18.12 / M3 private setup preparation; no mission calculation
Base revision: `d6534c567ecbeb0dc96364915a6c8a6abe5ceddc`, clean dev before preparation
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f1812-artificial-transaction-and-admission-result-2026-11-27), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture)
Supersedes / Superseded by: none; preserves0275consumed failure and0277future contract

## Context and constraints

The user asked to continue tests and enable automation after this stage.
[ADR0277](0277-design-supplemented-setup-test.md) permits temporary stdlib preparation
on fabricated files,120s/2MiB per invocation. No real resource payload reads/copies,
mounts, provisioning, native-science imports, SPICE or integration are admitted by
this stage. Successful preparation does not prove that Tudat setup will succeed.

## Options considered

- Reuse old five-resource admission or regenerate its adapter: insufficient for
  the new six-resource proofs; rejected by0277.
- Change package APIs/dependencies or add a reusable provisioning framework:
  unnecessary for one fixed setup diagnostic; not selected.
- Keep four qualified runtime controls unchanged, adapt only three outer paths,
  and qualify a temporary fixed-six transaction plus narrow admission: selected.

## Decision and rationale

The archived temporary provisioner validates exact six names/lengths/hashes and
non-symlink files/ancestors, writes an exclusive carried-byte precharge before
payload writes, then stages/fsyncs/readbacks and publishes one directory using
Darwin renameatx_np with RENAME_EXCL. Occupied targets, including an empty directory
created during the race, are refused without replacement. Failure retains partial
state and the charge; no hidden retry or rollback is implemented.

The separate admission checker binds precharge, provision, finalized outer outcome,
fresh read-only11file proof, source/native/control/old-ledger pin groups, full
profile/probe values and clock. Artificial mode requires fabricated inputs and an
explicit fake observer; its success cannot authorize native dispatch. Native mode
is fixed to the future namespace/official contract and cannot accept injected clock
or observer, but its positive image/mount path was not exercised here.

Durability is part of success. Provision's disk receipt remains pending outer
readback; admission's disk candidate remains PENDING_DURABLE_ADMISSION with
launch authority false. Only a successfully returned post-fsync result can be
considered by a future caller. This module does not emit launch-admission.json.
A future caller must bind that observed result to a fresh durable final launch
gate, refusing leftover files, late/failing fsync and stale profiles. That final
live gate and actual read-only image admission remain prerequisites for F18.13.

Four0275controls are byte-identical; run-once.py/native.sandbox/check-preservation.py
have exactly one literal namespace substitution each, independently compared to
explicit top-level members of the pinned0275archive. They were not executed.
An initial copy assertion found multiple basename call-once.py archive roles and
stopped before any copy; explicit top-level member selection corrected that check.
No adapter regeneration, oldprepare execution or runtime behavior change occurred.

## Evidence and verification

The [result and member manifest](experiments/0278-artificial-provision-admission-result.json)
and [25-member evidence archive](experiments/0278-artificial-provision-admission-evidence.zip)
preserve final sources,94-case driver/controller/logs, receipts, observed return,
prepared controls, source-review findings and completion reviews. Archive54054B,
SHA256 `76b2c10d5a35054fe0c16c8c2411132988e048f13c33ea75fcf6dff1e24387d8`;
expanded evidence171660B plus result7515B, below2MiB. Fake payload fixture trees
are not retained as evidence.

One invocation:94passed,0failures/errors/skips. Observed completion after outer
file/directory fsync1.1421269583515823s<120s, timed before qualification-child startup
through the final returned observation. Saved invocation records20982B including
outer receipt. Later review, observation-copy recording, packaging and documentary
checks are separate from that closed clock. Prefinal disk receipts alone do not
establish the reported completion.

Tests use six fabricated payloads totaling3578887B and five fake old files for an
exact11file readback. This is the full new payload volume, not a claim to reproduce
all131662oldpayloadbytes. Carried497045495+3578887=500624382<2GiB is tested arithmetic,
not real acquisition. Positive publication/admission, rejected badsize/hash/
nonregular/symlink/ancestor/occupiedtarget/race/shortread/overflow/clock/copy/fsync/
publication, and missing/stale/rehashed semantic proof failures are covered.
Tests connect actual temporary provision to artificial admission; live positive
admission is explicitly untested.

Independent source review initially found unbound native probe values, incomplete
control/profile binding and disk PASS before final fsync. These were corrected
before the first test invocation. A follow-up finalized-outcome omission was also
corrected, with three hash-rebound semantic refusal cases. Initial sources/findings
are retained; the60632follow-up source is an exact hash-verified reconstruction,
not an asserted pre-fix capture. Final independent code/reuse review PASS, no
remaining findings. This was preparation feedback, not a failed scientific run.

Repository runtime/tests/dependencies were unchanged. Prior8476passes/42unchanged
archival skips/Ruff from0274 remain retained and were not rerun. New temporary
logic has the94-case qualification and independent connected-source review.
[Document verification](experiments/0278-doc-verification.json) separately checks
facts/artifacts/AST/member hashes, protected history, links/anchors, shortCURRENT,
diff and strict OpenSpec.

## Consequences and revisit conditions

F18.12 alone is complete. F18.13 remains unchecked and unexecuted: first record
its distinct concrete execution/admission decision, prepare/check the minimal
final outer gate, and independently admit the actual isolated provision/read-only
restoration on a fresh original600s preflight before any once-only setup. Ordinary
reversible diagnostic decisions and tests are already covered by the user's
continued-tests instruction; ask only for an actual missing access/data/action
or scientific choice. Automation remains ACTIVE every5minutes for that next step.

No real resources were read/copied, image remained unmounted, and no Tudat/kernel
import, SPICE, integration or new native setup occurred. Original60s45/10/5 and
all other0277caps stay fixed; F18.9 remains consumed/unqualified. Owner/carry/
concurrency/ABI-FP/prior-arithmetic and physicalF0/M3/99-percent/safety gates remain
open. Artificial filesystem/admission correctness is not trajectory accuracy.
