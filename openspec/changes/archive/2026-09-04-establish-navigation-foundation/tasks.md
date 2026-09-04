## 1. Reproducible package foundation

- [x] 1.1 Add the `src/space_nav` package, `space-nav` console entry point, and test layout through `pyproject.toml`; verify a clean environment can import `space_nav` and display `space-nav --help`.
- [x] 1.2 Add the pinned Python 3.11/TudatPy/NumPy/pytest environment definition; verify dependency resolution and package installation complete without importing the legacy script.
- [x] 1.3 Add a complete example TOML scenario using the settled lunar departure, Martian target, spacecraft, tracking, and limits fields; verify it parses with the implemented loader.

## 2. Mission scenario contract

- [x] 2.1 Implement frozen `Scenario`, `SearchSpec`, `OrbitSpec`, `SpacecraftSpec`, `TrackingSpec`, and `LimitsSpec` dataclasses with the normalized field names and units from `design.md`; verify construction and equality tests pass.
- [x] 2.2 Implement `ScenarioValidationError` with message and optional dotted field, plus strict TOML section/key/type parsing in `load_scenario`; verify missing files, malformed TOML, unknown keys, booleans-as-numbers, and missing required fields report the correct field.
- [x] 2.3 Implement UTC syntax normalization, SI/radian conversions, orbit normalization, tracking defaults, and limits defaults; verify the example scenario and omitted-default fixtures produce the exact typed values specified in `mission-scenario`.
- [x] 2.4 Implement numeric, angular, date-order, time-of-flight, mass, orbit, and candidate-count validation; verify table-driven tests cover non-finite/nonpositive values, `initial_mass_kg <= dry_mass_kg`, invalid date order, and periapsis greater than or equal to apoapsis.
- [x] 2.5 Re-export the settled scenario API from `space_nav` and verify repeated loads return equal immutable values without loading SPICE.

## 3. Canonical reference states

- [x] 3.1 Implement `CartesianState` and `EphemerisError` with the exact public fields and `SSB/J2000`, TDB-since-J2000, meter, and meter-per-second conventions; verify shape, literal-frame, and finiteness tests pass.
- [x] 3.2 Implement lock-protected lazy loading of TudatPy standard kernels and verify importing `space_nav`, requesting help, and validating a scenario do not load kernels while repeated state queries initialize them only once.
- [x] 3.3 Implement UTC-to-TDB conversion and `query_body_state(body, epoch)` using geometric TudatPy SPICE states with observer `SSB`, orientation `J2000`, and aberration correction `NONE`; verify UTC–TDB–UTC round-trip error is at most 1 ms.
- [x] 3.4 Wrap initialization, invalid epoch, unsupported body, and coverage failures as actionable chained `EphemerisError` values without fallback states; verify each failure test includes the requested body and epoch where applicable.
- [x] 3.5 Add direct TudatPy parity and repeatability tests at fixed covered epochs; verify position differs by no more than 1 mm, velocity by no more than 1 micrometer per second, and repeated results compare equal.

## 4. Diagnostic command line

- [x] 4.1 Implement `space-nav validate SCENARIO [--json]` and verify human and exact JSON success output, resolved scenario path, exit `0`, and scenario/user error exit `2` with no traceback.
- [x] 4.2 Implement `space-nav ephemeris SCENARIO --body BODY --epoch UTC [--json]`, validating the scenario before kernel loading; verify human output labels every unit/frame and JSON contains the required state fields plus scenario/software/convention/seed provenance and names, versions, types, sizes, and SHA-256 values for every kernel actually loaded by TudatPy.
- [x] 4.3 Implement shared human/JSON error rendering and JSON-aware argument-parser failures; verify handled failures write only to stderr, use the stable error envelope, and exit `2` while help exits `0` without loading SPICE.

## 5. Acceptance and handoff

- [x] 5.1 Run the complete unit, integration, and CLI subprocess test suite in the pinned environment and verify all mission-scenario, reference-state, and diagnostic-cli acceptance scenarios pass.
- [x] 5.2 Run `openspec validate establish-navigation-foundation --strict` and resolve every reported issue before marking M1 implementation complete.
- [x] 5.3 Confirm `moon_to_mars.py` has no content diff and that no M2–M6 behavior was added; record both checks in the implementation handoff.
