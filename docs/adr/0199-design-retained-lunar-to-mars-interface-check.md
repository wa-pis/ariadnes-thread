# 0199 — Design a saved-data check of the lunar-to-Mars interface

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted for a bounded research design.
- Implementation: R5.52 design complete; worksheet and execution pending.
- Verification: saved input digests, record selectors and epoch inventory checked; no continuity residual computed.
- Scope: archived model B departure candidate `d0001-t0035` and the existing Mars-bound references.
- Base revision: `75b8fce2aa53c9ef85cc702212c9e2b39f0834e6`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-check-retained-lunar-to-mars-interface-readiness), [design](../../openspec/changes/refine-physical-trajectory/design.md#r552-design-the-retained-lunar-to-mars-interface-check-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none; [ADR0135](0135-fixed-orbit-boundary-contract.md) remains the mission interface.

## Context and constraints

[ADR0198](0198-far-lunar-range-marker-bracketed.md) shows an outward
crossing of 18,374 km in a restricted model B coast. The radius and
its crossing bracket do not define where another trajectory begins.
The question here is whether the verified archive can supply an
unambiguous outgoing state and whether the saved Mars-bound results
contain a compatible, independently produced incoming state at the
same epoch.

| Retained source | What it can establish | Limit for this check |
| --- | --- | --- |
| [R1/R2](0129-reference-coast-verification-passes.md) | Independent numerical verification of 121 ideal Sun-only samples for the same candidate | First two epochs are 978995455.2304223 and 979205237.0486041 TDB s. Every R5.51 epoch lies strictly between them. |
| [0079](experiments/0079-research-reference.json), [0082](experiments/0082-identical-start-coast.json), [0083](experiments/0083-coast-step-study.json), [0098](experiments/0098-central-correction-study.json) | Full-model research boundary/endpoint records; 0083 also has mesh summaries and digests | Shared nominal cutoff at 978998315.9635216 TDB s is 650 s before R5.51 starts. These reports retain no interior coast state in the R5.51 interval. The common cutoff is shared ancestry, not an independent comparison at the later epoch. |
| [R4 endpoint audit](0136-retained-boundaries-pass-arithmetic.md) and [D14 target](0105-local-finite-burn-contract.md) | Fixed arrival-cutoff target and arithmetic; a separate lunar two-body comparison at the same radius | The arrival target is not a coast start; D14's local target has different time and model semantics and is not a Mars-bound interface. |

The R5.51 interval is 978998965.9635216–979014965.9635216 TDB s.
No candidate ID, matching radius, epoch coverage between two saved
samples, copied state or stored mesh digest can substitute for an
independent state at the comparison epoch.

## Options considered

- Join at the bracket or interpolate between saved ideal nodes:
  neither supplies an authenticated pair at a common epoch.
- Replay the transfer, retarget its start or evaluate the R2 analytic
  coast at a new epoch: each creates new trajectory states and would
  require a separate contract.
- Check the saved endpoint packet and the retained receiving-side
  inventory as separate results: selected. The packet can be
  authenticated even when the two-sided comparison is unavailable.

## Decision and rationale

### Outgoing packet

Fix the **terminal common sample of tighter RK4**, +16,000 s at
979014965.9635216 TDB s, for the diagnostic packet. It is a saved
common epoch with raw and audited operands on both grids. It is
also the furthest common sample, without selecting a point based on
a comparison residual. This is a candidate seed for later study
and does not set a new M3 mission boundary.

Read the pins and exact selectors in the
[design input inventory](experiments/0199-design-inputs.json). Bind
both R5.51 manifests, attempt and receipt chains, passing parent
deadlines, matching audit-to-study digests and the clean measured
revision through [ADR0198's verification](experiments/0198-verification.json).
Check compressed and uncompressed digests, member headers, lengths
and row counts of the five selected members. Only the selected
members are read and verified again. The original R5.51 audited
full archive is preserved.

Require bit-for-bit epoch and spacecraft six-state agreement across
tighter native raw index 32,000, common sample 320 and the two
audited direction rows at those indices. Use the retained Moon
operands separately: the common row binds to node 320, the mesh
row to guard group 32,001; do not make equality across ephemeris
paths a new gate. Check the ordered native guard group and the
Sun/Moon/Earth model, SSB/J2000, SI, and TDB seconds since J2000.
Require the same stored mass word, 1351.7475727997967 kg, in the
native header, R5.51 inputs/result and the original simulated
cutoff. It is constant mass metadata, not an integrated seventh
component or a fuel-reserve result.

Use exact rational squared-radius and dot-product signs and an
independent Decimal80 metric calculation from the saved binary64
operands. Both audited endpoint records must have matching signs
and match radius and signed radial speed within the existing
1e-6 m and 1e-9 m/s arithmetic gates. This checks identity and
the endpoint interpretation, not forces or a new trajectory.

### Receiving side and verdicts

Check exact binary64 epoch words in all 121 R1/R2 nodes and hash-bound
timed boundaries/endpoints at the pinned record paths in the
full-model reports. Bind R1
to its independent R2 audit and preserve R4's arrival target record
as a target only. Compare original labels, model, frame, units, TDB
semantics, provenance and mass availability before admitting a
receiving state. Record the bracketing ideal nodes and rejection
reasons by source. Do not pass the source packet back as independent
receiving evidence, convert a diagnostic impulse into a finite burn,
use a nearest node, interpolate, shift time or estimate a corrective
impulse from noncoeval states.

The worksheet has three separate results:

- Source: `source-state-authenticated` only when all source checks pass.
- Ideal comparison: `ideal-reference-coepoch-unavailable` for the
  pinned inventory; there are zero exact coepochs over R5.51.
- Physical interface: `physical-join-not-established` when no
  compatible independent receiver is retained. Position, velocity,
  epoch-continuity and mass residuals are null, not zero. This is a
  valid completed inventory, not a failed trajectory or a fit result.

Missing or corrupt inputs, inconsistent operands and exceeded
limits instead yield `invalid-evidence`; no affirmative source
or interface verdict is issued. Report the first failing check.

A future physical test requires a distinct contract and an independent
Mars-directed state and mass at the same exact physical interface,
consistent dynamics and unchanged target/phase/event semantics.
That contract would report signed incoming-minus-outgoing position
and velocity components, their Euclidean norms, time and mass
differences using the existing R4 join ceilings of 1e-6 s,
0.001 m, 1e-6 m/s and 1e-9 kg. A force-model change cannot be
justified by state equality. No such residual or closure gate is
evaluated by this saved-data check. Arrival targeting and capture
remain separate.

### Bounded offline work

After preparation, one separately requested stdlib-only worksheet
run has a shared **15 s wall limit** including reads, integrity
checks, computation, exclusive evidence write, flush and receipt.
Allow five named members, at most 16 MiB raw per shard, 80 MiB raw
and 25 MiB gzip payload combined, and at most 218,972 lines. Include
at most 1 MiB of archive metadata/receipts, 2 MiB of compact input
JSON and 128 KiB of report and receipt. Read at most one bounded
shard at a time. Set a parent deadline and check limits before
and after work and finalization. Missing or untimely evidence
cannot certify a source packet; keep the first safe record or
bound failure receipt without retry. All budgets for SPICE, kernel
access, force evaluations, propagation and new trajectory states
are zero.

These ceilings come from the selected inventory (83,885,015 raw
bytes, 25,613,216 gzip payload bytes and 218,972 lines), not the
653.7 MB raw R5.51 archive or its solver budget. The wall limit
allows bounded hashing, decompression and a small receipt-bound
output. Artificial fixtures must qualify that limit at the
selected-member workload before running against the retained
operands; elapsed time for this design's metadata inspection is
not runtime qualification.

## Consequences and revisit conditions

A completed saved-data inventory can qualify the outgoing artifact
for reuse and identify the missing receiving evidence. It cannot
establish a connection to a Mars trajectory, a physical departure
boundary, capture, continuous safety or strict M3. Preserve the
existing target and model contracts. Any later calculation of
coepoch transfer states or controls needs separate design and
authorization.

## Evidence and verification

Checked ten pinned input SHA256 values, both R5.51 phase manifests
and the linked receipts, both hashes and row selectors of five
shards, stored terminal epoch and mass labels, exact cutoff mass words, and
the epoch inventories of the 121 ideal nodes and pinned boundaries. Verified local links,
JSON, diff and strict OpenSpec. This stage ran no worksheet,
continuity or force arithmetic, SPICE, propagation or runtime
regression. All scientific code and historical records are unchanged.
