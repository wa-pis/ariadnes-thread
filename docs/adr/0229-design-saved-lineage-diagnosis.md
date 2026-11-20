# 0229 — Design a saved-lineage check of interval widening

Date: 2026-11-20 (Europe/Samara)
Decision status: accepted
Implementation: not started; design only, no retained analysis or execution
Scope / milestone: M3, R5.59q; source-linked diagnosis of saved R5.59p observations
Base revision: clean `e22ea0f64fe2ccf754ed381b48cc6fd258133ef5`, synchronized `dev`/`origin/dev`
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves the consumed studies and [ADR0228](0228-record-corrected-retained-observations.md)

## Context and constraints

The user requested a design for checking the cause of widening using saved traces,
with no new calculations, SPICE or integration. ADR0228 established observations:
positive finite-cell speed widths94–98 m/s contrast with tiny midpoint singleton
widths, but no dominant cause was proved. Do not turn this contrast into an error
estimate or assume the physical phase variation is negligible.

The [contract](experiments/0229-saved-lineage-contract.json) pins the five ADR0228
raw artifacts, its verification manifest, ADR0224 contract and six source files.
Keep the same reference, rows62/94/125, cell/singleton domains, both signs and both
arithmetic paths:24 traces with1248 saved events. Historical `R5.59n` artifact labels,
original failures and all scientific gates remain unchanged. Do not rerun either
the old producer or its saved-only scientific auditor; that auditor evaluates mass.

### Question and evidential limit

Which source-linked stages already expose width, where are common inputs reused,
and do two local norm implementations respond differently to exactly identical
saved operands? A single saved midpoint cannot establish within-cell extrema,
quantify dependency overestimation, separate it from rounding, or allocate final
width to individual operations. A valid diagnosis may therefore leave causality
unresolved. This is an explicit outcome, not permission to start another experiment.

## Options considered

- Rank existing stage widths or subtract singleton width as an error contribution:
  rejected; differing observables and shared dependencies do not support that meaning.
- Run new point samples, precision variants, interval substitutions or deeper cells:
  outside the user's design-only request and consumed scientific contracts.
- Prepare a source-linked saved readback with one narrowly controlled local comparison:
  selected; it can test dataflow and a local algorithm response without new geometry.

## Decision and rationale

### 1. Authenticate and follow saved dataflow

A future reader must authenticate all13 pinned files and the attempt/report/receipt/
completion/audit chain,24-row identity, seals and source/method bindings before
analysing values. The old audit's status is historical evidence, not rerun authority.
Keep current reader counters separate from the historical48bounds/12mass calls.

Use each trace's ordered `index`, `call`, `parent`, `stage`, `event`, `fields` and
`scalars`. Match across traces by semantic parent path and same-stage direct-child
ordinal; a raw call number or coincident numeric value alone is not a source alias.
Verify the contract's exact alias groups linking anomaly, ellipse position/velocity/
GM, reverse inputs/results, final impulse speed and mass-arrival input. Record
JSON pointers and source-symbol/statement references. Required reached endpoints
must match exactly; no parity tolerance may hide a broken dataflow link.

Read18 predefined scalar/component checkpoints per trace from ellipse, reverse,
final speed and mass/duration fields. Only descriptive exact rational endpoint widths,
matching cell/singleton differences and ratios with a strictly nonzero denominator
are allowed. A zero denominator produces an unavailable ratio, never infinity or
an invented value. Keep units and observable identity; no ranking unlike quantities.
Expected early mass exit makes clearance `not-reached`, never a zero-width result.

The pinned source shows repeated-use motifs in common-anomaly geometry, normalized
vectors/root reconstruction and shared coast/final-mass expressions. Record these
as source-supported dependency risks. The scalar interval representation stores
endpoints rather than joint phase correlations. This structural observation alone
does not prove how much widening any motif causes on the retained cells.

### 2. Test only a controlled local norm comparison

The [bounds source](experiments/0219-phase-bounds.py) uses component squares in
its default `_norm2`, and `_dot(v,v)` plus nonnegative lower clipping in its
independent path. Freeze three semantic roles, not flat trace IDs:

| Parent path | Direct `_norm2` ordinal (zero based) | Quantity | Operand / result units |
| --- | ---: | --- | --- |
| `bounds` | 0 | Impulse squared norm | m/s / m²/s² |
| `bounds/_reverse[0]` | 1 | Position squared norm | m / m² |
| `bounds/_reverse[0]` | 4 | Angular-momentum squared norm | m²/s / m⁴/s² |

These yield36 candidate default/independent pair slots across rows, domains and signs. For
each, verify source role, all three saved operand endpoint pairs, pinned interval
implementation and unchanged Decimal96 contexts before comparing saved results.
Context equality is a conditional source/provenance assumption, not a saved runtime
context snapshot; if it cannot be justified, local-effect admission fails.
If operands differ, report `input-confounded`; do not attribute result differences
to the local branch. The two paths also differ upstream in trigonometry.

With identical operands and the fixed-context/source assumptions established,
identical saved results mean `no-local-difference-observed`. Different results mean
`conditional-local-method-response`: only the local algorithm changes in this
comparison. Missing required reached data, changed context/source or ambiguous
role is invalid; legitimate earlier exit is `not-reached`. No new norm or squared
value is computed. Never infer a contribution to final speed, a global dominant
cause, or validity of a tighter enclosure from this local observation.

### 3. Keep missing causal information explicit

The [observer](experiments/0225-bound-trace.py) captures function entry/return
locals, not every arithmetic operation. `_dot`, `_sum`, `_scale`, trig recurrence,
exp/sqrt internals, joint phase dependence and extremizer witnesses are not fully
recorded as operation-level events. The existing [summary](experiments/0225-trace-checks.py)
deliberately leaves generic primitive units unclassified; this design classifies
only the three norm roles above from their exact source contexts.

`_ellipse.radius` and `_reverse.radius` are distinct rounded expressions. Same units
and an exact-real orbital identity do not justify subtracting their widths as an
avoidable error or intersecting their enclosures; that would need a separate rounded
identity proof. Similarly, cell-minus-singleton width is descriptive, not an
upper/lower bound on overestimation or roundoff. Do not manufacture counterfactuals.

The resulting claim ledger must distinguish observed dataflow/widths, conditional
local method effects, source-supported risks and information not identifiable
from the archive. Overall success is `lineage-qualified-attribution-unresolved`;
inconclusive, invalid and exhausted results remain explicit. No causal percentage,
whole-cell exclusion, physical accuracy or command admission is an allowed output.

### 4. Bound implementation, qualification and later execution

R5.59q is this design only. R5.59r requires a separate implementation instruction:
prepare a stdlib-only reader and separately implemented verifier on fabricated
archives, without importing or evaluating any historical scientific module.
Use `ast`/text only for pinned sources. A separate artificial-only entry uses
explicit fabricated profiles: distinct data/reference/candidate/completion identities,
rechained raw pins and separate output roots, with the same six immutable source
pins, semantic role/dimension map and caps. The retained entry constructs its fixed
profile internally and rejects injected/rehash/mixed/relabeled test profiles.
The full-volume fixture has24 rows/36 candidate slots; early-exit variants declare
their own fixed event counts within the cap instead of pretending to have1248 events.
Tests must cover the full24-row/36-slot shape and at least the pinned source byte volume, alias/unit/role tampering,
identical versus confounded norm operands, equality, exact zero/undefined ratios,
legitimate non-reached stages, missing required fields, unsupported causal claims,
exclusivity, clocks/finalization and every exhausted cap. Include a fabricated
case where identical endpoint numbers have different source origins. A local
response fixture must not be reported as an end-to-end causal contribution.
Run focused and guarded full pytest, Ruff and strict OpenSpec before qualification.

Only after qualification and a separate explicit execution instruction may R5.59s
run one saved readback and one new independent verifier. That verifier independently
checks descriptors and permitted local comparisons from raw saved endpoints; it
calls neither the old scientific audit nor a shared producer analysis helper.
Preserve exclusive first complete/partial evidence and stop, without retry or caps
changed to obtain a preferred conclusion. Planned output paths are in the contract;
none is created now.

Both future processes have30 s from dispatch/imports/authentication through durable
finalization,4 MiB authenticated input each, and1 MiB combined new output with64 KiB
reserved for the verifier. Bound input events8192, counted event visits32768/process,
descriptors1024, alias links768 and norm-pair slots36. Reject oversized numeric text,
exponents or rational components before exact arithmetic under the contract's limits.
All new bound/trace/point/root/norm/mass/native/SPICE/force/integration counters are zero.

These limits bound a small archive traversal, not scientific accuracy. The13 pinned
inputs total3,784,677 bytes. Charge the contract and private reader/verifier sources
to the same4 MiB inventory during qualification;
no need to reread the nine older scientific inputs. ADR0228 timing is context, not a
new-reader performance guarantee. Full-volume artificial qualification must establish
that the declared envelope is sufficient before any retained analysis is authorized.

## Consequences and revisit conditions

This design can expose a local implementation effect or establish that a proposed
comparison is confounded. It cannot promise a dominant cause from inadequate data.
If causal information remains unavailable, document the missing observable and stop;
any new counterfactual evaluation, correlation-preserving formula or rounded-identity
proof is a separate scientific-method decision with its own scope and tests.
Automation remains PAUSED. No implementation, new retained arithmetic, repeated
0227 producer/auditor, deeper tree, altered threshold or R5.60 is authorized here.

## Evidence and verification

Only source/field-name inspection and byte/hash/identity metadata were checked for
this design; no new width analysis, norm-pair comparison or mathematical function
ran. Input pins and total byte inventory are in the contract. Independent read-only
source/schema review supports the distinction between lineage and causal attribution and
confirmed the three norm-role ordinals/dimensions. Its qualification-profile, slot
eligibility and alias-notation clarifications are incorporated in the contract.
All13 raw pins, six saved method-source bindings,18 checkpoint fields and36
candidate slots pass metadata checks;453 local Markdown links, finite JSON, unchanged
historical/runtime/legacy hashes, diff and strict OpenSpec pass. Runtime code is unchanged;
pytest/Ruff are not rerun. ADR0227's qualification remains historical evidence only.
