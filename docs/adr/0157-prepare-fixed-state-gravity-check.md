# 0157 — Prepare the fixed-position real-gravity check

Date: 2026-11-08
Decision status: accepted implementation of the unchanged ADR0156 contract.
Implementation: prepared; verification results recorded below, retained execution pending.
Scientific status: synthetic/component verification only; R5.11 has not executed.
Scope / milestone: M3 R5.10, private offline force calculator and evidence audit.
Base revision: `a53ee6193983f2c46d54fb427aea0c5639043b64`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [ADR0156](0156-fixed-state-real-gravity-contract.md), preserving historical helpers, data and gates.

## Context and constraints

The user authorized R5.10 preparation, tests and commit/push. The retained
real-source force experiment is a separate R5.11 stage. Reuse saved data and the
pinned Conda interpreter; do not modify production APIs, the environment, the
original13-kernel provenance, scientific tolerances or failed-reference history.
Keep real-source arithmetic, integration, physical fidelity and mission safety
as distinct claims.

## Options considered

- Extend retained historical experiment helpers in place: reject; their source
  hashes and raw evidence are immutable.
- Introduce a generic force/propagation framework: unnecessary for this bounded
  private fixed-position check.
- Small separate input, binary64, reference and audit modules: selected; reuse
  the pinned pure0145 JSON and0153 polynomial helpers while keeping reference
  arithmetic independent from the candidate.

## Decision and rationale

The [input adapter](experiments/0157-fixed-gravity-inputs.py) binds the three
ADR0156 input hashes, exact boundary equality, R5 harmonic lunar GM,21 raw source
rows,84 saved native returns, exact hi/lo epochs and Type2/frame/centre/coverage.
It reconciles saved assessments and distinguishes historical kernel assertions
from the current pinned Conda Python executable/build. It never queries a kernel
pool or evaluates gravity.

The [calculator](experiments/0157-fixed-gravity-study.py) keeps Bhat and Vhat*lo
separate through fsum subtraction at the unchanged X. It retains compensated,
uncorrected and wrong-sign arms, A/B totals, attempted/completed counts and the
ordered operation ledger. Invalid/nonfinite initial caller baselines are rejected
before creating an output; later clock failures retain finite partial evidence.
A real-mode call requires a fresh stdlib-only process and cannot reset its clock
after module initialization. An earlier explicit caller timestamp may include
pre-import setup; custom clocks/adapters are labelled injected tests.

The independent [reference](experiments/0157-fixed-gravity-reference.py)
reconstructs exact rational polynomials and d0..d3, then computes80/100-digit
Decimal fields, signed source/rephasing/assembly/evaluation contributions and
both unchanged force gates. Totals retain the sum-of-source-norm scale. Source
floors are never removed; controls remain diagnostic. Field vectors and completed
model results are stored before completion callbacks, preserving upstream values
if a later deadline/error interrupts the work. Checked helper bytes are compiled
directly so cached bytecode cannot substitute different source.

The separate [saved-data auditor](experiments/0157-fixed-gravity-audit.py)
imports no candidate/study code. It independently reassembles binary64 operands,
recalculates reference values/gates, and checks raw signed vectors, exact field
prefixes, identities and ledgers. Valid partial evidence remains partial;
corruption is rejected, and injected fixtures never qualify real science.
Its shared pure reference is independent of the candidate, not a second
implementation of the reference force formula or an independent ephemeris.

Both future execution paths retain the original10s process/import/read/hash /
compute/serialization/flush budget,168-reference-field cap and zero scientific
imports/native calls/GM acquisitions/propagations. Candidate fields are capped
at63, source rows21 and model totals14. The study stops at the first required
failure, preserves earliest error through finalization failures and uses exclusive
finite output. The auditor has its own budget; no real retained run was performed.

## Consequences and revisit conditions

The checks below complete R5.10 preparation. R5.11 remains
pending; its real force errors, control outcomes, execution budget feasibility
and independent saved-data result are not yet measured. Source-only/component
success does not prove moving-spacecraft drift/correction assembly, a corrected
solver, the historical R5 failure cause, Earth-force sensitivity, astronomical
uncertainty, strict M3/task3.9, full-force/finite-burn feasibility or mission safety.
No automatic retry, changed cap/tolerance/input, optimizer or automation restart.

## Evidence and verification

All221 new focused tests pass in0.72s. The complete suite passes5630 tests in
657.49s; process elapsed658.2959350412712s. Checkout status and all eight new
source/test byte hashes remained unchanged throughout the full run. All338
previously tracked protected runtime/test/example/environment/experiment/legacy
files remain byte-identical to the base. Repository-wide Ruff and strict OpenSpec
pass; links/diff/finite JSON and final protected-source checks pass before commit.

A fresh stdlib input-only preflight validates all21 retained source rows and the
pinned interpreter in0.1683014170266688s. It performs zero force evaluations,
native calls or propagations; this is input preparation, not R5.11 execution.
The future R5.11 invocation must first bind the tested source hashes retained in
this record's verification manifest; no repeat full regression is needed while
those source/test bytes remain unchanged.

- [Source hashes, checks and protected-file verification](experiments/0157-verification.json)
- [Focused tests](experiments/0157-focused-pytest.txt), [full tests](experiments/0157-full-pytest.txt)
- [Input-only preflight](experiments/0157-input-preflight.json)

New tests cover analytic3D/central/zero/cancellation and detectable mutations;
source discrepancies and gate/precision boundaries; exact metadata/hash/GM/SI
validation; failed controls versus required failures; partial field/model
retention, prefix counters and domains; stale-bytecode identity, fresh-process
and clock/deadline/cap paths; finalization/exclusivity and full synthetic
calculator-reference-auditor integration. Existing full-suite native tests keep
their original limits. No new real-body force calculation or R5 replay occurred.
