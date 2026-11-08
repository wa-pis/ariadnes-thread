# 0159 — Freeze moving-spacecraft coordinate assembly checks

Date: 2026-11-08
Decision status: accepted under the user's instruction to design and record this check.
Implementation: design complete; private preparation and retained execution not started.
Scientific verification: pending; no new spacecraft coordinates, forces or integration evaluated.
Scope / milestone: M3 R5.12, controlled moving-coordinate arithmetic before a new solve.
Base revision: `71fac0219c258e2d19658d0e469cb4ca485e2ee7`, initially clean `dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [ADR0158](0158-fixed-position-real-gravity-passes.md), preserving all previous data, helpers and gates.

## Context and constraints

ADR0158 verifies source-time compensation and force arithmetic at one fixed X.
A correction-coordinate solver instead assembles position from r0, a velocity
product and a position correction. Rounding a large absolute spacecraft position
before subtracting it from a body can lose small terms. Testing that boundary
must precede a corrected integration; it must not replay the failed R5.3.

The saved0148 native histories contain301/601 states at1s/0.5s grids. Exact
rational comparison with0155's seven epochs matches only elapsed zero. Neither
nearby native states nor interpolated corrections are genuine coepoch operands
for the other six samples. The existing failed oracle saved no completed
correction solution. Do not relabel manufactured or interpolated data as one.

## Options considered

- Interpolate0148 native states or start an integration to obtain corrections:
  reject for this arithmetic question; adds unverified dynamics/operands.
- Repeat the successful fixed-X study: cannot test moving drift/corrections.
- One explicitly controlled kinematic probe, anchored to the saved six-state and
  using the existing source samples: selected; exercises nonzero drift and both
  correction components with exact independent operand arithmetic, zero native
  acquisition and no claim of a dynamically valid spacecraft trajectory.

## Decision and rationale

### Frozen inputs, motion and meaning

Bind the following byte identities before deriving any probe states or fields:

| Artifact | SHA256 |
|---|---|
| [0136 boundary audit](experiments/0136-retained-boundary-audit.json) | `81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063` |
| [0148 partial study](experiments/0148-short-coast-study.json) | `8bbe6f5f7d08f4e220ee3cff450488531da0776b8a69cb4c37e1c9af9872b096` |
| [0155 real sources](experiments/0155-real-source.json) | `278b094cff6dd417ac15c04d3b4e4da137acede17de7147babd72fe9e3812102` |
| [0158 fixed-X study](experiments/0158-fixed-gravity-study.json) | `08b37c96df1bff965e0a93015085e5acf733747ddd1f97805b5b21f135bd02ed` |
| [0158 separate audit](experiments/0158-fixed-gravity-audit.json) | `19f89eda69d5d4b184a21f611a07287ea29c41041f72d6e305c1cb896c2d442d` |
| [0158 verification](experiments/0158-verification.json) | `834268e321b96355b3a2cb0ac7928bf6b8a0f2a39387735f90eec88f8007d3f9` |

Require exact0136/0148 endpoint equality and0158's verified input/helper bindings.
Keep r0=(-47124635282.7281,128473304107.83153,55670397503.89886)m and
v0=(-29590.75977762049,-9186.174444867514,-2407.2479826554863)m/s.
Keep t0=978995455.2304223TDBs and the seven original binary64 offsets, in order:
`0,2.9802322387695312e-8,5.960464477539063e-8,8.940696716308594e-8,
0.05260015195876773,150.00000008940697,299.9999999701977` seconds.
The exact epoch is T=exact(t0)+exact(s)=exact(hi)+exact(lo), using each saved
hi/lo identity. Craft drift and corrections use s, never hi-t0 or rounded T.

For this manufactured probe only, choose the exact dyadic vector
`a_fixture=(-1,1/2,-1/4)m/s^2`. For each exact binary64 s, form rational
`q_ideal=a_fixture*s^2/2` and `w_ideal=a_fixture*s`; independently round once,
nearest/ties-even, to binary64 q in m and w in m/s. Retain ideal fractions, rounded
hex/ratios and rounding errors; verify each rounding within half an ulp, with
exact zeros and even-significand tie selection preserved. These are prescribed
input corrections, not gravitational acceleration, thrust, a new mission
parameter/default or a saved solver result.

The assembly target treats the returned q,w as exact binary64 input operands:
`R*=exact(r0)+exact(v0)*exact(s)+exact(q)` and
`V*=exact(v0)+exact(w)`. Fixture quantization is checked and reported separately;
this check does not bound error in a future solver's q,w. The ideal quadratic
formula only manufactures inputs; the returned samples are labelled
`controlled-kinematic-arithmetic-probe`, never a propagated mission trajectory.
Use one probe/seven times, not a new trajectory search or extra motion branches.

Preserve SI/SSB/J2000/TDB/NONE, the original13-kernel saved provenance, INPOP19a
Type2 polynomials/centre chains/coverage and unchanged R5 GMs:
Sun1.327124400420322e20, Moon4902800121846.8,
Earth398600435468295.9m^3/s^2. Model A sums Sun/Moon; B adds Earth in that order.
Use direct SSB gravity; keep omissions and constant-mass/non-propagation scope.
No new body samples, kernel pool, GM lookup, public API or dependency changes.

### Candidate assembly and independent references

For each component j, use the frozen binary64 operations:

- `Dhat[j]=RN(v0[j]*s)` and `c[j]=RN(Vhat_body[j]*lo)`.
- Diagnostic/export position `Xhat[j]=fsum(r0[j],Dhat[j],q[j])`;
  velocity `Uhat[j]=fsum(v0[j],w[j])`.
- Required separation
  `dhat[j]=fsum(Bhat[j],-r0[j],-Dhat[j],-q[j],c[j])`.
- `rho=hypot(*dhat)`; `ahat[j]=mu*(dhat[j]/rho)/(rho*rho)`.

Keep all terms separate until the final sum. The force candidate must not use
Xhat or a flattened Bhat+c as its input separation. Componentwise model sums
use fsum in the frozen source order. Record all terms and returned six-states;
first sample q=w=Dhat=0 must reproduce the saved initial state and0158's
elapsed-zero compensated source/model vectors exactly, without rerunning0158.

An independent Fraction oracle constructs products/sums from integer ratios,
not candidate helpers or flattened coordinates. For every component require:

- `|Dhat-v0*s| <= ulp(Dhat)/2`, product error in m.
- `|Xhat-R*| <= ulp(Dhat)/2 + ulp(Xhat)`, in m.
- `|Uhat-V*| <= ulp(Uhat)`, in m/s.
- `|dhat-d2| <= ulp(dhat)`, in m, where d2 below is the exact sum of the
  candidate's rounded operands.

Interpret ulps/halves as exact rational quantities, including subnormals; reject
nonfinite/boolean operands, overflow and invalid units/dimensions before work.
Require exact-zero results when the exact sum of the actual fsum operands is
zero: r0+Dhat+q for Xhat, v0+w for Uhat, or d2 for dhat. This is not a zero
requirement on R* using the unrounded v0*s; that target retains the product-plus-
sum error bound. Numerical zero of either sign is permitted. At exact halfway
fixture conversions and RN products require the even significand; the half-ulp
bound alone is insufficient to check ties-even. Retain signed errors, bounds,
component flags and vector norms, with explicit units. These new assembly checks
do not replace or relax the unchanged force gates. The one-ulp sum envelope is a
predeclared empirical acceptance criterion to be tested on the pinned build, not
a measured result or universal theorem. [Python's fsum documentation](https://docs.python.org/3.12/library/math.html#math.fsum)
warns that some builds can double-round. Verify cancellation/rounding boundaries
in preparation rather than assuming exact or correctly rounded sums universally.

Reconstruct P(hi),P(T) exactly from the saved Type2 words through the hash-pinned
pure [0153 polynomial helper](experiments/0153-real-ephemeris-oracle.py)
(`23915fee1feacca37f4a4c0f794feec177aac777407b9c87cc0f8176b0b4a6c8`).
Reuse compatible pure input/reference/finite-evidence utilities; do not modify
historical helpers or load old study/solver modules to access their arithmetic.
The new exact moving geometry must be independent of candidate assembly.

For each body retain four exact geometries and the original80/100-digit force
formula F(d)=mu*d/(sum(d^2)*sqrt(sum(d^2))):

- `eB=exact(Bhat)-P(hi)`.
- `d0=P(T)-R*`.
- `d1=P(T)+eB-R*`.
- `d2=exact(Bhat)+exact(c)-exact(r0)-exact(Dhat)-exact(q)`.
- `d3=exact(dhat)`.

Separately retain exact signed geometry errors
`e_source_increment=exact(c)-(P(T)-P(hi))` and
`e_drift=exact(Dhat)-exact(v0)*exact(s)`; require
`d2-d1=e_source_increment-e_drift`. Do not call this combined step only a
source-time error. Four force contributions are `F1-F0` (native source),
`F2-F1` (rephasing plus drift-product rounding), `F3-F2` (relative sum rounding)
and `ahat-F3` (field evaluation). Retain signed vectors and telescope their sum
to ahat-F0 at both precisions. Sum vectors before norms in model totals.

Use unchanged ADR0156 source/model returned-geometry and overall gates:
`||ahat-F3|| <= max(1e-15m/s^2,1e-11*S3)` and
`||ahat-F0|| <= max(1e-15m/s^2,1e-11*S0)`. Source Sk is its reference norm;
model Sk is the sum of constituent source norms. Include the full source floor
and drift errors in overall agreement; no subtraction or added allowance.
Require the original relative1e-60 reference convergence, zero handling, stable
80/100 classifications and telescoping checks. No integration tolerance changes.

Two diagnostic controls use the same binary64 force expression:
`flattened-craft: d=fsum(Bhat,-Xhat,c)` and
`omitted-q: d=fsum(Bhat,-r0,-Dhat,c)`. Compare only with F0 using its overall
force envelope; do not claim their returned-geometry qualification without more
reference fields. Real control failure or universal improvement is not required.
Before any field, check all d0..d3 and all three arms strictly outside each body's
frozen radius: Sun696000000m, Moon1737400m, Earth6378136.6m, including Earth for A.
An invalid domain stops the study; false diagnostic force gates alone do not.

### Preparation, bounded execution and saved-data audit

R5.12 is design only. R5.13 prepares the private assembly, independent moving
reference and separate saved-data auditor. Test analytic3D/zero/cancellation,
nonzero drift/q/w, sign and component-order mutations, omitted drift/q, rounded
elapsed versus exact s, product and sum ulp boundaries/subnormals, early absolute
flattening, source/time/GM/hash/domain/schema corruption, both force/precision
gates and full partial/count/deadline/exclusive-output paths. Mutations must fail
at least one named independent fixture; do not require all controls to fail at
all retained times. Run focused/full pytest, Ruff, strict OpenSpec and frozen
source/history checks before considering a retained run. Preserve tested hashes.

Only after verified preparation and authorization, R5.14 executes one fresh
stdlib-only study with one shared10s cooperative budget from an external
pre-child-start timestamp through imports/reads/hashes, computation, serialization,
flush and a post-flush check. Maximum attempted/completed counts are seven
six-state assemblies,21 source rows,168 Decimal fields (21*4*2),63 binary64 source
fields (21*3), and14 A/B totals. Count each operation and preserve ordered prefixes;
assembly precedes its time's Sun/Earth/Moon rows, then A/B totals. Count fixture
construction within its assembly and the shared process budget. No additional
force sampling or hidden reference profiles. Budget feasibility is unmeasured.

A separate fresh stdlib-only auditor gets its own10s and the same seven/21/168/63 /
14 caps. It independently rebuilds prescribed q,w, exact products/sums, candidate
terms, reference geometries, gates and counters from pinned raw operands; it
must not import candidate assembly/force code or trust saved flags. Sharing the
independent pure reference is allowed with its identity pinned, not described
as a second force-oracle implementation or independent ephemeris truth.

Both runs make zero scientific-library imports, native calls, kernel loads,
GM acquisitions, propagations, optimizer calls or R5 replays. Bind current tested
helper bytes and pinned Conda interpreter/build, recheck input/helper identities
before/after, and check scientific import absence. Save fresh exclusive finite
JSON with original identities/epochs, manufactured-input labels/ratios, all
attempted/returned raw state/geometry/field/model vectors, signed contributions,
per-component/force gates, precision/domain checks, ledgers, timings and earliest
failure. Retain completed fields/models before later callbacks can fail.
Finalization cannot leave a passed record after a late error. Complete success
requires all caps completed, every required gate and separate saved-data audit;
valid partial evidence remains partial, corruption rejected. No retry, extra
profile, operand/control/gate/budget change or failed-reference replay.

## Consequences and revisit conditions

This checks the moving-coordinate assembly boundary given binary64 corrections
and the retained real source records. It does not establish a corrected solver,
physical validity or uncertainty of those corrections, continuous safety, an
independent ephemeris, Earth-force trajectory sensitivity, historical R5 cause,
finite-burn/mission feasibility or strict M3/task3.9 closure. R5.3 stays failed;
automation stays PAUSED. A new solve requires a separate scientific contract.

If required arithmetic/domain/identity/budget checks fail, retain negative evidence
and diagnose the first boundary; never tune the fixture or tolerance to pass.
Any proposed changed operands/gates/budget or integration belongs in a separately
reviewed contract, preserving these records and all successful0155/0158 evidence.

## Evidence and verification

[Design checks](experiments/0159-verification.json) bind the six source artifacts,
exact initial six-state, saved epochs and absence of coepoch native data except
zero; they record links, protected-source/history digests, diff and strict OpenSpec.
No probe state, force field, integration or retained study was evaluated in this
stage. Prior5630 passing tests/Ruff remain unchanged evidence; they are not new
coverage for the unimplemented moving check and are not rerun for documentation.
