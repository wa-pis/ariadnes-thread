# Current State

Updated: 2026-09-16. Keep this file under 60 lines; replace stale status instead
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

Perform D1 in the roadmap: inspect scenario → search → selected candidate → UI
and list the smallest missing pieces for one demonstration. Reuse existing
outputs; do not start another expensive safety-bound experiment.
Before implementation, reconcile the active OpenSpec artifacts with the proposed
slice and validate strictly. Changed scientific gates need explicit approval.

## Boundaries and references

- No tolerance changes, completed-task claims, M4–M6 work, ML or exporters now.
- Preserve research evidence and the immutable `moon_to_mars.py`.
- Rules: [AGENTS.md](AGENTS.md).
- Plan: [roadmap](openspec/ROADMAP.md).
- Outstanding checks: [active tasks](openspec/changes/refine-physical-trajectory/tasks.md).
- Latest evidence: [Decision 0078](docs/decisions/0078-fourth-gravity-sum.md).
- Older detail: [historical roadmap](docs/roadmap-history-2026-09-16.md).
