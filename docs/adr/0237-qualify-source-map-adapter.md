# 0237 — Qualify selected source bindings within sealed archive metadata

Date: 2026-11-21 (Europe/Samara)
Decision status: accepted
Implementation: complete for versioned R5.59y artificial repair only
Verification:124 focused/6788 guarded full passes,494 explicit exclusions; independent review agrees; final Ruff/strict/document checks recorded in manifest
Scope / milestone: M3, R5.59y; no repeated R5.59x or saved execution
Base revision: clean `21c6d69aca5cd1425fba4631ae95d2466fcb0397`, synchronized `dev`/`origin/dev`; new sources qualified at recorded hashes
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; versioned implementation repair preserves [ADR0234](0234-design-matched-input-norm-comparison.md), [ADR0235](0235-qualify-matched-input-norms.md) and [ADR0236](0236-record-saved-matched-norms.md)

## Context and constraints

The user authorized a new adapter/auditor version and artificial17-role/6-binding
qualification only. The consumed R5.59x failed before matrix selection because
its authenticated6-file source map was compared to the whole17-role historical
metadata map. All6 selected hashes matched; artificial fixtures missed the shape.
No saved comparison/audit is authorized, and SPICE, integration and R5.60 remain
excluded. Preserve every old source/test/evidence byte and the first failure.

## Options considered

- Edit0235 or trim historical metadata: rejected; would rewrite measured code/data.
- Ignore unselected fields or accept a smaller selected map: rejected; would allow
  malformed metadata or omit required authenticated bindings.
- Version the three private modules and require exact selected projection within
  closed6/17-key metadata forms: selected; repairs admission without changing math.

## Decision and rationale

The new0237 core and independent auditor each implement their own metadata check.
The authenticated map must have exactly `bounds`, `checks`, `interval`, `runner`,
`trace`, `trace_schema`. Every value is a64-character lowercase hexadecimal hash.
The whole historical map must have exactly those6 keys, or those6 plus `anchors`,
`archive`, `containment`, `core`, `io`, `oracle`, `orbit`, `points`, `reader`, `screen`,
`study`. Both complete forms are supported; partial/unknown sets, malformed keys
or hashes, missing/mismatched selected roles and scope drift are rejected before
trace selection or numerical work. Compare all6 selected values exactly.

The additional11 entries are sealed provenance, not newly authenticated source
files. Raw seven-record chains/pins, six selected source-file pins,13 original
input artifacts,13 source AST nodes and private-source hashes remain required.
No assertion is made that17 source files were independently read/verified.

The0237 runner retains the immutable scientific0234 and inherited0229 contracts,
all formulas/contexts/selection/caps/work/error/finalization guards. Only new source
filenames, artificial profile registration, stage labels and future output binding
are versioned. The operational output namespace is `0237-matched-norm-result` and
`0237-matched-norm-audit.json`; this ADR introduces that binding without editing
0234's historical output contract or reusing its consumed failure. These new fixed
paths remain absent. Future saved stage R5.59z needs a distinct explicit instruction;
R5.59x is not reopened. No new dependency or production/package behavior changes.

## Qualification contract

Use only fabricated17-role archives built from the existing full24-trace/1248-event
fixture and literal artificial extra-role hashes, keeping the authenticated map6.
Verify the complete72-box/144-method/72-exact-range/72-diagonal/72-comparison matrix
against the independent integer/Fraction auditor and unchanged6-role control.
Test every selected role missing/mismatched, reduced context maps, malformed/unknown/
partial extras, scope drift, rehashed chains, raw-pin rejection and legacy6-role
admission. Test actual four/five-argument retained/audit parent-child forms only
through a versioned test-only bootstrap that blocks real data reads.

Retain the original30 s/4 MiB source/1 MiB combined-output/64 KiB audit-reserve and
all numerical/work limits. Include all private/bootstrap/configuration bytes in
artificial inventory. Verify exclusivity, progress/partial evidence, immutable old
failure and absent new fixed outputs. Isolated local norm/oracle evaluations on
artificial data are nonzero; orbital/root/trig/sqrt/exp/mass/native/kernel/SPICE/
force/integration/old-audit/R5.60 work remains zero in qualification workers.
The guarded full regression includes existing artificial scientific unit tests;
its native/live/retained-force exclusions are preserved explicitly.

Run focused tests, freeze all checkout/docs/evidence/staging for one guarded full
suite, then Ruff/strict/source-delta/hash/link/finiteJSON checks and independent
review. Runtime/native qualification is not implied by this artificial repair.

## Evidence and verification

The [fixture](../../tests/matched_norm_metadata_fixtures.py) adds11 invented
provenance hashes to the existing artificial records, preserving all selected norm
operands. Its7 records total3,696,764 B; with6 source files the13-file volume is
3,787,235 B, exceeding the original3,784,677 B. The [tests](../../tests/test_matched_norm_metadata.py)
verify17/6 admission, exact complete-analysis equality with old6-role results,
all72 own-origin matches, independent directed-rounding/real-box checks and every
negative metadata class. Three existing guard tests are reused through scoped
monkeypatches against the new version, leaving old tests untouched.

The [artificial qualification](experiments/0237-qualification/artificial-summary.json)
and [independent audit](experiments/0237-qualification/artificial-audit.json) agree
on72 boxes/144 methods/72 exact-range oracles/72 diagonals/72 comparisons,1248
event visits,72 descriptors and3444 directed primitive operations/process.
All144 methods and72 oracles are attempted, charged and completed. Both method
results contain their exact-real box range and all72 own-origin checks pass.
The new [test-only bootstrap](../../tests/matched_norm_metadata_dispatch_harness.py)
exercises exact4/5-argument parent/worker forms using fabricated dependencies only;
it blocks real input reads. No unmodified retained command or saved numerical
comparison occurred. Whole-map metadata remains sealed by the raw file chain.

| Quantity | Verified artificial result | Unchanged limit |
|---|---:|---:|
| Complete source inventory/process |3,930,106 B|4,194,304 B|
| Producer + audit outputs |552,013 +1012 =553,025 B|1 MiB;64 KiB audit reserve|
| External producer / audit time |0.300015750 /0.233777375 s|30 s each|
| Dispatcher producer / audit time |0.288370667 /0.221699541 s|same shared deadline|
| Directed primitives/process |3444|8192|

The initial focused run had123 passes/1 failure: a new test incorrectly required
auxiliary metadata Budgets to share the main invocation clock. The corrected test
checks the primary parent/worker clock/id and all bootstrap/config charges/hashes;
no runtime change was needed. Its [first log](experiments/0237-qualification/first-focused-failed.log)
and frozen snapshots remain preserved. Subsequent focused checks pass124 tests.

The first external qualification summary helper misspelled a metadata key after
both fabricated commands succeeded. Its [failure record](experiments/0237-qualification/first-summary-helper-failure/driver-failure.json),
driver and first artificial outputs remain intact; no missing external timing is
invented. Correcting only the outer helper produced a separate artificial pair
with the complete measurements above. Neither pair used real retained inputs.

The frozen guarded full run passes6788 tests with494 explicit exclusions in
182.54 s. [Before](experiments/0237-qualification/before-snapshot.json) and
[after](experiments/0237-qualification/after-snapshot.json) hashes/status match
for every Git-visible file. The unchanged native guard and exact skip list are
retained; this is not unrestricted/native qualification. Existing artificial
scientific unit tests execute, so zero-prohibited-work worker counters are not
a claim that the whole suite performs zero scientific arithmetic.

Independent source/test/evidence review agrees on projection authentication,
closed schemas, unchanged arithmetic/guards, exact bootstrap clock scope and claim
limits. The [verification manifest](experiments/0237-verification.json) records
source hashes, complete evidence pins, final Ruff/strict/link/finiteJSON checks and
all unchanged historical13-file/13-AST/8-qualified-file/failure evidence identities.
Final checks pass:494 local links,27 finite JSON files, exact AST identity outside
the reviewed admission regions, original494 skip node IDs, Ruff and strict OpenSpec.
Code/docs whitespace checks pass; the byte-preserved first pytest transcript and
canonical unified diff retain their original whitespace and are excluded from
that formatting-only check.
New fixed0237 outputs remain absent; R5.59x stays consumed/unchecked. No saved
comparison, SPICE, integration, R5.60 or production/dependency change occurred.

## Consequences and revisit conditions

This repair can qualify admission of the17-role shape and unchanged local math on
artificial data; it cannot establish saved-call compatibility, interval-widening
cause, final-width improvement, eligible commands, physical continuity, mission
safety or strict M3. The40.085 m/s gap and continuous study remain unresolved.
Automation stays PAUSED. A future saved execution requires qualified repair and
a separate instruction/new attempt identity preserving ADR0236; R5.60 stays closed.
