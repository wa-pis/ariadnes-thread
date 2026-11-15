# 0208 — Qualify the fixed-command worksheet on artificial inputs

- Date: 2026-11-16 (Europe/Samara)
- Decision status: accepted synthetic qualification under [ADR0207](0207-design-fixed-command-seed.md).
- Implementation: R5.59b complete on artificial data; R5.59c and R5.60 unexecuted.
- Scope: offline analytic command arithmetic, refusal gates and saved-evidence limits.
- Measured base revision: `88cae06519970f331a26407d6aaf804eee473d26`, with the tested source hashes in the verification manifest.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-derive-and-freeze-one-fixed-command-seed), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559b-qualify-the-fixed-command-worksheet-2026-11-16), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

ADR0207 proposes a different fixed-endpoint hypothesis from the failed
scalar impulse seed. This stage qualifies only the arithmetic and the
bounded worksheet, with no access to retained scientific inputs.
The artificial packet has six independent section digests, plus a
separately pinned complete fixture. It tests fixed endpoint/epoch
identity and body-relative reconstruction from synthetic binary64
SSB operands. It is a separate schema from R5.59 synthetic readiness
and from any future retained command provenance.

## Options considered

- Test only a round trip through the same inverse formulas: insufficient
  for signed branch errors and shared mistakes.
- Manufacture known tilted conics from orbital elements, then compare
  a binary64 inverse and an independently implemented Decimal invariant
  reconstruction: selected. Neither path propagates a state.

## Decision and rationale

The [worksheet](experiments/0208-seed-worksheet.py) solves the
transverse-speed roots, screens minimum conic radius in the relevant
half-leg, reconstructs each physical-time asymptote and derives each
full vector impulse in pre-impulse TNW. The
[96-digit oracle](experiments/0208-seed-oracle.py) solves for angular
momentum instead and reconstructs the velocity from its eccentricity
vector. It checks energy, reconstructed momentum and signed asymptote
and independently computes sequential rocket-equation masses and
durations. Both paths must support the admissibility and ranking;
an ambiguous result does not supply controls.

The primary worksheet freezes six binary64 command words and checks
event order plus exact rational mass ledgers for commanded and
effective burn durations, before rounding. Synthetic failures cover
collapse of an epoch, a deficit that displays as 500 kg, a deficit
only in the effective ledger, historically rejected command words,
zero/collinear asymptotes, and an otherwise admissible near tie.
The [manufactured endpoints](experiments/0208-seed-fixtures.py) include
both transverse signs, an inward Moon leg with safe periapsis, and a
physical incoming Mars velocity. A variant exercises all four pairs.

The [runner](experiments/0208-seed-runner.py) uses an isolated
standard-library worker and digest-pinned bounded I/O from R5.59.
It has one 15 s shared watchdog, 512 KiB input and 128 KiB total
output. Attempt/report/receipt files are exclusive and durable; the
worker authenticates saved bytes before recording completion under
the same deadline. Separate readback can pin the final digest
without rerunning the solver. Oversize or substituted inputs, report
tampering, a stall during saved readback and an existing destination
cannot certify a new result. A partial report remains available
without a completion witness.

## Evidence and verification

The separate artificial invocation used **524,288 input bytes**
and **8,338 output bytes** in **0.059 s of 15 s**, from
interpreter startup through durable completion. The external pinned
readback agreed with the within-budget readback. The artificial
selection was Moon negative / Mars positive. Across the four roots
the largest velocity-vector discrepancy was 2.17e-12 m/s and the
largest minimum-radius difference was 9.31e-10 m. The two ledgers
were checked before rounding; the independent ideal sequential
duration and mass differences were at most 2.27e-13 s and
2.27e-13 kg. These are arithmetic differences on the manufactured
case, not physical error bounds.

All **29 focused tests** passed. The project regression using the
[offline guard](experiments/0189/pytest-offline-guard.py.txt) passed
**6,377 tests with 494 skipped** in 125.57 s. The guard excludes
native, live and retained-science cases; existing synthetic unit
tests remain enabled. Ruff and strict OpenSpec passed. The checkout
and tested source hashes remained frozen throughout regression.

The [verification manifest](experiments/0208-verification.json)
pins source/test/guard bytes and the original artificial records.
No retained archive read, SPICE, kernel access, force evaluation,
integrated trajectory, R5.59c or R5.60 occurred in the worksheet.

## Consequences and revisit conditions

There is no retained command pair. Before consuming the separately
authorized R5.59c generation, authenticate and map the six retained
sources in a separate adapter and qualify its selectors on artificial
archive shapes. Keep the tested geometry and selection logic; the
artificial envelope must not be used to certify a retained proposal.
Even a successful retained proposal still needs ADR0205 physical
readiness and separate R5.60 authorization.
