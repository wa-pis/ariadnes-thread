# 0234 — Compare norm-squared methods on identical interval boxes

Date: 2026-11-21 (Europe/Samara)
Decision status: accepted
Implementation: not started; design only, no numerical extraction or experiment
Verification: source/metadata/document checks only; arithmetic qualification remains pending
Scope / milestone: M3, R5.59v design; future R5.59w artificial preparation and R5.59x saved local experiment are separate
Base revision: clean `61a27028152d162f003262db3ba91c141ce6a4c9`, synchronized `dev`/`origin/dev`
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves [ADR0229](0229-design-saved-lineage-diagnosis.md), [ADR0231](0231-record-saved-lineage-result.md) and [ADR0233](0233-record-corrected-saved-lineage.md)

## Context and constraints

The user requested design only: no calculations, SPICE, integration or R5.60.
ADR0233 established that all 36 saved default/independent norm slots have different
input intervals. Comparing those outputs cannot isolate the local method. A new
controlled local experiment must give both formulas the identical input box.
Its future arithmetic is outside the zero-new-norm scope of ADR0229/0232;
their contracts, programs, results and consumed attempts are not modified or replayed.

The isolated step is the squared Euclidean norm, before square root. Historical
`_norm2` uses a sum of interval squares when `independent=False` and a sum of
interval self-products with a nonnegative lower clip when `independent=True`.
These local names do not imply independence of the whole physical calculation.
The [source](experiments/0219-phase-bounds.py) and
[scalar primitives](experiments/0219-interval.py) are inspected as text/AST only.

## Options considered

- Compare the existing output pairs: rejected; all 36 are input-confounded.
- Select one input origin or merge the two boxes: rejected; privileges one origin
  or changes the question and may hide relevant cases.
- Run both formulas on both unchanged saved origins: selected, a balanced finite
  matrix with no new phase, geometric state or trajectory calculation.
- Import the old interval module: rejected; its initialization computes `PI=_pi()`.
  A future private kernel contains only the required scalar primitives/formulas.

## Decision and rationale

### Fixed matrix and source identity

The [design contract](experiments/0234-matched-norm-contract.json) freezes the same
three selected rows 62/94/125, cell/singleton domains, positive/negative signs and
three norm roles from ADR0229. For each of its 36 structural slots, take both
saved input origins. This defines 72 three-component boxes, including duplicate
values as distinct provenance records. Each box is supplied unchanged to both
methods, giving 144 local method evaluations per future producer/auditor process.

Select directly from the original 24 traces using authenticated parent paths and
direct-child `_norm2` ordinals, matching call/return records and entry/exit mode
flags. Bind the exact six endpoint strings, field pointers, source mode, row,
domain, sign, role and units. Both methods must consume the same payload hash;
no hull, intersection, rounding of inputs, reboxing, deduplication or selection by
result is allowed. The units remain m2/s2, m2 or m4/s2 for the respective squared
velocity, radius and angular-momentum roles.

Authenticate all 13 original pinned data/source files, the unchanged0229 contract,
this contract and every new private implementation source. Node hashes are SHA256 of
`ast.dump(node, annotate_fields=True, include_attributes=False, indent=None)`
encoded as UTF-8 under pinned Python3.12.14, for exactly the named function,
method or assignment node; the line anchor is separate. Full raw source hashes
remain mandatory. ADR0233 is motivation,
not an extra numerical input; do not load its 550,761-byte lineage report into
the future 4 MiB inventory. That report is unnecessary because structural
selection and original operands are already fixed by the authenticated traces.

### Methods, contexts and compatibility gate

- `square-sum`: `(x.square() + y.square()) + z.square()`, preserving the source
  absolute-value rounding before each square and left-associated additions.
- `product-sum-clipped`: `raw = (x*x + y*y) + z*z`, followed by
  `[max(0, raw.lo), raw.hi]`. Record raw and clipped endpoints separately.

Use a small isolated private kernel with source/normalized-AST identity checks
for these expressions and their constructor/coercion/validation/add/mul/abs/square
primitives. Never import or execute a whole historical module, load arbitrary
source, or call orbital bounds, geometry, trig, sqrt, exp or mass functions.

For each box/method, create fresh explicit lower/upper Decimal contexts: precision
96, ROUND_FLOOR/ROUND_CEILING, Emin=-999999, Emax=999999, capitals=1, clamp=0;
only InvalidOperation/DivisionByZero/Overflow traps enabled, all flags initially
cleared. Record the context fingerprint and final flags; only Inexact/Rounded
may become set. Parse endpoint strings exactly without quantization or binary64
conversion. Context parameters and flags matter to Decimal operations and are
explicit controls of this new experiment, not recovered historical observations.
The [Python decimal documentation](https://docs.python.org/3.12/library/decimal.html#decimal.Context)
explains those controls and exact construction from strings.

Of the 144 computed results, 72 are the original method on its own saved origin.
Require exact endpoint equality with the corresponding saved `_norm2` return
for all 72, without extra method evaluations. A mismatch produces overall
`inconclusive` with `compatibility-mismatch` and preserved first evidence: no
context tuning, alternative operands, selective effect admission or retry.
Passing checks compatibility for these finite calls under the imposed contexts;
it does not recover the historical runtime context or prove general equivalence.

### Independent reference and measurable outcomes

For the exact-real Cartesian box X with components [l_j,u_j], define symbolically:

`m_j = 0 if l_j <= 0 <= u_j else min(l_j²,u_j²)`
`M_j = max(l_j²,u_j²)`
`R(X) = [sum_j m_j, sum_j M_j]`.

This range follows by separate minimization/maximization of each squared
coordinate over a Cartesian product. It is not the range of correlated orbital
geometry. A future exact Fraction/integer implementation evaluates 72 such
reference ranges per process, additional to the 144 method evaluations.
Both method intervals must contain R(X) with exact rational comparisons and
zero tolerance. That containment alone does not verify a rounded program.

A separate auditor independently reproduces directed 96-digit primitive
rounding/grouping with integers/Fractions, verifies every new endpoint exactly,
and computes the real-box reference without evaluator arithmetic helpers.
It reselects inputs from raw pinned traces and binds the new completion hash.
It never replays old scientific producers/auditors or the full trajectory.

For each box, record both final intervals, the raw product lower bound/clip,
real-box range, diagonal check, exact widths, width difference, endpoint excess
and excess width relative to R(X). Those excesses are local box over-enclosure,
not a separation into dependency and rounding contributions. Record equal,
strict-subset in either direction, overlapping incomparable or invalid-containment
outcomes; do not assume which method wins. Define the signed width difference as
W(product-sum-clipped)-W(square-sum), and the ratio as W(product-sum-clipped)/
W(square-sum). A zero denominator gives null and either both-widths-zero or
zero-denominator/nonzero-numerator status, never epsilon or infinity.

Endpoint/diagonal equality is exact rational numeric equality, not string equality:
signed or scaled exact zeros compare equal. Preserve raw input and Decimal output
strings and context flags as diagnostic provenance; canonical rational endpoints
use reduced fractions and zero0. The auditor validates their finite bounded
encoding, numeric consistency, context and allowed-flag rules. It does not claim
exact historical Decimal representation or per-operation flag-history recovery.
Keep all dimensions separate. No conversion
of squared-width findings to an arrival speed improvement or mission benefit is
allowed without a separately designed downstream study.

### Proposed budgets and qualification

Use 30 s per command through durable finalization, 4 MiB complete source inventory
and 1 MiB combined output with 64 KiB audit reserve. Retain the bounded 8192 input
events/32768 validation visits, 1024-character endpoints/256 significand digits/
absolute exponent512/4096-bit rational components. Charge every source file once,
including all private modules and artificial bootstrap/configuration bytes.

Count 72 boxes, 144 attempted local method calls, 72 exact-range oracle calls,
72 diagonal checks and 72 paired comparisons per process. Precharge every scalar
directed abs/multiply/add/nonnegative-clip operation; limit8192, with the auditor
charging equivalent directed primitive replays. Fixed-fanout oracle and descriptor
work is counted separately and guarded against rational growth before allocation.
Distinguish attempted/charged/completed work and partial results on failure.
Do not copy an old zero-new-norm ledger: these are new local mathematical evaluations.
Unrelated orbital/point/root/trig/sqrt/exp/mass/native/SPICE/integration work stays0.
Write summary records rather than an unbounded per-primitive transcript.

These limits are proposed, not measured sufficient. R5.59w must qualify the full
matrix and representative numeric/source volume on artificial archives, including
signed/zero-crossing/degenerate boxes, raw negative dot clipping, precision/exponent
boundaries, method/origin order, exact-zero encodings, context drift, a diagonal
mismatch, tampering, all cap failures and exact parent/child retained/audit command
shapes using artificial dependencies. Require focused tests, frozen guarded full
pytest, Ruff, strict OpenSpec and independent review. If any limit is insufficient,
stop for a justified design revision; do not raise it automatically.

## Consequences and revisit conditions

The design can identify controlled local interval differences under fixed inputs
and contexts. It cannot allocate final width, establish a dominant cause, eliminate
the 40.085 m/s mission gap, certify continuous exclusion, create eligible commands
or prove physical continuity, safety or strict M3. Historical data, methods,
runtime, dependencies and `moon_to_mars.py` remain unchanged.

R5.59v is design only. R5.59w implementation/artificial qualification needs a
separate instruction. Only qualified R5.59w and another explicit instruction
permit one R5.59x saved local experiment and one independent audit, preserving
their first complete or partial evidence without retry. Automation remains PAUSED.

## Evidence and verification

Current work inspects source/AST and metadata only. No retained endpoint values
are extracted, no methods/oracle are evaluated, and no experimental output path
is created. The new contract pins 13 source nodes and all inherited raw inputs.
Check local links, JSON, immutable hashes, scoped diff and strict OpenSpec;
results belong in the [verification manifest](experiments/0234-verification.json).
Metadata checks passed: 476 local links, two finite JSON files, 13 source AST
pins and 13 original input pins; historical hashes, scoped diff and strict
OpenSpec agree. A separate read-only review found no material contradictions
in the matrix, context/compatibility gates, numeric endpoint equality or metrics.
No implementation or test bytes change; pytest/Ruff are not rerun. No numerical
evidence, comparison result or sufficiency claim is asserted by this design.
