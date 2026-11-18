# 0225 — Qualify the retained-cell observation adapter on artificial archives

- Date: 2026-11-19 (Europe/Samara).
- Decision status: accepted artificial preparation under [ADR0224](0224-design-retained-cell-observations.md); no scientific contract changed.
- Implementation: complete for R5.59m. Artificial qualification passes; retained R5.59n is unexecuted and requires a separate explicit instruction.
- Scope / milestone: R5.59m, M3 diagnostic preparation for the fixed local Mars surrogate.
- Measured base revision: `a7fbb592f234bccacfbb76e9a84c557277dec037` plus only three new experiment modules and their new test file; exact tested bytes are in the [verification manifest](experiments/0225-verification.json). No checkout mutation during the full suite.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-observe-fixed-retained-phase-cells-without-rescanning), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559m-artificial-qualification-of-the-retained-adapter-2026-11-19), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. Historical sources, observations and [the ADR0224 contract](experiments/0224-retained-trace-contract.json) remain unchanged.

## Context and constraints

The user selected observations before changing the enclosure formula. ADR0224 fixes three saved leaves and their midpoint singletons, but the original ADR0223 entries intentionally reject retained scope. The necessary preparation is a separately scoped archive adapter and observer with the same mathematics and gates. This stage evaluates only the two already fixed artificial references. It does not explain the broad intervals on real operands.

## Options considered

- Relax the original artificial-only entry: rejected; it would erase a useful scope boundary and change historical source identities.
- Add separate hash-bound entries reusing the observation schema and unchanged mathematical modules: selected. Authenticate archived lineage and saved-point identities before any bound evaluation.
- Execute the retained matrix immediately: deferred under ADR0224 until artificial qualification and a separate user execution instruction.

## Decision and rationale

[The producer and saved-only verifier](experiments/0225-retained-trace.py), [observer](experiments/0225-bound-trace.py) and [point/summary adapter](experiments/0225-trace-checks.py) reuse the original Decimal96 mathematical functions. Sources, contract and references are pinned by byte hashes. Artificial scope accepts only the two exact previously qualified fixture reference hashes; retained scope has a separate fixed profile. Real operands cannot be relabeled as artificial. Source inspection/readback is permitted; no retained operand has been numerically evaluated here.

The new adapter checks nine source artifacts, canonical encoding, receipts, run/source/method identities, fixed row/phase/point identities and the six saved default-cell bound digests. It executes exactly the prescribed six domains × two signs × two paths, with one untraced control per trace. All 24 traced results match their own controls exactly. Six default finite-cell results additionally match fabricated archived records. Independent-path and singleton enclosures have no historical counterpart.

The saved-only verifier checks trace hierarchy, links, recorded values, parity and 24 sampled containment records, each with the 16 applicable oracle quantities. It performs zero bound calls, new traces, point/orbit constructions or conic solves. It does compute six new independent Decimal96 mass values. The producer computes six before evaluation and a fresh six-entry internal readback cache before serialization: its recorded 12 mass calls are observed work, not predicted future counters. Geometry/root parity remains 1 mm / 1 µm/s. Expected negative mass exclusion with clearance `not-reached` is preserved.

Named-stage widths, matching singleton widths, differences and available ratios use exact rational arithmetic with units. Zero singleton width yields an unavailable ratio. Context-dependent generic primitive fields remain raw ordered observations and are excluded from dimensional comparisons. Neither sampled containment nor these descriptive widths prove every internal enclosure, a causal contribution or a tighter formula.

One shared dispatcher clock covers imports through durable finalization. The worker has a watchdog and restricted input/output/method paths; native scientific loading and unrelated processes are denied. Calls, events, source bytes and evidence bytes are charged within the ADR0224 limits, including the 64 KiB audit reserve. Attempt/report/receipt/completion and audit are exclusive. Late failure invalidates only an invocation's own completion/audit marker and preserves partial evidence and foreign concurrent output.

## Evidence and verification

[The 38 focused tests](../../tests/test_retained_bound_trace.py) qualify both artificial witness and refusal cases, the full 24-row matrix, the six saved-default matches, source and method identity tampering, scope/reference/phase rejection, conditional stages, exact zero, counters, readback corruption, exclusive output, late failure and all work/time/byte caps. Spies reject forbidden historical scans, audits and point constructors outside the allowed bound arithmetic. Nine artificial source artifacts total 2,444,501 bytes for the witness and 2,318,982 for refusal; both exceed the 2,280,855-byte retained source volume while remaining within 4 MiB. Unselected archival rows and old audits are explicitly fabricated format fixtures; they are not independently recomputed historical scientific evidence.

The final isolated full-volume artificial witness invocation and separate saved-only audit both pass:

| Measurement | Producer | Separate auditor |
| --- | --- | --- |
| New signed bound calls | 48 | 0 |
| New direct points | 0 | 0 |
| Stage events emitted | 1,216 | 0 (1,216 saved events checked) |
| New oracle mass calls | 12 | 6 |
| External elapsed time including dispatch/finalization | 1.189270209 s | 0.239020125 s |
| Dispatcher elapsed time | 1.176174250 s | 0.225387416 s |

Authenticated producer input/method inventory is 2,667,616 bytes. The four producer artifacts and separate audit total 3,640,925 bytes, below the combined 4 MiB cap. The report contains 24 sampled containment records and six fabricated historical matches. The final status `observations-verified-attribution-unresolved` is an artificial adapter result, not a finding about retained operands. External timings cover final writes; pre-completion/pre-audit-write timestamps are separately identified in the manifest.

Preserve [attempt](experiments/0225-qualification/artificial-result/attempt.json), [report](experiments/0225-qualification/artificial-result/report.json), [receipt](experiments/0225-qualification/artificial-result/receipt.json), [completion](experiments/0225-qualification/artificial-result/completion.json) and [separate audit](experiments/0225-qualification/artificial-audit.json) byte-for-byte. The manifest lists all source/evidence identities and artificial input hashes. `build_profile` in the committed test file deterministically regenerates the fabricated archives in a fresh external scratch checkout. The isolated `artificial` and `audit-artificial` entries reproduce this preparation there; preserved evidence must not be overwritten. The actual retained output directory and audit file remain absent.

Final checks on the exact new source bytes: **38 focused tests pass in 10.44 s; 6,560 guarded full tests pass in 150.18 s, with 494 explicit exclusions**. Ruff and strict OpenSpec pass. The [retained guard](experiments/0225-qualification/offline-guard.txt), [skip inventory](experiments/0225-qualification/skipped-tests.txt) and [full log](experiments/0225-qualification/full-tests.txt) identify excluded native/SPICE, live UI and prohibited retained cases; native qualification is not claimed. An independent read-only review confirms the final ownership cleanup, auditor counters and source-chain checks. Historical files and `moon_to_mars.py` hashes remain unchanged. Documentation and evidence recording follow the passing suite; no full-suite repeat is needed for those prose/data additions.

No SPICE queries, real retained arithmetic, integration, R5.59n, old consumed study/audit replay, formula change or R5.60 occurred.

## Consequences and revisit conditions

The fixed retained diagnostic now has a qualified artificial adapter and bounded separate verifier. It is not yet a retained result. Automation `ariadna-m3` is **PAUSED** before R5.59n, as ADR0224 requires; the next necessary user action is a separate explicit instruction for that at-most-once retained diagnostic and saved-only audit. That future run entails 48 new bound calls and counted mass arithmetic, although it uses no SPICE or propagation. A failure would preserve the first evidence and require a new justified decision; no automatic retry or relaxed cap is authorized.

The internal cause of retained widening, the 40.085 m/s inter-node question, eligible commands, full-model continuity and mission safety remain unresolved. This stage does not extend M3 completion or authorize another scientific method.
