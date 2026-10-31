## ADDED Requirements

### Requirement: Explicitly accept the successor scope before new physical work

The proposed R2 actual-reference coast verification SHALL preserve completed R1
and all existing scientific gates. ADR0126 SHALL remain a proposal until the
next priority and detailed verification contract are explicitly accepted.

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
