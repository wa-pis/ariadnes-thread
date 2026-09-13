# Ariadna Space Navigation Roadmap

## Current priority — M3 resumed (2026-09-07)

On 2026-09-09 the user approved replacing production tabulated ephemerides with
direct SPICE, preserving all tolerances and the shared 300-second deadline.
This revision is implemented and verified as task 3.10 (881 passing tests);
the historical table counterexamples below remain evidence, not a new safety
certificate. Task 3.9 remains open after the switch.

The user approved resuming M3 after prototype delivery. The prototype is archived
as `2026-09-07-refine-physical-trajectory` and synced to `visual-transfer-explorer`.
The sole active `refine-physical-trajectory` restores unfinished M3 requirements.
Ephemeris qualification (2.7) and analytic subdivision controls (3.8) are complete.
The current prerequisite is the full-force safety-envelope investigation (3.9),
authorized on 2026-09-08 without weakening scientific tolerances or the shared
300-second deadline. Other finite-burn prerequisites remain open before the
targeting spike. Preserve the UI; scheduling state is managed in the app.

Latest initial-error qualification (2026-09-13): all 21 degree-map families
close inside the unchanged domains and pass position; 19 pass velocity.
With p=0.0001 m at Mars 1/8 s, velocity bounds for initial velocity radii
0, 5e-8 and 1e-7 m/s are respectively 9.520238237331104e-7,
1.0020238251660502e-6 and 1.0520238265989898e-6 m/s. The last two
do not resolve the 1e-6 m/s gate. All eighteen shorter families pass.
This diagnoses three explicit radii; it does not imply every nonzero velocity
radius fails, nor define a mission or measurement-error allocation. The seven
nominal controls and twelve old quadratic families remain unchanged.

Retained native comparison: whole-degree composition resolves
both endpoint gates in all seven existing zero-initial-error controls.
Mars 1/8 s position/velocity bounds are 3.21149285791862e-5 m and
9.520008966984693e-7 m/s, below 0.001 m / 1e-6 m/s. Reference-only
velocity is 8.814968728961376e-7 m/s. Mars 1/16 s velocity is
2.3324000568729125e-7 m/s. C00 alone is excluded, C20 is retained once,
and no second trace-free factor is applied. All old certificates, including
their unresolved Mars 1/8 s gates, remain regressions. These are conditional
short-control bounds, not measured errors, mission accuracy or native-stage safety.

Retained analytic prerequisite: the coefficient-to-Hessian map
has orthogonal polar columns and a largest squared norm
(3/2)*(2n+1)*(n+1)^2*(n+2)^2. Combining its map norm with the trace-free
lemma gives the ideal whole-degree operator bound
GM/d^3*(R/d)^n*(n+1)*(n+2)*sqrt((2n+1)*q_n), attained by a polar zonal
field. Forty-nine analytic/rejection controls pass, including exact Rodrigues
Gram calculations at degrees 0,1,2,3,8,19,120,200 and low-degree rotation
invariance. The universal proof is documented; native use is separately
verified by the whole-degree composition above.

Retained native bound comparison: applying the trace-free factor
only to generic Frobenius-derived spatial partitions strictly improves all
seven cubic controls. Mars 1/8 s endpoint velocity falls from
1.4619986809939294e-6 to 1.2803291799227853e-6 m/s; reference-only
velocity is 1.2098251561204536e-6 m/s, so both still exceed 1e-6 m/s.
Position passes at 3.212860892438589e-5 m. All six shorter controls pass;
Mars 1/16 s velocity is 3.125623325187028e-7 m/s. These remain conditional
upper bounds, not measured integration errors. C20, native arithmetic,
rotation, full-force state sensitivities and all prior certificates remain intact.

Retained analytic prerequisite: the symmetric trace-free Hessian
lemma ||J||2 <= sqrt(2/3)*||J||F has an exact directional sum-of-squares
proof. Twenty-eight independent matrix/rounding-bound/rejection controls
pass, including rotated known spectra, monopole/polar-C20 attainment and
counterexamples when either premise is absent. Ideal exterior harmonic
potentials have symmetric Hessians with zero Laplacian; native arithmetic,
other forces and arbitrary operator-only bounds are not covered. The isolated
lemma alone did not change native bounds; the separately qualified composition
above now applies it only to eligible partitions.

Retained degree diagnosis: exact degree enclosures and an explicit
nonnegative arithmetic slack reconstruct the unchanged Mars 1/8 s remainder.
Degrees 2..10 contribute about 22.27%, 11..30 52.82%, 31..60 22.24%,
and 61..120 2.66%. The largest single degree is 2 (excluding C20), only
4.41%, followed by 3, 14, 15 and 25. The remainder is distributed across
many degrees; a one- or two-degree remedy is not the indicated priority.
The velocity-equivalent arithmetic slack is 2.3088194487634463e-22 m/s;
it is retained, not rounded away. These are shares of a conservative bound,
not physical uncertainty or permission to truncate the field.

Retained spatial diagnosis: the composed C20/remainder choice
wins for both bodies at all seven native endpoint controls. At Mars 1/8 s,
C20 contributes 2.0161635635530162e-7 m/s and the independently enclosed
remainder 9.900060826637374e-7 m/s. Their exact sum reconstructs the
existing spatial allowance. Even removing the C20 allowance entirely from
this fixed certificate would leave about 1.26038e-6 m/s, above the 1e-6 m/s
gate; this hypothetical screen is not permission to drop a force or allowance.
The next improvement must address the remainder or another sufficient
combination of bounds. No totals or historical gates changed.

Retained diagnosis: exact additive attribution reproduces the
unchanged C20-composed bounds at all seven native controls. At Mars 1/8 s,
the spatial nonmonopole allowance contributes 1.1916224390190391e-6 m/s
(about 81.5% of the total bound), already above the 1e-6 m/s gate by itself.
Mars rotation contributes 1.7974500058952665e-7 m/s and the unchanged
native/reference residual 7.05040238023318e-8 m/s. Improving only other
nonnegative channels cannot make this fixed certificate pass. This is a
diagnosis of conservative allowances, not measured errors or uncertainty.

Retained trajectory-envelope evidence: composing the sharp C20
spatial bound with a separately enclosed remainder further reduces all
seven cubic-reference bounds. Mars 1/8 s endpoint velocity improves from
1.6096184185581396e-6 to 1.4619986809939294e-6 m/s but still exceeds
1e-6 m/s; the reference-only bound is 1.3914946571915977e-6 m/s.
Position passes at 3.213617848696668e-5 m. All six shorter controls pass;
Mars 1/16 s velocity is 3.5638249872724224e-7 m/s. These are conditional
upper bounds, not measured errors. No native dynamics or tolerances changed.

Retained rotation-composition evidence: composing zonal pole-only
and nonzonal full-rotation allowances improves the cubic reference bounds
without changing the model or tolerances. Mars 1/8 s still does not resolve
the velocity gate: 1.6096184185581396e-6 m/s versus 1e-6 m/s, including
a reference-only contribution of 1.5391143947558078e-6 m/s. Position
passes at 3.2142329309394564e-5 m. All six shorter controls still pass;
Mars 1/16 s now has a velocity bound of 3.930278975682486e-7 m/s.
These remain conditional diagnostic bounds, not measured integration errors.

Retained baseline trajectory-envelope evidence: a partial-jerk cubic
reference encloses all modeled forces and passes the unchanged 0.001 m /
1e-6 m/s endpoint gates in six conditional native controls: four at
1/64 s and nominal Mars fixtures at 1/32 s and 1/16 s. The new 1/16 s
control uses a separately recomputed 2000 m / 0.25 m/s domain; its
position/velocity upper bounds are 3.6709789185994044e-5 m and
4.110326697955418e-7 m/s. The original 1000 m / 0.1 m/s domain remains
unclosed at that duration. Domain radii are not endpoint error tolerances.
At Mars 1/32 s, the partial-cubic velocity bound remains
1.0267213213083907e-7 m/s. The old quadratic velocity upper bound of
1.978951932550837e-6 m/s remains a regression control, not a measurement
of the native integrator's true error. The Moon 1/32 s position domain
still cannot be closed; no native arc is run there. These are diagnostic
fixtures, not a qualified mission or native internal-stage safety certificate.

A seventh control at Mars 1/8 s closes its separately recomputed
4000 m / 0.5 m/s domain but does not resolve the velocity gate:
1.6822435338333072e-6 m/s versus 1e-6 m/s. Its reference-only bound is
already 1.6117395100309755e-6 m/s, so reducing only the nonnegative
endpoint residual cannot make this fixed certificate pass. Position
passes with 3.2145355355878815e-5 m. Retain this counterexample; it does
not show actual integrator error, physical infeasibility or a general
upper limit on usable coast duration.

The cubic coefficient uses initial jerk intervals for all eight monopoles,
derived from qualified ideal SPK position polynomials. Moon/Mars higher
harmonics, orientation changes, SRP and relativity remain explicitly bounded;
this is not a full-force jerk measurement. Exact point-mass curvature controls
and the existing full-force transport lemma supply the reference enclosure.
No force, arithmetic allowance, or historical quadratic control was removed.
Twenty-four exact analytic controls now verify that ideal zonal force
terms of degree 0..8 cancel prime-meridian spin, even with a tilted pole.
Independent monopole/C20 gradients and negative controls retain tesseral
spin dependence and zonal pole-motion dependence. They support the ideal
rotation partition, not a qualification of rounded PCK arithmetic.
Separate ideal pole-only PCK rate upper bounds now retain RA+DEC without
PM: 7.911311791211134e-9 rad/s for Moon and 9.239844018154159e-13 rad/s
for Mars over the candidate interval. Fifteen exact spherical-derivative
controls and the reused 26 native pole readbacks per inventory pass;
corrupted derivative input is rejected. Native sampling is not a uniform
arithmetic proof. The full-rate diagnostics remain unchanged.
The coefficient partition now reconstructs the pinned Moon 200 / Mars 120
fields exactly, with no source mutation or dropped degree-one terms.
Sixteen new synthetic/rejection controls cover disjointness, independence,
full model sizes and invalid input. Both real inventories agree on the
nonzero zonal/nonzonal counts. Twenty new composition controls qualify the
rotation-bound sum against exact mixed-quadrupole and pure-zonal controls.
Fifty new analytic controls qualify the sharp isolated-C20 spatial
operator bound 12*sqrt(5)*|C20|*GM*R^2/d^5 (s^-2), including exact
angular matrix identities, polar attainment, scaling and invalid inputs.
Forty-six additional mixed-field/rejection controls verify independent polar
Hessians and the C20/remainder composition. Native application changes only
the reference spatial-variation bound; full-force state sensitivities,
rotation allowances, arithmetic bounds and historical controls remain intact.
The initial-velocity frontier uses the existing affine error envelope at
fixed position radius, inclusive accuracy and strict domain closure.
Its exact boundary and strictly enclosing rounded brackets are checked
against the original inequalities and all existing family classifications.
An empty interval is never clipped into a safe zero. The interval is
conditional, not a mission allocation or an estimate of physical uncertainty.
At p=0.0001 m, the Mars 1/8 s frontier is strictly bracketed by
4.797617489195039e-8 and 4.7976174891950404e-8 m/s, with the exact
endpoint included. All seven boundary checks and all 21 prior family
classifications pass unchanged.

Analytic two-segment controls now carry both error radii and rebase D+J*t
at the boundary. Resetting either accumulated error or the force clock is
explicitly shown to underbound exact endpoints. Nine nonlinear controls
close both domains; three original longer controls remain unresolved despite
their exact paths staying inside. All four handoff gates are checked below,
at and above the boundary, retaining strict closure and inclusive accuracy.

Reference re-centring now verifies y-n=(y-q)+(q-n) separately for 3D
position and velocity, with exact squared Euclidean checks. Opposed bridges
attain the triangle bound; omitting them underbounds the result. An error
already relative to the handed-off native endpoint includes that bridge,
so adding it again is conservative but unnecessarily consumes accuracy margin.

Adjacent 1/64 s prerequisites now use the nominal short native endpoints
with their incoming error radii unchanged and the existing cumulative
1/32 s force/source bounds. Both source/PCK/epoch/frame and initial-ball
checks pass. Moon position reach 1291.1784323779905 m exceeds the original
1000 m domain; velocity reach 0.04596892340455283 m/s stays below 0.1 m/s.
Mars reaches 953.9021517983934 m / 0.09908321511137594 m/s, so both
strict closure gates pass. No new native arc was run. These are conditional
domain prerequisites, not adjacent-arc accuracy or collision classifications.

The shifted Mars reference now has a qualified conditional defect
D2=1.7425477995296341e-6 m/s^2, J2=0.00010574685550976585 m/s^3,
with time/state shifts and every old allowance retained. Exact cubic
translation and both reference/chord domain checks pass. Its reference-only
position/velocity bounds are 4.089633601148173e-5 m and
5.5459546090295223e-8 m/s. The adjacent native residual is added below.

One nominal adjacent Mars 1/64 s native coast now passes exact handoff,
time and saved-mass checks. Its residual adds 3.594394195990218e-5 m and
3.267852978397076e-9 m/s, yielding two-segment endpoint bounds
7.684027797138391e-5 m / 5.87273990686923e-8 m/s; both gates pass.
The counted warm native call takes about 0.00946 s, excluding preparation.

The tighter adjacent control from the same nominal handoff also passes:
6.69214346377787e-5 m / 5.872512533193787e-8 m/s. Observed nominal/
tighter differences are bounded by 1.0789593218788875e-5 m and
8.147468573574279e-12 m/s, consistent with both certificates. This is
neither a tighter rerun of the first arc nor an independent error proof.

Doubled continuation assessment (2026-09-13): the 1/32 s continuation
from the nominal two-segment endpoint closes in the existing cumulative
1/16 s Mars domain (2000 m / 0.25 m/s). Ideal-path reaches are bounded by
1907.8073796223553 m and 0.19830989705603871 m/s. Both references and
their convex chords close; transported reference-only error bounds are
7.684434624561636e-5 m and 2.1915314005860373e-7 m/s, within unchanged
gates. Both incoming radii are preserved; no native call was added.

Nominal doubled continuation (2026-09-13): one counted 1/32 s native coast
from the saved nominal two-segment endpoint completes with exact time/state
handoff and constant saved mass. Conditional three-segment endpoint bounds
are 0.00010529778787867129 m and 2.3227467748483292e-7 m/s, both within
unchanged gates. Native-to-reference residuals are included exactly once.
The warm call takes 0.009299166966229677 s; its control takes
0.022462582914158702 s excluding the shared qualification preparation.

Tighter doubled continuation (2026-09-13): the same nominal two-segment
handoff gives conditional endpoint bounds 9.296577205470382e-5 m and
2.322751322321838e-7 m/s, both within unchanged gates. Observed Euclidean
nominal/tighter differences are bounded by 3.168725533644896e-5 m and
2.2282620193436745e-11 m/s, consistent with both certificates. This is
neither a tighter rerun of preceding arcs nor an independent error proof.

Longer continuation assessment (2026-09-13): the 1/16 s continuation from
the nominal three-segment endpoint closes in the existing cumulative 1/8 s
Mars domain (4000 m / 0.5 m/s). Ideal-path reaches are bounded by
3815.627094157525 m and 0.3971959264759999 m/s. Both references/chords
close; reference-only error bounds are 0.00010533061154685136 m and
8.906014137108062e-7 m/s. Both gates pass, with limited remaining velocity
margin; no new native call was added and both incoming radii were retained.

Nominal longer continuation (2026-09-13): one counted 1/16 s native coast
completes from the nominal three-segment endpoint with exact state/time
handoff and constant saved mass. Conditional four-segment endpoint bounds
are 0.00014951220569742958 m and 9.436498377495054e-7 m/s, within unchanged
gates but with limited velocity margin. Native-to-reference residuals are
added once. Warm native/control times are 0.009076250018551946 s and
0.024772708071395755 s, excluding shared qualification preparation.

Next bounded work within 3.9 is one counted tighter 1/16 s continuation
from the same nominal three-segment endpoint, retaining incoming radii,
reference, domain and forces. WHEN it completes, THEN verify exact native
state/time/mass, its own residual and endpoint gates, and exact squared
Euclidean differences against combined nominal/tighter certificates. Reuse
the existing loop/comparison; do not call agreement an independent proof
or a tighter rerun of preceding arcs. Retain all twelve earlier controls,
explicitly count the added call and timing, preserve portable zero, unchanged
production caps and the shared 300-second budget. Keep Moon unresolved;
do not claim mission or native-stage qualification.
Keep all previous certificates. Preserve all
coefficients and arithmetic allowances. Do not add unqualified native controls or attempt mission composition
yet. WHEN a proposed
derivative/remainder bound is tested, THEN it must enclose an independent
analytic oracle with explicit SI units and tolerances before any native
application. Native application additionally requires its own closed domain,
source/rotation coverage, arithmetic allowances and runtime accounting.
Do not substitute endpoint agreement or sampled differences for that proof.

The latest completed code check has 2402 passing tests; both inventories
pass. Historical 1/8 s velocity gates remain unresolved; only the new
degree-map certificate resolves them for the exact initial-state fixture.
The native inventory runs twelve spacecraft arcs, the portable inventory
zero; each performs 40 affine source readbacks. These are diagnostic counts, not mission-cost
estimates. Production limits and the shared 300-second deadline are unchanged.
Task 3.9, the remaining finite-burn safety prerequisites and targeting remain
open; detailed evidence is in the active change's design and tasks.

Latest mass-label diagnosis (2026-09-10): comparing the same native states
using Tudat's high-resolution elapsed time makes all 72 isolated controls
meet the unchanged mass tolerance. Native-time and float-key histories have
identical state values: the prior violations arise from associating states
with rounded absolute-time labels in these fixtures. Preserve those
counterexamples; explicit timing-error handling at data boundaries and
uniform interval mass safety remain unqualified. Production is unchanged.

Mass-safety counterexample (2026-09-10): translating isolated engine
controls from TDB 0 to the candidate start epoch causes 18 of 36 controls to
exceed the unchanged intermediate mass tolerance, including six tighter
integrator controls. Final-state checks still pass. The worst sampled error
is 1.3204770034323948e-8 kg versus a 1e-8 kg gate in these fixtures. The
counterexample is retained in tests; it is not a qualified mission result.
Native timing/integration error requires investigation before interval mass
safety or targeting; no tolerance or production setting has been changed.

Position-envelope evidence (2026-09-10): direct-SPICE qualification now inventories
550 records across all 11 required source links. Exact polynomial rate/jump
controls, native selected-record readbacks and conditional index-roundoff
margins retain the source-boundary counterexamples. Static inspection pins
the type-2/type-3 reader arithmetic, with endpoint checks for the last-record
clamp. Conditional uniform supplied-record position-error bounds are below
0.001 m; sampled center-chain addition and SI conversion now match direct
SPICE bit-for-bit. Conditional interval-wide position-chain composition,
including SI conversion, is now below 0.001 m for all eight bodies.
Conditional source-join composition now covers 539 body/event pairs across
all eight chains, with 1,078 direct-SPICE side controls. These envelopes include
source-representation jumps and are distinct from the arithmetic-only bound.
Native execution premises still require qualification before full-force
safety and runtime checks; targeting remains gated.
See the active change's design and tasks for numerical scope and evidence.

Historical table counterexample (before the approved direct-SPICE switch): probes at all 73 mapped Saturn record boundaries
fail the position allocation; 71 also fail the velocity allocation. Maximum
errors are `0.182333 m` and `2.138636e-5 m/s` near `997133760 TDB seconds since
J2000`, versus unchanged `0.025 m` and `2.5e-6 m/s` limits. The earlier single
segment-junction counterexample is therefore not the only affected boundary.
The counterexample is retained; task 2.7's original samples are not a uniform
certificate. The approved switch above supersedes the proposed table remedy,
not the counterexample or the unchanged scientific tolerances.

### Historical prototype priority (superseded by resumption above)

The user temporarily paused M3 to deliver the [visible prototype](PROTOTYPE.md).
The prototype reused the change ID for continuity. Original M3 documents and
task states remain in `openspec/deferred/refine-physical-trajectory` as a snapshot;
they were never archived as completed engineering work.

## Engineering roadmap

This roadmap delivers the first Moon-to-Mars reference use case for the
[Ariadna product vision](VISION.md). The broader goal is an open specification,
reference implementation, and interoperability tests, not a new universal or
flight-qualified standard. Existing milestone gates remain unchanged.

The first proposed interoperability slice is a declared trajectory contract,
TudatPy calculation, CCSDS OEM export, and independent-reader verification.
It is not yet scheduled or implemented. Before implementation, assign it to an
accepted change with a pinned standard edition, supported profile, numerical
tolerances, and measurable acceptance scenarios. Do not insert a second active
change or silently extend M3. Reassess placement when reviewing the next change.

The engineering sequence is `M1 -> M2 -> M3 -> M4 -> M5 -> M6`. M1 and M2 are archived; M3 is resumed as `refine-physical-trajectory`. Do not archive incomplete engineering work as completed.

| Milestone / change | Status | Depends on | Verifiable result |
|---|---|---|---|
| **M1 — `establish-navigation-foundation`** | Archived 2026-09-04 | None | Reproducible Python environment, strict TOML scenario, canonical units/time/frame contract, real SPICE ephemerides, and diagnostic CLI. |
| **M2 — `plan-impulsive-transfer`** | Archived 2026-09-04 | M1 archived | Three-dimensional impulsive Moon-to-Mars search evaluates at most 2,000 candidates and returns a flight-time/fuel Pareto front. |
| **M3 — `refine-physical-trajectory`** | Resumed 2026-09-07 | M2 archived | One selected Pareto candidate is refined from the configured lunar orbit to the configured Martian orbit with declared gravity harmonics, radiation pressure and shadows, Sun Schwarzschild relativity, variable mass, finite burns, and honest physical status. |
| **M4 — `estimate-navigation-state`** | Planned | M3 archived | Synthetic observations from three ground stations feed batch least squares and produce an estimated state and covariance. |
| **M5 — `schedule-course-corrections`** | Planned | M4 archived | The planner selects zero to three TCMs using only measurements available before each maneuver. |
| **M6 — `verify-and-report-mission`** | Planned | M5 archived | Twenty Monte Carlo cases produce standalone HTML, CSV, and JSON reports and an independent GMAT comparison. |

## M1 completion gate (historical, at M1 archival)

- `openspec validate establish-navigation-foundation --strict` succeeds.
- A clean environment resolves and installs every pinned dependency and the local package.
- A complete TOML scenario loads to immutable normalized values without hidden launch dates or spacecraft parameters.
- Missing fields, malformed TOML/encoding, unknown keys, nonnumeric values, invalid date order, nonpositive dimensions, invalid mass order, and invalid orbit bounds fail with field-specific diagnostics.
- UTC to TDB to UTC round-trip error is no greater than 1 millisecond.
- The state adapter agrees with a direct TudatPy/SPICE query within 1 millimeter and 1 micrometer per second.
- Public states label SI units, TDB seconds from J2000, SSB origin, and J2000 orientation.
- Successful CLI calls exit `0`; user-input failures exit `2` without a traceback.
- Repeated diagnostics with the same scenario, dependency versions, and seed produce identical scientific values.
- The diagnostic manifest identifies the scenario, software, conventions, seed, and every loaded standard kernel available from TudatPy, including file hashes.
- `moon_to_mars.py` remains byte-for-byte unchanged and is not imported by `space_nav`; no M2–M6 behavior is present.

## M3 completion gate

- `openspec validate refine-physical-trajectory --strict` succeeds before implementation completion and immediately before archival.
- The supplied candidate is reproduced from the same normalized scenario and deterministic M2 Pareto front before any physical propagation.
- Production propagation uses Moon `gggrx1200` degree/order 200, Mars `jgmro120d` degree/order 120, declared point-mass perturbations, current-mass cannonball radiation pressure with Moon/Earth/Mars shadows, and Sun Schwarzschild relativity without gravity double counting.
- Departure ignition and arrival cutoff are the configured physical lunar and Martian orbit states rather than M2 body-centre endpoints.
- Separate departure-burn, coast, and arrival-burn arcs preserve state/mass continuity, follow the declared TNW guidance, obey the thrust mass-flow law, detect impacts, and never cross dry mass.
- `examples/reference_mission.toml` remains unchanged and candidate `d0001-t0035` returns `mass-infeasible` without finite-burn targeting because its ideal M2 final mass is below dry mass.
- The provisional M3 fixture changes only dry mass; candidate geometry and ideal masses remain unchanged but the M2 feasibility flag changes. Physical convergence must be demonstrated for `d0001-t0035` within `1000 m`, `0.01 m/s`, eight iterations, and the shared 300-second cooperative deadline before the fixture is called feasible.
- The exact TNW corrector demonstrates that feasible-fixture gate in a prerequisite spike before production correction proceeds; until then, the iteration/runtime limit is an acceptance hypothesis rather than measured performance and is not weakened silently.
- Frozen-command nominal/tighter propagation agrees within `10 m`, `0.0001 m/s`, and `0.000001 kg`; the isolated ten-orbit fixture keeps relative energy and angular-momentum drift within `1e-11`.
- Moon degree-400 sensitivity stays within `500 m` and `0.0001 m/s`; the finite Mars degree-60-to-120 tail is reported without claiming knowledge beyond the degree-120 model ceiling.
- Repeated canonical JSON results are byte-identical for the same scenario and resources, and the manifest records complete resource, force, numerical, targeting, and deferred-input provenance.
- Qualify ephemeris interpolation against direct SPICE and a denser table before the targeting spike; identical integrator results on the same interpolation table do not qualify ephemeris accuracy. Verify the combined forces and per-arc PPN reset independently.
- Check in the prerequisite spike and its scientific/timing evidence. A failed safe-seed or closure gate requires revising the active change before production correction proceeds. Preserve all existing closure and sensitivity tolerances until evidence supports an explicitly reviewed change.
- The complete pinned Python 3.12 test suite passes, existing M1/M2 behavior remains compatible apart from the planned `0.3.0` version, and `moon_to_mars.py` remains byte-for-byte unchanged and unimported.

## Future milestone completion gates

- **M4:** synthetic observation generation, batch estimation, and covariance output pass reproducible truth-recovery checks defined by its future change.
- **M5:** maneuver count and measurement-causality rules pass tests that prevent use of future observations.
- **M6:** all 20 seeded Monte Carlo cases complete, all three report formats agree, and the GMAT comparison satisfies the future change's documented tolerance.

Completion criteria for M4-M6 remain intentionally high-level until the preceding milestone is archived. Each future change must replace its high-level gate with measurable WHEN/THEN scenarios before implementation.

Twenty M6 cases are a reproducible regression ensemble, not evidence of a rare-event failure probability. Define uncertainty assumptions and the statistical scope in M6 before interpreting success rates.
