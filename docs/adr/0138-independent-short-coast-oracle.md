# 0138 — Prepare the independent short-coast oracle first

Date: 2026-11-01
Decision status: accepted preparation split under ADR0137; no scientific contract change.
Implementation: R5.2a independent oracle and54 tests implemented; 54 new/224 focused and4990 full tests pass after documented provenance drift. R5.2 overall remains incomplete.
Scope / milestone: private R5 preparation in M3; no reference execution or production change.
Base revision: `05b5d87e222fe1a825fbc2ca18565595267ade72`, clean initially; new oracle/tests untracked during verification.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements only the independent-oracle portion of [ADR0137](0137-short-coast-earth-gravity-contract.md).

## Context and constraints

R5 needs independent native/oracle paths, orchestration, provenance and an offline
auditor. Complete one verifiable unit first, preserving the frozen scientific
input/profile/gate/budget contract. No reference study may start before all
preparation is verified; this split does not waive remaining R5.2 requirements.

## Options considered

- Build all adapters before any verification: defer; unnecessarily large review unit.
- Reuse the production acceleration/propagation helper in the oracle: reject;
  would compromise the specified numerical independence.
- Prepare a lazy private oracle with analytic and boundary checks first: selected.

## Implementation and rationale

[The oracle](experiments/0138-short-coast-oracle.py) imports only the standard
library at module load. Its low-level correction-coordinate solver supports
closed-form fixtures; the R5-facing wrapper fixes A/B direct gravity, body order,
GM,300s/seven-node profiles and all three body guards. Runtime force/propagation
code imports no space_nav or Tudat implementation. SpiceyPy direct SSB/J2000/NONE
queries explicitly convert km/km/s; source metadata and finite nonboolean SI
values are checked, including unit-conversion overflow.

A shared context enforces10000 RHS and30021 Python-query caps across future
solves/node acquisition, with attempted/completed counts, checked-distance
minima and last-returned raw data preserved before after-call deadlines. A
returned solve failing its final deadline/sample/finite/initial gates carries
raw arrays in a dedicated exception. The future runner must retain these failures
and supply its shared60s deadline, solve ordering/counts and identity/evidence
policy. The low-level solver alone is not a compliant R5 reference runner.

Output sample times are monotonic; adaptive DOP853 internal stage calls may be
nonmonotonic after rejected steps/interpolation. They remain checked within the
frozen interval. This clarifies time validation, without changing epochs or the
method. Fixed settings, correction reconstruction and actual solver outputs are
exposed for testing. Unsupported binary64 squared-distance/strength ranges fail
rather than silently returning a fabricated zero force.

## Evidence and verification

[The54 new tests](../../tests/test_r5_short_coast_oracle.py) cover analytic direct
acceleration (explicitly rejecting an implicit indirect-origin field), translated/
rotated/multiple-source fixtures, circular-orbit and zero-force linear-motion
SciPy solves, frozen tolerances, body/time/frame/shape/numeric/domain failures,
shared counters, provider/deadline errors, raw-data retention, solver failure,
corrupted initial/sample/nonfinite outputs, lazy imports and exact-TDB/SI wiring.
The two synthetic circular profiles agree with independent closed-form positions
within1e-6m and velocities within1e-8m/s; neither uses the R5 initial state.
A real Moon/J2000-time-zero SPICE boundary check agrees with direct Tudat within
0.001m/1e-6m/s. It performs two state reads per invocation, not a propagation;
previous focused runs also included it. Full-suite native counts are not instrumented.

An initial synthetic A/B subtraction test failed because its large solar term
made the tiny difference poorly conditioned at the test's1e-16m/s^2 gate. The
fixture geometry was changed to a well-conditioned synthetic distance, retaining
that exact absolute gate and setting rel=0 explicitly. No R5 scientific input,
force model or tolerance changed and no reference experiment was attempted.

- First focused iteration:1 failed/43 passed in4.47s, corrected as above.
- Final focused new+R3+R2 checks:224 passed in3.18s after all code changes.
- Ruff over src/tests/new oracle and strict OpenSpec pass.
- The first full run completed with1 failed/4989 passed in677.10s, exit1.
  [Actual log](experiments/0138-provenance-drift-pytest.txt) and
  [failure context](experiments/0138-provenance-drift-regression.json) retained.
  At11:34:09 the agent created this untracked ADR while the UI provenance test
  was searching; its captured failure timestamp is11:34:09.014. Existing source
  identity includes `git status --short`, so the protection correctly rejected
  changing workspace identity before the test reached its intended assertion.
  No code or scientific result changed. This was an avoidable verification-process
  mistake, not a scientific R5 failure. Repeat the affected test and full suite
  with all workspace mutations suspended; do not bypass the identity guard.
  The affected unchanged test then passed once in3.11s on the stable workspace.

Prepared SHA256 (untracked during checks):

- Oracle: `d6a624f727e17de364f188f0941f2e1889741204ad035aefd9263728cf95e029`.
- Tests: `ee9611b32c3207f15f9b0e426c9b283f69452943a6a36da212f4387f1357204a`.

The stable-workspace full repeat passed4990 tests in671.36s, exit0; Git status
was byte-identical before/after. See the [actual log](experiments/0138-full-pytest.txt)
and [check summary](experiments/0138-oracle-preparation-checks.json), including
exact source/log hashes. All241 previously tracked files under src/tests/examples/
experiments plus environment.yml and moon_to_mars.py match the base byte-for-byte.
Only R5.2a is verified; the parent R5.2 remains incomplete. Documentation updates
after this pass do not alter the verified oracle/tests; full pytest is not repeated
for prose-only changes.

## Consequences and revisit conditions

The oracle unit is not R5.2 completion. Next prepare the independent Tudat adapter,
shared runner/identities and separate saved-evidence audit, then complete relevant
checks before one R5.3. Native RK4 settings, body systems, inventory/GM checks,
exclusive output/finalization and full orchestration remain unimplemented here.
No public API, dependency, mission state/control or production force model changed.
Numerical/reference/sensitivity gates stay separate from mission accuracy and
continuous safety; strict M3/task3.9/M6 remain open.
