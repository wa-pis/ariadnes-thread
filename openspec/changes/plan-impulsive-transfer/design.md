## Context

See `proposal.md` for motivation. M1 already provides immutable SI-normalized scenarios, lazy standard-kernel loading, exact SPICE provenance, UTC/TDB conversion, canonical `SSB/J2000` body states, and stable CLI error rendering. M2 must reuse those boundaries and the pinned Python 3.11/TudatPy 1.0.0 environment.

The installed TudatPy exposes the required zero-revolution Lambert targeter, escape/capture delta-v helper, SPICE state and gravitational-parameter calls, and standard gravity constant. A read-only spike using Tudat resources 2.4 and the current recorded kernel set solved all `44 * 45 = 1980` Lambert cases. Its lowest patched-conic cost was about `3583.210826 m/s`, which leaves about `887.966464 kg` from the reference spacecraft's `2000 kg` initial mass at `450 s` Isp. Because that is below its `1000 kg` dry mass, the useful design must expose an infeasible trade space rather than erase it.

## Goals / Non-Goals

**Goals:**

- Add one small transfer module that turns the existing scenario and SPICE boundary into a deterministic engineering screen.
- Make the fidelity limit visible in result names, units, manifest data, and tests.
- Preserve exact M1 API/CLI behavior and lazy dependency loading.
- Complete the reference search within its 300-second limit with ample margin.

**Non-Goals:**

- Produce executable burn directions or claim that the scalar patched-conic impulses satisfy the supplied parking-orbit planes.
- Introduce an optimizer framework, plugin interface, new scenario options, or a new dependency for one fixed M2 model.
- Implement any M3-M6 force, estimation, correction, reporting, or validation model.

## Decisions

### 1. Keep the additive implementation in existing package boundaries

Add immutable result dataclasses to `models.py`, `TransferSearchError` to `errors.py`, and the search plus small pure helpers to one new `transfer.py` module. Add package-private exact-TDB state and SPICE-GM adapters beside the existing ephemeris adapter, extend `cli.py` with the `plan` subcommand, and re-export only the documented public types, error, and function from `space_nav`. The new module SHALL defer TudatPy access until a planning call so additive exports do not break M1's import-time laziness.

This reuses the current validation, kernel initialization, JSON rendering, and manifest code. It avoids a solver abstraction, repository layer, configuration hierarchy, or separate command package that would have only one implementation in M2.

### 2. Use an exact deterministic rectangular grid

Let `B = max_candidates`, `n_departure = isqrt(B)`, and `n_flight_time = B // n_departure`. A standard-library helper generates an inclusive evenly spaced axis, or its midpoint when the count is one. Nested departure-major iteration gives the stable identifier `d{departure_index:04d}-t{flight_time_index:04d}` and attempts `n_departure * n_flight_time <= B` pairs.

The grid is deliberately independent of `random_seed`. Its simple visible rule is more reproducible than pseudo-random or adaptive sampling and gives 1,980 well-spread cases for the 2,000-candidate reference limit. Denser or adaptive optimization can be proposed only after M2 measurements show that this screen is inadequate.

### 3. Reuse M1's SSB states and convert only Lambert working vectors to heliocentric form

Convert the configured UTC bounds once to TDB. Add a package-private ephemeris adapter that accepts an exact TDB value and returns the same validated `SSB/J2000` SI state contract without a UTC text round-trip. At each endpoint, subtract the Sun's SSB state from the Moon or Mars SSB state immediately before the Lambert call. Do not store or expose Sun-relative positions as canonical reference states.

Cache departure Moon/Sun states by departure TDB and arrival Mars/Sun states by arrival TDB in ordinary dictionaries. Retrieve Sun, Moon, and Mars gravitational parameters once from the loaded SPICE pool. Any kernel, coverage, state, or GM problem is fatal and is chained into `TransferSearchError`; there is no alternate ephemeris or gravitational constant.

### 4. Use one explicit TudatPy transfer branch

For each pair instantiate:

```python
two_body_dynamics.ZeroRevolutionLambertTargeterIzzo(
    departure_position,
    arrival_position,
    flight_time_s,
    mu_sun,
    is_retrograde=False,
    tolerance=1e-9,
    max_iter=50,
)
```

The departure and arrival excess vectors are the Lambert velocities minus the corresponding heliocentric Moon and Mars velocities. A known Lambert non-convergence, degenerate geometry, or non-finite returned vector fails only that grid candidate; an unexpected programming exception is not swallowed. If every candidate fails, the search raises `TransferSearchError` instead of returning an apparently valid empty front.

The alternatives were rejected as follows:

- TudatPy's porkchop helper does not enforce the candidate budget, include the specified parking/capture energy, or return the required Pareto and mass data.
- Multi-revolution and retrograde branches expand scope and are unnecessary for the first screen; the installed multi-revolution bindings also warrant independent validation before use.
- A direct vector difference against fully oriented local parking states would appear to honor orbit orientation while silently omitting Moon/Mars gravity and hyperbolic geometry. That is less honest than an explicitly scalar patched-conic estimate.
- N-body propagation and vector finite burns are M3, not a second hidden implementation inside M2.

### 5. Treat local burns as scalar patched-conic energy estimates

Use `two_body_dynamics.compute_escape_or_capture_delta_v` with the norm of each excess vector. Compute local orbit geometry from the normalized altitudes and the same fixed M1 reference radii: Moon `1737400 m`, Mars `3389500 m`. For each orbit, `r_p = radius + periapsis_altitude`, `r_a = radius + apoapsis_altitude`, `a = (r_p + r_a) / 2`, and `e = (r_a - r_p) / (r_a + r_p)`. Take the absolute nonnegative helper result and verify it against the explicit energy equation in the specification.

The departure estimate is at lunar parking-orbit periapsis; the capture estimate is at the Martian target orbit's periapsis. The supplied inclination, RAAN, argument of periapsis, and true anomaly remain in the scenario, while the manifest identifies their field paths as ignored by M2; their values do not affect M2 cost. This is a documented model boundary, not an accidental unused field.

SPICE supplies gravitational parameters but not the reference radii: the installed SPICE average Mars radius differs from the M1-normalized radius by about `26.67 m`, and mixing it with stored orbit geometry would break reproducibility.

### 6. Expose required propellant and feasibility separately

Use `tudatpy.constants.SEA_LEVEL_GRAVITATIONAL_ACCELERATION` and apply the ideal rocket equation sequentially to the departure and arrival impulses. The public candidate contains both burn magnitudes, their sum, required propellant, final mass, and `mass_feasible = final_mass >= dry_mass`.

Mass feasibility is an annotation and count, not a Pareto filter. The reference spacecraft has no mass-feasible candidate under this M2 model; filtering would turn a successfully computed physical trade space into an empty and uninformative response. A later design may offer constrained optimization, but M2 returns the truth needed to decide whether spacecraft or mission assumptions must change.

### 7. Use a small exact Pareto implementation

Retain solved candidates until the grid completes, then compare their two objectives with the exact dominance predicate in the specification. An `O(n^2)` implementation is at most roughly four million simple comparisons for 2,000 candidates and is easier to audit than an optimizer dependency or tolerance-heavy structure. Resolve exactly equal objective pairs by candidate identifier and apply the documented stable final sort.

Floating-point objectives are not rounded before dominance. The pinned dependencies, deterministic evaluation order, and tests provide reproducibility; display formatting does not change stored values.

### 8. Public Python contract

The additive public interface is:

```python
search_impulsive_transfers(scenario: Scenario) -> TransferSearchResult

@dataclass(frozen=True, slots=True)
class ImpulsiveTransferCandidate:
    candidate_id: str
    departure_epoch_utc: str
    arrival_epoch_utc: str
    departure_epoch_tdb_s: float
    arrival_epoch_tdb_s: float
    flight_time_s: float
    departure_v_infinity_m_s: tuple[float, float, float]
    arrival_v_infinity_m_s: tuple[float, float, float]
    departure_delta_v_m_s: float
    arrival_delta_v_m_s: float
    total_delta_v_m_s: float
    propellant_mass_kg: float
    final_mass_kg: float
    mass_feasible: bool

@dataclass(frozen=True, slots=True)
class TransferSearchResult:
    ephemeris_origin: Literal["SSB"]
    transfer_central_body: Literal["Sun"]
    orientation: Literal["J2000"]
    time_scale: Literal["TDB seconds since J2000"]
    evaluated_candidates: int
    solved_candidates: int
    failed_candidates: int
    mass_feasible_candidates: int
    pareto_front: tuple[ImpulsiveTransferCandidate, ...]

class TransferSearchError(Exception): ...
```

The dataclasses validate finiteness, vector length, nonnegative magnitudes, epoch consistency, count invariants, and stable front ordering at construction. They do not expose configurable solvers or mutable implementation state.

### 9. A returned result is always complete

Use `time.monotonic()` to establish a deadline and check it before and immediately after each candidate evaluation and once before return. A deadline reached before a result can be returned raises `TransferSearchError` with the configured limit and evaluated count, including when one long solver call crosses the boundary. No partial result is returned because its contents would depend on machine speed. Tests inject a clock callable into a package-private search helper; the public signature remains fixed.

A complete search with solved transfers but zero mass-feasible candidates is successful. Candidate-level Lambert failures are counted. Fatal ephemeris/GM errors stop immediately, retain their exception as `__cause__`, and never become candidate failures. This separates an expected bad grid geometry from invalid scientific inputs or resources.

### 10. Extend the existing CLI and manifest, not its protocols

Add `space-nav plan SCENARIO [--json]` to the existing `argparse` tree. It resolves and validates the scenario before invoking transfer search or touching SPICE; importing the side-effect-free transfer module earlier is harmless. JSON success remains one sorted, finite object and uses the existing top-level pattern: `ok`, resolved `scenario`, conventions, counts, `pareto_front`, and `manifest`. Human output prints the same information with explicit units and a prominent message when `mass_feasible_candidates` is zero.

The plan manifest reuses the M1 manifest and adds a `transfer_model` object containing:

- model identifier `sun-centered-zero-revolution-patched-conic-v1`;
- grid dimensions and attempted budget;
- zero-revolution/prograde branch, tolerance, and maximum iterations;
- a finite numerical gravitational parameter for each of Sun, Moon, and Mars, labeled `m^3/s^2` and sourced from SPICE;
- reference radii and `g0` in SI;
- the scenario field paths intentionally ignored by M2.

`TransferSearchError` joins the existing handled CLI errors and therefore exits `2` with the same JSON or human envelope. Existing validate and ephemeris output is not refactored or reformatted.

### 11. Verification layers

- Pure tests cover axis/grid boundaries, identifiers, Pareto dominance and duplicate handling, sequential mass accounting, fidelity-field independence, dataclass invariants, candidate-failure counts, and fake-clock timeout behavior.
- A rotated three-dimensional analytic Lambert case checks velocity accuracy to `0.001 m/s`; wrapper parity against the direct pinned TudatPy calls checks excess vectors and scalar burns to `0.000001 m/s`.
- Reduced real-SPICE integration tests exercise exact-TDB caching, frames, units, reproducibility, and manifest completeness without making every test run evaluate 1,980 points.
- The completion gate runs the full `examples/reference_mission.toml` grid in the pinned environment, verifies 1,980 evaluated and solved candidates, a nonempty front, zero mass-feasible candidates for the current reference spacecraft, and elapsed time no greater than `300 s`. A checked-in baseline records the Tudat resources version and kernel hashes used by the spike; only that exact scientific resource set is compared with `3583.210826 m/s` at `0.01 m/s` tolerance, while a hash mismatch fails separately and requires reviewed baseline regeneration rather than silently accepting a different golden value.
- The complete M1 suite and the legacy file hash guard run unchanged before strict OpenSpec validation.

## Risks / Trade-offs

- **[Optimistic patched-conic cost]** Earth gravity between the lunar and Earth spheres of influence, finite boundary radii/times, third bodies, and local vector geometry are omitted. **Mitigation:** identify the model in every manifest, expose excess vectors separately from scalar burns, and require M3 propagation before treating any candidate as executable.
- **[Orbit orientation does not affect M2 cost]** Users could mistake fully populated orientation fields for enforced burn-plane compatibility. **Mitigation:** specify the ignored fields, test their independence, display only scalar burns, and avoid naming them maneuver vectors.
- **[Reference spacecraft is infeasible]** A feasible-only response would hide all results. **Mitigation:** preserve the full solved Pareto front and report mass feasibility per candidate and in aggregate.
- **[Kernel or dependency drift]** Scientific values can change outside the pinned environment. **Mitigation:** pin the already-installed Tudat resources 2.4 package, preserve the exact kernel/software manifest, and bind the numerical golden check to checked-in kernel hashes.
- **[Wall-clock variability]** A partial timeout could be nondeterministic. **Mitigation:** return no partial result and benchmark the complete reference grid with a generous fixed ceiling.
- **[Quadratic Pareto scan]** The simple algorithm would not scale to very large searches. **Mitigation:** the schema caps M2 at 2,000; replace it only if a future milestone intentionally raises that cap.

## Migration Plan

1. Add and test the result types, error, exact-TDB/GM adapters, and pure transfer helpers without changing existing public behavior.
2. Add the search API and public exports, then the CLI rendering and extended manifest.
3. Run unit, reduced integration, full reference, M1 regression, import-isolation, and strict OpenSpec checks in the pinned environment.
4. Pin the existing Tudat resources package, then bump the package minor version to `0.2.0` with one coherent CLI fallback when the new public API is complete.

No scenario migration is required. Rollback removes the additive M2 module, exports, command, and tests while leaving M1 files and scenario data valid; `moon_to_mars.py` remains untouched throughout.
