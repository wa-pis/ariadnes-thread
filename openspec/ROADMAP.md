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

Latest trajectory-envelope evidence (2026-09-13): composing the sharp C20
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
Next bounded work within 3.9 is to identify the dominant remaining
reference-defect contribution at Mars 1/8 s before choosing another analytic
bound; do not add longer controls or attempt mission composition yet. WHEN a proposed
derivative/remainder bound is tested, THEN it must enclose an independent
analytic oracle with explicit SI units and tolerances before any native
application. Native application additionally requires its own closed domain,
source/rotation coverage, arithmetic allowances and runtime accounting.
Do not substitute endpoint agreement or sampled differences for that proof.

The latest completed code check has 2025 passing tests; both focused
1/8 s limit-probe inventories pass, retaining the unresolved velocity gate.
The native inventory runs seven spacecraft arcs, the portable inventory
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
