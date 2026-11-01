# 0144 — Implement independent saved-node arithmetic

Date: 2026-11-01
Decision status: accepted bounded implementation unit under ADR0143; physical contract unchanged.
Implementation: R5.2g.1 arithmetic/profile core implemented;52 new/89 focused and5184 full tests pass. Complete auditor remains partial.
Scope / milestone: M3 R5 preparation, zero-native saved-data arithmetic only.
Base revision: `4dab14e9a03e297b254a143589a74b7d54f8eb47`, initially clean; new core/tests untracked during checks.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; bounded implementation of [ADR0143](0143-independent-saved-evidence-audit-contract.md) following [runner preparation](0142-short-coast-orchestration-and-evidence.md).

## Context and constraints

The next auditor contains independent arithmetic plus file/provenance orchestration.
Verify the arithmetic/raw-array boundary first, without creating a file entry point
that could claim complete verification before its provenance/error/budget checks
exist. This unit leaves R5.2g and R5.2 incomplete. No reference study, propagation,
production/environment/legacy/input/kernel change or new dependency.

## Options considered

- Reuse runner/oracle arithmetic: reject; would validate common mistakes.
- Build file orchestration and arithmetic as one unchecked path: larger review and
  test boundary; complete the independent arithmetic unit first instead.
- Stdlib-only Decimal/raw-array functions plus hand-built fixtures: selected.

## Decision and rationale

[Core](experiments/0144-short-coast-audit.py) imports no runner, force adapter,
production or scientific library. It has no audit_file/execute/CLI and cannot mark
reference evidence verified. The remaining file/provenance/partial-output path
must be implemented and tested before the one R5.3.

Compute direct inverse-cube gravity from exact binary64 operands at80/100 Decimal
digits, require relative1e-60 vector stability, and retain signed differences as
strings. Check source fields against max(1e-15m/s^2,1e-11*reference norm); total
fields use the sum of individual reference norms to preserve cancellation scale.
Check actual native node telemetry separately from explanatory node fields using
those same operands. These are ADR0143 arithmetic envelopes, not changed scientific
state/sensitivity gates or rigorous numerical/physical error bounds.

State-difference components must equal independently Decimal-subtracted and
rounded operands with the original expression tree. Norms must exactly match a
binary64 replay and lie within four ULPs of an80-digit Decimal norm. Retain signed
errors/norms; validate gate booleans at the original thresholds without increasing
them to admit rounding. Correctly false gates remain false, not rejected for
being scientifically unsuccessful.

Native profiles bind model/frame/units/GM/source order, nonboolean step/counts,
exact1s/0.5s301/601 grids and seven original nodes/initial states. Raw state and
force histories must match saved samples; all retained values are finite and
total/source sums obey the existing1e-12m/s^2 native consistency gate. Numeric
epoch-key collisions and incomplete integration are rejected. Oracle profiles
bind success/tighter/nfev/offsets, zero initial correction and independently
reconstructed states with explicit rounded binary64 velocity-times-offset products
followed by Decimal sum/rounding. This preserves declared expression semantics.

Node checks bind all seven moving-body labels/frames/NONE epochs and finite SI
states, exact model inventories and four-by-seven profile force rows. Check all
three exclusion radii at the available nodes, including Earth in model A; only
declared sources enter the force sum. Guard checks at unsaved native/RHS epochs
cannot be replayed from this data. No continuous safety claim.

## Evidence and verification

[52 new tests](../../tests/test_r5_short_coast_audit.py) use hand-built arrays and
analytic collinear/rational3D fields, translated geometry, zero GM and irrational
norm/stability fixtures. No solver generates those arrays. Tests cover signed3D
vectors, cancellation scales, exact/adjacent position and velocity gate boundaries,
wrong signs/indirect origin terms, raw node/history/force/epoch/profile/GM/finite /
completion corruption, oracle corrections and cancellation-sensitive product/sum
rounding. The exact reference epoch is exercised without time or ephemeris queries.
A fresh-process test verifies lazy stdlib imports and absence of an execution API.

Initial core run:49 passed in0.12s. After adding reference-epoch and indirect-term
coverage, core+runner tests:89 passed in0.25s (52 new+37 existing). Ruff and strict
OpenSpec pass. No focused-test failure or scientific execution occurred.
[Full pytest](experiments/0144-full-pytest.txt):5184 passed in648.51s, exit0.
[Checks](experiments/0144-arithmetic-preparation-checks.json) retain exact source/log
hashes and verification scope. Checkout status was byte-identical throughout the
full run; all265 tracked protected code/test/example/environment/legacy/experiment
files remain identical to the base. Ruff/strict OpenSpec, source/log digests, local
links, finite JSON and diff checks pass. No focused/full failure or scientific
retry occurred. Full-suite native call totals were not instrumented; the new52
tests import no scientific library and acquire no body states.

Prepared source SHA256:

- `docs/adr/experiments/0144-short-coast-audit.py`: `307ad5abb4b56c93abb9843ba5d657ab54d6a7954af238b07c21e342dcfbbdea`.

- `tests/test_r5_short_coast_audit.py`: `4d0bddc4a2c71c623a588f83a3ee3408c8069e21644a06d3bf004c96a2223a02`.

## Consequences and revisit conditions

Next wire the prepared core into the private file auditor: duplicate/nonfinite JSON
handling, immutable input/current-file and saved runtime/kernel identities, full
call/count/order/comparison ledgers, complete/partial/rejected outcomes and exclusive
10s finite output. Review all R5.2 evidence before parent completion/reference use.
The new unit verifies arithmetic and retained-array consistency only; no full-file
reference audit, empirical model sensitivity, historical-memory/kernel proof,
unsaved-stage replay, mission accuracy, finite burns, safety or strict M3/task3.9
closure. Ordinary preparation fixes need tests; changed scientific contracts still
require the user decision and automation pause under ADR0137.
