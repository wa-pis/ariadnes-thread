# 0169 — Screen the split Moon source on frozen coast states

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted design for a conditional offline screen.
Implementation: R5.23 pending.
Verification: R5.22 metadata verified; R5.24 screen not executed.
Scope / milestone: M3 R5.22, Moon point force only, no propagation.
Base revision: `e2439b0726aff338b0e1ae6a94d94505d8330e07`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none.

## Context and constraints

[ADR0168](0168-real-split-centre-probe-passes.md) passed at three epochs with
zero low time word. It does not say what happens at other predeclared
states or when the retained rephasing term is nonzero. The [R5.17
archive](0164-corrected-coast-force-gate-fails.md) contains both completed
300 s solve histories, although the force audit stopped in the normal profile.
Ask whether the same split-position assembly clears the original lunar
force gates across the already fixed [ADR0162](0162-corrected-real-integration-contract.md)
sample, keeping time and motion unchanged. The consumed R5.17 verdict and
the original missing final identity remain explicit.

## Options considered

- Recheck only one positive and one negative low-word point: cheap but
  cannot screen the predeclared sample or its control profile.
- Query all missing lunar legs now: it would observe the provider, but
  might be unnecessary if the candidate already fails with an ideal
  rounded geocentric position.
- Screen all saved observations offline with actual legs where available
  and a labelled, correctly rounded model substitute elsewhere: chosen.
- Integrate another coast now: premature; even a positive screen leaves
  actual provider behavior unverified at the unsampled rounded epochs.

## Decision and rationale

### Frozen sample and source modes

Keep ADR0162's order: normal outputs 0–6, normal first completed RHS
ordinals 0–6, then the same two groups for tighter. Keep duplicate epochs
as separate observations with their own actual q/w and motion operands.
Read each output's source states from the shared node table and its motion
from its profile. Read each RHS's source and motion from that RHS. Bind all
28 rows to the [input inventory](experiments/0169-inputs.json), including
exact binary64 local s, hi, lo and the original initial state. The three
R5.21 epochs cover seven observations; their measured E/G/B states come
from finalized evidence and the E/B bits match the corresponding R5.17
returns. The other 16 hi epochs cover 21 observations and have archived E/B
but no actual G, where E = Earth/SSB, G = Moon/Earth, B = Moon/SSB. Keep the
modes separate in all reports. Do not call a modeled leg a SPICE return.

### Candidate, controls and independent reference

Use `F(x)` for the exact rational value of a binary64 operand and `RN` for
round-to-nearest, ties-to-even. For each row, verify
`T=F(t0)+F(s)=F(hi)+F(lo)` and `hi=RN(T)`. At hi and T evaluate the two
hash-bound archived degree-12 Type 2 records, Earth399→0 and Moon301→399 in
J2000. A private exact-rational recurrence with differentiated velocity
provides Earth and geocentric states and the exact Moon/SSB sum P and its
velocity. Require both epochs to be inside the stored record/segment
coverage. This is an arithmetic reference to the same INPOP19a data.
Do not open a SPK/DAF or query new ephemerides.

Use measured G at the three saved epochs. At each other hi, set the
geocentric position proxy to `RN(P_G(hi)/1000)` componentwise in km. Do not
use rounded Earth or Moon/SSB to construct the reference. Retain per-state
E/B parity against the exact hi reference with the original 0.001 m and
1e-6 m/s norm limits, and those limits for the measured G as well. The
rounded model G is a conditional input, not evidence of real-state parity.
Report `RN(F(E)+F(G)) == B` separately for observed and modeled positions;
a modeled closure is diagnostic and does not qualify a real return.

Make exactly one numerical change from the archived candidate: replace the
Moon barycentric position in relative subtraction by its two exact binary64
legs in km, scaled exactly to SI. Preserve the original signed Moon/SSB
rephasing product `c=RN(Vhat_B*lo)` using the saved rounded SI velocity
`Vhat_B`, and preserve `Dhat=RN(v0*s)`. Check both products bitwise against
the archive, including signed zero, and require the original 1e-12 m
increment envelope on `c-(P(T)-P(hi))`. Retain its signed Taylor, velocity
source and product-rounding terms. Do not switch to rephasing each leg,
alter q/w or use a flattened spacecraft position.

For each component, with vectors interpreted exactly except at explicit RN:

- `X=F(r0)+F(v0)*F(s)+F(q)`; `Xhat=F(r0)+F(Dhat)+F(q)`.
- `S=1000*(F(E)+F(G))`; `eB=S-P(hi)`.
- `d0=P(T)-X`; `d1=P(T)+eB-X`;
  `d2=S+F(c)-Xhat`; `d3=F(RN(d2))`.

Check the signed source, drift/rephasing and relative rounding telescope,
including `d2-d1 = F(c)-(P(T)-P(hi))-(F(Dhat)-F(v0)*F(s))`.
Require strictly exterior lunar geometry for each exact d0–d3 and the
finite binary64 d3 norm (radius 1737400 m). Use the original binary64
Moon GM 4902800121846.8 m³/s² and `mu*(di/rho)/(rho*rho)` on d3.
Compare with independent d3 (returned geometry) and d0 (overall) fields
at 80 and 100 Decimal digits. Each original gate remains
`max(1e-15 m/s², 1e-11*norm(reference))`. Include all source and assembly
error. Require relative 1e-60 convergence, exact-zero agreement, stable
gate classifications and the signed four-field contribution telescope
under the ADR0166 relative 1e-60 residual rule.

Match the three original ADR0168 observations' exact separations and
binary64 accelerations bitwise where represented in binary64, with the
same force verdicts and reference agreement at relative 1e-60. For the
14 original assessed R5.17 rows compare the saved direct overall results
where present (including the negative row), and label missing direct
results unavailable. No direct-arm recomputation or retroactive
completion of the R5.17 audit.

### Limits and decision gate

R5.23 prepares a private standard-library runner with independent analytic
polynomial/derivative and gravity fixtures, archive mutations, signed lo,
cancellation/tie/zero tests, preserved measured/proxy modes, controls,
gates and evidence failure paths. Verify focused/full pytest, Ruff, strict
OpenSpec, protected bytes and tested hashes before execution.

R5.24 runs once offline in a fresh process. The inclusive 10 s deadline
covers imports, archived hash checks, evaluations, final flush and
receipt; a 15 s parent watchdog is an emergency limit. Maxima: 28 rows,
29 distinct reference epochs (19 hi plus ten T values outside that set),
58 individual record evaluations including derivatives, 28 binary64 Moon
fields, and 224 Decimal Moon fields (28×4×2). Count attempts before work.
No native imports, queries, GM acquisition, new record acquisition,
Sun/Earth forces, A/B total, or solver calls. Retain finite exclusive raw
operands, per-row source mode, exact/reference terms, signed errors,
gates, counts, timings, finalized receipt and earliest failure. A
finite numerical miss is evidence: retain other scheduled rows if their
prerequisites remain valid. Stop at invalid input, identity, domain or
budget, marking unavailable work. Do not retry or change the sample.

## Consequences and revisit conditions

A valid pass needs all 28 rows within both Moon force gates at both
precisions, all required arithmetic/parity/identity checks, the three
measured controls and successful finalization. That supports only
conditional feasibility on frozen observations. The next eligible
decision would be a separate source-only holdout design for the 16
unmeasured hi epochs, with explicit authorization before live work.
A failed or incomplete screen does not advance to that design
automatically; report the failing row and term before proposing any
revision. Neither outcome qualifies a changed provider, proves uniform
error or solver behavior, reopens R5.17, or resolves R5.3/Earth
sensitivity, strict M3 or mission safety. Automation stays paused.

## Evidence and verification

The [input inventory](experiments/0169-inputs.json) verifies 28 saved
motion/source mappings, 19 exact epochs, both signs among ten nonzero
lo rows, measured source overlap, record coverage and archive hashes.
The [verification manifest](experiments/0169-verification.json) binds
those facts and documents checks. This design performs no new record
acquisition, polynomial or force evaluations, native queries or
propagation. The unchanged 6283-test/Ruff baseline is reused without
rerunning runtime tests.
