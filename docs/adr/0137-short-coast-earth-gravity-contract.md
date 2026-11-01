# 0137 — Specify a short, independently checked Earth-gravity ablation

Date: 2026-11-01
Decision status: accepted bounded diagnostic design under autonomous M3 continuation.
Implementation: R5.1 specified; preparation and native execution not started.
Scope / milestone: M3 research,300s parked ballistic component; not lunar escape or a Moon–Mars solution.
Base revision: `f80d24b413cea50163f8ea009640a6ac9b277df1`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [audited endpoints](0136-retained-boundaries-pass-arithmetic.md) and [local force screen](0133-three-epoch-gravity-screening.md).

## Context and constraints

R3 measured instantaneous gravity; R4 independently checked the configured physical
initial state. Neither measures integrated model sensitivity. Existing
[coast diagnostics](../../src/space_nav/coast_diagnostic.py) bind the full M3
model and compare Tudat profiles, not an independent numerical engine. Existing
[R1/R2 oracles](0120-independent-elliptic-coast-benchmark.md) solve a single central
field and cannot represent moving three-body forcing. No GMAT adapter is present
in the inspected project files; this is not a claim about system installation.
SciPy1.17.1 is already pinned and installed (distribution metadata checked without
scientific imports). No new dependency or generic propagation framework is needed.

## Options considered

- Repeat the full failed coast or resume targeting: reject; unresolved controls,
  full-force reference and mission boundaries would confound this local question.
- Modify the full-model production adapter to masquerade as reduced gravity:
  reject; its model identity and existing tests intentionally forbid that.
- One private two-model point-mass experiment, native Tudat RK4 versus separately
  implemented SciPy DOP853 dynamics: selected for preparation after this design.

## Decision and rationale

### Fixed physical question, state and models

Question: how does adding Earth direct gravity change the first300s of unpowered
motion from the already configured parking-state initial condition, within two
explicit restricted models? No departure burn occurs; this is not an escape arc.

Bind0119 SHA256 `3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0`,
0098 SHA256 `b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057`,
0133 SHA256 `74238edd641e1b5fda42a209672c68e5bc201b20d3cffba24169e6f9b3b6a580`, and
0136 SHA256 `81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063`.
Keep complete scenario/candidate equality and raw0098 initial six-state at
`science.runs[0].run.boundaries[0]`. Initial epoch t0=978995455.2304223 TDB s;
tf=t0+300s=978995755.2304223. Compare seven exact nodes t0+50*j, j=0..6.
No initial rounding, phase/epoch shift, analytic reconstruction, interpolation
of native saved states, chained propagation or changed candidate d0001-t0035.

All dynamics are SI/SSB/J2000 with geometric NONE ephemerides. Model A is
`r5-ssb-sun-moon-point-v1`: direct Sun and Moon point masses. Model B is
`r5-ssb-sun-moon-earth-point-v1`: identical plus Earth. Use Moon4902800121846.8,
Sun1.327124400420322e20 and Earth398600435468295.9m^3/s^2 from the frozen records.
The harmonic-model lunar GM is deliberately reused as the point coefficient;
no lunar harmonics are enabled. Verify native assigned GMs within relative1e-15.
Bodies move on the same pinned direct SPICE tracks; do not integrate them or freeze
them at t0. A is an intentional omission control, not an adequate lunar model.

For included bodies C in the declared order Sun,Moon[,Earth],
`a(t,r)=sum(mu_C*(r_C(t)-r)/norm(r_C(t)-r)^3)`.
SSB is inertial: no Sun/Moon indirect term belongs in this equation. Do not use
R3's Sun-relative40.2% ratio as the acceleration ratio in this different model.
Production M3 forces/identifier remain unchanged; neither restricted model may
be labelled full M3. Both omit other planets, lunar/Martian harmonics, SRP/shadows,
relativity and thrust. Constant2000kg is metadata, not integrated mass dynamics,
reserve validation or a fuel-feasibility claim.

### Independent engine and fixed integration profiles

Use a private Tudat Cartesian translational adapter with central body SSB,
explicit three-body direct geometric ephemerides and point-gravity fields only;
inspect actual force inventory and reject defaults/extras or model substitution.
Reuse immutable R2 finite-input/budget/identity utilities where applicable, not
its Sun-only propagator or full-model coast guards. Retain/hash all new sources.

Each of four native arcs starts from the identical stored six-state: A RK4 h=1s,
A RK4 h=0.5s, B RK4 h=1s, B RK4 h=0.5s. No adaptive native stepping or later
profile change. All seven sample epochs must exist in native saved histories;
first state/epoch must match exactly, final completion within1e-6s. Each model
gets a fresh matched body system; no state carryover, burn or mass propagation.

The independent oracle uses pinned SciPy1.17.1 `solve_ivp(method='DOP853')` and
separate force code, no production force/propagation helpers. Obtain body states
with SpiceyPy8.2.0 geometric `spkezr` at the exact TDB argument, observer SSB,
J2000/NONE, explicitly convert km/km/s to SI and use unit-vector/squared-distance
fields. Shared SPICE data are authoritative inputs, not independent ephemeris
truth. Repeated calls use the existing kernel pool; no kernel reload/download.

To avoid relative tolerance scaling on1e11m coordinates, integrate correction
variables q_r=r-r0-v0*s, q_v=v-v0, s=t-t0: q_r'=q_v, q_v'=a(t0+s,r0+v0*s+q_r),
with all six initial corrections zero. Reconstruct and retain SSB states at the
seven nodes; report this coordinate change explicitly, not as different physics.
Oracle normal: rtol1e-12, atol(1e-7m x3,1e-10m/s x3), max_step5s, first_step1s.
Oracle tighter: rtol1e-13, atol(1e-8m x3,1e-11m/s x3), max_step2.5s, first_step0.5s.
Use t_eval=(0,50,100,150,200,250,300); DOP853's internal interpolation is part
of the declared oracle and is not resampling a native trajectory.

Run A's two native arcs, A's normal/tighter oracles and checks, then the equivalent
B sequence. At each node, native h1/h0.5 and native h0.5/oracle tighter must each
agree within0.01m/1e-5m/s in Euclidean norms; oracle normal/tighter within
0.001m/1e-6m/s. These are new component-integration comparison gates, not relaxed
R4 coordinate conversion, M3 mission closure or existing global-validation gates.

Retain signed B-minus-A position/velocity vectors and norms from native h0.5 and
oracle tighter. Their signed-vector discrepancy must be <=0.02m/2e-5m/s at all
nodes. Report any resolved sensitivity only after all numerical gates pass;
small/zero sensitivity is a result, not permission to tune. These comparisons
are empirical same-model numerical evidence, not rigorous exact-solution error
bounds, formal uncertainty envelopes or whole-arc force-completeness proof.

### Evidence, guards and fixed execution budget

Preparation must test analytic central/circular and zero-force limits, direct
SSB versus erroneous indirect forces, correction-variable equivalence, SI and
exact-TDB wiring, initial/sample/GM/model/hash/counter/profile drift and all
failure/deadline/partial-output paths before native reference execution. Check
pure numerical fixtures against an independent closed form or Decimal oracle;
prove the two integration paths do not share acceleration/propagation code.
New code completion requires focused/full pytest, Ruff and strict OpenSpec.
No scientific experiment is run during this design stage.

After verified preparation, permit exactly one fresh-process screening with a
shared60s cooperative budget including imports, setup, checks, both initial/final
identities, four native arcs, four oracle solves, comparisons and exclusive JSON
serialization/flush. Separate attempted/completed counts; stop before a fifth
native arc or oracle solve. Cap all oracle RHS evaluations at10000 attempted
across four solves. Each RHS queries Sun,Moon,Earth once, including Earth for
A's guards; at most30000 Python-visible oracle state reads plus21 once-only
node-table reads. Native internal ephemeris evaluations are not included in this
Python-query count and must not be reported as bounded by30021. No retries.

Guard finite/nonboolean states, time monotonicity/coverage, exact inputs and
spacecraft separation from Sun696000000m, Moon1737400m, Earth6378136.6m.
Apply guards at all retained native states and every oracle RHS evaluation;
report actual sampling coverage without claiming continuous safety or that
native internal RK stages were all guarded. Native errors stop immediately.
Record raw initial/body states at all seven nodes, model manifests/constants,
all eight trajectories at their applicable nodes (four native plus four oracle
profiles), signed numerical and model differences,
minimum checked distances, versions/imports/builds/source/binary identities,
original ordered13 kernel name/hash manifest, counters/timings and missing data.
Oracle internal RHS states need not all be saved; counts and source/solver settings
are retained, not an assertion that every internal evaluation was audited offline.

Initial/final kernel/resource/runtime/source identities must agree, extending
R2 identity with actual SciPy/NumPy module paths, versions and solver/coefficient
source/build identities. Preserve returned raw histories before after-call budget
checks. First unexpected numerical, resource, domain, identity, coverage, solver,
count or time failure stops without changed inputs/gates/budget or another run.
Retain finite partial evidence, actual overrun and unavailable downstream checks;
if a changed contract or user action is needed, pause automation. A separate
zero-native offline audit recomputes saved-node forces/differences/gates/metadata;
it does not replay all RHS stages or certify continuous integration.

## Consequences and revisit conditions

The result would quantify Earth-force model sensitivity on this300s parked arc
and independently compare two numerical engines at that restricted fidelity.
It does not extend R1's positive reserve, prove escape/capture/finite burns, bound
all omitted forces or the291-day mission, qualify the UI or close M3/task3.9/M6.
No new optimizer, public API, dependency or full-model production alteration.

## Evidence and verification

Reviewed existing pinned-model coast adapter, force assembly, direct-SPICE setup,
force-comparison tests and central-field benchmark; no native import or numerical
experiment occurred. [Tudat direct-gravity documentation](https://docs.tudat.space/en/stable/user-guide/state-propagation/propagation-setup/translational/third-body-acceleration.html)
supports the SSB direct versus non-inertial differential distinction; its live
page is1.1.0, mathematical guidance only, not pinned1.0.0 behavior validation.
[SciPy1.17.0 solve_ivp documentation](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.integrate.solve_ivp.html)
documents DOP853 and per-component tolerances/t_eval. Runtime remains installed
1.17.1; preparation must verify that build/API rather than infer parity from docs.
Strict OpenSpec, local facts/input hashes,175 local links and diff checks pass;
all241 previously tracked protected code/test/example/environment/legacy/evidence
files remain byte-for-byte unchanged. Unchanged runtime tests are not rerun; ADR0132 retains4936.
