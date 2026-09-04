## 1. Public contracts and SPICE adapters

- [x] 1.1 Add immutable `ImpulsiveTransferCandidate` and `TransferSearchResult` dataclasses, `TransferSearchError`, and additive package exports; verify focused constructor tests enforce finite three-component vectors, normalized/consistent epochs, nonnegative burns and masses, burn-sum consistency, count bounds, and front ordering, while search-level tests enforce mass semantics and package import loads no TudatPy/SPICE kernel.
- [x] 1.2 Add package-private exact-TDB Cartesian-state and gravitational-parameter adapters that reuse M1's single lazy kernel pool; verify direct TudatPy parity in `SSB/J2000` SI, repeated-call determinism, lazy loading, and body/epoch/GM failure chaining tests.

## 2. Deterministic search mathematics

- [x] 2.1 Implement the standard-library rectangular grid, midpoint/inclusive-axis rules, departure-major iteration, and stable candidate identifiers; verify budgets `1`, `17`, and `2000`, unique in-range pairs, the `44 * 45 = 1980` reference grid, absence of a 1,981st attempt, and scientific independence from `random_seed`.
- [x] 2.2 Implement normalized local-orbit geometry and scalar patched-conic escape/capture calculations using the fixed M1 Moon/Mars radii and SPICE GM values; verify both burns against the explicit energy equation to `0.000001 m/s` and verify orientation and all other deferred M2 fields do not change scientific results.
- [x] 2.3 Implement sequential ideal rocket-equation accounting with `g0 = 9.80665 m/s^2` and the dry-mass feasibility flag; verify total delta-v, final mass, and propellant against independent calculations to relative error `1e-12`, including a deliberately mass-infeasible candidate that remains available to Pareto selection.
- [x] 2.4 Implement the exact `O(n^2)` time/propellant Pareto predicate, duplicate tie-break, and stable output sort; verify membership against an independent oracle covering dominance, equal time, equal propellant, exact duplicate objectives, feasible and infeasible candidates, and input-order permutations.

## 3. TudatPy transfer search

- [x] 3.1 Wrap TudatPy's zero-revolution prograde Lambert targeter with the fixed tolerance and iteration limit and compute Moon/Mars hyperbolic-excess vectors from heliocentric endpoint velocities; verify a rotated analytic three-dimensional case to `0.001 m/s` and direct pinned-TudatPy wrapper parity to `0.000001 m/s` without two-dimensional projection.
- [x] 3.2 Implement `search_impulsive_transfers` with endpoint caching, candidate construction, complete counts, candidate-level Lambert failure isolation, and fatal ephemeris/all-unsolved behavior; verify reduced real-SPICE and injected-failure tests cover finite epoch/frame/unit data, count invariants, successful continuation, exception causes, and the absence of fabricated fallbacks.
- [x] 3.3 Enforce the monotonic runtime deadline before and after each candidate and before return without returning partial results; verify with an injected clock both that exactly `k` candidates finish with no next attempt and that one long final evaluation crossing the deadline still raises `TransferSearchError` with the configured limit and updated count, without a wall-clock wait.
- [x] 3.4 Verify complete-search reproducibility by running the same reduced real-SPICE scenario repeatedly and with only deferred fields changed, asserting identical aggregate counts and returned Pareto identifiers, epochs, physical values, and membership while permitting provenance fields such as scenario hash and recorded seed to differ.

## 4. CLI and provenance

- [x] 4.1 Extend the existing manifest with the transfer model identifier, grid, solver branch/settings, fixed radii, `g0`, ignored field paths, and finite Sun/Moon/Mars GM values labeled `m^3/s^2` and sourced from SPICE; verify JSON provenance retains the scenario/software/kernel data from M1 and contains every documented value and complete loaded-kernel hash.
- [x] 4.2 Add `space-nav plan SCENARIO [--json]` with flat JSON and labeled human rendering; verify success, zero-mass-feasible success, candidate serialization, exit `0`, deterministic JSON, and explicit UTC/TDB, `SSB/J2000`, Sun-centered, `m/s`, and `kg` labels.
- [x] 4.3 Route validation, argument, deadline, ephemeris, and search failures through the existing CLI error contract; verify invalid scenarios make no SPICE/search call and every handled failure exits `2` with empty stdout, one selected-format stderr error, no traceback, and no partial front.
- [x] 4.4 Pin the already-installed `tudat-resources` package at version `2.4` in `environment.yml`; verify a clean environment solve selects that version and introduces no new package beyond the existing dependency closure.
- [x] 4.5 Bump the declared package and module version to `0.2.0` and make the CLI metadata fallback reuse the module version instead of a third literal; verify installed metadata, `space_nav.__version__`, source-only fallback behavior, and the plan manifest all report `0.2.0`.

## 5. Completion gate

- [x] 5.1 Record the Tudat resources version and complete kernel hashes for the read-only reference spike, then run the full `examples/reference_mission.toml` plan in the matching pinned environment; verify 1,980 evaluated and solved candidates, zero Lambert failures, a nonempty Pareto front, zero mass-feasible candidates, minimum total delta-v within `0.01 m/s` of `3583.210826 m/s`, and elapsed time no greater than `300 s`, with a distinct failure requiring review when the resource hashes do not match.
- [x] 5.2 Run the complete pinned test suite, including every M1 regression and the new pure, CLI, analytic, and real-SPICE M2 tests; verify all tests pass from a clean process and help/import/validate remain kernel-lazy.
- [x] 5.3 Recompute the legacy file SHA-256 and scan package imports; verify `moon_to_mars.py` remains byte-for-byte at `4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf` and is never imported by `space_nav`.
- [x] 5.4 Run `openspec validate plan-impulsive-transfer --strict` after all implementation checks; verify it passes before M2 is marked complete or archived.
