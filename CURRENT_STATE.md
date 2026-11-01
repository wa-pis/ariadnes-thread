# Current State

Updated: 2026-11-01. Keep this file under 60 lines. Current instructions live
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
- R1.1 offline/identity/reserve checks pass; R1.4 full regressions are below.
  D17.2/D17.3 test counts remain historical evidence, not new reference checks.
- M1/M2 and visual explorer are archived. UI uses M2 with R1 research export.
- D17.3 remains unclosed: 44.386790 km /185.850963 m/s; retained
  [ADR 0116](docs/adr/0116-quadratic-steering-stagnates-at-bounds.md).
- Strict M3/task 3.9 and full-force/finite-burn/end-to-end safety gates remain open.

## Next action — choose the next user-visible priority
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
3. [ADR0125](docs/adr/0125-research-export-and-usable-path.md): R1.4 implements the
   input → calculation → display → verified JSON/OEM path; implementation complete. 151 focused
   and4766 full tests/630.19s pass; Ruff/strict OpenSpec/links/immutable checks pass.
   Local UI:127.0.0.1:8501. Original model/environment/evidence remain unchanged.

R2 complete for the retained ideal coast: [ADR0129](docs/adr/0129-reference-coast-verification-passes.md).
Exactly121 Sun reads; all121 nodes/both frames pass at max0.0021126122711470335m /
3.9825899625221015e-10m/s; root/invariant/resource/budget gates and offline audit pass.
Raw Sun track, comparisons and audit retained; no retries or runtime changes.
Shared ephemeris truth, continuous safety, finite burns and strict M3 stay unverified.
Choose the next priority separately; no automatic study, UI qualification or automation.
## Boundaries and references

- Preserve all historical JSON, scientific gates and immutable `moon_to_mars.py`.
- R1 cannot archive M3. M4/M5/M6, ML and object screening remain deferred.
- [Roadmap](openspec/ROADMAP.md), [active tasks](openspec/changes/refine-physical-trajectory/tasks.md), [requirements](openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
- [Rules](AGENTS.md), [ADR index](docs/adr/README.md), [M2 audit](docs/demo-audit.md).
