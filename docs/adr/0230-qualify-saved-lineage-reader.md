# 0230 — Qualify the saved-lineage reader on fabricated archives

Date: 2026-11-21 (Europe/Samara)
Decision status: accepted
Implementation: complete for R5.59r; artificial verification passed, R5.59s not run
Scope / milestone: M3, R5.59r; preparation under the unchanged ADR0229 contract
Base revision: `41170043605f2a3c9a3b221e0bf9ce85ef6796ae` on `dev`/`origin/dev`; six new source/test files were untracked during measurement, pinned in the [verification manifest](experiments/0230-verification.json)
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; implements [ADR0229](0229-design-saved-lineage-diagnosis.md) without changing its scientific decisions or immutable contract

## Context and constraints

The user explicitly requested implementation and artificial qualification, without
SPICE, integration or R5.59s. Saved-stage widths and repeated uses are observations;
local same-operand comparisons cannot assign a contribution to final interval width.
The prior retained ADR0228 result and every consumed experiment remain historical.
The new0230 reader/verifier and fabrication/qualification processes did not parse or
analyse retained numerical endpoints or evaluate a scientific helper. Those processes
read historical source files only as text/bytes; immutable archive checks use hashes only.

## Options considered

- Share analyzer formulas with the verifier: rejected because that would repeat a
  common error instead of independently reconstructing descriptors and dispositions.
- Accept caller-supplied rehashed artificial identities: rejected because relabeled
  historical payloads could bypass the preparation boundary.
- Use separate stdlib analysis implementations, three fixed fabricated content
  profiles and a common bounded I/O dispatcher: selected. This preserves independence
  of the analysis while keeping authentication and durable output checks explicit.

## Decision and rationale

[The dispatcher](experiments/0230-saved-lineage.py) provides separate artificial and
fixed retained entries. Only the artificial entry was exercised. Its allowlist pins
all seven fabricated file hashes/sizes, event count, scope, reference, candidate and
completion identity; paths may vary but must resolve outside the repository.
Resolved paths reject symlink-ancestor escapes. The retained profile is constructed
internally and refuses overrides; its two fixed output paths remain absent.

[The analyzer](experiments/0230-lineage-core.py) follows semantic parent paths and
direct same-stage ordinals, exact source aliases,18 checkpoints,24 trace identities
and36 candidate norm slots. It calculates only saved endpoint widths, differences
and nonzero-denominator ratios as exact bounded rationals. Zero-denominator ratios
remain unavailable; legitimate early exits remain not-reached. Equal values from
different source origins are not extra aliases. Source-symbol/statement links and
JSON pointers accompany units and claim limits.

[The verifier](experiments/0230-lineage-audit.py) independently reconstructs the
same descriptors, links and conditional local dispositions from the authenticated
fabricated archive. It neither imports the analyzer nor calls an old scientific
auditor. Rechaining altered output cannot conceal different identities, units,
counts, dispositions or causal claims. Decimal96 context equality is still the
contract's conditional source/provenance assumption, never an observed snapshot.

Both isolated CLI processes use `-I -S -B`, a dispatch-before-import shared clock,
a native/network/file-scope guard, bounded source inventory and exclusive durable
evidence. Input hashes precede JSON parsing; duplicate keys, nonfinite/noncanonical
numbers and excessive numeric sizes fail. Rational size checks precede subtraction
and division. Private source loading bypasses adjacent bytecode caches. Deadline,
work, input/output byte exhaustion and late fsync/readback failures cannot publish
a successful completion/audit marker; earlier partial evidence remains untouched.
All new bounds/traces/points/roots/norms/mass/native/SPICE/kernel/force/integration/
old-audit/R5.60 counters are zero. Production code, dependencies and all thresholds
remain unchanged.

## Evidence and verification

[Fabrication recipe](../../tests/lineage_fixtures.py) and
[semantic tests](../../tests/test_saved_lineage.py) construct a full24-row/1248-event
archive with6156 saved numeric descriptors, representative96-digit operands and
exponents, plus separately pinned early-exit96/1152-event variants. The full
seven-file plus six-source volume is3,784,844 bytes, exceeding the required3,784,677
without padding. The input catalog mirrors saved snapshots rather than evaluating
new geometry. The three artificial norm dispositions each occur12 times; these
counts describe fixtures, not retained observations.

[Runner tests](../../tests/test_lineage_runner.py) cover strict admission, tampering,
all shared budgets, native/source guards, exclusivity and late finalization. Final
focused tests:70 passed in6.33 s. The frozen-checkout guarded full suite:
6648 passed, 494 skipped in163.51 s; the inherited guard explicitly
excludes native SPICE, live UI ephemerides and prohibited retained force/scientific
replays. Existing artificial scientific-helper unit tests still execute in that
regression suite; the zero-new-science counters apply to the0230 qualification
processes, not simulated operations inside unrelated tests. These exclusions are
not native or physical qualification. Checkout status
and six measured source hashes match before/after. Ruff and strict OpenSpec pass.

A separate full-volume artificial [producer/result](experiments/0230-qualification/artificial-result/report.json)
and [independent audit](experiments/0230-qualification/artificial-audit.json) both
return0. External elapsed times are0.236658041 s and0.178167792 s versus30 s per
process. Charged source inventory is3,888,966 bytes/process versus4,194,304; combined
new output is387,623 bytes versus1,048,576 with65,536 reserved for the verifier.
Both process counters are1248 event visits,648 descriptors,528 alias links and36
norm-pair slots. The [summary](experiments/0230-qualification/artificial-summary.json),
[logs/guard](experiments/0230-qualification/full.log) and
[manifest](experiments/0230-verification.json) pin measured sources and evidence.
The deterministic recipe and artificial profile pins preserve the input identity;
large duplicated fake-input payloads are not retained. Absolute paths inside the
raw profile describe the measured temporary directory.

## Consequences and revisit conditions

R5.59r is qualified for the stated artificial envelope. Overall artificial success
is `lineage-qualified-attribution-unresolved`; it proves reader/verifier behavior,
not a widening cause, tighter enclosure, continuous refusal or mission feasibility.
A later explicitly authorized R5.59s may perform one fixed saved readback and one
independent verification under ADR0229. Artificial timing does not guarantee the
retained data will succeed; preserve its first complete/partial result without retry.
The0230 qualification processes ran no R5.59s, retained endpoint analysis,
scientific helper, SPICE or integration.
Automation remains PAUSED. No eligible commands or R5.60 admission follows.
