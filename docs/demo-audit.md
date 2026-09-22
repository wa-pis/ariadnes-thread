# D1 — Existing demonstration audit

Date: 2026-09-22. Inspected revision: `f132d8a`, initially clean working tree.
Scope: existing M2 scenario/search/sampling/Streamlit path, not M3 qualification.

## What already works

| Stage | Implementation | Evidence |
|---|---|---|
| Explicit input | `explorer_ui._load_example` loads the reference TOML only after a click; `scenario_from_mapping` normalizes edited fields. | AppTest checks initial empty inputs, edits and invalid-date rejection. |
| Search | `search_impulsive_transfers` computes the existing M2 Pareto front. | UI tests run real search; sampler test selects `d0001-t0035`. |
| Selection and summary | UI selects Pareto candidates and displays UTC dates, flight time, ideal delta-v, propellant and mass feasibility. | AppTest switches candidates and recalculates after a dry-mass edit. |
| Approximate trajectory | `sample_transfer` samples 121 states; UI draws Sun-relative J2000 XY and provides a time slider and SI/SSB state details. | Analytic circle checks, endpoint checks and repeated identical samples pass; slider test retains the search result. |
| Failure and scope | Inputs or resource errors remove previous results; M2 limitations and reference propellant shortfall are visible. | Invalid-input, search-failure and sampling-failure AppTests pass. |

Verification: `conda run --no-capture-output -n space-nav python -m pytest -q
tests/test_explorer.py tests/test_explorer_ui.py`: **14 passed in 3.83 s**.
One warning: sandbox denied writing pytest's cache; no test failed. The complete
suite was not rerun. AppTest exercises the application, not browser visual QA.

## Smallest missing slice proposed for D2

The UI does not display a calculation provenance manifest. The CLI already has
`_manifest` / `_plan_payload`; `transfer._transfer_model_manifest` records model,
solver, grid, resource version and constants. Reuse these conventions rather
than invent a second report format or new dynamics implementation.

Before implementation, specify a compact read-only provenance panel tied to the
actual edited scenario and successful calculation. Check that input edits and
errors invalidate provenance along with results, slider changes do not repeat
search, and displayed model/resource fields match the existing CLI conventions.
The CLI's path-based scenario handling must not falsely identify an edited UI
scenario as the unchanged example file. Agree this in the active OpenSpec change.

No new exporter, ML model, 3D viewer or all-candidate retention is needed for this
slice. The UI currently shows the Pareto front, not every evaluated candidate.
The existing example remains intentionally mass-infeasible; changing dry mass
is an explicit user action, not a hidden fix. Finite burns, lunar escape and
Martian capture remain unvalidated by this demonstration.
