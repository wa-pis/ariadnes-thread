# 0162 — Bound corrected integration on retained real inputs

Date: 2026-11-08
Decision status: accepted design under the user's instruction; execution is not authorized by this record.
Implementation: pending R5.16 preparation; R5.17 retained execution not started.
Scientific verification: pending; this stage checks metadata and documentation only.
Scope / milestone: M3 R5.15, numerical integration with real ephemerides, model A only.
Base revision: `4db0e34d0414652195dd62b344433e95d7b88eb4`, initially clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; narrows the next experiment without rewriting ADR0137/0148 or their failed result.

## Context and constraints

[ADR0161](0161-moving-coordinate-arithmetic-passes.md) verifies controlled q/w
assembly on retained real source operands. Its manufactured corrections are not
an integrated trajectory. [ADR0152](0152-compensated-synthetic-time-validation.md)
verifies a combined time/assembly candidate only on an analytic synthetic case.
Neither establishes that the candidate can finish the original real300s coast.

[ADR0148](0148-short-coast-oracle-rhs-limit.md) retains complete A native RK4
histories at1s/0.5s, but its first oracle exhausted10000 RHS and30021 source reads.
It saved no complete oracle, tighter solve, B result or Earth-force sensitivity.
Its final runtime/kernel identity was never reached. A new identity check cannot
retroactively complete that provenance. Saved native arrays are conditional
numerical references, not independently certified flight truth.

Physical question: can the combined numerical candidate complete two separately
executed A integrations over the unchanged300s and pass the original sampled trajectory
and force gates, using genuine dynamically solved corrections? This is numerical
verification before omitted-force sensitivity, not a new optimizer or a test of
whether a complete Moon-to-Mars mission is physically feasible.

## Options considered

- Repeat R5.3 unchanged or expand A/B immediately: reject; repeats the failed
  boundary and mixes its repair with omitted-force conclusions.
- Replace live ephemerides with a new polynomial runtime provider: defer; changes
  source rounding/selection as well as the integration boundary.
- Two A-only compensated DOP853 solves, compared with retained native histories
  and a separately reconstructed sampled force reference: selected. It isolates
  a bounded combined numerical candidate without new native propagation.

## Decision and rationale

### Frozen physical inputs and references

Bind all protected bytes and artifact/helper hashes from the
[0161 verification manifest](experiments/0161-verification.json), including its
SHA256 `d8397b00362e4a3464ec9895351a10d34e96a18132dfa6fd9d08e86834cfce99`.
Bind the original [ADR0137 contract](0137-short-coast-earth-gravity-contract.md),
[0136 anchor](experiments/0136-retained-boundary-audit.json),
[0148 histories](experiments/0148-short-coast-study.json),
[0155 source records](experiments/0155-real-source.json) and the pinned pure
[0153 polynomial helper](experiments/0153-real-ephemeris-oracle.py).
The new [metadata verification](experiments/0162-verification.json) records these
bindings without evaluating polynomials, new spacecraft states or fields.

Keep the exact saved binary64 initial values:

- t0=978995455.2304223 TDB seconds since J2000; local s in[0,300]s.
- r0=(-47124635282.7281,128473304107.83153,55670397503.89886)m.
- v0=(-29590.75977762049,-9186.174444867514,-2407.2479826554863)m/s.
- q(0)=w(0)=(0,0,0), with q in m and w in m/s; q'=w, w'=a.
- Output offsets s=(0,50,100,150,200,250,300)s. All seven are genuine coepochs
  of both saved native grids, unlike the earlier nanosecond assembly probes.
- SI, SSB origin, J2000 orientation, geometric NONE states. Direct point gravity
  in source order Sun/Moon: mu=1.327124400420322e20/4902800121846.8 m^3/s^2.
  Do not substitute the different SPICE lunar GM. Earth mu remains the frozen
  398600435468295.9 metadata; Earth supplies a guard and lunar centre chain,
  not a force in A. Mass2000kg is constant metadata, not a mass/fuel result.

Retain the same ordered13-kernel INPOP19a pool, resource/build/module/binary
identities, Python3.12.14 and SciPy1.17.1/NumPy identities. Use established
`kernel_metadata()` inventory of the actual SpiceyPy pool, including its Tudat
count cross-check, before/after. Allow initialization once; no reload, fallback,
new kernel, download or GM acquisition. Preserve original provider operations:
`spkezr(body,hi,"J2000","NONE","SSB")`, body order Sun/Moon/Earth, each raw
km/km/s component multiplied once by1000. Retain raw returns before post-call
checks, including calls that return too late.

The three unique retained Type2 records (Sun10->0, Earth399->0, Moon301->399)
and segment intervals cover the entire300s by exact metadata comparison. Use
those exact words for offline reference evaluation. This does not establish
fresh SPICE segment-selection parity at every unsampled epoch. State and source
agreement are qualified only at the predetermined observations below; do not
invent a uniform300s source-error bound from0155's sampled11.4um discrepancy.
No new segment selectors or record reads are required or allowed in this study.

### Numerical candidate and two solver profiles

For each callback s use TwoSum so exact(t0)+exact(s)=exact(hi)+exact(lo),
require finite s in[0,300], query the three bodies at hi, and preserve the sign
of lo. Set componentwise:

- Dhat=RN(v0*s), c=RN(Vhat_body*lo).
- dhat=fsum(Bhat,-r0,-Dhat,-q,c); never use a flattened spacecraft position
  as the force input.
- rho=hypot(*dhat), ahat[j]=mu*(dhat[j]/rho)/(rho*rho).
- Sum Sun/Moon acceleration components with fsum; return derivative (w,a).
- Export Xhat=fsum(r0,Dhat,q), Uhat=fsum(v0,w).

This freezes the verified ADR0159 field operation order; it differs from0138's
strength-first evaluation as well as its time/coordinate assembly. The physical
equations stay unchanged. Test the combined candidate; success cannot attribute
the old failure or any improvement to just one of these numerical changes.
Actual solver q/w, including intermediate trial states, are binary64 operands.
Do not manufacture q_ideal/w_ideal or import0160's prescribed-fixture constructor.
Assembly bounds do not establish physical or truncation accuracy of q/w.

Use SciPy `solve_ivp`, method DOP853, local t_span=(0,300), zero six-state y0,
and the seven fixed t_eval values. Keep the original settings exactly:

| Profile, in execution order | rtol | q atol, m | w atol, m/s | max_step, s | first_step, s |
|---|---:|---:|---:|---:|---:|
| normal | 1e-12 | 1e-7 | 1e-10 | 5 | 1 |
| tighter | 1e-13 | 1e-8 | 1e-11 | 2.5 | 0.5 |

DOP853's own dense output at t_eval is permitted; never interpolate the native
arrays. Inspect the pinned implementation and retain coefficient/controller
hashes. A bounded observer may record trial step, scale, error norm, accept/
reject decision and RHS index ranges, without changing controller behavior.
Preparation must prove exact observed-versus-untouched final t/q/nfev parity
on analytic fixtures only. There is no extra real parity solve. Preserve the
pinned acceptance test and floating t_new-t behavior; max_step is a setting,
not a new strict bound on a rounded recorded difference. Callback times can
move backwards or repeat; every actual attempt still counts.

### Gates and predetermined force observations

At every one of the seven output epochs require Euclidean position/velocity
norms for the exported Cartesian states, independently rebuilt from raw data:

| Comparison | Position, m | Velocity, m/s |
|---|---:|---:|
| saved native h1 versus saved native h0.5 | <=0.01 | <=1e-5 |
| saved native h0.5 versus corrected tighter | <=0.01 | <=1e-5 |
| corrected normal versus corrected tighter | <=0.001 | <=1e-6 |

These are unchanged ADR0137 gates, not accuracy certificates between nodes.
Do not use the synthetic RHS<=241 or first-trial-accepted targets as real gates.
No A/B difference or Earth-sensitivity result is available from this contract.

For each profile preselect its seven output observations plus its first seven
completed RHS observations by invocation ordinal0..6, retaining duplicates as
separate observations. Require at least one selected RHS with nonzero lo in
each profile for full success. An incomplete prefix remains incomplete; no
backfill, adaptive selection, extra callback or state query to fill a sample.
Thus completion requires28 observations,84 three-body state checks,56 included
source-force rows and28 sampled A totals. Only21 live node-state queries are
made, shared by both profiles; selected RHS reuse already returned raw states.

After both solves (within the same study budget), independently reconstruct
P(hi), P(T) and derivatives using the retained exact Type2 words. For each
selected body check original source-state0.001m/1e-6m/s parity and the1e-12m
increment envelope plus separate exact Taylor/velocity/product-rounding terms.
For each actual q/w use ADR0159's independent Fraction drift/product/state/
relative-component bounds, exact-zero and product ties-even handling, and four
geometries d0..d3 with signed telescoping at80/100 Decimal digits. Preserve
relative1e-60 precision convergence, zero handling and stable classifications.
There are56*4*2=448 Decimal source fields, with no Earth force field.

Require both returned-geometry and overall force gates for each included source
and A total: error norm <=max(1e-15m/s^2,1e-11*Sk), using the corresponding
source reference norm or sum of constituent reference norms. Include original
source and drift/rephasing errors without subtraction or extra allowance.
No flattened/omitted-q controls or extra diagnostic force arms are needed.
Deferred failures stop when checked; they cannot be described as having stopped
an earlier integration stage. Retain unavailable downstream checks explicitly.

Before each runtime field, all three candidate body separations must be strictly
outside Sun696000000m, Moon1737400m, Earth6378136.6m. Before each independent
reference field, all four relevant exact geometries must pass the same guards,
including Earth geometry even though A omits its force. Check every new RHS/
output geometry. For the saved native arcs verify retained guarded_states=301/
601 and minimum-distance metadata against the frozen radii, with their original
2712 returned native guard reads; do not re-query or claim an independent rebuild
of every historical native guard. Independently guard the14 native comparison
states (two grids times seven nodes;42 body separations) using the shared live
node table, without new state queries or force fields. This is sampled exclusion
only, not a certificate for native internal stages or continuous collision safety.

### Preparation, budgets, identity and separate audit

R5.16 prepares private helpers, observer and auditor without changing historical
helpers, production, public APIs or dependencies. Reuse compatible pure utilities.
Test analytic3D/zero/cancellation, split-time identity/sign/sub-ulp cases, genuine
nonzero solver q/w, independent force/component oracles, exact native coepochs,
profile/controller parity and source/provider/GM/kernel/hash/domain/schema
mutations. Every named mutation must fail a named independent fixture. Exercise
raw-return-before-deadline, attempted/returned/completed distinctions, partial
trials/solves, precision/gate boundaries and exclusive evidence/finalization.
Run focused/full pytest, Ruff, strict OpenSpec, links/digests/diff and frozen
checkout/protected-file checks; retain tested hashes before any real run.

Only after verified R5.16 and separate execution authorization may R5.17 launch
one fresh pinned study process, with a shared60s budget from its external
pre-child-start timestamp through imports/setup/identity/hashing, both solves,
all checks, serialization, flush and post-flush checks. Two solves are a maximum
and a full-success requirement: a failed normal solve or any already-checkable
required gate prevents the tighter attempt. No retry or extra profile.
Global maxima, including failed attempts and output/dense-evaluation work:

| Operation | Study cap | Separate audit cap |
|---|---:|---:|
| DOP853 A solve attempts | 2 | 0 |
| RHS attempts (all profiles/stages) | 10000 | 0 new; inspect at most10000 |
| Live spkezr state attempts | 3*N_RHS+21 <=30021 | 0 |
| Trial descriptors, both profiles | 1000 | inspect at most1000 |
| Native comparison-node guard separations | 42 | 42 rebuilt |
| Binary64 included-source fields | 2*(N_RHS+14) <=20028 | <=20028 rebuilt |
| High-precision observations/body checks/source rows | 28/84/56 | 28/84/56 |
| Decimal source fields / sampled A totals | 448/28 | 448/28 |
| Native spacecraft propagations / GM lookups / optimizer calls | 0/0/0 | 0/0/0 |

Counters are upper bounds; exact completed node/observation counts and both
complete solves are success prerequisites. Dynamic A totals are capped at
N_RHS+14<=10014, separately from28 sampled reference totals. Selected RHS
reuse dynamic fields; do not recompute them outside these budgets. Count any
attempt that raises or returns late. Node table is acquired once, not once per
profile. No hidden warm-up, replay or controller-parity solve on real inputs.

Initial/final kernel_metadata snapshots are at most two API attempts; each has
15 explicit metadata API calls at a13-kernel pool, recorded separately from
spkezr. Initialization is one bounded setup attempt; no reloads/selectors/array
reads. This does not claim an exact total of transitive C/FFI calls. All setup,
metadata and raw return bookkeeping share60s; identities must match frozen
inputs before/after, including binaries, coefficients and actual kernel order.
New final identity applies only to this process, not the incomplete0148 one.

Use a separate fresh stdlib-only auditor with its own inclusive10s from external
pre-child-start through final flush. It makes zero scientific imports/native
calls/kernel loads/queries/propagations. Independently reconstruct every RHS's
epoch identity, raw conversion/operands/derivative/domain/counters and binary64
fields without candidate force/assembly/controller imports or trusting flags.
At the28 fixed observations rebuild Fraction/Decimal reference checks, and
recompute all trajectory comparisons/required gates and identity/finalization.
The pinned pure independent polynomial/reference utility may be shared; this
is not a second ephemeris or independent force-reference implementation.

All-RHS arithmetic replay is distinct from sampled high-precision source/force
qualification. Neither certifies unsampled live source accuracy or continuous
safety. The audit10s feasibility and the real solve's convergence are unmeasured;
preparation must expose budget failures rather than silently increase them.

Bind code/input/runtime identities, ordered attempted/returned/completed ledgers,
all raw RHS s/q/w/hi/lo/body returns/drift/rephasing/separations/derivatives,
trial decisions or unavailable decisions, both returned arrays and seven exported
states, gates, sample selection, counters, elapsed times and earliest failure.
Use exclusive once-only attempt markers, finite duplicate-free JSON and immutable
receipts; retain partial raw arrays before checks. An emergency parent watchdog
cannot extend scientific deadlines. Late flush/final identity failure downgrades
success. Full success requires every gate, two complete solves, all counts and
both process finalizations plus the saved-data audit; process exit0 is insufficient.

## Consequences and revisit conditions

A pass would qualify this combined A numerical candidate at seven outputs and
the declared sampled force observations, conditionally on saved native provenance.
It would not prove historical R5.3 causality, an independent astronomical truth,
full-flight accuracy, omitted-force sensitivity, finite burns, continuous safety
or strict M3. Preserve R5.3 as failed and automation as PAUSED. M4-M6/ML/search/UI
qualification remain deferred. A later separately bounded A/B study would still
be needed before a claim about missing Earth gravity.

Any scientific/budget/provenance failure is a valid negative result. Preserve it,
stop without retry/tuning and revisit the specific failed assumption in a new
contract before changing gates, inputs, kernels, profiles, count/time caps or
physical scope. The user asked for design here; R5.16 and R5.17 remain unchecked.

## Evidence and verification

The metadata-only [verification record](experiments/0162-verification.json)
binds381 protected files, saved native301/601 grid coverage and the three exact
Type2 record/segment intervals. No new state/polynomial/force evaluation, solver,
scientific import, kernel setup or native call occurs in this design stage.
Unchanged tested bytes reuse ADR0160's5881 passing tests and Ruff; runtime tests
are not rerun for documentation. Local links, finite JSON, source/protected
hashes, diff and strict OpenSpec are checked before commit. Numerical gates and
all future budget feasibility remain unmeasured by this design.

Primary semantics: [NAIF spkezr](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkezr_c.html)
defines geometric TDB/J2000 state queries and km/km/s outputs;
[SciPy solve_ivp](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.integrate.solve_ivp.html)
documents t_eval and DOP853 output interpolation. These explanatory links do not
replace pinned1.17.1 source identity and preparation parity checks.
