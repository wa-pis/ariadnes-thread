# Diagnostic CLI Specification

## Purpose

Expose stable diagnostics that let people and automation validate mission inputs and inspect real ephemeris states before expensive planning work begins.

## Requirements

### Requirement: Scenario validation command
The application SHALL provide `space-nav validate SCENARIO [--json]`. A valid scenario SHALL produce exit status `0`; any missing file, TOML syntax problem, unknown field, or scenario validation error SHALL produce exit status `2` without a Python traceback.

#### Scenario: Human-readable validation success
- **WHEN** `space-nav validate mission.toml` receives a valid scenario
- **THEN** it exits `0` and writes a concise success message containing the scenario path to standard output

#### Scenario: JSON validation success
- **WHEN** `space-nav validate mission.toml --json` receives a valid scenario
- **THEN** it exits `0` and writes only `{"ok": true, "scenario": "<resolved-path>"}` as a JSON object to standard output

#### Scenario: JSON validation failure
- **WHEN** `space-nav validate mission.toml --json` receives an invalid scenario
- **THEN** it exits `2`, writes no normal output, and writes a single JSON error object to standard error with `ok: false`, error type `ScenarioValidationError`, message, and dotted `field` when one is available

### Requirement: Ephemeris inspection command
The application SHALL provide `space-nav ephemeris SCENARIO --body BODY --epoch UTC [--json]`. It SHALL validate `SCENARIO` before querying the requested state. Success SHALL produce exit status `0`; any scenario, epoch, body, kernel, coverage, or command-usage error SHALL produce exit status `2` without a Python traceback.

#### Scenario: JSON ephemeris success
- **WHEN** a valid scenario and covered Mars epoch are supplied with `--json`
- **THEN** the command exits `0` and writes one JSON object containing `body`, normalized `epoch_utc`, `epoch_tdb_s`, `origin: "SSB"`, `orientation: "J2000"`, `position_m` with three values, and `velocity_m_s` with three values

#### Scenario: Human-readable ephemeris success
- **WHEN** a valid ephemeris request is made without `--json`
- **THEN** the command exits `0` and labels the body, UTC and TDB epochs, `SSB/J2000` frame, meter position, and meter-per-second velocity in its standard output

#### Scenario: Ephemeris failure
- **WHEN** an unsupported body or uncovered epoch is supplied
- **THEN** the command exits `2`, emits an actionable `EphemerisError` on standard error in the selected output format, and emits no fabricated state

### Requirement: Stable diagnostic error envelope
In JSON mode, every handled command error SHALL use `{"ok": false, "error": {"type": "<type>", "message": "<message>", "field": "<field-or-null>"}}`. Human-readable errors SHALL be a single concise message on standard error. User-caused errors SHALL always exit `2`; successful diagnostics and standard help requests SHALL exit `0`.

#### Scenario: Invalid UTC argument
- **WHEN** `--epoch` is not a valid UTC timestamp
- **THEN** the command exits `2` and reports an `EphemerisError` without a traceback

#### Scenario: Help request
- **WHEN** the user requests command help
- **THEN** the command exits `0` and displays available syntax without loading SPICE kernels

### Requirement: Ephemeris provenance manifest
Every successful ephemeris response in JSON mode SHALL include a `manifest` object containing the scenario SHA-256, Python and application versions, TudatPy version, random seed, canonical origin, orientation, time scale, position unit, velocity unit, and the loaded standard-kernel source. The manifest SHALL inspect the shared CSPICE pool after TudatPy loads its standard kernels and inventory every actually loaded kernel in load order. Each kernel record SHALL contain its file name, version identifier, kernel type, byte size, and SHA-256. If the installed resources cannot supply and hash the complete loaded set, the diagnostic SHALL fail with `EphemerisError` rather than emit incomplete provenance.

#### Scenario: Inspect diagnostic provenance
- **WHEN** a valid ephemeris request succeeds in JSON mode
- **THEN** its `manifest` identifies the exact scenario and software environment and lists every kernel reported by the loaded CSPICE pool with a nonempty version and 64-character SHA-256 value
