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
  trajectory certificate. D3 verification: 3,502 tests pass in 608.17 s;
  29 focused checks, Ruff, strict OpenSpec and unchanged legacy checksum pass.

## Next action

D1–D3 are complete. The "О расчёте" panel reuses CLI metadata and records
normalized edited inputs; result/provenance invalidation and reuse are tested.
Implementation was based on `6a80424`; its commit is identifiable from Git history.
See [audit](docs/demo-audit.md) for the original gap and active tasks for closure.
Next: implement the specified explorer usability tasks UI.1–UI.4: elapsed days,
visible candidate budget/grid, priorities and ideal-fuel filtering. No code has
changed for this follow-up yet. Then review D4 scope before physical refinement;
do not automatically resume task-3.9 research.
Browser visual QA was not performed; application behavior was checked by AppTest.
Changed scientific gates still need explicit approval.

## Boundaries and references

- No tolerance changes, completed-task claims, M4–M6 work, ML or exporters now.
- Preserve research evidence and the immutable `moon_to_mars.py`.
- Rules: [AGENTS.md](AGENTS.md).
- Plan: [roadmap](openspec/ROADMAP.md).
- Outstanding checks: [active tasks](openspec/changes/refine-physical-trajectory/tasks.md).
- Latest evidence: [Decision 0078](docs/decisions/0078-fourth-gravity-sum.md).
- Older detail: [historical roadmap](docs/roadmap-history-2026-09-16.md).
