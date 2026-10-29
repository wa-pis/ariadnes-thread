## ADDED Requirements

### Requirement: Mission-first demonstration readiness after local research

R1 SHALL prioritize one reproducible research demonstrator with an independently
checked calculation and exportable result, following ADR 0117. It SHALL preserve
the long-term platform vision, historical evidence and all strict M3 gates.

#### Scenario: Stop local targeting continuation without erasing evidence

- **WHEN** next work is selected after the unclosed D17.3 study
- **THEN** the active priority SHALL be R1 readiness, not an automatic D18, second D17 run, new seed, chart extension or larger budget
- **AND** all historical JSON, targets, thresholds, model identities and results SHALL remain unchanged; an unclosed experiment SHALL NOT be relabelled successful or proof of global infeasibility
- **AND** any later local targeting study SHALL require an explicitly accepted problem, user-visible purpose, physical constraints and execution budget; this planning record SHALL authorize zero native launches

#### Scenario: Declare a positive reference at its actual fidelity

- **WHEN** R1.1 specifies the first demonstration problem before selecting its fixture
- **THEN** it SHALL declare the user-visible outcome, model/version and omissions, explicit physical inputs/dates, initial/final conditions, and rationale for every constrained state component and epoch
- **AND** it SHALL distinguish mission boundary requirements from reproduction of an ideal impulsive endpoint, and justify the connection to the outer transfer before a finite-burn lunar departure is used as a mission boundary
- **AND** it SHALL fix a finite numerical reserve strictly greater than zero in kg, the maneuvers/uncertainties covered by that allowance, numerical acceptance tolerances and verification budget before selection; a qualifying reference SHALL satisfy final_mass_kg >= dry_mass_kg + reserve_kg under the declared accounting
- **AND** an M2-only reference SHALL be labelled ideal-model feasible, NOT finite-burn or full-mission feasible; changing a fixture SHALL create an explicit new scenario, not mutate the retained references or silently alter spacecraft defaults
- **AND** missing inputs/reserve coverage or failed checks SHALL leave the reference unverified; simply changing dry mass, lowering a tolerance, optimizer success or lower residual SHALL NOT qualify it

#### Scenario: Check a small physical benchmark independently before expanding optimization

- **WHEN** R1.2 verifies a declared calculation before further optimizer complexity or end-to-end acceptance
- **THEN** its contract SHALL name an independently implemented analytic oracle or external engine, versions/resources, frozen initial state/command/epochs, identical force and mass models, numeric position/velocity/mass/time tolerances in SI and execution limits before any run
- **AND** it SHALL retain raw aligned states, differences, provenance and pass/fail/unavailable outcomes; every declared difference SHALL be within its predeclared tolerance to pass
- **AND** a finite-burn claim SHALL require a benchmark with finite thrust and non-negligible gravity; two profiles sharing the same dynamics adapter or independently reoptimized commands SHALL NOT count as independent physical validation
- **AND** unavailable tooling or a failed comparison SHALL stop the gate unverified or failed without automatic retries, increased budgets or fabricated reference data; agreement SHALL NOT establish mission feasibility, absolute accuracy or continuous safety
- **AND** this small benchmark MAY precede M6, but SHALL NOT be reported as M6 full-mission GMAT/Monte Carlo completion or a waiver of strict M3

#### Scenario: Specify traceable output and a narrow exchange profile before coding

- **WHEN** R1.3 prepares the demonstration's result and OEM exchange specification
- **THEN** it SHALL bind output to normalized actual inputs, model/fidelity, epochs/units/origin/orientation, physical and numerical status, reserve accounting and resource/source provenance
- **AND** it SHALL select the exact OEM edition/corrections, encoding, supported metadata/frames/time scales, conversion tolerances, independent reader and positive/rejection fixtures before exporter implementation
- **AND** exported epochs and physical states SHALL round-trip through that reader within the declared tolerances after explicit unit/frame/time conversion; successful parsing alone SHALL NOT qualify physics or interchange
- **AND** unsupported semantics SHALL fail clearly; stale UI/export results SHALL be invalidated after input changes or failed calculations, and absent covariance/safety/measurement data SHALL NOT become fabricated zeros or success flags

#### Scenario: Complete a usable path without closing the engineering milestone

- **WHEN** R1.4 is separately implemented after the readiness/benchmark/profile gates pass
- **THEN** one new positive reference SHALL traverse input, calculation, display, export and independent decoding, with all declared numerical/reserve checks and negative/stale-result tests passing
- **AND** focused tests, the full pinned regression suite, strict OpenSpec validation and immutable legacy checks SHALL pass before implementation completion
- **AND** the demonstration SHALL retain its declared research/M2 limitations; more private experiment records, passing component-test counts or format compatibility alone SHALL NOT constitute completion
- **AND** strict M3/task 3.9 SHALL remain open until their original gates pass; M4 estimation, M5 corrections, M6 mission validation, ML, generic backend frameworks and automation restart SHALL remain outside R1

### Requirement: Controlled M2 reference and historical evidence readiness

R1 SHALL keep the proposed ADR 0118 reference, empirical mission comparisons and
same-force independent numerical verification as separate claims. The proposal
SHALL NOT authorize execution or change public scientific behavior by itself.

#### Scenario: Accept explicit inputs and reserve before selecting the new reference

- **WHEN** the ADR 0118 R1.1 contract is accepted before a separately instructed verification
- **THEN** the new `r1-m2-reserve-reference` SHALL use model `sun-centered-zero-revolution-patched-conic-v1` and all explicit values from the unchanged hypothetical template `examples/m3_feasible_mission.toml`, SHA256 `2c3b2a140d6e6ea00c2173caab5c51b1c4be87a112d2dec28a40cd1e2a0a9b42`, not a GRAIL/MSL spacecraft or a relabelled D17 result
- **AND** the 2031 UTC window, 180–320 day flight range, 2000/500 kg initial/dry masses, 450 s Isp and all other supplied fields SHALL remain explicit; the model's ignored orientation/thrust/tracking/error fields and body-centre/instantaneous-burn approximations SHALL be disclosed
- **AND** before candidate selection the reserve SHALL be 50 kg, allocated only to aggregate additional ideal delta-v <=100 m/s at constant 450 s Isp, mass <=2000 kg and no staging/mass additions; `2000*(1-exp(-100/(9.80665*450))) < 50 kg` SHALL be independently checked, without claiming uncertainty coverage or scheduling a TCM
- **AND** only a candidate with final_mass_kg >=550.0 and independently recomputed ideal mass within 1e-9 kg SHALL qualify; the returned Pareto front SHALL be filtered by reserve and selected by `(total_delta_v_m_s, flight_time_s, departure_epoch_tdb_s, candidate_id)`, then frozen for replay
- **AND** the absence of a qualifying candidate SHALL leave R1.1 failed/unverified without changing the template, reserve, dates or historical evidence

#### Scenario: Verify reproducibility within the declared M2 budget

- **WHEN** the accepted R1.1 contract is separately executed
- **THEN** it SHALL permit exactly two complete planner calls and two 121-state sampler calls, at most 3960 Lambert attempts and 242 two-body samples, under one cooperative 300 s wall-clock acceptance budget including scientific/resource setup
- **AND** checks before/after every top-level call SHALL prevent further calls after exhaustion; a non-preemptible native-call overrun SHALL be reported with actual time as failure, not bounded success or permission to retry
- **AND** inputs/source/resources/GMs/versions and selection SHALL match, scientific payloads SHALL be identical apart from separately recorded timing, and finite SI/SSB/J2000 samples at TDB epochs SHALL pass existing M2 endpoint checks of 100 m and 0.001 m/s
- **AND** a reserve deficit SHALL NOT be admitted by numerical tolerance; resource mismatch, missing positive reference, error or overrun SHALL stop further calls, leave R1.1 open and SHALL NOT complete R1.2 or qualify finite burns/M3

#### Scenario: Admit a historical arc only with inspected coverage and event evidence

- **WHEN** an MSL or GRAIL historical trajectory is proposed for empirical comparison
- **THEN** readiness SHALL record exact product URLs/versions/hashes, inspected binary body/centre/frame/coverage and time scale, companion kernels/load order, a maneuver-free interval supported by event data, force omissions, epochs, tolerances and execution limits before propagation
- **AND** a directory entry, filename or label alone SHALL NOT certify continuous coverage, absence of thrust or full dynamics; conflicting generic/product-specific metadata SHALL be reconciled or leave readiness unverified
- **AND** missing reconstruction uncertainty SHALL remain unavailable rather than zero; historical residuals SHALL be labelled empirical model discrepancy, not same-force numerical error, reserve feasibility or mission qualification
- **AND** R1.2 SHALL still require its independently accepted frozen same-force oracle/engine contract; data discovery SHALL NOT start a replay, replace the Moon-to-Mars demonstration or bypass R1.1

### Requirement: Smooth additional steering freedom after the bound-limited study

D17 SHALL follow ADR 0114 as a separate private experiment, preserving D14/D15/D16
and all historical evidence. It SHALL change only the steering chart/control count
and explicitly separate compute ceiling, not the physical target, fuel, thrust,
force model, timing domain, native profiles or qualification thresholds.

#### Scenario: Diagnose saved response without inventing final stationarity

- **WHEN** D17.1 evaluates retained D16.3 evidence
- **THEN** it SHALL bind 0113 SHA256 417f4a33e6407a37e9a41caff29330557f39d7a3bbfc34e9b908cc1d5589cb89 and distinguish best objective 262 from last accepted/measured parent 249
- **AND** it SHALL independently check the active duration/reserve bound, saved-gradient normalization, five-free-column and bounded linear residual minima against exhaustive face/KKT oracles, without applying those commands or propagating a spacecraft
- **AND** conditional linear minima SHALL NOT become nonlinear impossibility bounds, returned SciPy stationarity or a Jacobian at unmeasured ID 262

#### Scenario: Add smooth curvature inside the unchanged chart envelope

- **WHEN** D17 constructs an eight-control command x=(delta_ti,tau,p0,q0,pc,qc,p1,q1)
- **THEN** for s=t/tau it SHALL use u(s)=(1-s)^2*u0+2*s*(1-s)*uc+s^2*u1 and normalize d0+u_p*e1+u_q*e2 in the original inertial basis; uc SHALL be labelled a Bezier control point, NOT a midpoint-time direction
- **AND** all six slope coefficients SHALL remain in [-1,1], so the convex-hull property bounds the complete physical chart for 0<=s<=1; norm of its unnormalized direction SHALL be >=1
- **AND** uc=(u0+u1)/2 SHALL embed the old linear chart; the same polynomial SHALL extend native trial stages outside the physical interval without clamping, guidance kinks or a new midpoint arc
- **AND** the sampled/state/mass guards SHALL remain authoritative; rate bound 2*max(norm(uc-u0),norm(u1-uc))/tau SHALL be diagnostic, not hardware qualification

#### Scenario: Bind a reproducible interior seed with separate model replay gates

- **WHEN** the separately verified D17 runner starts
- **THEN** it SHALL bind pinned 0104/0107/0110/0113 inputs, candidate d0001-t0035 and its original first free-phase branch, domain/resources/commands/target, explicitly selecting accepted 0113 proposal 158 only
- **AND** a fresh old two-node replay SHALL agree with retained ID 158 within 1 m / 0.001 m/s / 1e-6 kg, then a fresh embedded Bezier seed SHALL agree within the same limits against BOTH that replay and retained ID 158, before derivative work
- **AND** model ID SHALL be local-moon-point-mass-bezier-burn-v1 and algorithm ID bound-aware-bezier-trf-v1, with the old reference model separately identified; the old replay SHALL NOT qualify or become a new-model objective
- **AND** only the embedded seed residual SHALL supply the single exact initial objective cache; its controls SHALL equal the eight values frozen in ADR 0114, with y0=0 unchanged by SciPy; mismatch SHALL stop without clipping, alternate start, epsilon repair or silent cache reuse
- **AND** target six-state and tm=979002340.6346419 TDB s, Moon/J2000/SI, 1000 N / 450 s, 2000/500 kg masses, original reserve/window/ignition/duration bounds and >=1 s full-box coast SHALL remain unchanged; final mass SHALL vary analytically with duration, not become a seventh target

#### Scenario: Correct an underdetermined six-state residual with bounded probes

- **WHEN** the Bezier seed replay passes but the target is unclosed
- **THEN** D17 SHALL use pinned SciPy 1.17.1 TRF/exact/linear, x_scale=1, ftol=xtol=gtol=1e-10, max_nfev=40, verbose=0, workers=None; x=x_seed+T*y with T=(300 s,300 s,0.1,0.1,0.1,0.1,0.1,0.1) and the unchanged six 10 m / 0.01 m/s residual scales
- **AND** its callable 6x8 Jacobian SHALL use fixed h=(1 s,1 s,0.001,0.001,0.001,0.001,0.001,0.001), complete central pairs first, else forward or backward second-order pairs with the formulas of ADR 0111 and column scaling by T
- **AND** all sixteen commands SHALL be preflighted before any probe launch; unavailable pairs SHALL stop derivative-domain-unresolved without smaller h, penalty residual or fallback
- **AND** SVD SHALL retain six singular values and rcond=1e-10 full/free-column row-rank diagnostics; controls/gradients/active masks SHALL have eight components, with no rank-eight requirement, regularization residual, dynamic scale or changed physical merit
- **AND** face-free columns SHALL be identified by strict physical comparisons L[j]<x[j]<U[j] with recorded margins at the matrix parent, not an inferred SciPy active-mask or a full feasible-tangent-cone claim; eight-control and six-residual shape validation SHALL remain distinct

#### Scenario: Qualify only unchanged target closure and frozen tighter agreement

- **WHEN** an eligible Bezier seed or non-probe objective first satisfies norm(dr)<=10 m AND norm(dv)<=0.01 m/s
- **THEN** optimizer control flow SHALL stop before another Jacobian and exactly one fresh tighter burn/coast of that frozen eight-control command SHALL follow
- **AND** local-qualified SHALL require both profiles to close, endpoint agreement<=1 m / 0.001 m/s / 1e-6 kg, analytic cutoff-mass error<=1e-6 kg and exact coast-mass preservation
- **AND** a tighter failure/disagreement SHALL stop unqualified with no resumed correction; old-reference replays, probes, rank, lower score or optimizer success alone SHALL NOT qualify, and unclosed stationarity/stagnation SHALL retain D16's honest labels

#### Scenario: Bound the new study without extending the previous experiment

- **WHEN** D17 prepares or attempts any native work
- **THEN** one shared 300-second cooperative clock SHALL include binding, two nominal replay evaluations, <=40 objective requests including one initial cache hit, <=40 sixteen-probe Jacobian batches, and at most one reserved tighter evaluation
- **AND** own ceilings SHALL be 681 nominal evaluations (2+39+40*16), 682 total evaluations and 1364 native launches, with 1362 nominal launches and two reserved for the tighter check; attempted failures count before entry, and a complete sixteen-probe batch SHALL fit before its first launch
- **AND** all domain/nonfinite/native/guard/limit failures SHALL stop with finite partial evidence and no retry, substituted dynamics or continuation from an incomplete arc; completed cutoff SHALL survive coast failure
- **AND** evidence SHALL retain separate reference/current source provenance, roles/cache/parents/accepted IDs/best objective, eight controls/units, target/epoch/mass/endpoints, 6x8 matrices/stencils/SVD, bound-margin/gradient associations and independent counters; absent solver status/active-mask after interruption SHALL stay unavailable, not be inferred from an earlier matrix
- **AND** verified D17.2 implementation SHALL precede a separately user-authorized single D17.3 native study; no automatic second study, target/fuel/domain relaxation, new force, public API/UI, automation restart or strict M3 qualification SHALL follow

### Requirement: Bound-aware local targeting follow-up

D16 SHALL follow ADR 0111 as a separate private bounded experiment, preserving
D14/D15 behavior and their immutable evidence. It SHALL use the existing six
controls, two-node chart, forces, physical domain and fixed target state/epoch;
only correction orchestration and its explicitly separate budget SHALL change.
SciPy 1.17.1 SHALL be explicitly pinned with Conda before implementation completion.

#### Scenario: Bind and replay the explicitly selected warm start

- **WHEN** D16 is separately invoked after verified implementation
- **THEN** it SHALL bind the pinned 0104/0107 references and 0110 SHA256 678287cc7aee2b3d83e89c9fbff1113a96d24c5b8960f047aeadb82d049c4274, reconstruct their commands/target/domain/resources, and start only from accepted proposal 52
- **AND** a fresh nominal seed replay SHALL agree with that retained endpoint within 1 m / 0.001 m/s / 1e-6 kg before derivative work; target six-state and tm=979002340.6346419 TDB s, Moon-relative J2000/SI, thrust/Isp, all mass/reserve/window bounds and native profiles SHALL remain fixed
- **AND** the complete timing box SHALL imply at least 1 s coast, not just its seed; an unsupported coupled constraint or changed input SHALL stop without clipping, alternate seed or hidden repair

#### Scenario: Select bounded corrections rather than cap an unconstrained direction

- **WHEN** replay passes without physical closure
- **THEN** D16 SHALL use SciPy least_squares with method=trf, tr_solver=exact, loss=linear, x_scale=1, ftol=xtol=gtol=1e-10, max_nfev=40 and serial calls, in coordinates x=x_seed+T*y with y0=0 and T=(300 s,300 s,0.1,0.1,0.1,0.1)
- **AND** physical bounds SHALL be transformed to those coordinates, residuals SHALL retain the 10 m / 0.01 m/s scales, and the initial request SHALL reconstruct the replayed seed exactly; no uniform D15 cap, dynamic scale, penalty residual, target refit, method switch or fallback start SHALL be introduced

#### Scenario: Differentiate inside the admissible domain

- **WHEN** a callable Jacobian is requested at a completed objective command
- **THEN** each coordinate SHALL use fixed physical h=(1 s,1 s,0.001,0.001,0.001,0.001), preferring a feasible central pair, otherwise a feasible forward two-point pair, otherwise a feasible backward pair, with the second-order formulas of ADR 0111
- **AND** all twelve probes SHALL pass domain preflight before any native launch; an unavailable complete pair SHALL stop without changing h, and center residual reuse SHALL launch no new arc
- **AND** columns SHALL be scaled by T into dr/dy; all stencils, matrices and finite SVD rank/conditioning diagnostics SHALL be retained without treating local rank or a closed probe as physical success

#### Scenario: Qualify only the unchanged physical target

- **WHEN** replay or a completed non-probe objective first satisfies position-norm residual<=10 m AND velocity-norm residual<=0.01 m/s
- **THEN** optimizer control flow SHALL stop before another Jacobian and exactly one fresh tighter repeat of that frozen command SHALL follow
- **AND** local-qualified SHALL require both profiles to close, agreement<=1 m / 0.001 m/s / 1e-6 kg, analytic cutoff-mass error<=1e-6 kg and exact coast-mass preservation; tighter failure/disagreement SHALL stop unqualified without resuming correction
- **AND** optimizer gtol success without closure SHALL be stationary-unclosed, ftol/xtol success without closure SHALL be stagnated-unclosed, and neither SHALL be labelled mission feasibility or proof of nonlinear impossibility

#### Scenario: Bound every call and preserve failure evidence

- **WHEN** D16 prepares, evaluates objectives/probes or attempts native launches
- **THEN** one 300-second cooperative clock SHALL cover binding/setup and all work; counters SHALL include one replay, at most 40 objective requests including its single exact initial cache hit, and at most 20 complete twelve-probe Jacobians
- **AND** the independent ceiling SHALL be 280 nominal evaluations plus at most one reserved tighter evaluation, 281 total evaluations / 562 attempted native launches including failures; SciPy nfev alone SHALL NOT stand in for probe/native counts
- **AND** limits SHALL stop as budget-exhausted before excess work or an unaffordable batch; binding/domain/nonfinite/native/guard failure SHALL stop the entire study without substituted residual, retry or continuation after an incomplete arc
- **AND** new finite JSON and ADR SHALL retain all commands/roles/cache/accepted-iterate identities, residuals, masses/epochs, settings, Jacobians, active bounds/status, own counters and reference/source/resource/runtime provenance even on failure, distinguishing best objectives from probes and unavailable agreement
- **AND** implementation verification SHALL precede a separately user-authorized single native study; no automatic second study, relaxed fuel/target/time, new steering node, public API/UI, automation restart or strict M3 qualification SHALL follow

### Requirement: Bounded local steering and ignition targeting

D15 SHALL follow ADR 0108 as a private local experiment, preserving D14 behavior
and immutable 0104/0107 evidence. It SHALL vary only ignition shift, burn duration
and two dimensionless direction slopes at each of two steering nodes, with fixed
thrust/Isp, circular parking history and Moon-point-mass gravity. Target position,
velocity and absolute TDB epoch SHALL remain fixed; final mass SHALL be computed
from duration, not constrained to the D14 target mass.

#### Scenario: Construct an admissible steered command

- **WHEN** the pinned references and initial command pass validation
- **THEN** D15 SHALL use the fixed orthonormal inertial chart and normalized interpolated direction of ADR 0108, with zero slopes reproducing D14, abs(slopes)<=1 and norm(chart vector)>=1
- **AND** ignition shift SHALL satisfy abs(delta_ti)<=P/4 and the original launch window, duration SHALL satisfy the specified 0.5*tau_D14 to mass-reserve-capped 1.5*tau_D14 interval, cutoff SHALL precede the fixed match epoch by at least 1 s, and dry-mass/provisional-reserve checks SHALL pass before native work
- **AND** the circular initial state SHALL be rotated to actual ignition and steering-rate evidence SHALL NOT be labelled hardware qualification

#### Scenario: Perform only the prescribed local correction

- **WHEN** nominal baseline replay agrees with 0107 within 1 m / 0.001 m/s / 1e-6 kg and the target is not closed
- **THEN** D15 SHALL perform at most four iterations with twelve central probes per iteration, fixed h=(1 s,1 s,0.001,0.001,0.001,0.001), residual scaling 10 m / 0.01 m/s and trust scales T=(300 s,300 s,0.1,0.1,0.1,0.1)
- **AND** the scaled least-squares solve SHALL require rank six with rcond=1e-10 and condition number<=1e10, cap the normalized step once to infinity norm<=1 and require a strictly decreasing finite prediction
- **AND** alpha=1,1/2,1/4,1/8 trials SHALL be relative to the same iterate, accepting the first closed trial or score_trial<=(1-1e-4*alpha)*score_current, without clipping, new scales, fallback solve or native retry

#### Scenario: Qualify closure without changing the target

- **WHEN** the baseline or an accepted nominal iterate first achieves position-norm residual<=10 m AND velocity-norm residual<=0.01 m/s at the fixed target epoch
- **THEN** exactly one fresh tighter repeat of that command SHALL run, and local success SHALL require both profiles to close plus agreement<=1 m / 0.001 m/s / 1e-6 kg, analytic cutoff-mass error<=1e-6 kg and unchanged coast mass
- **AND** tighter disagreement or failure SHALL stop unqualified without resuming iteration; iteration exhaustion without closure SHALL report not-converged and SHALL NOT launch a tighter repeat

#### Scenario: Respect bounds, failures and total work

- **WHEN** binding/replay, central-probe feasibility, rank, finite prediction, step acceptance, sampled guards, native integration or the deadline fails
- **THEN** the study SHALL stop with the applicable unresolved/failure status; analytically infeasible line-search proposals alone SHALL be recorded/skipped within their prescribed slots, without native launch
- **AND** the schedule SHALL remain within 65 nominal proposals, 66 total evaluations and 132 native launches under one 300-second clock including setup, counting attempted failed launches and retaining command/residual/matrix/step/provenance evidence with unavailable fields explicit
- **AND** no alternate seed/branch, automatic follow-up, production-optimizer expansion, strict M3 qualification or automation restart SHALL occur

### Requirement: Bounded local finite-burn departure diagnostic

The system SHALL implement D14 only as the private local diagnostic defined in
ADR 0105, explicitly binding the immutable 0104 reference and its first free-phase
branch. It SHALL use Moon-relative J2000 SI states, TDB seconds from J2000,
constant inertial vector-impulse direction, centered rocket-equation duration,
analytically rotated circular ignition state and lunar point gravity with coupled
mass. It SHALL label omitted perturbations and SHALL NOT claim a full-force or
flight-qualified result. Actual ignition SHALL satisfy retained launch bounds.

#### Scenario: Fixed finite-radius state and time

- **WHEN** the bound reference passes validation
- **THEN** the target SHALL be the outgoing analytic hyperbola at explicitly recorded Rmatch=10*rp and its analytic time of flight, with independent state checks at the D13 invariant tolerances and time-of-flight agreement <=0.001 s
- **AND** cutoff SHALL precede the target epoch, and closure SHALL require position-norm residual <=10 m and velocity-norm residual <=0.01 m/s at that exact epoch, without changing the epoch or substituting asymptotic velocity

#### Scenario: Completed miss is distinct from integration agreement

- **WHEN** verified D14 implementation executes one nominal burn/coast command without a guard failure
- **THEN** one frozen tighter burn/coast repeat SHALL follow even if nominal closure fails, within four native launches and one 300-second deadline including setup
- **AND** agreement SHALL require endpoint differences <=1 m, <=0.001 m/s and <=1e-6 kg, with analytic cutoff-mass error <=1e-6 kg for each profile
- **AND** evidence SHALL report closure and agreement separately, including failed gates, explicit settings, hashes, raw residuals and model omissions, without optimizer, command tuning or retry

#### Scenario: Invalid input or propagation failure

- **WHEN** reference binding, physical/domain inputs, launch window, provisional mass reserve, impact/dry-mass guards, finite states, integration or shared budget fails
- **THEN** execution SHALL stop with a contextual reason and skipped/unavailable remaining evidence, never a substituted successful result or a retry
- **AND** D13 evidence SHALL remain immutable, strict M3 gates SHALL remain open and automation SHALL remain paused

### Requirement: Geometrically consistent local lunar departure seed
D13 SHALL construct an explicitly labelled impulsive two-body lunar departure
reference, not an executable finite-burn or qualified interplanetary trajectory.

#### Scenario: Enforce explicit geometry and phase policy
- **WHEN** given finite SI lunar mu, circular parking radius/oriented plane, nonzero outgoing Moon-relative J2000 excess velocity, TDB epoch and mandatory fixed/free phase policy
- **THEN** D13 uses e=1+rp*norm(v_inf)^2/mu and requires dot(u,v_inf/norm(v_inf))=-1/e at periapsis; fixed phase must satisfy this equality within 1e-12, while free phase enumerates the two nondegenerate plane solutions in normalized phase order without hidden state/epoch/plane changes or automatic selection
- **AND** with R the norm of the asymptote's projection into the parking plane, R<1/e-1e-12 is infeasible and abs(R-1/e)<=1e-12 is near-degenerate/unresolved; unsupported eccentric parking, nonfinite/zero inputs and nonrepresentable hyperbolic geometry fail explicitly rather than inventing a branch

#### Scenario: Build and independently verify a vector impulse
- **WHEN** a branch is geometrically admissible
- **THEN** D13 computes t=(s+u/e)/sqrt(1-1/e^2), v_h=sqrt(norm(v_inf)^2+2*mu/rp)*t and delta_v=v_h-v_parking at identical position/epoch, retaining all three SI vectors, phase, eccentricity, angular momentum and energy with units/frame/time metadata
- **AND** an independent angular-momentum/eccentricity-vector reconstruction matches the outgoing asymptote and velocity within 0.000001 m/s, position within 0.001 m and radial periapsis velocity within 0.000001 m/s; energy error is <=1e-10*max(mu/rp,norm(v_inf)^2/2) m^2/s^2, or the branch fails without tolerance relaxation

#### Scenario: Recompute mass without claiming finite-burn feasibility
- **WHEN** translating the branch's vector impulse into ideal propellant/duration estimates
- **THEN** D13 uses norm(delta_v), actual mass, thrust and Isp; any old arrival impulse is explicitly provisional and applied sequentially to the new departure mass, never reusing old arrival duration/final mass or M2 feasibility labels
- **AND** virtual impulse time is not silently treated as ignition; finite-burn timing/guidance and finite-radius state/epoch matching require a later specified contract, as do outer Lambert matching and Mars capture; no native mission run, automatic optimizer, UI change, public scenario mutation or strict M3 qualification occurs

### Requirement: Bounded damping of the retained central correction
D12 SHALL evaluate only alpha=0.5 and conditionally alpha=0.25 of the retained
D11 correction from the original seed, without a new solve, derivative probes,
chained updates or changes to D4–D11 scientific contracts.

#### Scenario: Bind central correction evidence and replay the baseline
- **WHEN** D12 receives pinned 0079 and 0098 with SHA256 17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235 and b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057
- **THEN** it verifies scenario/candidate/seed/target/runtime/resources/settings, historical 0079/0095 identities, completed nominal baseline and alpha=1 trial, not-improving outcome without selection/tighter, and finite rank-six matrix/correction with algebraically consistent cap, trust units and prediction; raw endpoint residuals and recorded improvement are reconstructed without a solver or native probes
- **AND** a fresh nominal baseline matches both retained baselines at four identical epochs/frames within 10 m, 0.0001 m/s and 0.000001 kg; mismatch stops before fractions, and both existing 1000 m and 0.01 m/s closure gates stop as baseline-closed with both fractions skipped

#### Scenario: Test independent fractions and stop at the first improvement
- **WHEN** the baseline replay passes without closure
- **THEN** D12 evaluates seed+0.5*retained_step and only after its completed non-improvement evaluates seed+0.25*retained_step, independently from the seed through existing canonical angle/window/mass gates, with unchanged target/settings and fresh environments
- **AND** empirical improvement requires S_trial <= S_baseline*(1-0.0001*alpha) or both closure gates, with actual thresholds, physical misses, raw/scaled residuals and score ratios recorded; any linear prediction is diagnostic only and cannot select a command
- **AND** the first improvement selects exactly one frozen canonical-command tighter evaluation with identical initial/target states and four-boundary 10 m, 0.0001 m/s and 0.000001 kg agreement gates; remaining fractions are skipped, and disagreement or failure preserves nominal improvement without fallback

#### Scenario: Bound one invocation and retain honest evidence
- **WHEN** D12 completes or a replay/analytic/event/native/nonfinite/deadline failure occurs
- **THEN** one shared cooperative 300-second clock permits at most three nominal control attempts counted before analytic validation, four evaluations and twelve native launches, with no extra control counted for the frozen tighter evaluation
- **AND** finite exclusive-output JSON retains reference/current/imported source provenance, retained matrix/step, exact fraction commands, completed diagnostics, skipped/unavailable reasons, attempted/completed counters and separate wall time, without unfinished endpoints
- **AND** no retry, additional fraction, derivative probe, new solve or budget increase occurs; continuous_safety_verified remains false and improvement, closure and numerical agreement are separate from strict M3 qualification; no further experiment starts automatically

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
