## Design

Use one Streamlit entrypoint and one sampling module. Streamlit is a presentation boundary alongside the CLI; domain modules do not render UI. Share in-memory TOML validation with load_scenario. Populate fields only after explicit example loading; expose all source fields. Any edited input invalidates previous results immediately. Store results per session and serialize native calls with a process lock because SPICE is process-global.

Reconstruct M2 heliocentric initial state from Moon-minus-Sun SPICE state plus candidate excess velocity. Propagate Kepler elements with Tudat, convert to Cartesian, and add the contemporaneous Sun SSB state. Store immutable validated CartesianState values in SI/TDB/SSB/J2000. Display an equal-scale Sun-relative J2000 XY projection in millions of km. Earth/Mars context comes from SPICE. The slider selects one of 121 epochs and displays UTC and Sun-relative speed. Do not label a decorative interpolated curve as a physical state.

Endpoint consistency bounds are 100 m and 0.001 m/s; an independent analytic circular orbit must agree within 0.01 m and 1e-6 m/s. These are consistency tests, not mission accuracy. Missing resources and unsupported propagation fail without substitute curves.

Pin Streamlit 1.49.1 and Plotly 6.3.0 via Conda while retaining scientific pins. Use AppTest for interaction checks. Bind the documented server to loopback; no deployment.
