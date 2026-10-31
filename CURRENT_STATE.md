# Current State

Updated: 2026-10-31. Keep this file under 60 lines. Current instructions live
here and at the top of the roadmap; retained detail belongs in the ADRs.

## Goal and scheduling

Near-term product: one understandable research trajectory demonstrator with an
independently checked calculation and exportable result, not operational navigation.
Keep Python/TudatPy/SPICE/Streamlit and the long-term open-platform vision.
Automation `ariadna-m3` remains paused. No automatic D18 or repeated D17 study.

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
- 18 native-free runner checks, offline evidence audit, Ruff, strict OpenSpec,
  links/diff/immutable checks pass. Production tests unchanged; full suite not
  rerun for this bounded evidence stage. Prior full 4588 tests/626.08 s are D17.2
  evidence; 607 focused/7.17 s are D17.3 evidence, not fresh R1 regressions.
- M1/M2 and visual explorer are archived. UI remains M2, unchanged in R1.1.
- D17.3 remains unclosed: 44.386790 km /185.850963 m/s; retained
  [ADR 0116](docs/adr/0116-quadratic-steering-stagnates-at-bounds.md).
- Strict M3/task 3.9 and full-force/finite-burn/end-to-end safety gates remain open.

## Next action — separately implement the R1.4 usable path

[ADR 0117](docs/adr/0117-mission-first-demonstration-priority.md) fixes the order;
accepted ADR 0118 and its verified R1.1 result remain retained in ADR 0119.

1. [ADR 0122](docs/adr/0122-independent-elliptic-coast-passes.md): R1.2 passes at
   base `35ae8a3`, exactly17 adapter calls in 0.5558036253787577s, no retries.
   Max differences 0.00159834m /3.66733e-10m/s; roots/alignment/invariants and
   offline identity/arithmetic audit pass. Synthetic Sun-relative coast only.
2. [ADR 0124](docs/adr/0124-oem-reader-and-research-profile-ready.md): R1.3 research
   readiness verified: corrected source, approved unregistered ARIADNA notice,
   actual INPOP19a/ICRF mapping, independent reader/88 native-free tests. Strict
   OpenSpec/lint/links pass; no writer/UI/native or full-regression work here.
3. R1.4 After readiness and separate implementation instruction, deliver one
   input → calculation → display → export → independent decoding path;
   verify focused/full regressions and strict OpenSpec at implementation completion.

Historical MSL/GRAIL metadata does not authorize replay; maneuver-free coverage,
uncertainty and gravity-version reconciliation remain unverified. No retries,
new solver/physics, API/UI/exporter/dependency changes or automation restart.

## Boundaries and references

- Preserve all historical JSON, scientific gates and immutable `moon_to_mars.py`.
- R1 cannot archive M3. M4/M5/M6, ML and object screening remain deferred.
- [Roadmap](openspec/ROADMAP.md), [active tasks](openspec/changes/refine-physical-trajectory/tasks.md), [requirements](openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
- [Rules](AGENTS.md), [ADR index](docs/adr/README.md), [M2 audit](docs/demo-audit.md).
