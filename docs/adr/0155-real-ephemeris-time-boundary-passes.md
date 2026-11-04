# 0155 — Real ephemeris time boundary passes

Date: 2026-11-04
Decision status: accepted; records the single user-authorized source-only study.
Implementation: immutable verified ADR0153 helpers; no runtime source changes.
Scientific status: all21 sampled same-kernel arithmetic checks pass; no real-force/solve qualification.
Scope / milestone: M3 R5.8, real Sun/Earth/Moon source time boundary only.
Base revision: `ec37e3ca3a899c00ff537e25e66c7838a0967fb9`, clean, preparation committed/pushed first.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Follows [ADR0153](0153-real-ephemeris-time-boundary.md) and [ADR0154](0154-resume-real-ephemeris-verification.md); supersedes no historical evidence.

## Context and constraints

The user authorized launch. The unchanged300s readiness check and all5409 tests
pass in ADR0154, satisfying preparation before real acquisition. Preserve the
original R5 inputs, candidate, epoch, ordered13 kernels, scientific gates and all
history. Only the previously frozen seven elapsed times/three bodies are sampled.
No new model, dependency, initial state, force evaluation or spacecraft propagation.

## Options considered

- Infer real-source behavior from the synthetic fixture: insufficient.
- Replay the failed R5 before isolating source arithmetic: reject.
- Execute the verified bounded source audit and separately inspect saved evidence:
  selected under the unchanged ADR0153 contract, once only.

## Decision and observed result

One import-inclusive source acquisition completes in2.1392379999160767s;
2.0888115419074893s before evidence flush, below60s. It returns exactly21 states,
28 segment selections/28 descriptor unpackings/1 kernel-handle check/6 array reads.
Before/after pinned identity is identical and clean. All seven exact hi+lo epoch
identities and all21 rounded-state parity, incremental and conditional Taylor gates
pass using exact rational comparisons, with both signs of the low time part.
Wrong-sign correction fails the incremental gate in18 nonzero rows; the three
zero-low-part rows correctly cannot distinguish the signs.

All sources are the pinned INPOP19a Type2/J2000 records: Sun10->0 degree10,
Earth399->0 degree12, Moon301->399 degree12 plus the Earth record. These are the
three selected record/trailer pairs, not DE440 data. Exact derivatives of the same
position polynomials supply the independent velocity reference; centre-chain sums
and km->SI conversion are exact in the rational oracle.

| Body | Max native/exact position discrepancy, m | Max velocity discrepancy, m/s | Max compensated increment error, m |
|---|---:|---:|---:|
| Sun | 2.1333181985673925e-8 | 1.7629331728075805e-15 | 2.904498426763159e-22 |
| Earth | 1.021940415809388e-5 | 3.4562558456037843e-12 | 1.0729010976817667e-17 |
| Moon | 1.1389867735956042e-5 | 4.527424841771295e-12 | 1.5152034779880028e-17 |

The gates remain0.001m/0.000001m/s for rounded-epoch parity and1e-12m for
increment error, plus the separate exact component Taylor/velocity/product-rounding
inequality. No bound was fitted or changed after observing the data. Unapplied time
shift reaches0.0018624201093363727m in these samples; this diagnostic
is the exact polynomial displacement, not an additional scientific pass criterion.

The combined compensation retains the provider's position discrepancy (up to
about11.4micrometres here). It does not reconstruct lost source bits. The observed
increment error is not a claim of astronomical position accuracy. Shared kernel
coefficients make this independent arithmetic of the same ephemeris model, not an
independent observational ephemeris or an astronomical uncertainty bound.

## Evidence and verification

A separate saved-row audit passes in0.10227383300662041s, checking all21 rows
without scientific imports or native calls. It reuses the independently tested
rational oracle; do not call it a second independent polynomial implementation.
An additional stdlib ledger audit passes in0.026060624979436398s and reconciles
all84 raw returns in order, independently unpacking the binary segment descriptors
and matching selected chains, cached records/trailers and raw native states to rows.
Both audits bind SHA256 `278b094cff6dd417ac15c04d3b4e4da137acede17de7147babd72fe9e3812102`.

All122 prior tracked experiment/legacy files and four prepared source/test hashes
remain unchanged. Checkout stayed clean throughout acquisition and offline checks.
Ruff/5409 full tests are reused on identical runtime/test bytes from ADR0154;
no full-suite replay is needed for this evidence-only stage. Strict OpenSpec,
local links, finite JSON, digests and diff are checked before commit.

- [Verification and exact artifact hashes](experiments/0155-verification.json)
- [Raw21-state evidence and84 native returns](experiments/0155-real-source.json)
- [Exact acquisition invocation](experiments/0155-real-source-invocation.txt) and [output](experiments/0155-real-source-output.txt)
- [Saved-row audit](experiments/0155-saved-audit.json), [invocation](experiments/0155-saved-audit-invocation.txt), [output](experiments/0155-saved-audit-output.txt)
- [Raw-return ledger audit](experiments/0155-return-ledger.json), [invocation](experiments/0155-return-ledger-invocation.txt), [output](experiments/0155-return-ledger-output.txt)

## Consequences and revisit conditions

R5.8 is complete as a source-time boundary check only. R5.3 remains failed/unclosed;
this does not prove its historical cause, qualify real spacecraft force arithmetic,
a corrected adaptive solve, missing-force sensitivity, strict M3 or mission safety.
No automatic R5 replay, integration, optimizer expansion or automation restart.
The next separately specified question is whether compensated relative assembly
and the retained native-position discrepancy satisfy the unchanged real-force
arithmetic envelope at fixed saved spacecraft states, before another solve.
