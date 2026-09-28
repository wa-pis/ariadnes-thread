# 0073 — Degree-100 speedup trades against interval growth

Date: 2026-09-15. Parent revision: `ea994bd`. M3 task 3.9 stays open.
Status: limited stored-input arithmetic comparison, not a mission force anchor.

## Decision and scope

Reuse the existing degree-100 exact evaluation and the shared comparison from
Decisions0071–0072. Add ONE bounded evaluation at each of 53/80/120 significant
bits, without a profiler or additional exact evaluation inside this test.
The existing degree-20/40 repetition counts remain unchanged. One 300 s budget
includes loading, the exact calculation, all three bounded calculations and
checks. No physical model, arithmetic recurrence, precision policy, acceptance
threshold, dependency or production code changes.

The pinned historical geometry is at TDB epoch 978995455.2929223, SSB/J2000;
resource, coefficient-array, snapshot and model hashes are retained. This is
not the fourth endpoint. Each bounded prefix and tail-expanded box contains
the ENTIRE corresponding exact interval, not just its midpoint. The exact
finite tail remains identical and is added once outside the prefix L2 bound.
Binary64 midpoint rounding is included. No native arcs or ephemeris queries
are added; one native coefficient load is reused.

## Focused evidence

The test passed in 50.36 s; internal shared work took 49.72059 s.
Evidence: `tests/data/m3_mars_degree100_bounded_comparison.json`.

| Recurrence | Single evaluation (s) | Prefix midpoint L2 bound (m/s^2) |
| --- | ---: | ---: |
| Exact Fraction | 22.156872 | Existing exact reference |
| 53 bits | 8.660870 | 0.0132360459142 |
| 80 bits | 8.918792 | 9.29801e-11 |
| 120 bits | 9.272126 | 2.87053e-17 |

The ratios are approximately 0.391/0.403/0.418: a local speedup in this
observation. The inherited JSON median fields contain singleton medians,
explicitly labeled as ONE observation per method, not repeated benchmark
medians. Separate verification runs test reproducibility, not a randomized
performance study or mission-runtime guarantee.

The 53-bit interval expands dramatically: its approximately 0.01324 m/s^2
prefix bound dominates the omitted-degree tail despite a plausible-looking
midpoint. This is a conservative arithmetic enclosure, not measured actual
force error. At 80 and 120 bits the unchanged degree-101-to-120 tail,
7.827778792894826e-6 m/s^2 reported outward, still dominates. The combined
bounds are respectively 7.827871773011379e-6 and 7.82777879292353e-6 m/s^2.
No precision is selected for production and no acceptance allocation changes.

Replay passed in 51.17 s. Full suite: 3485 passed in 519.71 s (native inventory
145.80 s, portable 47.76 s, degree-100 comparison 50.46 s). All three precision
cases match focused/replay/full-suite/retained data after excluding timers
only. Their shared work takes 49.72/50.50/50.46 s, respectively, below 300 s;
the full suite combines independent tests, not one mission's shared budget.
The existing test is extended, so the test count is unchanged.

Against the parent run, all 19 selected native, 6 portable, 5 fourth-point
audit, 1 subdivision, prior interval-jet and prior bounded-force reports are
unchanged. Original degree-20/40/100 profile science and call counts, including
both earlier bounded comparisons, match excluding timers. Native/portable
arcs remain 13/0; harmonic reuse remains 14 requests, 4 misses and 10 hits.
Ruff, strict OpenSpec validation and whitespace checks pass. The legacy model
remains unimported under `src`, with unchanged SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Next step

Consider a bounded-only full degree-120 stored-input evaluation after checking
its verification contract: retain the exact degree-100-plus-tail enclosure as
an independent coarse consistency control, and distinguish consistency from
an exact full-vector oracle. Do not rerun the known over-budget exact full
degree-120 vector. A higher degree can amplify interval dependency; measure
the actual width and cost under the unchanged deadline before using it.
Source/PCK/native input allowances, a fourth-endpoint binding, all other force
channels, reference transport and mission runtime remain separate obligations.
No new reference or native propagation is qualified by this comparison.
