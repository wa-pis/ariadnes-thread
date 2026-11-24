# 0249 — Qualify coupled shooting on the artificial problem

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (private artificial implementation under ADR0248)
Implementation: complete; artificial qualification, required local regressions and source-bound CI verified
Scope / milestone: F3 / M3 preparation; production F0 unchanged
Base revision: `0e09f5c544ccd17cde4ba16a02445e73f2f1243c`, with six new source/test files; exact measured hashes in the evidence
Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-coupled-shooting-on-an-analytic-finite-burn-benchmark), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; implements [ADR0248](0248-design-coupled-synthetic-benchmark.md)

## Context and constraints

The coupled method needed a known-feasible check before any real F0 solver.
Use exactly ADR0248's manufactured uniform field, six controls/two translation
nodes, perturbed seed, profiles, dimensional gates and budgets. No fixture,
tolerance, model, dependency or production-interface change is made.

## Options considered

- Reuse the historical mission/local correctors: they bind different physics or
  controls. Retain only existing pure TNW guidance helpers on the candidate side.
- A shared candidate/checker flow: smaller, but would conceal common guidance or
  integration errors. Keep an independent stdlib implementation instead.
- A generic research backend: unnecessary for this single qualification. Keep
  three private modules and an explicit bounded process invocation.

## Decision and rationale

[Candidate](../../src/space_nav/_coupled_benchmark.py) uses pinned TRF/DOP853,
explicit per-arc modes and derived masses/epochs. It counts finite-difference
callbacks, freshly evaluates the returned variables, and replays from the
initial state without injecting shooting nodes.
[Oracle/auditor](../../src/space_nav/_coupled_benchmark_oracle.py) independently
constructs Decimal80/100 reference states, rebuilds TNW and checks the actual
recovered command using both fixed RK4 meshes. It imports no NumPy/SciPy,
candidate guidance or mission model, and never reruns the optimizer.
[Runner](../../src/space_nav/_coupled_benchmark_run.py) separates workers, enforces
shared deadlines and bounded output, preserves first failures and unknown
partial counters, and records source/runtime/settings provenance.

A first artificial timing pilot passed numerical gates but review found that
the CLI's own bootstrap preceded its internal start clock. Preserve that pilot;
do not use it as complete timing qualification. A small instrumentation fix
inherits an explicit outer monotonic `--parent-start`; workers cannot reset it.
The final invocation also applies an external 300 s watchdog and receipt.
This changed no scientific settings or work limits. `report.elapsed_s` is sampled
before report fsync; the final post-fsync deadline check and external receipt
cover durable completion.

## Evidence and verification

The corrected standalone producer and separate auditor both exit0. External
startup-through-process-completion elapsed time is 3.621921458 s, with inherited
startup0.079521083 s. Producer2.783306250 s and auditor0.715798083 s fit all
unchanged stage limits. Benchmark evidence is8804 B, below2 MiB; input is below
64 KiB. The invocation checks the external deadline again after receipt fsync.

Producer:174 residual callbacks,528 synthetic arcs,228552 RHS. TRF nfev10/njev9;
the recovered command is numerically near the known witness, but command equality
or optimizer success is not the admission gate. Auditor:12 arcs/294912 RHS,
zero optimizer calls. Both report zero SPICE/kernel/real-archive reads and native
propagations. Gravity contributes1000 m/s versus initial1000 m/s; witness mass
loss is approximately453.21 kg of2000 kg.

| Maximum measured difference | Position (m) | Velocity (m/s) |
| --- | ---: | ---: |
| Witness versus analytic reference | 1.56090e-6 | 1.18234e-11 |
| Shooting defects | 3.55858e-8 | 4.54747e-13 |
| Candidate versus tighter RK4 | 1.59443e-6 | 1.22782e-11 |
| RK4 meshes | 2.19793e-6 | 8.41283e-12 |
| Candidate final target | 2.98024e-8 | 1.36425e-12 |
| Independent final target | 1.37836e-6 | 1.81899e-12 |

All corresponding ADR0248 gates pass; mass differences are at most1.13687e-12 kg.
Retain the complete states, raw18 defects, counters, profiles, hashes and timings,
rather than treating these rounded maxima as sufficient evidence.

Focused tests:89 pass. Required `make test` passes7140 portable tests in208.42 s
(42 archival skips,412 live deselections), then412 live tests in603.90 s
(7182 deselections). All1393 frozen files and Git status remain unchanged across
both lanes; all1081 previously protected non-Markdown files remain unchanged.
Repository Ruff, separate scientific/code/evidence review, local links, diff and
strict OpenSpec pass.

Subsequent [CI45493818215](https://github.com/wa-pis/ariadnes-thread/actions/runs/45493818215)
on exact commit `95ae3a3a9ef32844009ed017895c39f7e51df736` completes successfully
at2026-11-24T22:02:40Z. Portable:7139 pass/43 skip; live:376 pass/36 skip.
All89 new F3 cases pass; total7594 unique cases,7515 passes,79 skips and zero
failures/errors, with no lane overlap. The42 archival and37 platform-specific
skips have exactly the same case/reason inventory as ADR0245. The local logs
support the same total count, but contain no case inventory; exact local/CI
case-ID equality is not asserted. Preserve the original qualification manifest
with its historical CI-unobserved status. The new [CI receipt](experiments/0249-ci-verification.json)
binds run/job/commit, six source/test hashes and the original
[artifact ZIP](experiments/0249-ci-validation-results.zip), including both JUnit
files and the resolved Conda environment; the ZIP matches GitHub
SHA-256 `60b564fd8aae4b1673a6db5516b650dcc02738cffd7f4bc9ae86c3c3ca1e6d42`.
This documentation/evidence update reruns no tests or scientific work. The
receipt verification counters describe this documentary update only; the
completed CI live lane includes existing SPICE/native regression work.

Evidence: [final run](experiments/0249-coupled-benchmark/report.json),
[independent audit](experiments/0249-coupled-benchmark/audit.json),
[producer](experiments/0249-coupled-benchmark/producer.json),
[outer invocation](experiments/0249-benchmark-invocation.py) and
[receipt](experiments/0249-coupled-launch.json). Preserve the
[timing pilot](experiments/0249-bootstrap-pilot/report.json) as well.
[Focused log](experiments/0249-focused-tests.log),
[required regressions](experiments/0249-regression.log),
[frozen checkout](experiments/0249-frozen-checkout.json) and
[freeze verification](experiments/0249-freeze-verification.json) bind the tested
source bytes. [Qualification manifest](experiments/0249-qualification.json)
collects identities and completed checks.

## Consequences and revisit conditions

The artificial test demonstrates one successful coupled recovery under this
fixture. Independent flow checking covers witness and actual unreset command;
reported reset-arc ends/18 defects receive algebraic continuity checks rather
than separate reset-arc flow replays. Producer callback-history claims are checked for
types/caps/coherence, not independently reconstructed from final states.
Mesh agreement is diagnostic, not a certified global error enclosure.

The original admissible Moon-to-Mars pair/F0 feasibility and strict M3 remain
unmet. Before implementation or execution in F0, review full-force wiring,
boundary/seed binding, force/integration qualification and independently justified
physical error bounds; then adopt a separate concrete bounded contract and check
applicable authority. No real archive evaluation, SPICE mission study, consumed
P6 replay, R5.60 admission or altered date/phase follows from this artificial pass.
