# 0264 — Qualify the prepared original-row fixture packet

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (user resumed the exact prepared packet)
Implementation: one packet consumed; import failed before fixture calls; F17/F17.1 incomplete
Scope / milestone: F17.1 / M3 manufactured native-helper preparation
Base revision: `69d09b902d3fa02169cf8ea0304c3000c33fb2b5`
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f17-resumed-fixture-packet-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis)
Supersedes / Superseded by: none; preserve ADR0263 and its failed packet

## Context and constraints

[ADR0263](0263-authorize-isolated-native-build.md) built one isolated kernel,
then failed import before any visitor call because runtime quadrature data were
absent. Two exact local files were subsequently pinned/copied; upstream release
content identity remains unverified. The user then said “включи автоматизацию
обратно” directly after the concrete new-packet proposal;69d09b9 records that
resumption. This admits the prepared packet, not a new build or mission experiment.

## Options considered

- Reset the old build/failed-packet clocks or retry the import silently: rejected.
- Execute the separately authorized fixed packet on the retained artifact after
  hash/isolation preflight: selected. Retain failure as a terminal result if needed.

## Decision and rationale

Bound preparation to600s. Restore the existing capacity-limited image at its
original path and verify source, unchanged runner, kernel/artifact, two local
quadrature files, qualified control source and selected manifests. No rebuild,
installation, HTTP, new data resource, SPICE, simulator construction or integration.
Use exactly11 manufactured fixture calls under one new60s inclusive wall clock,
64KiB parameter input and2MiB structured evidence; cap logs separately at64KiB.
The old3600s build and failed packet remain closed, never reset.

Reuse the qualified control implementation with only a new episode/log root,
the same restored volume and a stricter log ceiling. The original helper and
its ledgers remain unchanged. Check these adaptations with fake subprocesses,
network/write/operational-read isolation and process-group watchdog semantics;
record any setup-test failure rather than hiding it. The new clock starts once,
before native import, with the existing five-second finalization reserve.
Store/fsync packet/stage observations and verify completion within60s.

The fixed runner expects53-bit long double/double and8-byte long double; its
actual compiled-context observation is required, not assumed from source labels.
Two valid rows check exact hour, state/mass association, signed negative zero,
native-neighbor export and owned scalar words. Nine refusals check invalid
remainder/schema/history/row size/nonfinite state. Scalar rejections exercise the
shared predicate before Time construction; they do not fabricate invalid native
simulator history. Audit saved JSON independently against literal case/bit
expectations without more native calls. Stop on drift or failure; no import retry.

## Consequences and revisit conditions

Even success qualifies only manufactured const-map/helper plumbing. The production
owner method, lifecycle/concurrency/mutation, prior arithmetic, actual native carry,
frame/body/physical interpretation and F0 gates remain open. F17 is not automatically
complete. No official-package CI inheritance, physical command pair,99% probability,
mission safety or M3 completion follows. Continue only ordinary preparation within
accepted requirements; pause automation for a needed user decision or failure.

## Evidence and verification

[Result](experiments/0264-fixture-failure-result.json) and
[evidence archive](experiments/0264-fixture-failure-evidence.zip) retain the one
packet, exact profile/control sources, failure log and independent audits. The
archive has42members/171537uncompressed bytes (43800compressed), SHA256
`3712b497c935ae94dd91e2a41b591179e6c304fb854598a932bae8fa4f733f80`.

- Pinned preflight ended at538.711207208s, within600s. Source/runner/kernel,
  local math files and old helper/manifests matched; no new build or data copy.
- Fake guard checks passed with a preserved initial PID-parser failure: an xcrun
  warning preceded the numeric PID. A separate follow-up verified descendant
  termination and the streamed64KiB log ceiling; neither imported Tudat.
  The independent exact-three-line control review passed **after** launch;
  it is not an independent prelaunch qualification receipt.
- One packet imported the unchanged kernel and aborted with returncode-6 in
  0.294s; inclusive observation after stage fsync was0.341545s, within60s.
  Missing `station_locations/glo.sit` caused an uncaught native runtime error.
  No result JSON exists. Zero visitor calls follow from the pinned runner's
  import-before-loop ordering, not native instrumentation. No compiled context
  or manufactured outcome was observed; the eleven cases did not execute.
- Independent offline failure accounting passes. The intended packet auditor
  ran once and refused missing evidence, not a successful qualification.
  Its19pure artificial selfchecks were reported successful in the independent
  agent's tool output; no standalone stdout receipt was retained. The source and
  this limitation are saved; the checks were not rerun to recreate evidence.
- All71459 operational paths/1646916124regular bytes match the original manifest
  after this packet (11.219s verification). Prior project non-Markdown evidence,
  legacy model, links/anchors/diff and strict checks are recorded in the
  [documentary receipt](experiments/0264-doc-verification.json).

The isolated runtime preparation was incomplete. Named-source inspection explains
that namespace-static station maps eagerly read `glo.sit`, `glo.vel` and
`ns_codes.dat`; this is unrelated to the endpoint helper. The observed initializer
is **not** a complete import-time dependency closure. No file was added and no
second import was attempted. Automation `ariadna-m3` was immediately set PAUSED
through the official app tool; F17 and F17.1 remain unchecked.

A separately bounded metadata-only inventory found155existing local resource
files totaling2231646932bytes. Copying the whole tree would bring aggregate
acquisition to2728560765bytes, above the unchanged2GiB ceiling. No payload was
copied/hashed and upstream release identity remains unverified. Whole-tree copying
or a higher acquisition ceiling is not selected. The next proposed decision is a
complete minimal source-derived offline import-resource manifest and provisioning
preflight, followed only by a separately authorized finite packet. Avoid further
one-file-at-a-time import retries. Both failed packets and the build stay preserved.

Ariadna runtime/test code is unchanged; full pytest, Ruff and CI were not repeated.
No SPICE query, simulator construction, integration, physical result or successful
native-helper/owner qualification follows from this failure record.
