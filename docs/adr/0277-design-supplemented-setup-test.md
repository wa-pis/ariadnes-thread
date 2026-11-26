# 0277 — Design one supplemented never-run setup test

Date: 2026-11-27 (Europe/Samara)
Decision status: accepted for concrete design and ordinary artificial preparation
Implementation / verification: F18.11 design complete; independent review PASS; transaction/admission preparation and actual provision/setup not performed
Scope / milestone: F18.11 / M3 private setup diagnosis; no mission calculation
Base revision: `62ba9878eca62e2b2242223c505a0f269546871c`, clean dev before design
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f1811-six-file-supplemented-setup-contract-2026-11-27), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture)
Supersedes / Superseded by: none; preserves0275consumed failure and0276source result

## Context and constraints

The user resumed automation and continued tests. [ADR0276](0276-inventory-fixed-setup-resources.md)
identifies six locally available eager converter payloads, absent from the isolated
image. This is source-linked local identity, not upstream authentication, parser
validity, full linked-binary closure or runtime success. [ADR0275](0275-record-failed-never-run-setup.md)
remains consumed/unqualified. Its four markers do not identify an exact native
instruction or prove that all six readers were reached.

This stage designs a distinct minimal resource/setup profile within600s of saved-
source reasoning and independent review. It performs no mounts, native/project
imports, tests, resource copies/provision, download, build, SPICE or integration.
A later transaction and setup need separately recorded execution/admission; this
contract does not replay the failed F18.9 permission. Ordinary reversible artificial
preparation can proceed under the user's continued-tests instruction without
asking again merely because a local guideline proposes confirmation.

## Options considered

- Add only EOP and retry: rejected; ignores the five other source-visible readers.
- Copy all resources/rebuild or change imports, environment or deadlines: unnecessary
  for the present question and changes the diagnostic path; not selected.
- Add exactly six pinned local files to isolated HOME, restore read-only state,
  then observe the same fixed setup/refusal once under a new identity: selected
  as the concrete future contract, conditional on preparation and admission.

## Decision and rationale

### Exact resources and isolation

The [machine-readable contract](experiments/0277-supplemented-setup-contract.json)
pins all six paths/sizes/SHA256 and the exact original16environment entries.
Under `earth_orientation/` these are EOP14, historicalDeltaT, UTC libration and
UTC ocean-tide amplitudes plus both corresponding fundamental-argument tables.
Exactly3,578,887B would be added, keeping the old5files/131662B unchanged:
11files/3710549B total. Carried acquisition497045495B becomes500624382B<2GiB;
8GiB scratch ceiling stays unchanged. No downloads/installer/dependency change.
The actual operational HOME/Conda environment is never modified.

Before any real mount or write, a future fresh600s preflight starts with a new
exclusive episode namespace `/private/tmp/ariadna-f18-supplemented-setup-v1`.
It is not this design clock or any old consumed clock. Verify clean dev/base,
no competing work, original49source/test+10native+5resource pins and25old ledgers,
plus preserved0275/0276evidence. Verify exact six local regular nonsymlink files,
real nonsymlink parent directories and absent destination using lstat/lexists.
An existing destination, including a dangling symlink, is occupied and refused.

Only this future provision phase may mount the existing isolated image writable.
Create/fsync an exclusive acquisition precharge carrying the old balance before
payload writes; never edit/reset an old ledger or roll back this charge after
partial failure. Create one same-filesystem sibling staging directory; write six
exclusive bounded files, fsync and read back all names/lengths/hashes, fsync stage.
Recheck final absence and publish the directory atomically **without replacement**;
ordinary os.rename's ability to replace an empty directory is insufficient.
The local macOS SDK declares renameatx_np and RENAME_EXCL0x4; a tiny temporary
stdlib/ctypes filesystem call may use that primitive only after artificial
qualification, failing closed if unsupported. This is no Tudat/native-science call.
Fsync parent and completion receipt; failure retains evidence and forbids launch.
Do not claim that old0266copier source is reusable: its scheme/receipts are saved,
but the actual copier source was not located among inspected artifacts.

Read back exactly11regular resource files with no extras/symlinks, then detach and
remount at the original path read-only. Independently confirm ST_RDONLY, capacity,
all11resource hashes and original source/native/ledger pins. No native test may
run with the image writable. Any provision/remount/admission failure means no
launch, controlled detach and immutable failure evidence, without hidden retries.

### Reuse and fresh admission

Reuse saved0275`call-once.py`, `launch-once.py`, `native-entry.py` and
`supervisor-adapter.py` byte-for-byte; contract pins their identities. Keep their
historical F18.9 labels/docstrings as provenance, while new outer records name
the new episode. Collector/sandbox/preservation scripts need only exact namespace
substitutions, checked by normalized diff. Do not rerun oldprepare.py or regenerate
the adapter: it encodes old five-resource assumptions and unnecessary mutations.

A small new temporary admission check must bind and recheck actual provision,
precharge, fresh read-only11file manifest, outer profile, control/source/native/
ledger identities and clock. Oldadmit-launch.py alone does not prove new resources;
this is narrow **new** admission logic with artificial rejection tests, not a
namespace-only change. Keep `probe_input`'s exact ten keys unchanged; resource
proofs belong to the outer profile/admission. Pin all prepared controls before
independent admission; no launch after missing, stale, drifted or exhausted proof.

### Fixed question and ceilings

Only ask whether the original `_native_factory('never-run', False)` returns an
owner whose first `_ariadna_original_endpoint(True, SCHEMA)` raises **exactly**
RuntimeError, message `completed original results unavailable`. Preserve original
initial words, synthetic SSB/J2000 settings, constant acceleration and mass,
never-run interval and all retention flags. SCHEMA remains
`cartesian-position-m_velocity-m-s_mass-kg`. No physical target or tolerance changes.

Require1context check (native53/53/8, helper list53/53/8),1factoryFalse,0integration,
1visitorTrue and the100000precharged acceleration callback cap; never assume zero
constructor callbacks or infer partial counts without a final snapshot. All eight
original <=512B markers fit4KiB. Reuse qualified producer/auditor and exact refusal,
childexit0, durable report/trace, independent saved audit, group cleanup and observed
post-fsync requirements. A partial trace supports failure accounting only.

Future preflight600s includes provision/read-only restoration/review through
consumption. The separate original60s episode (45producer/10audit/5finalization)
begins before cold import;64KiB input/combined logs and2MiB aggregate structured
records include outer evidence. The65s external failsafe contains failures only;
it cannot admit a result after60s. Preserve exact role flags/HOME/TMP/thread
settings, source/kernel/binary and old payloads. New resource proofs are checked
before episode consumption; they do not reset either clock or provide a time bonus.
After any result, retain full/partial evidence, verify recorded groups absent,
protected operational paths/old pins unchanged and image detached. No second setup,
added file, full-owner packet, integration or physical-gate claim follows.

## Consequences and revisit conditions

F18.11 is design only. Next F18.12 may prepare just the temporary fixed-six file
transaction and narrow admission checker. A <=120s startup/asserts/receipt-inclusive
artificial invocation covers six-file success and full byte volume, exact11file
readback with five fake old files; hash/size/nonregular/symlink/ancestor/existing-
target/race/overflow/deadline refusals; partial copy and fsync/publication failures;
stale/missing/tampered admission and clocks. Use fabricated tempfile payloads,
not real resources or native imports;2MiB evidence cap, no real acquisition.
Unsupported no-replace publication fails closed. Do not add a generic framework.

No repository runtime/test/dependency change is expected. Reuse successful0274
8476passes/Ruff and0275wiring qualifications where logic is identical. Qualify new
transaction/admission logic and any substantive control change directly. If actual
repository behavior changes, focused checks, frozen required portable/live make
test, Ruff and strict validation are required. Preparation cannot manufacture a
native result. F18.13 remains unexecuted pending its distinct recorded decision
and fresh independent admission after F18.12, never oldF18.9reuse.

Automation stays ACTIVE for preparation and pauses if real access/data/action or
a scientific-contract choice needs the user. All owner/carry/concurrency/ABI-FP/
prior-arithmetic and physicalF0/M3/99-percent/safety gates remain open; even later
success would qualify only the never-run setup/refusal seam, not mission accuracy.

## Evidence and verification

[Contract](experiments/0277-supplemented-setup-contract.json) and
[saved-source design evidence](experiments/0277-supplemented-setup-design-evidence.zip)
retain the original design clock, exact proposed local payload/control pins,
source excerpts and independent reuse/design reviews. [Final documentary verification](experiments/0277-doc-verification.json)
checks protected history, links/anchors, artifact syntax/digests, shortCURRENT,
diff and strict OpenSpec. Design acceptance is not implementation/runtime success.

Independent design review PASS at410.832705s; complete saved-source reading phase
ends443.133210s<600. Initial machine-contract admission label was corrected before
acceptance; the original draft/finding are preserved. Two false self-pin flags in
the reuse receipt are clarified against all14immutable0275archive member pins,
which match. No mount/runtime/test/copy/provision/download/SPICE/integration/build
or dependency action occurred. The9member archive is26771B, SHA256
`50d38b0b70820f8dbdce4bf69c5f290ccc9bdc6d29cff19d43722359c1fda292`. Final links/history/diff/strict checks are separate from this
closed source clock.
