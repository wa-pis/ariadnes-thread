## ADDED Requirements

### Requirement: Separate opt-in research experiment
The system SHALL provide an explicitly requested D4 research experiment distinct
from strict M3 refinement. It SHALL NOT return PhysicalTrajectoryResult, claim
converged M3 status, certify continuous safety or complete task 3.9. Existing M3
acceptance gates SHALL remain unchanged. The first experiment SHALL propagate
one fixed seed command, not optimize commands or silently choose a candidate.

#### Scenario: Run the reference experiment
- **WHEN** the user explicitly selects examples/m3_feasible_mission.toml and candidate d0001-t0035 from its default 2000-budget search
- **THEN** the experiment verifies the candidate against that scenario, records the normalized inputs and identifier, and labels all output research-only with continuous_safety_verified=false
- **AND** selecting another budget or scenario does not silently reuse the reference candidate's stored physical data

### Requirement: Fixed-command finite-burn propagation
The experiment SHALL reuse the pinned direct-SPICE M3 force inventory, physical
boundary-state conventions, existing TNW engine adapter and analytic seed
controls. It SHALL propagate departure burn, coast and arrival burn with coupled
mass and exact state handoff, without resetting state or mass between arcs.
It SHALL retain input/resource validation, analytic dry-mass rejection, sampled
mass/collision guards, detected-event handling and native failure checks. Unlike
strict M3, a whole-interval safety enclosure is not a prerequisite for this
separately labelled experiment; its absence SHALL be explicit in every report.

#### Scenario: Complete a nominal seed
- **WHEN** all three nominal arcs complete without a detected invalid state
- **THEN** the report contains four ordered boundary states in SI/SSB/J2000 with TDB epochs, two positive-duration burns, their directions and consumed masses, and position/velocity residual norms against the configured target state at the arrival epoch
- **AND** a miss is reported as a miss rather than silently corrected or called convergence

#### Scenario: Reject detected unsafe or failed propagation
- **WHEN** an initial or evaluated state reaches dry mass or a configured collision boundary, resources are unavailable, or the native integrator fails
- **THEN** the experiment stops with a reason and body/arc/epoch context where available, reports no completed endpoint or target residual from partial history, and never clamps mass or continues from an unsafe state
- **AND** event rejection takes precedence over a final-epoch mismatch caused by that event

#### Scenario: Declare observation limits
- **WHEN** any report is produced
- **THEN** it identifies which states/events were checked and explicitly states that undetected between-check impacts, small bodies and debris are not excluded; minimum sampled separation is not labelled continuous clearance

### Requirement: Independent integration-profile comparison
After nominal completion the experiment SHALL repropagate identical commands and
arc boundaries with the existing tighter profile. It SHALL report all four
boundary differences in metres, metres/second and kilograms. Numerical agreement
SHALL require differences no greater than 10 m, 0.0001 m/s and 0.000001 kg at
every boundary. Agreement SHALL NOT imply target closure or real-world accuracy.

#### Scenario: Compare frozen commands
- **WHEN** both profiles finish within resource limits
- **THEN** numerical_agreement is true only if all stated thresholds pass, target residuals are reported separately, and the commands are identical in both runs

#### Scenario: Comparison fails or cannot complete
- **WHEN** a boundary difference exceeds a threshold or the tighter run fails or times out
- **THEN** numerical_agreement is false or unavailable respectively with its reason; completed nominal diagnostics may be retained only as explicitly unverified research evidence, never a successful strict-M3 result

### Requirement: Bounded reproducible research report
The first experiment SHALL share the scenario's monotonic runtime budget across
candidate verification, resource preparation, nominal propagation and tighter
comparison (default 300 seconds, no reset). It SHALL allow at most six native
arc launches, with no optimizer, retries or hidden background runs. It SHALL
record attempted/completed arc counts, model/resource provenance, commands,
integrator settings, checked-state counts and outcome. Wall-clock diagnostics
SHALL be separated from reproducible scientific values.

#### Scenario: Stop at the budget
- **WHEN** the runtime budget expires or another arc would exceed six launches
- **THEN** no further arc is started, timeout/budget failure is explicit and partial diagnostics are not marked as a completed trajectory

#### Scenario: Repeat identical input
- **WHEN** identical inputs, resources and commands are run twice with sufficient time
- **THEN** scientific report values and classification agree, excluding wall-clock measurements, without modifying existing M2 outputs or strict M3 acceptance

### Requirement: Isolated identical-start coast diagnosis
The research-only D5 follow-up SHALL compare the two existing coast integrator
profiles from the same stored nominal departure-cutoff Cartesian state, mass
and TDB epoch to the same stored arrival-ignition epoch. Its reference SHALL be
the retained Decision 0079 report, whose science was reproduced in Decision 0081.
It SHALL verify the input artifact digest, normalized scenario, reproduced
candidate, epochs, frames and resource/model identity before propagation. A
stored cutoff is an experimental initial condition, not a qualified mission state.
Each profile SHALL use a fresh pinned full-force environment without thrust.
No departure or arrival burn, optimizer, retargeting or changed tolerance is
permitted. This separate experiment SHALL share one 300-second cooperative
deadline from input verification through both profiles and allow at most two
native arc launches, counted before execution, with zero automatic retries.

#### Scenario: Compare profiles with identical inputs
- **WHEN** the verified reference is propagated with nominal and tighter coast settings
- **THEN** both native initial histories match the same seven supplied SI state/mass components and start epoch exactly, both end at the stored arrival-ignition epoch within the existing 1 microsecond completion tolerance, and every saved coast mass equals the initial mass
- **AND** the report records both endpoints and their position, velocity and mass differences using unchanged 10 m, 0.0001 m/s and 0.000001 kg comparison thresholds, without claiming either profile is ground truth

#### Scenario: Distinguish restart drift from inherited differences
- **WHEN** both coast profiles complete
- **THEN** the report separately records the new nominal endpoint minus the stored nominal endpoint, the new nominal endpoint minus the new tighter endpoint, and the new tighter endpoint minus the stored tighter endpoint, as signed Cartesian differences and norms with explicit units
- **AND** it does not subtract norms to attribute errors, interpret restart drift exceeding existing comparison thresholds as isolated integration error, or claim that the new tighter-minus-stored-tighter difference is a mathematically exact sensitivity estimate

#### Scenario: Reject invalid inputs or an incomplete coast
- **WHEN** reference identity fails, a sampled guard rejects a state, the deadline expires or a native arc fails
- **THEN** no subsequent native arc starts, attempted/completed counters and a contextual reason are retained, and the failed arc has no endpoint or comparison derived from partial history
- **AND** complete prior-profile evidence may remain explicitly unqualified; D4 pre-arc/full-step/saved-history guards, dry-mass equality rejection, event-before-epoch-mismatch handling and declared coverage limitations remain in force

#### Scenario: Preserve diagnostic provenance
- **WHEN** a coast diagnostic finishes or aborts
- **THEN** finite machine-readable evidence records the reference digest, source identity, normalized scenario, candidate, resource/model metadata, actual integrator settings, supplied initial state and epochs, guard coverage, counters and outcome separately from wall time
- **AND** it states research-only and continuous_safety_verified=false, does not overwrite prior evidence, and does not qualify target closure, strict M3 or task 3.9

### Requirement: Bounded single-variable coast step study
The research-only D6 study SHALL run at most three coast profiles from the same
nominal departure cutoff used by D5, in order of maximum step 21600, 10800 and
5400 seconds. Each SHALL use the pinned tighter rkdp_87 profile with only its
maximum_step_s changed in a diagnostic-local copy. Relative/absolute tolerances,
initial/minimum step, termination policy, forces, mass, start/end epochs and
reference conventions SHALL remain unchanged. Production profiles and D5's
two-launch limit SHALL remain unchanged. One shared 300-second cooperative
deadline SHALL cover input verification, preparations and all three launches.
No retries, additional profiles, optimizer or automatic production promotion
are permitted. D5 reference/resource verification and sampled guards SHALL apply.

#### Scenario: Bind the step-study baseline
- **WHEN** D6 starts with verified Decision 0079 and Decision 0082 artifact identities
- **THEN** each native initial history matches the same seven supplied state/mass components and epoch exactly, and the first completed endpoint is compared to Decision 0082's tighter endpoint
- **AND** if baseline drift exceeds 10 m, 0.0001 m/s or 0.000001 kg, no smaller-step profile starts and the report states baseline mismatch rather than attributing a difference to step refinement

#### Scenario: Change only the maximum step
- **WHEN** all three diagnostic settings are constructed
- **THEN** their scientific settings differ only in maximum_step_s with exact values 21600, 10800 and 5400, and querying the original production profiles before and after returns identical values
- **AND** each profile uses a fresh resource-matched full-force environment without thrust, preserves constant coast mass and completes under the existing epoch tolerance

#### Scenario: Report empirical refinement without an accuracy claim
- **WHEN** all profiles finish
- **THEN** the report contains signed endpoint differences and position/velocity/mass norms for every pair, plus unchanged-threshold flags for each pair
- **AND** it reports the second adjacent difference divided by the first separately for position and velocity when the denominator is positive; zero denominators produce null ratios with an explicit reason, never NaN, infinity or a fictitious convergence order
- **AND** it distinguishes decreasing, unchanged or increasing adjacent differences without asserting absolute accuracy, an asymptotic order, a global error bound or task-3.9 safety

#### Scenario: Observe whether the step cap changed the calculation
- **WHEN** a profile completes
- **THEN** the report retains a digest of its ordered saved epoch sequence and saved-interval count, minimum, median and maximum in seconds, labelled saved intervals rather than RK stages or all attempted internal steps
- **AND** unchanged saved meshes or unchanged endpoints are reported explicitly and are not by themselves called proof of convergence

#### Scenario: Preserve failures and stop within the study budget
- **WHEN** input verification fails, a sampled event is rejected, a native call fails or the shared deadline expires
- **THEN** no further profile starts, attempted/completed arc counts and contextual reasons are retained, incomplete profiles expose no endpoint, and comparisons requiring missing endpoints are unavailable
- **AND** evidence is finite JSON, records source/reference/resource/settings identity and guard coverage, separates wall time, never overwrites earlier artifacts and always disclaims continuous safety and mission qualification
