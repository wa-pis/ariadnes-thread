## Context

### Approved safety-limit investigation (2026-09-08)

The user authorized revisiting native-call limits for adaptive safety subdivision,
without relaxing numerical tolerances or the shared 300-second deadline. First
qualify an isolated interval-screening experiment, capped at 32 native subsegments
per evaluation and counting discarded parents. Existing production defaults stay
three arcs per evaluation and 228 native calls until full-force measurements
justify a replacement; the targeting spike remains gated on continuous safety.

For analytic controls only, use a known bound A on relative acceleration. The
distance between the trajectory and its endpoint chord is at most A*dt^2/8:
the linear-interpolation error has a Green-kernel integral with this norm bound.
Subtract that deviation and a verified 0.001 m endpoint error allowance from
the chord's minimum distance before certifying clearance. Ambiguous intervals
are bisected; an interior sample inside the sphere rejects the control, while
depth/call/time exhaustion remains unresolved or an error, never safe. This is
not a mission certificate: native full-force relative-acceleration bounds,
ephemeris uncertainty, and endpoint error budgets must be justified separately.

Body motion must not be confused with interpolation error. For a body's
ephemeris b(t), its endpoint chord L_b(t), spacecraft trajectory x(t), and
spacecraft chord L_x(t), the relative chord defect obeys
`||(x-b)-(L_x-L_b)|| <= ||x-L_x|| + ||b-L_b||`. A uniform body-motion enclosure
and the spacecraft enclosure are therefore separate inputs to this approach;
the sampled `0.025 m` table/SPICE comparison cannot replace either enclosure.
Any table-to-SPICE uncertainty must also be handled explicitly if the safety
claim refers to SPICE rather than only the interpolated model. Shared orbital
curvature can cancel in relative motion, so separate bounds may be conservative.
The moving-body qualification uses actual Tudat/SPICE states at departure,
cruise, and arrival over 30 s, 300 s, and 86400 s. Sampled chord deviations are
lower bounds on the allowance needed to enclose body motion, not uniform upper
bounds, and do not establish spacecraft safety. No new native-call limit follows
from this measurement. See task 3.9 evidence for reproduction and numerical scope.

For the finite, geodesy-4pi-normalized gravity expansion, let
`q_n = sum_m(C_nm^2 + S_nm^2)` (with `S_n0=0`). The addition theorem gives
`sum_k Y_nk^2 = 2n+1` for this real basis. Applying the spherical Laplacian and
`Delta_S Y_nk = -n(n+1)Y_nk` gives
`sum_k ||grad_S Y_nk||^2 = n(n+1)(2n+1)`. The radial and tangential gradients are
orthogonal. The Frobenius norm of their coefficient-to-acceleration map is
`(2n+1)*sqrt(n+1)`; multiplying by the coefficient norm `sqrt(q_n)` and
summing degree contributions yields
`B = GM/r_min^2 * sum_n (R/r_min)^n * (2n+1)*sqrt((n+1)*q_n)`.
This derivation uses the [spherical-harmonic addition theorem](https://dlmf.nist.gov/14.30#E9)
with the [real 4pi normalization](https://shtools.github.io/SHTOOLS/real-spherical-harmonics.html).
For every `r >= r_min > 0`, B bounds the norm of the declared finite gravity
field in any orientation; degree zero is included exactly once. It neither
bounds omitted degrees nor proves the trajectory stays outside r_min.

Compute this private component bound from validated coefficients using a fresh
50-digit Decimal context with upward rounding of nonnegative operations.
Round square roots upward explicitly (Decimal square root uses half-even),
then round the final binary float outward. Reject invalid dimensions, non-finite
or boolean inputs, nonzero unused coefficients and overflow. The caller must
establish the distance lower bound and account separately for native force
evaluation error, all other forces, ephemeris motion and numerical trajectory
error before constructing a full safety enclosure. This helper alone does not
authorize a safe result or a larger propagation limit.

For unit-direction maximum-thrust burns and proven `mass >= dry_mass`, the
thrust norm is at most `T_max/dry_mass`; the coast contribution is exactly zero.
For the declared isotropic Sun and cannonball target, shadow fraction in [0,1]
implies `a_srp <= L*A*Cr/(4*pi*c*dry_mass*d_sun_min^2)`. See the native
[thrust definition](https://py.api.tudat.space/en/latest/dynamics/propagation_setup/thrust.html)
and [radiation model](https://docs.tudat.space/en/latest/user-guide/state-propagation/propagation-setup/translational/radiation-pressure-acceleration.html).
Use the simpler rational enclosure `L*A*Cr/(12*c*dry_mass*d_sun_min^2)` because
`pi > 3`. This is about 4.72% more conservative than the fully lit SRP expression,
not a change to the simulated force or a relaxed scientific tolerance. Use
the existing explicit luminosity and SI `c=299792458 m/s`, checked against
pinned Tudat. Evaluate positive products and reciprocal factors with the same
isolated 50-digit upward-rounded Decimal arithmetic as the harmonic bound.
Return separately labeled-by-contract thrust/SRP bounds in m/s^2, reject
invalid contributing inputs and non-finite outputs, and require an explicit
burn/coast flag. No current shadow sample may reduce the interval SRP bound.
The caller must prove the mass/distance floors; this does not include native
evaluation error, relativity, gravity, body motion or trajectory error.

For the declared Sun-only Schwarzschild correction with PPN beta=gamma=1,
write its [native-model expression](https://py.api.tudat.space/en/latest/dynamics/propagation_setup/acceleration.html#tudatpy.dynamics.propagation_setup.acceleration.relativistic_correction)
as `GM/(c^2*r^2) * [(A-s)*e_r + 4*v_r*v]`, where `A=4*GM/r`, `s=||v||^2`,
and `v_r=e_r dot v`; v is spacecraft velocity relative to the Sun, not its
absolute SSB velocity. The squared bracket norm is
`(A-s)^2 + 8*(A+s)*v_r^2 <= (A+3*s)^2`. Thus the orientation-independent bound
is `GM/(c^2*r_min^2) * (4*GM/r_min + 3*V_max^2)` for proven
`r >= r_min > 0` and `||v|| <= V_max`. Radial motion attains the orientation
maximum, and zero relative speed is valid. Use the existing exact SI light
speed and isolated upward-rounded Decimal operations, with outward final float
conversion. Reject invalid inputs and overflow. The caller must prove both
interval bounds and enforce PPN beta=gamma=1 in the force factory; this helper
does not load SPICE, change PPN globals, validate an interval, cover omitted
relativistic effects, or claim physical validity outside the model's weak-field,
slow-motion regime. Native evaluation and trajectory errors remain separate.

Combine component bounds by the triangle inequality in the exact existing body
order: eight gravity norms (Moon/Mars already include degree zero), followed
by thrust, fully lit SRP and Sun Schwarzschild. Require every named gravity
entry exactly once, positive finite gravity/SRP/Schwarzschild values and an
explicit phase flag; coast thrust must be exactly zero and burn thrust positive.
Reject omitted/extra sources rather than treating them as zero. Convert the supplied
binary bounds exactly to Decimal, sum in the isolated upward-rounded context and
round the resulting float outward. Check the caller's shared budget during collection
and after summation; this pure calculation starts no propagation or new deadline.
The result bounds the declared spacecraft acceleration only conditional on all
component enclosures being valid. It does not audit mutable native engine state,
prove the input distance/mass/speed bounds, include body motion or numerical
errors, or certify a safe trajectory. Qualify the composition against the
existing native complete-force fixed-state controls before any interval driver.

Qualify the local ephemeris representation before deriving polynomial interval
bounds: reconstruct the six-point, degree-five interior Lagrange polynomial from
direct SPICE states on the existing 300-second grid. Use exact rational node
weights and state sums as a test oracle, with only final float conversion.
Compare all six components with the existing native table at the 38 qualification
epochs using the unchanged sampled input-state allocation. Check the oracle
against analytic polynomials through degree five. Do not replace the native
ephemeris, infer unsampled SPICE error from these comparisons, or treat the
separately interpolated velocity components as derivatives of the position
polynomial. Boundary splines and all-interval roundoff remain separate obligations.

Do not assume a bounded classical second derivative across an interior grid
switch. Qualify native six-point tabulation on analytic degree-five and
degree-six motion with consistent sampled velocity, using explicit one-second
and 300-second grids. Compare both sides with the closed polynomial remainder
and distinguish the position derivative from the returned velocity channel.
Any future chord enclosure spanning knots must split its mathematical analysis
by interpolation cell or explicitly bound derivative jumps; this does not by
itself require an additional native spacecraft propagation per ephemeris cell.

For one six-node position polynomial, bound its deviation from its own endpoint
chord on a positive-duration subinterval contained in the middle node pair.
Normalize this interval to `u in [0,1]`. Construct the degree-five power
coefficients of its Lagrange basis using exact Fraction arithmetic on supplied
binary epochs and SI/SSB/J2000 positions. Subtract the endpoint chord exactly,
then convert power coefficients `a_j` to degree-five Bernstein coefficients
`b_k=sum(j<=k, a_j*choose(k,j)/choose(5,j))` componentwise. Nonnegative Bernstein
weights sum to one, so `max_k sum_axis(abs(b_k))` bounds the Euclidean chord
deviation in metres. This conservative L1 enclosure avoids square-root rounding;
convert its exact rational value outward to float (return exact zero for a line).
Reject malformed/nonfinite nodes, nonincreasing epochs, intervals crossing a
cell boundary and overflow. Reuse the shared budget without native propagation.
Verify exact monomial coefficient bounds, affine controls, subinterval scaling,
translation invariance, independent sampled Lagrange controls and deadline errors.
This only encloses the exact polynomial of supplied nodes: node provenance,
native floating evaluation, uniform SPICE approximation, cross-cell composition
and spacecraft integration error remain outside this helper. Bernstein basis
properties: https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node9.html

Qualify this cell enclosure on the reconstructed SPICE nodes already used by
the 38-epoch, eight-body fixture. For each request, bound its full 300-second
cell and compare native midpoint and knot states with the exact local polynomial
using the unchanged sampled allocation. Check native midpoint chord deviation
against the exact-polynomial bound plus twice that position allocation (one
midpoint and one convex endpoint-chord error). This is sampled native-error
qualification, not a uniform error certificate. Record bound maxima and
helper-only wall time separately; do not equate these helper calls with native
spacecraft runs or extrapolate them into a verified whole-mission runtime.

Compose adjacent cell enclosures using shared endpoint positions rather than
position derivatives. For global endpoint chord `L`, define each knot residual
`D_i=||p_i-L(t_i)||_1`. The difference between a local chord and `L` is affine,
so on cell `i` its norm is at most `max(D_i,D_(i+1))`. The total Euclidean
deviation is therefore bounded by `max_i(B_i+max(D_i,D_(i+1)))`, where `B_i`
is a supplied nonnegative Euclidean local-chord enclosure. Compute knot
residuals and composition exactly from binary inputs with Fraction arithmetic,
then convert outward; an exact zero stays zero. Require ordered finite times,
matching three-component SI/SSB/J2000 positions and exactly one finite
nonnegative bound per adjacent pair. Check the same budget throughout and do
not start/count native propagation. Verify corners, affine motion, unequal cell
durations, large translations, local curved-cell composition and invalid/expired
inputs. Callers must establish that cells share the supplied endpoints and that
their local bounds are valid; endpoint, native, SPICE and integration errors are
not silently included. This mathematical composition does not certify safety.

Qualify multi-cell composition on Moon/Mars motion at departure, cruise and
arrival using 1800-second and 86400-second local windows with six and 288
300-second cells respectively. Reuse each SPICE node across neighboring cells,
compose all cell bounds, and compare the native global-chord deviations at the
existing 35 off-grid/midpoint/endpoint samples against the bound plus the two
sampled position-error allocations. Independently reconstruct each sampled
local polynomial and retain the existing state tolerances. Record cell/helper
counts and helper-only timings separately from native spacecraft work. Do not
interpret this as full-force safety, uniform error or mission timing evidence.

Before deriving native evaluation roundoff, verify the pinned candidate grid's
binary64 arithmetic premises separately. Replay the source's repeated 300-second
time increments over the full padded interval against exact rational epochs.
Check all body settings share that grid, and that its positive endpoints differ
by at most a factor of two: Sterbenz's condition makes timestamp subtraction
exact for represented times within that range. At representative six-node
windows, compare every cached-denominator multiplication against exact integers
and `(-1)^(5-i)*i!*(5-i)!*300^5`; also check adjacent-representable interior query
times. This is an arithmetic-premise control, not a native rounding certificate.
Numerator products, division, state multiplication/summation, compiler/runtime
arithmetic and native node provenance still require separate error analysis.
Exact-subtraction reference: https://flocq.gitlabpages.inria.fr/theos.html

For the uniform six-node interior stencil `(-2,-1,0,1,2,3)` and `u in [0,1]`,
the Lagrange basis signs are `(+,-,+,+,-,+)` (allow zeros at endpoints).
Since `sum L_i=1`, its absolute-weight sum is `Lambda=1-2*(L_1+L_4)`.
Factoring gives `L_1+L_4=-w*(6+w)/8`, where `w=u*(1-u) in [0,1/4]`.
Thus `Lambda=1+w*(6+w)/4 <= 89/64`, with equality at `u=1/2`.
This proves that nodal vector errors each bounded by `epsilon` amplify to
at most `(89/64)*epsilon` under exact interpolation. Aligned error vectors
with the basis signs attain the bound, so replacing it by one is unsafe.
Verify the identity with rational basis evaluations and qualify the attaining
and constant-sign controls against native tabulation on one-second/300-second
grids. The factor does not bound native floating evaluation or SPICE polynomial
approximation, and applies only to this uniform middle-cell stencil, not
boundary splines or arbitrary grids. Keep it as a qualification result until
the complete rounding argument is established; add no unused runtime machinery.

Qualify the inspected arithmetic graph before attaching a roundoff bound to
native results. A test-only binary64 replay uses the source's cached-denominator
product order, repeated numerator and six ordered state multiply/add terms,
with an exact-knot shortcut. Do not use Python's compensated `sum` or implicitly
fuse multiply/add. Compare it with the existing native eight-body/38-epoch
fixture under unchanged state tolerances, and report exact state matches as
additional evidence. Analytic affine and cancellation controls independently
check the replay. Agreement at these inputs does not prove compiler flags,
runtime rounding, underflow/overflow behavior or a uniform native error bound.

Under the standard relative-roundoff model, exact time differences/denominators
leave at most 15 error factors per source term: six numerator multiplications,
one denominator multiplication (inverse factor), division, state multiplication
and at most six ordered additions. With `u=2^-53`, `gamma_n=n*u/(1-n*u)`, the
componentwise exact-polynomial error is bounded by `gamma_15*(89/64)*M_j`, where
`M_j=max_i(abs(state_ij))`. Comparison with a once-rounded rational oracle adds
at most `u*(89/64)*M_j`; `gamma_15+u <= gamma_16` therefore gives the test envelope
`gamma_16*(89/64)*M_j`. This is an absolute bound, including cancellation.
Check the replay's time/denominator exactness and each remaining operation's
relative model directly with Fraction arithmetic at the test inputs; reject
underflow/invalid examples rather than assuming the model universally. Compare
native and once-rounded rational states componentwise with the exact envelope
and report conservative position/velocity L1 summaries separately. These checks
do not establish the premises across unsampled epochs or compiled native paths,
and do not include SPICE approximation, boundary splines or integration error.
Reference for the product/inverse-factor lemma: Higham, Lemma 2.1,
https://nhigham.com/wp-content/uploads/2023/10/high99n.pdf .

For weight arithmetic only, exclude exceptional ranges over every represented
non-knot query in each uniform middle cell of the pinned positive epoch grid.
The minimum timestamp spacing is `delta=ulp(initial_time)` and each nonzero
exact time difference has magnitude in `[delta, 3h]`, `h=300 s`. Starting from
`[1,1]`, propagate numerator magnitude bounds through six products using exact
Fraction arithmetic and outward factors `1-u`, `1+u`. Cached denominator
magnitudes lie between `2!*3!*h^5` and `5!*h^5`; combine these with the time
difference range and one rounding factor, then bound the division similarly.
Check both each exact-operation range and its rounded enclosure strictly inside
the normal finite binary64 range. This inductive check justifies the relative
model's range premise for weights assuming correctly rounded binary64 operations;
it does not assume the relative model before excluding exceptional results.
Exact knots take the stored-state shortcut. Nearest representable interior queries
at the first, middle and last stencil have affine replay/oracle controls within
`1e-12` in each SI component. State multiplication, cancellation in accumulation,
oracle conversion for arbitrary data, compiled paths and SPICE approximation
remain separate obligations; this is not yet a uniform native state certificate.


See `proposal.md` for motivation and the three delta specs for normative behavior. M1 supplies strict immutable scenarios and one lazy SPICE/kernel boundary. M2 supplies deterministic center-to-center Lambert candidates, scalar patched-conic burns, and a Pareto front, but explicitly does not produce executable vector maneuvers.

Earlier exploratory runs reported an ideal M2 final mass of about `887.966464 kg` for candidate `d0001-t0035`, below the reference `1000 kg` dry mass. This fails the selected M2 seed budget; it is not a proof that every physical transfer is impossible. Earlier harmonic comparisons reported about `1,018,599 m` and `0.1453 m/s` between degree 20 and 200/120, and about `208 m` and `0.0000297 m/s` between Moon 200 and 400. Their reported single-propagation times were about `1.6 s` and `5.1 s`. Until a reproducible script, exact initial state, commands, resources, machine, and output are checked in, these are exploratory context, not acceptance evidence for the orbit-to-orbit finite-burn problem or its 300-second budget.

## Goals / Non-Goals

**Goals:**

- Turn one verified Pareto candidate into an actual lunar-orbit-to-Martian-orbit boundary-value problem.
- Make force, mass, targeting, convergence, and model-resolution limitations inspectable and reproducible.
- Return useful, typed physical non-successes without fabricating executable trajectories.
- Reuse existing dependencies and preserve M1/M2 behavior and lazy imports.

**Non-Goals:**

- Guarantee targeting convergence for every geometrically poor M2 seed.
- Optimize thrust level, steering history, launch epoch, or flight time.
- Treat numerical convergence as an operational uncertainty or flight-qualification statement.
- Consume tracking or maneuver-dispersion inputs before M4-M6.

## Decisions

### 1. Keep M3 additive and lazy

Add `trajectory.py`, immutable records in `models.py`, `TrajectoryRefinementError` in `errors.py`, package exports, and one `refine` branch in the existing CLI. `trajectory.py` imports TudatPy only inside physical calls. Scenario loading, package import, help, and invalid-input handling therefore remain kernel-lazy.

The public API is:

```python
refine_physical_trajectory(
    scenario: Scenario,
    candidate: ImpulsiveTransferCandidate,
) -> PhysicalTrajectoryResult

@dataclass(frozen=True, slots=True)
class TrajectoryBoundaryState:
    label: str
    epoch_utc: str
    epoch_tdb_s: float
    origin: Literal["SSB"]
    orientation: Literal["J2000"]
    position_m: tuple[float, float, float]
    velocity_m_s: tuple[float, float, float]

@dataclass(frozen=True, slots=True)
class FiniteBurnRecord:
    burn_id: Literal["departure", "arrival"]
    start_epoch_tdb_s: float
    end_epoch_tdb_s: float
    direction_frame: Literal["Moon-relative TNW", "Mars-relative TNW"]
    direction_tnw: tuple[float, float, float]
    thrust_n: float
    isp_s: float
    initial_mass_kg: float
    final_mass_kg: float
    propellant_mass_kg: float
    ideal_equivalent_delta_v_m_s: float

@dataclass(frozen=True, slots=True)
class TrajectoryBoundaryDifference:
    label: Literal[
        "departure-ignition",
        "departure-cutoff",
        "arrival-ignition",
        "arrival-cutoff",
    ]
    position_difference_m: float
    velocity_difference_m_s: float
    mass_difference_kg: float

@dataclass(frozen=True, slots=True)
class PhysicalTrajectoryResult:
    candidate_id: str
    status: Literal["converged", "mass-infeasible", "targeting-failed"]
    termination_reason: str
    origin: Literal["SSB"]
    orientation: Literal["J2000"]
    time_scale: Literal["TDB seconds since J2000"]
    force_model_id: str
    initial_state: TrajectoryBoundaryState
    target_final_state: TrajectoryBoundaryState
    terminal_state: TrajectoryBoundaryState | None
    burns: tuple[FiniteBurnRecord, ...]
    initial_mass_kg: float
    dry_mass_kg: float
    final_mass_kg: float | None
    propellant_mass_kg: float | None
    ideal_m2_final_mass_kg: float
    required_propellant_mass_kg: float
    available_propellant_mass_kg: float
    propellant_shortfall_kg: float
    terminal_position_error_m: float | None
    terminal_velocity_error_m_s: float | None
    integration_differences: tuple[TrajectoryBoundaryDifference, ...]
    lunar_harmonic_differences: tuple[TrajectoryBoundaryDifference, ...]
    martian_harmonic_differences: tuple[TrajectoryBoundaryDifference, ...]
    correction_iterations: int
    control_attempts: int
    propagation_evaluations: int
    native_arc_propagations: int
    rejection_counts: tuple[tuple[str, int], ...]

class TrajectoryRefinementError(Exception): ...
```

One status-bearing result avoids three nearly identical result hierarchies. Constructor rules make absent fields explicit: preflight infeasibility and status `targeting-failed` with reason `no-safe-complete-trial` have no terminal state, burns, or actual final/consumed mass; a complete safe nonconverged result and a converged result have a terminal state and two burns; only `converged` has reason `target-closure-and-validation-passed`, the three ordered four-boundary difference tuples, and permission to claim the closure and validation budgets. `ideal_m2_final_mass_kg` is always the verified M2 rocket-equation estimate and is never presented as propagated mass. Sorted immutable rejection counts preserve internal reasons such as `rejected-dry-mass`, `rejected-impact:Mars`, and `rejected-control-bounds` without misusing them as public status reasons.

### 2. Recompute and compare the M2 handoff

The API does not trust a manually constructed candidate. It runs the existing deterministic M2 search for the supplied scenario, locates the exact Pareto identifier, and compares every candidate value under the spec tolerances. The CLI accepts only `--candidate-id`, runs the search once, and passes the matching object into an internal already-verified path to avoid a second search.

An alternative candidate JSON input would require a versioned interchange schema and scenario binding. It adds no capability while the Pareto front is cheap and deterministic, so M3 does not add it.

### 3. Give orbit elements exact boundary semantics

At candidate departure TDB the departure elements are Moon-centred osculating elements on J2000 axes and define the state at burn ignition. At candidate arrival TDB the target elements are Mars-centred on J2000 axes and define the desired state at burn cutoff. Convert with TudatPy's element conversion and the harmonic field's own gravitational parameter, then add the central body's SSB/J2000 SPICE state.

Orbit altitude continues to use the M1 radii, Moon `1737400 m` and Mars `3389500 m`. These must not be confused with the harmonic normalization radii, Moon `1738000 m` and Mars `3396000 m`, or with Tudat's default Mars shape radius. For the circular lunar orbit, normalize through argument of latitude so redistributing angle between argument of periapsis and true anomaly cannot change the state.

### 4. Build one explicit Tudat environment

Use `get_default_body_settings_time_limited` with SSB/J2000 and the complete candidate interval. The literal production model identifier is `ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-cannonball-srp-schwarzschild-v1`. Override Moon gravity with pinned `gggrx1200` degree/order 200 in `IAU_Moon` and Mars gravity with pinned `jgmro120d` degree/order 120 in `IAU_Mars`, and require each gravity field's associated frame to equal its rotation target frame. The pinned baseline coefficient hashes are:

- Moon: `3f4652c01db58e14a4e4c67fe8225874d10120a29cbd7699f5068469ef65b21d`
- Mars: `d13b31d46862838abe62ebab3cef8209244588abe14e4e5e481c0fb64354e980`

Create direct point-mass settings for Sun, Mercury, Venus, Earth, Jupiter, and Saturn. Create only harmonic settings for Moon and Mars; degree zero is already included. Use and verify the field-provided GMs `4902800121846.8 m^3/s^2` and `42828375815756.1 m^3/s^2` to relative error `1e-15` rather than substituting the M2 SPICE GMs. Exact runtime values and hashes go into provenance.

The spacecraft receives a cannonball radiation target with scenario area and coefficient and `{"Sun": ["Moon", "Earth", "Mars"]}` occultation. Configure the Sun source explicitly at `3.828e26 W` rather than inheriting a mutable default. Add Sun Schwarzschild relativity only. No atmosphere, albedo, thermal radiation, Lense-Thirring, de Sitter, or EIH term is silently included.

Collision checks cover exactly Sun, Mercury, Venus, Earth, Moon, Mars, Jupiter, and Saturn. Require pinned `pck00010.tpc` hash `59468328349aa730d18bf1f8d7e86efe6e40b75dfb921908f99321b3a7a701d2`. Its SPICE radius vectors in meters are Sun `(696000000,696000000,696000000)`, Mercury `(2439700,2439700,2439700)`, Venus `(6051800,6051800,6051800)`, Earth `(6378136.6,6378136.6,6356751.9)`, Moon `(1737400,1737400,1737400)`, Mars `(3396190,3396190,3376200)`, Jupiter `(71492000,71492000,66854000)`, and Saturn `(60268000,60268000,54364000)`. Use each maximum component as a conservative spherical guard and define impact by `||r_spacecraft-r_body|| <= guard_radius`. A missing, non-finite, nonpositive, or more-than-`0.001 m` mismatched vector is a resource error. These collision surfaces are separate from the Moon/Mars mean shape radii used to interpret configured orbit altitude.

### 5. Parameterize credible minimal finite-burn guidance

Before segmented propagation, concatenate the existing force settings by source: Sun has point gravity, SRP, and Schwarzschild; Moon and Mars each retain exactly one harmonic term; other sources retain one point term. Verify the combined acceleration independently at near-Moon, cruise, and near-Mars states under the existing force tolerance. Reset and read back TudatPy 1.0's mutable global PPN gamma/beta as `(1, 1)` immediately before each arc's acceleration-model construction; concurrent simulations that mutate the shared SPICE/PPN state are unsupported. A resource record alone does not freeze the native globals.

The `300 s` time-limited ephemeris table is an approximation. Both integrators
using the same table do not test this source of error. Qualification evidence is
`tests/data/m3_ephemeris_qualification.json`, reproduced with
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py`.
It covers all eight bodies over the full provisional candidate interval at 38
deterministic epochs (32 off-grid interior points, endpoints and four near-edge
points), comparing the default six-point Lagrange tables at 300 s and 150 s
against direct SPICE with no aberration, SI/SSB/J2000 and TDB seconds from J2000.
The fixture constructs the same ephemeris settings as production and verifies
their safe runtime intervals; missing coverage is rejected before querying.

Measured maxima for 300 s versus direct SPICE were `0.0116642 m` and
`1.21554e-6 m/s`; 150 s versus direct gave `0.00540739 m` and `5.39573e-7 m/s`.
The table-to-table maxima were `0.0170707 m` and `1.75493e-6 m/s` (Saturn).
Adopt an input-state regression allocation of `0.025 m` and `2.5e-6 m/s` for
all three comparisons. These new measured bounds do not loosen the existing
`1000 m` / `0.01 m/s` closure gates. Sparse state samples neither prove a
uniform interpolation bound nor bound the downstream spacecraft error;
integration and model-sensitivity checks remain required. Do not claim denser
tables improve every component when floating-point rounding dominates.
Resource hashes, versions, exact epochs and per-body maxima are in the evidence.
See [Tudat's time-limited body documentation](https://docs.tudat.space/en/stable/user-guide/state-propagation/environment-setup/default-env-models/default-bodies-limited-time-range.html).

Each burn has two constant steering angles expressed in its instantaneous central-body-relative TNW frame plus a duration. For relative position `r` and velocity `v`, define `T = v / ||v||`, `W = (r × v) / ||r × v||`, and `N = W × T`. Reject a non-finite basis, zero velocity, or `||r × v|| <= 1e-12 ||r|| ||v||`. With azimuth `a` and elevation `e`, the ordered `(T, N, W)` command is `(cos(e) cos(a), cos(e) sin(a), sin(e))`. TNW is rebuilt from the propagated state, so the direction follows the orbital frame during burns lasting a significant fraction of a low lunar orbit. This is more credible than holding the M2 asymptote direction inertially for roughly 40 percent of the reference lunar period, while remaining the smallest guidance law with three controls per burn.

Both engines use scenario maximum thrust and Isp. Use the confirmed TudatPy 1.0 path: `rotation_model.custom_inertial_direction_based`, `thrust.custom_thrust_magnitude_fixed_isp`, `add_engine_model`, and `acceleration.thrust_from_engine`. Couple `mass_rate.from_thrust` through translation-plus-mass `multitype` propagation. Do not use the visible but disabled custom-thrust shortcuts that raise `no longer available` in TudatPy 1.0.0.

Run three exact arcs per evaluation: departure burn from the candidate departure epoch, coast, and arrival burn ending at the candidate arrival epoch. Rebuild the acceleration/propagator setup at each boundary so no adaptive integrator step crosses a thrust discontinuity. Carry the exact terminal state and mass into the next arc.

### 6. Use a bounded six-control differential corrector

Represent controls as `x = (a_d, e_d, tau_d, a_a, e_a, tau_a)`. Canonicalize each azimuth to `[-pi, pi)`, require each elevation in `[-pi/2, pi/2]`, require `tau_d > 0 s` and `tau_a > 0 s`, and require the strict positive-coast inequality `departure_epoch + tau_d < arrival_epoch - tau_a`; equality is invalid. The analytic two-burn terminal mass must also be at least dry mass. Any update outside this domain is rejected before propagation as `rejected-control-bounds` or `rejected-dry-mass`. For the departure direction, normalize `candidate.departure_v_infinity_m_s`, project it into the ignition Moon TNW basis, and set `a_d = atan2(p_N, p_T)` and `e_d = atan2(p_W, hypot(p_T, p_N))`. For arrival, apply the same formulas to the normalized negative `candidate.arrival_v_infinity_m_s` projected into the target-cutoff Mars TNW basis. A non-finite or at-most-`1e-12 m/s` excess-velocity norm is a candidate error. With `v_e = g0 Isp` and `mdot = thrust / v_e`, seed the sequential masses and durations exactly as `m_1 = m_0 exp(-delta_v_d/v_e)`, `tau_d = (m_0-m_1)/mdot`, `m_2 = m_1 exp(-delta_v_a/v_e)`, and `tau_a = (m_1-m_2)/mdot`.

For correction, scale the six component residuals as `rho = (delta_r/1000 m, delta_v/0.01 m/s)` and score `S = ||rho||_2`; the separate Euclidean position and velocity closure tests remain authoritative. Use forward differences `h = (1e-5 rad, 1e-5 rad, 1 s)` for each burn and trust scales `s = (0.25 rad, 0.25 rad, 600 s)` for each burn. Form the dimensionless columns `J_z[:,j] = (rho(x + h_j e_j) - rho(x)) / (h_j/s_j)`, require finite rank six, and solve `J_z dz = -rho` with `numpy.linalg.lstsq(..., rcond=1e-12)`. Scale `dz` by `1/max(1, ||dz||_inf)` and set `dx = s*dz`.

The seed must first produce one complete safe baseline. An analytically invalid or physically terminated seed returns status `targeting-failed` with reason `no-safe-complete-trial` without attempting a Jacobian. At each of at most eight iterations, evaluate forward probes in control order. If a probe is analytically rejected or terminates on dry mass or impact, do not propagate it mathematically to cutoff, do not switch difference direction, and stop correction because that Jacobian column is unavailable; the safe baseline remains eligible for status `targeting-failed` with reason `nonconvergence`. Otherwise try `x + alpha*dx` in the fixed order `alpha = (1, 1/2, 1/4)`. Accept the first safe trial that closes or satisfies `S_trial <= S_current * (1 - 1e-4*alpha)`; if none is acceptable, stop as `targeting-failed`. Finite-difference probes are never eligible commands. Among eligible safe commands, retain the deterministic lexicographic minimum `(S, ||delta_r||, ||delta_v||, propellant_mass, tau_d + tau_a, tuple(x))`. Reject a damping trial with a control/window, dry-mass, or collision violation, increment its deterministic rejection counter, and continue to the next alpha. A finite Jacobian with rank below six stops with status `targeting-failed` and reason `nonconvergence`; a non-finite propagated state, non-finite solve, or unsuccessful integration follows the fatal error contract and returns no result.

`control_attempts` increments before analytic validation for the seed and each correction probe or damping command. `propagation_evaluations` increments only when a control or frozen diagnostic starts its first native arc; an impact-terminated evaluation counts once, while an analytically rejected control does not. `native_arc_propagations` increments immediately before every native arc call, including an arc that terminates early. One seed plus eight iterations of six probes and three damping trials bounds correction at `1 + 8*(6+3) = 73` control attempts. The tighter-integrator, Moon-400, and Mars-60 frozen-command diagnostics add no control attempts but can bring a converged run to at most 76 propagation evaluations and 228 native arc propagations. The runtime deadline is an independent bound checked around every native call. This uses NumPy already pinned through TudatPy and avoids adding SciPy or an optimizer framework.

Tentative nominal closure triggers the three frozen-command diagnostics. Return status `converged` only after the tighter-integrator and Moon-400 bounds also pass and the finite Mars-60 tail is recorded. Exceeding a bounded diagnostic raises `TrajectoryRefinementError` for `scientific-validation` and returns no normal result; it is neither convergence nor targeting failure. Return status `mass-infeasible` with reason `preflight-m2-propellant-shortfall` only when the verified ideal M2 preflight budget already exceeds available propellant. If the bounded corrector finishes or loses finite rank without closure, return status `targeting-failed` with reason `nonconvergence` and the best complete safe trial when one exists. If none exists, use reason `no-safe-complete-trial`, null terminal/burn/actual-mass fields, and the sorted rejection counts. Invalid resources, non-finite output, failed integration, or deadline exhaustion remain errors rather than scientific statuses.

### 7. Use full production harmonics and separate sensitivity runs

The corrector and accepted nominal result use Moon 200/Mars 120. A frozen-command Moon 400/Mars 120 run quantifies lunar truncation sensitivity; a Moon 200/Mars 60 run exposes the last available Martian model increment. The 400-degree lunar run is diagnostic and does not silently replace the production result. The Mars 60-to-120 difference is reported without claiming convergence beyond the degree-120 coefficient ceiling.

A lower-degree coarse seed was considered. The measured 20-to-production endpoint difference exceeded 1000 km, so using that state inside the accepted correction path risks false convergence and is rejected for M3.

### 8. Separate integration error from model error

Use the current non-deprecated variable-step interface with elementwise tolerance vectors for the seven-component translation/mass state. Nominal RKF78 uses relative tolerances `(1e-11)*7`, absolute tolerances `(1e-3 m)*3 + (1e-6 m/s)*3 + (1e-9 kg)`, and burn initial/minimum/maximum steps `(1 s, 1e-6 s, 30 s)` versus coast `(300 s, 1e-3 s, 86400 s)`. Tighter RKDP87 uses relative tolerances `(1e-13)*7`, absolute tolerances `(1e-5 m)*3 + (1e-8 m/s)*3 + (1e-11 kg)`, and burn steps `(0.25 s, 1e-8 s, 7.5 s)` versus coast `(75 s, 1e-5 s, 21600 s)`. A requested step below the minimum, unsuccessful integration flag, or final epoch mismatch is a fatal `TrajectoryRefinementError` naming the arc and expected epoch; partial native history is discarded. Compare only identical exact arc boundaries and record independent-integrator differences separately from harmonic-degree sensitivity.

An isolated point-mass fixture supplies the required energy/angular-momentum invariant. The full trajectory has moving ephemerides, rotating harmonics, radiation pressure, thrust, and mass loss, so asserting full-trajectory conservation would be physically wrong.

### 9. Make dry mass, impact, and deadline hard boundaries

After constructing the physical environment and the two boundary states, return `mass-infeasible` before any finite-burn targeting propagation when the verified M2 candidate already exceeds the available propellant. During correction, reject a command before scheduling it when analytic maximum-thrust mass flow would cross dry mass. Also terminate Tudat propagation on dry mass and crossing any of the eight pinned collision surfaces as a defense against numerical or state-dependent discrepancies. Never clamp mass or continue below the boundary.

Use the scenario monotonic runtime limit across M2 verification, every correction evaluation, nominal repropagation, and numerical/model diagnostics. Check before and after each native propagation call and include propagation-evaluation count in deadline errors. Tudat cannot be safely interrupted mid-call, so a single call may cross the wall-clock boundary; it is rejected immediately afterward and no result is returned.

Create one deadline at API/CLI operation entry and pass it through M2 verification, resource construction/hashing, targeting, diagnostics, and manifest construction. Never restart a fresh 300-second clock for M2 or a later stage. This is a cooperative deadline, not a guarantee that a native call returns within 300 seconds. An expected impact/dry-mass early termination is a rejected trial; check this reason before treating a non-final epoch as an integration failure. Test both paths and initial states already on/inside a guard. Endpoint-only collision checks are insufficient: test an arc entering and leaving a guard between output epochs and verify that unsafe history is discarded.

### 10. Extend the CLI and provenance without new protocols

`space-nav refine SCENARIO --candidate-id ID [--json]` follows the existing parser, canonical JSON, human rendering, and error envelope. Completed physical classifications exit zero; malformed inputs and operational failures exit two. Human output makes nonconvergence or infeasibility prominent and never renders absent data as zero.

Extend the existing manifest rather than introduce a second provenance format. Include the M2 seed, force inventory, gravity models and hashes, field GMs/radii/frames, shape radii, SRP and occultors, relativity switches, burn law, integrators, corrector settings, thresholds, evaluation counts, and deferred scenario fields. Adaptive step histories remain private; M4 can request a stable sampling contract when observations actually need one.

### 11. Preserve the M2 budget baseline and qualify a trial fixture

Keep `examples/reference_mission.toml` unchanged and assert its preflight `mass-infeasible` status, explicitly labeled as rejection by the M2 seed-budget policy. Add `examples/m3_feasible_mission.toml` identical except for `dry_mass_kg = 500.0`. Preserve candidate identifier, geometry, epochs, excess velocities, delta-v, and ideal masses; `mass_feasible` changes from false to true and the aggregate feasible-candidate count may change. The filename is provisional: this is a propellant-admissible test case, not demonstrated physical feasibility. The fixture is an engineering regression case, not a proposed flight design.

Dry-mass feasibility does not prove that the six-control corrector can meet closure. Before production corrector work, a focused spike must demonstrate candidate `d0001-t0035` under the exact seed, force model, bounds, and 76-evaluation budget. Until that task passes, the eight-iteration/300-second feasible-fixture gate is an acceptance hypothesis, not measured performance; failure requires revising and revalidating this change rather than silently loosening the gate.

Retain the spike script and machine-readable evidence in the repository. First establish whether the exact seed completes safely; an unsafe seed is a failed prerequisite, not evidence of general mission infeasibility. Record trial controls, terminal residuals, safety reasons, counters, software/resources, machine, and elapsed time. Stop production corrector work if the gate fails. Revisit seed construction or the six-control formulation in this change before proceeding; do not merely reduce dry mass further or rename failure as convergence.

The stable `mass-infeasible` / `preflight-m2-propellant-shortfall` pair denotes only the selected seed-budget policy. Public text must not call the M2 patched-conic estimate a proven lower bound on fuel for the higher-fidelity problem. Likewise `converged` means a nominal trajectory passed the declared numerical checks, not flight readiness.

## Risks / Trade-offs

- **[Differential correction may diverge for a poor M2 seed]** -> Bound iterations and control steps, reject unsafe trials, retain the best safe result, and expose `targeting-failed` instead of loosening closure tolerances.
- **[Full harmonics multiply targeter cost]** -> Keep one selected candidate, cap eight iterations, terminate impacts early, measure every propagation, and enforce the existing 300-second deadline.
- **[Moon degree 200 leaves a measurable tail]** -> Record the degree-400 frozen-command difference under a `500 m`/`0.0001 m/s` diagnostic budget and never describe it as real-world uncertainty.
- **[Mars has no coefficient oracle above degree 120]** -> Report the 60-to-120 tail and label 120 as the pinned model ceiling rather than asserting unverified convergence.
- **[Gravity GMs and radii differ from M2 values]** -> Use each model consistently inside its milestone and include both old seed constants and M3 field constants in provenance.
- **[TNW guidance is not globally optimal]** -> State the fixed guidance law and leave optimized steering to a future accepted change.
- **[Completed classifications can be overinterpreted]** -> Label preflight rejection as an M2 seed-budget policy and `converged` as nominal numerical validation; neither establishes general mission impossibility or flight readiness.
- **[The feasible fixture changes spacecraft dry mass]** -> Keep it separate and clearly label it as a regression fixture; never rewrite the archived M2 reference.

## Migration Plan

1. Add and verify orbit-state semantics, immutable result contracts, candidate handoff, and failure statuses without importing TudatPy eagerly.
2. Add the force-model builder and independent acceleration/resource checks.
3. Add segmented burn/coast propagation, mass safety, and pure/short physical checks.
4. Run the exact targeting spike; only if it proves the accepted bounds, add the bounded production corrector, feasible regression fixture, numerical/model diagnostics, CLI, and provenance.
5. Run focused scientific checks, the full pinned suite, legacy isolation, reference/feasible completion gates, and strict OpenSpec validation.

Rollback removes the additive M3 module, exports, command, fixture, and tests. Existing M1/M2 scenario parsing and commands remain valid throughout.
