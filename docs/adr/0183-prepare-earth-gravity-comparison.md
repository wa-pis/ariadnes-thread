# 0183 — Prepare the Earth-gravity comparison

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted preparation under [ADR0182](0182-design-earth-gravity-sensitivity.md).
- Implementation: R5.36 complete in private experiment helpers.
- Verification: synthetic and archived-input checks passed; R5.37 not executed.
- Scope: R5.36 preparation of the restricted model B comparison.
- Base revision: `f52b989cb5e018585752ea79bb3098d49d7916d7`, clean synchronized `dev` at start.
- Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
  [design](../../openspec/changes/refine-physical-trajectory/design.md),
  [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

R5.34 passed the model A numerical check with Sun and Moon forces.
R5.36 prepares a future comparison that adds only direct Earth gravity
to the spacecraft. The saved A states and all input, tolerance,
profile, counter and timing limits from ADR0182 remain binding.

## Options considered

- Modify the existing research helpers in place: this changes the tested
  files pinned by historical evidence.
- Add a private B path that uses the immutable geometry, observer,
  native adapter and pure replay helpers where applicable: selected.
  This leaves production code and the historical paths unchanged.

## Decision and rationale

The [study](experiments/0183-earth-study.py) checks native RK4 B
profiles before the DOP853 B profiles. The
[DOP853 path](experiments/0183-earth-integrator.py) uses the same
four source routes, compensated motion and split Moon geometry;
Earth's existing guard geometry provides the operands for the
new direct acceleration. State and force operands are retained before
the subsequent validation and comparison steps.

The [native guard observer](experiments/0183-earth-native.py) captures
the states from the existing guard reads without acquiring them again.
The [native replay](experiments/0183-earth-native-replay.py) checks
those retained guards and validates the native node telemetry
using independent 80/100-digit direct fields. The
[sampled reference](experiments/0183-earth-reference.py) extends the
existing source and force checks to Earth and total B.

The independent [audit](experiments/0183-earth-audit.py) imports no
candidate force or solver code and reconstructs the checks from the
saved operands. It separately subtracts B and A states in each
engine and compares the resulting signed vectors. The
[input loader](experiments/0183-earth-inputs.py) binds the A archives
and R5.34 receipts. The [parent launcher](experiments/0183-earth-launch.py)
enforces exclusive phase attempts, source and checkout integrity,
deadlines and child/parent receipt digests.

## Evidence and verification

- The complete synthetic study and separate audit verified both DOP853
  B profiles, both native B stubs, 2,712 saved native guard reads, 14
  native telemetry rows, 28 sampled source/force observations, 21 B
  trajectory comparisons and seven signed effect rows.
- Tests also cover same-input Sun/Moon parity, a vanishing Earth term,
  a direct Earth field against Decimal, observation without changing
  DOP853 results, wrong Earth sign, vector and receipt tampering, and
  failure, deadline and exclusive-output paths. The archive load
  checks identities and shapes without evaluating retained fields.
- 26 focused tests passed. The full guarded regression finished
  with 6152 passed and 407 skipped. The
  [existing guard](experiments/0170/pytest-no-spice-guard.py.txt)
  blocks native binding imports and CSPICE loads; the skips require
  live access. Ruff, strict OpenSpec, local links and frozen checkout
  checks passed. The [manifest](experiments/0183-verification.json)
  pins tested files, design inputs and verification results.

## Consequences and revisit conditions

R5.36 makes no measurement of Earth's effect on the real trajectory.
R5.37 needs separate authorization for one B study and one offline
audit. Actual B convergence, telemetry agreement and the 60/10 s
deadlines remain unmeasured. The missing historical native-A final
identity, R5.3/R5.17 failures and strict M3 remain unchanged.
No new SPICE queries, kernel loads, retained record/force evaluations
or real trajectories were part of R5.36.
