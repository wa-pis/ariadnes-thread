# 0175 — Design the paired lunar force check

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted design.
Implementation: R5.29 pending; R5.30 not run.
Verification: R5.28 archive identities, fixed observation mapping and documents checked.
Scope / milestone: M3 R5.28; lunar point-mass acceleration on 11 frozen coast observations.
Base revision: `b72ebc76998bb4399ffc0816229023ec8fcf6af1`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md),
[design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none.

## Context and constraints

[ADR0171](0171-frozen-coast-moon-screen-passes.md) passed both Moon gates
on the frozen sample, using a rounded model position for 21 rows.
[ADR0174](0174-record-geocentric-moon-proxy-misses.md) measured the missing
Moon/Earth states. Its parity and archived closure passed, but nine
position components differed by one binary64 step, at seven hi epochs.
Those states affect 11 distinct observations. Ask how much the point-mass
acceleration changes when only that position is substituted and whether
either original Moon gate changes verdict. The design uses the same
model and exact reference already retained by R5.24.

## Options considered

- Infer force equivalence from passing state parity or archived closure:
  these checks do not inspect the relative spacecraft geometry or force.
- Use a first-order bound: useful for scale, but it cannot reproduce
  the original binary64 evaluation or test its actual gate verdicts.
- Compare a proxy replay and measured substitution at the same 11
  states: chosen. The saved exact reference and both operands are
  available, so a new SPICE query, record evaluation or solve is unnecessary.

## Decision and rationale

### Frozen inputs and pairing

Bind the [input inventory](experiments/0175-inputs.json) to the finalized
[R5.24](experiments/0171-verification.json) and
[R5.27](experiments/0174-verification.json) evidence, including original
reports, journals, attempt markers and child and parent receipts.
Verify packed and raw R5.24 digests, capture-to-analysis receipt links and
the original input identities. R5.27 analysis exit 2 is the recorded
proxy-bit negative, with all rows, phase finalizations, state parity and
closure intact. Refuse incomplete capture, changed data or a substituted epoch.

In original R5.24 order, admit only ordinals
`1, 2, 4, 6, 11, 15, 16, 18, 20, 25, 27` (eight outputs and three RHS
observations). Join by exact binary64 hi bits and observation ordinal
to the full saved `spkezr("Moon", hi, "J2000", "NONE", "Earth")` return
in the R5.27 capture ledger. Confirm it against the paired analysis and
require at least one position bit miss per admitted row. Four epochs
each map to two rows; those rows keep separate motion. Only rows 11 and
25 have nonzero lo (negative and positive respectively). Exclude the
seven originally measured observations and the ten observations whose
proxy position already matches in every component.

### Geometry and two original force gates

Let `F` interpret a binary64 operand as an exact rational and `RN`
round to binary64, nearest-even, following the original zero convention.
Retain the row's exact coepoch `T=F(t0)+F(s)=F(hi)+F(lo)` and
`hi=RN(T)` in TDB seconds from J2000. Use the saved exact Moon/SSB
position `P(hi)` and `P(T)`; do not evaluate the record polynomials.
The fixed spacecraft states are
`X=F(r0)+F(v0)*F(s)+F(q)` and `Xhat=F(r0)+F(Dhat)+F(q)`.
Verify the saved signed drift `Dhat=RN(v0*s)` and rephasing
`c=RN(Vhat_B*lo)` bitwise, including signed zero, against the original
operands, and retain the `1e-12 m` rephasing increment norm gate
against `P(T)-P(hi)`. Keep the saved direct Moon/SSB velocity `Vhat_B`,
Earth/SSB position `E`, direct Moon/SSB state, `q/w` and all other motion
unchanged. In particular, do not rephase with the measured geocentric velocity.

Use archived proxy position `G_p` in one arm and the first three
captured state words `G_m` in the other, both in km. For each arm
`j` keep the following separations in SI:

- `d0=P(T)-X`, common to both arms.
- `d2_j=1000*(F(E)+F(G_j))+F(c)-Xhat`, assembled exactly.
- `d3_j=RN(d2_j)` componentwise. Do not round a barycentric centre
  sum before subtraction.

Require the exact identity `d2_m-d2_p=1000*(F(G_m)-F(G_p))`.
Require every evaluated separation to be strictly exterior to the
original `1737400 m` radius (exact squared norms, and finite exterior
binary64 norms for both returned geometries). Keep the original binary64
GM `4902800121846.8 m^3/s^2`. For each arm evaluate the original
binary64 field `A_j = mu*(d3_j/rho_j)/(rho_j*rho_j)` componentwise,
with `rho_j=hypot(*d3_j)`. Use an independent Decimal
`f(d)=F(mu)*d/(d·d)^(3/2)` at 80 and 100 digits, nearest-even, for
the shared `d0` and both arms' `d2` and `F(d3)`. This measures the
unrounded input effect without adding an intermediate force stage.

At each precision compare each `A_j` against its own `f(F(d3_j))`
(returned geometry) and the common `f(d0)` (overall). Keep the original
inclusive envelope `max(1e-15 m/s^2, 1e-11*norm(reference))` for each
reference. Keep the original 80/100 field convergence
(`norm(f80-f100) <= 1e-60*norm(f100)` with component zero agreement)
and require stable gate classifications. Require the proxy replay to
reproduce saved exact `d0/d2`, `d3` and acceleration bits, the saved
`d0/d3` reference fields within the same relative precision rule, and
both saved gate verdicts at both precisions before attributing changes.
A proxy replay mismatch invalidates the comparison.

### Report and decision gate

For each row keep the signed exact source step, both `d3` and `A`
bit vectors, signed exact `F(A_m)-F(A_p)` and its norm, both arms'
reference errors, envelopes and signed margins `limit - error` in
`m/s^2`, and any gate flip. At each precision, separate the signed
difference into:

1. Source position at unrounded geometry: `f(d2_m)-f(d2_p)`.
2. Differential separation rounding:
   `(f(F(d3_m))-f(d2_m))-(f(F(d3_p))-f(d2_p))`.
3. Differential binary64 field evaluation:
   `(A_m-f(F(d3_m)))-(A_p-f(F(d3_p)))`, with each `A` interpreted exactly
   before conversion to Decimal.

Their sum must reproduce the signed acceleration difference within
`1e-60` times the sum of the six endpoint field norms
(`f(d2)`, `f(F(d3))`, and `A` for both arms). This is an arithmetic
consistency check, not a new threshold on the measured force effect.
Report a source difference masked by rounding separately from a change
in returned acceleration.

A confirmed result needs all 11 valid pairs, all original measured-arm
gates passing at both precisions, valid precision and attribution checks,
and finalized evidence. A stable finite gate miss is a negative result;
retain later valid pairs. An ambiguous precision or attribution result
does not qualify the affected pair. Invalid input, proxy reproduction,
geometry, identity or deadline stops the run and records the available
prefix, earliest failure and unavailable work.

### Preparation and limits

R5.29 prepares a private stdlib-only runner and saved-evidence readback.
Verify analytic and synthetic fixtures for one-step changes, masked
rounding, duplicate hi with distinct motion, signed lo and zero, same
gate versus a flip, precision instability, input tampering, and partial
and exclusive evidence. Run focused tests, a no-SPICE guarded regression,
Ruff and strict OpenSpec; freeze tested and reused source hashes.
No force evaluation on the retained observations during preparation.

Only after verified preparation and a separate execution instruction,
R5.30 runs once in a fresh pinned offline process. Inclusive budget:
10 s for imports, archive reads, work, identity recheck, final flush and
receipts; parent watchdog 15 s. Attempt caps: 11 observation admissions,
22 binary64 fields and 110 Decimal fields (five separations times two
precisions times 11 rows). Count attempts before work. Retain an exclusive
attempt marker, finite raw pairs, ordered attempted/returned/completed
journal and hash-bound child/parent receipts. Verify the saved evidence
offline without repeating the study or adding field evaluations. Zero
native calls, new record acquisitions or record evaluations, other-body
force evaluations, propagations or optimizer calls. No retry or changed
sample, gate or input after the result.

## Consequences and revisit conditions

A pass supports only preservation of the two sampled Moon force verdicts
under this one substitution. A failure localizes the change to a row and
gate. Neither result changes the R5.24 conditional record or the R5.27
bitwise negative, repairs the failed R5.17 audit, or validates unsampled
epochs, Earth-force sensitivity, strict M3 or mission safety. Automation
stays paused.

## Evidence and verification

The input inventory pins 41 retained files, both uncompressed R5.24
digests and the 11-row mapping, including captured ledger indices and
canonical row and entry digests. A metadata-only readback verified the
finalized archives, identities, exact coepochs, preserved motion and the
two signed low words. The [verification manifest](experiments/0175-verification.json)
records strict OpenSpec, link, diff and protected byte checks. This stage
implemented and ran no study; there were zero SPICE calls, polynomial or
force evaluations and trajectory propagations. Runtime tests were not rerun.
