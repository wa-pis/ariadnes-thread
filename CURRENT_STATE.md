# Current State

Updated: 2026-11-01. Keep this file under 60 lines. Current instructions live
here and at the top of the roadmap; retained detail belongs in the ADRs.

## Goal and scheduling

Near-term product: one understandable research trajectory demonstrator with an
independently checked calculation and exportable result, not operational navigation.
Keep Python/TudatPy/SPICE/Streamlit and the long-term open-platform vision.
Automation `ariadna-m3`: active every 5 minutes by user instruction 2026-11-01.
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

## Next action — R5.2 short-coast verifier preparation

[ADR0137](docs/adr/0137-short-coast-earth-gravity-contract.md) freezes a300s
unpowered parked-state Sun/Moon versus Sun/Moon/Earth direct-SSB comparison.
Same audited0098 initial state/R1 candidate; pinned SciPy1.17.1 already installed.
Verified helpers: [oracle](docs/adr/0138-independent-short-coast-oracle.md),
[native](docs/adr/0140-native-short-coast-adapter.md) and
[inputs/runtime](docs/adr/0141-short-coast-input-and-runtime-identity.md).
ADR0141 baseline:5095 full tests pass; no R5 reference state propagated.
[ADR0142](docs/adr/0142-short-coast-orchestration-and-evidence.md): runner implemented;
37 new/81 focused and5132 full tests pass in647.31s; Ruff/strict OpenSpec pass.
All260 protected tracked files unchanged; no R5 reference propagation.
[ADR0143](docs/adr/0143-independent-saved-evidence-audit-contract.md): audit design verified;
next implement private0144 offline auditor with its tests before R5.2 completion.

[ADR0136](docs/adr/0136-retained-boundaries-pass-arithmetic.md) completes R4 only
as endpoint arithmetic. Do not repeat R2/R3/R4/full tests on unchanged code.

[ADR0129](docs/adr/0129-reference-coast-verification-passes.md): R2 ideal coast passes
all121 nodes/both frames, max0.0021126122711470335m/3.9825899625221015e-10m/s.
[ADR0130](docs/adr/0130-full-regression-after-reference-verification.md):4852 full
tests pass in640.24s at7b22253. Do not repeat unchanged R2/full regression.
Automatic bounded continuation is authorized; pause if user input/action is needed.
## Boundaries and references

- Preserve all historical JSON, scientific gates and immutable `moon_to_mars.py`.
- R1 cannot archive M3. M4/M5/M6, ML and object screening remain deferred.
- [Roadmap](openspec/ROADMAP.md), [active tasks](openspec/changes/refine-physical-trajectory/tasks.md), [requirements](openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
- [Rules](AGENTS.md), [ADR index](docs/adr/README.md), [M2 audit](docs/demo-audit.md).
