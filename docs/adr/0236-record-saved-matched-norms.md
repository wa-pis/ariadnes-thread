# 0236 — Preserve the matched-norm run rejected at source metadata

Date: 2026-11-21 (Europe/Samara)
Decision status: accepted
Implementation: qualified0235 code unchanged; R5.59x attempt consumed, saved comparison and numerical audit incomplete
Verification: first failure metadata and source boundary independently reviewed; no numerical verification result
Scope / milestone: M3, R5.59x under the unchanged ADR0234 contract
Base revision: clean `063f7a4a0bef5fbc52b2062c8dc415f1ae7a6037`, synchronized `dev`/`origin/dev`
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-compare-source-defined-norm-squared-methods-on-identical-saved-boxes), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves [ADR0234](0234-design-matched-input-norm-comparison.md), [ADR0235](0235-qualify-matched-input-norms.md) and all historical evidence

## Context and constraints

The user explicitly authorized one offline72-box comparison and one independent
audit, without SPICE, integration or R5.60. Preflight found clean qualified code,
all8 measured source/test hashes and13 original raw pins matching, both immutable
contracts unchanged, no competing Ariadna calculation and absent fixed0234 outputs.
The full real source inventory is3,918,908 B, below4 MiB. Historical scientific
source files are inspected as text, never imported.

The exclusive [authorization](experiments/0236-saved-dispatch/authorization.json)
and [driver text](experiments/0236-saved-dispatch/dispatch.py.txt) preserve the
instruction, exact revision, Python3.12.14, raw pins and fixed caps before dispatch.
One unchanged0235 `retained` command ran through pinned Conda Python with `-I -S -B`,
without an artificial bootstrap, profile injection, source replacement or retry.

## Observed result and failure boundary

The producer returned **3**, without timeout, with exact stderr:

```text
matched norm: source/scope identity
```

External elapsed time was219,416,833 ns (0.219416833 s); the dispatcher reported
206,261,750 ns (0.206261750 s). Authentication and source-AST checks completed,
then the worker durably wrote [attempt.json](experiments/0234-matched-norm-result/attempt.json)
and [failure.json](experiments/0234-matched-norm-result/failure.json). Their bytes
are preserved unchanged. The attempt records the complete3,918,908 B source
inventory, original source/profile identities, null commands and
`physical-join-not-established`.

| Quantity | First failed attempt | Contract target / limit |
|---|---:|---:|
| Selected boxes / local methods / exact-range oracles |0 /0 /0|72 /144 /72|
| Own-origin checks / paired comparisons |0 /0|72 /72|
| Event visits / descriptors / directed primitives |0 /0 /0|32768 /1024 /8192|
| Completed rows |0|72|
| Source inventory |3,918,908 B|4,194,304 B|
| Durable producer files |2697 +553 =3250 B|1 MiB combined;64 KiB audit reserve|
| External / dispatcher elapsed time |0.219416833 /0.206261750 s|30 s through finalization|

All8 attempted/charged work counters are0; method/oracle attempted, charged and
completed progress is0. The failure precedes expected-event validation, trace
traversal, selected-vector extraction and local arithmetic. All14 prohibited-work
counters in the attempt are0. These counters and unchanged control flow support
the scoped no-SPICE/integration/scientific-helper finding; there is no completed
72-box result or independent numerical work ledger. The low resource usage of an
early failure does not qualify the full saved comparison.

There is no report, receipt, completion or audit file. The independent numerical
auditor was **not dispatched** because there is no completion hash or result to
verify. The requested numerical comparison/audit criteria remain unmet; R5.59x
stays unchecked and its sole producer authorization is consumed.

## Diagnosis and independent review

The [runner](experiments/0235-matched-norm.py) authenticates6 selected source roles
from ADR0229 `source_bindings`, creating `_context.source_pins`. The original
sealed report contains a17-key `method_sha256` map: those6 hashes all match, and
11 additional historical roles remain. Both scopes are `retained`.
The [evaluator](experiments/0235-matched-norm-core.py) requires full dictionary
equality, so17 entries cannot equal6 even with no selected hash mismatch.
This is an adapter/metadata admission defect, not a scientific divergence,
compatibility mismatch, input tampering or numerical limit exhaustion.

The [independent auditor](experiments/0235-matched-norm-audit.py) contains the same
whole-map equality check, although it was not run. The artificial fixture inherits
a6-key report map from [lineage_fixtures.py](../../tests/lineage_fixtures.py), with
the same6 keys in its authenticated context. The full-volume qualification covered
numeric volume and actual command shapes, but missed this historical metadata shape.
Passing artificial tests did not establish complete real adapter admission.

A separate [read-only failure review](experiments/0236-independent-failure-review.json)
independently confirms exact error/control flow,6 matching selected hashes versus
17 historical roles, the fixture gap, all8 qualified file hashes,13 original pins,
first durable evidence and absent numerical outputs. It does not rerun/import any
producer, numerical auditor, fixture or scientific module. The17 hashes are sealed
historical metadata; this run separately authenticates only the6 selected source
files and does not claim a new verification of the11 additional source files.
This review is not a replacement for the requested independent numerical audit.

## Options considered

- Edit the equality checks and retry now: rejected; would change measured code and
  exceed the fixed one-attempt contract before artificial qualification.
- Trim/rewrite the historical map or relax source identity: rejected; would alter
  pinned evidence or weaken admission without a reviewed contract.
- Preserve the failed attempt and independently record its precise boundary:
  selected. A versioned adapter repair and realistic artificial metadata-shape
  coverage are a separate next stage, followed by a new execution instruction.

## Decision and rationale

Preserve the first complete/partial evidence, [stdout](experiments/0236-saved-dispatch/producer.stdout),
[stderr](experiments/0236-saved-dispatch/producer.stderr),
[external measurement](experiments/0236-saved-dispatch/producer-measurement.json)
and [dispatch summary](experiments/0236-saved-dispatch/dispatch-summary.json).
No repair, normalization, changed formula/context/cap, repeated dispatch or invented
audit/completion occurs. R5.59w remains historical artificial qualification;
the newly observed real metadata admission gap is explicitly unresolved.
Automation `ariadna-m3` remains PAUSED.

## Evidence and verification

The [verification manifest](experiments/0236-verification.json) pins raw failure
files, dispatch evidence, independent review, unchanged code, contracts and13
original inputs. Metadata/document verification passed:491 local links,9 finite JSON files,
13 source-AST pins,13 original raw input pins and8 qualified source/test hashes;
scoped diff and strict OpenSpec pass. Runtime/test/dependency/legacy bytes and
historical evidence are unchanged. Pytest/Ruff are not rerun for this evidence-only
stage; ADR0235's86 focused/6750 guarded full passes,494 exclusions and Ruff result
remain artificial qualification, not successful real execution.

## Consequences and revisit conditions

No comparison, own-origin compatibility, exact-box containment, method advantage,
final-width attribution or dominant cause is established. The40.085 m/s mission
gap, continuous study, eligible command readiness, physical join, mission safety
and strict M3 remain unresolved; R5.60 stays closed. Revisit after a separately
instructed and independently qualified versioned producer/auditor metadata adapter,
with6-binding/17-role artificial coverage and unchanged historical data/contracts.
Any later execution needs a new authorization/output identity preserving this
consumed attempt. No SPICE or trajectory recomputation is needed to address the
identified metadata defect.
