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

## Next action — one offline audit of retained physical endpoints

[ADR0135](docs/adr/0135-fixed-orbit-boundary-contract.md) fixes retained0098
initial/target boundaries at R1 epochs with unchanged orbital phases/harmonic GMs.
Full-model joins remain actual burn cutoff/ignition; no arbitrary matching sphere.
Next R4.3: once-only10s/zero-native binary64 versus80/100-digit Decimal orbital
arithmetic audit at0.001m/1e-6m/s relative/SSB gates; exclusive evidence, no retry.
No propagation/controls/new observed states; mission experiment commands/dynamical
reference/native budget remain unresolved. Read the full frozen ADR before work.
[ADR0134](docs/adr/0134-boundary-evidence-reuse.md): R1/D13 inputs match;
reuse local evidence, not local-state splices. [ADR0133](docs/adr/0133-three-epoch-gravity-screening.md)
completes only local force sampling. No unchanged R2/R3/full-suite reruns.
[ADR0132](docs/adr/0132-gravity-screening-preparation.md):4936 tests/Ruff pass.

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
