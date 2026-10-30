## ADDED Requirements

### Requirement: Bind a research result to its actual inputs and scientific scope

The proposed `ariadna-result-v1` contract SHALL preserve the canonical SI/SSB/J2000
states at numeric TDB seconds since J2000 and the actual M2 calculation identity.
ADR 0123 SHALL remain a proposal until the R1.3 readiness checks pass.

#### Scenario: Retain one reproducible ideal coast result

- **WHEN** the separately instructed R1.4 implementation produces a completed result
- **THEN** JSON SHALL contain schema version, normalized actual scenario and input digest, complete selected candidate, model ID/omissions, state count and ordered states, input/result identities, execution diagnostics and source/resource provenance
- **AND** model ID SHALL remain `sun-centered-zero-revolution-patched-conic-v1`; the positive reference SHALL use 121 existing-sampler coast states, without new propagation during export or relabelling coast endpoints as parking-orbit states
- **AND** normalized-input digest SHALL use ADR 0123's sorted compact finite UTF-8 JSON rules including supplied-but-ignored fields; result identity SHALL also bind candidate data, sample count, model, actual source/resource hashes and schema version, excluding timings/creation timestamps
- **AND** actual Python/TudatPy versions, source revision/hashes/dirty state, kernel identities/order/hashes, GMs, selection policy, search completion/limits/seed and sampler conventions SHALL be retained; missing required provenance SHALL be unavailable, not invented

#### Scenario: Keep distinct scientific and exchange conclusions

- **WHEN** a calculation, reserve check or exchange check completes or fails
- **THEN** calculation, reserve, qualification and exchange SHALL use ADR 0123's separate status domains; successful parsing SHALL NOT turn an unqualified result into ideal-model-feasible or mission-qualified
- **AND** ideal-model-feasible SHALL require completed numeric/model checks and the unchanged reserve accounting; the reference SHALL require final_mass_kg >=550 and independent accounting within 1e-9kg
- **AND** absent covariance, tracking and safety data SHALL remain null/not-modelled; failures SHALL preserve error stage/message and available provenance without stale/partial successful exports

### Requirement: Freeze a narrow OEM profile before exporter implementation

The draft `ariadna-oem-kvn-v1` SHALL follow ADR 0123's explicit baseline and SHALL
NOT imply latest-edition conformity, third-party certification or all-OEM support.

#### Scenario: Resolve the exact baseline and responsible originator

- **WHEN** R1.3b prepares profile acceptance
- **THEN** it SHALL freeze the inspected CCSDS 502.0-B-3 April 2023 EC1 May 2023 document bytes/hash and reconcile later advertised corrections or explicitly review retaining this older baseline; unavailable correction text SHALL NOT be asserted irrelevant
- **AND** the actual responsible ORIGINATOR and its required SANA identity SHALL be verified, or a clearly labelled experimental deviation SHALL be separately proposed for user review; no Ariadna registration or authority to emit for another agency SHALL be assumed
- **AND** the unresolved baseline/originator and unverified reader/fixtures SHALL leave R1.3 open and SHALL NOT authorize production exporter implementation or external registration

#### Scenario: Represent only one admitted coast segment

- **WHEN** an admitted result is serialized after profile acceptance
- **THEN** OEM SHALL use version3.0, KVN ASCII/LF/final newline, one metadata/data segment, mandatory profile/research/result-ID comments immediately after the version, explicit UTC creation date, actual originator and result-ID MESSAGE_ID
- **AND** hypothetical OBJECT_NAME/OBJECT_ID SHALL be UNKNOWN, CENTER_NAME SHALL be SOLAR SYSTEM BARYCENTER, REF_FRAME SHALL be ICRF and TIME_SYSTEM SHALL be TDB; START_TIME/STOP_TIME SHALL match encoded endpoint epochs
- **AND** only provenance-admitted DE4xx-compatible SPICE J2000 axes SHALL map identically to ICRF; unsupported origin/frame/provenance/time SHALL fail without renaming, rotation, translation or automatic resource queries
- **AND** acceleration, covariance, maneuvers, extra segments, interpolation recommendations, usable-time overrides, REF_FRAME_EPOCH and user-defined keywords SHALL be omitted/rejected by this subset; no between-node accuracy or safety guarantee SHALL be implied

#### Scenario: Convert units and time without changing the physical samples

- **WHEN** each finite six-state is written
- **THEN** its numeric TDB epoch SHALL be represented as Gregorian TDB from the 2000-01-01T12:00:00 TDB anchor with six fractional digits, round-half-even/carry, years1900–2100, without Z or UTC/Unix conversion
- **AND** the six SI components SHALL be divided by1000 into km/km/s and emitted in normalized uppercase scientific notation with16 significant decimal digits and no units suffix
- **AND** calendar overflow, invalid/leap-second fields, nonfinite/bool values, wrong shapes, nonincreasing epochs and duplicate epochs after formatting SHALL fail before export publication
- **AND** UTC display strings SHALL NOT replace numeric TDB epochs; repeated exports of an identical stored creation-time/export request SHALL produce identical bytes, without altering scientific result identity

### Requirement: Independently decode and physically compare exported bytes

R1.3 SHALL select and verify independent reader `r1-oem-audit-v1` before exporter
implementation; local decoding SHALL NOT be advertised as third-party validation.

#### Scenario: Establish a separate reader against hand-authored fixtures

- **WHEN** R1.3b verifies its private stdlib verification reader
- **THEN** it SHALL parse file bytes using independently implemented Decimal/calendar arithmetic without production writer, its conversion/formatting helpers or Tudat imports; reader version/source hash SHALL be frozen before exporter work
- **AND** hand-authored asymmetric mixed-sign state data and independent expected SI/TDB tables SHALL cover epoch0, negative offset, day/leap-year/rounding carry and exact metadata/count/order; the retained R1.1 121-state payload SHALL support later offline acceptance without a new planner run
- **AND** unsupported version/section/frame/time/units, duplicate/missing metadata, extra/malformed fields, nonfinite data, unordered/duplicate epochs, truncated files, bounds mismatch and newline/comment injection SHALL be rejected by profile checks
- **AND** deliberately wrong1000x units, swapped axes or false UTC/TDB labels SHALL fail expected-physical-data comparison even when syntax parses; a parser alone SHALL NOT detect arbitrary lying metadata

#### Scenario: Verify every node through the independent reader

- **WHEN** R1.4 checks serialized bytes and their paired result
- **THEN** decoded centre/frame/time tokens, sample count/order and metadata endpoints SHALL match the admitted contract exactly; every reconstructed epoch SHALL differ by <=1e-6s and every SI vector by Euclidean <=0.001m position /1e-9m/s velocity
- **AND** JSON SHALL retain the OEM SHA256, profile/version, reader identity, maximum residuals and pass/fail/unavailable status; OEM MESSAGE_ID SHALL bind the result ID without a cyclic hash requirement
- **AND** read/compare failure SHALL disable export publication and preserve diagnostic evidence, without retries, loosened gates or promotion of physical qualification

### Requirement: Invalidate stale display and download state

The R1 result path SHALL reuse existing UI invalidation mechanisms and bind every
visible/downloadable result to current normalized inputs, selection and resources.

#### Scenario: Inputs or selected result cease to match

- **WHEN** actual inputs change, calculation starts/fails, resources/model change, or the selected candidate changes
- **THEN** old selected/sample/export caches and downloads SHALL be invalidated before presenting a current result; changed scenario/resources/model SHALL also invalidate the search
- **AND** a late calculation SHALL be published only if its captured identity still matches current controls; candidate changes MAY preserve the search but SHALL discard the old sampled/exported result
- **AND** sort/filter-only edits MAY preserve a still-selected matching candidate; stale UI/export behavior SHALL be tested independently of scientific and file-format success
