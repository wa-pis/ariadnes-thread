# 0202 — Design an independent Mars receiving state at lunar exit

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted for bounded research design.
- Implementation: R5.55 design complete; no receiver or comparison has been computed.
- Scope: fixed epoch and candidate `d0001-t0035`; ideal diagnostic and physical readiness are separate.
- Base revision: `4af2d2988bac4218bc271db1c74f558a3e5239ae`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-design-an-independent-mars-receiving-state), [design](../../openspec/changes/refine-physical-trajectory/design.md#r555-design-the-coepoch-mars-receiving-state-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0135](0135-fixed-orbit-boundary-contract.md) remains the R4 mission interface.

## Context and constraints

[ADR0201](0201-authenticate-lunar-exit-record-receiving-gap.md) authenticated
the R5.51 tighter RK4 terminal state at **979014965.9635216 TDB s since J2000**
(binary64 `0x1.d2d4a9afb54adp+29`). This is the saved +16,000 s
coast checkpoint, distinct from the 18,374 km crossing and from either
R4 burn interface. The state uses SI, SSB/J2000 and model B (Sun, Moon and
Earth point masses); its mass of 1351.7475727997967 kg is coast metadata.
R5.54 found no compatible archived receiver at this epoch. The R5.51
study does retain a geometric Sun six-state at that exact checkpoint,
which is sufficient for a limited ideal comparison in SSB/J2000.

## Options considered

- Interpolate the sparse ideal samples or seed the receiver with the R5.51
  spacecraft state. Interpolation would not reproduce the specified
  dynamics, and seeding with the outgoing state would impose the match.
- Evaluate the fixed R1 ideal conic at the checkpoint, working backward
  from its retained end and checking from its departure seed. This is
  small and can use saved inputs, but contains no capture burn or mass.
- Generate a physical receiver from the fixed R4 Mars orbit and a frozen
  admissible arrival command. This addresses an independent physical match,
  but requires explicit command, mass, model and numerical prerequisites.

## Decision and rationale

### One ideal coepoch diagnostic

Use R1 run 1 (`runs[0]`), state index 120 before the ideal arrival impulse,
and subtract R2 point 120's coepoch Sun position and velocity. Use the
**spacecraft** velocity, not the Mars body velocity. Apply the existing
R2 ellipse method in Sun-relative J2000 with solar GM
`1.327124400420322e20 m^3/s^2`. For this time-reversible Sun-only problem,
derive the ellipse from the terminal position and negated terminal
velocity, advance it by `t_final - t_check`, and negate the resulting
velocity to restore the forward-time convention. This allows reuse of
the frozen R2 arithmetic, whose elapsed-time interface is nonnegative.

Cross-check at the same checkpoint from R2's original independently
derived departure seed and `t_check - t_departure`, without fitting either
seed. These are separate endpoint constructions with shared analytic
arithmetic, not two independent integrators. Require the unchanged R2
ellipse-domain, basis, energy/angular-momentum and root gates. Require
the two reconstructions to agree in both Sun-relative and SSB states to
**1 m and 1e-6 m/s** in Euclidean norm. Translate each with the same
stored checkpoint Sun position **and** velocity. Bind exact epoch
words; no nearest node, interpolation, time shift or new ephemeris.

The Sun selector is [ADR0199's frozen inventory](experiments/0199-design-inputs.json),
study `00000.shard`, manifest index 0, zero-based row 337, type `node`,
index 320. Bind the study manifest and parent receipt; verify member
header, 42,862 rows, both digests, and 16,777,139 raw / 5,176,745 gzip
payload bytes. Require `hi_tdb_s` and the unique Sun request/response
epoch to match the checkpoint word; require Sun/SSB/J2000/NONE on both
and a finite `bodies.Sun.state_si` six-vector. This is a shared archived
translation input, not independent ephemeris validation. Bind the
ordered kernel inventory from identity row 16 in the same shard to
the matching R2 inventory; check saved metadata without opening kernels.

After freezing the ideal packet, disclose signed ideal-minus-B position
and velocity vectors and norms as **model differences**, with no pass
threshold against B. Retain separate ideal method-consistency gates.
The ideal mass is null and the physical verdict remains
`physical-join-not-established` with all four physical residuals null.
A small model difference would not establish physical continuity; a
large one would not by itself identify a failing force or integrator.

#### Inputs and budget

| Fixed input | SHA-256 |
| --- | --- |
| [R1 reference](experiments/0119-m2-reference.json) | `3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0` |
| [R2 reference](experiments/0129-reference-coast.json) | `e2c5d077285fe0218d1c93f3000f319048006eb55477d680f83041f6c70ce9d7` |
| [R2 independent audit](experiments/0129-reference-coast-audit.json) | `41a8d4434db26752e3cae96e965480710f36eabbff885ed957b2766e957456c7` |
| [R2 arithmetic source](experiments/0128-reference-coast.py) | `027d0b4e45f9ebd941249e427963e365fd7205f9594a96365a587eb0e8cd7e81` |
| [R5.51 design pins](experiments/0199-design-inputs.json) | `5afd7e263adf7c7aa03ee902a4e7adb85360c4cadd172244a8c8b26d6d8998df` |
| [R5.54 certificate](experiments/0201-verification.json) | `b4a760bd2b598d682b04969fb3b6e3f60cce5f738b3d6d655bb0a22207a25cd6` |
| [R4 fixed target and ignition](experiments/0098-central-correction-study.json) | `b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057` |

Use R2's retained audit result to bind the two seeds and the original
candidate; do not replay R2. Bind R5.54's authenticated outgoing packet
through its certificate and report digest. Later preparation will
qualify the actual metadata and single-shard workload on artificial
fixtures. After preparation and a separate execution request, allow
one isolated stdlib process with at most two analytic evaluations at
one new epoch, 64 root updates each, one member of at most 16 MiB raw
and 5 MiB gzip payload, 42,862 rows, 2 MiB pinned compact inputs,
1 MiB archive metadata/receipts and 128 KiB new output. Use the previous
15 s parent deadline through finalization: this reads one of R5.54's
five shards and solves two scalar roots. The budget is a ceiling to
qualify in preparation, not a measured runtime. Zero SPICE, kernel
access, force callbacks, numerical integrations, searches or fit
attempts. Preserve first complete or partial evidence with exclusive
paths and bound receipts; stop on tampering, a gate failure or overrun,
without retry or replacing an input.

### Physical checkpoint and true R4 interfaces

Use the retained `science.runs[0].run.target_state` as the **desired**
Mars arrival cutoff at 1004169273.4122404 TDB s. Keep R4's original
scenario, initial orbit and mass, target orbit and phase, and exact
departure cutoff and arrival ignition events. Before any physical run,
freeze one independently justified, admissible pair of departure and
arrival commands and derive the target-end mass from their sequential
propellant use and the fixed initial mass. Do not adopt a failed trial,
an ideal impulse, or fit commands to the R5.51 state or mass. This mass
is specified/budgeted from commands; agreement would check mass
bookkeeping, not independently measure propellant.

From the fixed cutoff state and target-end mass, integrate one arrival
burn backward to exact arrival ignition and one coast backward to the
checkpoint. Use the unchanged M3 production dynamics in both directions:
the physical-time TNW law and negative mass derivative do not change
sign for decreasing integration time. At ignition switch only thrust
according to the frozen schedule. Confirm the checkpoint is strictly
inside the coast. Freeze the receiving packet before reading outgoing
comparison operands. Matching requires a separately produced outgoing
state at the checkpoint from the fixed lunar initial state and planned
departure command under the **same production model**. The archived
model B state lacks that force inventory and is not this operand.
The checkpoint is a place to test two arcs, not a new burn interface.

For a compatible pair, require exact checkpoint, frame, model,
timing and mass provenance before evaluating incoming-minus-outgoing
six components, Euclidean norms, epoch difference and mass difference.
Keep R4 ceilings of **1e-6 s, 0.001 m, 1e-6 m/s, 1e-9 kg** and
separate target closure of **1000 m and 0.01 m/s** from a forward
check under the frozen command without resetting the state at the
checkpoint. Freeze independent dynamical validation and an error
budget that can resolve the join gates; existing M3 profile agreement
at coarser scales is insufficient. If the error allowance puts the whole residual interval within a
gate, it can pass; if the interval is wholly above the gate, it fails.
An interval straddling the gate is inconclusive. Require nonnegative
error allowances justified separately from the observed mismatch. If there
is no compatible pair, leave physical residuals null.

Commands, native coverage, force resources, reference solver/error
assessment and a qualified wall/RHS/query/output budget for the
months-long backward coast are not yet established. A later contract
must qualify those under synthetic inputs, bound at most two reverse
segments per receiver path and one fixed command with zero optimizer
trials, and separately authorize execution. The short model B budgets
do not transfer to this problem.

## Consequences and revisit conditions

The next bounded implementation can prepare an ideal comparison using
synthetic evidence. Physical execution remains unavailable until the
named prerequisites are resolved and the result could answer the R4
question. A future numerical match does not by itself qualify arrival,
capture, reserve, safety or strict M3. R5.51 and R5.54 remain unchanged.

## Evidence and verification

Verified source digests, the saved Sun record selector and kernel
metadata, fixed epoch words, archived candidate and endpoint roles,
links, diff and strict
OpenSpec. The design ran no worksheet, SPICE query, force evaluation,
propagation, new trajectory-state or residual calculation. Runtime
code is unchanged; the runtime suite was not rerun.
