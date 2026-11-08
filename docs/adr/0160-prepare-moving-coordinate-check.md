# 0160 — Prepare the controlled moving-coordinate check

Date: 2026-11-08
Decision status: accepted implementation of the unchanged ADR0159 contract.
Implementation: complete preparation; verification recorded below, retained execution pending.
Scientific status: synthetic/component verification only; R5.14 has not executed.
Scope / milestone: M3 R5.13, private coordinate assembly, reference and saved-data auditor.
Base revision: `ebb95fee7000c1a112f84106854fb54444680f45`, initially clean; eight new source/test files were untracked during regression and are bound by hashes.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [ADR0159](0159-moving-coordinate-assembly-contract.md), preserving all historical evidence and scientific gates.

## Context and constraints

The user authorized R5.13 implementation, tests and commit/push. The controlled
moving-coordinate experiment is a separate R5.14 stage. Only its input metadata
may be checked here; new retained motion or force results are not preparation
claims. Preserve the pinned Conda interpreter, six retained input hashes, source
polynomials, initial state, exact epochs, GMs, domain guards and original force
gates. No production, dependency, historical-helper or legacy-model changes.

## Options considered

- Modify the fixed-position helpers in place: reject; their bytes identify the
  retained0158 evidence and must remain immutable.
- Add a generic navigation or propagation framework: unnecessary for the narrow
  coordinate-arithmetic question.
- Separate private moving-input, assembly, reference and audit helpers: selected;
  reuse checked pure utilities while keeping the reference independent of the
  candidate and the auditor free of candidate/study imports.

## Decision and rationale

The [input helper](experiments/0160-moving-inputs.py) validates the six frozen
records, exact initial r0/v0 and hi/lo epochs, original GMs/source provenance,
and saved0158 source/model values at elapsed zero. Reconciliation is metadata
only: it performs no new moving-state or force calculation. Hash-checked source
bytes are compiled directly, preventing stale bytecode from substituting code.

The [assembly helper](experiments/0160-moving-study.py) constructs the explicitly
prescribed q/w fixture from exact rational coefficients and rounds once to
binary64. Absolute exported position/velocity are checked separately from the
relative force operands. Bhat, source rephasing, r0, rounded drift and q remain
separate until the final relative sum. Flattened-craft and omitted-q arms are
diagnostic controls. These prescribed corrections are not propagation outputs,
real gravitational acceleration, engine commands or evidence of solver accuracy.

The independent [reference](experiments/0160-moving-reference.py) reconstructs
rational motion targets and quantization, checks the half/one-ulp bounds, exact
zero sums and ties-even, and builds all four exact force geometries. It verifies
all exact and binary64 arm domains before any field evaluation. Candidate vector
norms and squared norms must also be finite and positive. Eight80/100-digit
Decimal fields per source retain signed native-source, rephasing-plus-drift,
relative-assembly and field-evaluation contributions. Both original force gates
remain unchanged. Overall agreement includes the full source discrepancy without
subtraction or allowance; returned-geometry agreement isolates field evaluation.
Model scales sum constituent norms. The one-ulp
criterion remains the predeclared empirical acceptance rule, not a universal
rounding theorem. Controls are reported without requiring failure or improvement.

The [saved-data auditor](experiments/0160-moving-audit.py) independently rebuilds
motion and binary64 arms from raw saved operands, then recalculates reference
gates and totals without importing candidate/study code. Its pure reference is
independent from the candidate; sharing that reference does not create another
independent ephemeris or force-formula implementation. It validates complete or
partial prefixes, including full preflight metadata and completed field vectors.
Injected fixtures are labelled as tests and cannot qualify real science.

Both future execution paths preserve the separate10s process/import/read/hash /
compute/serialization/flush budgets and caps seven assemblies/21 source rows /
168 reference fields/63 binary64 fields/14 model totals. Ordered attempted and
completed counts stop at the first required failure. Returned fields/model data
are stored before completion callbacks; errors retain the earliest failure.
Exclusive finite JSON and post-flush checks prevent late completion from being
reported as a pass. Invalid initial baselines create no evidence file; later
clock failures, including subtraction overflow, retain a finite partial result.
No scientific-library import, native call, GM acquisition, propagation, optimizer
or replay is added to these private paths.

## Consequences and revisit conditions

The checks below complete R5.13 preparation. R5.14 remains pending: there is no
measured moving real-source force result, control comparison or retained-study
budget-feasibility result. A later execution must bind the tested hashes first
and preserve all original inputs, gates and caps. A failed required gate requires
a separately justified review, not an automatic retry or weaker criterion.

Synthetic success does not prove correction quality, a corrected solver, the
cause of the historical R5.3 failure, Earth-force trajectory sensitivity,
astronomical accuracy, full-force/finite-burn feasibility, strict M3/task3.9 or
mission safety. Automation remains PAUSED; no integration or R5 replay occurred.

## Evidence and verification

The first full regression finished with5880 passed/one failed in642.41s.
The new freshness test called the real-mode runner in the long-lived pytest
process; its import-start10s budget had legitimately expired during collection
and earlier tests, so deadline rejection preceded the intended freshness check.
The test now launches a fresh isolated child process. Runtime code, scientific
budgets and gates were unchanged; the failed log and source-bound receipt are
retained rather than replaced. The successful rerun is recorded below.

All251 new focused tests pass in4.81s. The complete suite passes5881 tests in
629.48s; process elapsed630.201020375s. Checkout status and all eight new
source/test hashes remain unchanged throughout the full run. All354 protected
runtime/test/example/environment/experiment/legacy files, including the353
earlier protected files and0159 verification manifest, remain byte-identical.
Repository-wide Ruff and strict OpenSpec pass; final links/digests/diff/JSON
and protected-source checks are retained in the verification manifest.

A fresh stdlib input-only preflight validates21 retained rows in0.233663542s
total process time. It performs zero new moving-state/force evaluations,
scientific-library imports, native calls or propagations. This is metadata
preparation, not R5.14 execution. The separate retained moving study and
audit have not run; their real-input gate outcomes and10s feasibility
remain unmeasured. The compact input summary references a lossless archive of
the full metadata report instead of duplicating historical kernel tables.

New tests cover analytic3D/zero/cancellation examples; nonzero drift/q/w and sign
mutations; exact epoch/source/GM/hash identity; source-zero parity; product,
summation, tie, subnormal and negative-zero boundaries; source-inclusive force
and precision gates; flattened/omitted controls; all geometries before fields;
finite norms; deadlines/caps/ordering/partial output; input drift, stale bytecode,
fresh-process restrictions and finalization. The synthetic end-to-end test uses
manufactured constant source polynomials with the actual independent reference
and auditor, then verifies rejection of a changed saved motion component.
Existing full-suite native tests retain their original scope and limits.

- [Tested hashes, process receipts and protected-file verification](experiments/0160-verification.json)
- [Focused tests](experiments/0160-focused-pytest.txt), [full tests](experiments/0160-full-pytest.txt)
- [Input-only preparation](experiments/0160-input-preflight.json), [full metadata output (gzip)](experiments/0160-input-preflight.json.gz)
- [First full regression failure](experiments/0160-first-full-failure.txt.gz), [first-run receipt](experiments/0160-first-regression.json)
