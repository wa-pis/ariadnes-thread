# 0253 — Qualify the fixed synthetic native arc seam

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (ADR0252 implementation, limited synthetic qualification)
Implementation: complete fixed private native fixture and independent oracle/auditor; no physical adapter adoption
Verification:147 focused,7436 portable and413 live passes; first six-arc fixture and independent analytic audit pass; documentation/strict receipt linked below
Scope / milestone: F7 / M3 preparation in the sole active change
Base revision: `ff2c5db657db90204ec5b2fb4c1402ee8cd1befb`, clean dev before four new files
Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-check-native-arcs-on-the-existing-analytic-witness), [contract](../../openspec/changes/refine-physical-trajectory/design.md#f6-native-analytic-arc-conformance-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; implements the existing synthetic contract only

## Context and constraints

[ADR0252](0252-design-native-analytic-arc-conformance.md) asks whether the actual
pinned native engine can execute the existing manufactured two-burn witness,
carry seven-state handoffs, reverse the same physical RHS and expose exact event
identity without float-label substitution. Earlier F5 injected affine arcs could
not answer this native question. The original physical F0 goal remains unmet.

## Options considered

- Connect the full mission optimizer now: missing native fractional-time, seed,
  full-force/derivative, safety/resource and independent endpoint-bound readiness.
- Implement the selected fixed witness only, reuse native low-level helpers and
  audit independent retained operands: selected, with no new public API,
  dependency, optimizer or generic backend.

## Decision and rationale

The private [native fixture](../../src/space_nav/_native_arc_conformance.py) uses
fresh synthetic native contexts, explicitly initialized constant zero Moon/Mars
origins, uniform gravity on every arc, dynamic TNW burns and the existing tighter
RKDP87/seven-state settings. Native Time keys determine both directional endpoints;
actual returned state AND mass cross each join. Reverse starts only from the
original exact-decimal100-digit target rounded once, never the forward output.

The separate [stdlib oracle/auditor](../../src/space_nav/_native_arc_oracle.py)
retains the unchanged original Decimal reference and independently computes
binary64-word F/g/b nodes with F/b, precision checks and signed conversion effects.
The producer uses those reference data for per-event acceptance, never as native
flow or handoff state. The auditor recomputes dimensional differences, exact
mass ledgers, event requests and source/runtime/counter bindings independently.
Native equality and unretained stage/history-domain observations remain explicitly
producer-observed; the auditor never reconstructs native identity from labels.

Precharged native/provider limits and bounded subprocess pipes/watchdogs enforce
the accepted workload. Durable output partitions (producer1MiB, audit512KiB,
combined captured pipes256KiB, receipt256KiB) fit the unchanged2MiB ceiling;
initial input remains64KiB. Native reported function counts remain post-run
telemetry. Closed-context counters mean logical runner-scope exits, not proof of
C++ object-graph destruction or arbitrary full-force isolation.

## Evidence and verification

Preparation fixed Conda-receipt version discovery, fail-stop clock errors,
initial-state word binding and exclusive/shared output accounting after
artificial checks/source review, before the first native attempt. No scientific
input, method, tolerance or cap was changed to obtain a pass. Python open and
SPICE-call guards deny the new fixture's archive/kernel/query paths; the inspected
constant-only native builder supplies additional source evidence. These guards
do not intercept opaque C++ I/O and are not a general scientific-access certificate.

Focused verification:147 artificial tests pass; the separately bounded first
cold native fixture passes all six arcs and its independent audit. Counts are
6 native attempts,7436 uniform-gravity provider entries,6 entered/exited logical
contexts, zero guarded SPICE/kernel/archive attempts and no optimizer entry in
the inspected fixed source path. Native function
maxima by arc are1807,91,1807,1820,91,1820; equal aggregate counts in this fixture
do not establish one-to-one provider/RHS accounting in general.

Across both references and both directions, maximum event errors are
1.6423941114122893e-7m,4.252323696171565e-11m/s and1.0396399643341289e-10kg,
within the original0.001m/1e-6m/s/1e-9kg gates. All12 start/end observations report
native equality and zero residual. The1004B input and66858B durable evidence
fit the fixed caps. The2.984904166776687s measurement precedes parent-receipt
writing; the separate post-fsync60s deadline check passed. Do not report that
pre-receipt value as a measured inclusive finalization duration.

Both required regression lanes pass:7436 portable with42 unchanged archival
skips,413 live, zero failures/errors. All1441 measured files and Git status
remain unchanged through both lanes. Ruff passes after final source/test changes;
two independent read-only reviews find no blockers. The new
[qualification receipt](experiments/0253-qualification.json) binds source/test
hashes, raw first-native data, focused/full JUnit, logs and frozen-checkout proof.
The separate [documentation receipt](experiments/0253-doc-verification.json)
records local links/anchors, prior non-Markdown byte preservation, diff and strict
OpenSpec checks. CI is unobserved at this local qualification; a later source-bound
CI result must use new evidence, preserving this receipt.
No previous experiment artifact, scientific baseline or legacy model is changed.

## Consequences and revisit conditions

F7 qualifies this fixed synthetic integer-event engine seam only. It does not
adopt an F5 native response/optimizer, qualify F0's large or fractional events,
full-force derivatives/guards/reverse path, independent physical endpoint bounds,
or provide the original admissible command pair. The production six-control
FD/lstsq method and73/76/228/300s ceilings remain unchanged. No mission, SPICE
acquisition, consumed-study replay, R5.60, M4–M6, ML or UI qualification follows.

Continue only the smallest accepted readiness/design step toward the original
physical problem. A changed scientific contract needs an explicit decision;
ordinary reversible preparation does not need repeated permission. Preserve the
raw successful/failed receipts and source-bound CI separately without overwriting
history; numerical conformance is not physical fidelity or mission safety.
