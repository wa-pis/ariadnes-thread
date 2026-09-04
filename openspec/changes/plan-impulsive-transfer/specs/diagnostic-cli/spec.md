## ADDED Requirements

### Requirement: Impulsive transfer planning command
The application SHALL provide `space-nav plan SCENARIO [--json]`. It SHALL fully validate `SCENARIO` before loading SPICE or starting the transfer search. A completed search SHALL exit `0`, including when no candidate is mass-feasible. Scenario, command-usage, ephemeris, deadline, and transfer-search failures SHALL exit `2`, write no normal result, use the existing selected-format error contract, and expose no traceback or partial Pareto front.

#### Scenario: JSON planning success
- **WHEN** a valid scenario completes with `space-nav plan mission.toml --json`
- **THEN** the command exits `0`, writes nothing to standard error, and writes exactly one JSON object to standard output containing `ok: true`, the resolved `scenario`, `ephemeris_origin: "SSB"`, `transfer_central_body: "Sun"`, `orientation: "J2000"`, `time_scale: "TDB seconds since J2000"`, evaluated/solved/failed/mass-feasible counts, the ordered `pareto_front`, and a `manifest`

#### Scenario: Serialize a Pareto candidate
- **WHEN** a JSON planning result contains a Pareto candidate
- **THEN** that object contains its stable identifier, normalized departure and arrival UTC labels, departure and arrival TDB seconds, flight time in seconds, two three-element hyperbolic-excess vectors in `J2000 m/s`, scalar departure/arrival/total delta-v in `m/s`, propellant and final mass in `kg`, and a Boolean mass-feasibility flag

#### Scenario: Human-readable planning success
- **WHEN** a valid completed search omits `--json`
- **THEN** the command exits `0` and labels the scenario, all counts, reference `SSB/J2000`, Sun-centered model, UTC and TDB epochs, flight time, hyperbolic-excess vectors, scalar burns, total delta-v, propellant, final mass, and feasibility for every Pareto entry using their public units

#### Scenario: Completed search with no feasible spacecraft candidate
- **WHEN** the search completes with zero mass-feasible candidates and a nonempty physical transfer front
- **THEN** the command exits `0`, reports `mass_feasible_candidates: 0`, retains the Pareto entries with `mass_feasible: false`, and clearly states the infeasibility in human-readable mode

#### Scenario: Validate before planning
- **WHEN** `SCENARIO` is invalid
- **THEN** no SPICE or transfer function is called, the command exits `2`, standard output is empty, and the existing `ScenarioValidationError` envelope or concise human error is written to standard error

#### Scenario: Report a planning failure
- **WHEN** planning raises `TransferSearchError`
- **THEN** the command exits `2`, standard output is empty, and standard error contains either one JSON error envelope with type `TransferSearchError`, message, and `field: null` or one concise human-readable error, with no traceback or partial front

### Requirement: Planning provenance manifest
Every successful JSON planning response SHALL extend the existing diagnostic manifest with model identifier `sun-centered-zero-revolution-patched-conic-v1`, grid dimensions, the lunar and Martian reference radii, `g0`, the TudatPy Lambert branch and solver settings, and an explicit list of scenario fields ignored by M2. It SHALL record a finite numerical gravitational parameter in `m^3/s^2` for each of Sun, Moon, and Mars and identify SPICE as its source. The existing scenario hash, software versions, canonical reference conventions, random seed, and complete loaded-kernel inventory SHALL remain present.

#### Scenario: Inspect planning provenance
- **WHEN** a JSON planning command succeeds
- **THEN** its manifest is sufficient to identify the scenario, dependency and kernel versions, reference conventions, solver model and settings, grid dimensions, constants, and deferred input fields used to reproduce or interpret the result

### Requirement: M1 command compatibility
Adding transfer planning SHALL NOT remove, rename, or change the meaning of existing public Python names or the command schemas, scientific values, exit statuses, and error behavior established for `space-nav validate` and `space-nav ephemeris`. Additive public exports are permitted, and provenance version fields SHALL identify the new package version. Importing `space_nav`, requesting help, or validating a scenario SHALL remain free of SPICE kernel loading, and the package SHALL NOT import `moon_to_mars.py`.

#### Scenario: Re-run M1 compatibility checks
- **WHEN** the M1 API, validation, ephemeris, help, lazy-loading, and legacy-isolation test suite is run after M2 is added
- **THEN** all existing fields, exit statuses, numerical tolerances, and import side-effect checks still pass with their prior semantics, while any documented version field reports the M2 package version
