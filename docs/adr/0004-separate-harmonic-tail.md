# 0004 — Count the harmonic tail once in the midpoint norm

Date: 2026-09-13. Milestone: M3, task 3.9.

Status: accepted and verified bounded application; task3.9 remains open.

## Question and decision

The [previous midpoint contract](0003-local-harmonic-reuse.md) used a conservative
whole box. The native harmonic helper also provides an exact separate L2 tail.
Use that information during the already scheduled degree100 evaluation, without
another harmonic evaluation or propagation arc.

The helper constructs `(prefix_lo - tail, prefix_hi + tail)` using Fractions.
Undo only this exact expansion, verify an exact round trip, and apply
`sqrt(sum(e_i**2)) + tail`, where each `e_i` includes midpoint rounding and
distance to the corresponding prefix endpoints. Do not subtract the rounded
tail from historical JSON: that would not recover exact prefix intervals.

## Mathematical argument and checks

The exact prefix lies in its component box; its displacement from the rounded
midpoint has L2 norm bounded by the upward-rounded square root. The remainder
already has a vector-norm bound. The triangle inequality adds that bound once.
Independent rational direction/corner controls check squared errors, while
existing midpoint tests cover zero tails, nonrepresentable midpoints and invalid
inputs. Exact assertions verify identical midpoints, prefix/tail separation and
a strictly tighter bound than the whole-box form for these data.

## Numerical evidence

Base revision: `70add33`, pinned Conda `space-nav` environment. The committed
test change augments the existing isolated degree100 evaluation only.
Snapshot SHA256: `e401d88cbdd0110ac6c0357612b0053a34f87f8953856ac3372360e5ea3dca99`.
Frame: SSB origin, J2000 orientation, epoch 978995455.2929223 TDB seconds since J2000.

- Midpoint: (-3.149870347260298, 0.0032826169565977146,
  -0.005310257764904425) m/s^2, unchanged.
- Prefix plus midpoint-rounding L2 bound: 2.8705264613615397e-17 m/s^2.
- Prefix plus separate tail L2 bound: 7.82777879292353e-6 m/s^2.
- Whole-box bound from exact expanded intervals: 1.355811057972088e-5 m/s^2.
- Historical rounded-JSON whole-box bound: 1.3558110579856195e-5 m/s^2.

All reported bounds are outward rounded. The final two values differ because
the older JSON includes serialization rounding. The tighter bound preserves
known vector-norm information; it is not evidence of improved physical fidelity.

Reproduce focused verification from the repository root:

```sh
conda run -n space-nav python -m pytest -q -s tests/test_trajectory_harmonic_profile.py tests/test_trajectory_midpoint.py
```

## Limits and next step

[Verification evidence](../../tests/data/m3_separate_tail_midpoint_verification.json):
38 focused tests pass in 30.37 s; all 2823 tests pass in 475.24 s. Native
inventory takes 141.62 s with unchanged 13 arcs and 10 reuse hits. The isolated
degree100 test takes 24.40 s including checks; its harmonic evaluation alone
takes 24.304827166022733 s. These are observed costs, not runtime guarantees.
Ruff, strict OpenSpec validation and immutable legacy-file checks pass.

This qualifies only the stored-geometry Mars harmonic vector and its error.
Source-position/PCK uncertainty, the other bodies' gravity, SRP, relativity,
force variation and closed-domain premises remain separate obligations.
Keep all scientific tolerances, the shared 300 s deadline, full native controls
and task3.9 unchanged. Do not extend the coast or evaluate degree120.

Next compile a same-epoch full-force error ledger from existing evidence before
combining terms. WHEN a term is listed, THEN identify its epoch/frame/norm,
provenance and covered errors or mark the missing bound explicitly; no missing
term may be silently treated as zero or promoted from a different epoch.
