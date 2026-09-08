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
- [ ] 3.6 Assemble the complete per-source force mapping and reset/read back global PPN values before every arc; verify near-Moon/cruise/near-Mars total acceleration against an independent assembly under the existing force tolerance, poisoned PPN recovery, and no duplicated gravity. Complete this before task 4.3.
- [ ] 3.7 Verify safety termination precedence over final-epoch failure, an initially unsafe state, and a trajectory entering and leaving a collision sphere between output epochs; distinguish rejected trials from native integration failures and discard unsafe trial history before task 4.3.

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
