# 0026 — Bind the fresh native acceleration to the independent reference

Date: 2026-09-14. Parent revision: `64ad598`. M3 task 3.9 remains open.

## Reference before observation

Pin the retained common-force artifact from decision0022 by SHA256. Inside
the existing fresh probe, require exact agreement of its epoch, SSB/J2000
frame, model, nominal spacecraft state and mass with the evaluated state.
Retain its midpoint unchanged. Add the two freshly qualified full-field PCK
force allowances from decision0025 once to its existing L2 radius.
This changes the harmonic reference convention from stored matrices to
ideal PCK rotations at the exact ideal-source coordinates.

There is no second source bridge, harmonic tail or midpoint rounding term:
these are already included in the saved common-force total. Require exactly
one Moon and one Mars PCK channel. The live coefficients/matrices/epoch were
bound while deriving those channels; no new SPICE request is needed here.

## Bound the fixed-state native error

Use the already retained acceleration from the fresh derivative call as
an observation y, not as an independent force oracle. For the reference
midpoint m and its ideal-SPK/PCK radius R, compute all differences exactly
as Fractions and enclose d = |y-m|_2 with the existing dyadic square-root
helper. The triangle inequality gives

    |y - ideal_force|_2 <= d + R.

The numerical comparison includes the arithmetic effects present in this
observed native value at this one state. It does not separately certify
the native implementation over a state or time domain. Observed midpoint
distance d is not the actual error against the unknown ideal force, nor is
the conservative upper bound d+R a measured trajectory error.

Fourteen controls cover an attained aligned bound (including a large common
offset), zero and irrational distance, malformed/extra-category inputs,
negative/nonfinite/boolean allowances and deadline expiry. All 62 focused
comparison/midpoint tests pass in 0.51 s. Full suite: 3074 passed in 497.09 s,
native inventory 170.93 s, portable 56.58 s. Thirteen/zero arcs remain
unchanged. Ruff, strict OpenSpec, whitespace and legacy checksum/import
isolation pass. The comparison itself took 0.0001221 s in this run.

[Retained comparison](../../tests/data/m3_fresh_native_force_comparison.json)
matches captured output exactly. Original midpoint/radius, both PCK channels
and native observation match their existing diagnostics. The ideal-PCK
reference L2 radius is 7.838249091273487e-6 m/s^2. Observed midpoint distance
is at most 1.496686907541579e-8 m/s^2, giving a conditional native-error
upper bound of 7.853215960348902e-6 m/s^2. The reference uncertainty dominates;
do not report the smaller observed distance as the qualified force error.

## Provenance and next step

Report the midpoint, native observation, original radius, two PCK channels,
corrected reference radius, observed distance and native-error upper bound
with common state/model/time metadata. Preserve native counters and handoff.
The comparison timer is outside the harmonic sub-timer but inside the full
probe timer; do not add it again to the probe total. No additional query or
arc and no production, dependency, tolerance or limit changes.

Next use this fixed-state bound when constructing the next short reference
segment, preserving the incoming position/velocity error balls. Qualify the
fresh state/time domain and its force variation before claiming propagation
or safety. Do not silently reset incoming errors, transfer this single-state
bound across an interval, or close task3.9 from this comparison alone.
