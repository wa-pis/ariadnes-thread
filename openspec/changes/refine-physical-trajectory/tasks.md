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

- [x] 3.10 Apply the user-approved 2026-09-09 direct-SPICE production revision; verify whole-chain interval coverage, missing/gapped/incompatible resources and deadline rejection before body creation, direct settings/frame readback, 38-epoch eight-body and 219-probe Saturn production parity within 0.001 m / 0.000001 m/s, unchanged force controls, versioned model identity, complete pytest, Ruff and strict OpenSpec validation. This prerequisite does not complete 3.9 or permit the targeting spike.

Task 3.10 verification (2026-09-09): 139 focused environment/contract/gravity
tests and all 881 tests passed; Ruff, strict OpenSpec validation and the
unchanged legacy SHA-256 passed. The production comparison covers 523 state
requests under the stated tolerances. No new dependencies, kernel versions,
force settings, tolerances or native-call limits. Historical tables remain
test controls; current M3 result identity is explicitly direct-SPICE v2.

User-approved revision (2026-09-08): investigate adaptive subdivision and revise
native-call limits from measured evidence. Scientific tolerances and the shared
300-second deadline remain unchanged. Production limits are not replaced by
an arbitrary larger value; isolated qualification uses at most 32 subsegments.

- [x] 3.8 Qualify bounded adaptive interval screening on straight and constant-acceleration controls; verify collision, clear passage and unresolved tangency against independent analytic motion within 0.001 m, count all native subsegments including discarded parents, and preserve deadline/limit failures with no safe result.
- [ ] 3.9 Derive and verify full-force interval/ephemeris error bounds, measure representative full-force subdivision counts and wall time, and only then revise production native-call limits consistently in specs, design, result invariants and budget tests; verify all unchanged scientific tolerances and the shared 300-second deadline before the targeting spike.

- [x] 3.1 Implement the specified Moon-relative and Mars-relative TNW basis, `(T,N,W)` azimuth/elevation mapping, rebuilt-frame guidance, and degeneracy guards; verify orthonormality, handedness, unit norm, central-body selection, exact formula, and deterministic failure tests.
- [x] 3.2 Configure maximum-thrust engines with fixed Isp and coupled translation/mass propagation using supported TudatPy 1.0 APIs; verify isolated-burn mass loss and rocket-equation characteristic velocity meet their analytic tolerances.
- [x] 3.3 Configure the exact nominal RKF78 and tighter RKDP87 elementwise tolerances and burn/coast initial/minimum/maximum steps using the non-deprecated interface; verify settings introspection, forced minimum-step, failed-completion, and final-epoch mismatch tests enforce the numerical contract and chained errors.
- [ ] 3.4 Propagate exact departure-burn, coast, and arrival-burn arcs with state and mass handoff at fixed boundaries; verify a safely completed evaluation meets epoch, position, velocity, and mass continuity, preserves coast mass, and contains exactly two positive-duration burn records.
- [ ] 3.5 Enforce analytic and propagated dry-mass guards plus all eight collision surfaces without clamping or retaining unsafe states; verify unsafe internal trials increment deterministic reason/body counters without directly selecting public status, no unsafe state is retained, and no-safe-complete-trial results contain no propagated-result values.
- [x] 3.6 Assemble the complete per-source force mapping and reset/read back global PPN values before every arc; verify near-Moon/cruise/near-Mars total acceleration against an independent assembly under the existing force tolerance, poisoned PPN recovery, and no duplicated gravity. Complete this before task 4.3.
- [ ] 3.7 Verify safety termination precedence over final-epoch failure, an initially unsafe state, and a trajectory entering and leaving a collision sphere between output epochs; distinguish rejected trials from native integration failures and discard unsafe trial history before task 4.3.

Task 3.9 initial point-mass jerk intervals (2026-09-13):
Qualify sign-aware rational/root derivative intervals against exact radial,
transverse and irrational-radius analytic oracles and invalid inputs. Retain
the ideal SPK position and its derivative for the initial epoch; verify the
existing position allowance before reporting six point-mass derivative
intervals in both fixture geometries. Verify both real inventories, unchanged
native/readback counts, full pytest, Ruff, strict OpenSpec and legacy checks.
No native jerk measurement, new force model or completed cubic certificate
is claimed; task 3.9 remains open.

Focused verification: 38 tests passed in 196.66 s, including 36 analytic
interval/input controls and both real inventories. Ideal initial source
positions satisfy the existing arithmetic allowances for all eight bodies.
Both inventories report the same 12 point-mass jerk vectors (six sources
at two fixtures), each with three finite outward-rounded component intervals.
For example, the Sun x-component is enclosed by
[1.1755206120305393e-9, 1.1755206120305397e-9] m/s^3 near Moon and
[3.5808001683010496e-11, 3.580800168301051e-11] m/s^3 near Mars.
These are conditional arithmetic enclosures, not physical error allocations.
The five/zero spacecraft arcs and 24 affine readbacks per inventory remain
unchanged; no harmonic, radiation-pressure or relativistic jerk is supplied.

Completion verification: all 1828 project tests passed in 457.24 s.
Ruff, strict OpenSpec, diff and unchanged legacy checksum/import isolation
passed. The complete test-suite time is not a mission-operation runtime;
the shared 300-second deadline and native limits remain unchanged. No
dependencies, production force settings or UI behavior changed. Task 3.9
remains open; these intervals are initial component data, not a trajectory
or native internal-stage certificate.

Task 3.9 point-mass force-curvature control (2026-09-13):
Qualify a conservative second-time-derivative bound for point-mass
acceleration under explicit relative distance/speed/acceleration bounds.
Verify exact Cartesian chain-rule and circular-motion oracles, radial
Taylor remainders, invalid inputs, full pytest, Ruff, strict OpenSpec and
legacy isolation. No native calls or production changes; do not qualify
full-force cubic references or close 3.9 from this component control.

Focused verification: all 70 tests passed in 0.02 s: 36 exact Cartesian
chain-rule cases at two gravitational parameters, four circular controls,
six radial Taylor-remainder controls and 24 invalid-input checks. All
inequalities use exact rational arithmetic, with no floating tolerance.
The circular bound is intentionally 26 times its exact force curvature;
this documents conservatism, not a numerical-accuracy allocation.
Uniform relative-motion premises and all other force derivatives remain
unqualified for a native cubic reference; no native or SPICE calls were added.

Completion verification: all 1792 project tests passed in 456.00 s.
Ruff, strict OpenSpec, diff and unchanged legacy checksum/import isolation
passed. Full-suite duration is separate from the shared 300-second mission
operation deadline. Dependencies, production forces, UI and native limits
are unchanged. This completes only the stated analytic component controls;
task 3.9 remains open.

Task 3.9 reference-bound diagnosis and analytic cubic control (2026-09-12):
Report the existing weighted reference enclosure separately from endpoint
residuals, retaining their exact composition and all prior outputs. Verify
whether the reference velocity bound alone resolves the unchanged gate.
Qualify quadratic/cubic reference comparisons on exact time-forced rational
motion with both signs and large translations; do not transfer those
analytic gains to the physical model. Verify focused analytic/native tests,
unchanged five-arc/24-readback counts, full pytest, Ruff, strict OpenSpec
and legacy isolation. No new native calls or production settings; 3.9 stays open.

Focused verification: 100 tests passed in 198.26 s (98 analytic controls
and both real inventories). All 16 cubic-reference cases enclose the exact
rational position/velocity errors. At 1/32 s their enclosure ratio to the
quadratic reference is exactly 2/31, only for the stated analytic fixture.

For the real doubled Mars control, the weighted reference velocity bound
alone is 1.3500214429163211e-6 m/s, already above 1e-6 m/s. Its native-to-
reference endpoint residual is 6.289304896345159e-7 m/s, and the composed
bound remains 1.978951932550837e-6 m/s. These numbers are outward-rounded
individually; exact Fraction composition is retained internally. The
reference-only short bounds are 4.324104195093951e-7 m/s near Moon and
3.379036770041845e-7 m/s near Mars, unchanged for both native profiles.
All prior endpoint fields/gates, five arcs in the native inventory (zero
in portable) and 24 affine readbacks in each inventory are preserved.
Cubic physical-reference qualification is
still absent: the analytic force derivatives are not substitutes for it.

Completion verification: all 1722 project tests passed in 462.12 s,
including the reference-only gate failure in the doubled Mars control.
Ruff, strict OpenSpec, diff and unchanged legacy checksum/import-isolation
checks passed. Full-suite duration is not a mission-operation runtime;
the shared 300-second deadline is unchanged. Existing qualification code
was reused without dependencies or production changes. Task 3.9 remains open.

Task 3.9 doubled-duration coast control (2026-09-12):
Add a 1/32 s domain without changing the existing radii or scientific
settings. Recompute closure and all force bounds before one nominal native
control per newly closed domain; preserve unclosed cases without native
integration. Verify both real inventories and analytic transport controls,
exact readback/arc counts, separate unchanged position/velocity gates,
full pytest, Ruff, strict OpenSpec and legacy isolation. Preserve all older
short controls and the 1/64 s uniform-tiling counterexample. Do not mark
3.9 complete or infer actual trajectory errors from unresolved envelopes.

Focused verification: all 84 tests passed in 197.39 s, including 82 analytic
transport controls and both real inventories. Each inventory now verifies
24 affine SPICE positions instead of 16. The native inventory performs
exactly five spacecraft arcs: four preserved short controls plus one nominal
Mars control at 1/32 s, within the existing 32-control qualification ceiling.

The doubled Moon position reach is 1291.178421959348 m versus the unchanged
1000 m domain, so closure is unresolved and no native arc is launched there.
Mars closes with 953.9021169099452 m position reach and
0.09953182731368805 m/s velocity reach versus 1000 m / 0.1 m/s.
Its weighted position bound is 4.9306456908110534e-5 m (passes 0.001 m),
but its velocity bound is 1.978951932550837e-6 m/s (unresolved at 1e-6 m/s).
The extra native arc took 0.14766687504015863 s; the complete extra control,
including independent force qualification, took 23.39191791601479 s in this
local run. These are diagnostic timings, not mission-runtime predictions.
The four original weighted endpoint gates and initial-ball outcomes persist;
the failed doubled-duration velocity bound is retained without relaxing it.

Completion verification: all 1706 project tests passed in 463.21 s;
Ruff, strict OpenSpec, diff and legacy checksum/import-isolation checks
passed. Full-suite time is separate from the unchanged 300-second operation
deadline. Production limits, dependencies, force settings and the UI are
unchanged; the experiment reuses existing qualification routines. Task 3.9
remains open because the doubled interval did not pass all scientific gates.

Task 3.9 time-weighted reference defect (2026-09-12):
Qualify an explicit linear-in-time defect extension of the existing
test-only transport lemma. Verify exact constant-jerk controls, nonzero
sensitivity controls, zero-rate compatibility, invalid inputs and feedback
rejection. Compose the qualified relative-motion and unsaturated rotation
bounds in the same four native short controls, retaining all old results.
Verify focused analytic/native tests, full pytest, Ruff, strict OpenSpec,
diff and legacy isolation. No additional native calls, changed tolerances,
production settings or longer-interval claims; task 3.9 remains open.

Focused verification: all 84 tests passed in 181.55 s: 82 analytic controls
and both real inventories. All four weighted endpoint position/velocity
bounds are strictly below their prior uniform-defect bounds and meet the
unchanged 0.001 m / 1e-6 m/s gates. The linear rotation-branch assertion
passes for both bodies in all four declared domains. All old native and
initial-ball pass/unresolved checks remain unchanged. The duration is still
1/64 s, and the native spacecraft-arc count is still four; no longer arcs
or mission-runtime qualification are inferred from this improvement.

Completion verification: all 1706 project tests passed in 458.70 s.
Ruff, strict OpenSpec, diff checks and unchanged legacy checksum/import
isolation passed. Full-suite duration is not a measurement of one mission
operation; its shared 300-second deadline remains unchanged. No dependencies
or production code changed; the extension reuses the existing exact lemma.

Task 3.9 nonzero initial-state ball controls (2026-09-12):
Verify first-exit domain closure for explicit initial position/velocity
balls before applying the existing reference transport. Report both endpoint
gates for three cases per native control, preserving unresolved outcomes
without changing inputs or tolerances. Verify analytic transport controls,
both real inventories, full pytest, Ruff, strict OpenSpec and legacy checks.
Do not treat fixture radii as mission allocations or measured uncertainties;
no extra native calls or production changes, and task 3.9 stays open.

Focused verification: 57 tests passed in 167.02 s, including the 55 analytic
transport controls and both real inventories. All 12 initial-ball cases
close inside the original domains and pass the 0.001 m position gate;
position bounds span approximately 0.111-0.1442 mm. With 5e-8 m/s initial
velocity radius, Moon nominal/tighter bounds are 9.80293277042568e-7 /
9.802769061379362e-7 m/s, below the unchanged velocity gate.

With 1e-7 m/s initial velocity radius, Moon bounds become
1.0302932770660895e-6 / 1.0302769061614576e-6 m/s: explicitly unresolved,
not accepted and not evidence of an actual error exceeding the gate. Mars
bounds are 9.316263564472676e-7 / 9.316236279631623e-7 m/s and pass.
Preserve this exact pass/unresolved pattern as a full-suite regression.
The nominal initial state, reference, four native runs and deadline are unchanged.

Completion verification: all 1679 project tests passed in 435.30 s,
including the explicit pass/unresolved pattern. Ruff, strict OpenSpec,
diff checks and legacy checksum/import isolation passed. Full-suite time
is separate from the unchanged 300-second operation deadline. No native
calls, dependencies, production changes or relaxed tolerances were added.

Task 3.9 continuous quadratic-reference transport control (2026-09-12):
Reuse the exact initial-state quadratic reference only after verifying
its acceleration norm and existing position/velocity domain bounds.
Compose initial-force error and uniform reference-force variation into
an acceleration defect; apply the qualified transport lemma and add exact
native endpoint residuals. Verify all four short controls meet unchanged
position/velocity gates, retain older bounds, run analytic transport and
both inventory checks, full pytest, Ruff, strict OpenSpec and legacy checks.
Keep one-second/initial-uncertainty/internal-stage qualification open; do
not change production settings, limits or the status of task 3.9.

Focused verification: 57 tests passed in 169.73 s (55 analytic transport
controls and both inventories). Quadratic-reference defect bounds are
5.026853118186602e-5 m/s^2 near the Moon and 4.3161491844015855e-5 m/s^2
near Mars. Uniform reference-relative errors are 6.1362953117297215e-9 m /
7.854457999014044e-7 m/s and 5.268736798533911e-9 m /
6.743983102123406e-7 m/s respectively. These enclose the ideal solution
relative to the mathematical reference, not native internal stages.

After saved-endpoint residuals, nominal/tighter Moon position bounds are
1.098544953249081e-5 / 4.419101172685544e-5 m and velocity bounds
9.302902662842429e-7 / 9.30273895379611e-7 m/s. Mars bounds are
4.090019426766819e-5 / 2.9855559747167103e-5 m and
8.316235171505068e-7 / 8.316207886664015e-7 m/s. All satisfy the unchanged
gates. Four native arcs and all earlier bounds remain unchanged.

Completion verification: all 1679 project tests passed in 430.74 s.
Ruff, strict OpenSpec, diff checks and unchanged legacy checksum/import
isolation passed. Full-suite duration is distinct from the unchanged
300-second operation deadline; no native calls or dependencies were added.

Task 3.9 fully lit coast state-sensitivity composition (2026-09-12):
Extract and independently qualify the existing SRP position operator bound,
preserving its source-variation wrapper. Compose all ten fixed-epoch coast
position sensitivities after proving whole-domain illumination; keep only
Schwarzschild velocity sensitivity. Verify exact force inventory, outward
rounding and k<1 diagnostics in both inventories, focused/full pytest,
Ruff, strict OpenSpec and legacy checks. Keep domain closure/reference
defect prerequisites explicit, limits unchanged and task 3.9 open.

Focused verification: 43 tests passed in 166.92 s, including 24 new SRP
directional-derivative controls and both inventories. Short-domain Lx is
1.9268702739140936e-6 s^-2 near the Moon and 1.8171215339974738e-6 s^-2
near Mars. Corresponding Lv is 2.8050418990982346e-14 s^-1 and
7.305410983566095e-15 s^-1. Short-domain feedback bounds are
2.3521409477145077e-10 and 2.2181670765259764e-10. One-second domain
feedback also remains below one (1.7589339439860222e-6 and
9.624760840255162e-7), but those trajectory domains remain unclosed.
Both inventory variants reproduce all values. Four native arcs, source
queries, initial-force and endpoint allowances are unchanged.

Completion verification: all 1679 project tests passed in 431.74 s.
Ruff, strict OpenSpec, diff and legacy checksum/import-isolation checks
passed. No new native calls, dependencies or changed physical tolerances.
Full-suite time is separate from the unchanged 300-second operation limit.

Task 3.9 whole-domain full-illumination geometry (2026-09-12):
Include observer-position uncertainty in the existing apparent-sphere
separation proof. Verify exact tangency, smaller/larger/invalid balls and
large common offsets. Report per-occultor separation over all four declared
Moon/Mars domains using existing body reaches and the spacecraft position
ball; keep domain closure separate. Verify both real inventories, full
pytest, Ruff, strict OpenSpec, diff and legacy checks. Preserve SRP bounds,
all native-call limits and production behavior; task 3.9 remains open.

Focused verification: 41 tests passed in 166.63 s, including 14 new observer
ball controls and both real inventories. All 12 body/domain combinations
per inventory prove strict separation from Moon, Earth and Mars across the
entire declared position domain. Assert this pinned-fixture result explicitly
in the full suite. The two short ideal coasts have separately closed domains;
the one-second controls still do not, despite their domains being fully lit.
No force allowance or endpoint tolerance was tightened in this step.

Completion verification: all 1655 project tests passed in 430.70 s,
including explicit whole-domain separation assertions for all occultors.
Ruff, strict OpenSpec, diff and legacy checksum/import-isolation checks
passed. The operation deadline and four native control arcs are unchanged;
full-suite time does not measure a single mission operation.

Task 3.9 reusable Schwarzschild state sensitivities (2026-09-12):
Extract existing position/velocity operator bounds and preserve the source
variation wrapper. Verify exact Cartesian directional derivatives in four
directions at two positions and three velocities, prior variation/rejection
controls, and outward conditional sensitivity diagnostics in both real
inventories. Run focused/full pytest, Ruff, strict OpenSpec, diff and legacy
checks. Do not label this one-component result a full-force transport or
safety certificate; keep task 3.9 open and production unchanged.

Focused verification: 79 tests passed in 164.71 s, including 48 exact
directional-derivative controls and both real inventories. For the short
Moon domain, Lx=1.9115340404949474e-20 s^-2 and
Lv=2.8050418990982346e-14 s^-1; the short Mars domain gives
2.2335261462366957e-21 s^-2 and 7.305410983566095e-15 s^-1.
Both inventory variants agree on all four domain diagnostics. Existing
source-state allowances, endpoint gates and four native arcs are unchanged.
The one-second domains remain unclosed; these numbers do not close them.

Completion verification: all 1641 project tests passed in 429.42 s.
Ruff, strict OpenSpec, diff checks and legacy checksum/import isolation
passed. No new native calls or physical changes; the 300-second operation
deadline is unchanged and is distinct from full-suite duration.

Task 3.9 conditional initial-error transport lemma (2026-09-12):
Derive a rational position/velocity error enclosure from initial errors,
uniform acceleration defect and position/velocity sensitivities under a
strict feedback condition. Verify constant-acceleration equality, exact
nonlinear position/velocity/coupled controls, four-segment carryover,
near-singular arithmetic and invalid/unresolved input rejection. Run
focused/full pytest, Ruff, strict OpenSpec, diff and legacy checks.
Do not use unqualified full-force sensitivities or promote analytic
controls to real trajectory safety; preserve all limits and keep 3.9 open.

Focused verification: 55 controls passed in 0.02 s. The first run exposed
the velocity-only nonlinear h=0.25 s boundary: Lv=4 s^-1 gives k=1 even
though the exact endpoint (4/3 m, 16/9 m/s) is finite. Preserve that input
as an expected unresolved rejection; the strict criterion is unchanged.
The remaining nonlinear controls, constant-force equalities, carryover and
invalid-input checks pass. This is analytic evidence only, not a qualified
full-force transport or longer native-arc result.

Completion verification: all 1593 project tests passed in 428.43 s,
including existing real SPICE/native parity controls. Ruff, strict OpenSpec,
diff checks, legacy SHA-256 and import isolation passed. No new native
calls, dependencies, scientific tolerances or production changes. Suite
duration is separate from the unchanged 300-second operation deadline.

Task 3.9 short-control tiling cost screen (2026-09-12):
Verify the exact number of uniform 1/64 s segments covering the pinned
candidate interval and compare with the unchanged operation-wide 228-arc
limit. Report excluded work explicitly; do not claim a lower bound for
adaptive methods or mission infeasibility. Measure the existing four
native calls and their complete control-verification time separately,
preserving deadline checks and counters. Verify both inventory variants,
full pytest, Ruff, strict OpenSpec, diff and legacy checks. Keep 3.9 open.

Focused verification: both inventory variants passed in 166.80 s. Both
report exactly 1,611,124,364 hypothetical uniform arcs versus 228 available;
all 228 would cover only 3.5625 s of the 25,173,818.181818128 s interval.
Measured native-call times for Moon nominal/tighter were 0.156/0.409 s and
Mars 0.152/0.373 s. Complete per-control verification took 45.71/46.63 s
and 22.84/23.12 s respectively, excluding shared resource preparation.
Only four native calls ran; no projected calls were scheduled. The
operation deadline passed unchanged. These timings cannot be extrapolated
into a certified mission-runtime bound.

Completion verification: all 1538 project tests passed in 431.24 s; Ruff,
strict OpenSpec, diff checks and unchanged legacy checksum/import isolation
passed. Full-suite duration is separate from the operation deadline.
No limits or scientific tolerances changed; task 3.9 remains open.

Task 3.9 initial-acceleration position remainder (2026-09-12):
Bound saved-endpoint position error by its exact quadratic-reference L1
residual plus `(E+C)*h^2/2`, reusing qualified initial-force and interval
variation bounds. Verify analytic constant/linear acceleration controls,
vector residuals, exact zero and invalid inputs; compare all four short
native controls to the prior ballistic bound under the unchanged 0.001 m
gate. Run focused/full pytest, Ruff, strict OpenSpec and legacy checks.
Do not promote this conditional endpoint result to native-stage or
long-trajectory safety; keep task 3.9 open and all operational limits intact.

Focused verification: 25 tests passed in 165.78 s (23 analytic/rejection
controls and both inventories). Nominal/tighter conditional position
bounds are 1.0985449532489367e-5 / 4.4191011726853996e-5 m near the Moon
and 4.090019426766702e-5 / 2.9855559747165934e-5 m near Mars. All four
improve on the retained ballistic bound and pass 0.001 m without changing
velocity gates, native arc count, source requests or the shared deadline.
These are conditional upper bounds, not observed true trajectory errors.

Completion verification: all 1538 project tests passed in 430.59 s. Ruff,
strict OpenSpec, diff checks, unchanged legacy SHA-256 and package import
isolation passed. Full-suite duration is separate from the unchanged
300-second operation budget. No native calls or dependencies were added.

Task 3.9 lunar degree-150 qualification (2026-09-12):
Extend the independent nearby lunar prefix to 150, retain nearby Mars 120
and distant prefixes 20, and preserve all remainder bounds and dynamics.
Verify degree-150 analytic matrix/source composition, both real inventories,
the unchanged velocity gate for all four short native controls, full pytest,
Ruff, strict OpenSpec, diff and legacy checks. Keep task 3.9 open.

Focused verification passed 65 tests in 168.74 s, including nine additional
analytic controls. The lunar complete initial-force bound is now
4.824501711104862e-6 m/s^2. Its conditional 1/64 s endpoint velocity bounds
are 9.302902660994951e-7 and 9.302738951948632e-7 m/s, below the unchanged
1e-6 m/s gate. Mars remains at 8.316235170009139e-7 and
8.316207885168086e-7 m/s. Strengthen the explicit gate to both bodies.
Lunar generic evaluations took 42.82-43.41 s each; the shared deadline
passed unchanged. Four native arcs and source requests are unchanged.
This does not establish long-trajectory or internal-stage safety.

Completion verification: all 1515 project tests passed in 424.33 s,
including the strengthened Moon/Mars velocity assertions. Ruff, strict
OpenSpec and diff checks passed; legacy SHA-256 and import isolation are
unchanged. Suite duration is not a mission-runtime certificate.

Task 3.9 monopole-split operator bound (2026-09-12):
Compose the exact `2*GM/d^3` C00=1 operator norm with the existing
nonmonopole Jacobian bound. Verify monopole eigenvalues/point-mass parity,
mixed degree-4/12 polar derivatives, invalid domains and strict improvement.
Reuse this only for a separately reported relative spatial variation and
saved-endpoint velocity bound; preserve all other terms and older bounds.
Verify the unchanged Mars velocity gate, run focused/full pytest, Ruff,
strict OpenSpec and legacy checks. Do not close 3.9 from a short control.

Focused verification: 19 tests passed in 117.22 s, including 17 new analytic
and rejection controls and both inventories. Split force-variation bounds
are 4.5444029470761146e-5 m/s^2 near the Moon and
4.316119215669777e-5 m/s^2 near Mars, identical across inventory variants.
Moon velocity bounds are 1.310122212732238e-6 m/s (nominal) and
1.3101058418276061e-6 m/s (tighter), still above 1e-6 m/s. Mars bounds are
8.316235170009139e-7 and 8.316207885168086e-7 m/s, both below that gate.
The full suite additionally asserts the Mars gate for both native profiles.

The result is conditional on the existing exact-initial-state, source/PCK
and closed-domain premises and applies only to the two 1/64 s coast
fixtures. No full-trajectory or internal native-stage safety is claimed.
Four native arcs, 16 affine ephemeris requests per inventory, production
settings, numerical tolerances and the shared deadline are unchanged.
There are no new native calls, dependencies or UI changes. Task 3.9 is open.

Completion verification: all 1506 project tests passed in 378.15 s,
including the explicit unchanged Mars velocity gate. Ruff, strict OpenSpec
and diff checks passed. The legacy SHA-256 is unchanged and the package
does not import it. Suite time is separate from the 300-second mission
deadline; no physical or numerical acceptance tolerance changed.

Task 3.9 relative-motion composition (2026-09-12):
Use the qualified source position derivatives and curvatures to bound
relative displacement by `|v_ship-v_source|_1*h+(A_ship+B_source)*h^2/2`.
Verify independent opposing-acceleration/common-velocity controls, vector
norms, zero motion and invalid/coverage rejection. After original-domain
closure only, reuse existing distance floors/Jacobians to refine gravity
variation and the saved-endpoint velocity bound. Retain all other force
allowances, old bounds and the 1e-6 m/s gate. Run focused/full pytest,
Ruff, strict OpenSpec and legacy checks; keep 3.9 open.

Focused verification: 19 tests passed in 117.11 s, including 17 new
kinematic/domain controls and both inventories. Central-body displacement
bounds are 23.43768259540861 m near the Moon and 23.43788914719493 m near
Mars. Complete relative force-variation bounds are
6.402457168954275e-5 and 6.317737501360288e-5 m/s^2, respectively.
Both inventories reproduce these values. The one-second domains remain
unresolved and have null relative-motion diagnostics.

Combined velocity bounds in m/s are Moon nominal 1.6004431849007004e-6,
Moon tighter 1.6004268139960685e-6, Mars nominal 1.1443763741400563e-6,
and Mars tighter 1.144373645655951e-6. All are strictly below the preceding
anchored bounds and all remain above 1e-6 m/s; acceptance flags remain
false. These are conditional upper bounds, not actual errors.
The four native arcs, 16 affine ephemeris queries per inventory, shared
deadline and production settings are unchanged. No new dependencies or UI
changes; the result does not close interval safety or permit targeting.

Completion verification: all 1489 project tests passed in 377.72 s. Ruff,
strict OpenSpec validation and diff checks passed. The legacy SHA-256 is
unchanged and the package does not import the educational model. Suite
duration is not the unchanged 300-second mission deadline. Task 3.9 is open.

Task 3.9 SPK affine source-motion prerequisite (2026-09-12):
Evaluate exact initial position derivatives and uniform second-derivative
L1 bounds from position coefficients, including type-3 records without
using their separate velocity series. Verify expanded cubic controls,
single-mode endpoints, invalid inputs/intervals and deadlines. Select one
qualified core covering the first second for every source link, compose
SSB chains, and check direct-SPICE endpoints with the existing arithmetic
error allowance. Run focused/full pytest, Ruff, strict OpenSpec and legacy
checks; do not yet replace the force-variation bound or close 3.9.

Focused verification: 25 tests passed in 117.76 s, including 23 new analytic
and rejection controls and both inventories. Each inventory qualifies 11
links and makes 16 additional SPICE position queries: eight bodies at
1/64 s and 1 s. The source-polynomial acceleration L1 bounds in m/s^2 are
Sun 2.6261703387877057e-7, Mercury 0.062409018596834606,
Venus 0.019380598627597605, Earth 0.009777611384210193,
Moon 0.01494818190424113, Mars 0.002778410201880391,
Jupiter 0.003466485629056375 and Saturn 0.00015720062924796832.
Both inventories reproduce the same values. These are polynomial bounds,
not measured physical accelerations or new ephemeris uncertainty estimates.

The four existing native spacecraft arcs and zero portable arcs are
unchanged. No new dependencies, resources, production/UI behavior, budgets
or scientific tolerances. Existing anchored velocity bounds stay unresolved;
relative source/spacecraft motion composition is the next prerequisite.

Completion verification: all 1472 project tests passed in 378.90 s. Ruff,
strict OpenSpec validation and diff checks passed. The educational model's
SHA-256 remains unchanged and the package does not import it. Full-suite
duration is separate from the unchanged 300-second mission deadline.

Task 3.9 initial-acceleration velocity enclosure (2026-09-12):
Add the exact saved Euler residual plus `(initial_force_error +
interval_force_variation)*duration` velocity bound. Verify constant and
linear acceleration oracles, three-axis residuals, exact-zero resolution
and invalid inputs, then compose existing conditional full-force evidence
on the four saved 1/64 s native coast controls. Preserve the old bound and
unchanged gate; run focused/full pytest, Ruff, strict OpenSpec and legacy
checks. A failing upper-bound gate is unresolved, not measured mission error.

Focused verification: 25 tests passed in 117.69 s, including 23 new analytic
and rejection controls and both inventories. Near-Moon velocity bounds are
7.911016052555362e-5 m/s (nominal) and 7.911014415464899e-5 m/s (tighter);
near-Mars bounds are 7.504470858243644e-5 and 7.504470585395234e-5 m/s.
All improve the old norm-only enclosure and all remain above 1e-6 m/s.
Saved Euler residuals are respectively 1.448444663828386e-7,
1.448280954782067e-7, 1.5722520693816621e-7 and
1.572224784540609e-7 m/s; these alone are not trajectory error bounds.
The existing force-variation allowance dominates the combined result.

The same four native arcs and shared deadline are used, with no extra
force queries, dependencies, physical assumptions, public interfaces or UI
changes. Initial-state, SPK/PCK and closed-domain premises remain conditional;
the 1-second unresolved domain is not promoted. Task 3.9 stays open.

Completion verification: all 1449 project tests passed in 378.99 s. Ruff,
strict OpenSpec validation and diff checks passed. The educational model's
SHA-256 remains unchanged and the package does not import it. Suite wall
time is not the per-mission deadline; no numerical tolerance or budget changed.

Task 3.9 per-source degree-120/20 qualification (2026-09-12):
Use degree 120 for each near-body control's central field and degree 20
for the other source, retaining every remaining term in its source-specific
tail bound. Verify both allocations, per-term native parity, exact Mars
ceiling exhaustion, degree-120 polar perturbation controls, composed errors
and timing under the same deadline. Run focused/full pytest, Ruff, strict
OpenSpec and legacy checks. Keep production fields and task 3.9 unchanged.

Focused verification: 56 tests passed in 119.60 s. All 30,448 native term
vectors ((7381 nearby + 231 distant) * four controls) meet the unchanged
gate. The 54 analytic perturbation combinations include nine new degree-120
controls. Nearby prefix SPK/PCK/arithmetic L2 errors are bounded by
2.8786850092714696e-11 m/s^2 for the Moon and
1.2829335807524715e-11 m/s^2 for Mars. Complete conditional initial-force
bounds are 2.9133746295600405e-5 m/s^2 and 2.9968731808185163e-10 m/s^2,
respectively, identical across both integrator profiles. The anchor-only
error times 1/64 s is below the velocity allocation in both fixtures;
no interval accuracy or trajectory safety follows from that partial check.

Measured nearby evaluations take 20.02372816693969-20.835984291974455 s,
distant evaluations 0.12361487513408065-0.12741362513042986 s. The preceding
uniform-degree-100 focused run took 167.48 s; this comparison does not prove
full-mission runtime. There are still four native inventory arcs, zero
portable inventory arcs, and no enlarged deadline or propagation limits.
The private diagnostic now reports source-specific `qualified_prefix_degrees`;
public interfaces, production fields, scientific tolerances and UI are unchanged.

Completion verification: all 1426 project tests passed in 378.48 s. Ruff,
strict OpenSpec validation and diff checks passed. The legacy SHA-256 is
unchanged and the package does not import it. Suite duration is separate
from the unchanged 300-second mission deadline. Task 3.9 remains open.

Task 3.9 degree-100 qualification and cost (2026-09-12):
Extend the existing prefix oracle and composed full-force bound through
degree 100 without changing production fields or tolerances. Add degrees
50/100 to the independent polar matrix/source-perturbation checks. Verify
all term comparisons under the shared deadline, measure evaluator cost,
run focused/full pytest, Ruff, strict OpenSpec and legacy checks. Keep 3.9
open; neither a small anchor bound nor a completed inventory permits targeting.

Focused verification: 47 tests passed in 167.48 s. All 41,208 term vectors
(5151 terms, two sources, four existing controls) meet the unchanged gate.
The 45 analytic perturbation combinations include 18 new degree-50/100
controls. Additional-prefix SPK/PCK/arithmetic L2 error bounds are
2.8315355138753893e-11 m/s^2 for the near-Moon lunar field and
1.2817684204623578e-11 m/s^2 for the near-Mars Martian field. The complete
conditional initial-force bounds are 9.090490153088587e-5 m/s^2 and
1.6433030933895662e-6 m/s^2 respectively, identical across both profiles.
Multiplying only the anchor bound by 1/64 s remains above 1e-6 m/s near
the Moon and below it near Mars; this does not bound time variation or
prove the velocity gate for either trajectory.

Each generic evaluation took 10.599210041109473-21.467858250020072 s.
The same four native arcs are counted; no extra arcs, dependencies, settings,
deadline changes or production/UI edits. Representative full-mission and
higher-degree qualification costs remain unresolved.

Completion verification: all 1417 project tests passed in 427.88 s. Ruff,
strict OpenSpec validation and diff checks passed. The legacy SHA-256 is
unchanged and the package does not import the educational model. Full-suite
wall time is not the per-mission 300-second budget; no budget was enlarged.
Task 3.9 remains open.

Task 3.9 conditional degree-20 prefix composition (2026-09-12):
Extend native per-term parity through degree 20, then compose the additional
degrees 1 and 3-20 with existing PCK-matrix and SPK-position bounds. Replace
only the old remainder partition in a separately reported complete initial
force envelope. Verify analytic polar shift/dilation controls at degrees
3, 8 and 20, all native term gates, tighter-than-old composition, focused/full
pytest, Ruff, strict OpenSpec and unchanged legacy checks. Keep 3.9 open.

Focused verification: 49 tests passed in 33.73 s, including 27 new analytic
composition controls and both inventories. All 1848 native vectors (231
terms, two sources, four existing controls) meet the unchanged force gate.
The additional prefix's combined L2 error bounds are
7.2372515077845795e-12 m/s^2 for the near-Moon lunar field and
6.289794678711191e-12 m/s^2 for the near-Mars Martian field. The complete
conditional initial-force bound drops from 0.016305005499436833 to
0.007732609670047144 m/s^2 near the Moon and from 0.012168297081840857 to
0.0030663443245067807 m/s^2 near Mars. Both profiles reproduce these values.
Even multiplying these bounds by the 1/64 s control duration exceeds the
1e-6 m/s velocity allocation; this is unresolved, not measured trajectory
error or permission to relax the gate. The old envelope remains a regression.

Each generic prefix evaluation took 0.07090216712094843 to
0.1239720000885427 s in the focused run, excluding other qualification work.
This does not establish degree-200/120 runtime or mission feasibility within
300 s. The focused run uses the same four native arcs and adds none; no
production, resource, native-call limit or UI changes.

Completion verification: all 1399 project tests passed in 285.15 s. Ruff,
strict OpenSpec and diff checks passed; the legacy SHA-256 remains unchanged
and the package does not import it. Full-suite duration is not a mission
runtime certificate. Task 3.9 remains open.

Task 3.9 normalized harmonic acceleration pilot (2026-09-12):
Reuse exact polynomial jets with geodesy normalization, radial factors and
stored-matrix projection. Verify monopole and degree-two independent oracles,
degree-three axis formulas, invalid inputs and expiry, then compare all
degree-zero-through-three terms with existing native output. Run focused/full
pytest, Ruff, strict OpenSpec and legacy checks; keep 3.9 open.

Focused verification: 22 tests passed in 32.61 s, including both inventories
and 20 new analytic/error controls. All 80 native term vectors meet the
unchanged force gate. The largest degree-three L1 error bounds are
1.7166233711916968e-19 m/s^2 for the near-Moon lunar field and
1.684109681893384e-19 m/s^2 for the near-Mars Martian field, identical across
the two integrator profiles. These are errors against exact stored states
and matrices, not total physical force errors. The four existing native arcs
are reused; there are no additional propagation calls. The full-force bound,
production model, tolerances and UI remain unchanged. High-degree normalized
force runtime and PCK/SPK composition remain unqualified.

Completion verification: all 1372 project tests passed in 287.68 s. Ruff,
strict OpenSpec validation and diff checks passed. The legacy SHA-256 stays
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`,
and the package does not import the legacy model. Suite duration is not a
300-second mission-runtime certificate; task 3.9 remains open.

Task 3.9 exact solid-harmonic polynomial kernel (2026-09-12):
Implement a streamed Fraction recurrence for unnormalized regular solid
harmonics and Cartesian first derivatives, with positive sectoral phase
and deadline checks. Verify every value/gradient through degree eight
against independently expanded Rodrigues/binomial polynomials, both poles
through degree 200, nonpolar homogeneity through degree 200, invalid inputs
and mid-stream expiry. Measure cost before force integration; run focused
and full pytest, Ruff, strict OpenSpec and legacy checks. Keep 3.9 open.

Focused verification: 10 tests passed in 26.42 s. The nonpolar degree-200
stream produced 20,301 complex value/gradient pairs in 25.109488375019282 s,
with exact integer components up to 12,076 bits; all homogeneity checks pass.
Each polar stream also covers 20,301 pairs; the three degree-eight controls
each compare 45 pairs exactly against the independent expansion. Before
adding the nonpolar measurement, nine controls passed in 1.31 s. Neither
focused invocation propagated a spacecraft. Only two preceding degree rows
plus the current row are retained, not all polynomial values.

This kernel is not normalized gravity, a Tudat parity result, or a bound
on the complete field's native arithmetic. The conservative initial force
envelope is unchanged. A 25-second scalar-point polynomial measurement
does not establish feasibility of repeated full-force certification within
the mission's 300-second deadline. Production, limits and UI are unchanged.

Completion verification: all 1352 project tests passed in 287.52 s. Ruff,
strict OpenSpec, diff checks and the unchanged legacy SHA-256 passed.
The full suite includes the existing four native inventory arcs; the new
polynomial controls add none. Suite wall time is not a mission-runtime
certificate and task 3.9 remains open.

Task 3.9 diagnostic harmonic-tail sweep (2026-09-12):
Measure hypothetical remainders after degree prefixes 2,5,10,20,50,100,120,
150 up to each model ceiling, also including the ceiling. Reuse the existing
bound and saved native terms with one exact summation cursor; verify prefix
filtering, zero remaining sum, non-mutation, invalid cutoffs and deadlines.
Keep the original full-force envelope unchanged. Run both inventories,
focused/full pytest, Ruff, strict OpenSpec and legacy checks; keep 3.9 open.

Focused verification: 16 tests passed in 32.77 s. An earlier coarse sweep
passed in 32.29 s; each invocation used four native arcs, including the
superseded coarse run. Prefix-tail bounds for the local body (m/s^2):

| Excluded through degree | Near-Moon lunar tail | Near-Mars Martian tail |
|---|---|---|
| 50 | 0.0016033175640343855 | 0.00015999384208418237 |
| 100 | 9.090473165602382e-5 | 1.643003417723087e-6 |
| 120 | 2.9133575949243407e-5 | 0 (model ceiling) |
| 150 | 4.824331142727141e-6 | Not in the declared model |

At h=1/64 s, the lunar tail contribution after degree 100 alone exceeds
1e-6 m/s, while after 120 it is about 4.55e-7 m/s; the Martian tail after
100 contributes about 2.57e-8 m/s. These are hypothetical tail-only budgets,
not proof that either prefix is qualified, sufficient, or minimal. Temporal
force variation and other contributions remain. Both native profiles agree;
the complete initial force bounds stay exactly 0.016305005499436833 and
0.012168297081840857 m/s^2. No production truncation, tolerance, limit or
model changes; counts remain (4,4,4) or (0,0,0) per inventory variant.

Completion verification: all 1342 project tests passed in 259.80 s, including
another four native inventory arcs. Ruff, strict OpenSpec, diff checks and
the unchanged legacy SHA-256 passed. This additional diagnostic work consumes
the existing shared deadline; no timer is reset and suite time is not a
mission-runtime certificate. Task 3.9 remains open.

Task 3.9 conservative complete initial force envelope (2026-09-12):
Partition Moon/Mars fields into degrees zero, two and the remainder; bound
unqualified remainder error by the exact saved-remainder L1 norm plus the
existing ideal norm at the SPK-error chord floor. Compose all force errors
and both assembly levels once. Verify degree-one/three polar oracles,
degree-two exclusion, non-mutation, deadline rejection, both inventories,
full pytest, Ruff, strict OpenSpec and legacy checksum. Do not claim that
finite bounds are sufficiently narrow; task 3.9 remains open.

Focused verification: 10 tests passed in 30.55 s. Complete conditional
initial force-error bounds are 0.016305005499436833 m/s^2 near Moon and
0.012168297081840857 m/s^2 near Mars, identical for both profiles. Local
harmonic remainders dominate at 0.016305005357877322 and
0.012168296794982873 m/s^2 respectively. This conservative triangle bound
does not establish a large actual error. Its E*h contribution alone at
h=1/64 s is about 2.55e-4 / 1.90e-4 m/s, above the unchanged 1e-6 m/s
velocity allocation; it cannot resolve that first-order endpoint enclosure.
Sharper remaining-order arithmetic bounds are needed, not looser tolerances.
The focused inventory used four native arcs; controls/evaluations/arcs
remain (4,4,4) or (0,0,0), with no production settings or limits changed.

Completion verification: all 1336 project tests passed in 257.21 s, including
another four native inventory arcs. Ruff, strict OpenSpec, diff checks and
the unchanged legacy SHA-256 passed. Passing tests verify the conservative
bound and reproduce its excessive width; they do not satisfy the mission
accuracy/runtime gate or complete task 3.9.

Task 3.9 initial Schwarzschild/SPK-state error composition (2026-09-12):
Carry the qualified Sun velocity error into the existing coast controls;
combine independent spatial/velocity Jacobian norm bounds with Sun position
and velocity errors, then add the native arithmetic enclosure. Prove the
chord's distance floor and relative-speed cap without rounding subtraction.
Verify radial-position and radial/transverse-velocity exact oracles, zero
error, invalid domains, both inventories, full pytest, Ruff, strict OpenSpec
and the legacy checksum. Keep 3.9 open and all scientific gates unchanged.

Focused verification: 20 tests passed in 30.23 s. The conditional Sun
velocity error is 6.9538963374104784e-15 m/s. Combined initial Schwarzschild
Euclidean error bounds are 1.3414766729191487e-25 m/s^2 near Moon and
1.6302658872133053e-26 m/s^2 near Mars, identical for both profiles.
Controls/evaluations/arcs remain (4,4,4) or (0,0,0); four native arcs ran in
the focused inventory. These bounds concern conditional SPK arithmetic
and the fixed initial spacecraft state, not physical uncertainty or uniform
trajectory accuracy. Production, resources, limits and UI are unchanged.

Completion verification: all 1328 project tests passed in 256.49 s; the
full suite reran the four native inventory arcs. Ruff, strict OpenSpec,
diff checks and the unchanged legacy SHA-256 passed. Full-suite timing
does not qualify a mission run; task 3.9 remains open.

Task 3.9 initial SRP/source-position error composition (2026-09-12):
Reuse exact apparent-disc geometry with spheres enlarged by source-position
error radii; verify strict clearance, tangency, observer-inside-enlargement,
translation and invalid-input controls. Only after proving full light for
every position ball, combine the native SRP arithmetic enclosure with
`2*K_upper*E/d^3`, using the existing pi and point-force bounds. Verify radial
source-shift/area-scaling oracles, both native inventories, full pytest,
Ruff, strict OpenSpec and the unchanged legacy checksum. Keep 3.9 open.

Focused verification: 36 tests passed in 30.09 s. All 12 Sun/occultor pairs
in the four existing coast controls remain strictly clear after enlargement
by the conditional SPK errors. The combined initial SRP Euclidean error
bounds are 1.6427511986196103e-23 m/s^2 near Moon and
2.578720215592348e-24 m/s^2 near Mars, identical for both profiles. Native
controls/evaluations/arcs remain (4,4,4) or (0,0,0) by inventory; all four
focused arcs count as work. These are conditional numerical bounds at one
epoch with fixed spacecraft position/mass, not full-mission illumination,
physical uncertainty or a new tolerance. Production settings are unchanged.

Completion verification: all 1310 project tests passed in 257.04 s; the
full suite also reran four native inventory arcs. Ruff, strict OpenSpec,
diff checks and the unchanged legacy SHA-256 passed. Suite runtime is not
a mission-runtime qualification; no production limits or UI changed.

Task 3.9 initial SPK-position/gravity error composition (2026-09-12):
Pass each qualified initial source-position enclosure into the existing
coast controls, verify endpoint/core provenance before handoff, and prove
positive comparison-chord floors. Combine point-force arithmetic with
`2*GM*E/d^3` for all eight monopoles, and degree-two arithmetic/PCK error
with the existing harmonic Jacobian times E. Verify independent radial
quadrupole source-shift oracles and prior point-force controls; run both
inventories, full pytest, Ruff, strict OpenSpec and legacy checks. Keep all
native arithmetic gates and scientific tolerances unchanged; 3.9 stays open.

Focused verification: 22 tests passed in 29.98 s. Initial source-position
bounds span 1.4595070471278306e-7 m (Sun) to 7.284371515436439e-4 m
(Saturn). Near-Moon lunar monopole and degree-two combined error bounds are
1.4123540242346412e-10 and 3.211210370276435e-13 m/s^2; near-Mars Martian
bounds are 2.811771855495014e-10 and 5.677804516507641e-12 m/s^2.
Both native profiles report identical values. These are conditional upper
bounds relative to ideal pinned SPK/PCK models, not observed physical errors
or a new tolerance allocation. Controls/evaluations/arcs remain (4,4,4) or
(0,0,0); the focused run used four native arcs. No extra propagation or new
helper abstraction was added; the existing distance and force bounds suffice.

Completion verification: all 1290 project tests passed in 256.72 s; the
full suite reran the four native inventory arcs. Ruff, strict OpenSpec,
diff checks and the unchanged legacy SHA-256 passed. Full-suite wall time
does not qualify the mission runtime; production settings/limits/UI remain
unchanged and task 3.9 remains open.

Task 3.9 degree-two force/PCK error composition (2026-09-12):
Bound the effect of a stored, potentially nonorthogonal rotation matrix
using the already qualified force/Jacobian bounds on a proven chord floor.
Compose that bound with all three degree-two order-wise arithmetic errors.
Verify quadrupole dilation/contraction, radius scaling, proper rotation,
monopole non-invariance under dilation, invalid inputs and deadline rejection;
reuse the four native coast controls. Run focused/full pytest, Ruff, strict
OpenSpec and legacy checks. Do not claim a full harmonic-field, ephemeris or
trajectory certificate; task 3.9 remains open.

Focused verification: 20 tests passed in 30.19 s, including both inventories.
The exact sum of the three saved order vectors has an initial Euclidean error
bound against the ideal PCK-oriented degree-two field of
1.7737236576742766e-15 m/s^2 for near-Moon lunar gravity and
2.2845795288621046e-13 m/s^2 for near-Mars Martian gravity. Distant-body
bounds are respectively 1.7668792988230888e-32 (Mars near Moon) and
8.438684083285713e-36 m/s^2 (Moon near Mars). Both integrator profiles give
identical bounds. These conservative bounds are not measured force errors;
no new mission allocation or relaxed tolerance is introduced. In particular,
the old 1e-15 m/s^2 stored-matrix arithmetic gate is not a gate for the new
orientation-inclusive error. Controls/evaluations/arcs remain (4,4,4) or
(0,0,0) per inventory variant; all four focused native arcs count as work.

Completion verification: all 1278 project tests passed in 256.68 s, including
another four native inventory arcs. Ruff, strict OpenSpec, diff checks and
the unchanged legacy SHA-256 passed. The full-suite runtime is not a mission
runtime qualification. Production settings, limits and UI are unchanged.

Task 3.9 initial PCK rotation-matrix arithmetic (2026-09-12):
Reuse the pinned angle intervals and saved native rotations to enclose all
nine entries of `R3(PM) R1(90 deg - DEC) R3(90 deg + RA)`. Verify exact-axis,
composition, perturbed, irrational-diagonal, finite-width and rejection
oracles; preserve all five PCK resource controls. Report outward entry-L1
errors and check deadlines without adding spacecraft arcs. Verify focused
and full pytest, Ruff, strict OpenSpec and the unchanged legacy checksum.
This is an initial ideal-PCK matrix bound, not physical uncertainty or a
full-force/trajectory certificate; task 3.9 remains open.

Focused verification: 17 tests passed in 30.63 s, versus 76.89 s before
outward 120-bit dyadic rounding of trig endpoints. Containment is asserted
exactly; this computational precision is not a scientific tolerance.
All four native controls report identical dimensionless entry-L1 bounds:
Moon 2.31447111066898e-13 and Mars 1.6056874336998682e-12, unchanged at
reported precision by optimization. Controls/evaluations/arcs remain
(4,4,4) or (0,0,0) per inventory variant. Both focused invocations actually
ran four native arcs each; no discarded work is treated as free. No
production settings, physical resources, limits or public APIs changed.

Completion verification: all 1260 project tests passed in 256.89 s; Ruff,
strict OpenSpec validation and diff checks passed. The legacy SHA-256 is
unchanged and production does not import the legacy module. The full suite
also reran the four-control inventory; its total wall time is not evidence
of a complete mission satisfying the shared 300-second budget.

Task 3.9 initial PCK Euler-angle arithmetic (2026-09-10):
Evaluate the six initial Euler angles from pinned polynomial/periodic data
with rational sine/cosine and pi enclosures. Verify quadrant, diagonal,
large-turn and invalid-input oracles; preserve all five resource-rejection
controls and report outward radian bounds against BODEUL after wrap checks.
Run focused/full pytest, Ruff, strict OpenSpec and legacy checksum. Do not
allocate a new angular mission tolerance, infer a full-matrix certificate
or add spacecraft arcs; task 3.9 remains open.

Verification: 15 focused tests passed (29.86 s), including both inventories
and all resource-rejection controls; all 1250 project tests passed (255.89 s).
The largest observed angle-error enclosure is Mars PM at
5.055961329794478e-13 rad; both inventory variants reproduce all six bounds.
Ruff, strict OpenSpec and the unchanged legacy SHA-256 pass. Native spacecraft
controls/evaluations/arcs remain (4,4,4) or (0,0,0) by variant; two BODEUL
readbacks per inventory do not propagate a spacecraft or change the model.

Task 3.9 complete harmonic term assembly readback (2026-09-10):
Request 20,301 Moon and 7,381 Mars term vectors in the four existing coast
controls. Verify finite dimensions, stable degree/order mapping against the
separately qualified terms, and exact-Fraction component sums against the
native full fields within the existing assembly force gate. Report only
counts and outward residuals; check the shared deadline around processing.
Run both focused inventory variants, complete pytest, Ruff, strict OpenSpec
and legacy checksum, recording runtime without changing limits. This is
assembly consistency, not full-field accuracy; task 3.9 remains open.

Verification: both focused inventory variants passed (28.90 s); all 1242
project tests passed (254.78 s). Each of four controls reads 27,682 harmonic
vectors; selected low-degree entries are exactly equal to prior outputs.
Maximum observed L1 assembly residual is 2.847930732105142e-15 m/s^2, within
the unchanged norm-scaled gate (not its absolute floor alone). Ruff, strict
OpenSpec and the legacy SHA-256 pass. Native controls/evaluations/arcs remain
(4,4,4) or (0,0,0) by variant; no production limits or settings were changed.

Task 3.9 all degree-two orders at a stored rotation (2026-09-10):
Generalize the existing C20 Cartesian enclosure to orders 0/1/2 without
duplicating its arithmetic. Append native C21/S21 and C22/S22 vectors in the
same four coast runs; require all 24 order-wise bounds <=1e-15 m/s^2.
Verify independent cosine/sine, signs, rotated/translated/reversed vectors,
mixed coefficients and invalid orders, retaining all C20 tests and diagnostics.
Run focused/full pytest, Ruff, strict OpenSpec and legacy checksum. Keep
native counts and settings unchanged; summed degree-two, ideal rotation and
full harmonic errors remain unqualified, and task 3.9 stays open.

Verification: 34 focused tests passed (28.57 s), followed by four invalid
order/S20 checks (0.24 s); all 1242 project tests passed (254.53 s). All 24
degree-two order vectors meet 1e-15 m/s^2. New order-1/order-2 maxima are
2.1830285905683608e-23 / 2.339400995609037e-19 m/s^2; C20 bounds are unchanged.
Ruff, strict OpenSpec and the unchanged legacy SHA-256 pass. Native controls/
evaluations/arcs remain (4,4,4) or (0,0,0) by variant, with no production changes.

Task 3.9 C20 arithmetic at a stored rotation (2026-09-10):
Read Moon/Mars C20 vectors and inertial-to-fixed matrices in the four existing
coast runs. Verify row-major direct-SPICE matrix parity, S20=0 and an exact
Cartesian C20 gradient enclosure at the stored matrix within 1e-15 m/s^2.
Check independent pole/equator, both coefficient signs, rotated/translated
and reversed-observation controls, irrational radius, zero and invalid inputs.
Run focused/full pytest, Ruff, strict OpenSpec and legacy checksum. Preserve
all previous gates/counts; do not infer ideal-PCK or full harmonic error.
Task 3.9 remains open.

Verification: 13 focused tests passed (28.42 s), including both SPK inventory
variants; all 1220 project tests passed (257.59 s). The eight C20 observations
have stored-matrix reference bounds <=3.3644477105573347e-18 m/s^2, identical
between integrator profiles. Matrix parity, Ruff, strict OpenSpec and the
unchanged legacy SHA-256 pass. Native controls/evaluations/arcs remain
(4,4,4) or (0,0,0) by variant; production settings and tolerances are unchanged.

Task 3.9 harmonic degree-zero anchor enclosure (2026-09-10):
Append Moon/Mars `(0,0)` acceleration outputs to the four existing native
coast controls without replacing their full harmonic models. Verify C00/S00,
finite output dimensions and inertial direction using the existing exact
point-force error enclosure and force gate; report eight outward L1 bounds.
Rerun the independent point-force controls, both SPK inventory variants,
complete pytest, Ruff, strict OpenSpec and legacy checksum. Preserve native
counts, production settings and every previous gate; higher-degree and full
harmonic errors remain unqualified, so task 3.9 stays open.

Verification: 10 focused tests passed (28.63 s), including both SPK inventory
variants; all 1209 project tests passed (254.49 s). The eight degree-zero
observations have error bounds <=4.981248128809384e-16 m/s^2, identical
between nominal/tighter profiles. Ruff, strict OpenSpec and the unchanged
legacy SHA-256 pass. Native controls/evaluations/arcs remain (4,4,4) or
(0,0,0) by variant, with no production or scientific-setting changes.

Task 3.9 fully lit SRP initial anchor enclosure (2026-09-10):
Bound the four native SRP observations only after their exact clear-disc
proofs, using rational pi and root enclosures with explicit SI inputs.
Verify Machin identity/width, signed exact geometry, translation, corrupted
vectors, parameter scaling, irrational radius and invalid mass; require
outward L1 bounds <=1e-15 m/s^2. Run focused/full pytest, Ruff, strict
OpenSpec and legacy checksum. Keep all prior gates and native counts;
neither penumbra nor complete acceleration/trajectory error is qualified.
Task 3.9 remains open.

Verification: all 11 focused tests passed (27.59 s), including both SPK
inventory variants; all 1209 project tests passed (253.37 s). Four native
SRP observations have L1 error bounds <=1.6307362146447312e-23 m/s^2, with
identical nominal/tighter values per centre. Ruff, strict OpenSpec and the
unchanged legacy SHA-256 pass. Native controls/evaluations/arcs remain
(4,4,4) or (0,0,0) by variant; production physics and tolerances are unchanged.

Task 3.9 exact initial clear-disc geometry (2026-09-10):
Prove disjoint apparent Sun/occultor discs at exact stored initial positions
and native spherical radii using rational sign and squared inequalities.
Verify tangent/separated/overlap/opposite cases, translation and invalid
geometry. Append a shadow output to the four existing native runs; require
three independent clear-disc proofs per anchor, direct shadow parity within
1e-12 and saved combined illumination exactly 1. Run focused/full pytest,
Ruff, strict OpenSpec and legacy checksum. Preserve counts and all previous
gates; neither interval illumination nor SRP error is yet qualified, and
task 3.9 remains open.

Verification: 16 focused tests passed (27.63 s), including both SPK inventory
variants; all 1200 project tests passed (253.40 s). All 12 native-anchor
Sun/occultor pairs have exact disjoint-disc proofs, direct shadow parity
passes, and all four saved combined shadow factors equal 1. Ruff, strict
OpenSpec and the unchanged legacy SHA-256 pass. Native controls/evaluations/
arcs remain (4,4,4) or (0,0,0) by variant, with no production changes.

Task 3.9 Schwarzschild initial anchor enclosure (2026-09-10):
Reuse the dyadic root enclosure to bound the four observed native
Schwarzschild vectors at exact stored SI Sun-relative states and PPN=1.
Verify exact radial/transverse/mixed controls, translated states, corrupted
vectors, irrational radius, singular and non-finite input; require outward
L1 bounds <=1e-15 m/s^2 and retain point-gravity regressions. Run focused/full
pytest, Ruff, strict OpenSpec validation and the legacy checksum. Keep
native counts and production settings unchanged; task 3.9 stays open.

Verification: 21 focused tests passed (27.59 s), including both inventory
variants and all earlier point-anchor controls; all 1186 project tests passed
(253.30 s). The four native Schwarzschild bounds are <=1.311646303961854e-25
m/s^2, with identical nominal/tighter results. Ruff, strict OpenSpec and the
unchanged legacy SHA-256 pass. Native controls/evaluations/arcs remain
(4,4,4) or (0,0,0) by variant. No production or scientific settings changed.

Task 3.9 point-gravity initial anchor enclosure (2026-09-10):
Bound each observed point-force vector against the ideal force at exact
stored GM/position inputs using Fraction arithmetic and integer-sqrt dyadic
enclosures. Verify rational and irrational geometry, translation, perturbed
observations, extreme scales and singularity; retain the 24 native parity
checks and require outward L1 bounds within the unchanged force gate.
Run focused/full pytest, Ruff, strict validation and the legacy checksum.
Do not add native arcs or infer a complete acceleration-anchor certificate;
task 3.9 remains open.

Verification: all 10 focused checks passed (27.43 s), including both SPK
inventory variants; all 1175 project tests passed (253.17 s). The largest
per-source L1 bound is 2.154025085051632e-18 m/s^2, with identical
nominal/tighter observations. Ruff, strict OpenSpec validation and the legacy
SHA-256 pass. Native controls/evaluations/arcs remain (4,4,4) or (0,0,0)
by variant, and no production tolerances, kernels or settings changed.

Task 3.9 native initial acceleration readback (2026-09-10):
Add total and ten component acceleration outputs to the four existing native
coast controls. Verify exact native initial epoch, finite dimensions, exact
component summation within the unchanged force gate, independent point-force
vectors and identical nominal/tighter initial acceleration. Run focused/full
pytest, Ruff, strict validation and legacy checksum. Retain all prior gates
and counters; do not promote assembly consistency into an ideal-anchor error
certificate or complete 3.9.
The first attempt reproduced the native-Time binding incompatibility before
propagation (one inventory passed, one failed in 25.85 s). After retaining
that rejection and using constructor-time output settings, both focused
inventories passed (27.40 s) and all 1167 full-suite tests passed (253.13 s).
Four initial readbacks and 24 independent point-force checks pass; maximum
observed component-sum L1 residual is 1.4418908130884947e-16 m/s^2, not an
ideal-anchor error bound. Ruff, strict validation and the legacy SHA-256
pass; native controls/evaluations/arcs remain (4,4,4) or (0,0,0) by variant.

Task 3.9 conditional complete coast force-variation sum (2026-09-10):
Combine six point-source changes and two harmonic spatial/rotation pairs,
plus twice the SRP and relativity norm bounds with exactly zero coast thrust.
Verify exact aligned-vector controls, zero and non-dyadic sums, inventory
and negative-input rejection, outward reports, and all four existing trial
domains. Run focused/full pytest, Ruff, strict validation and legacy checksum.
Keep the 1 s inclusion failure, native counts and unresolved velocity evidence;
do not claim a qualified native acceleration anchor or complete mission error.
All eight focused checks passed (27.77 s), and all 1167 full-suite tests
passed (256.82 s). Both inventory variants reproduce short-domain total
variation bounds 0.005024646481491329 m/s^2 (Moon) and
0.004792798636344572 m/s^2 (Mars), with unchanged inclusion classifications.
Ruff, strict OpenSpec validation and the unchanged legacy SHA-256 passed;
native controls/evaluations/arcs remain (4,4,4) or (0,0,0) by variant.

Task 3.9 conditional angle-limited harmonic rotation (2026-09-10):
Compose the nonmonopole force/Jacobian bounds, relative-radius upper bound
and qualified ideal PCK angular path as min(2*B,Theta*(B+H*r_max)). Verify
exact rational quadrupole rotations, zero/small/global-cap branches, monopole
cancellation and invalid inputs. Report tighter bounds for both harmonic
fields on the four existing trial domains; preserve all coarse controls.
Run focused/full pytest, Ruff, strict validation and legacy checksum. Add no
native arcs; leave native arithmetic and complete trajectory error unqualified.
All six focused controls passed (27.47 s), and all 1161 full-suite tests
passed (253.08 s). Both inventory variants reproduce the tighter bounds;
dominant short-domain rotation contributions are 2.696904664414131e-8 m/s^2
(Moon) and 4.818121087323815e-7 m/s^2 (Mars). These are ideal component
bounds, not measured trajectory errors. Ruff, strict OpenSpec validation and
the unchanged legacy SHA-256 passed; native control/evaluation/arc counts
remain (4,4,4) or (0,0,0) by variant.

Task 3.9 conditional text-PCK angular-path bounds (2026-09-10):
Pin the selected Moon/Mars orientation coefficients and reject incompatible
binary/frame/phase/epoch overrides. Derive a uniform ideal Euler-rate bound
with explicit day/century scales and both periodic degree conversions; verify
signed quadratic, sinusoidal, zero and invalid-unit controls. Sum unit-axis
Euler rates to bound angular path length and compare 26 native state-transform
readbacks over the candidate window. Report angles for existing trial domains,
run focused/full pytest, Ruff, strict validation and legacy checksum. Keep
native roundoff and force-cap composition conditional/unqualified; do not
increase native arcs or close 3.9.
Six focused formula/inventory checks passed (25.73 s), followed by five
injected source-rejection checks (0.30 s). All 1157 full-suite tests passed
(251.02 s). Both inventory variants reproduce the short-interval angular
path bounds 4.181611885677073e-8 rad (Moon) and 1.1079798691355498e-6 rad
(Mars). Ruff, strict OpenSpec validation and the unchanged legacy SHA-256
passed. Each inventory adds 26 native orientation readbacks, but spacecraft
control/evaluation/arc counts remain (4,4,4) or (0,0,0) by variant.

Task 3.9 conditional arbitrary-rotation harmonic cap (2026-09-10):
Bound any two ideal field orientations by twice the nonmonopole acceleration
norm, retaining exact monopole cancellation. Verify unchanged coefficients,
three pure monopoles, signed analytic quadrupole rotations, cap arithmetic
and expired-budget rejection. Report both pinned-field caps in the existing
four trial domains without additional native arcs. Run focused/full pytest,
Ruff, strict validation and legacy checksum. Keep the cap's lack of angular
or elapsed-time sharpness explicit; do not claim native/full-trajectory error
qualification or close 3.9.
All eight focused controls passed (26.00 s) and all 1148 full-suite tests
passed (251.58 s). Both inventory variants reproduce the caps: dominant
closed-domain components are 0.034304352174851255 m/s^2 (Moon) and
0.064255605448081 m/s^2 (Mars). These are worst-orientation bounds, not
observed force changes. Ruff, strict OpenSpec validation and the unchanged
legacy SHA-256 passed. Native counts remain (4,4,4) or (0,0,0) by variant.

Task 3.9 conditional frozen-orientation harmonic variation (2026-09-10):
Derive the harmonic spatial Jacobian bound using the Laplacian of the
gradient addition identity. Verify independent Cartesian Hessian identities,
single-degree radial derivatives through degree 200, directed coefficient
weights, zero fields and deadline rejection. Reuse the existing gravity norm
helper with bound-only weights and report the two frozen-orientation field
variations on all four trial domains. Run focused/full pytest, Ruff, strict
validation and legacy checksum. Add no native arcs and do not claim coverage
of time-varying rotation or a complete force/trajectory-error certificate.
All 12 focused checks passed (25.51 s), and all 1142 full-suite tests passed
(250.74 s) after explicitly naming the Jacobian units s^-2. Both inventory
variants reproduce the frozen-field bounds. The dominant closed-domain
components are 0.005024341840953305 m/s^2 (Moon) and
0.004792226927804076 m/s^2 (Mars), excluding rotation between epochs.
Ruff, strict OpenSpec validation and the unchanged legacy SHA-256 passed;
native controls/evaluations/arcs remain (4,4,4) or (0,0,0) by variant.

Task 3.9 conditional point-mass acceleration variation (2026-09-10):
Derive 2*GM*D/d^3 from the point-gravity Jacobian on a nonsingular comparison
chord. Verify exact inward/outward/zero radial changes, GM scaling, rational
transverse motion and singular-floor rejection. Compose the existing trial
balls and distance floors for all six point sources using native GMs and
outward report rounding; preserve the unresolved 1 s domain distinction.
Run focused/full pytest, Ruff, strict validation and legacy checksum. Add no
native arcs; do not claim harmonic/full-force/trajectory error qualification.
All ten focused controls passed (23.83 s), and all 1132 full-suite tests
passed (249.02 s). Both inventory variants reproduced the six-source bounds;
the largest component bound in the closed Moon domain is Earth's
2.2087972387894688e-8 m/s^2, and in the closed Mars domain the Sun's
1.731174197972173e-11 m/s^2. These exclude Moon/Mars harmonic forces.
Ruff, strict OpenSpec validation and the unchanged legacy SHA-256 passed;
native control/evaluation/arc counts remain (4,4,4) or (0,0,0) by variant.

Task 3.9 conditional coast velocity certificate limitation (2026-09-10):
Derive the endpoint velocity bound from exact velocity increment plus A*h.
Verify constant-acceleration equality, zero duration/acceleration, and an
exact endpoint whose conservative bound remains unresolved. Measure all
four existing native coast endpoints without new native calls; record the
unresolved 1e-6 m/s local target separately from passing position bounds.
Run focused/full pytest, Ruff, strict validation and legacy checksum.
Keep 3.9 open; this diagnoses the enclosure method, not actual native error.
All seven focused checks passed (24.24 s), followed by all 1124 full-suite
tests (249.38 s). The four native velocity bounds remain above the local
target while their position certificates still pass. Ruff, strict OpenSpec
validation and the unchanged legacy SHA-256 passed. Native counts remain
four controls/evaluations/arcs in the native inventory and zero in the other.

Task 3.9 conditional native coast endpoint position certificate (2026-09-10):
Bound a saved endpoint using its exact ballistic residual plus A*h^2/2 from
the closed ideal domain. Verify independent constant-acceleration controls
reject corrupted endpoints. Run four near-Moon/Mars native coast controls
with unchanged nominal/tighter profiles, exact native endpoint epoch, initial
state and coast-mass checks; require the conditional position bound <=0.001 m.
Count four native arcs in the existing inventory budget; run focused/full
pytest, Ruff, strict validation and legacy checksum. Do not claim velocity,
accumulated error, internal-trial safety or completed task 3.9.
The four initial focused controls passed (23.83 s), and all three final
analytic residual controls passed (0.18 s). All 1119 full-suite tests passed
(248.97 s), including the four native endpoint bounds, whose maximum is
0.0008134678012758771 m. Ruff, strict validation and the unchanged legacy
SHA-256 passed; native qualification counts are (4,4,4) in the native variant.

Task 3.9 conditional full-force coast phase inclusion (2026-09-10):
Compose existing source-motion and Sun-speed envelopes with full-force
position/velocity domains near Moon and Mars at the qualified start epoch.
Verify matching source anchors, all eight distance floors, constant coast
mass, outward force summation, strict short-interval inclusion and unresolved
longer intervals. Reuse pinned physical fields and preserve the shared budget
with zero spacecraft propagations. Run focused/full pytest, Ruff, strict
validation and legacy checksum. This is an ideal-ODE control conditional on
source premises, not a native trajectory-error/safety certificate; keep 3.9 open.
Both focused inventory/domain controls passed (23.64 s), with short Moon/Mars
inclusion and unresolved 1 s controls. All 1116 full-suite tests passed
(249.47 s), as did Ruff, strict validation and the unchanged legacy SHA-256.

Task 3.6 per-native-arc PPN guard (2026-09-10):
Reproduce missing native-entry/continuation resets on the previous runner;
restore and read back beta/gamma immediately before each native call while
retaining the force-builder guard. Verify setup failure/timeout starts no
native arc and preserves error causes, and three continuations reset/count
correctly. Poison PPN after model construction in all 24 existing combined
force arcs; require native readback and unchanged independent force oracles.
Run runner/gravity/relativity tests, full pytest, Ruff, strict validation and
legacy checksum. No new native qualification arcs or interval safety claim.
All 83 focused tests passed (47.66 s), including the late-poison native force
controls; all 1116 full-suite tests passed (229.35 s). Ruff, strict OpenSpec
validation and the unchanged legacy SHA-256 passed. Task 3.6 is complete;
3.4/3.5/3.7/3.9 and the remaining targeting prerequisites stay open.

Task 3.9 conditional chain velocity and SI rounding (2026-09-10):
Derive coefficient-based native velocity magnitudes for all 11 source links,
checking 3300 existing supplied-record states and exact values. Compose
source errors, center-chain addition and SI rounding for all eight bodies;
require every conditional error bound to stay within 1e-6 m/s. Verify sixteen
near-limit arithmetic controls and outward finite speed ceilings. Run focused/
full pytest, Ruff, strict validation and legacy checksum. Add no native calls;
preserve execution/selection premises, source-jump caveats and the open 3.9 gate.
Both focused inventory controls passed (21.60 s), including all 3300 native
states and sixteen arithmetic cases. All 1113 full-suite tests passed
(229.18 s), as did Ruff, strict validation and the unchanged legacy SHA-256.

Task 3.9 conditional uniform type-3 stored-velocity rounding (2026-09-10):
Reuse the unchanged fused series arithmetic with an explicit coefficient-unit
contract. Bound normalization and series rounding for all 297 type-3 velocity
records; verify all 1782 existing native observations against bitwise replay,
exact polynomials and the conditional bound under the unchanged 1e-6 m/s gate.
Verify six synthetic records distinguish stored velocity from differentiated
position and erroneous radius scaling. Preserve earlier controls; run focused/
full pytest, Ruff, strict validation and legacy checksum. No spacecraft runs,
production changes or interval safety status; keep execution premises and 3.9 open.
All 19 focused tests passed (22.32 s); the maximum type-3 conditional bound
is 1.7455876272338752e-11 m/s. All 1113 full-suite tests passed (228.46 s),
as did Ruff, strict OpenSpec validation and the unchanged legacy SHA-256.

Task 3.9 conditional uniform type-2 velocity rounding (2026-09-10):
Derive a forward error bound for the inspected CHBINT derivative operations,
including contamination by position rounding and final division. Compose
normalized-time uncertainty through exact second-derivative envelopes;
verify their independent Chebyshev identity. Require all 253 supplied-record
bounds and 1518 existing native observations to meet the unchanged 1e-6 m/s
gate. Verify single modes, underflow, invalid domains, overflow and deadline;
run focused/full pytest, Ruff, strict validation and legacy checksum. Add no
spacecraft runs or safety status; retain execution premises and keep 3.9 open.
All 16 focused tests passed (16.93 s); the maximum conditional record bound
is 7.95907147216062e-11 m/s. All 1107 full-suite tests passed (224.36 s),
as did Ruff, strict OpenSpec validation and the unchanged legacy SHA-256.

Task 3.9 type-2 native velocity arithmetic replay (2026-09-10):
Pin the inspected CHBINT derivative instructions and replay their rounding
order. Verify twelve native single-mode controls against the independent
Chebyshev derivative identity, then all 1518 existing type-2 supplied-record
queries against bitwise replay and exact differentiated polynomials within
1e-6 m/s. Add no native propagation or new record queries; preserve the
shared deadline and position controls. Run focused/full pytest, Ruff, strict
validation and legacy checksum. Sampled agreement does not supply a uniform
velocity-error bound or close 3.9.
All 15 focused tests passed (11.97 s), including 1518 supplied-record
velocity comparisons; all 1093 full-suite tests passed (218.79 s).
Ruff, strict OpenSpec validation and the unchanged legacy SHA-256 passed.

Task 3.9 full-force coupled mass-history qualification (2026-09-10):
Add near-Moon/departure and near-Mars/arrival 100.25 s coupled burns with
both production integrator profiles and full direct-SPICE forces. Verify
native-Time endpoint, finite seven-states, monotone sampled mass and the
exact constant-flow oracle under unchanged mass tolerance. Account for each
of four qualification arcs with the existing budget; return no safety or
targeting result. Run focused/full pytest, Ruff, strict validation and legacy
checksum; sampled full-force evidence does not complete 3.9/3.5.
All four focused cases passed (5.53 s), covering 238 saved states with a
maximum mass error of 3.2088692720365647e-12 kg against the unchanged
1e-8 kg absolute tolerance. All 1081 full-suite tests passed (218.09 s),
as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 native force controls across a Jupiter record join (2026-09-10):
Add two direct burn cases to the existing matrix, with explicit coverage
bracketing the known TDB 1003871232 source join. Verify callbacks before/at/
after the join, all prior source parity/force checks and unchanged per-case
native counters/deadline. Preserve original cases and tolerances; report
the added six qualification arcs, not a production limit revision. Run
gravity/full pytest, Ruff, strict validation and legacy checksum; retain
the representation-jump caveat and leave interval safety/3.9 unqualified.
All 40 gravity tests passed (24.05 s) and all 1077 full-suite tests passed
(181.13 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 finite thrust-callback source-state observations (2026-09-10):
Wrap the existing thrust callback in six direct short burn controls without
changing returned thrust. Verify cached source states against SPICE after
propagation, including callback epochs absent from saved outputs. Count NaN
calls separately without querying/fabricating states; retain all finite-data,
force, saved-output and native-budget checks. Run gravity/full pytest, Ruff,
strict validation and legacy checksum. Callback samples do not prove all-stage
or interval safety; keep 3.9 open and production unchanged.
All 38 gravity tests passed (16.51 s) and all 1075 full-suite tests passed
(163.91 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 native saved-output source-state parity (2026-09-10):
Observe cached source states in nine existing combined/direct force arcs,
extending only those isolated test arcs to 0.025 s at unchanged RK4 step.
Verify rounded-epoch SPICE parity for all eight bodies at saved native Time
outputs, including nonrepresentable float epochs; retain all original force
controls and native counters. Report counts and residuals. Run gravity/full
pytest, Ruff, strict validation and legacy checksum. Saved-output evidence
does not qualify every RK stage or interval safety; keep 3.9 open.
All 38 gravity tests passed (16.55 s) and all 1075 full-suite tests passed
(164.27 s), as did Ruff, strict validation and the unchanged legacy hash.
All 288 sampled source comparisons reported zero position/velocity differences;
this is parity of computed values, not a physical uncertainty bound.

Task 3.9 Python direct-ephemeris time boundary (2026-09-10):
Extend the existing production parity fixture with 64 native Time input
controls across eight bodies and two epochs, including a Saturn segment
junction. Verify rounding labels, identical Time/float state values and
unchanged direct-SPICE parity limits. Preserve the earlier comparisons,
shared deadline and zero native propagation count. Run environment/full
pytest, Ruff, strict validation and legacy checksum. This tests the Python
binding, not internal native dispatch or interval safety; keep 3.9 open.
All 44 environment tests passed (36.14 s) and all 1075 full-suite tests
passed (165.10 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 joint mass-dependent thrust domain control (2026-09-10):
Compose the existing mass/position bounds and speed inequality on exact
constant-thrust motion. Verify strict closure, equality-unresolved and
mass-domain exit despite contained position/speed, using an independent
T/m(h) global bound. Preserve zero native counters and production settings.
Run focused/full pytest, Ruff, strict validation and legacy checksum; do
not transfer analytic evidence to native full-force safety or close 3.9.
All 98 focused tests passed (0.07 s) and all 1075 full-suite tests passed
(163.92 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 conditional labelled-sample mass floors (2026-09-10):
Compose the existing mass-floor primitive with outward rate/duration inputs
and the checked native/float label shift. Verify all saved native samples
above the floor under the explicitly declared unchanged sample-error bound,
and preserve counterexamples when the timing allowance is omitted. Retain
all prior checks and native counters. Run focused/full pytest, Ruff, strict
validation and legacy checksum. Sample-error premises are not interval
certificates; keep 3.9/3.5 open and production safety unchanged.
All 102 focused tests passed (6.26 s) and all 1072 full-suite tests passed
(164.15 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 terminal native-time gate correction (2026-09-10):
Require native Time endpoint residuals in the shared completion reader,
retaining float-label consistency and the unchanged 1-microsecond limit.
Verify real Time offsets on both sides of the limit, native simulator
readback, missing/empty/nonfinite/inconsistent/failing native data and
existing completion/safety precedence. Run focused/full pytest, Ruff, strict
validation and legacy checksum. No public types, tolerances or integrators
change; this endpoint fix does not complete interval safety or task 3.9.
All 133 focused checks passed (6.67 s) and all 1072 full-suite tests passed
(163.85 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 high-resolution native time diagnosis (2026-09-10):
Reuse all 72 native histories and verify identical arrays/counts under native
Time and float epoch keys. Subtract Time objects before conversion, verify
the half-ULP epoch-label shift control and the unchanged mass tolerance for
every native-elapsed sample, retaining the 18 float-label counterexamples.
Report both residuals and label shifts. Run focused/full pytest, Ruff,
strict validation and legacy checksum. This diagnoses the sampled boundary
error without changing production or proving interval safety; keep 3.9 open.
All 72 focused controls passed (6.09 s) and all 1062 full-suite tests passed
(164.19 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 mission-epoch mass-history counterexample (2026-09-10):
Repeat the 36 isolated engine controls at the candidate start TDB epoch,
preserving the original zero-epoch cases. Verify exact endpoint durations,
saved-epoch elapsed-time oracles and all unchanged final-state checks.
Preserve the 18 shifted-epoch intermediate-mass failures as explicit
counterexamples without widening the tolerance; require no violations in
all remaining controls. Report peak-error epochs and exceedance counts.
Run focused/full pytest, Ruff, strict validation and legacy checksum. This
qualifies neither mission safety nor the cause/remedy; leave 3.9/3.5 open.
All 72 focused controls passed as regression/counterexample checks (5.98 s);
all 1062 full-suite tests passed (163.83 s), as did Ruff, strict validation
and the unchanged legacy hash. The 18 scientific failures remain unresolved.

Task 3.9 conditional interval mass floor (2026-09-10):
Add the private outward mass-floor primitive with explicit duration, rate
and mass-error enclosures. Verify exact constant/variable flow and coast,
sub-ULP/subnormal/negative bounds, unresolved-not-crossing, invalid inputs,
overflow and both deadline checks without native counter changes. Run
focused/full pytest, Ruff, strict validation and legacy checksum. The caller
must justify all enclosures before any safety use; keep 3.9/3.5 open.
All 30 focused tests passed (0.04 s); all 1026 full-suite tests passed
(162.39 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 saved native mass-history evidence (2026-09-10):
Reuse the 36 isolated native burns to compare every saved mass with exact
stored-input constant flow under the unchanged mass tolerance. Verify finite
states, nonincreasing mass and a rate-only-envelope counterexample in every
fixture; report sampled errors/counts as reproducible JSON. No additional
native propagations. Run focused/full pytest, Ruff, strict validation and
legacy checksum. Saved samples do not enclose stages or between-output
states; keep 3.9/3.5 open and production settings unchanged.
All 36 focused controls passed (3.29 s); all 996 full-suite tests passed
(160.88 s), as did Ruff, strict validation and the unchanged legacy hash.

Task 3.9 conditional mass-rate arithmetic evidence (2026-09-10):
Verify the two-operation normal round-to-nearest rate-error bound
`2u/(1-u)` with exact Fraction oracles for Isp 300/450 s and three adjacent
dry masses. Record the accepted-equality/exact-law shortfall counterexample
and the conditional whole-powered-interval mass margin. Verify all control
tests, full pytest, Ruff, strict validation and unchanged legacy checksum.
This is not native engine, integration or timing qualification; keep 3.9
and 3.5 unchecked and preserve production behavior and resource limits.
All 29 control tests and 996 full-suite tests passed (161.10 s for the full
suite), as did Ruff, strict OpenSpec validation and the unchanged legacy hash.

Task 3.9 mass-premise control-gate correction (2026-09-10):
Reproduce a 5.684341886080802e-14 kg shortfall hidden by rounded burn-duration
summation at exactly 1 kg/s. Preserve the existing mass-rate calculation but
compare remaining mass with dry mass using exact validated binary64 operands.
Verify below/equal/above threshold durations, all control tests, full pytest,
Ruff, strict validation and legacy checksum. Equality remains accepted and
no epsilon is added. Native mass-rate/integration error and full propagated
safety remain unqualified; do not close 3.9 or 3.5.
All 23 control tests and 990 full-suite tests passed (160.56 s for the full
suite), as did Ruff, strict validation and the unchanged legacy checksum.

Task 3.9 declared phase-domain full-force controls (2026-09-10):
Add explicit 10 m position balls and 1 m/s velocity balls to the direct-SPICE
fixed-epoch full-force controls. Verify exact squared-distance implications,
outward Sun-relative speed bounds, and native total acceleration below the
composed domain majorant near Moon/cruise/Mars for coast and both burns.
Preserve old bounds, component parity, historical-table controls and native
counters; report old/new bounds with domain inputs. Run gravity/full tests,
Ruff, strict validation and legacy checksum. The domain radii are declared
test inputs, not proven trajectory reaches; do not close 3.9 or change safety.
All 38 gravity tests and 987 full-suite tests passed (161.26 s for the full
suite), as did Ruff, strict validation and the unchanged legacy checksum.

Task 3.9 conditional whole-interval body reach (2026-09-10):
Replace the second endpoint error in the reach construction with the maximum
error envelope across all intersecting strips, including joins centered
outside the interval. Verify 3,266 reused native-state comparisons over
adjacent/full intervals, endpoint-error containment, larger interior error
maxima on full intervals and outward radius reporting. Run all SPK and full
tests, Ruff, strict validation and legacy checksum. These conditional coarse
position balls do not establish spacecraft error, physical uncertainty or
native runtime premises; leave 3.9 and production safety unchanged.
All 60 SPK tests and 987 full-suite tests passed (160.29 s for the full suite),
as did Ruff, strict validation and the unchanged legacy checksum.

Task 3.9 velocity-domain first-exit counterexample (2026-09-10):
Verify joint position/speed inclusion on x'=v, v'=v^2 in normalized SI units:
0.1 s passes; 0.25 s fails strict speed inclusion without actual domain exit;
0.75 s retains positional inclusion while true speed invalidates the assumed
acceleration bound. Use exact rational velocity and analytic position oracles.
Run focused/full tests, Ruff, strict validation and legacy checksum. This is
a synthetic necessity control, not a real-mission or Schwarzschild enclosure.
Keep full-force domains and numerical-error premises open under task 3.9.
All 65 focused geometry/reach tests and 987 full-suite tests passed (159.69 s
for the full suite), as did Ruff, strict validation and the legacy checksum.

Task 3.9 first-exit closure on a monopole control (2026-09-10):
Compose distance, whole-domain monopole acceleration and reach bounds on an
independent circular solution. Verify strict inclusion for 0.05 s and failure
for 1 s at two source-reach radii, distinguish domain from initial-point
acceleration, reject a domain containing the force singularity, and retain
the strict equality boundary. Run focused/full tests, Ruff, strict OpenSpec
validation and legacy checksum. The first-exit argument closes only this
analytic positional domain; full-force velocity/mass, native arithmetic and
trajectory-error premises remain open. Do not close 3.9 or change production.
All 62 focused geometry/reach tests and 984 full-suite tests passed (159.73 s
for the full suite), as did Ruff, strict validation and the legacy checksum.

Task 3.9 conditional position-reach integration bound (2026-09-10):
Add an outward-rounded private reach radius e+v*h+A*h^2/2 with explicit
nonnegative initial error, initial speed bound, acceleration bound and duration.
Verify exact constant-velocity/acceleration controls, zero duration, mixed
inputs, underflow, invalid inputs, overflow and shared-deadline rejection.
Compose with the distance floor on an independent exact-motion control with
7 m minimum separation and distinct 6 m/8 m clearance guards. Run focused and
full tests, Ruff, strict validation and legacy checksum. Require an independently
justified full-interval acceleration bound before production use; the formula
does not cover source-representation jumps or certify numerical propagation.
Keep task 3.9 open and production safety decisions unchanged.
All 56 focused geometry/reach tests and 978 full-suite tests passed (159.92 s
for the full suite), as did Ruff, strict validation and the legacy checksum.

Task 3.9 conditional relative-distance floor (2026-09-10):
Add a private downward-rounded separation floor for two supplied position
balls, requiring explicit finite nonnegative spacecraft/body reach radii.
Verify exact translated 3-4-5 geometry, attainable collinear displacement,
irrational norms across extreme scales, tangency, negative overlap bounds,
external Decimal-context isolation, invalid input, overflow and deadline
rejection. Run focused tests, all pytest, Ruff and strict OpenSpec validation;
verify unchanged legacy checksum. Do not wire into production safety before
the reach radii and numerical error are justified; task 3.9 remains open.
All 30 focused geometry tests and 952 full-suite tests passed (159.78 s for
the full suite), as did Ruff, strict validation and the legacy checksum.

Task 3.9 conditional two-epoch body-motion composition (2026-09-10):
Compose per-link maximum position rates, every crossed source jump and both
native endpoint error envelopes. Reuse 1,078 chain-side states, add 16
candidate-endpoint reads with exact one-core membership, and verify 1,094
adjacent/full-interval L1 displacement comparisons against direct SPKSSB.
Verification: all SPK tests, full pytest, Ruff, strict OpenSpec validation and
legacy checksum. This coarse conditional displacement bound is not a chord
or propagated-spacecraft error bound, nor a safety/performance result.
Keep scientific tolerances and production limits unchanged; leave 3.9 open.
All 60 SPK tests and 922 full-suite tests passed (159.87 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 all-body center-chain join composition (2026-09-10):
Form the join-epoch union for all eight body chains. Verify distinct event
strips are disjoint and each nonjoining link contains the entire strip in
exactly one qualified record core. Compose active source jumps/rates with
the existing all-link evaluation/addition/SI bound, and compare 1,078 direct
SPKSSB side queries across 539 body/event pairs with exact polynomial sums.
Require generalized Moon bounds to equal the dedicated controls exactly.
Verification: all SPK tests, full pytest, Ruff, strict OpenSpec validation
and legacy checksum. Maximum composed envelope: 14.382604265140298 m
(Jupiter, including representation ambiguity, not just arithmetic error).
Keep the 0.001 m arithmetic gate unchanged; native execution premises,
full-force trajectory error and safety remain open. Do not close 3.9.
All 60 SPK tests and 922 full-suite tests passed (160.22 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 coincident Moon/Earth join composition (2026-09-10):
Verify the two source links share exactly 73 join epochs. Compose both source
jumps and extended rate terms with the existing uniform Moon-chain arithmetic
bound. Independently check all pairs of four exact mixed endpoint sums and
146 one-ULP-side SPKSSB positions against exact nominal polynomial sums.
Verification: complete SPK tests, full pytest, Ruff, strict OpenSpec validation
and unchanged legacy checksum. The envelope includes representation ambiguity;
it does not replace the 0.001 m arithmetic gate or estimate physical orbit
uncertainty. Keep native premises, other chain configurations and spacecraft
safety open; leave task 3.9 unchecked and production unchanged.
All 60 SPK tests and 922 full-suite tests passed (159.28 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 exhaustive representable-epoch Saturn priority strip (2026-09-10):
Enumerate all 33 binary64 epochs in the 16-ULP cross-segment strip; verify
exact endpoints and consecutive nextafter coverage. Use independent segment
eligibility and same-file priority to check 99 native selections in forward,
reverse and interleaved query orders. Require file handle, descriptor and
selected raw-record bytes to match, including the exact-junction left-segment
priority and final-record clamp. Verification: complete SPK tests, full pytest,
Ruff, strict OpenSpec validation and unchanged legacy hash. This qualifies the
pinned strip and tested orders, not arbitrary cache histories or kernel pools;
runtime premises, simultaneous chain joins and spacecraft safety remain open.
Keep 3.9 unchecked and production unchanged.
All 60 SPK tests and 922 full-suite tests passed (159.45 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 conditional within-segment selection domains (2026-09-10):
Construct 550 trimmed record cores and 539 join strips with exact endpoints;
verify their union covers the complete candidate interval for all 11 links.
Verify 1,100 native core endpoint reads and 1,076 internal-strip endpoint
reads against exact DAF records and the inspected index replay. Use the
fixed-profile selector's monotonicity to justify the one-record core and
two-record internal-strip implications, not sparse sampling alone.
Verification: complete SPK tests, full pytest, Ruff, strict OpenSpec validation
and unchanged legacy hash. Explicitly exclude the single cross-segment strip
(699, 986817600 TDB s) from the 538 internal-strip claim. Runtime premises,
segment priority and spacecraft safety remain open; keep 3.9 unchecked.
All 60 SPK tests and 922 full-suite tests passed (159.32 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 conditional native envelopes at every inventoried join (2026-09-10):
Combine exact endpoint jumps, both extended position-rate bounds and the
selected record's evaluation/SI error over each 16-ULP join strip. Verify
ULP-domain alignment for all 539 joins and outward reporting. All 1,078
existing side queries must lie inside their own conditional envelopes;
removing the jump must retain at least the 221 known failure controls.
Verification: complete SPK tests, full pytest, Ruff, strict OpenSpec validation
and unchanged legacy hash. Observed omission failures: 221; largest envelope:
14.382176411464647 m, including representation differences rather than only
roundoff. This does not replace the 0.001 m arithmetic gate. Selection,
segment priority, simultaneous chain joins and spacecraft safety remain
unqualified; keep 3.9 open and production unchanged.
All 60 SPK tests and 922 full-suite tests passed (159.52 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 conditional interval-wide position-chain composition (2026-09-10):
Derive native position-magnitude bounds from all 550 records' coefficient
majorants and evaluation errors. Verify exact and native magnitudes at all
3,300 supplied-record controls. Combine source, addition and SI conversion
errors for the eight one/two-link chains using exact fractions and upward
reporting, finite-range guards and independent aligned/opposed arithmetic
controls. Verify every conditional chain bound is below 0.001 m; the maximum
is 0.0007284371515436439 m for Saturn. Verification: complete SPK tests,
full pytest, Ruff, strict OpenSpec validation and unchanged legacy hash.
Record/segment choice, runtime arithmetic premises, velocity and spacecraft
safety remain outside this enclosure; keep 3.9 open and production unchanged.
All 60 SPK tests and 922 full-suite tests passed (159.30 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 sampled center-chain and SI arithmetic (2026-09-10):
Extend all eight 38-epoch chain controls with 456 selected-link state reads.
Verify add-then-scale replay is bit-identical to SPKSSB, the Tudat wrapper
and production direct ephemerides for all 304 states. Check separate and
combined addition/conversion roundoff against exact rational input-state
sums under unchanged 0.001 m / 0.000001 m/s gates. Retain scale-before-add
counterexamples for all four two-link bodies. Verification: complete SPK
tests, full pytest, Ruff, strict OpenSpec validation and unchanged legacy hash.
The maximum additional sampled L1 errors are 0.00024531567112262564 m and
5.491607169005874e-12 m/s. These exclude source-polynomial errors and do not
establish interval-wide magnitudes or native dispatch; keep 3.9 open.
All 60 SPK tests and 922 full-suite tests passed (162.31 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 conditional uniform supplied-record position error (2026-09-10):
Derive a fused-recurrence residual enclosure with relative and gradual-
underflow terms, exact Sterbenz subtraction premises, division error and the
existing extended L1 polynomial-rate bound. Verify all 550 record enclosures
are rounded outward and below 0.001 m; all 3,300 sampled native errors must
lie inside their own enclosure. Verify exact single-mode and constant/linear
oracles, smallest-subnormal rounding, overflow rejection and deadline failure.
Verification: complete SPK tests, full pytest, Ruff, strict OpenSpec validation
and unchanged legacy hash. Largest conditional bound: 0.0002473194716238903 m.
Keep the helper test-only: continuous rounding mode, dispatch, record/segment
selection, chain accumulation, SI conversion and spacecraft error are not
established by this step. No scientific tolerance or production-limit changes;
3.9 remains open.
All 60 SPK tests and 922 full-suite tests passed (158.92 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 native position-polynomial arithmetic replay (2026-09-10):
Pin the CHBVAL/CHBINT position instruction observations and replay fused
Clenshaw operations with exact fractions rounded once per fused expression.
Verify a manufactured one-ULP fused/unfused counterexample against both
native routines and an independent quadratic oracle. Evaluate all 550 records
at six epochs each, requiring 9,900 position components to match the replay
bit-for-bit and independent exact-polynomial errors to remain within 0.001 m.
Verification: complete SPK tests, full pytest, Ruff, strict OpenSpec validation
and unchanged legacy hash. Observed maximum sampled L1 error is
0.00016239212647380994 m; it is not a uniform bound. Native derivative error,
SI conversion, chain accumulation and interval safety remain outside this step.
Keep 3.9 open; no production model, dependency or tolerance changes.
All 50 SPK tests and 912 full-suite tests passed (152.90 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 pinned native record-selector arithmetic (2026-09-10):
Pin the inspected Darwin/arm64 CSPICE hash and identical type-2/type-3
selection bytes. Verify separate binary64 subtraction/division, signed
conversion/address ranges and the final-record clamp with 24 endpoint
readbacks across the 12 relevant segments. Preserve all prior readback and
counterexample checks. Verification: complete SPK tests, full pytest, Ruff,
strict OpenSpec validation and unchanged legacy hash. Static observation
does not establish continuous rounding mode, live dispatch or a native
evaluation-error enclosure; keep task 3.9 open.
All 49 SPK tests and 911 full-suite tests passed (152.30 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 conditional whole-segment index-roundoff margin (2026-09-10):
Derive `(2u+u^2)*segment_span_s` for the two-operation round-to-nearest
binary64 index replay. Verify normal-range bounds from the next epoch after
INIT through the segment end, exact zero offset and outward SI reporting
for all 12 segments. Check the quotient-error inequality and neighboring
record implication at all 1,628 readbacks, including all 466 early choices.
Verification: whole `tests/test_trajectory_spk.py`, full pytest, Ruff, strict
OpenSpec validation and unchanged legacy hash. The native arithmetic graph
and rounding environment remain assumptions, not a qualified native error
bound; keep 3.9 open and the targeting spike blocked.
All 48 SPK tests and 910 full-suite tests passed (155.31 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 all-link native record readback (2026-09-10):
Share a guarded test-only type-2/type-3 reader and preserve the previous
7,293 readbacks. Verify 1,628 additional midpoint/one-ULP-side probes across
all 11 links against direct DAF bytes and the index replay. Require the
observed 466 early record choices (245 type 2, 221 Mars/Jupiter type 3),
per-target counts and unchanged pool/deadline controls. Verification: whole
`tests/test_trajectory_spk.py`, full pytest, Ruff, strict OpenSpec validation
and unchanged legacy hash. Do not infer type-2 switch widths or uniform
native error from these probes; leave 3.9 open.
All 48 SPK tests and 910 full-suite tests passed (152.21 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 native selected-record readback (2026-09-10):
Add a separate pinned Darwin/arm64 qualification variant that directly reads
the selected type-3 record for all 7,293 existing switch probes. Verify type,
directory-derived buffer size, length word, guard, native error state and
bitwise equality of all 122 words with the selected source record. Keep the
portable variant, kernel pool and shared budget unchanged. Verification:
whole `tests/test_trajectory_spk.py`, full pytest, Ruff, strict OpenSpec
validation and unchanged legacy checksum. All sampled selections agree;
uniform native behavior and evaluation error remain open under task 3.9.
All 48 SPK tests and 910 full-suite tests passed (154.04 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.
Both focused variants also passed after placing native setup inside the budget.

Task 3.9 exact adjacent-branch ambiguity envelope (2026-09-10):
Combine exact L1 endpoint jumps with both extended rate bounds over explicit
16-epoch-ULP strips at 221 Mars/Jupiter joins. Verify 1,547 exact same-epoch
branch differences, including both strip edges and the sampled switch,
outward reporting and failure when the jump is omitted. Verification:
whole `tests/test_trajectory_spk.py`, full pytest, Ruff, strict OpenSpec
validation and unchanged legacy hash. This bounds two exact polynomials,
not native selection/roundoff or spacecraft safety; leave 3.9 open.
All 47 SPK tests and 909 full-suite tests passed (151.02 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 extended exact-polynomial rate qualification (2026-09-10):
Add an explicit nonnegative extension_s to the private rate helper and derive
the exact Chebyshev derivative majorant over that larger interval. Verify
independent finite-power degree 0/1/2/3/19 oracles, unchanged zero-extension
results, mixed-axis rational rounding, sub-ULP normalization and invalid/
overflow/deadline guards. Check 16-epoch-ULP extensions for all 550 source
records, without inferring native coverage or safety. Verification: whole
`tests/test_trajectory_spk.py`, full pytest, Ruff, strict OpenSpec validation
and unchanged legacy checksum. Native error, switches and jump/chain
composition remain separate open prerequisites; do not close 3.9.
All 47 SPK tests and 909 full-suite tests passed (160.09 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 sampled native record-switch brackets (2026-09-09):
Probe offsets -16 through +16 epoch ULP around all 221 Mars/Jupiter joins.
Verify native position agrees with the rounded index replay within 0.001 m,
the alternative record differs by more than 0.001 m, and each sampled switch
occurs at -4 ULP. Verify exact versus binary64 epoch-minus-INIT arithmetic
for all four early-selection epochs. Emit per-join brackets and maximum
replay discrepancies. Verification: whole `tests/test_trajectory_spk.py`,
complete pytest, Ruff, strict OpenSpec validation and unchanged legacy hash.
This is local position-only evidence, not a compiled-arithmetic proof or a
uniform native-error enclosure; retain the previous counterexample and 3.9.
All 35 SPK tests and 897 full-suite tests passed (159.23 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.
The maximum observed replay discrepancy was 9.203439287865708e-11 m.

Task 3.9 all-chain join qualification and native counterexample (2026-09-09):
Pair all 539 interior record joins, compute exact L1 endpoint jumps, and
verify one-ULP interior displacements against both local rate bounds plus
the jump. Preserve the 298 controls where omission fails. Compare both
sides to segment-native SPICE at the unchanged 0.001 m threshold: 221
left-side probes fail (163 Mars and 58 Jupiter), with a maximum Euclidean
error of 8.74270150900805 m. Verify those values agree with the neighboring
right-side probe within 0.001 m, and emit every failed epoch and error.
Verification: `tests/test_trajectory_spk.py -k chain_coverage`, whole SPK file,
complete pytest, Ruff, strict OpenSpec validation and unchanged legacy hash.
This is a reproducible failed scientific comparison, not successful native
qualification. Investigate record-selection arithmetic and its transition
width before using exact record intervals for native safety; keep 3.9 open.
All 35 SPK tests and 897 full-suite tests passed (162.38 s for the full suite),
as did Ruff, strict OpenSpec validation and the unchanged legacy checksum.
Passing regression tests reproduce the failed parity criterion, not resolve it.

Task 3.9 all-chain SPK record-rate qualification (2026-09-09):
Extend the existing loaded-chain test to decode type-2/type-3 position records
for all 11 required target/center links. Verify exact directory/header layout,
candidate-overlap selection, five derivative probes per record and segment-native
midpoint parity within 0.001 m and, for type 2 only, 0.000001 m/s. Verification:
`tests/test_trajectory_spk.py -k chain_coverage`, the whole SPK file, complete
pytest, Ruff, strict OpenSpec validation and the legacy checksum. The focused
check covers 550 records and passes; midpoint maxima are 0 m and
1.4210854715202004e-11 m/s. Type-3 velocity is not a derivative oracle. Keep
3.9 open: chain/jump composition, native rounding and spacecraft error remain
unverified, with no production or scientific-tolerance changes. All 35 SPK
tests and 897 full-suite tests passed (153.33 s for the full suite), as did
Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 3.9 exact SPK position-rate/jump controls (2026-09-09):
Derive a record-wide Chebyshev position-derivative majorant from exact raw
coefficients with outward SI rounding. Verify analytic endpoint equality,
mixed-axis arithmetic, subnormal/overflow, invalid-input and deadline guards;
check all 74 overlapping Saturn records and exact jump-inclusive motion bounds
at 73 joins. Verification: `tests/test_trajectory_spk.py -k 'rate_bound or segment_inventory'`,
whole SPK file, complete pytest, Ruff and strict OpenSpec validation. The initial
controls passed, with rates bounded by 3.043598–4.200999 m/s relative to the
Saturn barycenter. Native rounding, chain composition and spacecraft error
remain outside this bound; do not mark 3.9 complete or change production limits.

Task 3.9 loaded-SPK chain interval coverage (2026-09-08):
Scan all loaded SPK descriptors and verify candidate-overlapping target centers,
frames and types. Merge coverage by target and intersect all 11 required chain
windows; verify whole-interval inclusion, rejection of missing targets and an
interior gap, unchanged kernel records and the shared budget. Verification:
`tests/test_trajectory_spk.py -k chain_coverage`, the whole SPK file, full pytest,
Ruff and strict OpenSpec validation. The focused test passed across six files
and 2,028 segments. Nominal coverage is not a uniform accuracy or safety bound;
keep production settings and task 3.9 unchanged.

Task 3.9 direct-ephemeris fixed-state force controls (2026-09-08):
Extend the existing gravity/component-sum controls with test-only direct body
ephemerides and endpoint parity checks. Verify gravity, combined coast and both
thrust phases at all three existing fixed states, unchanged force tolerance,
PPN recovery, bounds and shared-budget accounting for every native run. Run
`tests/test_trajectory_gravity.py -k real_gravity`, the whole gravity file,
full pytest, Ruff and strict OpenSpec validation. All eight focused cases
passed, including 12 direct-path initial-state comparisons. No production
strategy switch or full-trajectory accuracy/performance conclusion; 3.9 stays open.

Task 3.9 bounded lookup-cost experiment (2026-09-08):
Compare the existing 300 s table and test-only direct ephemerides for eight
bodies using six alternating batches of 3,800 warm queries per path. Verify
finite states and unchanged sampled parity limits outside timed loops, emit
raw timings and medians, and preserve one shared 300-second budget with zero
native arcs. Verification: `tests/test_trajectory_spk.py -k lookup_cost`, the
whole SPK file, full pytest, Ruff and strict OpenSpec validation. The focused
run passed; measured direct/table cost ratios were about 2.9–3.6. No timing
ratio gate, full-force runtime projection or production changes are introduced.
Task 3.9 remains open; passing this check does not repair table inaccuracies.

Task 3.9 eight-body direct-SPICE path parity (2026-09-08):
Extend all eight sampled source-chain cases with explicit SSB/J2000 direct
native models and numeric-target CSPICE state comparisons at 38 epochs each.
Verify native frame readback, unchanged body-center chains, finite states and
`0.001 m` / `0.000001 m/s` agreement with
`tests/test_trajectory_spk.py -k sampled_spk_chains`, the whole SPK file, full
pytest, Ruff and strict OpenSpec validation. All 304 focused comparisons passed
with measured differences zero. No production setting, tolerance or dependency
changes; interval coverage and full-force performance remain open under 3.9.

Task 3.9 direct-SPICE native error controls (2026-09-08):
Verify unknown-body and both distant uncovered-epoch requests raise contextual
native RuntimeError subclasses with IDCODENOTFOUND/SPKINSUFFDATA, not states.
Verify a valid query recovers bit-for-bit without reset/reload, pending SPICE
error or loaded-kernel count change. Run
`tests/test_trajectory_spk.py -k direct_spice_errors` (three cases), the whole
SPK file, full pytest, Ruff and strict OpenSpec validation. Focused cases passed.
Use the already-pinned SpiceyPy pool inspection; no dependency changes.
These checks do not establish all coverage edges, project error translation
or full-force runtime. Production settings stay unchanged and 3.9 remains open.

Task 3.9 test-only direct-SPICE alternative (2026-09-08):
Construct a separate built-in direct-SPICE Saturn ephemeris in SSB/J2000 and
compare all 219 mapped boundary probes with named geometric SPICE queries.
Verify frame readback and `0.001 m` / `0.000001 m/s` parity using
`tests/test_trajectory_spk.py -k segment_inventory`, then the whole SPK file,
full pytest, Ruff and strict OpenSpec validation. Observed maxima are zero;
the production table's 73/71 failures remain reproduced. This is test-only
API parity, not a change to production or proof of source continuity, error
handling, full-force performance or trajectory safety. Task 3.9 stays open.

Task 3.9 exact Saturn record-endpoint differences (2026-09-08):
Read full records, verify finite coefficients and compute all 146 paired
endpoints using exact Chebyshev endpoint identities and rational SI conversion.
Verify NumPy Chebyshev parity within `1e-8 m` / `1e-12 m/s`, exact squared
differences exceeding twice the existing allocations at 70 position / 68
velocity joins, and nonzero differences at all 73 joins. Run
`tests/test_trajectory_spk.py -k segment_inventory`, the whole SPK file, full
pytest, Ruff and strict OpenSpec validation. The focused check passed; largest
reported jumps are `0.21757621126693544 m` / `2.5019583702437535e-5 m/s`.
These are source-representation discontinuities, not physical motion or a
production remedy. Preserve every kernel, production tolerance and limit;
task 3.9 remains open.

Task 3.9 all mapped Saturn record-join probes (2026-09-08):
Compare the production 300 s table with direct SPICE at all 73 directory-derived
interior boundaries and their adjacent binary64 epochs. Verify finite SI errors,
retain per-boundary maxima and reproduce 73 position / 71 velocity allocation
failures with `tests/test_trajectory_spk.py -k segment_inventory`; run the whole
SPK file, full pytest, Ruff and strict OpenSpec validation. Worst errors are
`0.1823327710720816 m` and `2.13863534474615e-5 m/s` near `997133760 TDB s`.
These 219 comparisons show that a single-segment-junction remedy is insufficient;
they do not certify unsampled epochs or same-epoch coefficient jumps. Preserve
all scientific tolerances and production settings. The regression reproduces
failure, and task 3.9 remains open.

Task 3.9 Saturn polynomial-record directory (2026-09-08):
Read both candidate-overlapping type-3 segment trailers and all 200 record
headers. Verify 100 records/segment, 122 words/record, degree 19, duration
343872 s, exact midpoint/radius agreement, storage length and segment coverage.
Verify 74 overlapping records and 73 sorted interior boundaries, including
the known segment junction, with `tests/test_trajectory_spk.py -k segment_inventory`.
Run the whole SPK file, full pytest, Ruff and strict OpenSpec validation.
The focused directory check passed. This identifies where to test other
record joins, not their accuracy; barycenter records and all-file precedence
remain unqualified. No coefficient, kernel, force, tolerance or limit changes;
task 3.9 and the interpolation counterexample remain open.

Task 3.9 selected Saturn file segment inventory (2026-09-08):
Exhaust the directory of the SPK file selected for Saturn at departure using
read-only DAF calls. Verify 1,223 entries, 171 Saturn entries with center/frame/
type `(6,1,3)`, and exactly the two documented candidate-overlapping segments,
including file order, word addresses and contiguous coverage. Verify EOF and
native error flags with `tests/test_trajectory_spk.py -k segment_inventory`,
then run the whole SPK file, full pytest, Ruff and strict OpenSpec validation.
The focused inventory passed with no spacecraft propagation or kernel changes.
This completes one file's segment inventory, not loaded-file precedence or
internal polynomial-record boundaries. Preserve the known allocation failure,
all tolerances and production settings; task 3.9 remains open.

Task 3.9 junction table-density control (2026-09-08):
Extend the existing junction regression to test-only 150 s and 75 s tables,
retaining the production 300 s path, candidate coverage and SSB/J2000 frames.
Verify both original allocations are exceeded at each spacing with
`tests/test_trajectory_spk.py -k segment_junction`; run the whole SPK file,
full pytest, Ruff and strict OpenSpec validation. All three focused cases
reproduced failure. Maximum position errors at 150/75 s are
`0.10801370752951119 m` / `0.12190976075097239 m`; velocity errors are
`1.285373338685058e-5 m/s` / `1.4591343096708111e-5 m/s`.
These denser tables are not a remedy; no production setting or tolerance is
changed and task 3.9 remains open. Investigate source boundaries before a
reviewed boundary-aware approximation policy.

Task 3.9 local junction query-order control (2026-09-08):
Verify all six permutations of before/exact/after Saturn junction queries with
two named requests per epoch, exact binary64 component equality across orders,
and raw CSPICE/SI parity. Verify six exact-junction descriptors select the
observed left segment. Run `tests/test_trajectory_spk.py -k query_order`, the
whole SPK file, full pytest, Ruff and strict OpenSpec validation. The focused
control passed: 36 named and 18 raw state queries, with no kernel/cache reset
or spacecraft propagation. This rules out these local query orders as the
explanation, not other runtime contexts; the interpolation allocation still
fails. No scientific/production changes; task 3.9 remains open.

Task 3.9 Saturn junction counterexample (2026-09-08):
Evaluate both adjacent SPK segments at their shared epoch and compare the
unchanged 300 s table to direct SPICE immediately before, at and after it.
Verify the native center/frame, distinct descriptors and finite states, retain
measured differences, and require reproduction of the existing position and
velocity allocation failures in `tests/test_trajectory_spk.py -k junction`.
Run the whole SPK file, full pytest, Ruff and strict OpenSpec validation.
Observed same-epoch segment differences: `0.1628216982412309 m` and
`1.940988845873698e-5 m/s`; maximum table/direct errors at the three probes:
`0.1394431198762437 m` and `1.6599647370186684e-5 m/s`.
This is a passing regression of a failed scientific allocation, not completion
of 3.9. Preserve `0.025 m` / `2.5e-6 m/s`, all kernels/forces/limits and the
targeting gate. Investigate source boundaries and query-order behavior before
proposing a reviewed remedy; original task 2.7 samples do not cover this failure.

Task 3.9 sampled SPK chain inventory (2026-09-08):
Use read-only installed CSPICE descriptor/state calls through ctypes, preserving
Tudat kernel loading. Verify eight body-to-SSB chains at the existing 38 epochs,
J2000 frame, type-2/type-3 selection and descriptor coverage; compare numeric
CSPICE targets to named Tudat states within `0.001 m` and `0.000001 m/s`.
Verify an unknown ID returns no descriptor without a SPICE error. Run
`tests/test_trajectory_spk.py`, full pytest, Ruff and strict OpenSpec validation.
All nine focused tests passed. Record Mercury/Venus targets 1/2 explicitly and
Saturn's observed segment change at `986817600 TDB seconds since J2000`.
These are sampled source identities, not complete interval selection, polynomial
coefficient bounds or a safety certificate. No dependency, force, tolerance,
production limit or deadline changes; task 3.9 remains open.

Task 3.9 conditional static factory-route observation (2026-09-08):
Trace direct calls from the double/double body factory through tabulated SPICE,
the SPICE node builder and the one-dimensional interpolator factory. The builder
uses repeated binary64 FADD for its grid. Enum 3 selects the Lagrange branch;
a successful settings dynamic cast precedes the direct call to the inspected
double/six-double/double constructor. Record eight additional instruction
observations under the unchanged binary hash. Verify them and all eight public
InterpolatedSpiceEphemerisSettings objects with
`tests/test_trajectory_ephemeris.py -k 'static_observation or grid_binary64'`,
then the full ephemeris file, full pytest, Ruff and strict OpenSpec. The binding
does not expose nested interpolator_settings, so this does not certify live
nested settings or virtual dispatch. No object-memory probing, settings changes,
new dependency, force/tolerance change or limit revision; task 3.9 remains open.

Task 3.9 static denominator-initializer observation (2026-09-08):
Inspect initializeDenominators for the same double/six-double/double native
specialization. Its `[0x19a348,0x19a390)` inner loop loads exact 1.0, excludes
the self-index, and uses sequential scalar binary64 FSUB/FMUL/store instructions.
Record six additional instruction observations under the unchanged module hash;
the existing byte check covers both named symbols. Verify
`tests/test_trajectory_ephemeris.py -k 'static_observation or grid_binary64'`,
the full ephemeris file, full pytest, Ruff and strict OpenSpec. The independently
checked exact-grid factorial denominators remain unchanged. This is compiled
code agreement with that arithmetic graph, not inspection of live caches or
verification of runtime construction dispatch. Continuous rounding-state and
dispatch premises remain open, as do SPICE/spacecraft error bounds. No binary,
force, tolerance or work limit changes; task 3.9 stays open.

Task 3.9 read-only rounding-environment observation (2026-09-08):
Inspect Darwin arm64 fenv_t (16 bytes: FPSR, then FPCR at offset 8) and record
the SDK header hash. Read fegetenv/fegetround with explicit ctypes signatures,
checking return code and layout. Bracket setup, eight native table constructions
and 304 state requests: require 626 caller-thread snapshots of FPCR=0 and
FE_TONEAREST=0. Verify nine synthetic invalid/nondefault/bool cases fail without
setting the CPU environment, using `tests/test_trajectory_ephemeris.py -k fpcr`,
then the full ephemeris file, full pytest, Ruff and strict OpenSpec. Skip this
ABI-specific observation on other platforms. Never set rounding modes or clear
exception flags; FPSR history is not used as a control-mode certificate. Preserve
the shared 300-second deadline and zero spacecraft-propagation counters. The
snapshots do not exclude temporary internal mode changes or qualify other threads
or future calls. Runtime dispatch and continuous arithmetic semantics remain
open, with no scientific tolerance or production limit change; 3.9 stays open.

Task 3.9 static native arithmetic observation (2026-09-08):
Apple LLVM 21.0.0 disassembly of the installed 42,188,016-byte Darwin/arm64
kernel identifies the double-time/six-double-state/double-scalar Lagrange symbol.
Its interior loop at `[0x19abd8,0x19acb0)` uses scalar FSUB/FMUL/FDIV and three
separate binary64 vector multiply/add pairs, with no fused multiply-add in that
loop. The checked-in JSON records the module SHA-256, exact symbol, selected
instruction bytes and command; the text segment's virtual address and file
offset are both zero. Verify installed hash/size and bytes using
`tests/test_trajectory_ephemeris.py -k static_observation`, then the full
ephemeris file, full pytest, Ruff and strict OpenSpec. The native file is read,
not modified; other platforms skip this observation, and build drift requires
re-inspection. Runtime dispatch, cached-denominator construction and FPCR state
are still unqualified; no complete native rounding/safety certificate follows.
No force model, scientific tolerance, production work limit or deadline changes;
task 3.9 remains open.

Task 3.9 whole-interval conditional arithmetic summary (2026-09-08):
Use complete required-node component maxima, rather than sampled cell maxima,
in the already-derived `gamma_15*(89/64)*M_j` envelope. Every candidate stencil
belongs to that node union. Record component bounds and separately upward-rounded
position/velocity L1 sums (also Euclidean upper bounds), using exact Fraction
arithmetic and checking every reported float is finite and no smaller than its
exact value. Verify with `tests/test_trajectory_ephemeris.py -k grid_binary64`,
the full ephemeris file, full pytest, Ruff and strict OpenSpec. This is a uniform
bound for the inspected arithmetic model versus its exact polynomial under the
stated binary64 premises; it is not a sampled-error maximum, a verified compiler
contract, SPICE approximation error or spacecraft safety. Oracle-conversion
rounding is excluded here and remains separate from the earlier gamma_16
sampled comparison. No production behavior, tolerance or budget changes; 3.9
remains open.

Observed whole-interval model L1 maxima: `0.005219971 m` (Saturn) and
`2.974497e-10 m/s` (Mercury), rounded upward here. The focused check passed
in 3.80 s. These are not directly interchangeable with the older sampled
gamma_16 figures: this uses maxima over all required nodes and gamma_15 excludes
the rational oracle's conversion. No improvement in physical accuracy is claimed.

Task 3.9 exhaustive required-native-knot parity (2026-09-08):
Derive the union of candidate six-node stencils with exact rational floor indices
and query every required knot through each production native ephemeris. Require
coverage of that full union and exact equality of all six binary64 bit patterns
against the reconstructed SPICE nodes, not a relaxed physical tolerance. Report
match counts and subset hashes separately from the larger padded source inventory,
and measure native construction/query/check time separately. Verify using
`tests/test_trajectory_ephemeris.py -k grid_binary64`, the full ephemeris file,
full pytest, Ruff and strict OpenSpec. Preserve deadline checks around native
construction, every 512 knot queries and after each body with zero spacecraft
propagations. This checks public knot values, not internal storage or compiled
between-knot arithmetic. SPICE accuracy and spacecraft numerical error remain
open; no production tolerance, force or native-call limit changes; 3.9 stays open.

Observed: 83,918 required knots per body (671,344 states total), from
`978994855.2304223` through `1004169955.2304223` TDB seconds since J2000.
All six binary64 component bit patterns matched at every requested knot.
Per-body construction/query/check times were 0.1456--0.1755 s, about 1.262 s
combined; the focused test passed in 3.64 s. These are qualification timings,
not measurements of spacecraft propagation or a revised production budget.

Task 3.9 complete source-node range inventory (2026-09-08):
Extend the exact-grid test to query all padded-grid nodes for all eight bodies
through pinned TudatPy/SPICE, in timestamp order, and apply the existing
zero-or-`[2^-100,2^100]` SI magnitude gate to every component. Record counts,
component extrema excluding zeros, zero counts, state hashes in an explicit
binary encoding, software/kernel provenance and inventory-only elapsed time.
Verify with `tests/test_trajectory_ephemeris.py -k grid_binary64`, the full
ephemeris file, full pytest, Ruff and strict OpenSpec. The shared 300-second
budget is checked every 512 queries and after each body; propagation counters
stay zero. This extends the node-range premise beyond the former 304 cell
requests, but reconstructs source inputs rather than reading native storage.
Native identity/compiler semantics, boundary splines, SPICE approximation and
spacecraft numerical error remain open. No runtime force, tolerance or work
limit changes; task 3.9 remains open.

Observed inventory: 83,933 nodes per body, 671,464 states / 4,028,784 SI
components total; every component passed. Inventory-only time was 1.0861 s
(machine-specific observation, not a new performance limit). The focused test
passed in 2.31 s. TudatPy version is read from its module, as in the existing
qualification, because the Conda package has no importlib distribution metadata.

Task 3.9 state-arithmetic range qualification (2026-09-08):
Check every node component of the existing 304 cell requests is zero or within
the test-only magnitude range `[2^-100, 2^100]` in m or m/s. The pinned-grid
weight enclosure fits `(2^-200, 2^40)`; exact and rounded product bounds and six
addition bounds stay normal/finite or exact zero. A `2^-353` binary64 lattice
argument handles cancellation uniformly within those cells. Verify the exact
Fraction bounds, all 720 orders of a tiny/large/zero cancellation control, and
rejection of nonfinite or out-of-range nodes in `tests/test_trajectory_ephemeris.py`;
run the full suite, Ruff and strict OpenSpec validation. Per-body JSON records
the count of qualified cell requests (including repeated cells). This is not
all-mission node coverage, compiled-native certification, a general rational
oracle-conversion guarantee, SPICE error control or integration safety. No
production range restriction or tolerance is added; task 3.9 remains open.

Task 3.9 weight-arithmetic range qualification (2026-09-08):
Extend the pinned-grid exact-arithmetic test with an inductive Fraction enclosure
for all represented non-knot middle-cell queries, not just sampled epochs.
Positive timestamp spacing bounds each nonzero difference below by
`ulp(initial_time)`; `3*300 s` bounds it above. Six numerator products, the
cached-denominator/time-difference product and division each have exact and
rounded enclosures strictly inside the normal finite binary64 range. Nearest
represented interior queries and knot shortcuts on the first, middle and last
stencils have independent rational affine controls within `1e-12` per SI
component. The JSON records exact weight-magnitude bounds and epoch spacing.
Verify with `tests/test_trajectory_ephemeris.py`, full pytest, Ruff and strict
OpenSpec validation. This addresses only range premises for correctly rounded
weight operations: state multiply/add cancellation, arbitrary oracle conversion,
compiled-native semantics and SPICE approximation are not certified. No runtime
behavior, scientific tolerance, native-call limit or deadline changes; 3.9 stays
open.

Task 3.9 conditional roundoff-envelope evidence (2026-09-08):
The design derives `gamma_15*(89/64)*M_j` for the inspected arithmetic graph
under exact differences/denominators and the standard relative-roundoff model.
Six numerator products, one denominator product (inverse error factor), division,
state multiplication and six additions give at most 15 factors per source term.
The once-rounded rational oracle adds at most `u*(89/64)*M_j`, covered by
`gamma_16*(89/64)*M_j` since `gamma_15+u <= gamma_16`, with `u=2^-53`.
The derivation uses Higham's product/inverse-factor lemma, not statistical error
assumptions or a fitted multiplier.

The replay now checks exact timestamp/denominator arithmetic and every remaining
operation against its exact Fraction result and the unit-roundoff condition.
The rational oracle checks its final float conversion too. Negative controls
reject underflow-to-zero, nonfinite output and excessive relative error; exact
factor-product controls check the 15/16-factor envelopes. All 304 native state
requests satisfy the exact rational componentwise envelope, retaining 304 exact
matches with the replay. Conservative L1 envelope maxima were `0.005314723 m`
(Saturn) and `2.332407e-10 m/s` (Mercury), rounded upward here. These are
conditional rounding allowances, not SPICE approximation or trajectory errors.

Reproduce with
`conda run -n space-nav python -m pytest -q tests/test_trajectory_ephemeris.py`
(36 tests). The full-candidate JSON reports per-body conditional position/
velocity envelopes separately from sampled errors. Native compiler/runtime
premises and exceptional-arithmetic exclusion over unsampled epochs still need
justification before any uniform native certificate. The test-only assessment
adds no runtime safety fallback and changes no scientific tolerance, force model,
work limit or deadline. Task 3.9 remains open.

Task 3.9 native arithmetic-graph replay evidence (2026-09-08):
Test-only `_replay_lagrange_state` follows the inspected header's denominator
product order, repeated numerator, division and six sequential state multiply/
add terms, with an exact-knot shortcut. Explicit Python float operations avoid
compensated `sum` and implicit fused multiply/add. Affine and cancellation
controls independently compare the replay with the rational oracle at knots
and interior points within `1e-12` in each SI component; knot values are exact.

The existing real eight-body fixture now records `300s_source_replay` errors
and `source_replay_exact_state_matches`. All 38 states per body, 304 total,
matched the native six-component values exactly in this run: maximum position
and velocity discrepancies were zero. The unchanged sampled allocation remains
the numerical acceptance gate; exact-match counts are reported as evidence,
not silently promoted into a cross-platform contract. Reproduce with
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py -k 'replay or full_candidate'`
(three tests). Existing output includes platform/software/kernel provenance.

This connects the inspected arithmetic graph to representative pinned native
outputs; it is not proof of all compiled paths, runtime rounding modes, absence
of exceptional arithmetic, or a uniform forward-error bound. Those premises
and SPICE approximation error remain separate work. No runtime ephemeris,
scientific tolerance, force model or work limit changed; task 3.9 stays open.

Task 3.9 six-node amplification evidence (2026-09-08):
The uniform middle-cell basis has signs `(+,-,+,+,-,+)`. Using partition of
unity and factoring its two negative weights gives the exact absolute-weight
sum `Lambda(u)=1+w*(6+w)/4`, `w=u*(1-u)`. Since `0<=w<=1/4`, its sharp maximum
is `89/64=1.390625` at the midpoint. The design records the algebraic proof;
exact rational evaluations at 33 points check the identity, signs, partition
of unity and attaining case (the grid alone is not the proof of uniformity).

Four native controls use one-second/300-second grids and constant-sign or
worst-sign position perturbations. They agree with the closed formula at seven
points within `1e-12 m`. With nodal perturbation magnitude `0.125 m`, the
worst-sign midpoint is exactly `0.173828125 m`; constant-sign interpolation
remains `0.125 m`. This shows why a unit amplification factor is insufficient.
Reproduce rational and native controls with
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py -k amplification`
(five tests, JSON identifies synthetic perturbations and SI/SSB/J2000/TDB).

The result bounds amplification of already-bounded node errors under exact
interpolation on this uniform stencil. It does not give those node errors,
native evaluation roundoff, uniform SPICE approximation or boundary-spline
behavior. No unused runtime helper, force change, tolerance relaxation or new
work limit was introduced. Task 3.9 remains open pending the complete error
argument and full-force interval qualification.

Task 3.9 binary64 arithmetic-premise evidence (2026-09-08):
`test_pinned_grid_binary64_arithmetic_matches_exact_rationals` replays the
installed source's repeated time addition for all 83933 nodes in the padded
candidate grid `[978992455.2304223, 1004172273.4122404) TDB s`, step `300 s`.
Every represented grid epoch equals its exact Fraction expression. All eight
body settings share the grid. Positive interval endpoints satisfy the factor-
of-two condition for exact binary64 subtraction of represented timestamps;
the test additionally checks knots, midpoints and adjacent-representable query
times in first/middle/last six-node windows.

Every denominator product intermediate in those windows equals exact rational
arithmetic. The independent factorial formula gives maximum absolute denominator
`291600000000000 s^5`, below `2^53`. Counterexamples with a `0.1 s` increment
and widely separated operands prevent generalizing exactness to arbitrary grids.
The shared budget/counters are preserved. Reproduce with
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py -k binary64`
(one test). The scope is Python binary64 replay of inspected source operations,
not compiled native interpolation certification or a complete roundoff bound.

Inspected installed Tudat headers and SHA-256:
- `math/interpolators/lagrangeInterpolator.h`:
  `a038876008ef917b817c88f754a4c4a35d1e03b43f176634d66fc32445a9de4b`
- `simulation/environment_setup/createEphemeris.h`:
  `c80a0dc0b491f615232437315a6737fb95ebe886fbdd482af9b10876feab3d1d`

The source caches denominator products and evaluates a repeated numerator,
division, state multiplication and summation; those remaining operations,
compiler/runtime arithmetic, native-node provenance and uniform SPICE error
still need qualification. Exact subtraction reference:
https://flocq.gitlabpages.inria.fr/theos.html . Task 3.9 stays open; scientific
tolerances, native-call limits, forces and the 300-second deadline are unchanged.

Task 3.9 real multi-cell composition evidence (2026-09-08):
The moving-body control now includes 1800-second windows and qualifies Moon/
Mars multi-cell enclosures at departure, cruise and arrival for both 1800 s
and 86400 s. Tables use local-window defaults, not the full-mission table grid.
Each body/window uses six or 288 adjacent 300-second cells, with
SPICE nodes reused across cells, plus one composition call. Across the six
qualified windows this is 1764 local bounds and 12 compositions, not spacecraft
propagations. The shared 300-second qualification budget is preserved and all
control/native propagation counters remain zero.

At the same 35 samples per body/window, reconstructed local polynomial states
agree with native states within the unchanged `0.025 m` / `2.5e-6 m/s` allocation.
The new observed maxima were `0.000106812 m` and `1.324245e-11 m/s` (rounded
upward). Sampled native global-chord deviations fit the composed enclosure plus
`0.05 m` for midpoint/interior and endpoint-chord error contributions. Over the
three one-day controls, Moon polynomial bounds were approximately 11.16-12.95
million metres against sampled native deviations 7.84-8.06 million metres;
Mars bounds were approximately 2.44-4.63 million metres against sampled
deviations 2.01-2.89 million metres. These are curvature allowances, not
ephemeris approximation errors or spacecraft misses.

Local helper-only times were about `0.0018-0.0022 s` for six cells plus
composition and `0.0868-0.0885 s` for 288 cells plus composition, excluding
SPICE queries, native table construction and parity comparisons. They are not
whole-mission timing evidence. Reproduce deterministic scientific data and
machine-dependent timings with
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py -k moving_body`
(12 tests, six with multi-cell Moon/Mars qualification). This supports the
conditional exact-polynomial enclosure only. Uniform native/SPICE errors,
endpoint roundoff in general adapters and spacecraft integration errors remain
open; no scientific tolerance, force model, production limit or safety gate changed.

Task 3.9 adjacent-cell composition evidence (2026-09-08):
`_compose_ephemeris_chord_bounds` combines valid local Euclidean chord bounds
without any derivative or smoothness premise. Exact Fraction arithmetic gives
each knot's L1 residual from the global endpoint chord; each cell contributes
its local bound plus the larger of its endpoint residuals. Their maximum,
converted outward to float, encloses the piecewise curve's global Euclidean
chord deviation. Zero remains exact. Callers must establish shared endpoint
positions and valid local bounds; the helper does not infer those premises.

Added controls verify unequal durations, a one-metre corner with zero local
curvature, large SSB translation cancellation, affine and single-cell cases,
and correct pairing of each local bound with its own endpoint residuals. The
existing degree-six remainder control is composed across its derivative jump
and checked at 65 rational epochs against the independent closed polynomial
formula. Invalid counts/order, nonfinite/Boolean values and negative bounds
fail clearly; subnormal results stay positive and overflowing L1 composition
fails. Deadline expiration at entry, validation, residual construction,
composition and exit returns no bound. Successful composition preserves already
used control/native counters and the original deadline; it starts no propagation.
Reproduce with
`conda run -n space-nav python -m pytest -q tests/test_ephemeris_cell_bound.py`
(53 tests, including 21 composition controls). No force, tolerance or work-limit
changes. Native/endpoint/SPICE error qualification and actual multi-cell adapter
integration remain separate work; task 3.9 is open and no safe trajectory is claimed.

Task 3.9 real-node cell enclosure evidence (2026-09-08):
The existing full-candidate ephemeris control now evaluates the cell enclosure
for all eight bodies at its 38 epoch requests (304 helper calls, including
repeated cells). Every 300-second cell's native midpoint and endpoint states
are compared with the exact local polynomial under the unchanged sampled
`0.025 m` / `2.5e-6 m/s` allocation. Native midpoint chord deviation must fit
the polynomial enclosure plus `0.05 m`, the sum of midpoint and convex
endpoint-chord position allowances. This sampled comparison is not proof of
native accuracy everywhere in a cell.

Observed maximum Moon/Mars polynomial bounds were `184.070500 m` and
`68.677088 m`; sampled native midpoint deviations were `99.317044 m` and
`34.818350 m` respectively (rounded upward). Maximum new native-minus-polynomial
discrepancies across all bodies were `0.000279699 m` and `8.185453e-12 m/s`.
The 304 helper calls took approximately `0.094 s` in this local run, excluding
SPICE node queries, table construction, comparisons and propagation. Timing is
machine-dependent metadata, not a deterministic scientific result or a verified
whole-mission runtime. The single shared 300-second qualification budget was
preserved, with zero native spacecraft propagations/control evaluations.

Reproduce with
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py -k full_candidate`
(one test). Its JSON includes per-body cell counts, bound/deviation maxima,
helper-only times, software/platform and kernel provenance. No full-force
trajectory, subdivision count, uniform native/SPICE error or production safety
claim follows; task 3.9 stays open with unchanged scientific tolerances and limits.

Task 3.9 exact single-cell chord enclosure evidence (2026-09-08):
`_ephemeris_cell_chord_bound` encloses the exact degree-five position polynomial
of six finite ordered SI/SSB/J2000 nodes over a positive-duration TDB subinterval
inside the middle node pair. It builds normalized Lagrange power coefficients,
subtracts the endpoint chord and converts to Bernstein coefficients using exact
Fraction arithmetic. The maximum coefficient L1 norm encloses Euclidean chord
deviation over the entire cell subinterval by the convex-hull property; only the
final float conversion is rounded outward. This deliberate conservative norm
avoids additional square-root rounding. Affine motion returns exactly zero.

`tests/test_ephemeris_cell_bound.py` verifies degree-zero through degree-five
monomial hulls against exact binomial coefficients on 1-second and 300-second
grids; quadratic subinterval scaling; exact cancellation of large SSB offsets;
and independent rational Lagrange defects at 33 points on an irregular grid.
It rejects malformed, nonfinite, Boolean, unordered and cross-cell inputs,
preserves a positive subnormal enclosure, and rejects a finite-input example
whose analytic midpoint L1 defect already exceeds float range. Shared-budget
expiration at entry, during either coefficient pass and at exit returns no
bound and leaves native/control counters unchanged. Reproduce with
`conda run -n space-nav python -m pytest -q tests/test_ephemeris_cell_bound.py`
(32 tests). No scientific tolerance, native-call limit or deadline changed.

The mathematical interval claim applies only to the exact polynomial of the
supplied binary nodes, not native floating evaluation, true SPICE motion or a
spacecraft path. Node extraction/provenance, cross-cell composition, uniform
ephemeris error and integration error still need qualification. This helper is
not wired into production safety screening, and task 3.9 remains open.

Task 3.9 grid-switch regularity evidence (2026-09-08):
`test_native_ephemeris_grid_switch_does_not_guarantee_smooth_position` uses
native six-point tabulation on analytic `x=u^d m`, `u=t/h`, with consistent
sampled `vx=d*u^(d-1)/h m/s`, degrees five/six and `h=1 s` / `300 s`.
At `u=1`, adjacent position polynomials share the same position. For degree
six the exact local polynomial is `u^6-product(u-node)`; differentiating its
node product gives left/right position derivatives `-6/h` and `18/h m/s`,
while the independently interpolated velocity is `6/h m/s`. Thus the
300-second control has a `0.08 m/s` derivative jump and returned velocity
`0.02 m/s`. These are analytic control values, NOT measured mission jumps.
The degree-five control has matching derivatives and velocity `5/h m/s`.

Native evaluations on both sides at normalized offsets `1/4096` and `1/8192`
agree with the exact rational remainder within `1e-10 m` and `1e-10 m/s`.
Native secants agree with exact secants within `1e-6 m/s`; their analytic
derivative-limit approximation allowance is `0.05/h m/s`, not a mission
tolerance. Reproduce all four controls and their SI/SSB/J2000/TDB JSON evidence:
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py -k grid_switch`.

This rules out assuming bounded classical second derivative across all knots
or using the returned velocity as the position derivative. Future interval
enclosures must work cellwise or include derivative jumps; splitting the
mathematical enclosure need not restart native spacecraft propagation at each
ephemeris knot. Real mission jump magnitudes, rounding and uniform SPICE error
remain unqualified. Task 3.9 stays open with unchanged production limits,
300-second budget, forces and scientific tolerances.

Task 3.9 local ephemeris polynomial evidence (2026-09-08):
The pinned headers `simulation/environment_setup/createEphemeris.h` and
`math/interpolators/lagrangeInterpolator.h` specify six stages and the interior
window from lower-knot index minus two through plus three. Six nodes define
degree five (the documentation also uses the ambiguous phrase "6th order").
The runtime factory exposes the base Python ephemeris without its interpolation
nodes, so qualification reconstructs the existing grid from settings and direct
SPICE; production still uses the unchanged native ephemeris.

The test-only `_rational_lagrange_state` computes exact Fraction weights and
weighted binary state sums before final float conversion. Six analytic controls
verify degrees zero through five at knots and off-grid points within `1e-12`
in each SI component. The existing full-candidate test checks all eight bodies
at all 38 recorded epochs, with windows strictly inside the padded table.
Maximum sampled native-minus-rational differences were `0.000258951 m`
(Saturn) and `1.499978e-11 m/s` (Mercury), rounded upward here. They pass the
unchanged sampled allocation `0.025 m` / `2.5e-6 m/s`; these maxima are not
new tolerances or uniform bounds. Reproduce with
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py`
(16 tests; output includes per-body `300s_rational_polynomial` measurements).

This supports further interval work on the represented position polynomial,
not an all-interval SPICE approximation or floating-point error certificate.
Velocity is interpolated independently; it is not assumed to be the derivative
of interpolated position. Boundary spline behavior, grid-switch behavior,
native roundoff and numerical spacecraft error remain separate obligations.
Task 3.9 stays open; no production forces, tolerances, call limits or deadlines
changed. API context: https://py.api.tudat.space/en/latest/math/interpolators.html
and https://py.api.tudat.space/en/latest/dynamics/environment_setup/ephemeris.html
(the installed headers and native tests resolve the pinned implementation).

Task 3.9 complete-force bound composition evidence (2026-09-08):
`_sum_force_acceleration_bounds` combines all eight ordered gravity sources,
phase-specific thrust, fully lit SRP and Sun Schwarzschild by the triangle
inequality. Exact binary-to-Decimal conversion, upward-rounded summation and
outward float conversion prevent a rounded-down total. Missing, extra or
reordered sources, invalid component values, inconsistent coast/burn thrust
and overflow fail clearly. Checks during collection and after summation reuse
the caller's shared deadline without starting propagation or changing counters.

Exact rational sum tests cover disparate magnitudes and caller Decimal-context
isolation. Existing native complete-force near-Moon/cruise/near-Mars controls
check the composition for coast and both burn phases, retaining their original
independent force-parity tolerances. Reproduce with
`conda run -n space-nav python -m pytest -q tests/test_trajectory_gravity_bound.py tests/test_trajectory_gravity.py`
(90 tests). Fixed-state distance/speed margins are test premises, not interval
proofs. This conditional sum neither audits native model configuration nor
encloses body motion or numerical trajectory error. Task 3.9 remains open;
no full-force safe interval, subdivision timing or targeting readiness is claimed.

Task 3.9 Schwarzschild-component enclosure evidence (2026-09-08):
`_schwarzschild_acceleration_upper_bound` implements the derived orientation
maximum `GM/(c^2*r_min^2)*(4*GM/r_min+3*V_max^2)` for the declared Sun-only
PPN beta=gamma=1 model. It requires an explicit positive distance floor and
nonnegative Sun-relative speed ceiling, uses the existing SI light speed and
isolated upward-rounded 50-digit Decimal arithmetic, and rounds the returned
float outward. It neither queries ephemerides nor changes native PPN globals.

`tests/test_trajectory_relativity.py` compares the scalar expression with exact
rational arithmetic at zero, 5 and 50000 m/s, verifies an independent rational
vector expression attains the orientation maximum for radial motion, checks
distance/speed monotonicity and caller-context isolation, and rejects invalid
inputs and overflow while preserving positive subnormal bounds. The existing
native fixed-state formula comparison now covers oblique, radial, transverse
and zero relative velocities with its unchanged `max(1e-15 m/s^2, 1e-12*norm)`
parity tolerance; all four native norms lie below the component bound. Reproduce
with `conda run -n space-nav python -m pytest -q tests/test_trajectory_relativity.py`
(30 tests). These are component controls, not a full-force propagated interval.
The distance/speed floors/ceilings, native force error, body motion and numerical
trajectory error still need independent interval justification. No force model,
PPN setting, propagation budget or scientific tolerance changed; task 3.9 remains
open and the targeting spike remains gated.

Task 3.9 thrust/SRP component enclosure evidence (2026-09-08):
`_thrust_and_srp_upper_bounds` returns separate orientation-independent
maximum-thrust and fully lit cannonball SRP bounds using dry mass and an
explicit minimum Sun distance. Coast thrust is exactly zero. The rational
`pi > 3` SRP enclosure is approximately 4.72% conservative relative to the
fully lit model; only the bounding calculation uses it, not the native force.
Like the harmonic helper, positive arithmetic is rounded upward in an isolated
50-digit Decimal context and final float conversion is outward. The exact SI
speed of light `299792458 m/s` is checked against the pinned Tudat constant.

`tests/test_trajectory_radiation.py` compares both formulas against exact
rational arithmetic, checks mass/distance scaling, explicit burn/coast flags,
ambient-context isolation, subnormal rounding, invalid contributing fields,
wrong record type and overflow. Existing native clear/umbra/penumbra controls
and the clear control at dry mass verify their acceleration norms stay below
the bound, retaining all original force-parity tolerances. Reproduce with
`conda run -n space-nav python -m pytest -q tests/test_trajectory_radiation.py`
(42 tests). Shadows at a sample cannot lower the interval allowance. The caller
still must prove mass/distance floors and include gravity, relativity, body
motion, native evaluation error and trajectory error. No native-call limit,
mission force, integration tolerance or safety status changed; task 3.9 is open.

Task 3.9 harmonic-component enclosure evidence (2026-09-08):
`_harmonic_acceleration_upper_bound` implements the addition-theorem/Frobenius
bound derived in the design for matching square 4pi-normalized C/S arrays.
It validates all coefficients and scientific scalars, includes degree zero
once, and uses outward-rounded nonnegative Decimal arithmetic before outward
conversion to binary float. Its 50-digit arithmetic context is isolated from
caller precision, rounding and traps; it does not alter integration tolerances.
At the pinned guard radii the returned bounds are `1.9198975285390047 m/s^2`
for Moon degree 200 at `1737400 m`, and `3.8745596511191156 m/s^2` for Mars degree
120 at `3396190 m`. Local helper-only timings were approximately `0.046 s` and
`0.016 s`, excluding file hashing/loading; these are not mission-runtime evidence.

`tests/test_trajectory_gravity_bound.py` verifies a monopole against exact
rational arithmetic (including subnormal output), the degree-0/2 expression
against an independent 100-digit calculation, distance/GM scaling, zero fields,
ambient-context isolation, malformed/non-finite/boolean inputs and overflow.
The existing native fixed-state gravity test additionally checks Moon/Mars
component norms near Moon, in cruise and near Mars against the bound without
new propagation fixtures. Reproduce with `conda run -n space-nav python -m pytest
-q -s tests/test_trajectory_gravity_bound.py tests/test_trajectory_gravity.py`
(62 tests). This encloses only the declared finite mathematical gravity field;
callers still need proven distance floors, native force-evaluation error,
other forces, moving-body enclosures and trajectory integration error. No safe
trial, production subdivision limit or complete task 3.9 is claimed.

Task 3.9 moving-body prerequisite evidence (2026-09-08):
`tests/test_trajectory_ephemeris.py::test_moving_body_chord_deviation_is_not_interpolation_error`
compares actual eight-body Tudat tables with direct SPICE in nine windows:
departure, midpoint cruise and arrival, each lasting 30 s, 300 s and 86400 s.
Each window has 35 epochs including endpoints, midpoint and off-grid samples;
the original qualification fixture supplies the candidate interval. Tables use
the production 300 s factory and SI/SSB/J2000/TDB conventions, but are built for
these local windows, not reused from the complete mission table. Coverage and
the existing `0.025 m` / `2.5e-6 m/s` sampled input allowances are checked;
maximum measured differences are `0.003881 m` and `9.038e-7 m/s` (rounded up).
The defect of a chord built from tabulated positions differs from the direct
SPICE defect by at most `0.05 m` at these samples, the triangle-inequality
allocation of twice the unchanged input position allowance.

Moon centre motion deviates from its SSB endpoint chord by approximately
`0.958-0.973 m` over 30 s, `95.77-97.25 m` over 300 s and `7.84-8.06e6 m` over
86400 s across these windows. Mars gives `0.242-0.348 m`, `24.19-34.82 m` and
`2.01-2.89e6 m`, respectively. These are body-motion measurements, not spacecraft
trajectory errors, and sampled maxima are lower bounds on a required enclosure,
never certified upper bounds. Reproduce with `conda run -n space-nav python -m
pytest -q -s tests/test_trajectory_ephemeris.py -k moving_body` (nine tests).
The test adds no dynamics model, tolerance, kernel, interpolation or runtime-limit
change. Next derive an all-epoch body-motion enclosure (including interpolation
stencil/edge behavior) and a spacecraft enclosure with full-force and numerical
error control; do not substitute these sample maxima for either. Task 3.9 and
all existing continuous-safety/targeting gates remain open.

Task 3.8 analytic subdivision evidence (2026-09-08):
`tests/test_native_adaptive_safety.py` reuses the native coast integrator and
shared budget with a stationary lunar guard sphere and known constant relative
acceleration, not the mission force model. Straight impact requires five native
calls, curved impact two, and both clear controls one each. Tangency remains
unresolved after eight calls at depth six and returns no trajectory. Every
discarded parent counts. The measured maximum endpoint position error is
`2.794e-9 m`, below the independent `0.001 m` allowance; velocity error is checked
against `1e-6 m/s`. A local run takes approximately `0.34-0.37 s` per normal
control including resource loading; these machine-dependent toy timings are not
full-force performance evidence. Forced two-call exhaustion and injected
300-second deadline expiry raise the existing domain error with no terminal
result. Budget tests separately exercise the 32-call override and unchanged
production limits. Reproduce with `conda run -n space-nav python -m pytest -q -s
tests/test_native_adaptive_safety.py tests/test_trajectory_budget.py` (27 tests).
Task 3.9 remains open: no full-force acceleration/ephemeris error bound or new
production native-call limit has been established.

Task 3.7 native-event qualification (2026-09-08):
The same test module now qualifies native `relative_distance` termination with
and without exact event localization. On the unchanged nominal coast profile,
a zero-force Moon-sphere crossing over `[100,500] s` is detected at the first
`300 s` step; ordinary termination stops inside, while exact termination with
bisection (`1e-12 s` root-time tolerance, 100-iteration throw-on-failure cap)
locates entry at `100 s` within `1e-6 s` and the surface within `1e-6 m`.
For the existing `[3,20] s` gap crossing, both settings miss the impact and
finish at `600 s`. All saved states satisfy the same `1e-6 m` straight-line
oracle. These root-finder settings are test-only, not a new production tolerance.
This agrees with the documented ordering: event localization follows a detected
termination condition, rather than continuously searching every step for roots
([Tudat propagation architecture](https://docs.tudat.space/en/latest/user-guide/state-propagation/propagating-dynamics/propagation-architecture.html)).
The pinned native interface confirms that custom blockwise step control chooses
error-norm blocks, not an arbitrary state-dependent step-size policy. This
investigation does not prove every possible Tudat extension inadequate, but
rules out enabling exact distance termination alone as the fix. Task 3.7 and
the spike prerequisites remain open; production behavior and resources are unchanged.
All eight focused sampling/event controls and 600 project tests pass, as do
Ruff, strict OpenSpec validation and the unchanged legacy checksum. Passing
characterization tests is not completion of the continuous-collision gate.

Task 3.7 between-stage counterexample (2026-09-08):
`tests/test_native_safety_sampling.py` now also uses the unchanged nominal coast
integrator with its `300 s` first step. The test-only zero-force straight line
starts at `x=-2350600 m`, `vx=204400 m/s` relative to a stationary sphere with
the pinned Moon radius `1737400 m`. It enters at `3 s`, crosses the centre at
`11.5 s`, and exits at `20 s`. Both endpoint-only and stage-latched guards miss
this crossing: no evaluated acceleration-stage epoch lies in `[3,20] s`, no
impact is latched, and native propagation reports successful completion at
`600 s`. All saved positions agree with the independent straight-line solution
within the existing `1e-6 m` test bound and lie outside the sphere. The earlier
burn-step crossing remains a positive control for stage latching.
This reproducible counterexample rules out stage latching alone, not the
possibility of a continuous guard. It is not a physical Moon-to-Mars trajectory
and changes no mission force, integrator, threshold or resource. Task 3.7 remains
open and the targeting spike remains blocked by its existing safety prerequisite;
do not interpret a null sampled rejection or successful integration as safety.
All four sampling characterization cases and 596 project tests pass, as do
Ruff, strict OpenSpec validation and the unchanged legacy checksum. Passing
these regression tests reproduces the unsafe sampling behavior; it does not
satisfy the continuous-safety acceptance criterion.

Tasks 3.5/3.7 environment-sample prerequisite evidence (2026-09-08):
`_classify_environment_trial_state` reads all eight native environment ephemerides
at an explicit covered TDB epoch and delegates to the existing SI/SSB/J2000
sample classifier. It validates state/mass/frame/epoch before native reads,
rejects missing or non-finite ephemerides with body context, and checks the same
shared budget around native queries. It neither propagates nor increments work
counters, making it suitable for an initial-state check before the first arc.
Injected tests cover interval endpoints, uncovered epochs, invalid inputs,
native failure, expiry, mass precedence and body ordering. Real off-grid checks
use direct SPICE positions to place states 1 m inside/outside each of the eight
pinned spherical surfaces and obtain the expected classification from the
native time-limited environment. No resources or tolerances changed.
This remains a single-sample adapter: the production driver must call it before
launching an arc, and continuous collision guards are still required. Tasks
3.5 and 3.7 remain open; no full-mission safety or target closure is claimed.
All 79 focused checks and 594 project tests pass, as do Ruff, strict OpenSpec
validation and the unchanged legacy checksum. Existing classification and
budget components were reused without new dependencies.

Task 3.7 outcome-precedence evidence (2026-09-08):
`_read_trial_arc_outcome` consumes an independently established physical safety
reason before the final-epoch/history reader. A successful native safety stop
returns only its validated dry-mass or one-of-eight-body impact reason, never
the unsafe state history. Invalid reasons are errors, and an unsuccessful or
unreadable native completion flag remains fatal even with a safety reason.
With no rejection, the existing strict completion reader is reused unchanged.
Injected property traps prove rejected/failed histories are not read; the
existing native stage-latch characterization verifies an actual early impact
stop is rejected rather than mislabeled as a final-epoch mismatch. The caller
must still discard its native simulator and establish safety independently:
this gate does not detect collisions or certify that a null reason is safe.
Continuous guards, initial-state guards, rejection counters and production
driver wiring remain open; tasks 3.5 and 3.7 are not complete. No scientific
constants, tolerances, dependencies or UI behavior changed.
All 43 focused checks and 579 project tests pass, as do Ruff, strict OpenSpec
validation and the unchanged legacy checksum.

Task 3.4 native-handoff prerequisite evidence (2026-09-08):
`tests/test_native_arc_handoff.py` chains the existing TNW engine installer,
coupled seven-state settings, integrators, shared-budget runner and completion
reader across departure burn, coast and arrival burn. Each arc uses a fresh
body system configured at `2000 kg`, while propagated mass begins at `1500 kg`
and is passed on without reset. The isolated fixture uses test-only stationary
Moon/Mars references with GM `1 m^3/s^2` to trigger native reference updates;
their velocity perturbation is below `1e-9 m/s` over the less-than-1200-second
fixture. These are not mission ephemerides or production force settings.
Both nominal and tighter profiles pass with `0.25 s` and `1000.5 s` coasts,
`100.25 s` departure and `50.25 s` retrograde arrival burns, starting at
`1000000000 TDB s`. Initial arc state matches the preceding terminal state
within `1e-6 s`, `0.001 m`, `1e-6 m/s` and `1e-9 kg`; coast mass is unchanged.
An independent closed-form displacement integral and signed rocket equation
check every endpoint to `0.001 m`, `1e-6 m/s` and `1e-8 kg`. Work accounting is
one control, one evaluation and three native calls. Production code, resources,
tolerances and UI are unchanged. Task 3.4 stays open: this test-only sequence
does not provide the safe full-force executor, public burn records or closure.
All four focused controls and 560 project tests pass, as do Ruff, strict
OpenSpec validation and the unchanged legacy checksum.

Task 3.6 burn-force assembly evidence (2026-09-08):
`_build_arc_force_models` reuses the verified external-force mapping and adds
exactly one Spacecraft self-source thrust term for the selected installed
`departure-main` or `arrival-main` engine. Coast explicitly selects no thrust,
even with an installed engine. Invalid burn identifiers fail before native
imports, and a missing selected engine fails with its original native cause;
there is no substitution of another engine. Existing callers default to coast.
Native near-Moon, cruise and near-Mars checks compare total acceleration with
independently assembled external forces plus analytic `thrust / current_mass`
times the signed TNW direction, using the unchanged force tolerance
`max(1e-15 m/s^2, 1e-12 * sum(component norms))`. They also verify a poisoned PPN
state is reset for both burns and coast. No dependency or integration tolerance
changed. Near-body test inputs now include transverse relative velocity of
`1500 m/s` so the TNW frame is non-degenerate; production mission inputs and
resources are unchanged. This supplies the complete force assembly but not the three-arc driver,
continuous safety or target closure; task 3.6 remains open for driver wiring.
All 70 focused force/burn checks and 556 project tests pass, as do Ruff, strict
OpenSpec validation and the unchanged legacy checksum. The existing force
assembler and installed-engine adapter were reused without new dependencies.

Task 4.10 environment-budget evidence (2026-09-08):
`_build_physical_environment` accepts the existing budget without constructing
or resetting it. Cooperative checks bracket resource hashing, kernel setup,
coefficient loading, native body construction and force preparation. A call
already in progress cannot be interrupted; its late result is discarded before
the next stage or environment return. Preparation does not increment control,
evaluation or native-arc counters. Existing component callers without a budget
remain compatible; the future mission driver must supply the shared budget.
Injected-clock expiry tests cover initial entry, hashing, ephemeris settings,
harmonic loading, body creation and final force preparation; the real one-day
environment check also verifies unchanged deadline and zero propagation counts.
No scientific settings, tolerances, dependencies or UI changed. Task 4.10 stays
open for end-to-end orchestration and final-output checks; this is not evidence
that the full 291-day environment or a targeted mission meets 300 seconds.
All 31 focused checks and 535 project tests pass, along with Ruff, strict
OpenSpec validation and the unchanged legacy checksum.

Task 4.10 native-runner evidence (2026-09-08): `_run_native_arc` now uses the
existing budget before lazy simulator import, immediately before a counted
native call, and after native completion. Import failure consumes no arc;
native failure or an early-terminated call consumes one. Deadline expiry after
the native call raises without returning its result. All 36 burn controls,
four conservative-orbit controls and both safety-sampling characterizations
now execute through this runner with explicit counter assertions. Injected
tests cover initial expiry, import-time expiry, native-time expiry and original
exception chaining. The returned native object is deliberately unclassified:
safety rejection must still precede the separate completion/epoch reader.
This does not solve continuous collision safety or provide the three-arc
executor. Resource/final-output budgeting and overall orchestration remain
pending; 4.10 stays open. Existing components were reused without changing
dependencies, force settings, integrator tolerances or the UI.
All 48 focused runner/native-science checks and 529 project tests pass, as do
Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 4.10 budget-accounting evidence (2026-09-08): `_RefinementBudget` is an
internal mutable work ledger with a single finite monotonic deadline. It counts
controls before analytic validation and evaluations only with their first native
arc. It enforces caps 73/76/228 without incrementing rejected over-limit calls,
accepts early-terminated evaluations, and lets frozen diagnostics consume arcs
without another control attempt. Continuation arcs require a started evaluation
and cannot exceed three arcs in that evaluation. Deadline errors include the
runtime limit and all three attempted-work counters, with no partial result.
Injected-clock tests cover exact expiry, no deadline reset, non-finite/backward
clock values, analytic rejection, partial impact, frozen diagnostics and every
cap. This is cooperative accounting, not interruption of an active native call.
Wiring the ledger around resource construction, native arcs and final output is
still pending; task 4.10 remains unchecked. No dependencies or science changed.
All 13 focused budget checks and 523 project tests pass, as do Ruff, strict
OpenSpec validation and the unchanged legacy checksum.

Task 4.10 handoff deadline evidence (2026-09-08): the private M2 search now
accepts an inherited absolute monotonic deadline and uses the earlier of that
deadline and its own scenario budget. `_verify_candidate_handoff` forwards the
same deadline and optional injected clock without restarting the remaining
budget. An expired or malformed inherited deadline fails before time conversion
or resource loading. Deterministic tests verify expiration after one candidate,
non-extension by a later inherited deadline, zero scientific work on initial
expiry, exact handoff forwarding and chained M3 failure. Public M2 signatures,
default behavior and scientific outputs remain unchanged. This is only handoff
plumbing: the top-level shared budget, resource/native-call checks, complete
attempt/evaluation/arc counters and final manifest checks are still pending.
Task 4.10 remains unchecked; no targeting run is authorized by this step.
All 55 focused M2/handoff checks and 510 project tests pass, as do Ruff,
strict OpenSpec validation and the unchanged legacy checksum. Existing clock
injection and search checks were reused; no new dependency was introduced.

Task 4.2 completion evidence (2026-09-08, supersedes earlier pending notes):
`_build_initial_burn_controls` composes the existing direction, sequential
duration and analytic-domain helpers using the same local orbit conversion and
explicit harmonic-field GMs as the physical boundary builder. Local states are
computed directly rather than subtracting large SSB positions. The real M2
candidate `d0001-t0035` produces repeatable controls for the 500 kg dry-mass
fixture and an internal dry-mass rejection for the preserved 1000 kg fixture.
Independent direct Tudat element conversion and cross-product reconstruction
confirm both signed directions within `1e-12`. Conversion failures retain their
original cause. Together with the existing 91 component checks, this completes
the initial-control construction criterion, not the safety or convergence gate.
Candidate verification and resource validation remain caller prerequisites;
this helper neither searches again nor propagates a trajectory. Counter and
deadline integration remain task 4.10; tasks 3.4-3.7 still prevent the targeting
spike. No physical model, numerical tolerance, dependency or UI was changed.
All 32 focused fixture/handoff checks and 500 project tests pass, as do Ruff,
strict OpenSpec validation and the unchanged legacy checksum.

Task 4.2 analytic control-gate evidence (2026-09-08):
`_prepare_burn_controls` validates all six finite inputs before rejection,
canonicalizes azimuths with stdlib remainder, enforces elevation and strictly
positive burn/coast intervals, and checks the analytic constant-flow terminal
mass against dry mass without clamping. A positive duration that rounds to
the same floating-point epoch is rejected as a zero-length represented arc.
Valid controls return an immutable canonical tuple; domain violations return
internal `rejected-control-bounds` or `rejected-dry-mass`, never a public mission
status. Malformed/non-finite inputs remain chained fatal errors. Tests cover
both sides and equality of the coast and dry-mass boundaries, angle wrapping,
repeatability, both sub-epoch-resolution burns, and invalid inputs. No native
propagation or new dependency is involved. Seed assembly with the verified
physical boundaries and wiring of attempt counters remain pending, so 4.2
stays open and targeting is not enabled. No existing tolerance was relaxed.
All 91 focused controls/seed/guidance checks and 499 project tests pass,
as do Ruff, strict OpenSpec validation and the unchanged legacy checksum.

Task 4.2 direction-seed evidence (2026-09-08): `_seed_burn_angles_rad`
projects normalized departure excess velocity and negative arrival excess
velocity into the supplied physical boundary TNW frame. It reuses the checked
basis builder, applies the specified atan2 formulas, maps positive pi to
negative pi, and rejects degenerate frames and non-finite or at-most-`1e-12 m/s`
excess norms. Tests reconstruct the signed inertial unit direction through an
independent cross-product oracle within `1e-12`, covering both burns, oblique
frames, azimuth wrapping and polar directions. Outputs are repeatable and stay
in the prescribed angle domains. Correct physical boundary selection and the
remaining control/window/dry-mass validation still need composition; task 4.2
stays open. No native setup, dependency or scientific tolerance changed.
All 58 focused guidance checks and 479 project tests pass, as do Ruff, strict
OpenSpec validation and the unchanged legacy checksum.

Task 4.2 duration-seed evidence (2026-09-08):
`_seed_burn_durations_s` implements the declared sequential exponential mass
loss and constant-thrust duration formulas using the existing standard-gravity
constant and immutable spacecraft parameters. It returns an immutable pair in
seconds, keeps zero seeds zero for later control-domain rejection, and rejects
negative, boolean, nonnumeric or non-finite impulses with chained context.
An independent 50-digit Decimal oracle agrees within `1e-6 s` for two burns
and zero-departure/zero-arrival boundaries. Repeatability and the use of the
post-departure mass for the arrival duration are checked. These seeds are not
a dry-mass/window or finite-burn feasibility certificate. Steering projection,
control-domain validation and integration remain pending, so 4.2 stays open.
No dependencies, scientific constants or tolerances changed.
All 13 focused checks and 458 project tests pass, as do Ruff, strict OpenSpec
validation and the unchanged legacy checksum.

Task 3.7 native sampling evidence (2026-09-08):
`tests/test_native_safety_sampling.py` propagates a test-only zero-force line
through the verified Moon collision sphere during `0.25..0.75 s`, using the
unchanged nominal burn integrator and production translation/mass composition.
Both initial and saved step-end positions lie outside the sphere. A native
custom termination that checks only the current full-step state misses the
crossing and successfully reaches `2 s`. An experimental latch in the
zero-acceleration callback observes internal stages and stops before `2 s`,
despite the final saved position again being outside. The straight-line oracle
matches saved positions within `1e-6 m`; both characterization tests pass.
This records an inadequate approach, not a deployed safety algorithm. A stage
latch alone can still miss crossings between stages and can reject tentative
stages of adaptive steps that would later be discarded. Production safety
requires a justified between-step strategy plus initially unsafe-state and
termination-precedence handling; task 3.7 remains unchecked. No force,
integrator setting or scientific tolerance was changed to hide this limitation.
Both focused controls and all 445 project tests pass, as do Ruff, strict
OpenSpec validation and the unchanged legacy checksum.

Task 3.5 sample-classification evidence (2026-09-08):
`_classify_trial_state` reuses the verified collision spheres and finite-state
validation to return an internal rejection reason or no rejection for one
SI/SSB/J2000 sample. All eight positions and surfaces are required and validated
before classifying; malformed/non-finite data remains a chained fatal error,
even when mass is already unsafe. Mass strictly below dry mass is rejected;
equality is allowed. Surface equality is impact. Simultaneous violations use
dry-mass precedence, then the fixed physical-body order, independent of input
dictionary order. Tests cover each sphere at radius minus one meter, radius,
and radius plus one meter, dry-mass boundaries, simultaneous violations and
invalid inputs. No state is clamped, mutated or retained by this pure helper.
This is only a single-sample check: native safety termination, between-step
impact detection, rejection counters and history disposal remain unfinished.
Tasks 3.5 and 3.7 therefore remain unchecked; no mission safety is claimed.
All 64 focused checks and 443 full-suite tests, Ruff, strict validation and
the unchanged legacy checksum pass; no scientific tolerance was modified.

Task 3.2 completion evidence (2026-09-07, supersedes earlier pending notes):
`_build_coupled_arc_settings` now constructs the shared seven-state native
translation/mass setup using thrust-derived mass loss or explicit zero coast
mass rate. It validates finite handoff state/mass/epoch and SSB/J2000, preserves
the supplied integrator and termination settings, and chains native setup
failures. All 36 native burn controls now use this production composition,
including initial propagated masses of `2000 kg` and `1500 kg` while the native
body starts configured at `2000 kg`. Existing mass, rocket-equation and TNW
direction tolerances all pass; four ten-orbit coast controls use the same
composition and preserve mass exactly. Eleven invalid-input/native-error
checks pass. All 406 project tests, Ruff, strict validation and the unchanged
legacy checksum pass. Existing Tudat factories and science fixtures were reused; no
dependency, scientific constant or tolerance changed. This completes the
engine/coupled-settings component, not the segmented executor: the caller must
provide matching force/thrust and safety-termination settings. Tasks 3.4-3.7,
the shared deadline and targeting prerequisites remain open.

Task 3.6 assembly evidence (2026-09-07): `_build_arc_force_models` concatenates
the verified external-force settings without mutating them: three Sun terms,
one Moon harmonic term, one Mars harmonic term, and five other point terms.
It resets and reads back global PPN immediately before native model creation.
The existing fixed-state gravity oracle now also tests the combined model at
near-Moon, cruise and near-Mars states against separately configured native
gravity/SRP/Schwarzschild components within the unchanged
`max(1e-15 m/s^2, 1e-12 * sum(component norms))` tolerance. Each combined setup
recovers from deliberately poisoned PPN values. Injected checks verify call
ordering, immutable input mappings, duplicate/misplaced terms, and chained
import/PPN/native-construction errors. All 28 focused and 373 full-suite tests,
Ruff, strict validation and the unchanged legacy checksum pass. No dependencies
or physical constants changed; existing component factories and the fixed-state
oracle are reused without a new force abstraction.
This bounded component excludes engine thrust; task 3.6 stays open
until the segmented executor calls it at every arc boundary. The targeting
spike remains blocked on the listed prerequisites.

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
- [x] 4.2 Implement the exact signed excess-velocity TNW projections, canonical angle domains, strict positive burn/coast window, analytic dry-mass domain, and sequential rocket-equation duration seed; verify formulas, direction signs, boundary equality rejection, degeneracy errors, `0.000001 s` duration agreement, and repeatability.
- [ ] 4.3 After tasks 2.7, 3.1-3.9, 4.1, 4.2, and shared-deadline plumbing in 4.10, run a reproducible targeting spike for provisional candidate `d0001-t0035` with the exact production force model, seed, corrector constants, eight-iteration/76-evaluation limits, and 300-second deadline; check in its script and machine-readable controls, residuals, resource/machine provenance, counters, safety and timing evidence. Verify a safe complete seed and the closure gate before production corrector work; if either fails, revise and strictly revalidate the formulation instead of silently weakening a bound.
- [ ] 4.4 Implement the specified safe-seed prerequisite, scaled residual, forward-only difference increments, unavailable-column stop, trust scales, `numpy.linalg.lstsq` solve with `rcond=1e-12`, fixed damping/acceptance sequence, lexicographic safe-command tie-break, and eight-iteration/73-control-attempt cap; verify unsafe seed, unsafe probe with no backward/fictitious continuation, synthetic convergence, finite rank-loss classification, non-finite solve errors, probe exclusion, exact tie-break, cap exhaustion, and repeatability tests.
- [ ] 4.5 Add exact status/reason invariants for `converged`, `mass-infeasible` with `preflight-m2-propellant-shortfall`, and `targeting-failed` with `nonconvergence` or `no-safe-complete-trial`; verify the preserved reference candidate is preflight mass-infeasible, no-safe exhaustion has null propagated-result values plus sorted rejection counts, and no status falsely claims target closure or an executable trajectory.
- [ ] 4.6 Refine the feasible fixture candidate through both finite burns within eight iterations, 73 control attempts, 76 propagation evaluations, 228 native arc calls, and the 300-second deadline; verify status `converged`, dry-mass and collision safety, and terminal errors no greater than `1000 m` and `0.01 m/s`.
- [ ] 4.7 Repropagate tentatively closed frozen commands with the distinct tighter integrator at identical arc boundaries; verify all four structured boundary differences stay within `10 m`, `0.0001 m/s`, and `0.000001 kg`, and an exceeded bound raises `scientific-validation` without returning a status.
- [ ] 4.8 Add frozen-command Moon 400/Mars 120 and Moon 200/Mars 60 sensitivity runs; verify both ordered four-boundary diagnostic tuples are returned only on convergence, the lunar differences meet `500 m` and `0.0001 m/s` or raise `scientific-validation`, the finite Martian tail is recorded, and degree 120 is labeled as the model ceiling rather than an error bound.
- [x] 4.9 Add the isolated ten-orbit point-mass conservation fixture; verify relative specific-energy and angular-momentum-norm drift are each no greater than `1e-11` without applying that invariant to the forced mission trajectory.
- [ ] 4.10 Apply one monotonic deadline and the exact control-attempt, propagation-evaluation, and native-arc increment rules across candidate verification, targeting, partial impacts, analytic rejections, and diagnostics; verify counter fixtures and forced deadline tests report the limit plus all completed counts and return no partial result.

Task 4.1 evidence: `tests/test_m3_fixture.py` compares both raw TOML and normalized scenarios and runs both full M2 searches with real TudatPy/SPICE. Candidate `d0001-t0035` is exactly equal after changing only its budget flag, with ideal final mass between 500 and 1000 kg. This is not a finite-burn propagation test; task 4.3 remains unchecked.

Task 4.9 evidence (2026-09-07): `tests/test_trajectory_conservation.py` uses
the real SPICE Sun GM with a test-only stationary central source at SSB,
semimajor axis `149597870700 m`, inclination `pi/6 rad`, and eccentricities
`0` and `0.2`. Both unchanged production coast profiles (nominal RKF78 and
tighter RKDP87) propagate a seven-component translation/constant-mass state
for ten analytic orbital periods. At every saved state, specific energy and
angular-momentum norm agree with the independent Kepler invariants within
relative `1e-11`; mass remains exactly `2000 kg`. Successful native completion
and the existing `1e-6 s` final-epoch gate are checked before reading history.
All four controls and all 377 project tests pass, as do Ruff, strict OpenSpec
validation and the unchanged legacy checksum. No production settings, tolerances, resources or UI
were changed. This isolated conservative check does not establish conservation,
target closure or accuracy for the time-dependent, forced Moon-to-Mars mission.

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
