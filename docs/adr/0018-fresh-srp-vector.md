# 0018 — Enclose the fresh fully lit SRP vector

Date: 2026-09-14. Parent revision: `6ba1e35`. M3 task3.9 remains open.

## Minimal composition

Implement decision0016's signed solar-gravity scaling in
`tests/test_trajectory_srp_vector.py`. Reuse the existing rational pi bounds,
ideal-source Sun gravity intervals and midpoint/error helper. There is no
second source/radius calculation, native call, dependency or production API.

The multiplier is -L*area*Cr/(4*pi*c*mass*GM_Sun), with c=299792458 m/s.
All parameter values are exact Fractions of their finite positive binary64
inputs. Both rational pi endpoints bound the negative multiplier. For every
component, take the minimum and maximum of all four endpoint products; this
handles positive, negative, zero and sign-crossing intervals. Keep the result
as exact component intervals until outward diagnostic rounding.

## Fresh input binding

Load the existing gravity assembly inputs with their full hash/identity
checks, then pin the light snapshot and Sun GM record by SHA256. Require
common epoch 978995455.2929223 TDB s, SSB/J2000, physical model identity,
spacecraft state, mass, luminosity and PCK identity. Recheck all three exact
source-ball illumination predicates using retained coordinates/radii; do not
trust a stored boolean alone. No native shadow or ephemeris query is required.

The Sun gravity box already uses exact position polynomials. Therefore the
scaled SRP box shares the common gravity source convention. Do not add a
stored-to-polynomial source bridge again. The full-light proof covers these
ideal positions through the previously qualified position-error balls.
Parameters and nominal spacecraft state are fixed, not uncertain intervals.

Use the existing midpoint helper with zero additional tail. Its L2 allowance
covers the exact scaled box and final midpoint rounding. Outward component
serialization widths are also retained in the diagnostic; a later consumer
must not narrow them or subtract rounded widths to recover an exact box.

## Independent controls

Six signed/zero-component examples compare the exact L1 reduction with the
older direct radius/pi SRP formula, including irrational radius and nonzero
observations. Five controls exercise each parameter's factor-two scaling.
A sign-crossing example checks endpoint extrema, and simultaneous doubling
of GM and the solar gravity vector must cancel exactly. Twenty-five cases
reject nonpositive/nonfinite/boolean parameters; four reject invalid boxes;
two reject deadline expiry before/after the calculation. One pinned fresh
case checks illumination, identity, rounding and zero native counters.

The retained fully lit vector is not an observed native force residual.
No native total is used as its oracle, and the gravity-only result is not
modified or relabelled as full-force.

## Next step and limits

Audit and bind the already retained Sun velocity to its selected SPK velocity
representation and fresh guarded cores before applying Schwarzschild source
error bounds. Then expose/verify its signed vector with the old error API
preserved. PCK/native arithmetic, incoming state balls and time/domain closure
remain separate obligations. Task3.9 stays open; no coast or targeting change.

## Verification and retained result

All 79 focused SRP/midpoint checks passed in 0.50 s. Full pytest: 2990 passed
in 474.67 s; native inventory 151.39 s, portable 53.84 s. Existing thirteen/
zero arc assertions remain unchanged. Ruff, strict OpenSpec, whitespace and
legacy checksum/import isolation pass. No production/model/limit changes.

[Retained SRP result](../../tests/data/m3_fresh_srp_vector.json) matches the
full-run output exactly. Midpoint: (-2.109577885891017e-8,
3.0224630193524166e-9, 1.955172407918586e-9) m/s^2. Its outward L2 numerical
allowance is 5.890205713199613e-24 m/s^2 under the stated fixed-input and
full-light premises. This small arithmetic allowance is not a physical
uncertainty estimate for spacecraft area, reflectivity or solar luminosity.
