# 0121 — Prepare the independent elliptic benchmark

Date: 2026-10-30
Decision status: accepted (user accepted ADR 0120 and requested preparation).
Implementation: R1.2b preparation verified; native comparison R1.2c not executed.
Scope / milestone: private evidence tooling only; R1.2 scientific gate remains open.
Base revision: `5fb0de86bba2a6212c8b948d94218e6d59fa02b0`, clean before preparation.
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
Supersedes / Superseded by: none; implements the accepted [0120 contract](0120-independent-elliptic-coast-benchmark.md).

## Context and constraints

Prepare the independent oracle and its evidence guards without prematurely
launching the benchmark. The accepted contract freezes the case, 17 epochs,
1 m/1e-6 m/s comparisons, root/invariant gates and cooperative 30 s budget.
Native execution needs a separate instruction after this preparation passes.

## Options considered

- Modify the production coast adapter or add an oracle framework: reject;
  this fixed synthetic check needs neither a new engine nor public API.
- A private standard-library script with native-free pytest coverage: selected.
  Reuse the existing adapter only in the separately authorized execution path.

## Decision and rationale

The [private script](experiments/0121-elliptic-coast.py) implements the independent
eccentric-anomaly bisection and differentiated Cartesian equations without Tudat,
SPICE or production conversion/propagation calls in its oracle. It preserves the
literal initial six-state, GM, basis and rounded-epoch elapsed times from ADR 0120.
Periapsis/apoapsis/recurrence closed forms self-check it before any native launch.

Execution is explicit `--execute`, never an import/default action. On later
authorization it will reserve a new evidence file exclusively, verify frozen
source/reference/environment identity and native versions/build paths/binary
hashes, then compare at most 17 existing-adapter calls in epoch order. No SPICE
requests, planner searches, sampler calls or native retries are introduced.
The reserved result is `experiments/0122-elliptic-coast.json`; it does not exist
at this preparation stage. A later execution record will use the next unused ADR.

The script records attempted/completed calls separately, raw oracle/native states,
root diagnostics, signed component differences/norms, conservation errors and
before/after provenance. First failure stops the study. Returned data is captured
before the post-call deadline check. Malformed/nonfinite native data is explicitly
tagged for finite JSON, not silently replaced with zero. Mass is not modelled.

## Consequences and revisit conditions

Preparation does not pass R1.2 or validate Tudat/real trajectories. Mock-adapter
equality is only a test of the schedule/guards, never independent physical evidence.
The real native import/build/propagation path has not run; unavailable resources
or a numerical failure must be retained honestly without a retry or changed case.
After a separate execution instruction, run once under ADR 0120, retain and audit
the result. No R1.3 exporter, finite-burn/M3/M6 claim or automation restart.

Production source, environment, public interfaces, examples and old scientific
artifacts remain unchanged. This is research evidence tooling, not a production
implementation completion or a waiver of the eventual full-regression gates.

## Evidence and verification

- [51 native-free pytest cases](../../tests/test_r1_elliptic_benchmark.py) pass:
  closed forms including a distinct E=pi/2 point, all 17 roots/vis-viva/plane checks,
  time/shape/bool/nonfinite rejection, root/rotation failures, inclusive numerical
  gates and vector angular momentum, exact rounded-time/17-call mock schedule,
  first/partial mismatch stops, failed-call accounting, expiry/overrun/final-timing evidence,
  changed/missing provenance, binary-path fallback, version rejection, native
  domain-error translation and exclusive output/no recomputation.
- Import guards forbid real TudatPy/SpiceyPy in these tests; fake modules exercise
  provenance without compiled libraries. Fake results are not retained as a study.
- Prepared script SHA256: `ed02d1299b646cff0686c474b67668dcff5e63f99b3c2fd69b72b7f8abb235bd`;
  test module SHA256: `c5314ce26d7c561da7345c90d10fb28212841e0aa9ef4c74c841c909c26df17d`.
- `--self-test` passes three independent closed-form cases with zero native calls.
- Ruff, strict OpenSpec, local links, diff/scope and immutable source/evidence/
  legacy checks pass. Installed wrapper sources and Conda metadata paths were
  inspected read-only; no native modules were loaded to inspect them.
- Full regression suite **not rerun**: this accepted preparation explicitly excludes
  native launches, while the full suite contains them. Existing production/tests
  are unchanged; only this new isolated test module was added. Full regressions
  remain required at production/R1.4 implementation completion.

No `--execute` invocation, native state pairs, benchmark JSON or scientific pass
is claimed. R1.2c and the parent R1.2 gate remain unchecked.
