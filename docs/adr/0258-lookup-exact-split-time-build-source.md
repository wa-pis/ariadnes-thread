# 0258 — Look up the exact split-Time build source

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (one bounded source-provenance lookup only)
Implementation: no production code or native adapter change
Verification: exact artifact/declarations independently audited; full lookup incomplete from controller EOF; documentary/strict checks below
Scope / milestone: F12 / M3 preparation in the sole active change
Base revision: `9d82f85775f0b08bac47e61397a64f0bc07bf4c4`
Related OpenSpec: [lookup contract](../../openspec/changes/refine-physical-trajectory/design.md#f12-exact-build-source-provenance-lookup-2026-11-25), [conditional readback requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves ADR0257 and every physical gate

## Context and constraints

[ADR0257](0257-design-conditional-split-time-enclosure.md) isolates two unqualified
premises: the installed compiled exporter/caster route and a lawful finite native
domain. Its conditional adjacent-neighbour lemma is not actual readback evidence.
The exact installed py312 extracted cache is absent. This stage attempts only to
recover source/build provenance from the exact immutable package identity.

The canonical contract fixes the question, completion criterion, artifact, source
reference, unchanged model/gates and600s/8response/256MiB/16MiB/4MiB limits
before the first request. No runtime/scientific work or dependency changes follow.

## Options considered

- Treat the retained different-ABI recipe or a current upstream header as actual
  build evidence: rejected; identities do not match the installed package.
- Install/rebuild/execute a library to probe the path: deferred; source lookup
  is enough to determine the precise next missing fact without changing runtime.
- Retrieve at most one hash-verified exact artifact and its pinned primary source
  records, retaining uncertainty layers separately: selected.

## Decision and rationale

Use one exclusive bounded lookup, as specified in the linked design. Package
identity, recipe declarations, selected-build evidence and binary/domain
qualification are different outcomes. A package recipe can name pybind11 without
proving the headers/macros that generated the installed binary. No successful
source retrieval may silently promote actual epoch or physical admission.

## Consequences and revisit conditions

This source preparation may resolve a concrete provenance gap; it cannot prove
finite native inputs, exact event carry, mass/force effects or endpoint accuracy.
If the record is incomplete, preserve the precise gap instead of retrying or
substituting versions. Ordinary reversible source lookup is already authorized.
Pause only for a concrete required user/access/dependency/contract decision.
Any later implementation/native experiment needs its own complete scoped contract;
no automatic diagnostic chain or changed F0 target follows.

## Evidence and verification

The contract preceded one external attempt. HTTP200 returned23975956bytes and
the complete SHA-256 matched the installed py312 artifact identity. Only its
metadata component was decoded:532480bytes/28safe unique regular members. The
eight captured selections total326681bytes; later offline extraction retained
the458byte `info/git` record from the same saved component. No package payload
component was decoded and no package content was executed.

The controller then encountered stdin EOF after reporting ready and before any
primary caster-file fetch or successful finalization. Both original failure and
outer receipts remain incomplete, exit2. The outer4.048007s observation precedes
its final-receipt writing; it is not inclusive post-fsync completion evidence.
No second capture, new request or hidden retry repaired this attempt. F12 stays
unchecked because its complete lookup/receipt obligations were not satisfied.

Independent offline audits verify the whole saved package hash, raw metadata
component, all selections and declarations. The exact recipe declares pybind11
and pybind11-global3.0.1 with their build strings, Clang18.1.8 and requestedC++14.
Its feedstock revision is `7e891d1257b2ca0f1bede583cdeea2e2f01a8063`; the archived
Git record names TudatPy checkout `2300d7fe3d7db4db9a78dd4a9a4a713f614da22d`.
The Time header, pickle binding and shipped CMake file match package paths hashes
byte-for-byte. That CMake record uses pybind11 include/definition variables; their
actual effective values and the compiled generic caster remain unqualified.
Build-script flag declarations do not prove complete effective FP behaviour.

The immutable [source lookup ZIP](experiments/0258-source-lookup.zip) preserves
raw metadata, selected records and original failure receipts. The separate
[lookup verification](experiments/0258-lookup-verification.json) records identities,
scope, partial result and limitations. It retains the full package outside the
repository; the metadata-only ZIP is not a standalone cryptographic membership
proof for that full package. A [documentary receipt](experiments/0258-doc-verification.json)
records links/protected bytes/CURRENT/diff/strict checks. No runtime tests were
rerun; all production/scientific source, inputs and gates are unchanged.

Next preparation must reuse the retained exact package/info records and archived
source revision. Any narrowly scoped missing primary-source acquisition needs a
distinct bounded, noninteractive contract; do not restart this controller,
redownload this artifact or build a generic invocation framework. The actual
readback/domain basis and physical pair remain unavailable.
