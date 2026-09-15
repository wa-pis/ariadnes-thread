# 0069 — Reuse the exact harmonic recurrence with outward intervals

Date: 2026-09-15. Parent revision: `3f9741c`. M3 task 3.9 stays open.
Status: low-degree polynomial/derivative enclosure, not force qualification.

## Decision

Extend the existing TEST-ONLY `_regular_solid_harmonic_jets` input contract
to accept either three Fractions or three same-precision dyadic intervals.
Keep its recurrence formulas and exact Fraction path unchanged. Mixed input
types/precisions are rejected. The old independent Rodrigues expansion tests
continue to check the formula; the new tests compare interval results with
that exact path instead of implementing another recurrence.

The small immutable interval type uses Decision0068 outward rounding after
addition, subtraction, four-corner multiplication, negation and division by
a positive integer. Squaring uses interval multiplication, conservatively
losing repeated-variable dependence. There is no interval division, square
root, normalization, force summation or production caller. Floats, mismatched
precisions and unsupported operations fail explicitly. Exponents and final
interval width are NOT globally bounded by the significand precision.

## Evidence

Four coordinate triples cover non-dyadic signed rationals, the stored binary64
values (0.31, -0.47, 0.83), the negative z pole, and the origin. For each, use
24/53/80/120 significant bits through degree 8. Each run checks all 45 terms,
both real/imaginary jets, and their value/dx/dy/dz components: 5,760 component
enclosures in total. Coordinates and outputs here are DIMENSIONLESS,
UNNORMALIZED polynomial quantities, not SI accelerations or relative force
errors. The origin is valid for polynomials, not for a singular gravity field.

For the binary64 nonpolar triple, maximum absolute interval widths are about
1.28125 (24 bits), 1.5425e-9 (53), 1.2360e-17 (80), and 7.8886e-30 (120).
Pole/origin controls have zero widths at this degree. The report also records
width/max(1,abs(exact component)); that diagnostic is not a relative-error
claim near a zero component and imposes no physical acceptance threshold.

In the focused run, exact recurrence evaluations took about 0.00089–0.00184 s
per point; bounded evaluations including input enclosure took about
0.0143–0.0340 s per point/precision. Thus this implementation is SLOWER at
degree 8. These are single-run observations, not benchmark medians or
extrapolated high-degree costs. Exact-oracle timings exclude interval
construction; rounded timings include it. Comparison/assertion/report work
is outside those per-evaluation timers but inside the shared 300 s budget.
No native arcs or ephemeris queries are added.

Sixteen signed/zero-crossing box controls check arithmetic against exact
corners and midpoints; eight cases check rejected inputs/operations. Two
mixed-coordinate cases and an injected-clock control verify rejection and
the existing between-row deadline checks. The focused run passed 106 tests
in 1.14 s, including the old Rodrigues and deadline/rejection controls.
Machine-readable focused evidence is retained in
`tests/data/m3_low_degree_interval_jets.json`.

Replay of the rounding/interval files: 99 passed in 1.15 s. Full suite:
3442 passed in 461.18 s (native inventory 141.51 s, portable 46.54 s).
All 16 new scientific cases match focused/replay/full-suite/retained data,
excluding elapsed timers only. Compared with Decision0067's retained full
run, all 19 selected native, 6 portable, 5 fourth-endpoint audit and 1
subdivision reports are unchanged after excluding timers only. Native/portable
arc counts remain 13/0; harmonic reuse remains 14 requests, 4 misses, 10 hits.
The full suite comprises independent tests, not one mission's 300 s budget.
Repository-wide Ruff, strict OpenSpec validation and whitespace checks pass.
The legacy model remains unimported under `src` and its SHA-256 is unchanged:
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Remaining obligations

Before claiming a cheaper anchor, qualify LOW-DEGREE normalized force assembly
against the existing exact oracle, including positive radial division and
square-root enclosures. Then measure a bounded moderate-degree case. Retain
all source/PCK/native arithmetic and input-error charges separately. Do not
extrapolate these polynomial widths to a full Moon/Mars acceleration, select
a truncation/reference, or repeat the known over-budget exact full-degree
evaluation. No native partition, production model, UI, dependency, tolerance
or allocation is changed. M3 safety and mission-scale runtime remain open.
