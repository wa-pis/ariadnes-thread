# 0232 — Qualify the saved-reader retained and audit command shapes

Date: 2026-11-21 (Europe/Samara)
Decision status: accepted
Implementation: complete; exact command dispatch qualified on fabricated archives only
Scope / milestone: M3, R5.59t dispatcher repair after the consumed R5.59s failure
Base revision: clean `2f98132d986b6629536d958bacc04d94d0029636`, synchronized `dev`/`origin/dev`; measured source/test pins are recorded below
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves [ADR0231](0231-record-saved-lineage-result.md), [ADR0230](0230-qualify-saved-lineage-reader.md) and the immutable ADR0229 scientific contract

## Context and constraints

The user explicitly authorized a dispatcher repair and qualification of retained/audit
commands on fabricated data only. No repeated R5.59s, SPICE, integration or R5.60 is
allowed. ADR0231's consumed failure arose because the retained worker has four argv
items but the historical0230 guard requires at least five. The artificial entry's
longer shape did not exercise that boundary.

## Options considered

- Add a dummy argument to pass the old guard: rejected; hides the grammar defect and
  violates the exact command-shape check.
- Edit historical0230 source: rejected; destroys the qualified/failure source identity.
- Version the dispatcher with the minimum four-item worker prefix, then delegate
  exact command arity to its existing CLI: selected. Scientific modules, formats,
  input identities, output paths and every inherited limit remain unchanged.

## Decision and rationale

Create0232-saved-lineage.py as a versioned copy of0230 with only the worker minimum
changed from five to four and its private self-source name updated. Keep the exact
analyzer and independent verifier sources and ADR0229 contract. The existing CLI
still admits only exact retained, audit, artificial and audit-artificial forms;
truncated, unknown or extra-argument commands must fail without data access.
No profile override is added to the production retained/audit entry.

Qualification must reproduce both complete parent-to-child worker shapes on an
explicit fixed fabricated profile, rather than merely call artificial aliases or
an isolated parser. A test-only isolated bootstrap may inject fabricated profile
and output dependencies and redirect only the child script path back to that
bootstrap. It must retain command arguments exactly, introduce no dummy argument,
and never replace authentication, profile admission, guards, analyzer or verifier.
Charge bootstrap/configuration bytes as well as the complete data/private-source
inventory; keep all same30 s/4 MiB/1 MiB limits and native/scientific prohibitions.
The bootstrap is test code, never a production CLI mode or retained-profile escape.

Exercise exact retained/audit and worker prefixes, malformed/truncated/extra arities,
full24-row/1248-event/36-slot fabricated analysis and separate verification, existing
artificial aliases, source/output isolation, exclusive evidence, clocks/finalization
and counter/byte limits. Run focused tests, frozen guarded full pytest, Ruff and
strict OpenSpec. The new specification must be valid before implementation.

## Consequences and revisit conditions

This repairs command dispatch, not scientific feasibility or retained-data admission.
R5.59s remains unchecked and consumed. No fixed retained outputs may be created or
numerical historical payload analysed during qualification. Any later saved readback
requires a distinct explicit execution decision after this repair qualifies.
Automation remains PAUSED. Old source bytes, evidence, failure labels, tolerances,
scientific assumptions and moon_to_mars.py remain immutable.

## Evidence and verification

The measured base is `2f98132d986b6629536d958bacc04d94d0029636` with the three
new source/test files untracked and the prepared ADR/OpenSpec edits present.
Checkout status and source hashes were identical throughout the full suite;
logs and qualification data were written outside the checkout until it exited.
No historical source or evidence was edited. The [exact two-edit delta](experiments/0232-qualification/source-delta.json)
changes only the minimum worker prefix and private self-source filename.

- [Dispatcher](experiments/0232-saved-lineage.py):
  `27213db58d711adf66634a960ffdbd12c060cbf68e327bcaac5ec42561cdc9c1`.
- [Test-only bootstrap](../../tests/lineage_dispatch_harness.py):
  `abbad6350806afc98d27bc575fc45591243589830a4070247a3f034266efd041`.
- [Command tests](../../tests/test_lineage_dispatch.py):
  `ed7ce250f575aa14f92800081266e82bc212069f0ef6449d8857c2c767480827`.

The retained-shaped parent dispatches `worker START NONCE retained` (four items);
the audit-shaped parent dispatches `worker START NONCE audit COMPLETION_SHA256`
(five). Each child preserves the parent start/nonce. These are exact CLI shapes
over the content-pinned artificial profile: the test-only bootstrap changes only
profile/output dependencies and the child script path, and retains the production
profile admission, authentication, guard, analyzer and independent verifier.
The [raw producer](experiments/0232-qualification/producer.stdout) and
[audit transcripts](experiments/0232-qualification/auditor.stdout) record both
processes, charged bootstrap/config bytes, read traps and scientific counters.
Parent/worker data reads are0/7 fabricated files and0/0 real files per command.

The full24-row artificial matrix and independent proof agree:1248 event visits,
648 descriptors (432 checkpoints +216 comparisons),528 aliases and36 norm slots.
Complete charged source inventory is3,894,481 bytes/process, including7143 bytes
of bootstrap/configuration; limit4,194,304. Producer output386,871 bytes and audit752
bytes total387,623; combined limit1,048,576 with65,536 bytes reserved for the audit.
External producer/auditor durations are0.214605959/0.211662958 s, below30 s each.
Inherited raw report stage remains `R5.59r`, explicitly artificial scope;
this qualification is R5.59t, not a retained R5.59s result.
The [summary](experiments/0232-qualification/artificial-summary.json),
[saved proof](experiments/0232-qualification/artificial-audit.json) and
[independent read-only review](experiments/0232-qualification/independent-review.json)
agree. The reproducible fixture recipe and all source/data pins are retained;
the3.7 MB fabricated inputs are not duplicated in Git.

17 new cases cover exact command paths, early malformed/truncated/extra-argument
refusals without data reads, immutable evidence/exclusivity, owned-marker cleanup
after a late child failure, unchanged artificial aliases, fixed production profile
and the two-edit source boundary. Combined focused tests:87 passed in9.43 s.
Frozen guarded full suite:6665 passed/494 skipped in174.63 s;
Ruff and strict OpenSpec pass. The inherited offline guard explicitly excludes
native/SPICE/live-UI and selected retained force/replay tests; this is not an
unrestricted full-suite result. Older artificial scientific tests still execute.
Zero scientific/native/SPICE/integration/replay counters apply to the new
qualification commands, not to every old regression test.

The immutable0229 contract and13 raw pins, all six0230 qualified source/test hashes,
ADR0231 failure evidence and `moon_to_mars.py` remain unchanged. Both fixed real
output paths remain absent. R5.59s is still consumed/unchecked; no numerical
historical readback, SPICE, integration or R5.60 was launched. Attribution and
physical feasibility remain unresolved; automation stays PAUSED pending a distinct
execution decision. Full [verification manifest](experiments/0232-verification.json).
