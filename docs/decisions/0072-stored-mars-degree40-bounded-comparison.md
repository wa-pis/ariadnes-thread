# 0072 — Degree-40 cost gap narrows, but no speedup yet

Date: 2026-09-15. Parent revision: `285a566`. M3 task 3.9 stays open.
Status: repeated stored-input comparison, not a full-force trajectory anchor.

## Decision and scope

Extend Decision0071's existing comparison to the already available degree-40
profile. Only its degree guard and report labels change; no recurrence,
precision, scientific tolerance, physical field, dependency or UI is changed.
Reuse the same historical snapshot at TDB epoch 978995455.2929223, SSB/J2000,
with pinned Mars coefficient/model/environment hashes. This is NOT the fourth
endpoint or a newly qualified reference state.

At each of 53/80/120 significant bits, three evaluations must return identical
intervals, contain the entire exact prefix and tail-expanded boxes, and retain
the exact same finite tail. The shared 300 s budget includes the three prior
unprofiled exact evaluations, one profiled exact evaluation, nine bounded
evaluations, coefficient loading and comparisons. Native coefficient loads
remain one; no ephemeris queries or native arcs are added.

## Focused evidence

The extended profile passed in 18.33 s. Its internal shared work took 17.67713 s.
Evidence: `tests/data/m3_mars_degree40_bounded_comparison.json`.

| Recurrence | Median prefix-plus-tail evaluation (s) | Prefix midpoint L2 bound (m/s^2) |
| --- | ---: | ---: |
| Exact Fraction | 1.003264 | Not newly reported |
| 53 bits | 1.302072 | 6.08976e-12 |
| 80 bits | 1.390497 | 5.38948e-18 |
| 120 bits | 1.487625 | 5.36247e-18 |

The bounded/exact timing ratios are about 1.30/1.39/1.48. This is still SLOWER,
although the gap is smaller than the earlier degree-20 observations. These
ordered local three-run medians do not prove a crossover at a higher degree,
or a speed advantage on another machine or state.

The 53-bit arithmetic bound grows from roughly 6.66e-15 at degree 20 to
6.09e-12 m/s^2 here. Bounded significands do not guarantee bounded interval
growth as degree increases. The much smaller 80/120-bit midpoint errors here
also reflect this particular vector's binary64 representability; they do not
establish monotonic improvement with degree or a general rounding floor.

The finite degree-41-to-120 tail remains 0.0020034676779043326 m/s^2 (reported
outward). It dominates the combined L2 bounds, approximately 0.00200346768
m/s^2. Count the norm-bounded tail ONCE outside the prefix box; preserve full
midpoint rounding. Source/PCK/native input allowances, other forces, model
uncertainty beyond degree 120 and trajectory error remain separate obligations.
No cutoff or precision is selected for the real mission.

Replay passed in 18.87 s. Full suite: 3485 passed in 486.55 s (native inventory
145.74 s, portable 46.36 s, extended degree-40 profile 17.55 s). The test count
is unchanged because an existing profile now checks additional evaluations.
All three precision cases match focused/replay/full-suite/retained data after
excluding timers only. Against the parent run, 19 selected native, 6 portable,
5 fourth-point audit, 1 subdivision, prior interval-jet and prior bounded-force
reports are unchanged. Previous degree-20/40/100 profile scientific values and
call counts, including the degree-20 bounded comparison, also match excluding
timers. Native/portable arcs remain 13/0; harmonic reuse remains 14 requests,
4 misses and 10 hits. Suite time combines independent tests, not one mission's
shared deadline. Ruff, strict OpenSpec validation and whitespace checks pass.
The legacy model remains unimported under `src` and retains SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Next step

Use the existing previously measured exact degree-100 reference for a limited
stored-input comparison, with an explicitly counted small number of bounded
evaluations under the same 300 s deadline. Report their actual cost and width;
do not infer success by extrapolating the degree-40 timings. This reuses an
already-running regression reference, not the known over-budget exact full
degree-120 vector. Do not add native arcs or transfer historical inputs to a
new anchor. M3 safety, the full error ledger and mission runtime remain open.
