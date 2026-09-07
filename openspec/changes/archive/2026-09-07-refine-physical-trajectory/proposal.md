## Why

The user prioritizes a usable Streamlit research prototype over high-fidelity M3. The existing change ID is retained to keep one open change. Former M3 documents and task states are preserved in `openspec/deferred/refine-physical-trajectory`, not completed.

## What Changes

Add a local Streamlit input form, existing M2 search, candidate selection, sampled trajectory, and time slider. Reuse scenario validation and TudatPy/SPICE; pin Streamlit and Plotly in Conda.

## Capabilities

### New Capabilities

- `visual-transfer-explorer`: explicit mission inputs, approximate transfer exploration, and honest model limitations.

## Non-goals

High-fidelity refinement, real engine schedules, estimation, TCMs, exports, hosting, accounts, other mission routes, and certification. Existing code and tests remain intact.
