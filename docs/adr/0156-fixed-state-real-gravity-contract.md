# 0156 — Freeze a real-source gravity check at one retained position

Date: 2026-11-08
Decision status: accepted under the user's instruction to specify and commit the check.
Implementation: design complete; private implementation and execution not started.
Scientific verification: pending; no new force evaluation or propagation in this stage.
Scope / milestone: M3 R5.9, fixed-position point-gravity arithmetic only.
Base revision: `d5815fa3498cd73cc000bff7e40496272e1f4e9a`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [ADR0155](0155-real-ephemeris-time-boundary-passes.md), preserving all historical evidence and gates.

## Context and constraints

ADR0155 verifies compensation of source time against the same INPOP19a
polynomials. Its observed native position discrepancy reaches about11.4um;
this is neither astronomical uncertainty nor a universal error bound. Whether
that discrepancy and compensated relative assembly meet the inherited gravity
arithmetic envelope remains unverified. Do not infer a corrected solve or the
cause of the failed [R5 attempt](0148-short-coast-oracle-rhs-limit.md).

Only elapsed zero in ADR0155 matches an exact saved spacecraft epoch in ADR0148.
Pairing the other source samples with nearby1s/0.5s spacecraft grid points would
mislabel the epochs. R5 also deliberately uses the lunar harmonic-model GM as
its point coefficient; the different SPICE lunar GM in ADR0133 is not a replacement.

## Options considered

- Replay R5 or start a new corrected integration: reject here; confounds force
  arithmetic with unverified solver behavior and consumes a separate experiment.
- Interpolate saved spacecraft histories or construct a new drift trajectory:
  unnecessary for this question and would introduce additional operands/errors.
- Reuse the saved real sources with one unchanged saved spacecraft position:
  selected; zero native calls, no new trajectory, and an independent force check.

## Decision and rationale

### Frozen question, operands and model

Question: at one retained SSB position, do binary64 compensated source separations
and direct point-gravity fields agree with independent high-precision evaluation
of the selected ephemeris polynomials within the existing arithmetic envelope?
This is a fixed spatial probe at seven source times, not seven spacecraft states
on a trajectory. No target arrival or dynamical closure is tested.

Bind these immutable inputs; reject a digest mismatch before computing fields:

| Saved input | SHA256 | Required fields |
|---|---|---|
| [0136 boundary audit](experiments/0136-retained-boundary-audit.json) | `81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063` | `rows[0].stored_endpoint`, lunar `gm_m3_s2` |
| [0148 partial study](experiments/0148-short-coast-study.json) | `8bbe6f5f7d08f4e220ee3cff450488531da0776b8a69cb4c37e1c9af9872b096` | `inputs.initial`, `models.A.gm_m3_s2` |
| [0155 real source](experiments/0155-real-source.json) | `278b094cff6dd417ac15c04d3b4e4da137acede17de7147babd72fe9e3812102` | `t0_tdb_s`, `offsets_s`, all21 `rows`, selected records and raw returns |

Require exact endpoint equality between0136 and0148. Freeze its binary64 position
`X=(-47124635282.7281,128473304107.83153,55670397503.89886)m`
identically in all rows; retain its original epoch and velocity only as provenance.
No `v0*s`, correction state, interpolation or spacecraft propagation is introduced.
The full six-state remains unchanged; a stationary probe does not assert that the
spacecraft stays at X. The omitted drift/correction assembly remains unqualified.

Keep binary64 `t0=978995455.2304223` TDB seconds from J2000 and `u=ulp(t0)`.
Use exactly the saved offsets `0,u/4,u/2,3*u/4,0.05260015195876773,
150+3*u/4,300-u/4` seconds, in that order. Require the saved numeric/hex values
and exact rational identity `hi+lo=exact(t0)+exact(s)` to agree. Within each time,
consume the saved Sun,Earth,Moon rows; force sums use Sun,Moon[,Earth] order.
Positions/velocities are SI, origin SSB, orientation J2000, correction NONE.

Use the saved R5 coefficients, interpreted as their exact binary64 values:
Sun `1.327124400420322e20`, Moon `4902800121846.8`, Earth
`398600435468295.9` m^3/s^2. Require0136's lunar coefficient to match; do not
substitute ADR0133's `4902800205346.301` m^3/s^2 lunar value. For source C use
`F_C(d)=mu_C*d/||d||^3`; model A sums Sun/Moon, B adds Earth. These are the
existing restricted direct-SSB models, with no indirect-origin term. Other bodies,
harmonics, SRP/shadows, relativity, thrust and mass evolution remain omitted.

### Candidate and independent reference

For each saved source let Bhat,Vhat be its already-returned binary64 SI state
at hi. Preserve that conversion rounding; do not replace Bhat with polynomial
coordinates. Compute `c_j=RN(Vhat_j*lo)` and keep it separate from Bhat.
The private binary64 candidate uses `dhat_j=fsum(Bhat_j,-X_j,c_j)`,
`rho=hypot(*dhat)`, then `ahat_j=mu*(dhat_j/rho)/(rho*rho)`.
Sum source components with `fsum` in the frozen model order. Also compute two
labelled diagnostic controls: no c and wrong-sign c with the same recipe.
Never round Bhat+c into one large absolute coordinate before subtracting X.

Independently reconstruct P(hi) and P(T), `T=exact(hi)+exact(lo)`, from the
saved raw Type2 words with exact Fraction coefficients, chain sums and exact
km-to-m factor1000. Reuse only the hash-pinned pure [0153 polynomial oracle](experiments/0153-real-ephemeris-oracle.py)
(SHA256 `23915fee1feacca37f4a4c0f794feec177aac777407b9c87cc0f8176b0b4a6c8`);
check selected Sun10->0, Earth399->0, Moon301->399->0, frame1/Type2 and record /
segment coverage for both hi and T. Reconcile saved assessments with reconstruction
rather than trusting stored passed flags. No new SPK selection or kernel read.

Define exact rational geometries, retaining fractions through Decimal conversion:

- `d0=P(T)-X`: the same-polynomial exact-time reference.
- `eB=exact(Bhat)-P(hi)` and `d1=P(T)+eB-X`: source-discrepancy diagnostic.
- `d2=exact(Bhat)+exact(c)-X`: exact assembled candidate operands.
- `d3=exact(dhat)`: actual returned binary64 separation.

Evaluate each F(d0..d3) independently at80 and100 Decimal digits as
`mu*d/(sum(d^2)*sqrt(sum(d^2)))`. Convert binary64 via exact ratios or
Decimal.from_float, never display text; convert Fraction numerator/denominator
inside each precision context, never via a binary64 intermediate. The force
oracle must not import candidate force/assembly functions. Do not import0152 or
0153 study runners merely to read operands; they load scientific dependencies.
The source oracle shares ephemeris coefficients, not candidate force arithmetic.

Retain signed contributions `F(d1)-F(d0)` (native source discrepancy),
`F(d2)-F(d1)` (residual rephasing), `F(d3)-F(d2)` (relative assembly),
`ahat-F(d3)` (field evaluation). Their vector sum must telescope to
`ahat-F(d0)` within the stated precision-convergence scale. d1 is an algebraic
counterfactual, not another measured native state. Sum vectors before computing
model-total norms; never add component/contribution norms as signed attribution.

### Required gates and fail-stop semantics

Before each field, reject nonfinite/boolean operands, invalid GM/metadata/source
sets and zero separation. For each source C, each of its four reference geometries, actual candidate
and control separations must exceed that source's radius: Sun696000000m,
Moon1737400m or Earth6378136.6m. Check exact squared distances for all three
sources, including Earth for model A.
Historic moving-state minimum distances do not establish these fixed-probe guards.

Require80/100-digit vector agreement within relative1e-60 for every reference
field (zero must remain zero). Use the sum of constituent reference norms as
the precision/telescoping scale for totals. Retain precision differences and
require unchanged gate classifications at both precisions; ambiguity is failure,
not permission to tune. Decimal convergence is an arithmetic check, not a rigorous
interval bound or physical uncertainty estimate.

For every source and each of14 model totals independently require BOTH:

- Returned-geometry arithmetic: `||ahat-F(d3)|| <= max(1e-15m/s^2,1e-11*S3)`.
- Overall same-polynomial agreement: `||ahat-F(d0)|| <= max(1e-15m/s^2,1e-11*S0)`.

For a source, Sk is `||F(dk)||`; for a model total it is the sum of its individual
source norms, preserving cancellation. These are the unchanged
[ADR0143 arithmetic envelopes](0143-independent-saved-evidence-audit-contract.md),
not new integration/mission tolerances. The overall gate includes source,
rephasing, assembly and field errors: do not subtract eB, enlarge a bound, change
inputs/GMs/precision profiles, or call an arithmetic-only pass combined success.
Each control is compared only against F(d0) using its overall envelope. Its
returned-geometry arithmetic is not independently qualified within the168-field
cap. Control outcomes are diagnostics; a false control gate must not trigger
required-gate fail-stop. No universal improvement or mandatory real-force control
failure is presumed. Preparation
must nevertheless prove wrong-sign/omitted-source/rounding mutations detectable
on independent analytic fixtures, including zero and cancellation cases.

### Preparation, finite execution and evidence

This commit specifies R5.9 only. R5.10 preparation and R5.11 retained execution
are separate future stages; this design does not execute or mark either complete.
Reuse existing strict-input/exclusive-output and pure arithmetic utilities where
suitable, not a generic framework or new dependency. Before a retained run, test
analytic3D/central/zero/cancellation fixtures, exact operands and epoch signs,
both required gates and boundary/precision ambiguity, domain/source/GM/unit/hash
corruption, all ledgers/deadlines/partial paths, and a separate saved-data auditor.
Run focused/full pytest, Ruff and strict OpenSpec for implementation completion.

Freeze one future stdlib-only offline study with a shared10s cooperative budget,
from process start before imports through input reads/hashes, computation, output
serialization/flush and post-flush elapsed check. It may complete at most21
source rows,168 Decimal reference field evaluations (four geometries times21
rows times two precisions) and63 binary64 source fields (three arms times21).
Totals reuse contributions; no additional source sampling. Count attempted and
completed work separately. There are zero scientific-library imports, native
calls, kernel loads, GM acquisitions, spacecraft propagations or R5 replays.
The10s budget is predeclared, not measured feasibility or a hard interrupt guarantee.

Retain a fresh exclusive finite JSON result with original input/helper digests,
current pinned Conda interpreter identity, exact saved epoch/geometry/GM/record
operands, raw candidate/control vectors, four reference fields and signed errors,
source/model gate values, counters, elapsed times and earliest failure. New file
names must not overwrite any historical artifact. First unexpected required-gate,
identity/domain/count/deadline/output failure stops; downstream checks remain
unavailable. Finalization failure cannot leave an overall passed result; preserve
partial evidence where output remains possible. No retry or changed contract.

A separate stdlib-only saved-data audit gets its own shared10s including flush;
it makes zero native/scientific calls, reconstructs raw operands independently,
recalculates all available fields/gates/ledgers within the same168-reference-field
cap, and retains its own exclusive result. It must not import candidate force /
assembly functions or trust their flags. Complete success needs21 source rows,
14 model totals, both required gates, precision/domain/identity/count/time checks
and saved-data audit; a valid failed/partial record is not scientific success.

## Consequences and revisit conditions

This isolates the next boundary without another expensive integration. Reused
sources retain their historical ordered13-kernel identity; no current live kernel
pool is queried or certified. ADR0148 has no final identity snapshot; it supplies
frozen operands, not a newly verified trajectory. Current input/helper rehashes,
saved provenance assertions and scientific conclusions must remain distinct.

Any failure remains evidence, with exact signed attribution and no automatic
retry, tolerance relaxation, GM substitution or new state sampling. A subsequent
change needs a separately justified contract. Even success does not qualify
moving-spacecraft drift/correction assembly, a corrected adaptive solve, the
historical R5 failure cause, omitted-force sensitivity, astronomical ephemeris
accuracy, strict M3/task3.9, lunar escape/capture, fuel feasibility or mission safety.
Automation remains PAUSED; no R5 replay, optimizer or later-milestone work.

## Evidence and verification

Design-stage inspection confirms the three input digests, exact0136/0148 endpoint
equality, saved source schema/count and R5 GM map. The21 saved source offsets do
not supply seven matching spacecraft trajectory epochs. No force evaluation,
scientific import, body query or propagation was performed for this decision.
The design checks pass:14 new local links, four pinned input/helper digests,
21 saved exact epoch identities, endpoint/GM facts, seven-document change scope
and protected-history/diff checks, plus strict OpenSpec validation. No new force
errors are measured. Runtime/test/environment bytes remain unchanged;
reuse ADR0154's5409-test/Ruff pass, with no runtime test rerun for documentation.
Implementation verification, measured force errors, study and audit are pending.
