# Current State

Updated: 2026-10-30. Keep this file under 60 lines. Current instructions live
here and at the top of the roadmap; retained detail belongs in the ADRs.

## Goal and scheduling

Near-term product: one understandable research trajectory demonstrator with an
independently checked calculation and exportable result, not operational navigation.
Keep the long-term open-platform vision and Python/TudatPy/SPICE/Streamlit.
Automation `ariadna-m3` remains paused. No automatic D18 or repeated D17 study.

## Verified baseline

- Planning baseline: R1 priority at `ab9f2f5`; its earlier push failed. D17.3
  evidence at `866e593` was pushed. Report this stage's actual push outcome.
- M1/M2 and the visual explorer are archived. The working UI remains M2:
  explicit scenarios, impulsive search/Pareto, trajectory display and provenance.
- D17.3 ran once at clean `3434a31`: 503 nominal evaluations / 1006 arcs /
  76.614638 s; `ftol`, unclosed at 44.386790 km / 185.850963 m/s.
  Duration reached the reserve ceiling; no tighter repeat or mission qualification.
  See [ADR 0116](docs/adr/0116-quadratic-steering-stagnates-at-bounds.md).
- Last runtime verification: 607 focused tests pass (7.17 s); full 4588-test
  evidence (626.08 s) is from unchanged D17.2, not rerun for documentation.
- Strict M3/task 3.9 and full-force/finite-burn/end-to-end safety gates remain
  open. Local rank, lower residuals or format compatibility cannot close them.

## Next action — R1, not another local solver

[ADR 0117](docs/adr/0117-mission-first-demonstration-priority.md) records the
user-approved priority reset. Only planning/source-readiness records are complete.

1. R1.1 Accept [ADR 0118](docs/adr/0118-m2-reference-and-historical-data-readiness.md):
   explicit M2 hypothetical inputs, 50 kg reserve/100 m/s ideal allocation and
   bounded repeatability contract; separately instruct verification afterwards.
2. R1.2 Verify a small frozen physical calculation against an independent oracle
   or engine at that scope; stop on unavailable evidence or failed comparison.
3. R1.3 Specify minimal traceable results and an exact OEM profile/independent
   reader with conversion/rejection checks before implementing export.
4. R1.4 After readiness and a separate implementation instruction, deliver one
   input → calculation → display → export → independent decoding path; verify
   focused/full regressions and strict OpenSpec at implementation completion.

No native runs, new fixture or runtime/API/UI/exporter/dependency changes here.
ADR 0118's contract is proposed, not a positive result. MSL cruise is a metadata
candidate for later empirical comparison; maneuver-free coverage/uncertainty and
GRAIL gravity-version reconciliation remain open. Historical agreement cannot
replace a same-force oracle. R1.2 details and OEM profile remain unselected.

## Boundaries and references

- Preserve all historical JSON, scientific gates and immutable `moon_to_mars.py`.
- R1 success cannot archive M3. M4/M5/M6, ML and object screening remain deferred.
- [Roadmap](openspec/ROADMAP.md), [active tasks](openspec/changes/refine-physical-trajectory/tasks.md), [requirements](openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
- [Rules](AGENTS.md), [ADR index](docs/adr/README.md), [M2 audit](docs/demo-audit.md), [older history](docs/roadmap-history-2026-09-16.md).
