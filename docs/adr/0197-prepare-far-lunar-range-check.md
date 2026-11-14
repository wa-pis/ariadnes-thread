# 0197 — Prepare and capacity-check the far lunar range study

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted within [ADR0196](0196-design-far-lunar-range-check.md).
- Implementation: R5.50 complete; R5.51 unexecuted.
- Verification: full-work-cap artificial calculation and independent saved-data audit passed.
- Scope: private 16,000 s model B study, 18,374 km diagnostic marker and bounded evidence.
- Base revision: `ae10a3d17763bacc35fa481abd40ae54b193156e`; exact tested files in the verification manifest.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-the-18374-km-lunar-range-marker), [design](../../openspec/changes/refine-physical-trajectory/design.md#r550-prepare-and-capacity-check-the-far-lunar-range-study-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

The 50 s and 600 s helpers have frozen ranges and archival formats.
The far study must keep their force and comparison gates, preserve
the exact audited R5.48 terminal state, and make substantially more
evidence available for an independent replay. The original helpers,
scientific baselines and production settings remain immutable.

## Options considered

- Collect one JSON report per phase: all operands would be readable,
  but full-scale memory use and interruption recovery would be poor.
- Save summary values or digests alone: a later audit could not verify
  source, force, integration trace and range arithmetic independently.
- Keep lossless bounded shards and replay ordered records in an isolated
  stdlib process: selected. This permits small checked prefixes and
  exact readback without a second raw archive.

## Decision and rationale

Use private duration-aware study orchestration and new ordered, synced
shards with raw and compressed hashes, byte and row counts, and bound
phase and checkout receipts. Reuse the pinned force, source, clock,
native-history and reference arithmetic without altering their original
callers. Both scientific paths start from the same authenticated input
when reference mode is eventually authorized; opening and closing
attestations bind the runtime and ordered kernel metadata. The offline
audit replays saved operands, sampled native guards, force observations,
trial membership and decisions, state comparisons and exact direction
signs. A missing or late receipt, work limit, corrupt shard or partial
study cannot certify a marker; a committed prefix remains readable.

The capacity harness supplies artificial native histories and a scripted
adaptive controller with distinct callback epochs and source values.
It uses the real producer and independent replay arithmetic, with no
kernel queries or native solver. The 13,000 trial records include 3,020
rejections. The two complete profile traces supply 157,928 RHS rows;
2,072 separately labeled capacity rows bring arithmetic replay to
160,000 without falsifying the dense-output linkage. Reference mode
does not accept those rows. The 7,704 SPK evaluation limit is a ceiling;
the sampled artificial rows exercised 5,703 polynomial evaluations
per phase, without reading any kernel file.

## Evidence and verification

| Phase | Parent elapsed | Preparation threshold | Child peak RSS |
| --- | ---: | ---: | ---: |
| Artificial study and finalization | 36.9564 s | 360 s | 270.78 MiB |
| Independent offline audit and finalization | 39.2530 s | 225 s | 265.75 MiB |

The study reaches 785,296 explicit synthetic attempts (including
144,012 native guard substitutes), all 1,284 adaptive observations
and 642 native telemetry rows. The audit passed 963 state comparisons
and 49,286 direction rows. It independently found an outward bracket
on the fixture: common +12,150–12,200 s, native overlap +12,193–12,193.5 s.
The audit made zero native calls, kernel loads or propagations and
imported no scientific modules.

Storage and readback passed: 49 lossless shards, 814,839,524 raw bytes
and 225,105,514 compressed payload bytes combined. The retained local
directory is `/Users/agrudin/dev/my/ariadna-evidence/R5.50-verified`,
outside the checkout. Readback verified all 419,128 records, their
shard digests and bound receipts from a fresh process. The
[verification manifest](experiments/0197-verification.json) records
the path, phase manifest and receipt digests, measured budgets and
exact tested sources. Large shard files stay local.

31 focused tests and the full guarded suite (6,217 passed,
494 skipped) passed on the final source bytes. Ruff,
Strict OpenSpec, local links, diff, input hashes and unchanged
historical evidence passed. The [offline guard](experiments/0189/pytest-offline-guard.py.txt)
blocked native SPICE imports and loads during regression. Focused
cases cover negative and conflicting brackets, tampered operands,
storage and work caps, interrupted shards and receipt failures.

## Consequences and revisit conditions

Artificial timings establish capacity for the exercised workload.
They do not measure actual RK4/DOP853 convergence, ephemeris latency,
or physical attainment of the lunar marker. R5.51 is unexecuted and
requires a separate authorization bound to the prepared revision,
preparation digest and once-only evidence directory. Its 480 s and
300 s wall limits, restart, force model and acceptance gates are
unchanged. A resource or evidence failure does not authorize a replay.
