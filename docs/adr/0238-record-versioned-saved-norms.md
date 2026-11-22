# 0238 — Record the versioned matched-input saved comparison

Date: 2026-11-22 (Europe/Samara)
Decision status: accepted
Implementation: one R5.59z producer and one independent numerical audit complete; both authorizations consumed
Verification: both commands return 0; independent saved-evidence review agrees; final metadata/document checks in verification manifest
Scope / milestone: M3, finite saved-call local norm comparison only
Measured revision: clean `f5437e44bcbaebf14c977b67c1fa6f1617d578fc`, synchronized `dev`/`origin/dev`; qualified 0237 sources unchanged
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves [ADR0234](0234-design-matched-input-norm-comparison.md), [ADR0236](0236-record-saved-matched-norms.md) and [ADR0237](0237-qualify-source-map-adapter.md)

## Context and constraints

The user separately authorized exactly one offline R5.59z execution through the
qualified 0237 version on 72 saved sets, followed by an independent audit. The
[authorization](experiments/0238-saved-dispatch/authorization.json) binds the clean
revision, runtime, six qualified files, thirteen original inputs, both contracts,
complete source inventory and unchanged limits before dispatch. No bootstrap,
profile override, SPICE, integration or R5.60 is admitted. The earlier R5.59x
failure remains consumed and unchecked; its original namespace is preserved.

## Options considered

- Repeat the consumed 0235 attempt or overwrite its evidence: rejected.
- Tune contexts or select successful rows after observing results: rejected.
- Run the separately qualified 0237 version once in its new fixed namespace and
  independently audit its raw completion: selected under the explicit instruction.

## Decision and rationale

Retain the first complete result and separate numerical audit unchanged. Accept
only the finite local comparison conclusion below, preserving every original
scientific gate and historical failure. Neither the producer nor auditor is rerun.
The [dispatcher and external records](experiments/0238-saved-dispatch/dispatch-summary.json)
preserve the exact isolated commands, first-attempt identities, return codes and
external timings; the [driver](experiments/0238-saved-dispatch/dispatch.py.txt) is
saved as text for provenance, not as permission to execute it again.

## Evidence and verification

The [producer report](experiments/0237-matched-norm-result/report.json) returns
`matched-norm-qualified-local-only`, reason null. The [independent audit](experiments/0237-matched-norm-audit.json)
returns `matched-norm-independently-verified`, with proof status `verified` and
that same local result. All 72 own-origin checks match the saved original returns;
all 144 method enclosures contain the independently verified exact-real box range.

| Saved semantic role | Compared boxes | Final enclosure classification |
|---|---:|---|
| Impulse squared, m2/s2 | 24 | 24 equal |
| Radius squared, m2 | 24 | 24 equal |
| Angular momentum squared, m4/s2 | 24 | 24 equal |

There are 36 boxes per saved origin, preserving both origins for each structural
slot. Each box supplies identical inputs to both methods. All 72 final rational
endpoint pairs agree; the stored product-minus-square width differences are 0
and all 72 finite product-over-square ratios are 1. This reports the saved local
results without recomputing the trajectory or replaying historical auditors.

Each process records 72 boxes, 144 method calls, 72 exact-real box oracles,
72 diagonals, 72 comparisons, 1248 event visits, 72 descriptors and 3672 directed
primitives. All 144 methods and 72 oracles are attempted, charged and completed.
All 144 fresh imposed Decimal96 context pairs share fingerprint
`fd1906f2c2eaa3b2266f36e6b453eed95a141ab037217761440412fd6b48127b`;
initial flags are clear and final flags permitted. These are controlled new
contexts, not recovered historical runtime snapshots. Diagonal success establishes
compatibility for these finite calls only.

| Quantity | Measured saved result | Unchanged limit |
|---|---:|---:|
| Complete source inventory/process | 3,920,340 B | 4,194,304 B |
| Producer / audit outputs | 641,648 / 997 B | 1 MiB combined; 64 KiB audit reserve |
| Combined output | 642,645 B | 1,048,576 B |
| External producer / audit time | 0.397030292 / 0.330206208 s | 30 s each |
| Dispatcher producer / audit time | 0.381559375 / 0.314619875 s | same shared deadline |
| Directed primitives/process | 3672 | 8192 |

Both commands exit 0 without timeout. Producer invocation
`d1f6b7815fd84257889b0de50143792b` and auditor invocation
`dfc5512edd4e40e5933ddb9a173b96f0` are distinct. The raw
[completion](experiments/0237-matched-norm-result/completion.json) SHA256 is
`aa0d8696294093c6c812c2ce5dac78f684c963c89156f92dca36e9c2773f7243`,
which binds the audit. The attempt/report/receipt/completion/audit chain,
canonical analysis hash, six qualified files, thirteen original inputs,
thirteen source AST pins, both contracts and all prior 0236/0237 evidence are
checked in the [verification manifest](experiments/0238-verification.json).

All fourteen prohibited counters are 0 in producer/receipt/audit: no new bounds,
traces, points, point roots, mass oracle, orbital norms, stage events, SPICE,
kernel access, force evaluations, integration, native calls, old-audit replay or
R5.60. Local norm/oracle arithmetic is nonzero and counted separately. Commands
remain null; physical status remains `physical-join-not-established`.

The [independent saved-evidence review](experiments/0238-independent-saved-review.json)
agrees without importing numerical modules or repeating the numerical audit.
The outer documentation checker stopped twice before manifest creation: an exact
version-string comparison and the forward link to its not-yet-written manifest.
The [first](experiments/0238-saved-dispatch/initial-metadata-check-failure.json) and
[second](experiments/0238-saved-dispatch/second-metadata-check-failure.json) metadata
failures are preserved; only those outer checks were corrected. Neither caused
a producer/auditor rerun or changed the saved scientific result.

No implementation, dependency, runtime source or test file changed. Pytest/Ruff
were not rerun for this evidence/document stage. ADR0237's 124 focused / 6788
guarded full passes (494 exclusions) remain historical artificial qualification,
not a claim that the post-run checkout passes that suite.

A separate test-lifecycle issue is explicit: [the new fixed-path test](../../tests/test_matched_norm_metadata.py)
at line 352 assumes the fixed 0237 outputs are absent before execution. Authorized
R5.59z has now created them, so that precondition is stale. No test failure was
executed or invented. Preserve the six qualified bytes during this measured
stage; adapt that test before a future code-stage regression. This does not
invalidate the completion chain, independent numerical audit or scientific gates.

## Consequences and revisit conditions

On these 72 identical saved input boxes neither method yields a narrower final
local enclosure. ADR0233's original 36 comparisons were input-confounded; the
controlled comparison now observes zero local method difference for both saved
origins. It does not explain the incoming widths, correlated orbital domain or
final arrival-width contribution, identify a dominant cause, prove general
formula equivalence or establish a speed/fuel benefit.

The 40.085 m/s grid gap, unresolved continuous study, absent eligible commands,
physical join, mission safety and strict M3 remain unchanged. R5.60 stays closed.
Both new authorizations are consumed; no retry, formula/context/input/cap change
or further research is implied. Automation remains PAUSED. A next investigation
needs its own scoped question and decision; fix the stale pre-execution test in
a separate verified code stage before relying on a new full-suite result.
