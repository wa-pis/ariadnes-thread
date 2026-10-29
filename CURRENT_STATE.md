# Current State

Updated: 2026-10-29. Keep this file under 60 lines. Current instructions live
here and at the top of the roadmap; retained detail belongs in the ADRs.

## Goal and scheduling

Near-term product: one understandable research trajectory demonstrator with an
independently checked calculation and exportable result, not operational navigation.
Keep the long-term open-platform vision and Python/TudatPy/SPICE/Streamlit.
Automation `ariadna-m3` remains paused. No automatic D18 or repeated D17 study.

## Verified baseline

- Latest completed stage: D17.3 evidence at `866e593`, pushed to `origin/dev`.
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
user-approved priority reset. Only its planning record is complete.

1. R1.1 Specify the mission/demo problem, actual model fidelity, boundary rationale
   and positive reference with predeclared nonzero reserve, tolerances and budget.
2. R1.2 Verify a small frozen physical calculation against an independent oracle
   or engine at that scope; stop on unavailable evidence or failed comparison.
3. R1.3 Specify minimal traceable results and an exact OEM profile/independent
   reader with conversion/rejection checks before implementing export.
4. R1.4 After readiness and a separate implementation instruction, deliver one
   input → calculation → display → export → independent decoding path; verify
   focused/full regressions and strict OpenSpec at implementation completion.

No new native runs, runtime/API/UI/exporter/dependency changes in this planning
stage. Exact fixture, reserves, benchmark limits/tolerances and OEM profile remain
unselected; they must be accepted before the corresponding implementation/run.

## Boundaries and references

- Preserve all historical JSON, scientific gates and immutable `moon_to_mars.py`.
- R1 success cannot archive M3. M4/M5/M6, ML and object screening remain deferred.
- [Roadmap](openspec/ROADMAP.md), [active tasks](openspec/changes/refine-physical-trajectory/tasks.md), [requirements](openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
- [Rules](AGENTS.md), [ADR index](docs/adr/README.md), [M2 audit](docs/demo-audit.md), [older history](docs/roadmap-history-2026-09-16.md).
