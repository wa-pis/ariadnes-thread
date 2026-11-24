# Current State

Updated: 2026-11-25. Keep under 60 lines; durable evidence in ADRs.

## Current planning result
[ADR0247](docs/adr/0247-formulate-coupled-moon-mars-problem.md) documents F1:
[requirements/variable ledger and coupled F0 problem](openspec/changes/refine-physical-trajectory/design.md#coupled-moon-to-mars-formulation-2026-11-25).
Fixed orbital boundaries/epochs and six existing finite-burn TNW controls;
one full-force position/velocity/mass history, derived masses and switching times.
M2/excess vectors are seeds, not extra physical endpoint equalities.
Auxiliary shooting nodes would require continuity; no method/node count selected.
Free dates/phases or orbit-membership targeting remain proposed, not adopted.
Strict gates unchanged. Docs-only checks; no scientific calculations/SPICE/integration.
Next F2: specify one minimal independent benchmark and method contract before
implementation/runs; explicitly resolve any proposed boundary change first.
Keep pinned Python/TudatPy/SPICE/Streamlit and the extensible platform vision.

## Goal and stop state
One independently audited admissible analytical pair was the user-selected goal;
it remains unmet. No 99% probability, physical closure or safety claim.
Automation `ariadna-m3` remains PAUSED after the once-only P6 result.
F1 authorizes documentation only, no automatic successor or scientific run.

## Latest scientific result
[ADR0246](docs/adr/0246-record-bounded-retained-inconclusive.md): on clean33fea7c,
one unchanged0245 retained command returns complete inconclusive exit2:
no-verified-witness. Separate stdlib audit exit0 verifies all13 recorded points
and counters/eligibility; zero optimizer replay, namespace0243-p3-retained consumed.
Positive proposal151.33118995827647deg fails commanded-dry-floor:
6157.712787309595m/s against6117.706618414368m/s budget; negative objective guarded.
No continuous refusal, global optimum or physical mission impossibility proved.
13phases/26slots; parent1.048381667s;312980B namespace; all caps/pins agree.
No SPICE/integration/force/R5.60 work. P6 execution complete; physical join open.

## Qualified preparation and preserved boundaries
[ADR0245](docs/adr/0245-qualify-retained-dispatch-lifecycle.md): qualified code
aad842f, readiness33fea7c;53 new invocation tests,7051 portable/412 live pass,
42 archival skips;7505 exact local/CI IDs. CI45358338765:7426 passes,
42archive+37platform skips, all37platform cases pass locally. Ruff/review/strict pass.
Tests reused for subsequent documentation-only records; no fresh runtime claim.
[ADR0129](docs/adr/0129-reference-coast-verification-passes.md):121 ideal nodes only.
[ADR0135](docs/adr/0135-fixed-orbit-boundary-contract.md) and
[ADR0205](docs/adr/0205-design-fixed-command-physical-join.md) retain fixed boundaries,
join/error-bound/readiness gates; changed Mars phase is not the R5.60 target.
No executable pair, physical join, strict M3/task3.9 or mission safety established.
No retry/resume/overwrite, changed inputs/caps/tolerances, new method/physics,
M4–M6/ML/UI qualification/publication without an accepted contract and authority.
Use pinned Conda, dev/origin only; preserve all history and moon_to_mars.py.
