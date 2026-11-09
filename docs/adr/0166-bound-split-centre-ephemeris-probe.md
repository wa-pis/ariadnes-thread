# 0166 — Bound the split-centre ephemeris probe

Date: 2026-11-09 (Europe/Samara)
Decision status: accepted design; live execution is not authorized by this record.
Implementation: R5.20 pending; R5.21 not started.
Scientific verification: pending; this stage verifies retained metadata and documents only.
Scope / milestone: M3 R5.19, three fixed lunar source epochs and static Moon-only acceleration checks.
Base revision: `0ee4d2d52472cc549bf43a452457b8fafc982e02`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [ADR0165](0165-reproduce-lunar-source-rounding.md), preserving the failed [ADR0164](0164-corrected-coast-force-gate-fails.md) result.

## Context and constraints

In R5.17 both A solves and all 21 trajectory comparisons completed. The sampled
Moon force gate failed at local 0.25 s. R5.18 reproduced 42 saved raw lunar
position components using a rounded model of the Earth and geocentric Moon terms;
the actual Moon/Earth return was never acquired. Check two distinct questions:
does the sum of the two **returned** legs reproduce the direct lunar position,
and does retaining the legs through relative subtraction pass the unchanged
static force gate at the failed state and the two controls?

Use the frozen R5.17 provider, kernel bytes, spacecraft operands, Moon GM and
force envelope. No trajectory integration, new initial state, optimisation,
kernel replacement, tolerance relaxation, Sun/Earth force or A/B comparison.

## Options considered

- Keep using the calculated geocentric term as a proxy: it cannot measure
  the actual Moon/Earth return.
- Query only the two legs and compare with archived Moon/SSB: cheaper by three
  calls but cannot check direct closure and historical reproducibility separately.
- Select three geometric states per epoch in one bounded capture, then perform
  all arithmetic offline: chosen. The direct query is a same-process control.
- Repeat a coast or qualify a new provider immediately: outside this question.

## Decision and rationale

### Frozen sample and reference

Use this order. Every row is from the normal R5.17 profile, with `lo=+0`, `hi`
in TDB seconds from J2000 and orientation J2000. No rephasing or new time samples.

| Role | Archived observation / row | Local s | Binary64 `hi` |
|---|---|---:|---|
| Failed force gate | observation 13 / RHS 6 | 0.25 | `0x1.d2d247fbd7e7ap+29` |
| Matching raw position control | observation 0 / output 0 | 0 | `0x1.d2d247f9d7e7ap+29` |
| One raw ULP but passing force control | observation 5 / output 5 | 250 | `0x1.d2d24fc9d7e7ap+29` |

For output rows use the archived node table for body returns and the normal
profile's output motion for `q` and `Dhat`. For RHS 6 both come from that saved
RHS. Preserve exact binary64 `r0`, `v0`, `q` and `Dhat=RN(v0*s)`; do not subtract
the exported rounded spacecraft position. Bind the [input inventory](experiments/0166-inputs.json)
and its archived compressed/uncompressed digests, including the partial audit.
It pins the saved per-epoch identifiers, initial state, all six returned
Earth/SSB and Moon/SSB components and both segment descriptors/record indices.

Reuse audited exact rational Earth/SSB and Moon/SSB position and velocity
at each `hi` from the three observations. Their exact difference is the
geocentric reference under the retained `301→399→0` chain (the Earth record
is identical in the standalone reference). Use the archived Moon `d0` geometry,
80/100-digit field and corresponding norm after verifying the exact geometry
below. No new polynomial evaluation or Type 2 array/record read. This is an
arithmetic reference to the same ephemeris, not independent astronomical data.

### Native capture and identity

In the fixed epoch order, capture these three [geometric SPICE states](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkezr_c.html)
with `spiceypy.spkezr(target, hi, "J2000", "NONE", observer)`:

| Label | Target | Observer | Position points from → to |
|---|---|---|---|
| E | `Earth` (399) | `SSB` (0) | SSB → Earth |
| G | `Moon` (301) | `Earth` (399) | Earth → Moon |
| B | `Moon` (301) | `SSB` (0) | SSB → Moon |

Retain every raw binary64 state in km/km/s, the finite returned light time in
seconds, and the call arguments and order before post-call checks. `NONE` does
not require light time to be zero. Archive all six state components; the
rounding hypothesis concerns position only. No Tudat SI state wrapper.

Before the first query and after the final selector, verify the actual ordered
13-kernel inventory (including paths/handles in the raw `kdata` ledger and
file digests in `kernel_metadata`), standard setup, pinned Python/TudatPy/
SpiceyPy/build/resource files, and tested helper/input bytes. Also compare the
resolved SpiceyPy `libspice_path` file to the current Conda CSPICE pin in the
input inventory, with no library replacement or override. This file pin is
new preflight evidence; R5.17 did not record that loaded library identity.
No SciPy/solver import is needed. Before/after snapshots bind this capture only;
they cannot repair the missing final identities in ADR0148 or ADR0164.

After all nine state reads, make two [segment selections](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spksfs_c.html)
per epoch in the same epoch order: `spksfs(399, hi, 128)` then
`spksfs(301, hi, 128)`. Verify the selected handle against
the INPOP19a entry already returned by `kdata` and the descriptor/label against
the archive. Decode the descriptor independently from its bytes and match
`399→0`/`301→399`, frame 1, Type 2, coverage, DAF addresses and retained record
index 12192 using the pinned trailer. Each of the three epochs is within
`[978739200,979084800)` for both retained records. No `spkuds`, `kinfo` or new
DAF reads are needed. The selections check applicable segments at these times;
they do not expose intermediate calls or values inside `spkezr`.

### Offline acceptance and static relevance

Use one fresh stdlib-only analyzer that validates the saved capture and receipt,
before doing numerical checks. Require E and B to reproduce all six archived
components bitwise at all three epochs (36 comparisons). Check each of E/G/B
against its exact retained reference using exact squared SI norms, position
`<=0.001 m`, velocity `<=1e-6 m/s`. A failed prerequisite prevents force
qualification. Record signed SI differences and per-component raw ULP offsets.

1. **Position closure.** For each position component require
   `RN(F(E)+F(G))` bitwise equal to B, where F preserves the exact binary64
   operand and RN rounds once to nearest-even. Report the 9 comparisons and
   signed residuals. Compare G to directly rounded exact geocentric position
   as a diagnostic only; neither velocity closure nor nearest-G bits are
   required to confirm the position hypothesis. In SI verify the exact sum of
   the two leg errors, `1000*(F(B)−F(E)−F(G))`, and `F(B_saved_m)−1000*F(B)`
   against the archived direct source residual. Here `B_saved_m` is the saved
   R5.17 rounded SI position. A finite closure miss is a result, not a reason
   to adapt the sample. Continue static force diagnostics if reproduction,
   parity, provenance, domain and budget prerequisites still hold.
2. **Static split assembly.** Interpret all following operands exactly until
   the explicit RN, using position components and metres. Let `X=r0+v0*s+q`,
   `Xhat=r0+Dhat+q` as exact sums of their displayed terms, and `P` be exact
   Moon/SSB in SI. Verify archived `d0=P−X`; set `d1=1000*(F(E)+F(G))−X`,
   `d2=1000*(F(E)+F(G))−Xhat`, and `d3=F(RN(d2))` componentwise. Do not round a
   barycentric sum, intermediate SI leg or spacecraft state. Fraction is
   sufficient for this private three-row diagnostic, not a runtime proposal.
   Retain the exact source, drift and relative rounding deltas and check
   the single RN including exact zero.
3. **Moon force only.** Before evaluating any field require strictly exterior
   Moon geometry for all four distances (`radius=1737400 m`). Use the saved
   binary64 `mu=4902800121846.8 m^3/s^2` and the ADR0162 field order on `d3`:
   `rho=hypot(*d3)`, `mu*(d3[j]/rho)/(rho*rho)` (with binary64 operands).
   Check that the binary64 `rho` is finite and strictly exceeds the radius.
   At 80 and 100 Decimal digits reuse the checked saved `a_ref(d0)` and independently
   evaluate the exact point field `a_ref` for `d1,d2,d3`. For returned geometry
   and overall compare the candidate to `a_ref(d3)` and `a_ref(d0)` respectively,
   with the unchanged
   envelope `max(1e-15 m/s^2,1e-11*norm(reference))`. Require 80/100 relative
   convergence `<=1e-60`, exact-zero agreement and stable classifications.
   Check signed force telescoping (source, drift, assembly, evaluation) with
   residual norm `<=1e-60` times the sum of four field norms at that precision.
   Include source error in the overall gate. No baseline field is reevaluated.

Full sampled confirmation needs valid finalized capture/analysis, position
closure 9/9 and both static force gates at all three points. Compare to the
unchanged saved direct baseline (fail/pass/pass); the two controls must still
pass but need not improve. Report closure and static force classifications
separately, even if one fails. Keep sampled negatives and explicitly mark
unavailable checks. A point pass cannot show a new 300 s integration would pass.

### Limits, partial outcomes and preparation

Only after R5.20 verification and separate execution instruction, R5.21 may
launch one capture and one offline analysis. Inclusive budgets are **15 s and
10 s** respectively, from external pre-child monotonic timestamps through
imports, input/library/kernel hashing, final flush and receipt checks. Parent
watchdogs (20 s/15 s) are emergency bounds, not acceptance limits.

| Count (including failed attempts) | Capture cap | Offline cap |
|---|---:|---:|
| Standard kernel setup | 1 | 0 |
| Inventory calls (`ktotal` + 13 `kdata` + Tudat count per snapshot) | 30 | 0 |
| `spkezr` state queries | 9 | 0 |
| `spksfs` selections | 6 | 0 |
| New Type 2 reads/evaluations, GM queries, propagations, optimiser calls | 0 | 0 |
| New binary64 / Decimal Moon fields | 0 / 0 | 3 / 18 |

This is 46 explicit setup/inventory/state/selector attempts at most, not a cap
on transitive native calls. Reject an unexpected inventory count before iterating.
Keep an ordered attempted/returned/completed ledger, finite exclusive outputs,
input/library/file hashes, startup/finalization times and earliest failure.
Preserve late returns before checking deadline. Fail closed on malformed data,
identity, bounds, coverage or budget failure, retaining the available prefix.
No retry, alternate provider, new epoch, or replacement of missing operands.

R5.20 implements private capture and separate analyzer only. Verify analytic
state and force fixtures, source/sign/epoch/order/descriptor/library/identity
mutations, binary64 cancellation and one-step rounding, parity/gate edges and
independent closure versus force outcomes. Test exact sample/count/time,
exclusivity, raw-return-before-check, partial and late-finalization paths.
Run focused/full pytest, Ruff, strict OpenSpec and protected-source checks and
freeze tested hashes before any R5.21 acquisition. Preparation fixtures use
injected sources or retained metadata for this probe.

## Consequences and revisit conditions

A positive result supports sampled closure and a private fixed-state numerical
diagnostic only. It does not reveal the native call's internal trace, bound
unsampled error, authorize production changes or prove trajectory convergence.
R5.17 remains failed; R5.3, Earth sensitivity, strict M3 and safety remain open.
No automatic continuation/retry; ariadna-m3 remains PAUSED.

## Evidence and verification

The [input inventory](experiments/0166-inputs.json) verifies three genuine
coepochs, fixed row/reference mapping, two Type 2 record intervals/addresses,
the INPOP19a digest and current installed Conda CSPICE file without loading
SPICE or evaluating any polynomial or force. The [verification manifest](experiments/0166-verification.json)
records finite JSON, local links, protected files, diff and strict OpenSpec.
Reuse unchanged R5.16's 6182 passing tests and Ruff; runtime tests are not rerun
for this design. R5.19 only; no probe implementation or live results.
