# Current State

Updated: 2026-11-01. Keep this file under 60 lines. Current instructions live
here and at the top of the roadmap; retained detail belongs in the ADRs.

## Goal and scheduling

Near-term product: one understandable research trajectory demonstrator with an
independently checked calculation and exportable result, not operational navigation.
Keep Python/TudatPy/SPICE/Streamlit and the long-term open-platform vision.
Automation `ariadna-m3`: PAUSED after R5.3 cap failure, per user instruction.
Pause immediately when user input/action is needed; no automatic D17/D18 replay.

## Verified baseline

- R1.1 passed at measured base `5c7012c`, unchanged production/environment;
  new runner/fixture were untracked (exact hashes/dirty state retained).
  [ADR 0119](docs/adr/0119-positive-ideal-m2-reference.md): exactly two identical
  1980-attempt searches/two 121-state samplings in shared 1.993807459 s.
  Selected d0001-t0035: 291.363636 days, ideal delta-v 3583.210826 m/s,
  final mass 887.966464 kg >=500 kg dry +50 kg reserve; spare 337.966464 kg.
  Decimal mass/reserve, endpoint/provenance/repeatability/offline checks pass.
- Only ideal M2 feasibility: Sun-point-mass coast/body-centre endpoints/scalar
  instantaneous maneuvers. Not finite-burn, operational or full-mission feasibility.
- M1/M2 and visual explorer are archived. UI uses M2 with R1 research export.
- D17.3 remains unclosed: 44.386790 km /185.850963 m/s; retained
  [ADR 0116](docs/adr/0116-quadratic-steering-stagnates-at-bounds.md).
- Strict M3/task 3.9 and full-force/finite-burn/end-to-end safety gates remain open.

## Paused — R5.3 once-only attempt failed

[ADR0148](docs/adr/0148-short-coast-oracle-rhs-limit.md): one attempt at clean24154be;
A native h1/h0.5 arcs complete, first A oracle hits10000 RHS/30021 body reads.
Study elapsed before flush1.8111813748255372s, finalization passed; no B model.
Separate offline audit:partial/study_verified=false,0.07836870802566409s, zero native.
No independent A agreement or Earth-force sensitivity result; final identity not reached.
287 protected files unchanged in diagnosis; no runtime/test/environment changes or replay.
[ADR0147](docs/adr/0147-short-coast-preparation-review.md): R5.2 preparation complete.
Reuse5255 full tests/Ruff from ADR0146; strict OpenSpec/evidence/link checks pass.
[ADR0149](docs/adr/0149-oracle-time-precision-diagnosis.md): user-requested read-only diagnosis;
119ns epoch grid/mixed time precision confirmed,7 scalar probes pass in0.03053s,
zero scientific imports/body queries/integrations; actual rejection cause unproven.
Automation remainsPAUSED. Instrumented solve needs a separate contract; no replay.
Preserve raw partial study/audit0148, inputs/kernels/gates and all prior evidence.

[ADR0136](docs/adr/0136-retained-boundaries-pass-arithmetic.md) completes R4 only
as endpoint arithmetic. Do not repeat R2/R3/R4/full tests on unchanged code.

[ADR0129](docs/adr/0129-reference-coast-verification-passes.md): R2 ideal coast passes
all121 nodes/both frames, max0.0021126122711470335m/3.9825899625221015e-10m/s.
[ADR0130](docs/adr/0130-full-regression-after-reference-verification.md):4852 full
tests pass in640.24s at7b22253. Do not repeat unchanged R2/full regression.
Automation remains paused; no further study is authorized by this failure record.
## Boundaries and references

- Preserve all historical JSON, scientific gates and immutable `moon_to_mars.py`.
- R1 cannot archive M3. M4/M5/M6, ML and object screening remain deferred.
- [Roadmap](openspec/ROADMAP.md), [active tasks](openspec/changes/refine-physical-trajectory/tasks.md), [requirements](openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
- [Rules](AGENTS.md), [ADR index](docs/adr/README.md), [M2 audit](docs/demo-audit.md).
