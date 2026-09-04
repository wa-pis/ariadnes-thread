## Context

See `proposal.md` for motivation and the three delta specifications for observable behavior. The repository currently contains only `moon_to_mars.py`, a NumPy-based educational 2D simulation that writes CSV and SVG files. There is no package metadata, scenario schema, automated test suite, or installed TudatPy environment. M1 is an additive foundation; the legacy script is not a migration source and must remain byte-for-byte untouched.

## Goals / Non-Goals

**Goals:**

- Create a small importable `space_nav` package with immutable public data types, a strict TOML loader, a TudatPy/SPICE reference-state adapter, and an `argparse` CLI.
- Make every public boundary explicit about units, time scale, frame origin, and frame orientation.
- Keep scenario loading independent from SPICE so validation remains fast and deterministic.
- Provide a reproducible developer environment and automated acceptance tests.

**Non-Goals:**

- Do not implement any M2–M6 behavior, including Lambert targeting, trajectory propagation, optimization, finite burns, tracking simulation, state estimation, TCM selection, Monte Carlo, reporting, or GMAT.
- Do not create an interchangeable dynamics-engine abstraction, download custom kernels, or add a circular-orbit fallback.
- Do not add UI, database, service, or network layers.

## Decisions

### 1. Package and dependency boundary

Create an installable `src/space_nav` package and expose the `space-nav` console script through `pyproject.toml`. Use Python 3.11, standard-library `argparse`, `dataclasses`, `json`, `pathlib`, and `tomllib`. TudatPy is the only astrodynamics dependency and supplies both time conversion and SPICE access. The reproducible environment file pins Python, TudatPy, NumPy, and pytest versions used by CI/development.

Public imports are re-exported from `space_nav`:

```python
load_scenario(path) -> Scenario
query_body_state(body, epoch) -> CartesianState

Scenario
SearchSpec
OrbitSpec
SpacecraftSpec
TrackingSpec
LimitsSpec
CartesianState
ScenarioValidationError
EphemerisError
```

The implementation is divided only by responsibility: immutable models and errors, scenario parsing, ephemeris access, and CLI. A generic repository layer or replaceable ephemeris interface is intentionally rejected because M1 has one file format and one authoritative ephemeris provider.

### 2. Immutable normalized scenario model

All public model types are frozen dataclasses. The TOML document preserves human-friendly UTC, kilometer, degree, day, hour, and arcsecond fields; `load_scenario` converts physical values into a canonical typed model:

```text
Scenario
  search: SearchSpec
  departure_orbit: OrbitSpec
  target_orbit: OrbitSpec
  spacecraft: SpacecraftSpec
  tracking: TrackingSpec
  limits: LimitsSpec

SearchSpec
  departure_start_utc: str
  departure_end_utc: str
  time_of_flight_min_s: float
  time_of_flight_max_s: float

OrbitSpec
  central_body: str
  periapsis_altitude_m: float
  apoapsis_altitude_m: float
  eccentricity: float
  inclination_rad: float
  raan_rad: float
  argument_of_periapsis_rad: float
  true_anomaly_rad: float

SpacecraftSpec
  initial_mass_kg: float
  dry_mass_kg: float
  max_thrust_n: float
  isp_s: float
  srp_area_m2: float
  reflectivity_coefficient: float
  maneuver_magnitude_sigma_fraction: float
  maneuver_pointing_sigma_rad: float

TrackingSpec
  stations: tuple[str, ...]
  cadence_s: float
  range_sigma_m: float
  range_rate_sigma_m_s: float
  angular_sigma_rad: float
  min_elevation_rad: float

LimitsSpec
  runtime_seconds: float
  random_seed: int
  max_candidates: int
```

The 100 km circular departure orbit is normalized to equal periapsis and apoapsis altitude. M1 also fixes the target orbit to a 300 km periapsis and 10000 km apoapsis while requiring the user to supply its angular orientation. Target eccentricity is derived from Mars mean radius plus those validated apsis altitudes, so later milestones receive one orbit representation. UTC strings are syntax-checked and normalized to a `Z` representation without loading SPICE; their conversion to TDB remains the ephemeris layer's responsibility.

The loader uses explicit allowed-key sets for the document and each section. It rejects unknown keys, booleans where numbers are expected, missing fields, non-finite values, invalid ranges, and inconsistent cross-field values. `ScenarioValidationError` carries `message` and optional dotted `field`; its string form includes the field once. This explicit parser is preferred over a schema dependency because the contract is small and custom cross-field diagnostics are required.

### 3. Lazy TudatPy/SPICE adapter

`query_body_state` accepts a body name and UTC string. On its first call, a private, lock-protected initializer invokes TudatPy standard-kernel loading once. Importing the package and calling `load_scenario` do not import or initialize SPICE eagerly. Subsequent calls reuse the loaded process-wide kernel pool.

The adapter converts UTC to TDB seconds since J2000, then asks TudatPy SPICE for the geometric state using observer `SSB`, orientation `J2000`, and aberration correction `NONE`. No manual unit scaling is applied to the TudatPy SI result. It returns:

```text
CartesianState
  body: str
  epoch_utc: str
  epoch_tdb_s: float
  origin: Literal["SSB"]
  orientation: Literal["J2000"]
  position_m: tuple[float, float, float]
  velocity_m_s: tuple[float, float, float]
```

The adapter validates the returned shape and finiteness. TudatPy exceptions from initialization, time conversion, lookup, or coverage are wrapped in `EphemerisError` with the body and epoch, using exception chaining for developer diagnostics. There is no fallback path. UTC round-trip tests use the same TudatPy/SPICE time facilities but remain separate from the state query.

Using TudatPy's standard kernels is chosen for M1 because it avoids a second SPICE binding and kernel downloader. A project-managed kernel manifest is deferred until a later milestone needs mission-specific kernels; reproducibility in M1 comes from pinned TudatPy and test epochs within its standard coverage.

### 4. Stable CLI and serialization

The console entry point exposes exactly:

```text
space-nav validate SCENARIO [--json]
space-nav ephemeris SCENARIO --body BODY --epoch UTC [--json]
```

`validate` calls only `load_scenario`. `ephemeris` first loads the scenario, then calls `query_body_state`. The scenario argument deliberately gates ephemeris diagnostics so every later workflow starts from validated mission input.

Successful commands write to stdout and exit `0`. User-caused file, TOML, validation, argument, body, epoch, kernel, and coverage failures write to stderr and exit `2`; expected failures never print tracebacks. JSON uses `json.dumps(..., allow_nan=False, sort_keys=True)` and emits no surrounding prose. A small custom `ArgumentParser.error` path preserves the same JSON envelope for usage errors when `--json` appears in the original arguments. Unexpected programming failures are not relabeled as user errors.

The validation success object is exactly:

```json
{"ok": true, "scenario": "<resolved-path>"}
```

Ephemeris success adds `ok: true` to the state fields required by the diagnostic CLI spec. Errors use:

```json
{"ok": false, "error": {"type": "ScenarioValidationError", "message": "...", "field": "search.departure_start_utc"}}
```

For errors without a field, `field` is JSON `null`; ephemeris errors use type `EphemerisError`. Human output labels all units and the `SSB/J2000` convention explicitly.

Successful JSON ephemeris output also contains a nested provenance manifest. It hashes the scenario file and records Python, application, TudatPy, and SpiceyPy versions, the scenario seed, and canonical conventions. Kernel loading and state queries remain exclusively in TudatPy. Its pinned SpiceyPy dependency is used read-only after initialization to enumerate the actual shared CSPICE pool, including kernels not listed by an outdated docstring. The adapter records each file name, version-bearing stem, kernel type, byte size, and SHA-256, and verifies the pool count against TudatPy. Missing, unreadable, or inconsistent resources fail the diagnostic instead of producing incomplete provenance. Human output reports the kernel source and count; validation remains SPICE-free and therefore does not emit this manifest.

### 5. Verification strategy

Unit tests exercise every required/default TOML field, unknown keys, numeric type handling, validation ranges, cross-field ordering, immutability, and deterministic loads. They also verify that importing and validating do not initialize SPICE.

Integration tests use covered fixed epochs to verify UTC–TDB–UTC round trips within 1 ms, compare the adapter with a direct TudatPy SPICE state query within 1 mm and 1 micrometer per second, and verify deterministic repeated queries. CLI subprocess tests assert exact exit codes, stdout/stderr separation, JSON shapes, absence of traceback text, and lazy behavior for help and validation.

The implementation check also confirms that `moon_to_mars.py` has no diff. Tests do not depend on the existing CSV or SVG generated artifacts.

## Risks / Trade-offs

- **TudatPy standard kernels change with the pinned package version** → Pin the TudatPy version, use covered fixed test epochs, and report its version in test diagnostics.
- **SPICE maintains process-global kernel state** → Hide initialization behind one lock-protected function and never unload kernels during normal application execution.
- **TOML and Python can treat booleans as integers** → Use exact numeric type checks before coercion.
- **Strict unknown-key rejection makes additive schema changes explicit** → Version later schema changes through OpenSpec instead of silently accepting misspelled or unused input.
- **Normalizing the scenario changes field names and units after load** → Keep unit suffixes on every normalized dataclass field and test each conversion directly.
- **The CLI takes a scenario for an otherwise independent ephemeris query** → Retain this deliberate validation gate so diagnostic behavior matches later mission commands.

## Migration Plan

This is additive and has no existing package API to migrate. Implement the environment, package, scenario example, and tests; install the console entry point; run the complete test suite and strict OpenSpec validation. Rollback consists of removing the new package and configuration files. `moon_to_mars.py` and its generated artifacts remain independent throughout.
