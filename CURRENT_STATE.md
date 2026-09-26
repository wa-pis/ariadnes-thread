# Current State

Updated: 2026-09-27. Keep this file under 60 lines; replace stale status instead
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
UI follow-up delivered: elapsed days, visible budget/grid, priorities and ideal-fuel
filter, Russian field/result help and unscreened-object warning. Based on `3da51c7`
plus the subsequently approved specification edits. 33 focused checks and 3,506
full-suite tests pass (623.39 s); Ruff, strict OpenSpec and legacy checksum pass.
The candidate ceiling is now 10000 (default 2000, default deadline 300 s).
UI.7: 94 focused checks and 3,507 full-suite tests pass (625.11 s); real reference
search: 10000 solved, 35 Pareto entries, 3.175 s on this machine. Scientific
model/tolerances are unchanged; details are recorded in the active tasks.
D4.1/D4.2 delivered: immutable research reports, shared six-arc budget, three-arc
composition and sampled guards. Baseline `e9f125c`: 242 focused checks and
3,583 full-suite tests pass (585.16 s); Ruff, strict OpenSpec and legacy pass.
D4.3 complete, based on `e9f125c`: fixed commands, fresh environment and shared
deadline; 124 focused checks and 3,598 full-suite tests pass (626.61 s).
Ruff, strict OpenSpec and legacy pass. Partial failures remain unqualified.
D4.4 complete: six arcs in 20.10 s; agreement fails (1751.29 m), miss ~198M km.
Based on `2aca9f6`: 130 focused / 3,604 full tests pass (607.53 s); static checks pass.
D4.5 complete: replay 22.11 s; exact science/source match; 130 focused tests pass.
No whole-interval safety claim; strict M3 gates remain open. Catalogue screening
is deferred. Do not automatically resume task-3.9 proof research.
Browser visual QA was not performed; application behavior was checked by AppTest.
Next: agree bounded identical-start coast diagnosis; no changed scientific gates.

## Boundaries and references

- Future optional display/gravity/screening: [deferred draft](openspec/deferred/optional-object-analysis/spec.md); not implemented or an active change.
- No tolerance changes, completed-task claims, M4–M6 work, ML or exporters now.
- Preserve research evidence and the immutable `moon_to_mars.py`.
- Rules: [AGENTS.md](AGENTS.md).
- Plan: [roadmap](openspec/ROADMAP.md).
- Outstanding checks: [active tasks](openspec/changes/refine-physical-trajectory/tasks.md).
- Latest evidence: [Decision 0081](docs/decisions/0081-research-reproducibility.md); repeatable, not accurate.
- Older detail: [historical roadmap](docs/roadmap-history-2026-09-16.md).
