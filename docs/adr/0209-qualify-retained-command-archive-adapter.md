# 0209 — Qualify the retained command archive adapter on artificial files

- Date: 2026-11-16 (Europe/Samara)
- Decision status: accepted synthetic adapter qualification under [ADR0207](0207-design-fixed-command-seed.md).
- Implementation: adapter complete and tested on fabricated archives; R5.59c and R5.60 unexecuted.
- Scope: normalize the six pinned source shapes without selecting or verifying a command.
- Measured base revision: `f9f9f3fa0d1866c6c3d9e99dd489f2533a2c0e73`, with the tested source hashes recorded below.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-derive-and-freeze-one-fixed-command-seed), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559b1-qualify-the-retained-archive-adapter-2026-11-16), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0208](0208-qualify-fixed-command-seed.md) remains the independent arithmetic evidence.

## Context and constraints

The worksheet is already qualified on manufactured conics. It needs
an independent boundary between the frozen files and that arithmetic.
A test of selectors must not consume the separately authorized
retained generation or turn a synthetic result into a real proposal.

## Options considered

- Pass raw archives to the worksheet and allow it to choose values:
  rejected; that mixes source semantics with the geometry and offers
  too many opportunities to select a nearby epoch or later trial state.
- Validate and normalize at a separate, bounded input boundary:
  selected. The adapter returns authenticated operands and rejected
  history with null commands.

## Decision and rationale

The [adapter](experiments/0209-archive-adapter.py) requires six named,
independently pinned regular files. It refuses symlinks, additional or
missing names, mixed artificial and retained pins, and more than
512 KiB total. It reads and validates bytes before selecting any
operands, and takes the parent deadline check at entry, before each
read, after reading and before returning. No entry point starts the
worksheet. The real policy fixes the ADR0207 pins and exact epoch
words, and may not accept fabricated digests.

The adapter verifies the repeated R1 scenario/candidate and recorded
body states against 0098 and 0136. It checks the ADR0205 model, the
three exact epoch words, and the contract/R1/audit/correction digest
edges. Only the R1 signed excess vectors and exact R4 ignition and
target records supply geometry. It uses exact rational subtraction
of the binary64 SSB operands, verifies the recorded Decimal
convergence and original R4 boundary gates, and keeps the orbit
shape and conservative surface radii distinct. The 0079 named
commands and the two correction studies are decoded only into the
exclusion list, in explicit departure/arrival TNW order. No archived
propagation, checkpoint spacecraft state or failed residual is an
operand.

The [fabricated file builder](experiments/0209-archive-fixtures.py)
uses the known synthetic geometry of R5.59b, wrapped in the original
selector shapes. The tests check exact normalized operands and
preserved approach sign, then alter input bytes and separately
rebind external pins during structural faults. Wrong event words,
lineage, candidate, model, relative state, frame, orbit phase,
command order or metadata cannot produce a normalized packet.

## Evidence and verification

One isolated artificial measurement normalized **524,288 input
bytes** in **0.0015 s**; a scoped file audit saw exactly the six
fabricated opens and the supplied deadline was checked nine times.
The normalized packet occupies 4,561 compact JSON bytes and
contains four historical exclusions from the artificial records.
This measurement covers file authentication and normalization; it
does not time a retained solve or its evidence finalization.

All **39 focused tests** passed. The [offline guard](experiments/0189/pytest-offline-guard.py.txt)
regression passed **6,416 tests with 494 skipped** in
146.93 s. The guard excludes native, retained-science and live
cases; existing purely synthetic tests remain enabled. Ruff and
strict OpenSpec passed. Checkout state and pinned sources were held
unchanged throughout regression.

The [verification manifest](experiments/0209-verification.json) pins
sources, the test and regression guard, fabricated file digests, and
a digest of the normalized output. No retained seed evaluation was
performed. The worksheet, solvers and physical thresholds were unchanged.

## Consequences and revisit conditions

The output is normalized archive input, with null commands and no
launch authority. The fabricated files establish the selector and
refusal behavior only. The separately requested R5.59c invocation
still needs to bind this adapter to the tested arithmetic and
the shared watchdog/readback envelope before consuming its one
retained attempt. R5.60 remains blocked by the complete ADR0205
readiness and separate authorization.
