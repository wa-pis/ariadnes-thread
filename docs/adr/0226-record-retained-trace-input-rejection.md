# 0226 — Preserve the retained trace dispatch rejected on historical JSON encoding

- Date: 2026-11-20 (Europe/Samara).
- Decision status: accepted preservation of the first failed dispatch; no retry, adapter repair or scientific change authorized by this record.
- Implementation: the qualified R5.59m code is unchanged. R5.59n dispatch is consumed; retained observation and separate-audit verification remain incomplete.
- Scope / milestone: R5.59n, M3 diagnostic of the fixed local Mars surrogate.
- Measured base revision: `30b143c046be24b96e4358f826d1ae4cd86b9bd3`, clean synchronized `dev`; no checkout changes before the dispatch.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-observe-fixed-retained-phase-cells-without-rescanning), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559n-first-dispatch-rejected-on-historical-json-encoding-2026-11-20), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0224](0224-design-retained-cell-observations.md), its immutable contract, [ADR0225](0225-qualify-retained-cell-observation-adapter.md) and all historical evidence retain their original scopes.

## Context and constraints

On 2026-11-20 the user explicitly enabled the proposed single R5.59n retained diagnostic and separate saved-only audit. Git, process inspection, qualified source hashes, nine input byte hashes and the absent fixed output paths were checked first. No competing calculation or tests were running. The existing qualified outer dispatcher was invoked exactly once through pinned Conda Python 3.12.14 with `-I -S -B`. The shared 30 s clock, fixed paths, formulas, cells and caps were unchanged.

## Observed result

The producer dispatcher returned **3**. Its exact stderr was:

```text
R5.59m: study_audit canonical record
```

External elapsed time was **0.181515250 s**; the dispatcher's own elapsed time was **0.168107791 s**. This is an input-admission failure, with no retained observation result. No fixed output directory, attempt, report, receipt or completion was created. The separate auditor was not invoked because no producer completion exists. The authorized dispatch is consumed despite the absent output path; it must not be automatically retried.

## Diagnosis and evidence

[The loader](experiments/0225-retained-trace.py) authenticates each raw file hash before requiring its bytes to equal either compact sorted JSON with a newline or sorted two-space-indented JSON with a newline. The ninth role, `study_audit`, is the unchanged [ADR0221 independent audit](experiments/0221-independent-audit.json): **616,362 bytes**, SHA256 `0f874ca92231b8b1c43069a158bb7f698ef2758954f2a8ba278511f9391fdc82`, exactly matching the frozen contract. Its bytes equal sorted single-line JSON with the default spaced separators (`: ` and `, `) plus a newline. That third historical encoding is not admitted by this loader.

The [read-only encoding inspection](experiments/0226-failed-retained-dispatch/source-encoding-inspection.json) verifies all nine original hashes and byte counts, totaling 2,280,855 bytes. Seven files use the accepted compact form, one uses accepted indentation, and the last uses the default-spaced form. The historical data were not altered, reserialized on disk, relabeled artificial or computationally replayed.

The failure is at `_inputs`' canonical-record check, before that function returns. Post-loop lineage and selected-row semantic checks were **not reached**. Output creation, saved-point `prepare_points`, oracle-mass arithmetic and every signed bound/control call occur later. Thus zero bounds, traces, new points and new mass values were reached. This conclusion follows from the exact error location and unchanged source control flow; there is no completed runtime work-counter artifact. No SPICE, propagation, integration, old scientific audit or R5.60 ran.

[The verification manifest](experiments/0226-verification.json) pins the unchanged qualified sources and preserves [dispatch metadata](experiments/0226-failed-retained-dispatch/dispatch.json), [external measurement](experiments/0226-failed-retained-dispatch/measurement.json), [stdout](experiments/0226-failed-retained-dispatch/producer-stdout.txt), [stderr](experiments/0226-failed-retained-dispatch/producer-stderr.txt) and [invocation-driver text](experiments/0226-failed-retained-dispatch/invocation-driver.txt). These new artifacts record the failed invocation without rewriting any historical input or creating a false completion witness. An independent read-only review agrees on the encoding mismatch and ordering; it performed no scientific functions or old audit replay.

## Options considered

- Reserialize the old audit, bypass the input check or rerun immediately: rejected. It would change frozen evidence, conceal the admission failure or exceed the at-most-once instruction.
- Preserve the first failure and pause: selected under ADR0224.
- A new versioned adapter recognizing this exact encoding for the affected historical role: recommended for a separate repair design and artificial qualification. Raw SHA authentication and existing finite/numeric/schema gates must remain. Include fabricated archives matching all nine historical encoding profiles and malformed/duplicate/nonfinite rejection, followed by a read-only metadata preflight. This is a proposed next step, not an implemented repair or authorization to dispatch again.

## Decision and rationale

Record the failed attempt and its small technical cause before changing any code. The artificial qualification exercised archive volume and matrix behavior but did not reproduce every historical input serialization. Its passing tests remain valid for that scope and do not establish successful admission of the real archive. Retain this distinction rather than weakening the input gate after seeing a failure.

Automation `ariadna-m3` was immediately set to **PAUSED**. A separate user decision is needed on the proposed compatibility repair and its verification; any subsequent retained dispatch requires separately stated authorization. Neither an absent attempt directory nor an unchanged scientific formula makes this dispatch unused.

## Evidence and verification

Raw input/source hashes, finite JSON, exact serialization comparison, local links, unchanged historical/runtime/test/legacy bytes, staged diff and strict OpenSpec are checked for this evidence-only stage. No runtime or test code changed. Reuse ADR0225's 38 focused / 6,560 guarded full passes, 494 exclusions and Ruff result; no pytest or scientific calculation is repeated. R5.59n remains unchecked because its 24-trace, containment, width and separate-audit criteria were not met. This record is a verified failure report, not a passing implementation or science gate.

## Consequences and revisit conditions

The observed blocker is the adapter's encoding policy for a correctly hash-pinned historical file. Retained interval widening has still not been observed internally; no numerical attribution, continuous refusal, admissible command pair, physical continuity, M3 completion or mission safety is established. Revisit after a separately accepted encoding-compatibility repair and artificial verification, preserving this consumed first-dispatch record and all original bytes/caps. Do not repeat the producer or auditor in this stage.
