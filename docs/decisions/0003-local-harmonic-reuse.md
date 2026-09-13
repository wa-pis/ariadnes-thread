# 0003 — Reuse exact harmonic errors within one inventory

Date: 2026-09-13. Milestone: M3, task 3.9.

Status: accepted and verified bounded implementation; M3 remains incomplete.

## Context and decision

[0001](0001-inventory-runtime-investigation.md) identified expensive exact
arithmetic; [0002](0002-exact-harmonic-input-duplicate.md) established a duplicate.
Reuse successful exact-input harmonic error results only within one inventory
invocation. Retain exact Fraction arithmetic, all native controls and the 300 s
deadline. A global cache, weaker tolerances and new dependencies remain unnecessary.

The key contains both scalar binary64 representations and every array's shape,
dtype and bytes. Successful keys retain the unchanged oracle's input validation;
invalid or expired calculations are not inserted. Immutable entries and fresh
returned dicts prevent caller mutations from changing subsequent results. Budget
checks also run for hits. No SPICE queries, production dynamics or scientific
parameters were replaced.

## Verification and provenance

Base: `d964ed8`, pinned Conda `space-nav` environment. This commit contains the
measured reuse code and the previously unfinished midpoint unit. See
[retained results](../../tests/data/m3_harmonic_reuse_verification.json).

- 735 focused checks passed in 0.77 s, including 19 reuse checks and 35 midpoint
  checks. Reuse agrees exactly with the uncached oracle, has an independent
  monopole control, misses for every changed dependency, rejects invalid input,
  isolates mutations and preserves deadline failure on hits and completed misses.
- Full pytest: 2823 passed in 444.18 s. Native inventory: 135.28 s, 14 requests,
  4 uncached evaluations, 10 hits, all 13 native arcs. Portable inventory:
  38.85 s with zero requests and arcs. Existing scientific assertions pass.
- Ruff, strict OpenSpec validation and legacy-file isolation pass.
- An earlier development run was intentionally interrupted after review found a
  misplaced test decorator (1611 passed in 104.87 s before interruption). The
  decorator was restored, all four original cases passed, then the complete run
  above passed. This is not hidden or counted as a scientific deadline failure.

Reproduce the complete check from the repository root:

```sh
conda run -n space-nav python -m pytest -q --tb=short --durations=5 -p no:cacheprovider
```

The measured run additionally enabled JUnit logging to a temporary XML file to
extract captured request/hit counts. For visible counters, run the inventory
test explicitly with `-s`. The exact-input key uses no approximate hashing or
rounded comparisons. The uncached oracle and its existing controls remain.

## Interpretation and limits

Compared with the historical completed inventory time of 282.16 s and subsequent
300 s deadline failures, this run completes with substantial margin. It is not a
paired controlled benchmark or a guarantee against future machine-load changes.
The 10 eliminated evaluations establish actual reduced work; elapsed time remains
an empirical observation. Generator resumptions are not used as evaluation counts.

The midpoint whole-box error is 1.3558110579856195e-5 m/s^2, including its already
expanded tail and midpoint rounding. This is a stored-geometry Euclidean bound,
not a source/PCK, full-force, stage-safety or mission certificate. See the
[design contract](../../openspec/changes/refine-physical-trajectory/design.md).

## Next step

WHEN the existing isolated degree100 evaluation provides exact prefix intervals
and its exact separate tail, THEN apply the verified midpoint formula with the
tail counted once and verify consistency with the conservative whole-box bound.
Do not subtract a rounded JSON tail, add native arcs or evaluate degree120.
All other task3.9 and finite-burn prerequisites remain open.
