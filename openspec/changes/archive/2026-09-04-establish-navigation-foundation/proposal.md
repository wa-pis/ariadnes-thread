## Why

The project currently has only a self-contained educational two-dimensional simulation, so later navigation milestones have no reproducible scenario contract, canonical state convention, or trustworthy real-ephemeris boundary. M1 establishes that foundation before trajectory search or guidance logic is introduced.

## What Changes

- Define a strict TOML mission-scenario contract for search bounds, lunar departure orbit, Martian target orbit, spacecraft properties, tracking assumptions, and execution limits.
- Establish SSB/J2000, TDB seconds since J2000, and SI units as the canonical internal state convention.
- Add a lazy TudatPy/SPICE adapter that returns deterministic Cartesian reference states and fails explicitly when kernels or epoch coverage are unavailable.
- Add diagnostic commands for scenario validation and body-state inspection, with stable JSON output and exit behavior suitable for automation.
- Define a reproducible Python environment and tests for validation, time conversion, and ephemeris parity.

### Non-goals

- M1 does not search or propagate Moon-to-Mars transfers, model maneuvers, estimate navigation state, schedule course corrections, run Monte Carlo cases, generate mission reports, or integrate GMAT.
- M1 does not add a graphical interface, consume real tracking data, implement a fallback circular ephemeris, or modify the legacy `moon_to_mars.py` model.

## Capabilities

### New Capabilities

- `mission-scenario`: Parse and validate the complete TOML input contract required by the navigation roadmap.
- `reference-state`: Query deterministic SPICE-backed Cartesian body states using canonical time, frame, and unit conventions.
- `diagnostic-cli`: Validate scenarios and inspect ephemerides through stable human-readable and JSON command-line interfaces.

### Modified Capabilities

None.

## Impact

- Introduces a new installable `space-nav` Python package and its test suite in the future M1 implementation.
- Adds TudatPy as the source of SPICE kernels, time conversion, and ephemeris data; no separate ephemeris engine is planned.
- Establishes public Python types and errors that later milestones will consume.
- Implements roadmap milestone M1, `establish-navigation-foundation`; milestones M2–M6 remain deferred.
