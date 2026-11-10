# Current State

Updated: 2026-11-10. Keep under60 lines; current instructions here/roadmap, detail in ADRs.

## Goal and scheduling
Near-term product: one understandable independently checked research trajectory/export.
Keep Python/TudatPy/SPICE/Streamlit and the long-term open-platform vision.
Automation `ariadna-m3`: PAUSED after R5.3 cap failure, per user instruction.
Pause immediately when user input/action is needed; no automatic D17/D18 replay.

## Verified baseline
- R1.1 passed at base `5c7012c`; runner/fixture untracked, exact hashes in ADR0119;
  [ADR 0119](docs/adr/0119-positive-ideal-m2-reference.md): exactly two identical
  1980-attempt searches/two 121-state samplings in shared 1.993807459 s.
  Selected d0001-t0035: 291.363636 days, ideal delta-v 3583.210826 m/s,
  final mass 887.966464 kg >=500 kg dry +50 kg reserve; spare 337.966464 kg.
  Decimal mass/reserve, endpoint/provenance/repeatability/offline checks pass.
- Only ideal M2 feasibility: Sun-point-mass coast/body-centre endpoints/scalar
  instantaneous maneuvers; finite-burn/mission feasibility unverified.
- M1/M2 and visual explorer are archived. UI uses M2 with R1 research export.
- D17.3 remains unclosed: 44.386790 km /185.850963 m/s; retained
  [ADR 0116](docs/adr/0116-quadratic-steering-stagnates-at-bounds.md).
- Strict M3/task 3.9 and full-force/finite-burn/end-to-end safety gates remain open.
## Paused — R5.3 once-only attempt failed
[ADR0148](docs/adr/0148-short-coast-oracle-rhs-limit.md): one attempt at clean24154be;
A native h1/h0.5 arcs complete, first A oracle hits10000 RHS/30021 body reads.
Separate offline audit:partial/study_verified=false,0.07836870802566409s, zero native.
No independent A agreement or Earth-force sensitivity result; final identity not reached.
304 prior protected files preserved; production/environment/legacy unchanged, no replay.
[ADR0149](docs/adr/0149-oracle-time-precision-diagnosis.md): user-requested read-only diagnosis;
119ns epoch grid/mixed time precision confirmed,7 scalar probes pass in0.03053s,
zero scientific imports/body queries/integrations; actual rejection cause unproven.
[ADR0150](docs/adr/0150-synthetic-step-trace-and-binary-localization.md):
Synthetic tracing/search complete:37/73/2413 RHS,64 rounded-time rejections,
all endpoint gates pass; first bad callback at0.052600152s, not a time crossing.
5285 full tests/Ruff reused; strict OpenSpec and saved-data checks pass.
[ADR0151](docs/adr/0151-frozen-stage-error-attribution.md):39 frozen stages/234 fields
pass in0.067s; clock-only norm15.679 versus reference0.02889, actual15.734.
Explains first frozen synthetic estimator rejection; historical R5 cause unverified.
[ADR0129](docs/adr/0129-reference-coast-verification-passes.md): R2 ideal coast passes121 nodes/both frames; preserve evidence.
[ADR0152](docs/adr/0152-compensated-synthetic-time-validation.md):34 focused/5319 full
pass; candidate61 RHS/5 accepted/0 rejected, all gates pass, provider floor retained.
[ADR0154](docs/adr/0154-resume-real-ephemeris-verification.md): readiness/90 focused/5409 full pass, exact restored sources/gates unchanged.
[ADR0155](docs/adr/0155-real-ephemeris-time-boundary-passes.md):21 real source states/all gates pass;84 returns audited; same-model arithmetic only; source discrepancy11.4um retained.
[ADR0157](docs/adr/0157-prepare-fixed-state-gravity-check.md):221 new/5630 full tests/Ruff passed; tested code remains unchanged.
[ADR0158](docs/adr/0158-fixed-position-real-gravity-passes.md):R5.11 study/audit pass21 rows/14 totals,0.4372s/0.3447s; fixed-X arithmetic only.
[ADR0160](docs/adr/0160-prepare-moving-coordinate-check.md):ADR0159 preparation;251 focused/5881 full/Ruff pass; tested bytes unchanged.
[ADR0161](docs/adr/0161-moving-coordinate-arithmetic-passes.md):R5.14 study/audit pass7/21/168/63/14 in0.630s/0.574s;370 protected files unchanged. Controlled q/w and real-source arithmetic only.
[ADR0162](docs/adr/0162-corrected-real-integration-contract.md):R5.15 design complete; two future A-only300s solves, original gates/inputs, bounded sampled audit.
[ADR0163](docs/adr/0163-prepare-corrected-integration.md):R5.16 complete;301 focused/6182 full/Ruff pass, tested hashes frozen. Artificial-source checks only.
[ADR0164](docs/adr/0164-corrected-coast-force-gate-fails.md):R5.17 attempt consumed;both300s solves/21 trajectory comparisons pass, but Moon overall force gate fails at normal RHS6/local0.25s by8.8864%; audit partial/scientific_verified=false, final identity unavailable.
External2.704s/1.643s, finalizations/caps pass;5132 RHS/15417 states/424 trials, no native propagation.6182 tests/Ruff reused on unchanged bytes.
[ADR0165](docs/adr/0165-reproduce-lunar-source-rounding.md):R5.18 localizes 13.269 µm before SI /16.645 µm after; staged centre sum reproduces42/42 saved position components. No native work/replay.
[ADR0178](docs/adr/0178-consolidate-lunar-force-coverage.md): R5.31 covers 28/28 frozen rows: 7 captured in R5.24, 10 bitwise matches, 11 confirmed by R5.30. Both Moon gates supported; no new evaluations. R5.17 stays failed; M3 open, automation PAUSED.
## Boundaries and references
- Preserve all historical JSON, scientific gates and immutable `moon_to_mars.py`.
- R1 cannot archive M3. M4/M5/M6, ML and object screening remain deferred.
- [Roadmap](openspec/ROADMAP.md), [active tasks](openspec/changes/refine-physical-trajectory/tasks.md), [requirements](openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
- [Rules](AGENTS.md), [ADR index](docs/adr/README.md), [M2 audit](docs/demo-audit.md).
