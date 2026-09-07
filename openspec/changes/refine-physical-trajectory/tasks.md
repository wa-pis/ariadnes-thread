## 1. Public contracts and candidate handoff

- [x] 1.1 Add frozen, slotted `TrajectoryBoundaryState`, `FiniteBurnRecord`, `TrajectoryBoundaryDifference`, and `PhysicalTrajectoryResult` records with status-dependent field/count/diagnostic invariants, unit/frame/time labels, finite-value validation, and serialization; verify constructor and round-trip tests cover valid, invalid, infeasible, failed, and converged forms.
- [x] 1.2 Add `TrajectoryRefinementError` and lazy public package exports for the M3 API without importing TudatPy or loading kernels at import time; verify import-isolation and chained-error tests pass.
- [x] 1.3 Implement exact M2 Pareto-candidate reproduction and handoff comparison for identifiers, epochs, vectors, burns, and masses; verify matching candidates pass within the specified tolerances and malformed, missing, or altered candidates fail before physical propagation.

## 2. Physical boundary states and resources

- [x] 2.1 Convert the configured Moon and Mars osculating elements into body-relative J2000 Cartesian states at the candidate burn-boundary epochs using each harmonic field's gravitational parameter, then add SSB ephemeris states; verify direct-conversion, radius, non-body-centre, and circular argument-of-latitude equivalence tests meet the specified tolerances.
- [x] 2.2 Build the time-limited Tudat environment with the literal production model identifier, pinned SPICE resources, Moon `gggrx1200` 200x200 in `IAU_Moon`, Mars `jgmro120d` 120x120 in `IAU_Mars`, distinct shape/normalization radii, and exact required coefficient hashes; verify missing, altered, uncovered, or frame-inconsistent resources raise `TrajectoryRefinementError` without fallback.
- [x] 2.3 Assemble direct gravity from Sun, Mercury, Venus, Earth, Jupiter, and Saturn plus exactly one harmonic term each for Moon and Mars; verify inventory tests prevent double counting and independent fixed-state vector-sum tests meet the force tolerance.
- [x] 2.4 Add cannonball solar-radiation pressure using current mass, explicit `3.828e26 W` Sun luminosity, and Moon/Earth/Mars occultation; verify independent scaling plus clear, umbra, and penumbra tests meet the specified bounds.
- [x] 2.5 Add only the Sun Schwarzschild relativistic acceleration with PPN beta/gamma equal to one; verify a fixed-state comparison meets the force tolerance and provenance/tests show Lense-Thirring, de Sitter, and EIH disabled.
- [x] 2.6 Verify the pinned PCK hash and exact eight SPICE radius vectors, build conservative collision spheres from each maximum component, and keep Moon/Mars orbit-altitude and harmonic radii separate; verify every expected value within `0.001 m`, the impact inequality, private manifest-fragment output, and missing/invalid/drifted resource failures. Public CLI composition remains task 5.3.
- [x] 2.7 Measure the 300-second interpolated ephemerides against direct SPICE for all eight bodies at deterministic off-grid epochs and interval edges, and compare a denser table; record maximum position/velocity errors and adopt a measured error allocation within the existing endpoint budgets through strict spec validation before task 4.3. Verify coverage failures and record the interpolation method, spacing, and validation epochs.

Task 2.7 evidence (2026-09-07): `tests/test_trajectory_ephemeris.py` reproduces
`tests/data/m3_ephemeris_qualification.json` across the complete provisional
candidate interval at 38 epochs. Maximum 300 s/direct differences are
`0.0116642 m` and `1.21554e-6 m/s`; maximum 300 s/150 s differences are
`0.0170707 m` and `1.75493e-6 m/s`. The strict spec adopts `0.025 m` and
`2.5e-6 m/s` sampled input-state limits, not a bound on propagated error or
unsampled epochs. Both coverage rejection paths pass. All 304 tests, Ruff,
strict change validation, and the unchanged legacy checksum passed. No
production force, step size, closure tolerance, or dependency was changed.

## 3. Segmented finite-burn propagation

- [x] 3.1 Implement the specified Moon-relative and Mars-relative TNW basis, `(T,N,W)` azimuth/elevation mapping, rebuilt-frame guidance, and degeneracy guards; verify orthonormality, handedness, unit norm, central-body selection, exact formula, and deterministic failure tests.
- [ ] 3.2 Configure maximum-thrust engines with fixed Isp and coupled translation/mass propagation using supported TudatPy 1.0 APIs; verify isolated-burn mass loss and rocket-equation characteristic velocity meet their analytic tolerances.
- [x] 3.3 Configure the exact nominal RKF78 and tighter RKDP87 elementwise tolerances and burn/coast initial/minimum/maximum steps using the non-deprecated interface; verify settings introspection, forced minimum-step, failed-completion, and final-epoch mismatch tests enforce the numerical contract and chained errors.
- [ ] 3.4 Propagate exact departure-burn, coast, and arrival-burn arcs with state and mass handoff at fixed boundaries; verify a safely completed evaluation meets epoch, position, velocity, and mass continuity, preserves coast mass, and contains exactly two positive-duration burn records.
- [ ] 3.5 Enforce analytic and propagated dry-mass guards plus all eight collision surfaces without clamping or retaining unsafe states; verify unsafe internal trials increment deterministic reason/body counters without directly selecting public status, no unsafe state is retained, and no-safe-complete-trial results contain no propagated-result values.
- [ ] 3.6 Assemble the complete per-source force mapping and reset/read back global PPN values before every arc; verify near-Moon/cruise/near-Mars total acceleration against an independent assembly under the existing force tolerance, poisoned PPN recovery, and no duplicated gravity. Complete this before task 4.3.
- [ ] 3.7 Verify safety termination precedence over final-epoch failure, an initially unsafe state, and a trajectory entering and leaving a collision sphere between output epochs; distinguish rejected trials from native integration failures and discard unsafe trial history before task 4.3.

Task 3.2 integration evidence (2026-09-07): the native engine fixture now
exercises `_build_tnw_direction_callback` through Tudat rotation, thrust,
translation, and mass propagation for both departure/Moon and arrival/Mars.
Nonzero azimuth/elevation `(0.4, 0.2) rad` produces changing inertial directions
over 0.25 s and 100.25 s burns. An independent cross-product oracle agrees at
each callback within `1e-12`; mass retains the existing analytic tolerance and
speed obeys `v1-v0=cos(e)*cos(a)*g0*Isp*ln(m0/m1)` within `1e-6 m/s`.
Synthetic constant reference ephemerides and GM `1 m^3/s^2` are test-only;
the latter requests native reference-state updates and contributes less than
`4e-11 m/s` over these fixtures. They do not replace production resources.
All 43 focused checks, 308 full-suite tests, Ruff and strict validation passed;
the legacy checksum is unchanged. No production code or tolerance changed.
Task 3.2 remains unchecked: production installation/arc composition, adaptive
settings and safety guards are not supplied by this prerequisite experiment.

## 4. Bounded trajectory correction and science diagnostics

Task 3.3 completion evidence (2026-09-07, supersedes earlier pending notes):
`tests/test_native_minimum_step.py` uses the synthetic unstable ODE
`dv_x/dt = (1e12 / s) * v_x`, coupled with constant mass, to force both unchanged
production integrator profiles below their configured minimum step. Each native
run reports a minimum-step error and unsuccessful integration; the completion
reader raises a chained `TrajectoryRefinementError` instead of returning history.
Together with the exact settings tests, 18 native burn controls, and the
failed-completion/final-epoch rejection tests, this completes the component
criteria of 3.3. Both new tests and all 365 project tests pass, as do Ruff and
strict validation; the legacy checksum is unchanged. The full arc executor,
dry-mass/impact precedence and shared deadline remain separate unfinished tasks;
this check does not authorize the targeting spike. No physical model or
scientific tolerance was changed.

Task 3.3 completion-boundary evidence (2026-09-07):
`_read_completed_arc_state` returns only immutable Cartesian SI values and a
positive mass from a successful native simulation at the requested TDB epoch
within the existing `1e-6 s` tolerance. Failed completion is rejected before
reading partial history. Empty history, invalid epochs, wrong state dimensions,
non-finite/boolean components and invalid mass fail with chained candidate/arc/
expected-epoch context. Native RK4/RKF78/RKDP87 burn fixtures use this reader.
All 40 focused checks, 363 full-suite tests, Ruff and strict validation passed;
the legacy checksum is unchanged. Callers must classify safety terminations
before this reader and discard failed simulator history; positivity alone is
not the dry-mass guard. Task 3.3 remains open pending a forced native
minimum-step failure and arc-executor integration; no public refinement run is
enabled and no tolerance was relaxed.

Task 3.3 settings evidence (2026-09-07): `_build_arc_integrator` uses the
non-deprecated variable-step factory, seven-by-one elementwise SI tolerances,
exact nominal RKF78/tighter RKDP87 burn/coast steps, and explicit rejection of
below-minimum, NaN and infinite proposed steps. Native factory-call inspection
checks all six configurations; invalid inputs/imports/setup failures are covered.
The existing native engine oracles pass for RK4, nominal and tighter profiles,
both TNW frames and both durations. All 31 focused checks, 341 full-suite tests,
Ruff and strict validation passed; the legacy checksum remains unchanged.

Keep `assess_termination_on_minor_steps=False` (the native default). An exploratory
True setting left the last saved epoch at `97.00987294652838 s` instead of
`100.25 s` in the tighter arrival fixture despite exact time termination. The
default setting passes the original `1e-6 s` epoch gate. This is not evidence
of collision safety between full steps; task 3.7 remains a prerequisite.
Task 3.3 remains open: forced native minimum-step failure and production
failed-completion/final-epoch error translation still need the arc executor.

Task 3.2 adapter evidence (2026-09-07): `_install_tnw_engine` now installs the
validated maximum-thrust/fixed-Isp engine and TNW rotation on a fresh SSB/J2000
body system without resetting mass. Native departure and arrival fixtures use
this adapter and retain the independent direction, mass and speed oracles above.
Invalid spacecraft/steering inputs fail before native setup; wrong frames,
unavailable imports, rotation and engine failures produce contextual chained
errors. Discard a failed body system because native installation is not atomic.
The 51 focused checks, 316 full-suite tests, Ruff and strict OpenSpec validation
passed; the legacy checksum and scientific tolerances are unchanged. Task 3.2
remains open until production coupled arc composition is available; the adapter
alone does not expose a usable refinement API or satisfy the safety gates.

Task 3.2 prerequisite evidence: `tests/test_native_burn.py` qualifies the pinned native engine/rotation/translation-plus-mass path with isolated 0.25 s and 100.25 s burns. It checks mass loss within `max(1e-8 kg, 1e-11 * consumed_mass)` and the directed rocket-equation velocity increment within `1e-6 m/s`, using a non-axis-aligned-with-engine inertial direction. The thrust factory is `propagation_setup.thrust.custom_thrust_magnitude_fixed_isp`, not an `environment_setup.thrust` module. Production engine installation, TNW coupling, safety guards, and the adaptive propagator are still pending; task 3.2 remains unchecked.

- [x] 4.1 Add provisional `examples/m3_feasible_mission.toml` by changing only `dry_mass_kg` to `500.0`; verify all other normalized inputs and candidate geometry/epochs/delta-v/ideal masses are identical, while `mass_feasible` changes from false to true. Do not claim finite-burn feasibility before task 4.3 passes.
- [ ] 4.2 Implement the exact signed excess-velocity TNW projections, canonical angle domains, strict positive burn/coast window, analytic dry-mass domain, and sequential rocket-equation duration seed; verify formulas, direction signs, boundary equality rejection, degeneracy errors, `0.000001 s` duration agreement, and repeatability.
- [ ] 4.3 After tasks 2.7, 3.1-3.7, 4.1, 4.2, and shared-deadline plumbing in 4.10, run a reproducible targeting spike for provisional candidate `d0001-t0035` with the exact production force model, seed, corrector constants, eight-iteration/76-evaluation limits, and 300-second deadline; check in its script and machine-readable controls, residuals, resource/machine provenance, counters, safety and timing evidence. Verify a safe complete seed and the closure gate before production corrector work; if either fails, revise and strictly revalidate the formulation instead of silently weakening a bound.
- [ ] 4.4 Implement the specified safe-seed prerequisite, scaled residual, forward-only difference increments, unavailable-column stop, trust scales, `numpy.linalg.lstsq` solve with `rcond=1e-12`, fixed damping/acceptance sequence, lexicographic safe-command tie-break, and eight-iteration/73-control-attempt cap; verify unsafe seed, unsafe probe with no backward/fictitious continuation, synthetic convergence, finite rank-loss classification, non-finite solve errors, probe exclusion, exact tie-break, cap exhaustion, and repeatability tests.
- [ ] 4.5 Add exact status/reason invariants for `converged`, `mass-infeasible` with `preflight-m2-propellant-shortfall`, and `targeting-failed` with `nonconvergence` or `no-safe-complete-trial`; verify the preserved reference candidate is preflight mass-infeasible, no-safe exhaustion has null propagated-result values plus sorted rejection counts, and no status falsely claims target closure or an executable trajectory.
- [ ] 4.6 Refine the feasible fixture candidate through both finite burns within eight iterations, 73 control attempts, 76 propagation evaluations, 228 native arc calls, and the 300-second deadline; verify status `converged`, dry-mass and collision safety, and terminal errors no greater than `1000 m` and `0.01 m/s`.
- [ ] 4.7 Repropagate tentatively closed frozen commands with the distinct tighter integrator at identical arc boundaries; verify all four structured boundary differences stay within `10 m`, `0.0001 m/s`, and `0.000001 kg`, and an exceeded bound raises `scientific-validation` without returning a status.
- [ ] 4.8 Add frozen-command Moon 400/Mars 120 and Moon 200/Mars 60 sensitivity runs; verify both ordered four-boundary diagnostic tuples are returned only on convergence, the lunar differences meet `500 m` and `0.0001 m/s` or raise `scientific-validation`, the finite Martian tail is recorded, and degree 120 is labeled as the model ceiling rather than an error bound.
- [ ] 4.9 Add the isolated ten-orbit point-mass conservation fixture; verify relative specific-energy and angular-momentum-norm drift are each no greater than `1e-11` without applying that invariant to the forced mission trajectory.
- [ ] 4.10 Apply one monotonic deadline and the exact control-attempt, propagation-evaluation, and native-arc increment rules across candidate verification, targeting, partial impacts, analytic rejections, and diagnostics; verify counter fixtures and forced deadline tests report the limit plus all completed counts and return no partial result.

Task 4.1 evidence: `tests/test_m3_fixture.py` compares both raw TOML and normalized scenarios and runs both full M2 searches with real TudatPy/SPICE. Candidate `d0001-t0035` is exactly equal after changing only its budget flag, with ideal final mass between 500 and 1000 kg. This is not a finite-burn propagation test; task 4.3 remains unchecked.

Task numbering is stable identification, not a mandate to defer cross-cutting checks: implement the shared deadline before the spike and extend it through final manifest construction. Resource loading/hashing also consumes this budget; test that M2 and later stages never reset it.

## 5. CLI, provenance, and compatibility

- [ ] 5.1 Add `space-nav refine SCENARIO --candidate-id ID [--json]` using the existing parser and candidate search without duplicate refinement handoff work; verify completed classifications exit `0`, user/resource/deadline/integration/scientific-validation errors exit `2`, and invalid input starts no physical propagation.
- [ ] 5.2 Add human rendering that labels status, boundary conventions, SI units, burns, masses, residuals, and diagnostics while omitting absent values; verify snapshots for converged, mass-infeasible, and targeting-failed results contain no traceback or fabricated zeros.
- [ ] 5.3 Extend canonical JSON and the diagnostic manifest with the literal model ID and all M2 seed, exact force/gravity hashes/frames, collision surfaces, explicit luminosity/SRP, relativity, burn, exact integrator/corrector, threshold, count, and ignored-input provenance; verify schema assertions and two identical runs produce byte-identical JSON.
- [ ] 5.4 Prove M3 ignores tracking settings, maneuver-error sigmas, and random seed; verify paired scenarios differing only in those deferred fields produce identical commands, states, statuses, and scientific diagnostics.
- [ ] 5.5 Set package and manifest version fields to `0.3.0` only after the capability is complete; verify version tests and all existing `validate`, `ephemeris`, and `plan` API/CLI compatibility tests pass.

## 6. Completion gate

Checked component tasks do not imply an operational M3 API, full-force propagation, public manifest integration, or proven feasibility. At the start of the 2026-09-06 review the authoritative repository `/Users/agrudin/dev/my/ariadna` was on `main` at `7823031` after an earlier branch rename. Continue work on `dev` as required by AGENTS.md. The earlier M3.3.1 working-copy material was subsequently reviewed, constructor and norm guards were strengthened, and only the verified guidance source/tests were transferred. `tests/test_trajectory_guidance.py` checks the independent vector oracle and direct TudatPy TNW rotation within `1e-12` dimensionless direction cosines, explicitly selecting inward N rather than Tudat's outward-N default. Callback frame rebuilding and errors use injected current body states; native engine/propagator integration remains task 3.2 onward.

- [ ] 6.1 Run focused M3 unit, integration, CLI, scientific, resource-failure, determinism, feasible-reference, and infeasible-reference tests in the pinned Python 3.12 Conda/uv environment; verify every test passes and the feasible end-to-end run remains below 300 seconds.
- [ ] 6.2 Run the complete project test suite and verify all M1/M2 regression, numerical, provenance, and lazy-import checks pass with no test exclusions introduced by M3.
- [ ] 6.3 Verify `moon_to_mars.py` is byte-for-byte unchanged from its pre-M3 checksum and is not imported by `space_nav`, then record both checks in the implementation evidence.
- [ ] 6.4 Run `openspec validate refine-physical-trajectory --strict`, verify the working tree contains only intended M3 changes, and mark tasks complete only when their stated checks have actually passed.
