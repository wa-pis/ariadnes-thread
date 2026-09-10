## Context

### Native terminal-epoch gate (2026-09-10)

The float-only completion gate can hide a final-time violation: around TDB
978995455.2304223 s, native offsets of approximately +/-1.01 microseconds
both produce float-label offsets of +/-0.95367431640625 microseconds.
The latter pass the unchanged 1-microsecond gate while the native offsets
do not. `_read_completed_arc_state` now additionally requires native Time
history, checks that its latest epoch maps to the selected float label, and
compares `(native_terminal - expected).to_float()` against the same limit.
Subtract before converting. Missing/empty/invalid native time fails with a
chained contextual error; there is no float-only fallback. Keep the existing
completion flag, float-history, state, mass and safety-precedence checks.

Real Tudat Time tests exercise +/-0.99 and +/-1.01 microseconds and zero
offset. Existing native burns, handoff, conservation and minimum-step tests
exercise the reader against actual simulators. Injected tests cover missing,
empty, inconsistent, nonfinite and failing native-time data. This fixes a
boundary acceptance error without changing output types or tolerances; it
does not correct arbitrary saved-state time labels, resample states or
establish interval safety. Tasks 3.9 and 3.5 remain open.

### High-resolution native time isolates the mass-label error (2026-09-10)

The installed TudatPy 1.0 binding documents `state_history_time_object` as
the same history keyed by the high-resolution `Time` independent variable.
Its Time API stores integer hours and a sub-hour remainder and permits
subtraction before `to_float()`. Reuse all 72 existing controls with no new
propagations: pair each native-time entry with its ordinary float-key entry,
require equal counts and identical state values, then compute elapsed
seconds as `(native_epoch - Time(initial_epoch)).to_float()`. This preserves
the small elapsed interval before conversion instead of subtracting already
rounded large absolute epoch labels.

Every saved mass now satisfies the unchanged `max(1e-8 kg,
1e-11 * consumed_mass)` oracle at the native elapsed time. The original
18 float-label counterexamples remain asserted separately. The observed
label shift is at most half an absolute-epoch ULP plus half an elapsed-time
ULP, checked exactly with Fractions. Shifted-epoch maxima are:

| Integrator | Native-elapsed mass error (kg) | Absolute-label elapsed shift (s) |
|---|---:|---:|
| RK4 | 5.18140157752548e-11 | 4.7706407713121735e-8 |
| Nominal RKF78 | 6.133610589705078e-13 | 0 |
| Tighter RKDP87 | 5.657159660278695e-12 | 5.827462246088544e-8 |

Only the epoch representation used by the oracle changes; native states and
integrator settings do not. This isolates the prior threshold violations to
state/time-label association in these fixtures, not a demonstrated failure
of integrated mass at its native epoch. The float-label boundary still needs
an explicit timing-error treatment before safety use. These sample checks
are not uniform integration/Time-arithmetic certificates or permission to
shift frames, time scales or scientific tolerances. Keep 3.9/3.5 open.

### Mission-epoch mass-history counterexample (2026-09-10)

Repeat the 36 isolated engine controls with ignition shifted from TDB 0 to
978995455.2304223 s since J2000, the qualification candidate's start epoch.
The synthetic stationary geometry is unchanged: this is an epoch-translation
control, not a real mission propagation. Both tested durations (0.25 and
100.25 s) remain exactly representable as the difference of endpoint epochs,
verified with Fractions. The mass oracle uses the exact difference of each
saved epoch and the ignition epoch; it does not round elapsed time first.

All 36 shifted controls pass the existing final mass, epoch, velocity and
guidance checks. However 18 violate the unchanged saved-state mass tolerance
`max(1e-8 kg, 1e-11 * consumed_mass)`: all 12 RK4 controls and the six tighter
100.25 s controls. Keep these as explicit expected counterexamples; all 36
original zero-epoch controls and the other 18 shifted controls must still
have no violations. No test is skipped and no tolerance is increased.

Shifted-epoch measurements (6229 saved states, 2418 tolerance violations):

| Integrator | Saved states | Violating states | Maximum sampled error (kg) |
|---|---:|---:|---:|
| RK4 | 6048 | 2412 | 1.086197618146042e-8 |
| Nominal RKF78 | 54 | 0 | 6.133610589705078e-13 |
| Tighter RKDP87 | 127 | 6 | 1.3204770034323948e-8 |

The worst tighter sample is at TDB 978995456.6371623 s, in the 2000 kg,
100.25 s inertial fixture. Per-control JSON retains the initial and peak-error
TDB epochs, counts and kg residuals. Shifting the epoch changes the observed
error; this does not yet isolate native time arithmetic from integration
updates or justify a remedy. In particular, a tighter profile is not an
interval-error certificate. The prior zero-epoch evidence remains valid
only for its declared fixtures. Keep 3.9/3.5 open; do not use these sample
maxima as safety bounds or alter the full-force model, timing contract,
integrators, native-call limits or shared 300-second deadline.

### Conditional interval mass floor (2026-09-10)

Add the private `_mass_lower_bound` arithmetic primitive. For positive anchor
mass `m0`, nonnegative uniform mass-error enclosure `E`, consumption-rate
upper bound `Q` and duration `h`, return a downward-rounded binary64 value
of exact `m0 - E - Q*h` kg. If consumption is bounded by Q throughout the
interval and all initial/native/integration mass deviations are enclosed by
E, integrating the rate inequality gives this floor for every elapsed time
in `[0,h]`. Required premises are explicit inputs, not inferred from saved
samples or solver tolerances. Timing effects must be included in the supplied
duration/rate/error enclosures. No production safety path uses this helper yet.

Exact Fraction arithmetic followed by conditional nextafter toward minus
infinity preserves sub-ULP deficits, exact zero and signed negative floors.
A floor below dry mass is unresolved, not proof of crossing; no clamping or
public status is introduced. Validate finite inputs, positive initial mass,
nonnegative remaining fields, output overflow and the shared deadline at
entry/exit. No native counters are incremented. Tests cover exact constant
flow/coast, subnormal and rounded-boundary cases, and variable consumption
`q(t)=t kg/s`, `m(t)=10-t^2/2 kg` with a declared 0.25 kg error enclosure.
The latter includes an unresolved conservative floor while the exact mass
stays above dry mass. These analytic controls do not qualify native mass
errors or complete tasks 3.9/3.5; tolerances and budgets are unchanged.

### Saved native mass history versus exact constant flow (2026-09-10)

Reuse all 36 isolated native burn controls (two durations, two initial masses,
three guidance modes and three integrators), without additional propagations.
At each saved TDB epoch, compare mass to exact Fraction evaluation of
`m0 - T*t/(g0*Isp)` on stored binary64 inputs; ignition is TDB 0 s in these
fixtures. Retain the existing final-state and rocket-equation checks, and
apply the unchanged `max(1e-8 kg, 1e-11 * consumed_mass)` mass tolerance at
each saved state. Validate finite seven-component states and nonincreasing
saved mass. This is neither internal-stage nor between-output safety.

The focused run observes 6229 saved states. Maximum sampled error is
5.727098398589237e-11 kg (2000 kg initial mass, 100.25 s inertial RK4 burn).
6193 samples exceed the conditional Python rate-only error margin; every
fixture contains such a counterexample, now asserted. This does not refute
the conditional two-operation rate bound: native engine arithmetic, state
updates and timing are outside its scope. The sampled residual does not
isolate those contributions, and its maximum is not a uniform bound to use
in safety screening. Reproducible per-fixture JSON reports units, sample
counts, peak errors and rate-only exceedance counts. No native-call budget,
force, tolerance or production behavior changes; tasks 3.9/3.5 remain open.

### Conditional mass-rate roundoff envelope (2026-09-10)

The Python control gate retains two rounded operations, exhaust velocity
`g0 * Isp` and rate `T / exhaust`. For positive normal binary64 operations
rounded to nearest, with unit roundoff `u = 2^-53`, their rate satisfies
`q_hat/q = (1+d_div)/(1+d_mul)` and relative error at most `2u/(1-u)`.
Here `q` is the exact law on the stored binary64 inputs, not a claim that
binary64 g0 equals its decimal definition exactly. At constant thrust, the
mass error for every powered duration in `[0,h]` is bounded by
`q * 2u/(1-u) * h`; coast introduces no consumption in this analytic law.
This conditional enclosure excludes underflow/overflow, native engine
arithmetic, state integration error and arc-boundary timing error.

Six exact-Fraction controls use 2000 kg initial mass, dry mass 1000 kg or
either adjacent float, 1000 s powered duration, and Isp 300/450 s. Set thrust
to the rounded `9.80665 * Isp`, giving computed rate exactly 1 kg/s. At Isp
300 s the exact stored-input law consumes 2.1736558430047985e-14 kg more
than the available 1000 kg while the current gate accepts equality. At
450 s it consumes 8.131082968277209e-14 kg less. The conditional rate-error
margin exceeds even the adjacent-float mass headroom in all six controls:
none certifies dry-mass safety using that enclosure. Preserve this explicit
counterexample rather than equating an accepted control with a safe trajectory.
No production behavior, tolerance or native-call limit changes; tasks 3.9
and 3.5 remain open pending native and integrated interval-mass evidence.

### Analytic mass-gate rounding correction (2026-09-10)

The existing analytic control gate could accept a sub-ULP mass shortfall.
With the existing calculated mass rate exactly 1 kg/s, initial/dry masses
2000/1000 kg and burn durations 500 s and nextafter(500,+infinity) s, the
rounded duration sum is 1000 s. The old computation therefore reports exactly
dry mass and accepts, although the exact sum of the validated binary64
durations consumes 5.684341886080802e-14 kg too much at that mass rate.

Retain the existing exhaust-velocity/mass-rate calculation and its validation.
After it, form the duration sum, consumed mass and remaining mass exactly as
Fractions, and compare with the exact binary64 dry-mass value. Retain the
finite-result/overflow guard. No epsilon or tolerance is introduced: equality
remains accepted; either adjacent representable duration is classified on
the correct side of the threshold. All callers use the shared control gate.

This fixes downstream summation/product/subtraction rounding, not uncertainty
in the calculated mass rate, native engine arithmetic or integrated mass.
Those remain separate prerequisites for an interval mass enclosure and
propagated dry-mass safety. Keep tasks 3.9 and 3.5 open; no force, kernel,
scientific tolerance or work limit changes.

### Declared phase-domain full-force controls (2026-09-10)

Connect the new distance-floor primitive to the existing direct-SPICE
near-Moon, cruise and near-Mars force controls for coast and both burns.
Retain all prior percentage-margin bounds and component parity checks.
Add a separate declared domain: spacecraft and each source position lie in
10 m balls around their fixed-epoch anchors; spacecraft and Sun velocity
lie in 1 m/s balls. These radii are explicit test inputs, not hidden mission
defaults or claims about actual between-epoch motion.

For every gravity source, compute the downward separation floor and verify
its squared-distance implication independently with exact Fractions. Feed
these floors into the existing degree-200/120 harmonic and monopole bounds.
For Schwarzschild, use an outward bound on the exact L1 anchor-relative
velocity plus both 1 m/s radii; L1 bounds Euclidean speed. Reuse the declared
dry-mass thrust/SRP bounds and all-component summation. Compare the native
full-force value at each domain center to the new majorant, preserving all
existing numerical tolerances and native propagation counters.

Print both old and new total bounds with domain radii and control labels so
their numerical differences remain inspectable. The historical table path
is unchanged. These are spatial phase-domain controls at fixed epochs, not
evidence that a real arc stays inside the balls, nor uniform native force
roundoff bounds. Ephemeris/time-domain, mass/speed closure and propagated
state-error premises remain open under 3.9; production settings do not change.
Observed coast totals (old -> declared-domain, m/s^2): near-Moon
1.4810058584359551 -> 1.4776833812418995; cruise
0.004741393414576713 -> 0.004731915483136204; near-Mars
3.1869964690322714 -> 3.180447036857837. All nine direct full-force controls
pass both bounds; these changes describe the additional test domain, not a
changed force model or tolerance.

### Conditional whole-interval body reach (2026-09-10)

The two-epoch displacement bound does not alone provide an anchor-centered
ball for all intermediate epochs. For [a,b], take Emax as the maximum of
the chain arithmetic bound and every chain join envelope whose closed
16-ULP strip intersects [a,b]. Include intersecting strips even when their
central join epoch lies just outside the interval. With the previous global
rate majorant L and exact jump sum J over [a,b], use
`R = L*(b-a) + J + E(a) + Emax` meters around native position N(a).

For any t in [a,b], the two-epoch proof gives L*(t-a), the crossed jump
sum up to t, and E(t). Each nonnegative term is bounded by its corresponding
whole-interval term, so the same R encloses every N(t), conditional on the
existing native premises. The L1 bound also encloses Euclidean displacement.
This allows a position ball without treating endpoint error estimates as
uniform error estimates or assuming a smooth SPK representation.

Reuse all existing native states for adjacent panels and complete candidate
intervals. Verify 3,266 anchor-to-state comparisons, containment of both
endpoint error bounds, and outward binary64 radius reporting. For every
body, the full-interval Emax is strictly larger than either candidate-endpoint
error bound, preserving the interior-strip distinction. No extra SPICE
queries or native propagations are introduced.

The resulting conditional radii are deliberately coarse, especially on long
intervals. They are not physical orbit uncertainty, a spacecraft enclosure,
a native execution certificate, or proof of usable safety/performance bounds.
Production safety remains unwired and task 3.9 remains open.

### Velocity-domain first-exit counterexample (2026-09-10)

For a force majorant A valid only inside a position/speed domain, the
first-exit argument must close both coordinates: require initial inclusion,
`e+v0*h+A*h^2/2 < R` and `v0+A*h < V`. Before a hypothetical first exit
through either boundary, both integral bounds hold and contradict that exit.
Positional inclusion alone does not establish a speed-dependent force bound.

Use the synthetic SI control x'=v, v'=k*v^2 with k=1/m, x0=0 m and v0=1 m/s.
Its exact solution, in these SI units, is v=1/(1-t), x=-log(1-t) for t<1 s.
A trial |x|<=2 m, |v|<=2 m/s implies A=4 m/s^2. At h=0.1 s both strict
tests pass. At h=0.25 s the speed majorant equals 2 m/s, so the strict test
is unresolved even though the true speed is still below the boundary. At
h=0.75 s the position majorant remains 1.875 m < 2 m, but true speed is
4 m/s and true acceleration 16 m/s^2: position-only acceptance would rely
on a false force premise. The exact position remains inside the trial box.

Verify these cases using exact rational speed values and the independent
analytic position formula, with no new production API or native work.
This synthetic counterexample is not the actual Schwarzschild model and
does not establish M3's speed, mass, ephemeris or numerical-error domains.
It records a required joint-domain check before any real safety integration.
Keep task 3.9 and all production decisions/limits unchanged.

### First-exit closure on a monopole control (2026-09-10)

A trial position-ball radius R is not itself a proven reach. First establish
an acceleration majorant A on the entire trial domain for the whole time
interval, using independently enclosed source positions. If initial error
e<R and the integrated reach e+v*h+A*h^2/2 is strictly below R, a continuous
trajectory cannot first exit that domain by h: until a hypothetical first
exit A applies, yet the integration inequality places the exit point
strictly inside. This closes the positional assumption without substituting
an acceleration measured only at the initial state. Equality fails this
strict sufficient test; a failed test is not generally proof of collision.

Compose the existing distance-floor, monopole-force and reach helpers on
the analytic orbit GM=1000 m^3/s^2, radius=10 m, angular speed=1 rad/s.
Use a 1 m trial ball centered on (10,0,0), with source reach 0 or 0.25 m
(the actual source is stationary). The domain force bound exceeds the
anchor acceleration of 10 m/s^2. A 0.05 s interval closes; a 1 s interval
does not, and the analytic circular orbit actually leaves the trial ball.
Check the independent circular displacement formula and its Cartesian
identity within 1e-12 m, singularity-containing domain rejection, and the
strict equality boundary using an exact constant-velocity control.

These are analytic controls only, with no native propagations. For M3 the
full force field also needs a velocity domain for the Schwarzschild term,
mass/dry-mass bounds for thrust/SRP, time-dependent ephemeris enclosures and
native force-evaluation/numerical trajectory error controls. A position-only
first-exit argument does not discharge those premises. Keep 3.9 and production
safety unchanged; do not infer real-mission safety or native-call limits.

### Conditional position-reach integration bound (2026-09-10)

For a continuous position trajectory with initial anchor error e, initial
speed at most v and acceleration norm at most A throughout [0,h], integrating
the acceleration inequality twice gives an anchor-centered reach radius
`R = e + v*h + A*h^2/2` meters. All four inputs are explicit, finite and
nonnegative; v must include initial velocity uncertainty. The acceleration
premise must be independently established on the entire region reached.
Using an acceleration evaluated only at the initial state would be circular
and is not allowed. Discontinuous SPK source representations still require
their separate jump-aware ephemeris enclosure, not this smooth-motion formula.

The private helper computes the expression with exact Fractions and rounds
binary64 upward only when needed. Exact zero is preserved; a positive value
below the smallest subnormal rounds upward, and unrepresentable upper bounds
fail. Check both shared-deadline boundaries without incrementing native work.

Verify exact kinematics for zero duration, initial error, constant velocity,
constant acceleration, mixed binary inputs and positive underflow; reject
negative/boolean/nonfinite inputs and overflow. Compose the reach and distance
helpers on x_ship(t)=10-t-t^2 and x_body(t)=t over [0,1] seconds: the exact
minimum is 7 m, and the computed floor may establish clearance for a 6 m
guard but not an 8 m guard. This analytic control does not establish the
full-force acceleration premise, integration error or actual mission safety.
Production safety remains unwired and task 3.9 remains open.

### Conditional relative-distance floor (2026-09-10)

Add a private geometry primitive for two declared SSB/J2000 position balls.
Given anchors x0 and b0 and nonnegative reach radii Rx and Rb, return a
downward-rounded lower bound for `norm(x0-b0) - Rx - Rb` in meters. The
reverse triangle inequality supplies the geometric implication; the caller
must independently enclose all spacecraft/body motion and numerical error
inside the two balls over the requested interval. The helper does not make
that assumption true and is not connected to production safety decisions.

Compute squared anchor separation exactly from the binary inputs using
Fractions, convert its rational value downward in an isolated 50-digit
Decimal context, and take the predecessor of the half-even square root.
Subtract both radii exactly as Fractions, then round the returned binary64
value downward. Handle coincident anchors exactly. Negative lower bounds
are retained, not clamped; nonpositive results establish neither clearance
nor actual impact. Reject invalid vectors, boolean/nonfinite scalars,
negative radii and unrepresentable outputs with a chained domain error.

Verify translated 3-4-5 triangles against exact rational distances and
attainable collinear displacements, irrational norms by exact squaring at
scales 1e-300 through 1e300, tangency/overlap, poisoned Decimal context,
invalid inputs, overflow and both shared-deadline checks. No native work
counters are incremented. This prerequisite closes neither the input reach
enclosures nor the full-force trajectory error and safety requirements.

### Conditional two-epoch body-motion composition (2026-09-10)

Let R(t) be the nominal piecewise exact source-polynomial chain in SSB/J2000,
and N(t) its native SI position. Use a global rate majorant L equal to the
sum of each link's maximum qualified record position-rate bound, not a
sampled velocity maximum or the separate type-3 velocity polynomial.
For a <= b in the candidate interval, the triangle inequality gives
`|N(b)-N(a)|_1 <= L*(b-a) + sum(J in [a,b]) + E(a) + E(b)`.
The jump sum includes every crossed source-link join, counting simultaneous
joins from both links. Inclusive endpoint membership is conservative for
either nominal boundary convention. E is the existing chain arithmetic
bound in record cores or the chain join envelope in a 16-ULP strip.

The proof splits R at every source join, bounds each smooth piece by its
rate majorant, adds the intervening jumps, and then adds both native endpoint
errors. It must not omit either endpoint error or assume source continuity.
Reuse the 1,078 existing chain-side states and read 16 candidate-endpoint
states, verifying that every link at those endpoints lies in exactly one
qualified core. Check all adjacent sample pairs and each body's entire
candidate interval: 1,094 exact-rational L1 displacement comparisons.

This is a deliberately coarse conditional displacement bound, not a chord
error, spacecraft trajectory error, collision-clearance certificate or
useful subdivision-count measurement. Its native premises remain those of
the preceding qualification. No production safety wiring, force, tolerance,
deadline or native-call limit changes; task 3.9 remains open.

### All-body center-chain join composition (2026-09-10)

Extend the Moon/Earth composition to every union of source-link join epochs
for the eight production bodies. Exact rational comparisons prove distinct
16-ULP strips within a chain are disjoint. For every nonjoining link, require
the entire event strip to lie inside exactly one previously qualified record
core; evaluate that record's polynomial at the same query epoch. Thus no
unchanging link is silently dropped or treated as a zero position.

For active joining links A, use
`B_chain + sum_A(J_link + h*(L_link_left + L_link_right))` meters.
Nonjoining links contribute through B_chain, which already includes every
link's evaluation error and chain addition/SI conversion. No motion term is
needed for them in this same-epoch comparison. This is not a bound on
two-time displacement or numerical spacecraft propagation.

There are 539 body/event pairs: Sun 18, Mercury 36, Venus 18, Earth 73,
Moon 73, Mars 172, Jupiter 67 and Saturn 82. Only Moon has simultaneous
two-link joins (73). All 1,078 one-ULP-side SPKSSB L1 comparisons with exact
polynomial sums fit their own outward-rounded bounds. The generalized Moon
bounds must equal the previous dedicated controls exactly. The largest
composed envelope is 14.382604265140298 m for Jupiter; it includes the known
source-representation jump and does not replace the unchanged 0.001 m
arithmetic criterion or describe physical orbit uncertainty.

Native execution/selection premises remain conditional, and the side probes
are not an exhaustive runtime certificate. This completes the test-only
composition across the inventoried chain join configurations, not task 3.9,
full-force error propagation, safety or runtime-budget qualification.

### Coincident Moon/Earth join composition (2026-09-10)

The inventories for Moon relative to Earth and Earth relative to SSB have
exactly the same 73 internal join epochs. At each join, bound the Moon's
SSB position against the sum of either adjacent exact polynomial per link:
`sum(J_link) + h * sum(L_link_left + L_link_right) + B_chain`, in meters,
where h is 16 epoch ULPs and B_chain is the existing uniform Moon-chain
evaluation/addition/SI error bound. The triangle inequality composes both
representation jumps without assuming cancellation or independent errors.
This is a same-epoch comparison, not displacement between two query times.

For each join, exact rational arithmetic verifies every pair of the four
mixed endpoint sums against sum(J_link). Then 146 direct SPKSSB positions
at the one-ULP sides are compared with exact sums of the nominal-side
polynomials. Require each L1 error to fit its own outward-rounded envelope.
Retain the existing 0.001 m arithmetic gate: the composed envelope is a
different quantity including source-representation ambiguity, not a relaxed
arithmetic tolerance or a physical orbit-uncertainty estimate.

The uniform implication remains conditional on the previously stated native
selection and arithmetic premises. The native probes verify only their query
epochs. Other center-chain join configurations, runtime premises and complete
spacecraft error/safety remain open under 3.9; no production settings change.

### Exhaustive representable-epoch Saturn priority strip (2026-09-10)

The previously excluded cross-segment strip is centered at
986817600 TDB seconds since J2000 with half-width 16 ULPs. Enumerate all 33
binary64 epochs in this closed strip; exact endpoint checks and consecutive
`nextafter` equality prove that no representable input epoch is skipped.
The complete inventory contains exactly two relevant Saturn segments in
the same file. Their coverage intervals intersect only at the junction;
the left-time segment occurs later in DAF order.

[NAIF's segment-priority contract](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html#Segment%20Order%20and%20Priority)
selects the later-in-file applicable segment for the same target. Consequently
only the left segment is eligible before the junction, both are eligible at
it (left wins), and only the right segment is eligible afterward. Verify this
eligibility independently from descriptor intervals before native selection.

Query all 33 epochs in forward, reverse and even/odd-interleaved orders.
All 99 SPKSFS results match the expected file handle and complete descriptor
bytes. Then read the selected record: it matches the left segment's last or
right segment's first DAF record byte-for-byte, including the last-record
clamp at the exact junction. All prior coverage, core/strip, source-jump,
roundoff and kernel-pool-preservation checks remain intact.

This exhausts the epoch inputs in this fixed strip for three query orders,
not all possible cache histories, altered kernel pools or other builds.
It supplies the previously separate Saturn priority-strip evidence without
extending a single-segment monotonicity proof across segment boundaries.
Runtime arithmetic premises, simultaneous center-chain joins and spacecraft
safety remain separate under 3.9. No production setting, kernel, scientific
tolerance or native-call limit changes.

### Conditional within-segment selection domains (2026-09-10)

For each of the 550 inventoried records, form a closed core trimmed by 16
epoch ULPs at its nominal ends and clipped to the candidate interval. All
core endpoints are exactly representable binary64 epochs. At 1,100 native
core endpoint reads, the complete returned record matches that core's DAF
record byte-for-byte and agrees with the inspected index replay.

For the 538 joins internal to a single segment, read the selector at b-h and
b+h, h=16 ULPs. All 1,076 additional reads return exactly the left and right
records, respectively. Under a fixed correctly rounded arithmetic profile,
subtraction of INIT, division by positive INTLEN, in-range integer truncation
and the final min-clamp are nondecreasing in epoch. The previously qualified
integer/range premises exclude wraparound or invalid conversion. Therefore
equal endpoint indices force one index throughout a core; adjacent endpoint
indices confine selection to those two records throughout an internal strip.
This is a monotonicity argument with native endpoint controls, not an inference
from arbitrary sparse samples.

Merge the 550 cores and all 539 closed join strips using exact rational
endpoints. Their union covers the full candidate interval without gaps for
each of the 11 source links, including both candidate endpoints. Intervals
may share endpoints; no representable epoch is silently discarded.

One strip is intentionally outside the within-segment result: target 699 at
986817600 TDB seconds since J2000 joins two different file segments. Its
selection requires segment-priority reasoning, not monotonicity of either
individual reader outside its segment. The strip remains in the geometric
cover but is explicitly excluded from the 538 internal-strip selector claim.
Keep native runtime/rounding premises, this priority boundary, simultaneous
center-chain joins and spacecraft safety separate under task 3.9. No kernels,
production settings, scientific tolerances or native-call limits change.

### Conditional native envelopes at every inventoried join (2026-09-10)

Extend the existing exact-branch treatment to all 539 internal joins across
the 11 source links, retaining all previous source-jump and early-selection
counterexamples. For join epoch b use h=16 epoch ULPs on each side. Check
that boundary and record-midpoint ULPs agree, so both existing extended rate
and arithmetic bounds apply on [b-h,b+h]. Here h is exactly
`1.9073486328125e-6 s` for every inventoried join.

Let J be the exact L1 difference of the two endpoint polynomials, L_left and
L_right their extended L1 position-rate bounds, and E_left/E_right their
individual evaluation-plus-SI-conversion bounds. Conditional on native
selection being one of those two records, its position at any t in the strip
differs from either exact record polynomial at that same t by at most
`J+(L_left+L_right)*h+max(E_left,E_right)` meters. This follows by routing
the exact polynomial difference through b and adding the selected record's
arithmetic error. It is not a two-time displacement bound; comparing two
native evaluations would require both arithmetic errors.

The new native-readback variant compares the existing 1,078 one-ULP side
queries to their nominal exact polynomials using exact rational differences
from native SI values. Every comparison lies inside its own outward-rounded
envelope. Removing J fails 221 comparisons, preserving rather than masking
the known early-selection counterexample. Envelopes range from
`3.725238072706269e-5 m` to `14.382176411464647 m` (target 599 at
`1003871232 TDB seconds since J2000`). Their size includes representation
differences, not just floating-point rounding or physical orbit uncertainty.
No millimeter gate is applied to or replaced by this distinct quantity.

This treats one source link at a time. It does not prove the two-record
selection premise or segment priority, compose simultaneous joins along a
center chain, bound velocities, or establish spacecraft safety. Keep those
obligations and the existing sub-millimeter arithmetic-only bounds separate.
Native comparisons use only the already qualified Darwin/arm64 variant;
the original portable checks remain unchanged. Task 3.9 stays open with no
production, kernel, tolerance or native-call-limit changes.

### Conditional interval-wide position-chain composition (2026-09-10)

For each of the 550 inventoried records, bound the exact position polynomial's
L1 magnitude by `P=sum_axis,sum_k |c_k|*T_k(q)` in km, using the already
qualified q>=1 domain. Add its uniform position-evaluation bound E/1000 to
obtain a native-output magnitude bound M. Exact rational evaluation avoids
rounding the coefficient majorant inward. All 3,300 supplied-record probes
check both the exact polynomial magnitude against P and native magnitude
against M; these are checks of coefficient-derived bounds, not sample maxima
used as bounds.

Take the maximum record M and outward E for each source link, then sum them
over each of the eight declared one- or two-link J2000 chains. Write these
sums as M (km) and E (m). For a two-link chain the extra L1 addition error is
bounded by `A=u*M+3*eta` km; copying a single link has A=0. Unit conversion
then contributes `C=u*1000*(M+A)+3*eta` m. Thus the total conditional L1
position error relative to the exact selected-record sum is
`B=E+1000*A+C` m. The factor three accounts for the componentwise absolute
underflow terms. Check native and scaled magnitudes against the finite
binary64 range; report B with upward rounding.

This bounds every allowed combination of inventoried source records on their
qualified extended domains, not just the 38 previously sampled epochs.
Constructed aligned/opposed vectors at the link magnitude limits independently
check the addition/conversion term against exact rational sums; these are
arithmetic controls, explicitly not mission states. All eight B values are
below the unchanged 0.001 m gate. The largest is
`0.0007284371515436439 m` for Saturn, of which at most
`0.0004811117291734273 m` is addition/conversion. Jupiter's B is
`0.0004281144922474497 m`; the smallest is the Sun's
`1.4595070471278306e-7 m`.

The result remains conditional on each selected record being in the inventory,
its epoch lying in its qualified extended domain, the inspected position
arithmetic, round-to-nearest with gradual underflow, and add-then-scale chain
composition. It does not include differences between competing record or
segment polynomials, certify selection/dispatch throughout the interval,
bound physical ephemeris uncertainty or velocity evaluation, or establish
spacecraft safety. Keep those obligations separate under 3.9; no production
settings, kernels, scientific tolerances or native-call limits change.

### Sampled center-chain and SI arithmetic (2026-09-10)

Extend the existing eight-body, 38-epoch chain inventory without changing
production queries. Read each selected segment state through SPKPVN and
verify its J2000 orientation and expected center. The four direct-to-SSB
bodies have one link; Moon, Mars, Jupiter and Saturn have two. Across 304
body/epoch states and 456 link reads, copying one link or adding the two
links componentwise in km/km/s matches SPKSSB bit-for-bit. Multiplying that
result by 1000 matches both the Tudat SPICE wrapper and production direct
ephemeris bit-for-bit for all six components.

Isolate the extra arithmetic error relative to the already-rounded link
states, not the exact source polynomials. For each component, form their
exact rational sum S. The two-link addition has conditional rounding bound
`e_add=u*|S|+eta` in native units; one-link copying has zero error. With
native summed value y, the unit conversion has bound
`e_scale=u*|1000*y|+eta` in SI. Use the previous round-to-nearest/gradual-
underflow assumptions and explicitly exclude overflow. The combined bound
is `1000*e_add+e_scale`; compare each term and their combined error against
exact fractions and report the sum of three absolute component errors.

Maximum sampled additional L1 errors are `0.00024531567112262564 m`
(Saturn) and `5.491607169005874e-12 m/s` (Moon). Maximum sampled local
bounds are `0.0004777256199478826 m` and `1.1281778968486291e-11 m/s`.
Every local bound is below the existing `0.001 m` / `0.000001 m/s` gate.
These maxima are not uniform interval bounds and omit source-polynomial
evaluation errors; do not interpret them as total ephemeris accuracy.

Reordering to scale each link before addition changes at least one component
at 33 Moon, 33 Mars, 36 Jupiter and 38 Saturn epochs. Retain this countercheck
so a mathematically equivalent but differently rounded composition cannot
silently replace the observed order. This is sampled evidence, not static
dispatch certification. Next derive interval-wide link-magnitude bounds and
compose them with the supplied-record error bounds, retaining separate
record/segment-choice and floating-point-mode premises. Task 3.9 stays open.

### Conditional uniform supplied-record position error (2026-09-10)

Assume the inspected fused position graph, binary64 round-to-nearest and
gradual underflow throughout evaluation. For exact operation result z,
use `|RN(z)-z| <= u|z|+eta`, where `u=2^-53` and `eta=2^-1075` in the
operation's units. The additive term covers subnormal rounding, not flushing
to zero; overflow is excluded separately. See the rounding and gradual
underflow discussion in [Goldberg](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html).
These are explicit conditional premises, not continuous CPU-mode observation.

For a supplied record with midpoint m, radius r and extension h=16 epoch ULPs,
exact rational endpoint inequalities put every binary64 epoch in
`[m-r-h,m+r+h]` inside the positive Sterbenz domain `[m/2,2m]`. Thus the
subtraction t-m is exact. With `Q=1+h/r`, division contributes normalized
error at most `d=uQ+eta`. Round Q+d upward to a binary64 upper bound q.
All 550 records satisfy `1<=q<2`, so doubling any represented normalized
argument is exact and cannot overflow. Enlarge the existing exact-polynomial
rate helper's domain outward to include q; its L1 rate bound L contributes
at most `L*r*d` meters for normalization error.

Bound the remaining recurrence at any fixed represented argument |s|<=q.
Set trailing computed-magnitude majorants A_(n+1)=A_(n+2)=0. For k=n,...,1,
let `S_k=2q*A_(k+1)+A_(k+2)`, `F_k=(1+u)S_k+eta`, and
`A_k=(1+u)(F_k+|c_k|)+eta`. The local fused-plus-add residual satisfies
`R_k=u*S_k+eta+u*(F_k+|c_k|)+eta`. For the final k=0 operation use
`S_0=q*A_1+A_2` and the same residual formula. Check both S_k and
F_k+|c_k| against the largest finite binary64 number before using these
bounds; no observed-small-intermediate assumption is used.

The local residuals act exactly as coefficient perturbations in Clenshaw's
recurrence, giving `p_hat-p(s)=sum(delta_k*T_k(s))`, |delta_k|<=R_k.
For q>=1, `|T_k(s)|<=T_k(q)` on [-q,q]: inside [-1,1] the bound is 1;
outside use the monotone hyperbolic-cosine representation. See
[DLMF Chebyshev representations](https://dlmf.nist.gov/18.5#E1).
Compute `sum(R_k*T_k(q))` with exact fractions, sum the three component
bounds, convert km to m exactly and add L*r*d. Round only the reported
final bound upward. This is a uniform conditional error enclosure relative
to the exact supplied-record polynomial at the requested epoch.

The 550 record bounds range from `4.868023067692928e-10 m` to
`0.0002473194716238903 m` (largest for target 6), all below `0.001 m`.
All 3,300 native supplied-record controls lie within their own bound and
retain bit-exact fused replay parity. Independent single-mode polynomial
controls cover degrees 0/1/2/19 at q=1 and 5/4; constant/linear closed-form
residual checks, a smallest-subnormal half-way rounding control, overflow
rejection and expired-deadline checks guard the derivation's implementation.
Every rational loop consumes the existing shared qualification budget.

The enclosure does not include wrong-record or segment-priority effects,
center-chain summation, floating-point km-to-m conversion, derivative or
stored-velocity evaluation, or spacecraft integration error. It is not a
bound on physical ephemeris uncertainty. Native dispatch and uninterrupted
rounding-mode premises remain conditional. Keep this helper test-only and
task 3.9 open until these remaining terms and interval-safety composition
are qualified; production settings and tolerances are unchanged.

### Native position-polynomial arithmetic replay (2026-09-10)

The pinned binary's SPKE02 path calls CHBINT for three position polynomials
and their derivatives; SPKE03 calls CHBVAL for six stored components.
[NAIF CHBINT](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/chbint_c.html)
and [CHBVAL](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/chbval_c.html)
document the coefficient and midpoint/radius contracts. Static inspection
shows that both position paths normalize time with separate subtraction and
division, then use the same fused Clenshaw recurrence. Unlike the previously
inspected index arithmetic, this recurrence is not a sequence of separate
multiply/subtract operations. Retain the instruction bytes under the same
CSPICE hash in `m3_spk_selector_observation.json`.

For rounded normalized time `s`, set `a=fl(s+s)` and two trailing recurrence
values to zero. For coefficients from degree n down to 1, compute
`b_k=fl(RN(a*b_(k+1)-b_(k+2))+c_k)`; finish with
`p=fl(RN(s*b_1-b_2)+c_0)`. Each inner RN denotes one fused rounding.
The test-only replay uses exact fractions before that single conversion to
binary64. A degree-2 control with coefficients `(0,0.1,0.3)` and `s=0.3`
distinguishes fused result `-0x1.ba5e353f7ced9p-3 km` from the one-ULP-different
separate-operation result; both native position routines match the fused replay.
An independent quadratic expression checks the control within `1e-12 m`.

Evaluate all 550 inventoried records directly, bypassing record selection,
at six epochs each: both nominal endpoints, midpoint, midpoint plus radius/3,
and 16 epoch ULPs beyond either endpoint. All 3,300 evaluations (9,900 position
components) match the replay bit-for-bit. Independent exact Chebyshev-basis
recurrences at the exact rational normalized epochs give sampled L1 position
errors below the unchanged `0.001 m` gate; the largest is
`0.00016239212647380994 m` for target 6 (Saturn barycenter). The tiny extension
is an explicit test domain, not authorization for arbitrary extrapolation.

These are sampled supplied-record comparisons in native km, with errors
converted exactly to SI for reporting. They do not bound every epoch, qualify
the derivative/stored-velocity arithmetic, include floating-point SI conversion
or center-chain accumulation, or establish segment selection and spacecraft
safety. Derive a uniform error enclosure using this fused graph before using
it in interval screening; never substitute the sampled maximum for that bound.
Production settings, dependencies and tolerances remain unchanged.

### Pinned native record-selector arithmetic (2026-09-10)

Read-only disassembly of the installed Darwin/arm64 `libcspice.dylib`
shows identical contiguous selection instructions in `_spkr02_` and
`_spkr03_`: binary64 subtraction, binary64 division, signed integer
truncation and a one-based `min(trunc(q_hat)+1,N)` clamp. Truncation equals
floor for the nonnegative in-segment quotient. The subsequent `MADD` is
integer DAF addressing, not a floating-point fused operation. Retain the
library hash, text/file mapping, bytes, interpretation and reproduction
command in `tests/data/m3_spk_selector_observation.json`; a regression test
rejects changed builds on the inspected platform instead of inheriting this
observation silently. Other platforms are explicitly unqualified.

The existing 12-segment inventory checks signed 32-bit conversion, increment
and address ranges, including the conditional quotient-roundoff margin.
At both endpoints of every segment, 24 additional guarded raw-reader queries
match the first/last DAF records byte-for-byte. In particular, the exact final
epoch gives quotient N and exercises the clamp, not an out-of-range record.
The previous 1,628 all-link and 7,293 switch readbacks remain unchanged.

This qualifies the static arithmetic graph used in the conditional
bound, not a uniform runtime certificate. Continuous floating-point control,
live dispatch, segment selection, native polynomial evaluation and center-chain
summation remain separate obligations. No production settings, scientific
tolerances or source resources change; task 3.9 remains open.

### Conditional whole-segment index-roundoff margin (2026-09-10)

For the declared replay `q_hat = fl(fl(t-INIT)/INTLEN)`, assume two correctly
rounded binary64 round-to-nearest operations, exact stored inputs and no
overflow or nonzero subnormal intermediate/result. With `u=2^-53`, write
`q_hat=q(1+d1)(1+d2)`, `|d1|,|d2|<=u`, hence
`|q_hat-q|*INTLEN <= (2u+u^2)*|t-INIT|`. This is the standard relative-error
model discussed by [Goldberg](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html).
Use exact fractions and the whole segment span as the maximum offset,
not a sampled maximum, then round the reported seconds upward.

For each of the 12 relevant segments, the next representable epoch after
INIT bounds the smallest positive offset. Explicit rational lower/upper
checks establish normal-range subtraction and division throughout the
segment for binary64 epochs; the zero offset is exact and checked separately.
The resulting margins are `1.4365468814503404e-6 s` for the type-2 segments,
`1.3587517670998752e-6 s` for Mars, `1.1911860937630083e-6 s` for Jupiter,
and `7.635492238478038e-9 s` for each relevant Saturn segment. Each is
less than one record duration and less than the existing 16-ULP strip
half-width on the candidate interval.

Since flooring can change only across an integer boundary, this conditional
margin confines a replay index discrepancy to a neighboring record within
that time margin of a join. Exact rational comparisons at all 1,628 native
readback probes verify the quotient-error inequality, index difference at
most one, and coverage of all 466 observed early choices. This does not
prove the native binary uses exactly that arithmetic graph or rounding
environment at every epoch; native evaluation error, segment priority and
spacecraft safety remain separate. No production limits or tolerances change.

### Native readback for every required source link (2026-09-10)

Reuse one guarded test-only reader for the installed `spkr02_` and `spkr03_`
entry points. Its buffer size comes from the validated segment directory;
the length word, trailing guard and native error state are checked before
returning copied record words. The previous 7,293 type-3 switch readbacks
continue to use this same reader.

Add 1,628 readbacks across all 11 required source links: 550 midpoints and
both one-ULP interior sides of 539 joins. All raw records match the binary64
index replay and direct DAF record bytes exactly. Midpoints retain their
own record; 466 left-side probes already select the following record:
245 type-2 joins plus the known 221 Mars/Jupiter type-3 joins. No such early
selection occurs at the 73 sampled Saturn joins. These are side-probe
observations, not measured switch brackets for all type-2 segments.

This explains why passing the earlier 0.001 m position comparison did not
identify record choice for type 2: those source jumps are small enough to
remain within that gate. The readback reports counts for every target and
preserves source-center/J2000 and TDB conventions, unchanged kernel pool,
the shared deadline and zero spacecraft arcs. It neither changes production
behavior nor proves uniform native selection or evaluation accuracy.

### Native selected-record readback (2026-09-10)

A separate Darwin/arm64 variant of the existing qualification reads the
selected type-3 record through the installed CSPICE `spkr03_` entry point.
The [NAIF record layout](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/spkr03.html)
starts with the record length, followed by midpoint, radius and six coefficient
series. Before calling, verify the type and both adjacent 122-word records
against the previously checked directories. Allocate the length word plus
122 words and an extra guard, verify the length/guard and native error state,
then compare all 122 data words byte-for-byte with the replay-selected record.

All 7,293 queries across the 221 Mars/Jupiter joins agree exactly, including
the four early-selection epochs. Thus selection is now directly observed at
those samples, not only inferred from nearby position values. The original
portable test variant remains intact; only the additional raw-ABI variant
uses the existing platform gate. Both retain the kernel-pool equality check,
shared 300-second budget and zero spacecraft propagations.

This diagnostic binding stays in tests and does not change the production
SPICE wrapper. It is still sampled selection evidence, not a uniform native
arithmetic proof, evaluation-error enclosure or completion of task 3.9.

### Exact adjacent-branch ambiguity envelope (2026-09-10)

For a shared record boundary `b`, let `J` be the exact L1 endpoint jump
and `L_left`, `L_right` the already qualified position-rate majorants on
records extended by an explicit `h` seconds. The triangle inequality gives
`||p_left(t)-p_right(t)||_1 <= J + (L_left+L_right)*|t-b|`
for `|t-b|<=h`. Consequently `J+(L_left+L_right)*h` uniformly encloses the
difference between these two exact polynomial branches in that strip,
regardless of which branch is chosen. L1 also bounds the Euclidean norm.

The existing 221 Mars/Jupiter join controls use `h=16` epoch ULP and exact
Chebyshev recurrences at offsets -16/-5/-4/-1/0/1/16. All 1,547 same-epoch
branch differences satisfy the bound; dropping `J` fails every control.
Each reported SI bound is rounded upward after exact fraction composition.
The reported values range from `0.03839044549637998 m` to
`14.382176150648052 m`; these are per-center branch-ambiguity bounds, not
physical uncertainty, native roundoff or propagated spacecraft errors.

This mathematical strip bound does not prove that native SPICE selects one
of these two records throughout the strip or that it cannot switch elsewhere.
The previous 7,293 sampled native comparisons remain separate evidence.
Native evaluation rounding, center-chain composition and spacecraft error
are still open; no production behavior, tolerance or work limit changes.

### Exact rate bound on an explicitly extended record (2026-09-10)

The private position-rate helper accepts keyword-only `extension_s >= 0`,
defaulting to zero (the unchanged closed-record contract). With exact
`q = 1 + extension_s/radius_s`, use
`L = 1000/radius_s * sum_j sum_k |c_jk| k U_(k-1)(q)`.
For `|x| <= 1`, the existing derivative bound is `k^2`. For `1 <= |x| <= q`,
write `|x|=cosh(u)`: the finite representation of `U_n` pairs terms into
nonnegative increasing `cosh` terms, so `|U_n(x)| <= U_n(q)` and
`U_n(q) >= n+1`. Thus this same majorant covers the entire extended domain.
This derives from the [DLMF derivative identity](https://dlmf.nist.gov/18.9#E21)
and [finite representation](https://dlmf.nist.gov/18.5#E2).

Evaluate `U_-1=0, U_0=1, U_n=2q U_(n-1)-U_(n-2)` with exact fractions and
round only the final positive SI bound upward. In particular, do not round
`1 + extension_s/radius_s` to binary64 before the recurrence. At zero
extension, `k U_(k-1)(1)=k^2` reproduces the old numerical values.

Independent finite-power coefficient oracles cover degrees 0/1/2/3/19;
mixed-axis rational controls, sub-ULP normalization, invalid/overflow and
existing deadline guards cover arithmetic. All 550 loaded position records
also receive explicit 16-epoch-ULP extensions, with derivative probes kept
inside the exact enlarged interval and rates no smaller than the old bounds.
This is exact-polynomial extrapolation qualification only: it neither
authorizes uncovered ephemeris queries nor bounds native evaluation rounding,
record-selection width, jumps, center composition or spacecraft error.
Production ephemeris settings and all scientific tolerances/limits stay fixed;
task 3.9 remains open.

### Sampled native record-switch bracket (2026-09-09)

For each of the 221 Mars/Jupiter joins in the preceding counterexample,
probe every binary64 epoch offset from -16 through +16 ULP. Across all
7,293 queries, native positions agree within `0.001 m` with the polynomial
selected by the binary64 replay `floor((epoch - INIT) / INTLEN)`; the other
adjacent polynomial differs by more than `0.001 m`. The maximum replay
position discrepancy observed is `9.203439287865708e-11 m`.

All brackets switch to the right record at offset -4 ULP, with offset -5
still selecting the left record: the first observed right-record epoch is
`2^-21 s` (`0.476837158203125 microseconds`) before the exact boundary.
At offsets -4 through -1, exact rational epoch-minus-INIT is less than its
boundary value, while binary64 subtraction equals that boundary value.
This establishes an early-switch mechanism in the arithmetic replay and
agrees with native output at every tested epoch. It is not an inspection or
proof of the compiled native arithmetic graph, nor a uniform bound for
other segments, type-2 records or epochs outside these small brackets.
Only position is qualified here; the type-3 velocity series remains separate.

No custom SPICE reader, extra native binding or production workaround is
introduced. The sampled switch brackets narrow the open native-selection
problem; they do not remove the source jumps or complete task 3.9.

### All-chain joins and native near-boundary counterexample (2026-09-09)

The all-chain record qualification now pairs both sides of all 539 interior
joins by target ID and exact TDB epoch, independently of segment file order.
Every exact position-polynomial endpoint has a nonzero L1 jump. Using exact
Chebyshev recurrence one binary64 epoch ULP (`2^-23 s`) inside each record,
all displacements satisfy `L_left*h + J_L1 + L_right*h`. Omitting the jump
fails at 298 joins. The largest L1 source-position jump is
`14.382072321860564 m` for Jupiter center relative to its barycenter; this
is a representation discontinuity, not physical motion or ephemeris uncertainty.

The independent segment-native SPICE comparison adds 1,078 one-ULP-side
position probes with the unchanged `0.001 m` parity threshold. It fails at
221 probes: just before all 163 Mars-center joins and all 58 Jupiter-center
joins. Maximum Euclidean discrepancy is `8.74270150900805 m`, for Jupiter
at the left-side probe of `982745568 TDB seconds since J2000`. These native
values instead agree within `0.001 m` with the right-side exact position
probe. This is consistent with a near-boundary record-selection effect;
its native arithmetic cause and transition width are not yet qualified.
The test retains all failing epochs, sides and errors in its JSON diagnostic
and explicitly requires this counterexample, rather than loosening the gate.

Thus exact mathematical record boundaries cannot yet be assumed to partition
native SPICE evaluation at arbitrary binary64 epochs. Midpoint parity remains
valid, but does not establish this stronger claim. The exact-polynomial motion
inequality is qualified separately from the failed native near-join parity;
neither completes task 3.9 or accepts a safe spacecraft trajectory. Production
forces, direct-SPICE strategy, kernels, tolerances and work limits are unchanged.

### All-chain SPK record-rate qualification (2026-09-09)

Extend the existing loaded-file inventory with the same exact position-rate
helper for all 11 target/center links needed by the eight production bodies.
Read type-2 and type-3 record directories, verify their exact midpoint/radius
headers and storage lengths, and select candidate-overlapping records with
rational index arithmetic, including both touching records at exact boundaries.
The pinned candidate has 550 records: target IDs 1/2/4/5/6/10/301/399/499/599/699
contribute 37/19/10/10/10/19/74/74/164/59/74 respectively.

Five NumPy derivative probes per record satisfy the exact-polynomial rate
majorant. At all 550 record midpoints, NumPy positions match segment-native
SPICE positions within `0.001 m` (observed maximum `0 m`). For the 253 type-2
records only, derivative velocities match within `0.000001 m/s` (observed
maximum `1.4210854715202004e-11 m/s`). Type-3 stored velocities are separate
series and are deliberately not used as a position-derivative oracle.
The diagnostic emits per-target counts and minimum/maximum rate bounds in
m/s relative to each listed center, with J2000 orientation and TDB epochs.

This extends the verified record inputs, not the bound's scope: combining
center chains, accounting for every record/segment jump, native evaluation
roundoff and spacecraft integration error remain open. The kernel pool,
production model, tolerances and shared 300-second budget are unchanged;
no spacecraft propagation or safety acceptance is performed.

### Exact SPK position-rate and jump controls (2026-09-09)

For one record write each position component as `p_j(t) = sum c_jk T_k(x)`,
where raw coefficients are km and `x=(t-midpoint)/radius_s` lies in `[-1,1]`.
Since `T'_k=k U_(k-1)` and `|U_(k-1)|<=k` there, the position derivative's
Euclidean norm is bounded by the L1 majorant
`L = 1000/radius_s * sum_j sum_k |c_jk| k^2` in m/s. The latter inequality
follows from `U_(k-1)(cos(theta))=sin(k theta)/sin(theta)` and the finite sum
of k unit complex terms, with endpoint limits. Evaluate this majorant using
exact rational arithmetic on the stored binary64 coefficients, then round
the final positive bound upward; keep an exactly zero constant-polynomial bound.
References: [DLMF derivative identity](https://dlmf.nist.gov/18.9#E21) and
[Chebyshev representation](https://dlmf.nist.gov/18.5#E2).

The 74 overlapping Saturn-center-relative-to-barycenter/J2000 records give
record-wide bounds from `3.0435980202672015` to `4.200998456248276 m/s`.
These are derivative bounds for exact position polynomials, not the separately
stored type-3 velocity series or Saturn's heliocentric orbital speed.
Five NumPy derivative probes per record verify the implementation separately
from the uniform mathematical inequality. Single-mode degree 0/1/2/19 controls,
mixed-sign/axis rational controls, subnormal/overflow and invalid-input/deadline
controls qualify the arithmetic and guards.

Across a record join, add the exact L1 endpoint jump `J`: the displacement
between interior points at offsets `h_left,h_right` is at most
`L_left*h_left + J + L_right*h_right`. Exact Chebyshev recurrences at offsets
`2^-23 s` verify this bound at all 73 joins and show that omitting `J` fails
at every one. This does not assume source continuity or equate velocity with
the derivative of position. The bound still excludes native evaluation error,
other center-chain contributions and spacecraft integration error. It is a
private qualification building block, not a production safety acceptance rule;
task 3.9 and all current tolerances/limits remain unchanged.

### Accepted production revision (2026-09-09)

The user approved direct SPICE after the table counterexample, lookup-cost,
fixed-state force and chain-coverage investigations. This section supersedes
dated references below to unchanged production tables; those describe the
historical v1 experiments, not the current production choice.

Build default SSB/J2000 bodies and explicitly assign Tudat `direct_spice` to
each body. Before body-system creation, inspect unique loaded SPK files and
merge segment intervals for each of the eleven required target/center IDs.
Require full candidate-interval inclusion for every link and reject overlapping
segments with unsupported center, frame or type. Do not use the interpolation
safe-interval API as evidence for direct SPICE. Read back runtime frames and
finite endpoint states. Every inspection remains under the supplied shared
deadline; no kernel reload, fallback or caching of coverage is introduced.

The revised full model identifier ends in `cannonball-srp-schwarzschild-direct-spice-v2`.
Existing v1 table controls remain historical regression evidence. Removing our
table eliminates the measured additional interpolation difference (up to
0.182333 m / 2.138636e-5 m/s at sampled Saturn joins); it does not remove source
representation jumps or establish a spacecraft error bound. Preserve every
force, dependency, kernel, tolerance and native-call limit. M3/3.9 remains open.

### Loaded-SPK chain interval coverage (2026-09-08)

Use the already-pinned SpiceyPy bindings to inspect all six Tudat-loaded SPK
files without loading/unloading kernels. Deduplicate resolved file paths for
scanning only: the full suite repeatedly initializes kernels and exposes 120
registrations of these six files. Preserve and compare the complete raw kernel
registration list before/after, and report its count separately. Exhaust the
unique files' 2,028 DAF segment
descriptors before invoking coverage routines, which may start other DAF
searches. For the candidate interval, verify every overlapping segment for the
11 required target IDs has the expected center, J2000 frame and type 2 or 3.
There is one overlapping segment per target except Saturn 699, which has two.
The existing effective Mercury/Venus IDs 1/2 remain unchanged.

Merge each target's file coverage with SPICE `spkcov`, then intersect the 11
windows with the candidate interval using `wnintd`. Verify `wnincd` accepts
the whole interval `[978995455.2304223, 1004169273.4122404]` TDB seconds since
J2000 for every target and the intersection retains both exact endpoints.
Negative controls reject an absent target and a two-second interior gap even
when both requested endpoints are covered. All checks passed; kernel records
and pending-error state remain unchanged, with zero native spacecraft arcs
under one shared 300-second budget.

This establishes nominal segment coverage for the required fixed-center chains,
not polynomial-record integrity, source continuity, uniform approximation error,
kernel physical accuracy or trajectory safety. It does not switch production
ephemerides or complete task 3.9. The known Saturn representation jumps remain.
API semantics: [NAIF SPK coverage](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkcov_c.html),
[window intersection](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/wnintd_c.html)
and [interval inclusion](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/wnincd_c.html).

### Direct ephemerides in fixed-state force controls (2026-09-08)

Extend the existing independent force-component-sum test with test-only direct
ephemerides for all eight bodies. Replace native body ephemerides after the
normal physical resource validation and before constructing acceleration models;
do not alter the production factory or its table-specific coverage checks.
Read back SSB/J2000 and verify endpoint state parity within `0.001 m` and
`0.000001 m/s` against named geometric SPICE queries.

Run the original gravity-only, combined coast, departure-thrust and arrival-thrust
cases with both ephemeris paths. Each case evaluates near-Moon, cruise and
near-Mars fixed states at the existing one-day control's departure epoch.
All eight cases passed (24 initial-state comparisons, 12 with direct ephemerides)
using the unchanged `max(1e-15 m/s^2, 1e-12 * sum of component norms)` tolerance,
the existing analytic thrust direction and fixed-state acceleration bounds.
Combined cases retain deliberately poisoned PPN reset/readback controls.

Use one 300-second budget per case for environment construction, all three
short native runs and bound evaluation; route runs through the existing native
runner and verify counters after each run. Do not create fresh timers for each
fixed state. These 0.01-second controls only inspect initial forces, not nominal
mission propagation, interval enclosure, closure, mass evolution or full-force
subdivision performance. Both assemblies share the same body ephemerides, so
component agreement is not an independent ephemeris-accuracy certificate.
Task 3.9 and all production limits and scientific allocations remain unchanged.

### Direct versus tabulated lookup cost (2026-09-08)

The bounded lookup experiment uses the existing 38 candidate epochs, eight
bodies, six alternating-order batches per path and 3,800 queries per batch.
Validate finite states, explicit SI/SSB/J2000 frames and the existing sampled
parity tolerances before timing. Keep table construction separate from direct
construction and query time; kernel loading is outside reported setup timings.
One shared 300-second budget covers the experiment, with zero propagated arcs.

On macOS 26.6.2 arm64, Python 3.12.14 and the pinned scientific environment,
the first focused run measured median table queries of 0.412–0.550 microseconds
and direct queries of 1.223–1.630 microseconds (about 2.9–3.6 times the cost).
Per-body table construction took 0.088–0.111 seconds; direct construction took
4.5–8.6 microseconds, with 0.060 seconds for shared table settings creation.
The test prints raw batch timings and per-body medians; wall times are host/load
dependent, not deterministic scientific baselines or test acceptance thresholds.

This measures warm Python-boundary calls with repeated sampled epochs, not the
native integrator's query distribution, full-force runtime, uniform accuracy
or trajectory safety. It supports continued direct-path investigation without
changing production tables, resource limits or scientific tolerances. Task 3.9
remains open, including its existing table-accuracy counterexamples.

### Eight-body direct-SPICE path parity (2026-09-08)

Extend the existing sampled source-chain qualification with a separate built-in
direct native ephemeris for each of the eight bodies. Explicitly set SSB/J2000
and the body name, read back the native frame, and compare the six SI components
to numeric-target CSPICE SSB states at all 38 qualification epochs. The existing
chain checks retain effective Mercury/Venus targets 1/2, Moon/Earth chaining,
and planet-center offsets for Mars/Jupiter/Saturn; no new name substitutions
are introduced. All 304 direct-native comparisons pass `0.001 m` and
`0.000001 m/s`, with measured maxima zero for every body.

This extends API-path parity beyond the Saturn join experiment, not physical
truth validation, whole-interval coverage or full-force performance. Both paths
use the same authoritative kernels. Production tables and their known failures
remain unchanged, and task 3.9 remains open.

### Direct-SPICE native error controls (2026-09-08)

The experimental direct path rejects `ARIADNA_UNKNOWN_BODY` with native
`SPICE(IDCODENOTFOUND)` and Saturn requests at `-1e12` / `1e12` TDB seconds
since J2000 with `SPICE(SPKINSUFFDATA)`. The pinned Tudat exceptions derive
from RuntimeError and include body context. No state is returned on these
paths. After each failure, a valid Saturn request at `986817600 TDB s` matches
its pre-failure state in every binary64 component bit, the existing SpiceyPy
pool inspection reports no pending error, and the loaded-kernel count is
unchanged. The test performs no manual reset, kernel reload or unload.

These controls qualify three native failure/recovery cases, not every coverage
edge or missing-resource configuration. Project-level error translation,
complete interval coverage validation and full-force performance remain
unimplemented for the experimental alternative. Production behavior and all
scientific tolerances remain unchanged; task 3.9 is not closed.

### Test-only direct-SPICE alternative (2026-09-08)

Build TudatPy's existing `ephemeris.direct_spice("SSB", "J2000", "Saturn")`
as a separate experimental native ephemeris. Keep the production table and
its known failures unchanged. At all 219 mapped record-boundary probes,
compare the direct native model with named geometric TudatPy/SPICE requests;
require frame readback and agreement within `0.001 m` / `0.000001 m/s`.
Observed maximum differences are `0 m` and `0 m/s` in the pinned environment.
No custom ephemeris evaluator, added dependency, kernel reload or production
configuration change is involved.

This demonstrates a built-in alternative that avoids the additional table
error at these probes. Both sides use SPICE, so it is API-path parity, not an
independent physical truth oracle or a uniform accuracy certificate. Direct
queries retain the source-record discontinuities. Full-force performance,
resource/coverage failure behavior and integration through record boundaries
remain unqualified for this alternative. Do not promote it to production or
clear task 3.9 on this evidence alone; any accepted strategy revision must
preserve the shared deadline, scientific tolerances and existing resource gates.

### Exact Saturn record-endpoint differences (2026-09-08)

Read the full 122-word records rather than only headers, rejecting nonfinite
coefficients. For each of the 73 candidate-interior boundaries, evaluate both
neighboring degree-19 records at that same epoch with exact Fraction sums.
The [Chebyshev identity](https://dlmf.nist.gov/18.5#E1) gives `T_k(1)=1` and
`T_k(-1)=(-1)^k`, so endpoint evaluation needs no floating recurrence. Multiply
by exactly 1000 to convert native km/km/s coefficients to SI. Independently
compare all 146 endpoint states to NumPy's Chebyshev evaluator within
`1e-8 m` and `1e-12 m/s`; these are oracle checks, not relaxed physical limits.

Exact squared Euclidean differences exceed `(2*0.025 m)^2` at 70 boundaries
and `(2*2.5e-6 m/s)^2` at 68. All 73 have nonzero position and velocity
differences. The largest rounded reported norms are `0.21757621126693544 m`
and `2.5019583702437535e-5 m/s`, both at `979596288 TDB seconds since J2000`.
Threshold decisions use rational squares, not rounded reported square roots.
These are target-699/center-6, J2000 representation discontinuities, not
physical jumps or errors against a true Saturn orbit.

By the triangle inequality, where the separation exceeds twice an allocation,
one common endpoint value cannot approximate both record limits within that
allocation. This supports investigating a boundary-aware treatment, not an
unreviewed kernel change or increased allowance. It does not by itself prove
the native evaluator's interval error, resolve all-file precedence, certify the
separate barycenter contribution, or fix the production interpolation failure.

### All mapped Saturn record-join probes (2026-09-08)

Compare the unchanged candidate-wide 300 s table to named direct TudatPy/SPICE
in SSB/J2000 at each of the 73 directory-derived interior boundaries and their
immediately adjacent binary64 epochs: 219 comparisons in the same qualification
budget, with no spacecraft propagation. Report position/velocity Euclidean
error maxima for each boundary in explicit SI units, not differences between
two physically distinct epochs and not purported polynomial jump bounds.

All 73 boundaries exceed the `0.025 m` position allocation; 71 exceed
`2.5e-6 m/s` in velocity. Both largest errors occur near boundary
`997133760 TDB seconds since J2000`: `0.1823327710720816 m` and
`2.13863534474615e-5 m/s`. The two velocity-passing boundaries are
`986129856` and `995414400`; their position checks still fail. Retain the full
per-boundary error report and reproduce the 73/71 failure counts as a
regression, not a successful scientific acceptance check.

The issue is therefore not confined to the previously identified segment
junction. A remedy confined to that single junction would miss observed
failures at the other 72 record joins. These probes still do not bound errors
away from joins, audit other bodies or establish coefficient discontinuities
at the same epoch. Production sources, table spacing, tolerances and work
limits remain unchanged; task 3.9 remains open.

### Saturn polynomial-record directory (2026-09-08)

Extend the selected-file inventory with read-only DAF data reads for the two
candidate-overlapping type-3 segments. Following the documented
[SPK type-2/type-3 layout](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html),
read each four-word trailer `(INIT,INTLEN,RSIZE,N)` and all record `(MID,RADIUS)`
headers. Both trailers have duration `343872 s`, record size 122 words and
100 records, giving six degree-19 coefficient sets per record. All 200 headers
exactly match their integer-valued directory midpoints and `171936 s` radii;
record storage lengths and full segment coverage agree exactly too.

There are 74 records intersecting the candidate and 73 distinct interior
boundaries, from `979252416` through `1004011200 TDB seconds since J2000`,
including the known `986817600` segment junction. The test reports every boundary
in sorted order. These describe only the target-699/center-6 contribution:
the Saturn-system barycenter's type-2 records and other loaded files remain
outside this inventory. Coefficients, state jumps at the other 72 boundaries
and uniform error bounds have not been verified. No production settings or
tolerances change; the original interpolation counterexample remains open.

### Selected Saturn file segment inventory (2026-09-08)

Select Saturn's SPK file at candidate departure through the existing loaded
pool, then exhaust its segment directory using the documented
[DAF forward search](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/dafbfs_c.html).
The read-only qualification checks every native error flag and the shared
deadline, allocates DAF's maximum 125-double summary buffer, and does not
close/reload Tudat-owned files. It finds 1,223 total segments, including 171
for target 699, all relative to center 6 in J2000 with SPK type 3.

Exactly two Saturn segments intersect the candidate interval. In file order:
`[986817600,1021204800]` at DAF words `25956465..25968668`, then
`[952430400,986817600]` at words `25969025..25981228` (epochs in TDB seconds
since J2000). Their union covers the candidate; their only common epoch is
the known junction. This is a complete segment inventory for this selected
file, not just the earlier 38 epoch samples. It is not a complete loaded-file
priority audit and does not enumerate Chebyshev records inside segments.
No further segment junction in this file was found on the candidate interval;
the known interpolation failure remains unchanged and task 3.9 stays open.

### Junction table-density control (2026-09-08)

Parameterize the existing Saturn junction counterexample with candidate-wide
300 s, 150 s and 75 s default Tudat tables. Keep the 300 s production path;
the other spacings are test-only, as in the earlier 150 s qualification.
Require unchanged candidate coverage and SSB/J2000 frames for every table.
At the same three adjacent binary64 epochs, the maximum errors are:

| Table step (s) | Position error (m) | Velocity error (m/s) |
|---|---|---|
| 300 | 0.1394431198762437 | 1.6599647370186684e-5 |
| 150 | 0.10801370752951119 | 1.285373338685058e-5 |
| 75 | 0.12190976075097239 | 1.4591343096708111e-5 |

All three exceed the existing `0.025 m` / `2.5e-6 m/s` limits. The maximum
does not decrease monotonically with these grid refinements. This rules out
these two simple densifications as a remedy for the observed junction, not
every possible spacing or a boundary-aware method. Each case retains the same
300-second qualification budget and zero spacecraft propagations. No production
spacing, kernel, force, tolerance or native-call limit changes. The regression
passes by reproducing failure, and task 3.9 remains open.

### Local junction query-order control (2026-09-08)

The Saturn junction counterexample is not explained by the six permutations
of the immediately-before/exact/immediately-after queries. In the existing
loaded pool, repeat each request twice: all 36 named TudatPy states match the
corresponding first-observed binary64 component bit patterns. Eighteen raw
CSPICE SSB requests, converted from km/km/s to SI, match those bits too.
All six exact-junction descriptor checks select coverage
`[952430400,986817600]` TDB seconds since J2000, the left segment.

`test_saturn_junction_query_order_is_repeatable` checks this local observation
without kernel reloads, cache resets, native changes or extra dependencies.
It is neither a universal SPICE tie-breaking rule nor a guarantee across
processes, threads, other epochs or kernel sets. The 14 cm interpolation
counterexample remains unresolved; complete source-boundary investigation and
a reviewed remedy are still required before any uniform qualification.

### Saturn junction counterexample (2026-09-08)

The sampled inventory led to a failing expanded interpolation control at
`986817600 TDB seconds since J2000`. Read the selected Saturn descriptors at
the immediately adjacent binary64 epochs and evaluate both segments at the
same shared epoch with [SPKPVN](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkpvn_c.html).
Both return target 699 relative to center 6 in J2000; their differences are
`0.1628216982412309 m` and `1.940988845873698e-5 m/s`. These are discrepancies
between native kernel representations, not evidence of a physical Saturn jump.
Selection at the exact shared epoch after a left-side request returned the left
descriptor; do not assume an unverified tie-breaking rule.

With the unchanged candidate-wide 300 s table, SSB/J2000 interpolation errors
at `[986817599.9999999,986817600,986817600.0000001]` are respectively
`[0.1394431198762437,0.13939384782048214,0.027673705998418514] m` and
`[1.659964579534151e-5,1.6599647370186684e-5,3.367634353876283e-6] m/s`.
The existing `0.025 m` / `2.5e-6 m/s` allocation fails on these new probes.
The original 38-epoch task 2.7 result remains historical sampled evidence only;
it cannot qualify this junction or a uniform approximation. A single common
position cannot be within `0.025 m` of both segment values: their separation
exceeds twice that allowance by the triangle inequality.

`test_saturn_spk_segment_junction` is a regression of this counterexample: it
must reproduce allocation exceedance, not silently call it a passing scientific
gate. Production kernels, interpolation, tolerances and limits stay unchanged.
Task 3.9 and targeting remain gated. Before a remedy, investigate complete
segment/record boundaries and exact-junction query-order behavior; any resource
or approximation-policy change requires explicit scientific review. No uniform
coefficient or trajectory-error certificate follows from the native samples.

### Sampled SPK source-chain inventory (2026-09-08)

The read-only `tests/test_trajectory_spk.py` uses the installed Darwin/arm64
CSPICE ABI through standard-library ctypes, with TudatPy remaining the kernel
loader. No kernels, error policy or production states are changed. At the 38
qualification epochs it follows each selected segment's center to SSB and
compares the numeric-target CSPICE state (km and km/s converted once to SI)
with the named TudatPy state within `0.001 m` and `0.000001 m/s`.

Observed chains (target -> center, SPK type): Sun `10 -> 0, 2`, Mercury
`1 -> 0, 2`, Venus `2 -> 0, 2`, Earth `399 -> 0, 2`, Moon `301 -> 399, 2`
then Earth, Mars `499 -> 4, 3` then `4 -> 0, 2`, Jupiter `599 -> 5, 3` then
`5 -> 0, 2`, and Saturn `699 -> 6, 3` then `6 -> 0, 2`. All frames are
J2000 (ID 1). Mercury/Venus named-state parity is observed for targets 1/2,
not inferred from the separate name-to-ID function, which returns 199/299.
This does not authorize substituting barycenters for other planet centers.

Saturn's sampled type-3 descriptors change at `986817600 TDB seconds since
J2000`; observed coverage is `[952430400,986817600]` and
`[986817600,1021204800]`. A future uniform bound must account for segment and
polynomial-record boundaries and every link in the chain. Descriptor coverage
at samples alone does not prove highest-priority selection throughout the
interval. No coefficient, derivative, native-roundoff or integration bound
is established by this inventory; task 3.9 remains open.

NAIF documents [highest-priority segment selection](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spksfs_c.html),
[descriptor unpacking](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkuds_c.html),
[SSB state units](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkssb_c.html)
and [SPK types 2/3](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html):
type 2 stores position Chebyshev polynomials, while type 3 stores separate
position and velocity polynomials. The chains above are local observations,
not claims about every kernel set or Tudat build.

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

For the existing 304 real six-node cell requests, additionally check every stored
SI component is zero or has magnitude in `[2^-100, 2^100]`. These deliberately
loose bounds are test-only arithmetic premises, not new scientific input limits.
The preceding weight enclosure fits `(2^-200, 2^40)`. Therefore each nonzero
exact state product lies in `(2^-300, 2^140)`, and its correctly rounded value
lies in `(2^-301, 2^141)`. Zero inputs yield exact zero. All such binary64 terms
are multiples of `q=2^-353` (the spacing of the lowest permitted binade).
By induction, every exact partial sum is a multiple of q. Below `2^-301`, that
multiple has at most 53 significant bits and is exactly representable; at larger
magnitudes binary64 rounding still preserves the q lattice. Thus a nonzero
cancellation result is at least q, well above the smallest normal value; exact
zero remains allowed. Six additions bounded by `U_next=(U+2^141)*(1+u)` from zero
stay below `2^145`, so neither exact nor rounded partial sums overflow. Exact
Fraction controls check the enclosures and all 720 permutations of a six-term
zero/tiny/large cancellation fixture check lattice preservation and rounding.
Out-of-range and nonfinite node controls fail qualification. This extends range
premises over the whole middle cells of those supplied node sets, not every
mission cell or all compiled paths; native-node provenance, arbitrary rational
oracle conversion, SPICE approximation and spacecraft integration remain open.
The lattice argument above is a project derivation from binary significand
representation and correctly rounded operations, as described in Goldberg's
Floating-point Formats and Exactly Rounded Operations sections:
https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html . It does not assert
that the currently installed native compiler uses those operations on all paths.

Extend the source-node range inventory to the complete padded candidate grid:
retain every timestamp from the already-verified repeated-addition loop and query
all eight bodies directly through the pinned TudatPy/SPICE interface in SI,
SSB/J2000, without aberration corrections. Apply the same zero-or-`[2^-100,2^100]`
gate to every component, not a sample. Report per-body counts, component minima
excluding zeros, maxima, zero counts, and a SHA-256 of row-major big-endian
binary64 states in timestamp order, with software/kernel provenance and measured
inventory-only time. Check the existing shared budget every 512 requests and
after each body; these are ephemeris queries, not spacecraft propagations, and
native-arc/control/evaluation counters remain zero. This establishes the range
premise for all reconstructed source nodes, not readback of native table storage.
Together with the grid/weight/lattice derivations it covers the arithmetic range
premises for their interior six-node polynomials. Compiler semantics, native-node
identity, boundary splines, SPICE approximation and spacecraft error remain open;
no uniform native safety claim or production budget revision follows.

Qualify node identity through the public native ephemeris interface, without
claiming direct storage introspection: derive the union of six-node stencils for
the closed candidate interval using exact rational floor indices, from the first
lower knot minus two through the last lower knot plus three. Construct each
production ephemeris, require its safe interpolation interval to contain this
entire knot union, and query every required knot. Compare all six binary64 bit
patterns against the corresponding reconstructed direct-SPICE state, including
signed zeros. Report exact-match counts and hashes for this explicitly labelled
subset, with construction/query/check time separate from the full source-node
inventory. Check the original shared deadline before and after construction,
every 512 knot queries, and after each body; propagation counters remain zero.
This is exhaustive knot-value agreement for the candidate's required nodes in
the pinned runtime. It does not establish compiled between-knot arithmetic,
boundary-spline behavior, SPICE approximation accuracy or spacecraft safety.

Summarize the arithmetic model over the entire candidate interval, separately
from the former sampled native/oracle comparisons. For each component let M be
the largest absolute value across the complete required-node union, which
contains every candidate stencil. The established bound is then
`E_j=gamma_15*(89/64)*M_j` against the exact local polynomial for any represented
query in the candidate interval, conditional on the inspected correctly rounded
binary64 graph. Its range premises follow from the preceding complete-grid
weight and state/lattice checks. At exact knots the error is zero. Compute E in
Fraction arithmetic, round each reported component upward, and separately round
the exact sums of the three position and velocity bounds upward. These L1 sums
also bound Euclidean error; check every serialized float remains finite and is
at least its exact rational bound. This summary deliberately excludes the extra
rounding of a rational oracle (the older sampled comparison uses gamma_16).
Do not interpret it as verified compiler semantics, SPICE interpolation error,
spacecraft integration error, or permission to certify a safe trajectory.

Record bounded static evidence for the installed Darwin/arm64 kernel in
`tests/data/m3_native_arithmetic_observation.json`: module SHA-256/size, symbol,
text-to-file offset mapping, disassembler version, reproduction command and
selected instruction bytes. The double-time/double-six-state/double-scalar
Lagrange symbol's interior loop contains scalar FSUB/FMUL/FDIV and three pairs
of vector binary64 FMUL/FADD, without fused multiply-add in that inspected loop.
On the matching platform, verify the entire installed module hash and selected
bytes; a changed binary requires renewed inspection, not a silently refreshed
baseline. Other platforms explicitly skip this platform-specific evidence.
This narrows the compiled-graph premise for one symbol, but does not establish
runtime dispatch to it, cached-denominator construction or FPCR rounding state.
Arm documents that floating-point instructions depend on FPCR; no runtime mode
is inferred from the instruction mnemonics:
https://developer.arm.com/documentation/111108/2025-12/SIMD-FP-Instructions/FDIV--vector---Floating-point-divide--vector-- .
The native safety certificate and task 3.9 remain incomplete.

Read the caller-thread floating-point environment only on the inspected Darwin/
arm64 ABI: `fenv_t` has two 64-bit unsigned fields, FPSR then FPCR. Use standard
ctypes with explicitly declared C signatures for fegetenv and fegetround, check
the return code and buffer size/alignment, and require both FPCR and the rounding
mode to be zero. This deliberately qualifies only the observed default mode;
synthetic nonzero/invalid/bool controls fail without modifying the actual CPU.
Bracket kernel/settings setup, each of eight ephemeris constructions, and the
304 existing state requests with read-only snapshots under one 300-second
budget. Report 626 snapshots and their unique values; no setters, exception
clearing or native spacecraft propagation are used. FPSR exception history is
not a rounding-mode proof and is not required to be clear. Record the inspected
SDK header hash/ABI in the native observation fixture, but do not require the
SDK to be installed when tests run. Other platforms skip this ABI-specific test.
Before/after snapshots cannot exclude temporary changes within calls, other
threads, or future calls; continuous runtime semantics and dispatch remain open.

Extend the same hash-pinned static observation to initializeDenominators for the
double-time/six-double-state/double-scalar specialization. At the inspected
`[0x19a348,0x19a390)` loop, the accumulator is loaded with exactly 1.0, equal
source/target indices skip the factor, and scalar FSUB/FMUL plus a store update
each cached product in order. Record and verify these additional instruction
bytes without changing the module hash. This agrees with the existing exact
Fraction grid test and its `(-1)^(5-i)*i!*(5-i)!*300^5` denominators, whose
intermediates are exactly representable on the pinned grid. It narrows the
compiled-denominator premise for that symbol; it is not live cache readback or
proof that all production construction paths select this specialization. Runtime
dispatch and continuous rounding-state premises remain unqualified.

Trace static construction in the same pinned binary: createBodyEphemeris<double,
double> calls the corresponding tabulated-SPICE factory, which calls the
double-time/six-double-state SPICE interpolator builder. The builder increments
timestamps with scalar FADD and calls the matching one-dimensional factory.
Its enum-3 (Lagrange) branch checks the settings dynamic cast before directly
calling the double-time/six-double-state/double-scalar Lagrange constructor.
Record direct calls, enum/cast branches and the grid increment in the existing
byte-checked observation. Require all eight public settings objects to have the
InterpolatedSpiceEphemerisSettings type. The Python binding does not expose its
nested interpolator_settings; do not infer live nested settings or virtual-call
dispatch merely from available static branches. This narrows the construction
route evidence without changing settings or certifying runtime selection.


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

Use `get_default_body_settings` with SSB/J2000, explicit direct-SPICE ephemerides and verified coverage of the complete candidate interval. The literal production model identifier is `ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-cannonball-srp-schwarzschild-direct-spice-v2`. Override Moon gravity with pinned `gggrx1200` degree/order 200 in `IAU_Moon` and Mars gravity with pinned `jgmro120d` degree/order 120 in `IAU_Mars`, and require each gravity field's associated frame to equal its rotation target frame. The pinned baseline coefficient hashes are:

- Moon: `3f4652c01db58e14a4e4c67fe8225874d10120a29cbd7699f5068469ef65b21d`
- Mars: `d13b31d46862838abe62ebab3cef8209244588abe14e4e5e481c0fb64354e980`

Create direct point-mass settings for Sun, Mercury, Venus, Earth, Jupiter, and Saturn. Create only harmonic settings for Moon and Mars; degree zero is already included. Use and verify the field-provided GMs `4902800121846.8 m^3/s^2` and `42828375815756.1 m^3/s^2` to relative error `1e-15` rather than substituting the M2 SPICE GMs. Exact runtime values and hashes go into provenance.

The spacecraft receives a cannonball radiation target with scenario area and coefficient and `{"Sun": ["Moon", "Earth", "Mars"]}` occultation. Configure the Sun source explicitly at `3.828e26 W` rather than inheriting a mutable default. Add Sun Schwarzschild relativity only. No atmosphere, albedo, thermal radiation, Lense-Thirring, de Sitter, or EIH term is silently included.

Collision checks cover exactly Sun, Mercury, Venus, Earth, Moon, Mars, Jupiter, and Saturn. Require pinned `pck00010.tpc` hash `59468328349aa730d18bf1f8d7e86efe6e40b75dfb921908f99321b3a7a701d2`. Its SPICE radius vectors in meters are Sun `(696000000,696000000,696000000)`, Mercury `(2439700,2439700,2439700)`, Venus `(6051800,6051800,6051800)`, Earth `(6378136.6,6378136.6,6356751.9)`, Moon `(1737400,1737400,1737400)`, Mars `(3396190,3396190,3376200)`, Jupiter `(71492000,71492000,66854000)`, and Saturn `(60268000,60268000,54364000)`. Use each maximum component as a conservative spherical guard and define impact by `||r_spacecraft-r_body|| <= guard_radius`. A missing, non-finite, nonpositive, or more-than-`0.001 m` mismatched vector is a resource error. These collision surfaces are separate from the Moon/Mars mean shape radii used to interpret configured orbit altitude.

### 5. Parameterize credible minimal finite-burn guidance

Before segmented propagation, concatenate the existing force settings by source: Sun has point gravity, SRP, and Schwarzschild; Moon and Mars each retain exactly one harmonic term; other sources retain one point term. Verify the combined acceleration independently at near-Moon, cruise, and near-Mars states under the existing force tolerance. Reset and read back TudatPy 1.0's mutable global PPN gamma/beta as `(1, 1)` immediately before each arc's acceleration-model construction; concurrent simulations that mutate the shared SPICE/PPN state are unsupported. A resource record alone does not freeze the native globals.

Historical v1 regression only: the `300 s` time-limited ephemeris table is an approximation. Both integrators
using the same table do not test this source of error. Qualification evidence is
`tests/data/m3_ephemeris_qualification.json`, reproduced with
`conda run -n space-nav python -m pytest -q -s tests/test_trajectory_ephemeris.py`.
It covers all eight bodies over the full provisional candidate interval at 38
deterministic epochs (32 off-grid interior points, endpoints and four near-edge
points), comparing the default six-point Lagrange tables at 300 s and 150 s
against direct SPICE with no aberration, SI/SSB/J2000 and TDB seconds from J2000.
The fixture constructs the former v1 ephemeris settings and verifies
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
