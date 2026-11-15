# 0206 — Prepare the synthetic fixed-command readiness check

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted synthetic qualification under [ADR0205](0205-design-fixed-command-physical-join.md).
- Implementation: R5.59 complete on artificial evidence; R5.60 unexecuted and unavailable.
- Scope: admission, numerical comparison decisions and bounded evidence on invented inputs.
- Measured base revision: `ef0ecadd622bff5a526ada388c46df7d1fc83219`, with the three source files pinned in the verification record.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-test-one-fixed-command-pair-at-the-physical-checkpoint), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559-qualify-the-synthetic-readiness-check-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

ADR0205 defines a future full-force two-arm comparison at the exact
R5.51 checkpoint. No eligible commands, covered and qualified reverse
solvers, independently justified endpoint errors or enforceable live
counters are available. This preparation uses invented command words,
hashes, coverage and evidence and must always leave the actual physical
status unresolved. Only the fixed event words, reference model identity,
spacecraft constants and acceptance limits are taken from the contract.

## Options considered

- Add the scientific adapters now: unnecessary for testing admission,
  and would mix simulated evidence with live verification.
- Use a private standard-library checker and an isolated synthetic
  runner: selected. No public API, dependencies or production dynamics
  change.

## Decision and rationale

The [checker](experiments/0206-readiness.py) requires a separately
pinned input digest. A second digest binds the command, exact epoch
words, boundary identities, ordered resources and settings to the model
qualification, budget and synthetic measurements. It checks the
closed coverage interval for each of the eleven SPK links and two
rotations in the fixture. It requires distinct synthetic RKDP87 and
DOP853 qualifications for decreasing physical time and the three
force-check regions. The fake certificate hashes test binding and
presence; no certificate or actual resource is qualified by this step.

Each burn uses the exact rational value of the production binary64
mass-loss rate. Two ledgers distinguish the commanded durations from
the differences of the native event words in the artificial binary64
clock. Both must preserve the 500 kg dry floor before rounding.
Tests independently reproduce a deficit that rounds to 500 kg and
a deficit in the effective-span ledger despite a passing commanded
ledger. There is no 550 kg reserve claim.

The synthetic comparison checks exact checkpoint and target epoch
words and keeps join and forward target verdicts separate. It compares
outward Decimal intervals from exact rational input magnitudes and
allowances with the unchanged ADR0205 limits. An interval at the upper
edge passes; touching the limit at its lower edge does not prove a
miss. Missing bounds or solver disagreement remain inconclusive.

A chronological list of fake charges counts rejected work and reserved
upper bounds before assessing completion, with separate per-solver
segment limits. The ceiling fixtures cover 12 segments, 1,000,000 RHS
charges, 32,000,000 state/rotation charges, 64 MiB of hypothetical
evidence, the 285/300 s work/finalization boundary, and a separate
30 s audit with bound input and output sizes. No solver or provider
performs those charges. A quota breach, unaccounted work or incomplete
or failed segments cannot pass.

The [runner](experiments/0206-readiness-runner.py) has one isolated
standard-library worker, one 15 s parent watchdog, and 2 MiB input and
128 KiB aggregate output limits. It commits files exclusively, flushes
files and their directory, and uses a completion record after the
receipt. Readback checks source and fixture identity, the evidence hash
chain, timing and zero-work/authorization fields after the launcher
exits. A terminated or late worker can leave partial files but cannot
certify them. The evidence chain detects mismatches; published external
digests bind the original records independently of their internal
chain.

## Evidence and verification

A separate successful artificial invocation processed **2,097,152 input
bytes** and saved **4,396 bytes** in **0.063 s of 15 s**,
including interpreter startup and durable finalization. Saved readback
passed without re-executing the checker. All five counts (SPICE,
kernel access, force evaluation, integration and R5.60) were zero.

All **64 focused tests** passed. The [offline regression guard](experiments/0189/pytest-offline-guard.py.txt)
excluded native, live and retained-science cases; the project-wide
regression had **6,348 passed and 494 skipped** in
131.64 s. Existing purely synthetic unit tests
remained enabled. Ruff and strict OpenSpec passed; the checkout and the
three source hashes were unchanged throughout regression.

The [verification manifest](experiments/0206-verification.json) pins
the three tested source files, verification guard, artificial fixture
and saved records.

## Consequences and revisit conditions

R5.59 verifies artificial decisions, caps and evidence handling only.
No SPICE or kernel files were accessed by the worksheet; it evaluated
no forces and integrated no state. R5.60 was never launched and has
no authorization. Before seeking it, obtain an independently justified
fixed command pair and prove real coverage, full-force reverse and
reference accuracy, endpoint error bounds and enforceable timing and
counters under ADR0205. Strict M3, physical continuity, target closure,
safety and propellant reserves remain open.
