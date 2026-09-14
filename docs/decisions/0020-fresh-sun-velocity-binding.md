# 0020 — Bind fresh cached Sun velocity to its series

Date: 2026-09-14. Parent revision: `8635c44`. M3 task3.9 remains open.

## Reuse existing inputs and arithmetic

Extend the existing SPK inventory, not production code. Require the single
overlapping Sun segment to be type2 with center0, preserving the existing
frame1 assertion. Pin its kernel SHA256 from decision0019 and report the
record midpoint/radius, 16-ULP guard and fresh epoch. Existing exact checks
require the original one-second interval and fresh following 1/16 s to fit
the same unique guarded core. A type3 substitution fails before identifying
the position derivative with physical velocity.

Keep all six components from the existing `spkssb` call instead of discarding
velocity. At the fresh epoch, compare the Sun's binary64 SI velocity to the
exact rational derivative already computed from this type2 position series.
Its L1 residual must not exceed the existing uniform Sun-chain velocity
allowance. That allowance covers normalization, differentiated-series
evaluation and km/s-to-m/s rounding; the one-link Sun chain has no center
addition. No new allowance is inferred from the observed residual.

Pass that retained velocity into the existing full-force probe. The cached
Sun velocity after its fresh derivative evaluation must match exactly, then
independently satisfy the same rational residual inequality. Report its full
state, common epoch/SSB/J2000/model, allowance, outward-rounded observed
residual and zero additional native query/arc counters. This closes the
previous readback-only velocity prerequisite without a new state request.

## Limits and next step

This is a conditional supplied-record arithmetic bridge, not ephemeris
uncertainty from observations or a bound on the Schwarzschild acceleration.
The fixed nominal spacecraft state is not replaced with an uncertainty ball.
The light snapshot remains an immutable historical input; its readback-only
wording describes its original scope, superseded only by this separate check.

Next expose the signed Schwarzschild vector using the existing exact-radius
formula and retain its old error API as a control. Apply the qualified Sun
position/velocity source allowances once when changing from stored Sun state
to the common ideal-source convention. PCK/native force arithmetic, incoming
state balls and time/domain closure remain open; no full-force or targeting
certificate follows from this velocity check.

## Verification

The 109 focused type2/type3 velocity and Schwarzschild controls pass in
0.61 s. Full suite: 2990 passed in 473.27 s, native inventory 152.86 s,
portable 50.87 s. Existing thirteen/zero arc assertions and forty position
readbacks pass unchanged. Ruff, strict OpenSpec, whitespace and legacy
checksum/import isolation pass. No production/model/tolerance/limit change.

[Retained result](../../tests/data/m3_fresh_sun_velocity_binding.json)
matches the two captured full-run diagnostics exactly. The conditional
L1 velocity allowance is 6.9538963374104784e-15 m/s; the outward observed
L1 residual is 8.779188700062134e-16 m/s. The former is the existing uniform
arithmetic bound, not the observed residual inflated into a new bound.
The full Sun state matches the historical light snapshot exactly.
