# 0119 — Retain a positive ideal M2 reference

Date: 2026-10-30
Decision status: accepted (retain the observed R1.1 result; no new physical model).
Implementation: R1.1 verified at M2 fidelity; R1.2–R1.4 and strict M3 remain open.
Scope / milestone: R1 reference verification inside the sole active M3 change.
Base revision: `5c7012ceb348f4ccef3f020060f01bfe23b0d240`. Native run used unchanged production source/environment; the new runner/fixture were untracked and ADR 0118 acceptance was modified. Exact dirty status, import path and source hashes are retained, not described as a clean-revision experiment.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [ADR 0118](0118-m2-reference-and-historical-data-readiness.md), preserving previous experiments.

## Context and constraints

The user approved the explicit ADR 0118 contract and its bounded execution.
R1 needs one understandable, positive example before more local targeting work.
Repeatability and correct ideal mass accounting do not independently validate
the propagation physics or turn body-centre Lambert endpoints into a mission.

The distinct [scenario](../../examples/r1_m2_reserve_reference.toml) copies every
explicit value from the unchanged hash-bound `m3_feasible_mission.toml`.
This is a hypothetical 2000/500 kg spacecraft with 450 s Isp, the declared
2031 departure window and 180–320 day flight range, not a historical mission.
No old example, result, production module or dependency was changed.

## Options considered

- Adjust inputs, reserve or selected candidate after viewing results: rejected;
  the accepted contract fixes these before execution and requires fail-stop.
- Retain the observed result at its actual ideal fidelity and proceed to an
  independently specified small benchmark: selected. No new optimizer or engine.

## Decision and rationale

Accept **R1.1 only**. Exactly two full M2 searches and two 121-state samplings
completed in **1.993807459 s**, including imports and resource/provenance setup,
inside the shared cooperative 300 s budget. There was no retry, parameter
adjustment, historical replay or additional native search/sampling test.

Each search attempted/solved 1980 grid entries (44×45), failed zero and returned
16 Pareto candidates; 256 grid entries met the existing dry-mass-only flag.
All 16 returned Pareto entries also preserved the separate 50 kg reserve.
The prescribed tuple selected and froze `d0001-t0035`:

| Observed quantity | Value |
|---|---|
| Departure UTC | 2031-01-09T11:09:46.046266Z |
| Arrival UTC | 2031-10-27T19:53:24.229781Z |
| Flight time | 25173818.18181818 s = 291.36363636 days |
| Ideal departure / arrival delta-v | 1728.78507624 / 1854.42574940 m/s |
| Total ideal delta-v | 3583.210825639004 m/s |
| Propellant / final mass | 1112.033535959039 / 887.9664640409611 kg |
| Final mass above dry / above dry + reserve | 387.9664640409611 / 337.9664640409611 kg |
| Independent sequential Decimal50 mass difference | 2.784246186e-14 kg, below 1e-9 kg |
| Departure position / velocity residual | 0.000337423 m / 6.30182e-11 m/s |
| Arrival position / velocity residual | 0.002428833 m / 3.03593e-10 m/s |

Both complete scientific payloads are identical: search counters/front,
selection, mass arithmetic, all sampled states, endpoint evidence and provenance.
Timings are stored separately. States are finite SI, SSB/J2000 at TDB seconds
since J2000; both endpoints pass 100 m / 0.001 m/s internal consistency gates.
The ordered 13 kernel names/hashes match the existing kernel baseline; actual
SPICE GMs, ignored fields, Python/TudatPy/resources/SpiceyPy/NumPy/SciPy versions
and source/scenario hashes are retained and unchanged across runs.

The predeclared 50 kg reserve covers only aggregate *additional ideal*
delta-v <=100 m/s at 450 s Isp, mass <=2000 kg, no staging or mass additions.
Its conservative Decimal propellant bound is 44.811085412142 kg. It is held back
after both scalar M2 maneuvers, not consumed twice or a verified TCM schedule.

## Consequences and revisit conditions

This is **ideal-model feasible**, not finite-burn, full-force or full-mission
feasible. Model `sun-centered-zero-revolution-patched-conic-v1` uses Sun-point-mass
coast, zero-revolution prograde Lambert, body-centre endpoints and scalar
instantaneous escape/capture estimates. Real parking/insertion planes, finite
thrust, perturbations, SRP, tracking and maneuver errors do not constrain it.
Millimetre endpoint agreement is internal consistency, not absolute accuracy.

Next: specify a small frozen same-force R1.2 benchmark and independent oracle,
including initial state, epochs, resources, tolerances and execution budget;
accept that contract before separately authorized execution. The offline mass
and endpoint audit below is not this independent propagation benchmark.
Keep R1.3 OEM/profile and R1.4 usable-path implementation pending. Do not start
another D17/D18 study, historical replay, M4–M6 or ML; automation remains paused.
Strict M3/task 3.9 gates are unchanged and cannot be archived by R1.1 success.

## Evidence and verification

- [Raw evidence](experiments/0119-m2-reference.json), SHA256
  `3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0`.
  Retains both raw scientific payloads, source/input/resource/version snapshots,
  resolved GMs, call order/counters/timings, mass and endpoint residuals.
- [One-shot runner](experiments/0119-run-m2-reference.py): reuses the existing
  M2 planner, shared deadline, sampler and manifests. Exclusive output creation
  prevents overwriting this evidence; no further scientific execution authorized.
  `--self-test` passes 18 native-free checks for exact reserve boundary/deficits,
  deterministic selection, mass mismatch, endpoint limits/nonfinite/epoch,
  expiry/overrun, preserving returned science and recording native-call failure.
- [Offline audit](experiments/0119-check-m2-reference.py): passes using only the
  standard library; recomputes mass/reserve at Decimal60, independent endpoint
  sum-of-squares, selection, all 242 states, full equality, 3960 attempts and
  source/kernel identity. This audit makes no SPICE or propagation requests.
- Explicit and normalized new/template inputs match; runner/audit Ruff, strict
  OpenSpec, local links, JSON syntax, whitespace and immutable checks pass.
  `moon_to_mars.py` retains SHA256
  `4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

Production runtime code and its regression tests are unchanged. The full suite
was **not rerun** for this bounded evidence stage: some tests invoke extra native
searches/samplings. Previous 4588-test D17.2 evidence (626.08 s) remains historical,
not a fresh result or substitute for the pending R1.4 implementation regressions.
