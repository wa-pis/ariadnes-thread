# 0213 — Qualify the Mars capture-phase screen

- Date: 2026-11-17 (Europe/Samara)
- Decision status: accepted artificial qualification under [ADR0212](0212-design-mars-capture-phase-seed.md).
- Implementation: complete artificial-only phase screen and independent saved-evidence readback; no retained runner.
- Scope: R5.59e, two manufactured four-record archives, no physical admission.
- Measured base: `6b5e1f03e7698796404579716b8d8a9a3d17179e` plus the source hashes in the verification manifest.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-verify-the-full-artificial-workload-before-retained-admission), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559e-qualify-the-artificial-capture-phase-screen-2026-11-17), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0211](0211-record-fixed-command-seed-refusal.md) and [ADR0205](0205-design-fixed-command-physical-join.md) stay in force.

## Context and constraints

The archived Mars arrival cost is dominated by the vector direction.
The next question is whether varying only the capture phase on one
ellipse can produce a unique, cheaper pair under the existing local
conic and fuel gates. The qualification uses fabricated archives
with known outcomes and does not answer that question for the
retained mission.

## Options considered

- Check only a chosen favorable point: rejected; this would miss
  wrong grid coverage, alternate branches and ranking failures.
- Verify the complete fixed grid using manufactured success and
  empty-grid archives, and audit saved bytes: selected.

## Decision and rationale

The [runner](experiments/0213-phase-runner.py) accepts four explicitly
pinned artificial records, verifies the prior receipt chain and
fixed zero-phase refusal, and guards file access in an isolated
standard-library worker. The [orbital state module](experiments/0213-phase-orbit.py)
reconstructs each phase twice: binary64 perifocal and 96-digit
radial/transverse states with orbital invariant checks. The
[screen](experiments/0213-phase-screen.py) compares both signed Mars
conics, keeping the lunar branch and other fixed data. It checks
the existing arrival sign, exterior margin, exact event order and
two mass ledgers, and refuses ambiguous rank. Independent saved-byte
readback checks per-phase state errors, root/pair inventory, evidence
counts, rejection reasons, ledgers and ranking. It does not reopen
input archives or resolve the conics.

## Evidence and verification

The [fixture builder](experiments/0213-phase-fixtures.py) supplies a
known tilted synthetic ellipse. Its
independent polar-elements/bisection oracle predicts the winner
and runner-up gap without calling the screen's conic solver.
Both full cases cover all **360 phases and 720 Mars root slots**
and reproduce the zero-phase commanded dry-floor rejection.

| Artificial case | Outcome | Pairs checked | Input bytes | Output bytes | Through saved readback |
| --- | --- | ---: | ---: | ---: | ---: |
| Known tilted ellipse | 95°, both positive roots | 437 | 131,072 | 1,199,175 | 0.371755 s |
| Higher excess speed | No eligible pair on grid | 316 | 13,401 | 1,035,269 | 0.356440 s |

The known case improves from 6,296.905 m/s
at phase zero to **4,056.156 m/s** at 95°. The margin to the
next eligible pair is 0.626415 m/s and the
ideal final mass is **797.724 kg**. The independent fixture
oracle agreed within 1e-6 m/s and 1e-8 kg. The largest state
differences across the main grid and both frames were 2.1e-05 m
and 4.18e-12 m/s. The verified empty grid left commands null.

The [targeted tests](../../tests/test_capture_phase_screen.py)
also verify the one-byte-over input/output refusals, tampering
with rebound hashes, mode separation, ranking ambiguity, no
source reopen and timely exclusive completion. **20 focused tests**
passed in 2.18 s. The [offline guard](experiments/0189/pytest-offline-guard.py.txt)
regression passed **6,451 tests** in 125.37 s with **494
skipped** for native, live and retained-science cases. Ruff and
strict OpenSpec passed. Checkout status and source hashes were
frozen during testing. The [verification manifest](experiments/0213-verification.json)
records tested source hashes, both workload measurements and
artifact digests. The phase screen used no kernel access, SPICE,
force evaluation or integration. R5.59f and R5.60 were not run.

## Consequences and revisit conditions

Only synthetic results are admitted by this entry point. A separate
request and pinned retained binding are required before R5.59f.
The artificial pair cannot be used as a flight command. Even a
retained phase proposal would change the Mars target state and
require a reviewed new physical boundary before admission. The
original R5.60 remains unavailable.
