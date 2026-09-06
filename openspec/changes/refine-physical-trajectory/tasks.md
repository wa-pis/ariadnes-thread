## Prototype delivery

- [x] 1. Preserve deferred M3 documents and replace the sole active scope; verify strict OpenSpec validation.
- [x] 2. Pin/install Streamlit and Plotly while preserving scientific pins; verify imports and environment tests.
- [x] 3. Share in-memory scenario validation and sample SI/SSB M2 states; verify parser parity, analytic orbit, endpoints, determinism, and failures.
- [x] 4. Build explicit example loading, editable fields, results, plot, and slider; verify AppTest success, edits, invalid input, and stale-result removal.
- [ ] 5. Run full tests and strict validation, inspect UI, document launch, and commit/push dev; verify legacy checksum and clean Git status. Deferred M3 tasks remain incomplete.

Verification on 2026-09-07: 289 tests passed in the pinned Conda environment
(`python -m pytest -q -p no:cacheprovider`); strict validation passed. The browser
walkthrough loaded the example, calculated a candidate, and displayed the real
projected trajectory. AppTest additionally verified slider time, candidate
changes, valid/invalid reruns, and search/sampling failure cleanup. Sampling
checks use 100 m / 0.001 m/s endpoint bounds and 0.01 m / 1e-6 m/s circular-orbit
bounds; no high-fidelity feasibility is inferred. Legacy SHA-256 remains
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.
Task 5 remains unchecked solely because push to origin/dev was rejected by the
execution safety review pending explicit destination confirmation. Local code
and documentation commits are retained; do not work around the push block.
