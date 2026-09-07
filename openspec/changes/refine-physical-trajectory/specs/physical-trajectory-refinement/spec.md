## Purpose

Turn one explicitly selected M2 trade-space candidate into a reproducible, physically classified Moon-to-Mars trajectory with finite burns, coupled mass, and declared numerical limits.

## ADDED Requirements

### Requirement: Verified M2 candidate handoff
The system SHALL expose `refine_physical_trajectory(scenario: Scenario, candidate: ImpulsiveTransferCandidate) -> PhysicalTrajectoryResult`. It SHALL accept only a Pareto candidate reproduced from the same normalized scenario and M2 grid, and SHALL treat the M2 body-centre Lambert solution and scalar impulses only as the initial targeting seed rather than as physical endpoint states.

#### Scenario: Accept a matching Pareto candidate
- **WHEN** a candidate from the scenario's deterministic M2 Pareto front is supplied
- **THEN** recomputation matches its identifier, epochs, flight time, hyperbolic-excess vectors, burn magnitudes, and masses within `0.000001 s`, `0.000001 m/s`, and relative mass error `1e-12` before refinement begins

#### Scenario: Reject a mismatched candidate
- **WHEN** the identifier is malformed, is not on the scenario's Pareto front, or any supplied scientific value exceeds the handoff tolerance
- **THEN** the system raises `TrajectoryRefinementError` naming the candidate and performs no physical propagation

### Requirement: Physical orbit-to-orbit boundary states
The selected candidate's departure epoch SHALL mean departure-burn ignition and its arrival epoch SHALL mean arrival-burn cutoff. The initial state SHALL be the configured Moon-centred departure orbit at ignition, and the target state SHALL be the configured Mars-centred target orbit at cutoff. Public boundary states SHALL expose normalized UTC, TDB seconds since J2000, `SSB` origin, `J2000` orientation, position in meters, and velocity in meters per second. Neither physical state SHALL be placed at a body centre.

#### Scenario: Construct the reference departure state
- **WHEN** the configured circular 100 km lunar orbit is converted at ignition
- **THEN** the Moon-relative position norm differs from `1837400 m` by no more than `0.001 m` and the public SSB/J2000 state is finite

#### Scenario: Construct the reference target state
- **WHEN** the configured Martian target orbit with true anomaly zero is converted at cutoff
- **THEN** the Mars-relative position norm differs from `3689500 m` by no more than `0.001 m` and the state is not the M2 Mars-centre endpoint

#### Scenario: Close a feasible target
- **WHEN** refinement returns status `converged`
- **THEN** the terminal Mars-relative state differs from the configured target by no more than `1000 m` in Euclidean position norm and `0.01 m/s` in Euclidean velocity norm

### Requirement: Declared gravitational dynamics
The production trajectory SHALL use model identifier `ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-cannonball-srp-schwarzschild-v1`, direct inertial gravity from the Sun, Mercury, Venus, Earth, Jupiter, and Saturn, Moon `gggrx1200` spherical-harmonic gravity through degree and order 200, and Mars `jgmro120d` spherical-harmonic gravity through degree and order 120. The Moon field SHALL use GM `4902800121846.8 m^3/s^2`, normalization radius `1738000 m`, coefficient SHA-256 `3f4652c01db58e14a4e4c67fe8225874d10120a29cbd7699f5068469ef65b21d`, and `IAU_Moon`. The Mars field SHALL use GM `42828375815756.1 m^3/s^2`, normalization radius `3396000 m`, coefficient SHA-256 `d13b31d46862838abe62ebab3cef8209244588abe14e4e5e481c0fb64354e980`, and `IAU_Mars`. Loaded GMs SHALL match those values to relative error `1e-15`; each gravity field's associated frame SHALL equal its rotation-model target frame, whose base frame is `J2000`. Moon and Mars point-mass accelerations SHALL NOT be added separately because the harmonic terms already include degree zero. The harmonic fields' constants, coefficient files, frames, and hashes SHALL remain distinct from orbit-altitude shape radii and conservative collision surfaces.

#### Scenario: Match an independent force assembly
- **WHEN** acceleration components are evaluated at fixed near-Moon, cruise, and near-Mars SSB/J2000 states
- **THEN** the production total matches the vector sum from a separately configured direct TudatPy model within `max(1e-15 m/s^2, 1e-12 * sum(component norms))`

#### Scenario: Prevent gravity double counting
- **WHEN** the production acceleration inventory is inspected
- **THEN** Moon and Mars each have exactly one harmonic-gravity entry and no separate point-mass entry

#### Scenario: Preserve gravity and shape constants separately
- **WHEN** the force-model provenance is emitted
- **THEN** it reports the literal production model identifier, expected and actual coefficient hashes, `J2000`-to-`IAU_Moon` and `J2000`-to-`IAU_Mars` frame matches, orbit-altitude shape radii `1737400 m` and `3389500 m` separately from gravity normalization radii `1738000 m` and `3396000 m`, and the verified Moon/Mars field GMs `4902800121846.8 m^3/s^2` and `42828375815756.1 m^3/s^2`

#### Scenario: Define every collision surface
- **WHEN** collision protection is configured
- **THEN** it requires `pck00010.tpc` SHA-256 `59468328349aa730d18bf1f8d7e86efe6e40b75dfb921908f99321b3a7a701d2`, records the pinned SPICE radius vectors in meters as Sun `(696000000,696000000,696000000)`, Mercury `(2439700,2439700,2439700)`, Venus `(6051800,6051800,6051800)`, Earth `(6378136.6,6378136.6,6356751.9)`, Moon `(1737400,1737400,1737400)`, Mars `(3396190,3396190,3376200)`, Jupiter `(71492000,71492000,66854000)`, and Saturn `(60268000,60268000,54364000)`, and uses each vector's maximum as its conservative spherical guard

#### Scenario: Reject collision-resource drift
- **WHEN** any required SPICE radius vector is missing, nonpositive, non-finite, or differs from the pinned vector by more than `0.001 m`
- **THEN** refinement raises a resource error before propagation and does not substitute an orbit-altitude, harmonic-normalization, or default shape radius

#### Scenario: Bound lunar truncation sensitivity
- **WHEN** the converged commands are repropagated with Moon degree and order 400 while Mars remains at 120
- **THEN** every common boundary differs from the production result by no more than `500 m` and `0.0001 m/s`, and both values are recorded as model-resolution diagnostics

#### Scenario: Expose the Martian model ceiling
- **WHEN** the converged commands are repropagated with Mars degree and order 60 and compared with production degree and order 120
- **THEN** finite boundary differences are recorded and the result identifies degree 120 as the pinned coefficient model's ceiling without claiming a bound on omitted higher degrees

### Requirement: Solar radiation pressure, shadows, and relativity
The production trajectory SHALL model the spacecraft as a cannonball solar-radiation target using the scenario's area and reflectivity coefficient and the current propagated mass. The Sun source SHALL be configured explicitly with luminosity `3.828e26 W`, and the Moon, Earth, and Mars SHALL occult it. The force model SHALL include the Sun's Schwarzschild correction with PPN beta and gamma equal to one and SHALL exclude Lense-Thirring, de Sitter, and Einstein-Infeld-Hoffmann terms.

#### Scenario: Scale unshadowed radiation pressure
- **WHEN** area, reflectivity coefficient, or inverse mass is varied independently at otherwise identical unshadowed geometry
- **THEN** the solar-radiation-pressure acceleration scales linearly with that factor to relative error no greater than `1e-12`

#### Scenario: Evaluate clear, umbra, and penumbra geometry
- **WHEN** controlled full-illumination, total-occultation, and partial-occultation geometries are evaluated
- **THEN** every shadow factor lies in `[0, 1]`, the clear and umbra factors differ from one and zero by no more than `1e-12`, and the penumbra factor is strictly between them and matches direct TudatPy output within `1e-12`

#### Scenario: Include only Sun Schwarzschild relativity
- **WHEN** the relativistic acceleration is inspected at a fixed finite state
- **THEN** it is finite, nonzero, agrees with a direct Sun-Schwarzschild calculation under the force-sum tolerance, and the manifest marks all other relativistic terms disabled

### Requirement: Segmented finite burns and coupled mass
The system SHALL target with two maximum-thrust finite burns that share the scenario's thrust and specific impulse. For central-body-relative position `r` and velocity `v`, TNW SHALL mean `T = v/||v||`, `W = (r cross v)/||r cross v||`, and `N = W cross T`. A constant azimuth `a` and elevation `e` SHALL command components `(cos(e)cos(a), cos(e)sin(a), sin(e))` in ordered `(T,N,W)` axes rebuilt from the propagated state: Moon-relative for departure and Mars-relative for arrival. Degenerate or non-finite bases SHALL be rejected. Translation and mass SHALL be propagated together during each burn, coast mass SHALL remain constant, and ignition and cutoff SHALL be exact arc boundaries. During a burn, mass SHALL obey `dm/dt = -T/(g0 * Isp)` with `g0 = 9.80665 m/s^2`.

#### Scenario: Verify constant-thrust mass loss
- **WHEN** an isolated burn of duration `dt` is propagated from mass `m0`
- **THEN** its final mass agrees with `m0 - T*dt/(g0*Isp)` within `max(1e-8 kg, 1e-11 * consumed_mass)`

#### Scenario: Verify characteristic velocity
- **WHEN** an isolated thrust-only burn completes with masses `m0` and `m1`
- **THEN** its integrated characteristic velocity differs from `g0*Isp*ln(m0/m1)` by no more than `0.000001 m/s`

#### Scenario: Preserve mass during coast
- **WHEN** the coast arc starts and ends without thrust
- **THEN** the two boundary masses differ by no more than `0.00000001 kg`

#### Scenario: Join exact arc boundaries
- **WHEN** departure burn, coast, and arrival burn are assembled
- **THEN** adjacent boundary epochs agree within `0.000001 s`, positions within `0.001 m`, velocities within `0.000001 m/s`, and masses within `0.000000001 kg`

#### Scenario: Protect dry mass
- **WHEN** a requested or trial burn would consume reserved dry mass
- **THEN** that trial is rejected and is not retained as the best trajectory, no returned or retained state has mass below `dry_mass_kg`, and correction continues within its fixed bounds without treating that one rejected trial as a final classification

### Requirement: Bounded deterministic boundary-value targeting
The system SHALL use the two finite-burn TNW directions and durations as six controls to target the six-component configured Martian orbit state. Each azimuth SHALL be canonicalized to `[-pi,pi)` and each elevation SHALL remain in `[-pi/2,pi/2]`. Both burn durations SHALL be strictly positive and SHALL satisfy `departure_epoch + tau_d < arrival_epoch - tau_a`; equality and zero coast are invalid. The analytic two-burn terminal mass SHALL be at least dry mass. The departure direction seed SHALL be the normalized M2 departure excess-velocity vector projected into ignition Moon TNW; the arrival seed SHALL be the normalized negative M2 arrival excess-velocity vector projected into target-cutoff Mars TNW. Azimuth SHALL use `atan2(p_N,p_T)` and elevation `atan2(p_W,hypot(p_T,p_N))`. Sequential duration seeds SHALL use `v_e=g0*Isp`, `mdot=thrust/v_e`, `m_1=m_0*exp(-delta_v_d/v_e)`, `tau_d=(m_0-m_1)/mdot`, `m_2=m_1*exp(-delta_v_a/v_e)`, and `tau_a=(m_1-m_2)/mdot`.

The corrector SHALL require one safe complete seed evaluation before constructing a Jacobian. An unsafe seed SHALL return status `targeting-failed` with reason `no-safe-complete-trial` without correction. It SHALL scale residual components by `1000 m` and `0.01 m/s`; use forward differences `(1e-5 rad, 1e-5 rad, 1 s)` and trust scales `(0.25 rad, 0.25 rad, 600 s)` per burn; solve the dimensionless Jacobian with `numpy.linalg.lstsq` and `rcond=1e-12`; cap its infinity-norm trust update at one; and try damping factors `(1, 1/2, 1/4)` in that order. An analytically or physically rejected forward probe SHALL NOT be propagated to a fictitious cutoff or retried backward; its unavailable column SHALL stop correction as nonconvergence with the complete safe baseline. The first safe damping trial that closes or reduces scaled residual norm by at least the factor `1e-4*alpha` SHALL be accepted. Safe-command retention SHALL use the lexicographic key `(scaled residual norm, position norm, velocity norm, propellant mass, duration sum, control tuple)`; finite-difference probes SHALL never be retained as commands. Dry-mass, impact, and control/window violations SHALL be internal rejected-trial counters and SHALL NOT directly select a public status. A finite Jacobian with rank below six SHALL stop as nonconvergence; a non-finite propagated state, non-finite solve, or failed integration SHALL be fatal.

`control_attempts` SHALL increment before analytic validation of the seed and each correction probe or damping command. `propagation_evaluations` SHALL increment only when a control or frozen diagnostic starts its first native arc; an impact-terminated evaluation counts once and an analytically rejected control counts zero. `native_arc_propagations` SHALL increment before every native arc call, including an early-terminated call. A run SHALL attempt no more than eight correction iterations and 73 controls, and a converged run SHALL use no more than 76 propagation evaluations and 228 native arc propagations including its three diagnostics. It SHALL return `converged`, `mass-infeasible`, or `targeting-failed` rather than mislabel an unclosed, impacting, or below-dry-mass trajectory as executable. Status `mass-infeasible` with reason `preflight-m2-propellant-shortfall` SHALL mean that the verified ideal M2 mass budget already exceeds available propellant before targeting. A bounded correction with a safe complete trial SHALL return status `targeting-failed` and reason `nonconvergence` when it does not close; one with no safe complete trial SHALL use reason `no-safe-complete-trial` with null propagated-result fields and sorted rejection counts.

#### Scenario: Reproduce the exact correction seed
- **WHEN** the same finite nondegenerate candidate and boundary states are seeded twice
- **THEN** both six-control tuples are identical, their directions have unit norm, their signs follow positive departure and negative arrival excess velocity, and both durations match the sequential rocket-equation formulas within `0.000001 s`

#### Scenario: Bound correction work deterministically
- **WHEN** the corrector reaches every iteration and damping attempt without closure
- **THEN** it performs no more than eight Jacobians and 73 control attempts in the fixed probe/damping order, uses the declared acceptance and tie-break rules, reports each counter under its exact increment rule, and returns `targeting-failed` rather than starting another attempt

#### Scenario: Lose a forward-difference column
- **WHEN** a safe complete baseline exists but a forward probe is analytically rejected or terminates on dry mass or impact
- **THEN** no backward or fictitious-cutoff probe is evaluated, correction stops with status `targeting-failed` and reason `nonconvergence`, and the complete safe baseline remains the reported trajectory

#### Scenario: Converge the feasible M3 fixture
- **WHEN** candidate `d0001-t0035` from the checked-in feasible M3 scenario is refined with matching pinned resources
- **THEN** the result is `converged`, contains exactly two positive-duration burn records, respects dry mass and collision limits, and meets the `1000 m` and `0.01 m/s` target-closure bounds in no more than eight iterations and `300 s`

#### Scenario: Classify the preserved M2 reference
- **WHEN** candidate `d0001-t0035` from `examples/reference_mission.toml` is refined
- **THEN** the result is `mass-infeasible`, reports that the ideal M2 final mass is below `1000 kg`, and begins no finite-burn targeting propagation

#### Scenario: Detect an impact
- **WHEN** a trial crosses a required collision surface
- **THEN** that trial is rejected, its body-specific counter such as `rejected-impact:Mars` is incremented, and it is not retained as the best trajectory; if no complete safe trial exists when correction stops, the result has status `targeting-failed`, reason `no-safe-complete-trial`, and null terminal, burn, and actual-mass fields

#### Scenario: Exhaust the correction bound
- **WHEN** eight correction iterations finish without meeting the target-closure bounds and at least one safe finite trial exists
- **THEN** the result is `targeting-failed`, identifies nonconvergence, and reports the best safe terminal residual without claiming executable arrival

### Requirement: Numerical error budget and scientific checks
Each trajectory evaluation SHALL propagate a seven-component translation/mass state with the non-deprecated variable-step interface and exact-time termination. Nominal RKF78 SHALL use elementwise relative tolerance `1e-11`; absolute tolerances `1e-3 m` for each position component, `1e-6 m/s` for each velocity component, and `1e-9 kg` for mass; burn initial/minimum/maximum steps `1 s`, `1e-6 s`, and `30 s`; and coast steps `300 s`, `1e-3 s`, and `86400 s`. Tentatively closed commands SHALL be repropagated at identical fixed boundary epochs with RKDP87, elementwise relative tolerance `1e-13`, absolute tolerances `1e-5 m`, `1e-8 m/s`, and `1e-11 kg`, burn steps `0.25 s`, `1e-8 s`, and `7.5 s`, and coast steps `75 s`, `1e-5 s`, and `21600 s`. A minimum-step request, unsuccessful completion flag, or final-epoch mismatch SHALL be a fatal integration error with no partial result. Nominal and tighter results SHALL agree within `10 m` position, `0.0001 m/s` velocity, and `0.000001 kg` mass at every common boundary. Moon-400 sensitivity SHALL meet its separate bound and the finite Mars-60 tail SHALL be recorded before status `converged` is returned. Exceeding the integration or lunar-sensitivity bound SHALL raise `TrajectoryRefinementError` naming operation `scientific-validation` and return no normal result. These are numerical/model validation bounds, not real-world uncertainty. Full-trajectory energy or angular momentum conservation SHALL NOT be claimed for the time-dependent, forced, variable-mass model.

#### Scenario: Meet the integration convergence budget
- **WHEN** the frozen converged commands are run with the nominal and independently tighter integrators
- **THEN** every departure-ignition, departure-cutoff, arrival-ignition, and arrival-cutoff comparison satisfies all three numerical bounds

#### Scenario: Reject unvalidated nominal closure
- **WHEN** nominal commands meet the target closure but any tighter-integration or Moon-400 boundary difference exceeds its bound
- **THEN** refinement raises `TrajectoryRefinementError` for `scientific-validation`, emits no completed result, and does not label the trajectory `converged` or `targeting-failed`

#### Scenario: Verify an isolated conservative orbit
- **WHEN** a point-mass, no-thrust test body is propagated for ten complete orbits
- **THEN** relative drift in specific orbital energy and angular-momentum norm is no greater than `1e-11`

### Requirement: Complete immutable refinement result
`TrajectoryBoundaryState`, `FiniteBurnRecord`, `TrajectoryBoundaryDifference`, and `PhysicalTrajectoryResult` SHALL be immutable values that reject invalid, non-finite, negative-difference, inconsistent, or unitless construction. Every result SHALL contain the candidate identifier, status and termination reason, `SSB/J2000` and TDB conventions, force-model identifier, initial and target states, initial and dry masses, the verified ideal M2 final mass, required/available/shortfall propellant masses, correction iterations, control attempts, propagation evaluations, native arc propagations, sorted rejected-trial counts, and terminal position/velocity residual norms. A converged result SHALL use reason `target-closure-and-validation-passed`. A converged result or a complete-safe result with status `targeting-failed` and reason `nonconvergence` SHALL also contain its actual final and consumed masses, terminal state, and exactly two burn records. A pre-propagation mass-infeasible result or status `targeting-failed` with reason `no-safe-complete-trial` SHALL contain none of those propagated-result values. Only a converged result SHALL contain three four-entry `TrajectoryBoundaryDifference` tuples in fixed departure-ignition, departure-cutoff, arrival-ignition, arrival-cutoff order for nominal-versus-tighter integration, Moon-400 sensitivity, and Mars-60 sensitivity; all other statuses SHALL use empty tuples.

#### Scenario: Return a complete converged result
- **WHEN** physical refinement converges
- **THEN** the result uses reason `target-closure-and-validation-passed`, and every required state, burn, mass, residual, count, convention, and model field is finite, internally consistent, explicitly labeled by its public units/frame/time scale, and satisfies the status invariants

#### Scenario: Return an honest infeasible result
- **WHEN** the verified M2 seed budget exceeds the available propellant under the declared preflight policy
- **THEN** the immutable result contains status `mass-infeasible`, the ideal M2 final mass, required/available/shortfall propellant budget and reason, null actual final/consumed masses, null terminal state, zero burn records, and no fabricated propagated values

### Requirement: Fatal failure, deadline, and M3 fidelity boundary
A missing kernel or gravity file, hash or frame mismatch, uncovered epoch, invalid candidate, failed integration, non-finite state/solve, failed scientific-validation bound, or runtime deadline SHALL raise a chained `TrajectoryRefinementError` identifying the candidate and failed operation and SHALL return no fabricated replacement. The monotonic deadline SHALL cover candidate verification, targeting, propagation, and numerical checks. M3 SHALL remain nominal: tracking settings, maneuver dispersions, and random seed SHALL NOT change its commands or scientific result.

#### Scenario: Lose a required scientific resource
- **WHEN** SPICE coverage, a required harmonic coefficient file, its expected hash, or its associated rotation frame is unavailable or inconsistent
- **THEN** refinement raises `TrajectoryRefinementError` with the affected resource and emits no point-mass, circular-orbit, stale-data, or reduced-degree fallback

#### Scenario: Reach the runtime deadline
- **WHEN** the monotonic runtime limit is reached before all required classification and checks complete
- **THEN** refinement raises `TrajectoryRefinementError` containing the configured seconds plus control-attempt, propagation-evaluation, and native-arc counts and returns no result

#### Scenario: Change a deferred input
- **WHEN** two otherwise identical nominal M3 inputs differ only in tracking settings, maneuver-error sigmas, or random seed
- **THEN** their status, commands, boundary epochs, scientific values, and model diagnostics are identical

### Requirement: Qualification of feasibility and shared numerical state
The system SHALL describe `mass-infeasible` with reason `preflight-m2-propellant-shortfall` as rejection by the selected M2 seed-budget policy, not proof that no physical transfer exists. A scenario passing that filter SHALL NOT be described as a demonstrated finite-burn solution until the targeting gate passes. The implementation SHALL qualify interpolated ephemerides independently of integrator agreement, validate the combined force assembly, and reestablish the declared PPN values before every native arc. The single cooperative deadline SHALL include M2 verification, resource construction/hashing, and manifest construction; it SHALL NOT restart between stages.

#### Scenario: Change only dry mass in the provisional fixture
- **WHEN** reference dry mass changes from 1000 kg to 500 kg and all other scenario inputs remain fixed
- **THEN** candidate `d0001-t0035` retains its geometry, epochs, excess velocities, delta-v, and ideal masses, its M2 `mass_feasible` flag changes from false to true, and no finite-burn convergence is inferred from that flag

#### Scenario: Qualify interpolation before targeting
- **WHEN** the time-limited ephemeris environment is prepared for the prerequisite targeting spike
- **THEN** checked-in evidence reports per-body maximum position and velocity differences against direct SPICE at deterministic off-grid and interval-edge epochs and against a denser table, and an explicit measured error allocation within the existing endpoint budgets is strictly validated before the spike proceeds

Before targeting, the sampled ephemeris input-state allocation SHALL be
`0.025 m` in Euclidean position and `0.0000025 m/s` in Euclidean velocity for
both tables against SPICE and for their mutual difference. This allocation
does not bound unsampled epochs or propagated spacecraft error and does not
replace the existing closure, integration, or model-sensitivity gates.

#### Scenario: Reproduce the ephemeris qualification fixture
- **WHEN** candidate `d0001-t0035` from `examples/m3_feasible_mission.toml` is checked using the default six-point Lagrange ephemerides with 300 s and 150 s table spacing, no aberration, SSB origin and J2000 orientation
- **THEN** all eight bodies satisfy the input-state allocation at the 38 TDB epochs recorded in `tests/data/m3_ephemeris_qualification.json`, including the two boundary epochs, four near-edge points, and 32 off-grid interior points; each runtime safe interval contains the complete candidate interval

#### Scenario: Reject insufficient ephemeris coverage
- **WHEN** validation requests an interval extending 86400 s beyond either end of the configured candidate interval
- **THEN** it fails with a coverage error before attempting an out-of-range state query, without extrapolation or substitute states

#### Scenario: Reestablish PPN at an arc boundary
- **WHEN** native global PPN values have been changed before a new Ariadna arc is constructed
- **THEN** arc setup restores and reads back beta=gamma=1 before constructing acceleration models, and the independent fixed-state force check meets the existing force-sum tolerance

#### Scenario: Classify intentional safety termination
- **WHEN** an arc terminates early on dry mass or a collision surface, including a test that enters and exits a guard between output epochs
- **THEN** it is counted as a rejected trial with the corresponding safety reason, no unsafe history is retained, and its early epoch is not misclassified as an unexpected final-epoch integration failure

#### Scenario: Preserve the operation deadline
- **WHEN** M2 verification or resource setup consumes part of the runtime budget
- **THEN** targeting, diagnostics, and manifest construction receive only the remaining time, and expiration after any native call produces a deadline error with no completed result; native-call wall-clock overrun is not represented as a hard real-time guarantee
