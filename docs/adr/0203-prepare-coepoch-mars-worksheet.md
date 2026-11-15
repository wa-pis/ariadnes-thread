# 0203 — Prepare the offline Mars checkpoint worksheet

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted preparation under [ADR0202](0202-design-coepoch-mars-receiving-state.md).
- Implementation: R5.56 complete on synthetic inputs; R5.57 unexecuted.
- Verification: full artificial shard, bounded write and readback, focused and guarded full pytest passed.
- Scope: exact-epoch ideal reference and signed model comparison.
- Base revision: `2bf7217cbf5cd2abc2664e3c55cb5fc9ed8cd07c`, with exactly the five pinned preparation files present during verification.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-design-an-independent-mars-receiving-state), [design](../../openspec/changes/refine-physical-trajectory/design.md#r556-prepare-the-offline-coepoch-worksheet-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[ADR0201](0201-authenticate-lunar-exit-record-receiving-gap.md) found no
archived receiver at the authenticated R5.51 checkpoint. ADR0202
defines a Sun-only analytic comparison for that exact epoch and
preserves the separate R4 physical join. This stage prepares the
comparison and qualifies its limits entirely on artificial inputs.

## Options considered

- Build a new propagator or query a new Sun state: unnecessary for the
  ideal worksheet, and outside its archive-only contract.
- Reuse the frozen R2 scalar arithmetic and the R5.53 archive and
  isolation primitives: selected; the new code binds the smaller
  workload and records an ideal result separately from physical gates.

## Decision and rationale

The [worksheet](experiments/0203-coepoch-worksheet.py) verifies the R1
reference and its R2 audit binding, reconstructs the departure seed
and checks that the arrival seed uses the spacecraft's pre-impulse
velocity. It authenticates the embedded R5.54 attempt/report/receipt,
both R5.51 archive phases' metadata and the one selected study shard.
Two decoded records establish exact Sun coepoch, geometry and
matching ordered kernel metadata. The runtime guard rejects
scientific imports, CSPICE loads and kernel-file reads.

The [arithmetic](experiments/0203-coepoch-arithmetic.py) computes the
ideal state from both endpoint seeds using the pinned R2 ellipse and
root method, including the two velocity sign changes for the reverse
path. It checks both frames and endpoint invariants and records
signed ideal-minus-B differences. Ideal mass and all four physical
residuals are null. The parent bounds wall time through finalization,
reserves output exclusively and verifies the child report through
digest-bound readback. A late marker vetoes certification.

## Evidence and verification

The [full artificial fixture](experiments/0203-coepoch-fixtures.py)
contains one study shard with **42,862 lines, 16,777,216 raw bytes
and 5,207,814 gzip payload bytes**. The process also verified
1,982,095 bytes of compact inputs and 4,791 bytes of archive
metadata. The complete invocation took **0.141 s of 15 s**,
including interpreter startup and finalization, with
64,307,200 bytes peak child RSS and
5,489 output bytes. Fixture generation and
separate readback are outside that elapsed measurement. The
attempt, report and parent receipt match their stored digests.

Both analytic paths took 49 root updates. Their sampled agreement
was 0.178 mm and 4.15e-11 m/s in
each frame, inside 1 m and 1e-6 m/s. Against the independent
artificial ellipse constructed with Newton roots, the largest
position and velocity vector errors were 0.747 mm and
1.80e-10 m/s. An injected signed model difference was recovered
within 0.01 m and 1e-8 m/s; this comparison does not use a
physical join tolerance.

The [verification manifest](experiments/0203-verification.json)
binds tested sources, the full-volume report and receipt chain,
profile and check digests. The fixture and originals remain at
`/Users/agrudin/dev/my/ariadna-evidence/R5.56-verified` outside Git.

All **37 focused tests** passed, including known-anomaly tilted
orbits, forward-time velocity recovery, exact epoch and source
mutations, frame and Sun translation, caps, corrupted receipts,
exclusive output and timeout rejection. The
[offline guard](experiments/0189/pytest-offline-guard.py.txt) full
suite had **6,284 passed and 494 skipped** in
122.00 s. Ruff, strict OpenSpec, links, diff and
frozen checkout checks passed.

## Consequences and revisit conditions

R5.57 still requires separate authorization bound to the tested
sources and a clean synchronized revision. No R5.57 attempt,
archived trajectory evaluation, SPICE query, force evaluation
or numerical integration was performed. Physical readiness and
the R4 continuity and target gates remain open.
