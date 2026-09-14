# 0022 — Compose the three fresh force groups

Date: 2026-09-14. Parent revision: `22d3a61`. M3 task 3.9 remains open.

## Common fixed-state target

Compose the retained gravity, fully lit SRP and PPN=1 Sun Schwarzschild
results from decisions0015, 0018 and 0021. Their source convention is exact
position polynomials; the Sun velocity is its qualified type2 derivative.
The lunar/Martian harmonic matrices remain fixed stored binary64 matrices.
This is a coast control at the fixed nominal spacecraft state and mass,
not an active-engine calculation or a spacecraft uncertainty domain.

Pin all three result artifacts by SHA256. Pin the light and harmonic replay
inputs too, and require their epoch, SSB/J2000 frame, spacecraft state, mass
and PCK identity to agree. Check the source/matrix conventions and three
full-light flags explicitly. These are retained qualified inputs, not new
ephemeris or native force measurements. During full verification, compare
the producer diagnostics to the retained inputs as well as the new sum.

## Exact sum and error accounting

`_force_group_midpoint` accepts exactly gravity, srp and schwarzschild.
Each supplies a finite binary64 vector and nonnegative L2 allowance.
Convert components and allowances exactly to Fractions and sum each axis
before rounding. Reuse the existing midpoint helper on the singleton sum
to bound its final binary64 rounding. Keep four named error channels:
the three unchanged group totals and the final midpoint rounding.

By the triangle inequality, the sum of those radii encloses the common
ideal force vector around the reported midpoint. Do not sum the groups'
displayed subchannels as well: the gravity total already includes harmonic
tails and source bridges; the Schwarzschild total already includes its
Sun source-state bridge. SRP uses ideal Sun positions directly. No channel
is inferred by subtracting rounded diagnostic quantities.

## Checks and next step

Cancellation controls include 2^60 + 1 - 2^60 and signed error-ball offsets.
A 2^-54 addition checks nonzero final midpoint rounding. Seven invalid-input
cases reject missing/extra groups, negative/nonfinite/boolean errors and bad
vectors. Two deadline cases and the pinned fresh case complete thirteen new
tests. All 71 focused composition/midpoint tests pass in 0.51 s; Ruff passes.
Full suite: 3029 passed in 473.75 s, native inventory 152.97 s, portable
50.68 s. Existing thirteen/zero arcs and forty readbacks remain unchanged.
Ruff, strict OpenSpec, whitespace and legacy checksum/import isolation pass.
All three producer diagnostics exactly match their pinned input artifacts.

[Retained sum](../../tests/data/m3_fresh_force_assembly.json) also matches
captured output exactly. Midpoint is (-3.1477509045315113,
0.0029787932997721, -0.0055067603918823125) m/s^2. Its outward conditional
L2 allowance is 7.838016334890343e-6 m/s^2; final midpoint rounding adds
5.254174618261198e-17 m/s^2 to the three retained group totals. Gravity
dominates this allowance. This is a numerical enclosure, not a measured
trajectory error, physical uncertainty or full native-force certificate.

No production code, dependency, query, propagation arc, limit or scientific
tolerance changes. Next qualify the fresh PCK matrix-to-ideal rotation bridge
and bind the retained native acceleration to this independent reference.
Do not reuse old-anchor PCK angles at the fresh epoch or call an observed
native residual an independent force oracle. The incoming position/velocity
error balls and time-domain closure are still open, and no trajectory safety
or mission accuracy follows from this fixed-state assembly.
