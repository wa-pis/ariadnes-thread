# 0222 — Diagnose the saved positive bound widths

- Date: 2026-11-18 (Europe/Samara).
- Decision status: accepted saved-only diagnosis and artificial tracing plan; no changed enclosure formula or retained invocation.
- Implementation: diagnosis completed; artificial stage tracer not implemented or qualified.
- Scope: R5.59j; read-only scalar and source inspection following [ADR0221](0221-record-retained-inter-node-result.md).
- Measured revision: `f1ae7146a20232f3cf3cdad0348cc62ca5ff83fd`, clean synchronized `dev` before inspection.
- Related OpenSpec: [scenario](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-diagnose-unresolved-enclosures-without-replay), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559j-saved-bound-diagnosis-and-r559k-artificial-tracing-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. The [ADR0218](0218-design-inter-node-mars-phase-check.md) procedure, [ADR0221](0221-record-retained-inter-node-result.md) inconclusive result and consumed attempts retain their scopes.

## Context and constraints

The authorized next step was to inspect the saved positive-root bounds without rerunning the local study, its audit or any scientific enclosure. A narrower sampling interval is not itself a proof. Identify the recorded failed exclusion tests, then distinguish observations from hypotheses about the unrecorded internal arithmetic.

The diagnosis used five authenticated ADR0221 artifacts, 1,219,666 bytes, with a 15 s/4 MiB read budget. It parsed existing scalar fields and performed exact rational comparisons and descriptive Decimal subtraction only. It did not import or call the numerical worksheets, interval/conic constructors or scientific backends.

## Observations and inference limits

The [saved summary](experiments/0222-saved-bound-summary.json) preserves exact hashes, rational ledgers, sample cells and descriptive ranges. All 64 terminal cells have width 1/32° and partition [150°, 152°]. Every positive-root record contains the speed, mass/duration and clearance fields and no arithmetic-error detail.

| Saved positive-root terminal quantity | Recorded range or decision |
| --- | --- |
| Exact consumed-mass lower bound, decimal display | 1,499.101717–1,499.262399 kg |
| Strict exclusion threshold | Lower bound must exceed 1,500 kg; none does |
| Arrival impulse-norm enclosure width | 94.114771–98.405627 m/s |
| Clearance upper bound | 8,187,163.791–8,282,685.131 m |
| Guard exclusion threshold | Upper bound must be below 0.001 m; none is |
| Terminal midpoint excess over recorded ideal budget | 40.006176–41.246023 m/s |

The mass quantities are **lower bounds**, not actual propellant consumption. Falling below 1,500 kg does not establish feasibility. The clearance quantities are **upper bounds**, not actual clearance. They cannot prove a guard failure.

[The source](experiments/0219-phase-bounds.py) computes the arrival impulse norm before mapping it through the mass/duration bounds. The saved norm widths therefore show uncertainty already upstream of the exponential, binary64-duration conversion and comparison allowance. They do not prove that upstream width is the sole or dominant cause of the failed ledger exclusion. The full saved field inventory shows that the positive path reached both mass and clearance tests, rather than returning a recorded alignment, denominator or root-sign exception.

Natural interval expressions reuse vectors and normalizations without preserving all correlations. Ellipse/trigonometric recurrence, normalized cross products, signed-root reconstruction, impulse norms and the coast/final-mass difference are possible contributors. The report did not save their intermediate widths, so no particular operation is identified as the dominant source. An artificial example may diagnose its own widening but cannot retrospectively prove attribution for these retained operands.

The prior audit recomputed independent bounds but retained no per-sign independent enclosure fields for unresolved rows. The saved negative `mass` annotations are not new independent branch certificates. This diagnosis does not upgrade them, certify any leaf or change `inconclusive`.

## Options considered

- Increase depth or rerun the retained study: would change the consumed contract and remains excluded.
- Choose a tighter formula from the final scalar ranges alone: premature; the recorded intermediates do not support attribution.
- Instrument the existing functions on fabricated fixtures and compare traced/untraced outputs: selected as the smallest next diagnostic within the current artificial-only authorization.

## Decision and bounded next step

Prepare R5.59k as an artificial-only observational tracer. Use the existing `witness` and `refusal` fixtures from [the pinned point module](experiments/0219-phase-points.py), whose candidate and scope are explicitly artificial. Never substitute retained operands into a relabeled fixture. Do not modify the historical method files, formulas, constants, phase interval, scientific tolerances or mass/guard rules.

Trace both signed roots and both existing arithmetic paths on the fabricated parent cell [151°,152°], its child [151°,151+1/32°], and that child's singleton midpoint. Record ordered interval endpoints at ellipse state, unit-vector/cross-product and root reconstruction, impulse norm, mass, comparison durations and binary64 conversion. Explicitly identify stages not reached after an early disposition. Clone or wrap isolated module namespaces; tracing must leave the original methods and outputs unchanged.

Qualification must compare the final traced and untraced bound records byte-for-byte for every fabricated case/path/sign/cell, preserve canonical finite endpoints, and show that matching Decimal96 independent-oracle point quantities and their designated binary64 comparison-duration conversions lie within the corresponding recorded enclosures. Retain the existing binary64/oracle parity gates; a singleton oracle enclosure need not contain a separately rounded binary64 geometry value. Include strict mass equality, a branch/guard transition, early failure, mutated trace, missing stage, scope/pin rejection and exhausted resource limits. A trace is diagnostic evidence, not an exclusion certificate or a proposed scientific replacement.

Charge fixture creation, tracing, untraced controls, readback and exclusive durable output to one 30 s budget. Cap this unit at 64 signed bound evaluations including controls, 32 direct phase evaluations including fixture anchors, 8,192 emitted stage entries, 4 MiB pinned artificial input and 4 MiB new evidence. Fail inconclusive or invalid on a missing/malformed stage or exhausted limit; do not enlarge a cap to obtain a successful result. Verify focused and guarded full pytest, Ruff, strict OpenSpec and immutable source hashes before declaring the tracer qualified.

## Evidence and verification

The saved-only inspection completed in 0.017257 s within its declared limits. Exact rational comparisons, the two-degree terminal inventory, report/audit/completion chain and field-presence assertions passed. A separate read-only source/schema review agreed with the attribution limits. Documentation checks cover facts, links, finite JSON, byte hashes, immutable historical/runtime files, diff and strict OpenSpec.

No conic solve, interval evaluation, phase construction, new audit replay, SPICE query, force evaluation, integration, retained attempt or R5.60 occurred. Runtime sources and tests remain unchanged; ADR0220's 9 focused/6,495 guarded full passes with 494 exclusions and Ruff result are reused, with no repeated pytest.

## Consequences and revisit conditions

Saved evidence now localizes which exclusion tests remain unproved, while the internal cause stays unestablished. R5.59k can proceed on artificial data under the recurring authorization. A changed proof formula, deeper retained subdivision or any real-data instrumented invocation needs a separately reviewed contract and the user's decision; none is authorized here. Physical continuity, the 40.085 m/s inter-node question and M3 remain open.
