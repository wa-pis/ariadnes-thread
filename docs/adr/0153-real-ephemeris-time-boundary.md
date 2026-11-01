# 0153 — Check compensated time against real ephemeris polynomials

Date: 2026-11-02
Decision status: accepted under the user's instruction to examine real data.
Implementation:90 focused tests pass; full verification failed on an unchanged300s test. Pending sources retained outside checkout, not committed.
Scientific status: real boundary acquisition NOT executed; full-suite prerequisite remains unsatisfied.
Scope / milestone: M3 R5.8, private ephemeris arithmetic only.
Base revision: `80e56acf2a9b40a7bc3cd298140bcba120106062`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes: none; follows [ADR0152](0152-compensated-synthetic-time-validation.md), preserving all previous evidence.

## Context and constraints

The synthetic compensation passes, but real sources accelerate and retain SPICE's
binary64 position floor. User asks to inspect real data. Preserve the R5 candidate,
initial state, epoch and original ordered13 kernels. Metadata inspection identifies
INPOP19a Type2/J2000 segments: Sun10->0, Earth399->0, Moon301->399->0.
This is not DE440. No state query or spacecraft integration informed this contract.

## Options considered

- Repeat failed R5 or change its tolerances/caps: reject; isolate the boundary first.
- Compare two ordinary SPICE calls or finite differences: insufficient at sub-ULP time.
- Evaluate the selected polynomial with exact rational arithmetic: selected; small
  degree10/12 records permit independent arithmetic without dependencies or a full
  SPK parser. Shared ephemeris coefficients do not constitute independent physical truth.

## Decision and frozen contract

Reuse the immutable0152 TwoSum implementation. Let t0 be the retained binary64
978995455.2304223TDBs and u=ulp(t0). Seven fixed binary64 elapsed times are
0, u/4, u/2, 3u/4, 0.05260015195876773, 150+3u/4, 300-u/4 seconds.
For Sun, Earth, Moon query exactly21 geometric states at hi=round(t0+s),
J2000/NONE/SSB; preserve both hi and lo=exact(t0+s)-hi as hex and numbers.
All conversion uses exact binary64 operands, never decimal display strings.
Keep the returned SI position and the correction V_hat*lo separate, rather than
rounding their sum back into a large absolute binary64 coordinate.

Use SPICE selection metadata for each centre chain at hi (at most28 selections),
read only three unique Type2 trailers/records (at most6 DAF array reads), and fail
on changed expected centre/frame/type, missing segment, invalid layout, nonfinite
values, or any hi/exact-time interval leaving the selected record or segment.
Independently evaluate position and derivative using Fraction.from_float,
Chebyshev recurrence and exact sums along the chain; km->SI exactly1000.
No native polynomial evaluator supplies the independent result.

For every one of21 states require SPICE versus exact polynomial at hi Euclidean
position error<=0.001m and velocity error<=0.000001m/s. Retain component errors.
Evaluate the exact displacement D=P(hi+lo)-P(hi). The separate binary64 correction
c_i=V_hat_i*lo must satisfy norm(c-D)<=1e-12m. Also require componentwise
|c_i-D_i| <= |V_hat_i-V_poly_i(hi)|*|lo| + A_i*lo^2/2 + |c_i-exact(V_hat_i*lo)|,
where exact rational A_i bounds the entire selected polynomial interval:
1000*sum_k |c_ik|*k^2*(k^2-1)/(3*RADIUS^2), summed along the centre chain.
The bound follows sup|T_k''|<=k^2*(k^2-1)/3 on[-1,1]; record both exact rational
bounds and measured errors. This is conditional on those pinned polynomial records,
not a bound on errors in the physical solar system. A wrong-sign correction must
fail the incremental1e-12m gate on at least one nonzero sample. Check quarter/tie
splits and immutable source identity in native-free unit tests first.

Retain the original position floor and total corrected absolute polynomial error
separately, with no claim of improved absolute source accuracy, force-field
suitability, integration efficiency, R5 causality, full-force fidelity or safety.
No spacecraft/force evaluation, GM read, optimization or propagation. No replay.

One retained acquisition/audit, no automatic retry or grid/tolerance adjustment.
Shared60s cooperative import/identity/query/exact-arithmetic/output budget; cap21
state reads/28 selections/6 array reads; before/after pinned identity snapshots.
These count explicit Python adapter calls, not internal CSPICE operations.
Additional descriptor-unpack/kernel-handle verification caps are28/3; no other state acquisition.
Finite exclusive evidence retains completed counters/rows on failure. Preparation
requires analytic exact polynomial/derivative/Taylor/chain/boundary/sign/cap/error
fixtures, focused/full pytest, Ruff and strict OpenSpec. After execution perform a
separate saved-data audit without native queries, preserving all earlier files.

## Consequences and revisit conditions

A pass qualifies only the sampled real-source time boundary under the same model.
A failure remains evidence; revise a separate contract before another acquisition.
Real force arithmetic, solver behavior and R5 replay remain unapproved/unverified.
Automation stays paused. Production and dependencies remain unchanged.

## Evidence and verification

Contract recorded before scientific acquisition. New preparation consists of a
stdlib Fraction oracle, private bounded acquisition/saved-row audit, and native-free
analytic, boundary, error, sign, counter, deadline, finite-partial and exclusive-output
fixtures. Installed API review corrected an unavailable DAF helper to kinfo and
verified all actual call signatures without native acquisition.90 focused tests and
Ruff/strict OpenSpec pass. Full pytest reports5408 passed/1 failed in975.78s.

The unchanged `test_loaded_spk_chain_coverage_contains_candidate_interval[native-readback]`
reached the existing300s wall-clock deadline while computing exact harmonic bounds,
with3 control attempts/3 propagation evaluations/3 native arcs. No numerical
mismatch was reported; this is not proof that its remaining checks would pass.
Source files and checkout status stayed frozen throughout full pytest;112 tracked
historical experiment/legacy files and all four pending sources retain their hashes.

Observed1-minute system load rose from11.96 to14.97; unrelated Tunnel/Yandex processes
used225.4%/103.5% CPU at one observation, on AC power. Contention is a plausible
explanation, not a demonstrated cause. Thermal status was unavailable. No process
was stopped and no timeout, tolerance or scientific contract was weakened.

The full-suite prerequisite failed, therefore real acquisition and offline real-data
audit have NOT run. No new study state/segment/GM/force/propagation calls occurred;
the full suite itself includes existing native tests. No retry performed. Automation
remains PAUSED; user was asked to reduce competing load before a same-limit rerun.

This is an evidence-only documentation stage, not completed implementation. Four
pending source/test files were hash-verified, shelved outside checkout, then removed
from the working tree; they are excluded from the commit. Their exact hashes, local
bundle/patch paths and patch digest are in the manifest. Restore those bytes before
subsequent implementation verification; do not recreate or modify scientific inputs.

Retained [verification manifest](experiments/0153-verification.json),
[focused log](experiments/0153-focused-pytest.txt), and
[full failure log](experiments/0153-full-pytest.txt).

Type2 layout, derivative velocity and record normalization follow
[NAIF SPK required reading](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html#Type%202:%20Chebyshev%20(position%20only));
[segment selection](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spksfs_c.html),
[descriptor unpacking](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkuds_c.html),
and [DAF array reading](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/dafgda_c.html).
