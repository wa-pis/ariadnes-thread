# Current State

Updated: 2026-09-23. Keep this file under 60 lines; replace stale status instead
of appending a diary. This is a navigation aid, not an alternative specification.

## Goal and scheduling

One reproducible, understandable Moon-to-Mars demonstration with the existing
stack and UI. Prioritize the end-to-end result over further numerical-proof work.
Automation `ariadna-m3` is paused by user request. Do not restart it automatically.

## Verified baseline

- Scientific baseline: `bbe61db`, pushed to `origin/dev` before this planning edit.
- M1 and M2 are archived; the Streamlit impulsive-transfer explorer is delivered.
- M3 remains open, not an operational high-fidelity mission capability. Task 3.9
  and end-to-end finite-burn/safety/runtime checks remain unresolved.
- Decision 0078 assembled eight nominal gravity contributions, not a full-force
  trajectory certificate. Baseline verification recorded 3,496 passing tests;
  these were not rerun for this documentation-only planning change.

## Next action

D1 is complete at inspected revision `f132d8a`: scenario/search/selection/UI
already work. All 14 explorer and UI tests passed in 3.83 s; the full suite was
not rerun. Pytest cache writing was denied by the sandbox (warning only).
See [audit](docs/demo-audit.md) for evidence and limitations.
D2 is specified in the active proposal/design/tasks and visual-explorer delta.
Next: implement D3 tasks 0.1–0.3, a read-only "О расчёте" panel reusing CLI
metadata with a detached normalized-input snapshot and atomic invalidation.
No code or scientific gate changed during D2; runtime tests were not rerun.
No new dynamics work; changed scientific gates still need explicit approval.

## Boundaries and references

- No tolerance changes, completed-task claims, M4–M6 work, ML or exporters now.
- Preserve research evidence and the immutable `moon_to_mars.py`.
- Rules: [AGENTS.md](AGENTS.md).
- Plan: [roadmap](openspec/ROADMAP.md).
- Outstanding checks: [active tasks](openspec/changes/refine-physical-trajectory/tasks.md).
- Latest evidence: [Decision 0078](docs/decisions/0078-fourth-gravity-sum.md).
- Older detail: [historical roadmap](docs/roadmap-history-2026-09-16.md).
