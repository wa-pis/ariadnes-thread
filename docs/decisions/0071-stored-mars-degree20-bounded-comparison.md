# 0071 — Bounded Mars degree-20 comparison at the retained handoff

Date: 2026-09-15. Parent revision: `b53936a`. M3 task 3.9 stays open.
Status: stored-input arithmetic/cost comparison, not a new trajectory anchor.

## Decision and binding

Reuse the existing Mars degree-20 profile and its single pinned coefficient
load. Forward optional significand precision through the TEST-ONLY prefix
vector wrapper; the stored-matrix finite-tail calculation is unchanged.
No new physical formula, environment, ephemeris query or native arc is added.

Use `m3_fresh_harmonic_replay.json` at TDB epoch 978995455.2929223, SSB/J2000.
This is the HISTORICAL fresh handoff, not the current fourth endpoint at
978995455.3554223. The profile validates the snapshot model/environment hash,
Mars resource hash, coefficient-array hashes, shape, GM and normalization
radius. The new report links the same snapshot and coefficient hashes.
Do not transfer this result to a different state, epoch, matrix or reference.

## Checks and accounting

Compare three unprofiled repeats at each of 53/80/120 significant bits with
the existing exact result. Every repeat must be identical at each precision.
The existing exact run comprises three unprofiled evaluations plus one
profiled evaluation. All four exact and nine additional bounded evaluations,
coefficient setup, comparisons and reports share the same 300 s budget;
no timer is restarted. Native coefficient loads remain one and arcs zero.

Every bounded prefix box must contain the WHOLE exact prefix box, and every
tail-expanded bounded box must contain the exact tail-expanded box. Recover
prefixes only by undoing the helper's EXACT Fraction tail expansion, never by
subtracting its rounded JSON value. The finite tail must remain exactly equal
between methods. Existing independent signed-pole/scaled-matrix tail controls
also run at 80 bits; they check zero, retained and omitted degree-three terms.

Reuse the existing L2 midpoint helper, including binary64 midpoint rounding.
Keep the tail as a separate L2 contribution: combined bound is exactly
`prefix_midpoint_L2_error + tail`, not three copies of the norm bound.
The full finite Mars field here ends at degree 120. No assertion concerns
unmodeled degrees beyond that ceiling, source/PCK/native input error, other
forces or trajectory accuracy.

## Focused observations

All 28 focused controls passed in 5.70 s. The retained comparison is
`tests/data/m3_mars_degree20_bounded_comparison.json`.

| Recurrence | Median evaluation (s) | Prefix midpoint L2 arithmetic bound (m/s^2) |
| --- | ---: | ---: |
| Exact Fraction | 0.138614 | Not newly reported |
| 53 bits | 0.351017 | 6.65806e-15 |
| 80 bits | 0.377470 | 1.64051e-16 |
| 120 bits | 0.412854 | 1.64051e-16 |

Bounded arithmetic is about 2.53/2.72/2.98 times SLOWER at degree 20 in this
ordered local run. These medians cover complete prefix-plus-tail evaluations,
not just polynomial kernels; they do not predict a high-degree crossover.
The whole profile control including setup and all evaluations took 4.92090 s.

The unchanged finite-tail upper bound is 0.014624902702398076 m/s^2. Combined
L2 bounds remain approximately 0.0146249027024 m/s^2: omitted degrees dominate
this enclosure. The 80/120-bit midpoint-error values are mainly binary64
midpoint rounding even though their internal interval widths differ. None of
these observations selects a precision, truncation or physical allocation.

Replay: 28 focused tests passed in 5.88 s. Full suite: 3485 passed in
491.08 s (native inventory 149.91 s, portable 48.68 s). All three new precision
cases match focused/replay/full-suite/retained data after excluding timers.
Against the parent full run, all 19 selected native, 6 portable, 5 fourth-point
audit, 1 subdivision, prior interval-jet and prior bounded-force reports are
unchanged. The earlier degree-20/40/100 profile scientific values and call
counts also match after excluding timers only. Native/portable arc counts stay
13/0; harmonic reuse stays 14 requests, 4 misses and 10 hits. Suite duration
combines independent tests, not one mission's shared 300 s budget. Ruff,
strict OpenSpec validation and whitespace checks pass. The legacy model stays
unimported under `src` and retains SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Next step

Compare degree 40 using the already bounded existing exact profile, checking
both width and repeated evaluation cost before moving higher. Do not rerun
the known over-budget exact full-degree vector. A useful moderate-degree
prefix still does not establish a full-force anchor or viable mission budget.
Preserve all finite tails and source/PCK/native allowances in any later
physical composition. No model, UI, dependency, tolerance, reference family
or native partition is changed; M3 safety remains open.
