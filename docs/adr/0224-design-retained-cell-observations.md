# 0224 — Design bounded observations of retained phase cells

- Date: 2026-11-19 (Europe/Samara).
- Decision status: accepted diagnostic design and artificial preparation under the standing automation authorization; retained execution requires a separate instruction after qualification.
- Implementation: not started. This record verifies only the saved identities and design, not a retained numerical trace.
- Scope / milestone: R5.59l–n, M3 numerical diagnosis of the fixed local Mars surrogate.
- Base revision: `9dd3512d752931d3dda5ca3009c5f43b65bd0c94`, clean synchronized `dev` before design inspection.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-observe-fixed-retained-phase-cells-without-rescanning), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559l-design-retained-cell-observations-2026-11-19), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0221](0221-record-retained-inter-node-result.md), [ADR0222](0222-diagnose-saved-positive-bound-widths.md) and [ADR0223](0223-qualify-artificial-bound-observations.md) retain their evidence and original scopes.

## Context and constraints

The user selected designing a trace of several saved retained cells rather than changing the enclosure formula. All 64 saved positive-root lower mass bounds remain below the strict exclusion threshold. Artificial tracing is qualified, but no retained intermediate observations exist. The numerical question is: **which recorded stages carry width on three fixed terminal cells, and how do those widths compare with singleton evaluations at their already saved midpoints?** This is a diagnostic of the unchanged surrogate, not a new physical propagation or proof of feasibility.

Only JSON parsing, byte hashes and source inspection were performed for this design. No numerical worksheet, interval, conic or point constructor, old scientific audit, SPICE or integration was invoked.

## Options considered

- Repeat the entire local study or increase its subdivision depth: rejected; the R5.59i attempt is consumed and its inconclusive result remains immutable.
- Trace three existing leaves only: smaller, but lacks a fixed comparison for residual interval arithmetic at one phase.
- Trace those leaves and their three saved-midpoint singletons: selected. It uses the same 48 total signed calls as the qualified artificial matrix and introduces no new phase samples or adaptive tree.
- Change the proof formula before observing the actual operands: deferred. Widths alone do not establish a correct tighter enclosure.

## Decision and rationale

### Fixed evidence and domain

[The machine-readable contract](experiments/0224-retained-trace-contract.json) pins nine existing artifacts, 2,280,855 bytes in total: the ADR0215 attempt/report/receipt and ADR0217 saved audit, plus the ADR0221 attempt/report/receipt/completion and independent audit. The producer and auditor must authenticate all hashes, receipt chains, run/source/method identities and the frozen reference hash `6b845f74881f658d2eeea28bfdde43c9190a283da5bb166644bb845c4f847c5b`. Candidate, epochs, endpoint operands, spacecraft, model identity, constants, roots, mass and guard thresholds remain unchanged. The inherited full-model label is provenance; these interval expressions still describe only the archived local analytical surrogate.

Select rows by **both** zero-based index and exact canonical fields. No ranking or numerical search chooses the cells:

| Saved R5.59i row | Existing closed cell (degrees) | Saved midpoint / singleton (degrees) |
| --- | --- | --- |
| 62 | `[150,4801/32]` | `9601/64` |
| 94 | `[151,4833/32]` | `9665/64` |
| 125 | `[4863/32,152]` | `9727/64` |

All are depth-5 unresolved leaves of width 1/32°. Each point record is already complete in that same row. The six fixed domains are the three cells and their midpoint singletons; a singleton is a diagnostic control, not a new subdivision or coverage certificate. Check positive then negative signs and default then independent arithmetic for each domain, in fixed row order with cell before singleton. This produces **24 traces and 24 untraced controls**.

For each traced record require exact canonical-byte equality with its own untraced result. The six default-path, finite-cell results must additionally equal the six authenticated saved branch records. Independent-path and singleton interval records were not previously saved: compare them only with their own controls and applicable oracle quantities, never claim historical parity for them. The old independent audit embeds the producer's bound fields, not separately saved independent enclosures.

### Observation and independent checks

Retain the qualified observation schema: ordered call/return hierarchy, finite canonical endpoints, exact input/return links, norm, mass, duration and designated binary64-conversion fields, conditional stages and explicit failures. Pin the unchanged mathematical sources and Decimal96 context. Do not modify historical files, monkeypatch their formulas, or relabel retained reference values as artificial.

Both ADR0223 trace and containment entries intentionally reject retained scope. R5.59m must implement a separate hash-bound retained entry and saved-point adapter, reuse their observation/validation scheme where practical, and qualify the new boundary on fabricated archival evidence first. Preserve the existing artificial-only entry's rejection behavior. Do not call historical `_scan`, `_saved`, `verify_result`, anchor replay, phase/orbit constructors or point-root solvers to obtain inputs or to audit this diagnostic.

Use only the **three saved midpoint points**, matched by row and point hash; construct zero new points. Check both saved signed roots with the existing readback gates and the corresponding Decimal96 quantities. For each of the 24 traces, compare the same 16 applicable oracle quantities as ADR0223 (ellipse state/anomaly, impulse norms, masses/durations and designated duration conversions). Retain the existing 1 mm / 1 µm/s geometry/root parity gates; singleton oracle containment does not require containing separately rounded binary64 geometry. A negative branch may legitimately finish at mass exclusion with clearance `not-reached`; validate that disposition instead of inventing a clearance value.

Mass values are not present as a complete oracle cache in the saved point rows. Compute at most six unique `oracle.mass` results per checking pass: three existing points × two signs, cached across both paths and both domain types. Explicitly count this new Decimal96 exponential arithmetic. Allow at most 12 such evaluations in the producer including one fresh six-entry internal readback, and at most six in the separate saved-only auditor. These are not zero-arithmetic checks. The 48 permitted bound calls themselves reconstruct interval signed-root geometry; there are zero point-root constructions outside those calls.

The separate auditor reads the pinned inputs and saved new evidence, validates the hash chain, exact matrix, six historical controls, trace structure, recorded numeric links and sampled containment, and recomputes descriptive summaries. It performs **zero new bound calls, traces, point/orbit constructions or signed conic solves**. Its independent mass arithmetic is counted as above. Do not rerun the already completed R5.59i scientific audit. Audit success verifies these observations and sampled checks; it is not a new independent proof that every internal enclosure or the physical model is correct.

### Width interpretation and completion

Record exact rational `hi−lo` for each selected scalar/component by converting the saved canonical decimal endpoints to fractions. Preserve exact endpoints as primary evidence; decimal displays are explicitly descriptive. Tag units by stage: ellipse position and clearance in m, velocities and final impulse norm in m/s, unit directions/eccentricity vectors dimensionless, angular momentum/root in m²/s, squared impulse norm in m²/s², mass in kg and duration/conversion in s. Other recorded intermediates require their own dimensional tags; never rank widths across unlike quantities.

Compare each stage with the matching singleton by cell, sign, path, call position and field. Report cell width, singleton width and their exact difference; a zero denominator makes a width ratio unavailable, not infinite or erroneous. Keep component-wise values and explicit non-reached/error states. Report where widths occur and which corresponding quantities differ; do not infer causal error contributions, a global dominant source, physical error or a tighter proof from three sampled cases. An unresolved attribution is a valid diagnostic outcome. A formula change needs a separate design and verification.

### Budgets, evidence and authorization

| Resource | Fixed plan / hard limit |
| --- | --- |
| Producer shared wall time | 30 s including dispatch/imports, input/method authentication, controls, trace, internal readback and durable finalization |
| Separate saved-only audit | 30 s including its final evidence flush |
| Interval signed-bound calls | Exactly 48 planned; hard cap 48, all controls included; no hidden warm-up/replay |
| New direct phase / point-root constructions | 0 outside the interval calls |
| Independent mass arithmetic | Producer at most 12, separate auditor at most 6; charge before evaluation |
| Stage entries | At most 8,192 across all 24 traces |
| Authenticated source inventory | At most 4 MiB per process, including this contract and method bytes; nine historical files are 2,280,855 bytes |
| New evidence inventory | At most 4 MiB for the producer artifacts plus separate audit; bound reads, event emission, serialization and writes |
| Native/SPICE, force, integration, R5.60 | 0 |

The same-sized artificial matrix in ADR0223 used 48 calls, 1,232 entries, 2,092,809 output bytes and a 1.163 s external producer time. Those measurements justify reusing the limits as an initial envelope, not a guarantee for retained operands. R5.59m must exercise the full new matrix, full-volume fabricated archives, finalization and every exhausted cap before qualification. No cap increase follows from a failure.

Use a dedicated fixed output directory, `docs/adr/experiments/0224-retained-trace-result`, with exclusive attempt/report/receipt/completion files, and a separately exclusive `0224-retained-trace-audit.json`. Include contract/method/source/point/old-bound digests, exact counters, stage summaries, null commands and separate statuses. The 4 MiB combined evidence envelope reserves 64 KiB for the audit, rather than consuming the full envelope in the producer. Producer completion is created only after all applicable checks and is removed on late write/flush/readback failure; preserve partial evidence and never overwrite an existing attempt. A final deadline check and externally measured elapsed time must cover finalization, not merely a pre-write timestamp. A single dispatcher owns the 30 s producer clock and worker watchdog; do not reset it in child processes.

R5.59l is this design. R5.59m is reversible artificial-only implementation and qualification, permitted under the user's standing automatic-progression instruction. **R5.59n remains a separately authorized, at-most-once retained diagnostic after R5.59m passes.** Its new interval evaluations are explicitly narrower than a replay of the old study; they must not be described as computation-free. Before any R5.59n dispatch, automation must pause for the user's execution decision. A failure or inconclusive result never authorizes a retry, new cell, deeper proof tree, new point, changed formula/threshold, SPICE, integration or R5.60.

## Evidence and verification

Design inspection confirms the nine file hashes and byte counts, reference hash, row/cell/midpoint identities, three point hashes and six historical bound hashes. An independent read-only source/schema review confirms that independent enclosures were not separately retained and that both existing artificial entries reject retained operands. No scientific functions were called.

Documentation verification covers new local links, canonical finite contract JSON, exact recorded identities, unchanged runtime/tests/environment/legacy and historical artifacts, clean diff and strict OpenSpec. Reuse ADR0223's 27 focused / 6,522 guarded full passes with 494 exclusions and Ruff result on unchanged code; no pytest or numerical trace was repeated. Implementation, full-volume qualification and retained execution remain unperformed.

## Consequences and revisit conditions

The next observation has a fixed question, small reproducible matrix, unchanged result controls and an explicit distinction between new interval arithmetic and saved-only audit. It can identify where width is represented for these operands without spending another trajectory solve. It may still leave causal attribution unresolved; preserve that finding instead of turning it into a new feasibility claim. R5.59c/f/i remain consumed, the 40.085 m/s question and R5.60 admission remain open, and no full-force trajectory or mission safety is qualified.
