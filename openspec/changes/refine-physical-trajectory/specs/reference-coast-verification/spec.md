## ADDED Requirements

### Requirement: Explicitly accept the successor scope before new physical work

The user-selected R2 actual-reference coast verification SHALL preserve completed
R1 and all existing scientific gates. ADR0126 priority and ADR0127 preparation
contract are accepted; ADR0128 records native-free preparation, not R2.3 execution.

#### Scenario: Record a successor without automatically executing it

- **WHEN** the completed R1 demonstrator is reviewed and R2 is proposed
- **THEN** documentation SHALL distinguish synthetic physical verification, all-node file conversion and actual-reference coast verification; the latter SHALL remain unverified
- **AND** the proposal SHALL authorize zero native calls, no new oracle/runner or UI code, no automatic D18/D17 replay, no new force model and no automation restart
- **AND** another selected priority SHALL leave this proposal deferred, without changing retained evidence or R1 completion

### Requirement: Freeze the actual-reference verification contract before preparation

After scope acceptance, R2.1 SHALL bind ADR0119's original reference, independently
derived coast and explicit source/resource/frame/time alignment before code or
native execution. This requirement SHALL NOT assert that the contract is ready.

#### Scenario: Declare the missing inputs and independent method

- **WHEN** the detailed R2.1 contract is prepared
- **THEN** it SHALL bind ADR0119 SHA2563606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0, run1, candidate d0001-t0035, all121 original SI/SSB/J2000 states and numeric TDB epochs, retained Sun GM and unchanged ordered kernel identity
- **AND** it SHALL explicitly account for the missing Sun track, define its permitted acquisition/freeze/audit process and initial-state derivation, and forbid fitting to later samples or changing candidates/epochs
- **AND** it SHALL specify independent Cartesian-to-conic/initial-phase equations, admitted domain, pure analytic fixtures, exact time/frame translations, justified fixed numerical gates and one bounded fail-stop execution budget before preparation
- **AND** shared Sun ephemerides SHALL remain declared inputs, not independent ephemeris validation; success SHALL NOT qualify search optimality, finite burns, mission safety or strict M3/M6

#### Scenario: Fail to establish readiness

- **WHEN** input identity, resource/time coverage, oracle domain, numerical gates or execution budget is unresolved
- **THEN** preparation/execution SHALL remain unavailable with the missing check named; no native query, retry, tolerance relaxation, substitute trajectory or new propagation SHALL fill that gap without the separately accepted contract


### Requirement: Freeze the independently derived reference-coast contract

The R2 study SHALL use ADR0127's exact inputs, equations, admitted domain, gates
and bounded procedure only after detailed-contract acceptance and verified
preparation. Recording the contract SHALL NOT authorize native execution.

#### Scenario: Recover the actual initial phase without fitting retained samples

- **WHEN** the independent verifier is prepared under the accepted detailed contract
- **THEN** its seed SHALL be retained Moon departure position/velocity minus matching Sun0, plus retained departure excess velocity with ADR0127's explicit operation order; no saved propagated spacecraft node or final state SHALL set or fit the seed
- **AND** the oracle SHALL derive h, evec, a, P/Q/W, E0 via atan2 and M0, then solve remainder(M0+n*dt,2*pi) with at most64 bisections, bracket width and residual each<=2e-14rad; it SHALL use only stdlib scalar/vector arithmetic without production or native conversion/propagation helpers
- **AND** its admitted domain SHALL be finite nondegenerate negative-energy input, 1e9<=a<=1e13m, 1e-6<=e<=0.95 and orthonormal/right-handed basis within1e-12; unsupported input SHALL stop unavailable without candidate substitution, fitting or clamping
- **AND** eight tilted/prograde/retrograde initial fixtures at E0=0,+pi/2,pi,-pi/2 SHALL reconstruct within0.01m/1e-8m/s, relative a and absolute e errors<=1e-12 and wrapped phase<=2e-14rad; independent forward-phase/recurrence and negative/budget fixtures SHALL pass before native execution

#### Scenario: Compare every retained point in explicitly aligned frames

- **WHEN** the separately instructed study evaluates the frozen121-point reference
- **THEN** at every original numeric TDB epoch, both Sun-relative and re-added SSB state differences SHALL be Euclidean<=1m position/1e-6m/s velocity with exact epoch/dt/GM alignment; no mean or median SHALL replace any node's gate
- **AND** each path's Sun-relative specific-energy and vector-angular-momentum relative errors against the unchanged initial seed SHALL be<=1e-12; raw Sun states, seed operands, initial residual, signed differences, roots and frame translations SHALL be retained
- **AND** the Sun ephemeris SHALL remain a shared authoritative input, not independently validated truth; successful comparison SHALL leave finite burns, scalar mass dynamics, mission safety, search optimality and strict M3/M6 unqualified

#### Scenario: Stop one bounded study and preserve provenance and failures

- **WHEN** verified preparation and a separate execution instruction permit R2.3
- **THEN** a fresh pinned process SHALL admit only the original ordered13-kernel hashes and ADR0127 runtime/source identities; at most121 exact-epoch Sun provider calls and zero native spacecraft propagations/planner/sampler/extra-body/GM reads SHALL occur
- **AND** one cooperative30s budget SHALL include imports, resources, pure checks, comparisons, final inventory and evidence finalization, with checks before/after calls; actual non-preemptible overrun SHALL fail and retain returned data
- **AND** attempted/completed counts SHALL distinguish calls from returned states; first error/unavailable/domain/numeric/root/invariant gate SHALL stop further calls without retry, replacement samples or changed gates/budget
- **AND** exclusive new output SHALL retain full/partial evidence, original/reference/runner/native/resource hashes, counters, timing and contextual error; a zero-native offline audit SHALL recalculate all available comparisons before any R2 success claim
