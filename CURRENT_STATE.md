# Current State

Updated: 2026-11-19. Keep under 60 lines; durable evidence is in ADRs.

## Goal and scheduling
Near-term product: one understandable independently checked research trajectory/export.
Keep Python/TudatPy/SPICE/Streamlit and the extensible open-platform vision.
User selected retained-cell observational design; [ADR0224](docs/adr/0224-design-retained-cell-observations.md)
freezes rows 62/94/125 and their midpoint singletons (24 traces + 24 controls).
Automation `ariadna-m3` is PAUSED after qualified R5.59m artificial preparation.
Next: separate explicit instruction for at-most-once R5.59n under unchanged ADR0224.
No retained numerical work, SPICE, new trajectory/points or formula change is authorized now.

## Latest verified implementation
[ADR0225](docs/adr/0225-qualify-retained-cell-observation-adapter.md): R5.59m adapter,
scope-specific observer and separate saved-only verifier qualified on fabricated archives.
24 traces equal controls; six fabricated historical bound matches; 24×16 sampled checks.
48 bounds / 0 new direct points / 1,216 events; 12 producer + 6 audit oracle-mass calls.
Full-volume source 2,444,501 bytes; combined evidence 3,640,925 bytes.
External producer 1.189270209 s; separate audit 0.239020125 s; no retained launch.
38 focused / 6,560 guarded full passes, 494 explicit exclusions; Ruff/strict OpenSpec pass.
Base a7fbb59 plus exact tested new source hashes in ADR0225's verification manifest.
Historical arithmetic, contract and evidence unchanged; retained widening attribution unproved.

## Unresolved retained question
[ADR0221](docs/adr/0221-record-retained-inter-node-result.md): sole R5.59i attempt
and audit agree on inconclusive: 126 cells / 252 bounds / 129 phases;
64 unresolved depth-5 cells; no witness or two-sign continuous exclusion. Consumed.
[ADR0222](docs/adr/0222-diagnose-saved-positive-bound-widths.md): positive lower mass
bounds 1,499.102–1,499.262 kg do not exceed 1,500 kg; arrival norm widths
94.115–98.406 m/s precede the mass map, but internal widening attribution is unproved.
[ADR0217](docs/adr/0217-verify-the-saved-mars-phase-grid.md): all 360 saved grid
points fail the floor; best gap 40.085 m/s. Between-node feasibility remains open.
R5.59c/f/i consumed; original incomplete/negative evidence remains immutable.
R5.60 is unavailable until an eligible frozen command pair and readiness are accepted.

## Scientific baseline and limits
[ADR0119](docs/adr/0119-positive-ideal-m2-reference.md): ideal candidate d0001-t0035,
291.363636 days, delta-v 3583.210826 m/s, final mass 887.966464 kg;
Sun-point-mass/body-centre/instantaneous-maneuver model only.
[ADR0129](docs/adr/0129-reference-coast-verification-passes.md): R2 verifies all 121
ideal coast nodes. This does not qualify finite burns or full-model continuity.
M1/M2 and visual explorer are archived; UI uses M2 with R1 research export.
D17.3, strict M3/task 3.9, physical continuity and end-to-end mission safety remain open.
Do not start D17/D18, new search/optimizer, M4–M6, ML, UI qualification or external publication.
Use the pinned Conda environment; preserve historical evidence and `moon_to_mars.py`.
