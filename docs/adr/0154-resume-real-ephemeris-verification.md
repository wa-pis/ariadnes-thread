# 0154 — Resume real ephemeris verification with unchanged limits

Date: 2026-11-04
Decision status: accepted under the user's explicit instruction to start again.
Implementation: exact four pending source/test files restored and verified;90 focused/5409 full tests pass.
Scientific status: real boundary acquisition eligible but unexecuted; no real-force/solve qualification.
Scope / milestone: M3 R5.8 preparation and the previously frozen source-only audit.
Base revision: `c3233fac0c3a35823fe7b4a9c730eba392e2fce2`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Follows [ADR0153](0153-real-ephemeris-time-boundary.md); supersedes no historical result.

## Context and constraints

ADR0153's90 new tests passed, but a pre-existing full-suite native-readback test
reached its300s deadline. The user now explicitly authorizes another launch.
The saved patch and all four exact source hashes match the retained manifest;
no scientific input, kernel, implementation byte or tolerance is revised.
Current1-minute load is15.73; background Tunnel CPU was243.2% at observation.
Contention remains possible, not proven causal; no outside process is altered.

## Options considered

- Raise/ignore deadlines, skip the old failing test or run real data before full
  verification: reject, would bypass the frozen prerequisite.
- Immediately repeat the entire suite: permitted but wastes work if the same
  deadline persists; prefer the single failed-node readiness check first.
- Restore exact bytes and frontload that same unchanged node: selected under the
  new user instruction; this is a bounded verification retry, not an R5 mission replay.

## Decision and bounded progression

Run exactly one readiness attempt of
`tests/test_trajectory_spk.py::test_loaded_spk_chain_coverage_contains_candidate_interval[native-readback]`,
keeping its original300s wall-clock budget and all assertions/native settings.
An outer360s watchdog only bounds process/import/cleanup overhead; it cannot
extend the test's scientific/runtime300s gate. If this fails, retain its evidence,
stop and keep R5.8 open without starting full pytest or the real-source audit.

If it passes, run90 focused tests, Ruff, strict OpenSpec and at most one complete
pytest suite with all original tests included (outer1800s process watchdog, no
changed per-test budget). Freeze all checkout mutations throughout native-readiness
and full pytest; retain live logs outside the repository and do not overlap work.
Failure at either gate remains failure; no hidden retry or successful subset claim.

Only after all preparation passes, execute once the exact ADR0153 seven-time,
three-body source audit, under its unchanged60s/21-state/28-selection/6-array-read
caps and original13 kernels. Then separately audit saved rows without native calls.
No R5 reference replay, spacecraft/force evaluation, optimizer or automation restart.

## Consequences and revisit conditions

A repeated deadline will require a separately justified performance/resource step;
no model/gate change is authorized by this record. A real-source pass still checks
only sampled arithmetic of the same ephemeris, preserving the source-position floor;
full-force, solver and mission/safety conclusions remain outside scope.

## Evidence and verification

Before execution: original protected files, patch hash and four restored source
hashes checked. Readiness passes once in132.76s under the unchanged300s test budget.
90 focused tests pass in0.20s; all5409 full tests pass in665.51s. Ruff and strict
OpenSpec pass. The115 historical experiment/legacy files and four new sources
remain byte-identical, and checkout status remained frozen throughout checks.
This addresses the verification prerequisite only, not a causal diagnosis of the
previous deadline. No new source-only study or R5 reference replay was executed.

[Verification manifest](experiments/0154-verification.json),
[exact commands](experiments/0154-verification-invocation.txt),
[readiness log](experiments/0154-readiness-pytest.txt),
[focused log](experiments/0154-focused-pytest.txt),
[full log](experiments/0154-full-pytest.txt).
The once-only real-source acquisition is the next separate verified stage,
under the unchanged ADR0153 contract; automation remains PAUSED.
