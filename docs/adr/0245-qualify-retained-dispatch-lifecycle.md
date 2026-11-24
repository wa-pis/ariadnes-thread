# 0245 — Qualify the retained dispatch lifecycle on fabricated archives

Date: 2026-11-24 (Europe/Samara)
Decision status: accepted
Implementation: dispatcher and candidate binding implemented; full P5 qualification pending
Verification:53 synthetic cases,7051 portable and412 live pass; Ruff/review/strict pass; CI pending; no saved attempt
Scope / milestone: remaining P5 preparation inside active M3
Base revision: `376015224484a3739852d86cbab1ff3d0c3ef949`, clean `dev` before this stage
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-use-bounded-scalar-search-only-to-propose-an-analytical-witness), [design](../../openspec/changes/refine-physical-trajectory/design.md#p4-one-retained-bounded-attempt-2026-11-24), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md)
Supersedes / Superseded by: none; implements ADR0243 under the standing authority recorded in ADR0244

## Context and constraints

[ADR0244](0244-start-bounded-autonomous-preparation.md) qualifies the isolated
point-identity version. It does not qualify the retained dispatcher. The user's
selected objective is one admissible analytical pair with independent audit on
fixed saved inputs; no probability or physical-closure percentage is claimed.
The standing instruction authorizes completing P5 and, only after qualification,
one unchanged ADR0243 P6. The four inputs, scientific gates, runtime tables,
129-phase work envelope, time/byte ceilings and terminal stop policy stay fixed.

Hypothesis: a versioned parent/worker lifecycle can reuse the qualified numerical
helpers and independent point/trace audit, with authenticated complete witness
and complete inconclusive outcomes, while preserving all original bounds. This
is a preparation hypothesis, not a claim that a saved admissible pair exists.

## Options considered

- Alter the completed artificial invocation or relabel its profiles: rejected;
  this would change historical evidence and blur the execution boundary.
- Add another numerical solver or repeat a retained diagnostic: rejected; neither
  is needed to qualify the already selected method.
- Add one private versioned dispatcher, reusing the existing numerical and runtime
  helpers: selected. Exercise the same lifecycle with fabricated archives before
  admitting the fixed retained route.

## Decision and rationale

Implement `experiments/0245-retained-invocation.py` around unchanged 0241 search,
trace/runtime, 0220 archive/anchor helpers and the qualified 0244 point adapter.
The parent performs structural authentication only; numerical point/oracle work
belongs to separate isolated producer/auditor processes. The no-argument retained
route fixes the four original roles, qualified binding and exclusive namespace.
An external artificial route exercises the same lifecycle on fabricated files;
it supplies no execution authority for saved data.

Reuse only the exact runtime subobjects from the immutable 0242 local profiles
for retained readiness. Freeze new source/configuration bindings after synthetic
qualification without a self-hash cycle or automatic runtime regeneration. Keep
original profile metadata, including artificial-bootstrap identity, historical.
Use a fixed `0245-readiness.json` qualification receipt to pin the raw
`0245-binding.json` without embedding a circular self-hash in the dispatcher.
Create that receipt only after all P5 checks pass. Missing/unqualified readiness
refuses before creating the fixed attempt namespace; no caller environment or
CLI override supplies a readiness pin.
Ordinary portable qualification may use the existing artificial profile harness
on its own platform; that never migrates the fixed retained runtime tables.

Charge startup, every source/configuration/input reread and final structural
readback to its reader. The inherited runtime Guard exempts own-output reads,
so finalization/readback needs explicit accounting. Start the producer parent
clock before reservation/bootstrap; preserve late/partial bytes rather than
copying the old launcher's completion deletion. Audit exactly once after a complete
authenticated producer exit0 or2; never after a partial chain. Retain the existing
4096-byte launcher, producer remainder, 64KiB audit and combined4MiB allocations.

Focused qualification budget: at most six successful cold synthetic pipelines
and24 negative/auxiliary cold commands, with the unchanged30s producer and separate
30s audit limits;15min focused wall budget. Test full129phase output and at least
1,065,958B raw fabricated inputs, not just a small metadata inventory. Pure
fault-injection tests cover deadline/partial/cap boundaries without real science.
Required ordinary regression/CI checks are separate verification, not saved
attempts. Repeating a check requires a relevant source fix or unresolved failure;
no real data are used for buffer sizing or tuning.

## Consequences and revisit conditions

P5 stays incomplete until cold command forms, fixed identities, role-specific raw
encoding, independent witness/inconclusive audit, tampering, failure consumption,
all time/read/output/runtime caps, full-volume synthetic work, required frozen
regression lanes, Ruff, independent review and strict OpenSpec pass. Preserve
all1052 pre-existing non-Markdown files. No preparation command creates the fixed
`0243-p3-retained/` namespace or evaluates saved scientific operands.

A runtime artifact outside the fixed table or an inability to meet the declared
contract leaves retained readiness unavailable. Do not raise caps, weaken gates,
retry saved work or claim continuous refusal. A real terminal outcome belongs to
P6 after full qualification; automation pauses on that outcome or required user
involvement. M3, executable admission, original R5.60 and mission safety stay open.

## Evidence and verification

The versioned dispatcher and [candidate binding](experiments/0245-binding.json)
are implemented. All53 final synthetic tests pass. The first candidate had48
passes and two stale test-interception failures; repaired interception tests pass
and the final source is qualified separately. Preserve those initial results.
The full129phase case reads1,065,959B of fabricated input, with360 metadata rows
and720 signed input pairs, then produces788,688B of combined process evidence.
Producer charged source/readback:2,920,709B; auditor:2,360,056B. Both exact local
runtime subobjects match0242 and the independent audit makes zero optimizer calls.
These are artificial resource/lifecycle observations, not real feasibility.

The first full portable lane then exposed three parent-process test-seam failures:
7,048 cases passed,42 archival checks skipped, and the direct stdlib-only Guard
constructor rejected NumPy/SciPy already imported by earlier tests. No dispatcher
or scientific arithmetic failed. The three shared read-accounting checks now
permit the already loaded scientific packages, deliberately register fabricated
preloaded-module metadata, and assert startup artifact accounting before testing
the unchanged cumulative4MiB boundary. All three repaired offline cases pass;
production source, runtime tables and caps are unchanged. Preserve the failed full
lane and its frozen-checkout proof. The earlier non-live invocation without the
required offline guard was interrupted and is not qualifying evidence.

The immutable [local preparation](experiments/0245-preparation.json) and
[synthetic observations](experiments/0245-synthetic-observations.json) retain the
source/test hashes, full-volume metrics and separate successful/failed logs.
After the test-seam repair, required portable regression passes7,051 cases with42
archival skips in195.13s; live regression passes412 in579.98s. All7,505 case IDs
are unique across disjoint lanes, with7,463 passes and42 unverified archival cases.
The same1,359 Git-visible files, HEAD and Git status remain byte-identical across
both lanes. All1,052 pre-existing non-Markdown files remain unchanged. Independent
review, Ruff and strict OpenSpec pass. CI remains required before P5 completion
and readiness; no receipt or fixed retained namespace exists at this recording.

Original scientific sources/evidence remain unchanged; no new retained search or
mission trajectory calculation is part of this preparation. The ordinary existing
live regression did use SPICE/native resources and is separately counted. These
successful tests qualify implementation behavior, not the existence of a saved
admissible pair, physical closure, strict M3 or a99%probability.

The verbatim initial-focused and first-portable failure logs retain22 original
trailing-whitespace rows from pytest tracebacks. Whitespace checking excludes
only those raw logs; changed code, tests and prose pass. Their recorded raw hashes
are preserved rather than normalizing evidence after the fact.
