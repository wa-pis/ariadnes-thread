## ADDED Requirements

### Requirement: One retained-central-matrix research correction
D11 SHALL test at most one correction computed from the retained D10 central
matrix around the original seed, without re-probes, iterative targeting,
additional fractions, changed settings or modifications to D4–D10 contracts.

#### Scenario: Verify central evidence and replay the baseline
- **WHEN** D11 receives pinned 0079 and 0095 with SHA256 17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235 and 8be4356f4c339eaad9ca30ce2f49786d7e65498ae731fc468d8810836a97fb55
- **THEN** it verifies completed D10 evidence, scenario/candidate/seed/target, reference/runtime/resource/settings identity, thirteen nominal runs, six finite ordered central columns reconstructed from raw endpoint residuals with the original scales, and both passing <=0.10 D10 nominal slope checks before preparing a correction
- **AND** a fresh nominal baseline must match both retained nominal reports at all four identical epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg; mismatch stops before the solve, and a baseline already within 1000 m and 0.01 m/s stops as baseline-closed without a solve or trial

#### Scenario: Solve and cap one new direction
- **WHEN** the baseline replay passes and is not closed
- **THEN** D11 forms J with residual rows and central-control columns, solves J*z=-r once for the fresh scaled residual using NumPy least squares with rcond=0.000000000001, records finite singular values/rank and requires rank six without a fallback
- **AND** it records uncapped z, divisor=max(1,norm_inf(z)), capped z, dx=T*z/divisor with T=(0.25 rad,0.25 rad,600 s) repeated twice, and the signed/scaled prediction r+J*(dx/T); a zero step, nonfinite result or predicted score not strictly below baseline stops before trial propagation

#### Scenario: Evaluate one trial and optionally freeze it for tighter checking
- **WHEN** the capped correction is available
- **THEN** the sole nominal trial uses seed+dx at alpha=1 through existing canonical angle/window/mass gates, with the unchanged target and fresh matched environment
- **AND** empirical improvement requires S_trial <= S_baseline*(1-0.0001) or both unchanged closure gates, with separate position/velocity misses, predicted/observed residual changes, score ratio and threshold; non-improvement stops without tighter propagation
- **AND** only an improving trial receives one tighter evaluation with frozen canonical commands, initial and target states; all four boundaries use the existing 10 m, 0.0001 m/s and 0.000001 kg gates, and failed/unavailable agreement does not erase nominal improvement or trigger another command

#### Scenario: Enforce a single invocation budget and preserve failure evidence
- **WHEN** D11 completes or any replay/analytic/native/event/nonfinite/deadline gate fails
- **THEN** one shared cooperative 300-second clock and limits of two control attempts, three evaluations and nine native launches apply from input verification through reporting, nominal attempts count before analytic validation, and the frozen tighter run adds no control attempt
- **AND** finite exclusive-output JSON retains pinned/current/imported provenance, raw residuals, imported matrix, solve/cap/prediction, exact commands, available comparisons, attempted/completed counters, unavailable reasons and separate wall time; completed earlier diagnostics remain, unfinished endpoints do not
- **AND** no retry, additional fraction, derivative probe, second solve or budget increase occurs, continuous_safety_verified stays false and improvement, closure and numerical agreement remain distinct from strict M3 or mission qualification

### Requirement: Approval-gated central-column research diagnosis
D10's scope in ADR 0093 was explicitly approved by the user on 2026-10-04.
D10 SHALL test a nominal central Jacobian at the
original six D7 probe increments without selecting commands, solving another
correction, changing production settings or modifying D4–D9 contracts.

#### Scenario: Bind retained evidence and replay nominal inputs
- **WHEN** an approved D10 invocation receives 0079, 0086 and 0092
- **THEN** it verifies the pinned SHA256 hashes 17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235, c370c31f4a3dcd1f3ef324d0f2331bb46d707af0eae6d256ee935471a6c9233d and 164760a35451b3e8cf43bf2213e8466a331dbcb85004249e134e9daefa1a7374 respectively, scenario/candidate/seed/target, resource/runtime/settings identity and completed retained diagnostics before perturbation
- **AND** it verifies the finite retained rank-six D7 direction/Jacobian and nonzero predicted norm, replays all four nominal baseline boundaries against all three references at identical epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg, and verifies each positive probe against its matching D7 run with those same gates before the corresponding negative probe
- **AND** any mismatch stops without running later commands, while cross-profile baseline disagreement is retained as context rather than used to relax replay gates

#### Scenario: Evaluate only the prescribed central columns
- **WHEN** the baseline replay passes
- **THEN** D10 forms twelve independent seed-based perturbations, positive then negative per column, in departure then arrival azimuth/elevation/duration order with h=(0.00001 rad,0.00001 rad,1 s) repeated twice, using the existing canonical command gates, fixed target epoch and fresh matched environments
- **AND** the baseline and twelve probes use nominal settings only, with limits of thirteen control attempts counted before analytic validation, thirteen evaluations and thirty-nine native launches under one cooperative 300-second clock from input verification through reporting
- **AND** analytic rejection, sampled event, native failure, nonfinite calculation or deadline terminates the invocation without retries, tighter runs, chained controls, incomplete endpoints or automatically enlarged limits

#### Scenario: Compare central prediction with retained directional response
- **WHEN** all thirteen nominal evaluations complete
- **THEN** with scaled residuals r, original trust scales T and z=retained_step/T it reports columns C_i=(r(+h_i)-r(-h_i))*T_i/(2*h_i), F_i=(r(+h_i)-r(0))*T_i/h_i and E_i=((r(+h_i)-r(0))+(r(-h_i)-r(0)))*T_i/(2*h_i), including signed differences from the retained D7 columns and the arithmetic identity F_i-C_i=E_i
- **AND** it reports each central/forward directional contribution, E_i*z_i, their sums, retained and new predictions and cancellation metrics, with explicit unavailable reasons for zero-denominator or nonfinite ratios
- **AND** the two norm(D9_nominal(a)-sum(C_i*z_i))/norm(g_D7) checks for a=2^-14 and 2^-15 use the exploratory <=0.10 threshold; overall nominal directional consistency requires both checks, zero central direction is not divided by, and no correction solve or command selection occurs even if a probe improves
- **AND** consistency at this one seed/increment/profile does not qualify individual columns, cross-profile sensitivity, derivative error bounds, convergence, accuracy, mission closure or continuous safety

#### Scenario: Retain complete or failed column-study evidence
- **WHEN** D10 completes or aborts
- **THEN** finite exclusive-output JSON retains source/reference/resource/settings identities, historical imported hashes separately from current source hashes, seed and exact commands/column/sign ordering, raw SI and scaled residuals, replay differences, attempted/completed counters, available columns/checks with unavailable reasons and separate wall time
- **AND** earlier evidence is untouched, unavailable summaries are not manufactured from incomplete pairs, continuous_safety_verified remains false and no additional native study is started automatically

### Requirement: Bounded local directional-response diagnosis
D9 SHALL evaluate the retained D7 direction around the original seed using
alpha=(0,+2^-14,-2^-14,+2^-15,-2^-15), with nominal then frozen tighter
propagation for each command. It SHALL preserve the physical model, target,
reference bindings and existing D4-D8 contracts without selecting a command
or performing another correction solve.

#### Scenario: Verify inputs and both baseline profiles
- **WHEN** D9 receives the pinned 0079 and 0086 artifacts
- **THEN** it verifies their hashes, scenario, candidate, seed, finite rank-six direction, Jacobian and resource/runtime/settings identity under the shared deadline
- **AND** the nominal baseline must match the retained 0079/0086 nominal boundaries and the tighter baseline must match 0079 tighter boundaries at identical epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg before perturbations
- **AND** nominal-versus-tighter disagreement is retained as a diagnostic and does not replace within-profile replay checks or prevent the requested sensitivity study

#### Scenario: Execute fixed small perturbations
- **WHEN** both baseline replay checks pass
- **THEN** the four signed perturbations are independently formed as seed+alpha*retained_step in the specified order, validated through the existing command gates, and each receives nominal then tighter propagation with frozen canonical controls and fresh matched environments
- **AND** control attempts count five distinct nominal commands before analytic validation, while all ten profile evaluations and thirty native launches are counted independently; frozen tighter runs add no control attempt
- **AND** one cooperative 300-second clock covers verification through reporting; a command rejection, sampled event, native failure, nonfinite calculation or deadline stops all later runs without retries or partial endpoints

#### Scenario: Quantify response rather than choose a correction
- **WHEN** all ten profile evaluations complete
- **THEN** using scaled signed residuals r and g=J*(retained_step/trust_scales), D9 reports predicted and observed changes at every signed alpha, central slopes D(a)=(r(+a)-r(-a))/(2*a) and curvature C(a)=(r(+a)+r(-a)-2*r(0))/(2*a) for a=2^-14 and 2^-15 in each profile
- **AND** with G=norm(g)>0 it reports norm(D(a)-g)/G, norm(C(a))/G, norm(D(a)-D(a/2))/G and norm(D_nominal(a)-D_tighter(a))/G, including signed vectors and unavailable-ratio reasons rather than NaN or infinity
- **AND** each discrepancy is diagnostically consistent when at most 0.10; overall consistency requires every model, curvature, scale and profile check to pass, and the report records actual thresholds without implying absolute accuracy, a derivative error bound, mission closure or continuous safety
- **AND** zero predicted directional norm prevents perturbations with an explicit unavailable diagnostic; improvement/closure is informational only and no trial is selected even if its score decreases

#### Scenario: Preserve complete or failed diagnostic evidence
- **WHEN** D9 finishes or aborts
- **THEN** finite exclusive-output JSON retains source/reference/resource/settings provenance, original direction/Jacobian, exact commands and alpha/profile ordering, residuals, baseline comparisons, completed discrepancies and attempted/completed counters with contextual reasons
- **AND** missing comparisons remain absent with a reason, historical imported source hashes remain distinct from current hashes, wall time is separate, and continuous_safety_verified remains false

### Requirement: Bounded damping of a retained research correction
D8 SHALL evaluate the retained D7 control direction at alpha=0.5 followed by
alpha=0.25 only if the first completed nominal trial does not improve. It SHALL
reuse the original seed, physical model and integrator settings without new
probes, a new solve, chained updates or changes to D4–D7 contracts.

#### Scenario: Bind evidence and replay the baseline
- **WHEN** D8 receives the pinned Decision 0079 and Decision 0086 artifacts
- **THEN** it verifies hashes, normalized inputs, seed, candidate, runtime/resources/settings and a finite rank-six D7 direction within the existing trust scales before damping
- **AND** a fresh nominal baseline must match both retained baselines at all four boundary epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg; mismatch stops before either fraction, and an already-closed baseline stops without a convergence claim

#### Scenario: Try fractions in deterministic order
- **WHEN** the baseline passes and remains outside target closure
- **THEN** each attempted command is canonicalized from x_seed+alpha*dx_D7 with alpha in (0.5,0.25), never from a previous trial
- **AND** improvement is both unchanged endpoint gates of 1000 m and 0.01 m/s passing or S_trial <= S_baseline*(1-0.0001*alpha), using the existing residual scales of 1000 m and 0.01 m/s
- **AND** the first improving nominal trial is selected, any remaining fraction is explicitly skipped, and no probes, alpha=1 repeat, additional fraction or second iteration runs

#### Scenario: Validate only the selected trial
- **WHEN** a nominal fraction is selected
- **THEN** exactly one tighter run uses its frozen canonical controls, initial state and epochs in a fresh resource-matched environment, with all four boundary differences checked against 10 m / 0.0001 m/s / 0.000001 kg
- **AND** disagreement or unavailable validation remains separate from nominal improvement and cannot trigger another fraction; if neither fraction improves, no tighter run starts

#### Scenario: Bound failures and preserve honest evidence
- **WHEN** validation, a command, a sampled guard, integration or the deadline fails
- **THEN** no subsequent run starts; incomplete endpoints remain absent, previous completed diagnostics and contextual reasons are retained, and no successful mission is inferred
- **AND** one shared 300-second cooperative deadline, three control attempts, four propagation evaluations and 12 native launches bound the invocation with no retries or budget resets
- **AND** exclusive finite JSON records both references, source/resource/settings identity, frozen direction, controls and alpha, residual norms/scores/ratios with explicit unavailable reasons, actual acceptance thresholds, selected/skipped fractions, counters, coverage and separate wall time, always with continuous_safety_verified=false

### Requirement: Bounded research-only command correction
The D7 experiment SHALL test at most one six-control update from the prescribed
reference seed, using the unchanged physical model, target and nominal/tighter
integrator profiles. D4–D6 limits SHALL remain unchanged. D7 SHALL remain separate
from the production corrector and SHALL always disclaim continuous safety.

#### Scenario: Verify baseline before changing commands
- **WHEN** D7 is invoked for the pinned reference fixture and candidate d0001-t0035
- **THEN** it verifies Decision 0079 identity, scenario, candidate, seed and resource provenance and recomputes a nominal baseline with a fresh environment
- **AND** probes start only if all four boundary epochs and controls match and state/mass drift stays within 10 m, 0.0001 m/s and 0.000001 kg; otherwise the report records the mismatch and no probe launches

#### Scenario: Compute one empirical correction
- **WHEN** the baseline completes and does not already meet both target gates
- **THEN** six forward probes run in control order using increments (0.00001 rad, 0.00001 rad, 1 s) for each burn, with separate fresh resource-matched environments
- **AND** the scaled residual uses 1000 m and 0.01 m/s, trust scales use (0.25 rad, 0.25 rad, 600 s) for each burn, and the scaled Jacobian and NumPy least-squares solve use rcond=1e-12 with finite rank six required
- **AND** the update is capped to unit infinity norm in trust coordinates before one alpha=1 trial; no damping retry, alternate finite difference, extra iteration or probe-as-command is permitted

#### Scenario: Distinguish improvement from target closure and validation
- **WHEN** the corrected nominal trial completes
- **THEN** the report stores signed terminal residuals, separate position/velocity norms, scaled score and its ratio to baseline (null with reason for a zero denominator)
- **AND** improvement means both endpoint gates of 1000 m and 0.01 m/s pass or the score is at most 0.9999 times the baseline score; neither improvement nor closure implies mission qualification
- **AND** only an improving trial receives one frozen-command tighter run, whose four boundary differences use the unchanged 10 m / 0.0001 m/s / 0.000001 kg gates and whose failed or unavailable agreement is retained separately

#### Scenario: Preserve bounded failures and evidence
- **WHEN** a control or probe is rejected, the Jacobian loses rank, a native run fails, a sampled guard triggers or the deadline expires
- **THEN** no further trial starts; the reason, prior completed evidence and attempted/completed counts remain, while incomplete endpoints and unavailable comparisons stay absent
- **AND** one shared 300-second cooperative deadline, eight control attempts, nine propagation evaluations and 27 native arcs are hard invocation limits, with no retries or automatically enlarged budget
- **AND** finite exclusive-output JSON records source/reference/resource/settings identity, each run's controls and role, residual changes, Jacobian, rank and singular values when available, sampled-check coverage and separate wall time; the report never marks strict M3 or continuous safety complete

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
