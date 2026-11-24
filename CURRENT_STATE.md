# Current State

Updated: 2026-11-24. Keep under 60 lines; durable evidence in ADRs.

## Goal and scheduling
One independently checked research trajectory/export remains the goal.
Keep Python/TudatPy/SPICE/Streamlit and the extensible platform vision.
[ADR0239](docs/adr/0239-stop-diagnostics-at-a-feasibility-decision.md) stops automatic
R5.59 diagnostics. User selected one admissible analytical pair plus independent
audit on fixed saved inputs. No witness means inconclusive and stop; Brent
cannot prove continuous refusal. Existing evidence remains inconclusive.
[ADR0240](docs/adr/0240-choose-bounded-scalar-witness-search.md) selects bounded
Brent per Mars sign as a witness proposer, with unchanged independent point gates.
[ADR0241](docs/adr/0241-qualify-artificial-bounded-witness-search.md) implements
P3 artificial-only: 124 focused tests/Ruff pass, full 129-phase stress and audit.
Full portable: 6961 pass, 42 archival skips, 412 live deselections; checkout frozen.
[ADR0242](docs/adr/0242-finish-p3-regression-qualification.md) closes P3 preparation:
412 local live pass on4f5cbb3; latest repair152 focused/6965 local portable pass.
CI45260154283 on1812360:7340 pass,42 archival+37 platform skips,0fail/error;
all128 P3 cases pass; all7419 case IDs match local combined inventories.
Both failed CI outcomes preserved; retained execution remains unavailable.
[ADR0243](docs/adr/0243-design-one-retained-bounded-attempt.md) designs one fixed
saved attempt: P4/P5 complete; one fixed P6 dispatch remains pending.
[ADR0244](docs/adr/0244-start-bounded-autonomous-preparation.md): P5a point unit
passes161 focused/6998 portable/412 live and CI45347814462; unit-only qualification.
[ADR0245](docs/adr/0245-qualify-retained-dispatch-lifecycle.md): P5 complete;53 new cases,
7051 portable/412 live pass; CI45358338765 on aad842f and fixed readiness verified.
A different Mars phase changes the target and cannot enter the original R5.60.
Automation ACTIVE/5min; user goal:one admissible saved pair with independent audit.

## Latest verified science
[ADR0238](docs/adr/0238-record-versioned-saved-norms.md): R5.59z completed once on
clean f5437e4 through unchanged 0237; separate numerical audit returns verified.
72 boxes / 144 methods / 72 oracles / 72 diagonals / 72 comparisons per process.
All 72 saved-call checks pass; all 144 intervals contain the exact-real box range.
All 72 matched-input final enclosures equal: width differences 0, finite ratios 1.
Both authorizations consumed; no SPICE, integration or R5.60, and no retry.
No incoming/final-width attribution, general equivalence or physical conclusion.

## Verified test and CI maintenance
Latest P5 code:f572464c dispatcher; frozen1359-file checkout on3760152+additive0245.
7505 exact local/CI IDs; CI7426pass+42archive+37platform skips, all53 new cases pass.
Ruff/strict/review pass;53 new invocation cases pass in the full portable lane.
P5a CI45347814462 remains verified. New saved searches/mission experiments:0.
42 exact historical checks unverified; arithmetic/dependencies/workflow unchanged.
Ordinary live regression used native/SPICE resources; fixed retained readiness now present.

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
