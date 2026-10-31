# 0128 — Prepare the independent reference-coast verifier

Date: 2026-10-31
Decision status: accepted preparation under ADR0127; user instructed continuation after R2.1.
Implementation: R2.2 private verifier/audit and native-free tests complete; R2.3 not executed.
Scope / milestone: current R2 within active M3, retained ideal Sun-point-mass coast only.
Base revision: `b232154861dfe13f42f39c9eea4d8d9c94f327e1`, clean before this stage.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/reference-coast-verification/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [ADR0127](0127-reference-coast-verification-contract.md), preserving its equations and scientific gates.

## Context and constraints

The user requested the next stage after the detailed contract was presented.
This accepts preparation; it does not authorize the separately gated native
comparison. The old reference lacks the Sun track needed to recover the original
Sun-relative initial condition. Its actual admitted-domain membership and
all-node numerical agreement therefore remain unverified.

No native library was imported or queried in this stage. No new reference JSON,
planetary data, force model, dependency, production package or UI was introduced.
Existing experiment scripts/JSON, environment, examples and legacy model remain
unchanged. Automation remains paused.

## Options considered

- Extend the production dynamics backend: rejected; no runtime feature is needed.
- Reuse the synthetic fixed-periapsis oracle: rejected; actual initial phase and
  Cartesian seed must be independently recovered.
- Prepare a private stdlib-only evidence runner and a separately implemented
  arithmetic audit: selected. Reuse the existing exact-TDB Sun provider only at
  the future native boundary; do not reuse production propagation/conversion code.

## Decision and rationale

[The runner](experiments/0128-reference-coast.py) implements ADR0127's seed,
Cartesian-derived ellipse and initial phase, independent bisection, derivative
velocity, Sun-relative and SSB differences, and relative energy/vector-angular-
momentum checks. Initial fixtures use literal quadrant sine/cosine values;
forward-phase tests and the synthetic all-node control use independently
constructed expected states, including an independent Newton solver for that
control. Passing injected tests is preparation evidence, not physical validation.

The runner freezes reference/source identities, exact121-point grid, GM, units,
frames and ordered13-kernel manifest. Scientific imports remain lazy. Metadata
inspection found TudatPy and tudat-resources have no Python distribution metadata
in the pinned environment: their versions/builds are read from Conda JSON instead;
the TudatPy module version is also checked at the future native boundary.

An exclusive new file is reserved before native work; existing files are never
overwritten. CLI native execution requires a fresh process and explicit
`--execute NEW_OUTPUT`. One cooperative30s budget covers setup/scientific imports,
checks, at most121 exact-epoch Sun provider calls, comparisons, final identity
and evidence serialization/flush. First failure stops without retries. Attempted
and returned counts differ on provider exceptions; returned raw data is retained
before the after-call deadline check. A non-preemptible overrun is failed and
its failure evidence is rewritten in the already reserved file. The reported
elapsed sample precedes initial serialization; the post-flush gate also checks
the budget, so that sample alone is not evidence of bounded finalization.

[The separate audit](experiments/0128-audit-reference-coast.py) imports no runner
or native library. It recalculates seed/geometry/phase/root residual/state,
translations, signed differences, invariants and verdicts from retained operands;
checks call order/counts, manifests and complete-success gates; and handles
explicit partial failures without declaring the coast verified. File-mode audit
also checks the frozen original digest, current source/native binary identities
and runtime versions without making native calls. It is an arithmetic/provenance
audit, not a second independent planetary ephemeris or a tamper-proof signature.

## Evidence and verification

- **86 new native-free tests** cover eight tilted/prograde/retrograde initial
  phases, forward phases, half/full periods, root residuals, conservation,
  independent121-node control, both translations, malformed/nonfinite/boolean
  values, time/frame/units/grid/GM/selection/scenario errors, domain failure,
  kernel order/hash/count/version changes, source/runtime/Conda admission,
  first numeric failure, attempted/completed calls,122nd-point rejection,
  provider/initial/final/serialization deadline failures, exclusive output,
  fresh-process guard and corrupted/partial offline evidence.
- Combined new tests and the existing synthetic elliptic/OEM-reader preparation
  suites: **225 passed in0.82s** after all code changes; Ruff and strict OpenSpec pass.
- Subprocess preparation checks and an import guard assert no TudatPy, SpiceyPy,
  NumPy or SciPy imports; synthetic test providers never query ephemerides.
- No `--execute` command or actual-reference state comparison was run. The full
  native regression suite was not rerun: this bounded preparation is explicitly
  native-free and changes only private experiment scripts/tests/documentation.
  R1.4's4766-test full regression remains historical evidence, not a new result.

Prepared file SHA256 identities:

- Runner: `027d0b4e45f9ebd941249e427963e365fd7205f9594a96365a587eb0e8cd7e81`.
- Audit: `138d6c98b9f914dbcc7b26355e0e8c2019bece997f1d18b089a90b3cce095ad9`.
- Tests: `54b60754ff6647822efc27ae0f414664dd84022ef260399d8babf9db149eac06`.

Final checks pass: Ruff, strict OpenSpec, diff,153 local documentation links,
three prepared-file hashes and225 unchanged tracked protected files.
CURRENT_STATE remains under60 lines. Do not infer R2.3 success from preparation.

## Consequences and revisit conditions

R2.2 is ready for a separately instructed single native comparison and offline
audit, with the same contract/budget/tolerances. Native wiring is prepared but
not empirically exercised by this stage. Missing resources, uncovered epochs,
unsupported actual seed, numerical mismatch or overrun must be retained as
unavailable/failed evidence and reviewed; no automatic retry or tuning.

Even success would verify one retained ideal coast using shared authoritative
Sun states. It would not validate the Sun ephemeris, search optimality, finite
burns, lunar escape/capture, mass dynamics, mission safety or strict M3/M6.
