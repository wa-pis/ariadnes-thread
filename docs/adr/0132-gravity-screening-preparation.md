# 0132 — Prepare the fixed-epoch gravity diagnostic

Date: 2026-11-01
Decision status: accepted implementation of ADR0131 under bounded autonomous continuation.
Implementation: private calculator/runner/audit and84 new tests implemented; full regression verified; preparation complete.
Scope / milestone: R3.2 private preparation in active M3; R3.3 not executed.
Base revision: `629f53f3a9258d4ed7f35292c8cbcaba2a8f79a7`, clean before preparation; new files untracked during verification.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/omitted-gravity-screening/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [ADR0131](0131-screen-omitted-gravity-at-fixed-epochs.md) without changing its bodies, epochs, domains, arithmetic gates or execution limits.

## Context and constraints

The autonomous schedule authorizes preparation of the next specified diagnostic.
R1/R2 retain their declared ideal Sun-only scope. The next question is local
Earth/Moon/Mars differential gravity at exactly three saved epochs, with explicitly
inadmissible lunar/Martian body-centre endpoint terms; no new spacecraft states,
search, force integration, optimizer, mission-safety or full-force claim is made.

## Options considered

- Duplicate the previous native identity/budget infrastructure: rejected; it is
  already frozen and tested, and is unrelated to the new force oracle.
- Import production propagation/force helpers as an independent reference: rejected.
- Reuse immutable R2 validation, identity and cooperative-budget utilities, while
  implementing binary64 gravity and independent Decimal equations separately:
  selected. No production module, dependency or public API changes are needed.

## Implementation and rationale

[The private runner](experiments/0132-gravity-screen.py) checks the immutable R2
utility digest before loading it without scientific imports. It binds the two
frozen original/R2 evidence files, exact three epochs/spacecraft/Sun records and
retained endpoint bodies/GM. Its native boundary calls only the specified exact-
TDB body provider and Earth-GM provider; these are prepared, not exercised against
native resources in the new screening during this stage. Existing package native
boundaries are covered by full regression, not a new R3 observation.

Binary64 direct and indirect inverse-cube vectors are computed independently of
[the Decimal oracle/offline audit](experiments/0132-gravity-audit.py), which uses
80-digit unit-vector/squared-distance arithmetic. Evaluated terms are retained
before the independent arithmetic gate. Inside/on exclusion spheres the field
is absent, with a reason; it is never zeroed or clipped. The middle sample needs
all three admitted terms; endpoints have no three-body total. Individual vectors,
solar ratios, vector sum and sum of norms preserve cancellation information.

The separate audit does not import the runner or native libraries. It recomputes
Decimal components, domain classifications, norms, sums and ratios, checks exact
acquisition/counter/time and input identities, and handles unavailable/partial
results without certifying screening. File mode checks the actual frozen source
records and live prepared/native binary digests without new native queries.
It is an arithmetic/provenance audit, not independent ephemeris truth or a signature.

The shared30s budget, exclusive new output, fresh-process guard, before/after
identities and first-error stop remain as specified. Seven state requests and
one Earth-GM request are separately capped and counted as attempted/returned.
Raw returned values survive deadline or validation failures; non-preemptible
flush/call overruns remain failures. The elapsed field is a pre-flush sample;
the additional post-flush gate checks finalization, without claiming an exact
post-flush timestamp. No R3 `--execute` command has been issued.

## Evidence and verification

[Tests](../../tests/test_r3_gravity_screen.py) contain84 new native-free cases:
closed-form10/9 acceleration, axes/sign/tilted rotation, frame translation,
small differential cancellation, guard boundaries, endpoint/middle admission,
GM/metadata/epoch/frame/shape/nonfinite/bool failures, wrong indirect term,
resource/source identity drift, every acquisition failure/order/count, returned
partial data, setup/GM/state/final-identity/flush deadlines, exclusive output,
fresh-process guard, native error translation with fake providers, no scientific
imports in a fresh subprocess, and corrupted/partial offline evidence.

- Focused R3+R2 preparation checks: **170 passed in1.98s**, after all code changes.
- Ruff over src/tests and the new scripts passes; strict OpenSpec passes.
- A failed preparation test exposed a missing-Earth-GM path in the offline audit.
  It was corrected without altering any scientific gate. An inadvertently started
  full run was deliberately interrupted after695 passes/28.62s while that focused
  failure was being fixed; exit2/KeyboardInterrupt is not passing evidence.
  The final full regression was started only after all170 focused checks passed.
- Final full regression: **4936 passed in616.00s (0:10:16)**, exit0;
  [actual terminal log](experiments/0132-full-pytest.txt) and
  [machine-readable checks](experiments/0132-preparation-checks.json) retained.
  Existing native regressions are included and query counts were not instrumented.
  No native R3 screening has run.

Prepared source SHA256:

- Runner: `febc1e7728ac834895bb0daa65a4e2137ff91231e9f7f90453e5aecf615fbab3`.
- Oracle/audit: `47d03f269d8ab9774d87416c31af39bdc25e5661b857c97437862cbe5460759d`.
- Tests: `3023a6ec834b1d3b5566472efc377d8a3d4b51f1149554b751e9354ceabedacf`.

Final scope/link/diff/JSON/digest and immutable checks pass; 164 local links
resolve and 232 previously tracked protected files are unchanged. No scientific gate changed.

## Consequences and revisit conditions

R3.2 preparation is complete: declared checks, including full regression, pass.
A later autonomous step may run exactly one frozen R3.3 screening
and retain its independent audit. Expected endpoint inadmissibility is not a
scientific failure; unsupported middle-domain/resources/arithmetic require the
frozen fail-stop policy. A changed contract or required user action pauses the
automation instead of triggering retries or silent model changes.

Even a successful screening would quantify only Earth/Moon/Mars at three epochs.
It cannot bound other bodies/forces, integrated error or continuous safety, nor
establish finite-radius escape/capture, finite burns, UI qualification or strict
M3/task3.9/M6 completion. Preserve all previous evidence and the legacy model.
