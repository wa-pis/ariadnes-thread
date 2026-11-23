# Current State

Updated: 2026-11-24. Keep under 60 lines; durable evidence in ADRs.

## Goal and scheduling
One independently checked research trajectory/export remains the goal.
Keep Python/TudatPy/SPICE/Streamlit and the extensible platform vision.
[ADR0239](docs/adr/0239-stop-diagnostics-at-a-feasibility-decision.md) stops automatic
R5.59 diagnostics. Next scientific objective: one independently checked analytical
witness or gap-free two-sign refusal on the existing [150 degrees, 152 degrees]
domain; otherwise inconclusive and stop. Existing evidence is still inconclusive.
[ADR0240](docs/adr/0240-choose-bounded-scalar-witness-search.md) selects bounded
Brent per Mars sign as a witness proposer, with unchanged independent point gates.
[ADR0241](docs/adr/0241-qualify-artificial-bounded-witness-search.md) implements
P3 artificial-only: 124 focused tests/Ruff pass, full 129-phase stress and audit.
Full portable: 6961 pass, 42 archival skips, 412 live deselections; checkout frozen.
[ADR0242](docs/adr/0242-finish-p3-regression-qualification.md): 412 live pass on4f5cbb3;
first repair:6964 portable pass. Two failed CI outcomes are preserved.
Latest executable-map/early-error repair:152 focused/6965 portable pass; CI pending.
Full P3 open, retained execution unavailable.
A different Mars phase changes the target and cannot enter the original R5.60.
Automation `ariadna-m3` stays PAUSED; no further saved execution is authorized.

## Latest verified science
[ADR0238](docs/adr/0238-record-versioned-saved-norms.md): R5.59z completed once on
clean f5437e4 through unchanged 0237; separate numerical audit returns verified.
72 boxes / 144 methods / 72 oracles / 72 diagonals / 72 comparisons per process.
All 72 saved-call checks pass; all 144 intervals contain the exact-real box range.
All 72 matched-input final enclosures equal: width differences 0, finite ratios 1.
Both authorizations consumed; no SPICE, integration or R5.60, and no retry.
No incoming/final-width attribution, general equivalence or physical conclusion.

## Verified test and CI maintenance
Commit e2b82fe: output lifecycle/clocks repaired, portable and live lanes required.
Local: 6837 portable + 412 live pass; exact JUnit union covers 7249 non-archive cases.
42 exact historical runtime/checkout or bit-replay cases are skipped, not verified.
Ubuntu CI 45016544787: 7212 pass, 42 archival + 37 platform skips, zero failures.
Ruff/strict OpenSpec pass; frozen checkout verified through both local full lanes.
No scientific source/dependency/evidence changes. No local runtime rerun for ADR0239/0240 docs.

## Preserved history and unresolved science
[ADR0221](docs/adr/0221-record-retained-inter-node-result.md): 64 unresolved leaves;
no continuous refusal. [ADR0217](docs/adr/0217-verify-the-saved-mars-phase-grid.md):
360 grid points fail mass floor; best gap 40.085 m/s, no continuous exclusion.
[ADR0228](docs/adr/0228-record-corrected-retained-observations.md): whole-cell speed
widths 94.115–98.406 m/s unresolved; singleton widths ~1.8e-89 m/s.
ADR0236 R5.59x and ADR0231 R5.59s remain failed/consumed/unchecked; no replay.
[ADR0119](docs/adr/0119-positive-ideal-m2-reference.md): d0001-t0035 ideal reference;
[ADR0129](docs/adr/0129-reference-coast-verification-passes.md): 121 ideal nodes only.
No accepted executable pair, physical join, D17.3/strict M3/task 3.9 or mission safety.
R5.60 closed. No retained optimizer/D17/D18/M4–M6/ML/UI qualification/publication.
Use pinned Conda; preserve all historical contracts/evidence and moon_to_mars.py.
