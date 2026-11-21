# 0235 — Qualify matched-input norm methods on artificial archives

Date: 2026-11-21 (Europe/Samara)
Decision status: accepted
Implementation: complete for R5.59w; artificial qualification only
Verification: 86 focused / 6750 guarded full passes, 494 explicit exclusions; Ruff passed; document/strict checks recorded in manifest
Scope / milestone: M3, R5.59w; R5.59x and R5.60 not executed
Base revision: clean `f4fe57c7272d8f2a6da80391dcba7ceac032ffe5`; seven new source/test files qualified uncommitted at recorded hashes
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; implements [ADR0234](0234-design-matched-input-norm-comparison.md), preserves all historical evidence

## Context and constraints

The user authorized artificial implementation/qualification of the fixed same-input
norm-squared design, with no SPICE, integration, R5.59x or R5.60. The prior
[ADR0233](0233-record-corrected-saved-lineage.md) observation remains unchanged:
all36 real saved pairs have different operands. Artificial results qualify the
method and wrapper; they do not establish how the real saved pairs will behave.

The immutable [0234 contract](experiments/0234-matched-norm-contract.json) retains
its matrix, source expressions, context controls, scientific gates and all caps.
No public package, physical model, stack, dependencies or historical scientific source changed. One existing admission test is corrected below; its prior version and all old evidence remain preserved.

## Options considered

- Import historical interval/orbit modules: rejected; their initialization and
  unrelated scientific functions exceed this local arithmetic scope.
- Share evaluator arithmetic with the audit: rejected; would weaken independence.
- Version the qualified dispatcher mechanism, isolate its two local formulas,
  and implement a separate integer/Fraction replay: selected. Existing artificial
  trace structure and stdlib infrastructure are reused; historical scientific
  source/evidence files remain intact.

## Decision and rationale

The versioned [runner](experiments/0235-matched-norm.py) authenticates both immutable
contracts, the fixed13-file data/source inventory (or its explicitly pinned
artificial counterpart), source AST nodes and every private source byte. Its fixed retained profile/output paths are separate from
the content-pinned artificial profile. A test-only bootstrap substitutes only
fabricated dependencies while exercising the actual `retained`/`audit` parent
and four/five-argument worker paths. This is command-shape qualification, not a
retained invocation or authorization to execute R5.59x.

The isolated [Decimal evaluator](experiments/0235-matched-norm-core.py) preserves
abs-before-square rounding, four-corner self-products, left-associated additions
and the nonnegative lower clip. Each method has fresh explicit Decimal96 contexts.
The separate [auditor](experiments/0235-matched-norm-audit.py) reconstructs input
selection and directed rounding with bounded integers/Fractions without evaluator
arithmetic helpers. It checks all endpoints/metrics, exact-real range containment,
source pointers, contexts, zero representations and work ledgers independently.
The imposed contexts still do not recover a historical runtime snapshot.

Own-origin compatibility checks remain mandatory. Any mismatch makes the whole
analysis inconclusive. The wrapper binds outer/inner/independently verified
statuses, so a rehashed envelope cannot promote an inconclusive result. Partial
failure evidence preserves completed row payloads, successful charges, attempted
work and attempted/charged/completed method/oracle progress when finalization fits
the original deadline and producer byte reserve. It never creates a success marker
on failure or overwrites the first attempt; an exhausted deadline may leave only
the already durable partial evidence.

## Evidence and verification

The [fixture](../../tests/matched_norm_fixtures.py) reuses24 fabricated traces and
1248 events, with independently constructed selected norm snapshots and6156 saved
endpoint descriptors. It includes signed, zero-crossing/touching, degenerate,
96/97-digit and mixed-exponent inputs; volume is not manufactured by padding an
unrelated field. Nonselected snapshots remain fabricated metadata and do not
claim orbital consistency. Seven data records total3,694,257 B; their six original
source bindings make3,784,728 B, exceeding the original13-file3,784,677 B volume.

[Arithmetic tests](../../tests/test_matched_norm.py) cover exact analytic cases,
both formulas, all72 diagonals, same-payload/source-origin invariance, context
order/drift, bit/parse/work boundaries, ratio/zero semantics, provenance tampering
and first partial progress. A defensive zero-denominator/nonzero-numerator branch
is fault-injected and rejected by the auditor; no attainability claim follows.
[Dispatch tests](../../tests/test_matched_norm_dispatch.py) cover actual command
forms, profile isolation, complete charging, malformed arguments, caps, exclusive
writes, late cleanup, rehashed status tampering and retained partial rows.

The initial guarded full run exposed one stale assertion in an older test:
`test_fixed_retained_profile_rejects_override_without_input_read` required the
0229 outputs to be absent, although ADR0233 legitimately created them. That run
had6749 passes,494 exclusions and one failure; its log and frozen snapshots are
preserved. The [corrected existing test](../../tests/test_lineage_runner.py)
retains both rejection assertions, blocks original data reads, and checks output
existence/raw hashes before and after rejection instead of deleting saved data.
It does not parse endpoints, alter a scientific gate or add an exclusion. The
[prior test source](experiments/0235-qualification/prior-lineage-runner-test.py.txt)
is preserved at the old recorded hash. A new frozen full run follows the fix.

The full-volume [qualification](experiments/0235-qualification/artificial-summary.json)
returns `matched-norm-qualified-local-only`; its separate
[audit](experiments/0235-qualification/artificial-audit.json) returns
`matched-norm-independently-verified`. Both processes agree on:

| Quantity | Verified artificial result | Unchanged limit |
|---|---:|---:|
| Boxes / methods / exact-range oracles |72 /144 /72|72 /144 /72|
| Own-origin checks / paired comparisons |72 /72|72 /72|
| Event visits / descriptors |1248 /72|32768 /1024|
| Directed primitive operations |3444|8192|
| Complete source inventory per process |3,926,066 B|4 MiB|
| Producer + audit outputs |552,007 +1012 =553,019 B|1 MiB;64 KiB audit reserve|
| External producer / audit time |0.271878792 /0.269035041 s|30 s each through finalization|
| Dispatcher producer / audit time |0.260736166 /0.257245750 s|same shared deadline|

All144 method and72 oracle calls are separately attempted, charged and completed;
all72 own-origin checks pass. Qualification worker ledgers and reviewed isolated call paths show zero prohibited
orbital/new-point/root/trig/sqrt/exp/mass/native/kernel/SPICE/force/integration/
old-audit/R5.60 activity. New local norm/oracle arithmetic is explicitly nonzero.
Real retained input reads are blocked in both test parent and worker.

86 focused tests pass. The frozen guarded full suite passes6750 tests with
494 explicit exclusions in186.61 s. Its copied native guard and exact skip
list are retained. This is a guarded full run, not an unrestricted live/native
qualification: existing artificial scientific unit tests still execute, so the
worker's zero-prohibited-work ledger is not a claim about every test calculation.
[Before](experiments/0235-qualification/before-snapshot.json) and
[after](experiments/0235-qualification/after-snapshot.json) Git/source snapshots
match exactly throughout the full run, including no documentation or staging
mutations. Ruff, independent cross-review and final metadata/strict OpenSpec
results are recorded in the [verification manifest](experiments/0235-verification.json).

## Consequences and revisit conditions

R5.59w is complete only for the fixed artificial scope and measured source hashes.
No retained input endpoints were extracted by this implementation, no real
matched-method conclusion was obtained, and fixed0234 retained output paths remain
absent. A separate explicit user instruction is required for one R5.59x saved local
experiment and one independent audit; no retry, context tuning or automatic cap
increase follows from this qualification. Automation remains PAUSED.

No conclusion about final arrival width, dominant widening cause, the40.085 m/s
mission gap, continuous exclusion, eligible commands, physical continuity, mission
safety or strict M3 follows. R5.60 remains closed and historical failed/consumed
attempts remain unchanged. Revisit only with explicit scope and preserved evidence.
