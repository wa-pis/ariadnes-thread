# 0231 — Preserve the saved-lineage dispatch rejected before analysis

Date: 2026-11-21 (Europe/Samara)
Decision status: accepted preservation of the first failed dispatch; no repair or retry
Implementation: qualified0230 code unchanged; R5.59s attempt consumed, numerical readback and independent numerical audit incomplete
Scope / milestone: M3, R5.59s under the unchanged ADR0229 contract
Base revision: clean `4b708bbb9d867a215b454daa1d8e4dbf248d38a3`, synchronized `dev`/`origin/dev`; no checkout change before the execution authorization record
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-diagnose-widening-through-saved-lineage-and-controlled-local-comparisons), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves [ADR0229](0229-design-saved-lineage-diagnosis.md), [ADR0230](0230-qualify-saved-lineage-reader.md), their sources and all historical evidence

## Context and constraints

The user explicitly authorized one R5.59s offline readback of the saved data and one
independent audit, with no SPICE, integration or R5.60. Before invocation, Git was
clean on the qualified revision, all six qualified source/test hashes and13 raw
input pins matched, both fixed output paths were absent, and no competing Ariadna
calculation was found. Raw hashing is metadata verification, not endpoint analysis.
An unrelated pytest process observed during the initial process check was not touched.

The [exclusive authorization record](experiments/0231-saved-dispatch/authorization.json)
was durably written before dispatch. The [driver text](experiments/0231-saved-dispatch/dispatch.py.txt)
then invoked unchanged0230 through pinned Conda Python3.12.14 with `-I -S -B`.
It contains no retry path. Shared30 s limits, cells, sources, inputs, formulas and
scientific gates were unchanged.

## Observed result

The sole producer command returned **3**, with exact stderr:

```text
R5.59r: worker arguments
```

The inherited error prefix is preserved. The dispatcher reports76,497,458 ns;
external elapsed time is90,031,584 ns (0.090031584 s), below30 s, without timeout.
No fixed result directory, attempt/report/receipt/completion or audit file exists.
The independent numerical verifier was not dispatched because no producer completion
or report exists. There is no numerical lineage result to audit.

The invocation is consumed despite the absence of result files. The R5.59s task
remains unchecked: its24-trace/1248-event analysis, alias/checkpoint/36-slot results,
resource inventories and independent numerical verification were not reached.
An early time limit pass is not successful readback qualification.

## Diagnosis and independent review

The retained command is expanded to four worker arguments:
`worker`, start time, invocation ID, `retained`. The worker's first check requires
`len(args) >= 5`, so it rejects that valid command shape before constructing its
Budget or calling its CLI. The artificial command adds a profile and output path,
giving six worker arguments; passing that path did not cover the four-argument
retained path. This is a test-coverage and dispatcher defect, not evidence about
the mathematical model or interval-widening cause.

A separate [read-only review](experiments/0231-independent-dispatch-review.json)
independently checked new dispatch metadata, source control flow, all six source
hashes and output absence. It agrees that the failure precedes worker authentication,
private analyzer loading and endpoint processing. The parent only constructs fixed
profile metadata from the contract; the external preflight hashes the retained raw
bytes without parsing numerical payloads.

Consequently no new endpoint descriptors, widths, local norm comparisons, scientific
helpers, old scientific auditor, SPICE, integration or R5.60 were reached. This is
an inference from the unchanged source and exact error boundary, **not** a completed
worker work-counter artifact. No runtime counters, completed source inventory or
verified numerical dispositions are invented. Independent failure review does not
substitute for the requested independent numerical verifier.

## Options considered

- Change the guard and rerun immediately: rejected in this stage. It would change the
  measured qualified code and exceed the one-attempt instruction.
- Treat absent outputs as an unused authorization: rejected; one dispatch occurred.
- Preserve first evidence and pause: selected under ADR0229's no-retry contract.
- Separately repair and qualify command-shape handling, then request a distinct
  execution decision: recommended next step, not performed by this record.

## Decision and rationale

Retain the [attempt metadata](experiments/0231-saved-dispatch/producer-attempt.json),
[external measurement](experiments/0231-saved-dispatch/producer-measurement.json),
[stdout](experiments/0231-saved-dispatch/producer.stdout),
[stderr](experiments/0231-saved-dispatch/producer.stderr) and
[summary](experiments/0231-saved-dispatch/dispatch-summary.json) without rewriting
history. Record the actual blocker before any repair. All0230 source bytes and
artificial qualification results remain historical; they do not prove admission
of the retained command.

Automation `ariadna-m3` remains PAUSED. A repair should test the exact retained and
audit worker command shapes using injected artificial dependencies, without starting
a retained analysis or importing scientific modules. A subsequent retained dispatch
requires qualified repair and a distinct explicit authorization, preserving this
consumed failure. Neither a formula change nor new trajectory work is needed to
address the observed argument-count defect.

## Evidence and verification

[The verification manifest](experiments/0231-verification.json) pins authorization,
logs, driver text and independent review, the unchanged qualified code, contract and
13 raw inputs. Finite JSON, links, exact error/control-flow facts, unchanged
historical/runtime/test/legacy bytes, diff and strict OpenSpec are checked.
No runtime or test code changed: reuse ADR0230's70 focused/6648 guarded full passes,
494 exclusions and Ruff result; pytest/Ruff and scientific calculations are not rerun.
This is a verified failure record, not an implementation completion or a science gate.

## Consequences and revisit conditions

The saved-lineage/36-slot question remains unanswered by R5.59s. There is no new
causal attribution, tighter interval, continuous exclusion, eligible command pair,
physical continuity, M3 completion or mission safety evidence. Revisit after a
separately instructed command-dispatch repair and artificial qualification. Do not
repeat a producer or numeric auditor in this stage.
