# 0223 — Qualify artificial interval-bound observations

- Date: 2026-11-18 (Europe/Samara).
- Decision status: accepted artificial-only implementation; no retained invocation or changed enclosure formula.
- Implementation: complete; verification is recorded below.
- Scope / milestone: R5.59k, M3 diagnostic preparation under [ADR0222](0222-diagnose-saved-positive-bound-widths.md).
- Base revision: `d7d60fa72700c63b9cc3c4fe30637a4c9621dfc0`; new runner, tracer, containment helper and tests were untracked during qualification. Exact tested hashes are retained in the verification manifest.
- Related OpenSpec: [scenario](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-diagnose-unresolved-enclosures-without-replay), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559j-saved-bound-diagnosis-and-r559k-artificial-tracing-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. The [ADR0218](0218-design-inter-node-mars-phase-check.md) method and [ADR0221](0221-record-retained-inter-node-result.md) consumed, inconclusive retained attempt are unchanged.

## Context and constraints

ADR0222 found broad arrival-norm bounds in the saved retained result, but no internal stage widths were saved. Inspecting its final lower mass bound cannot establish which operation dominates that width. The authorized preparation is to observe the existing method on its two fixed artificial fixtures before proposing any new proof or retained attempt.

Qualification must preserve the original arithmetic and thresholds, use the exact parent, child and singleton cells, compare both signs and both existing arithmetic paths, and contain the corresponding independent-oracle point quantities. Artificial observations cannot attribute a cause to different, retained operands.

## Options considered

- Modify or duplicate the scientific expressions to emit intermediate values: rejected for this observational step because the copied computation could diverge from the method under diagnosis.
- Observe calls and returns of the unchanged functions with `sys.setprofile`: selected. Isolated module instances, source pins, explicit stage validation and byte-for-byte final-record comparisons detect disconnected or altered observations.
- Instrument the retained study immediately: excluded by the current artificial-only contract; requires a separate reviewed decision.

## Decision and rationale

The private [runner](experiments/0223-artificial-trace.py) accepts no caller-provided reference or archive. It constructs only the two existing `witness`/`refusal` fixtures and verifies their full canonical reference hashes. A scope label alone is insufficient. Its isolated `-I -S -B` CLI restricts file access to pinned methods, its exclusive artificial evidence directory and required standard-library modules; it blocks scientific imports, native loading, network and subprocess access.

The [tracer](experiments/0223-bound-trace.py) records ordered calls/returns, canonical interval endpoints, parent links, geometry and normalization/root stages, impulse norms, mass, comparison durations and the original binary64 lower conversion. It additionally labels the nearest-binary64 image of observed duration endpoints as an observation. Early errors and non-reached stages remain explicit. It restores the previous profile hook on success and failure. Historical formulas and method files are unchanged.

The separate [containment helper](experiments/0223-trace-oracle.py) checks matching saved Decimal96 point quantities and designated duration conversions: 16 quantities per sampled point. It also preserves the existing binary64/oracle point-parity gates and links observed return ranges to downstream fields. It does not require a singleton oracle enclosure to contain separately rounded binary64 geometry. It does not independently reconstruct every root/clearance intermediate or prove an all-phase enclosure theorem. Its independence concerns the matching oracle arithmetic and saved readback; it is not an independent physical propagator.

All traced final results equal their untraced controls in canonical serialized bytes. A saved-only second process verifies the source identities, exact matrix, event structure, point-phase identities, containment and four-file receipt chain without new bound or point construction. Seals and hashes detect mutations relative to their supplied pins; they are not authenticity certificates against a malicious producer.

## Evidence and verification

The fixed matrix is two fixtures × three cells × two signs × two arithmetic paths: 24 traced records and 24 untraced controls. Cells are `[151°,152°]`, `[151°,151+1/32°]` and the child midpoint singleton `9665/64°`. Fixture anchors and extra sample points total 12 point constructions. There are 56 endpoint/midpoint containment records, each with 16 checked quantities.

[The verification manifest](experiments/0223-verification.json) records hashes, commands, timing boundaries and limitations. [The complete saved trace](experiments/0223-qualification/r559k-artificial-result/report.json) and its [attempt](experiments/0223-qualification/r559k-artificial-result/attempt.json), [receipt](experiments/0223-qualification/r559k-artificial-result/receipt.json) and [completion](experiments/0223-qualification/r559k-artificial-result/completion.json) are copied byte-for-byte from the final isolated qualification.

| Resource / result | Observed | Approved cap |
| --- | --- | --- |
| Signed bound calls, including controls | 48 | 64 |
| Point calls, including anchors | 12 | 32 |
| Emitted stage entries | 1,232 | 8,192 |
| Four-file durable evidence | 2,092,809 bytes | 4 MiB |
| Producer external invocation | 1.163318416 s | 30 s |
| Saved pre-completion-write elapsed | 1.065730041 s | 30 s |
| Separate saved-only readback, external | 0.116146833 s | 30 s |

The saved completion timestamp is pre-write timing. The runner separately checks its shared deadline after exclusive durable output and full readback; the external elapsed includes finalization and process overhead. Each readback has its own bounded check, with zero new conics, phases or interval calls. These times characterize this artificial matrix, not retained work or mission propagation.

[Tests](../../tests/test_artificial_bound_trace.py): 27 focused cases passed; the guarded complete suite passed 6,522 cases with 494 explicitly excluded cases in 143.73 s. Equality, transition/early failure, malformed/resealed events and missing stages, containment failure, changed pins, caller-payload/scope rejection, exclusive outputs and exhausted wall/work/event/byte caps are covered. Review found two readback issues before qualification: a completion file could survive a post-write failure, and a cache key could disagree with the point phase. Both were fixed and have regression coverage; finalization failures now remove the owned completion marker while preserving the earlier evidence files. The initial incomplete full regression was stopped for these fixes; it is not counted as a passing run.

Ruff, strict OpenSpec, finite JSON, new local links, source/evidence hashes, clean diff and historical-file immutability checks pass. Conda `space-nav` is authoritative. The full regression uses the existing guard which excludes native SPICE and specifically prohibited retained scientific evaluations; skipped cases are not new native verification. Production code, environment, historical methods/evidence and `moon_to_mars.py` remain unchanged.

## Consequences and revisit conditions

The tracer is qualified on the fixed artificial matrix only. It exposes the internal quantities without modifying the method, but does not establish the widening source for retained R5.59i. No off-grid witness, full-interval refusal, physical command pair or M3 closure follows. The 40.085 m/s retained question remains open.

The next consequential choice is whether to design a separately bounded **observational trace of retained operands**, or develop a different enclosure formula on artificial data. Recommend the former design first: freeze a minimal subset of the already saved cells, require unchanged-result parity, and retain stage widths before selecting a formula. This is a proposed direction, not authorization to replay R5.59i or start retained numerical work. Automation is paused at this boundary pending the user's choice. No SPICE, integration, retained replay or R5.60 was performed or enabled.
