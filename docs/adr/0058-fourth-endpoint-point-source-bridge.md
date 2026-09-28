# 0058 — Bind six point-source arithmetic channels

Date: 2026-09-15. Parent revision: `d90ef67`. M3 task 3.9 stays open.
Status: fixed-state point-force source channel, not a complete force ledger.

## Decision and method

Complete the source-arithmetic counterpart of Decision0053's six nominal
point forces using existing exact source anchors, GMs and actual fourth
spacecraft endpoint. Reuse `_point_mass_variation_bound_m_s2`; no new force
model, numerical tolerance or dependency is introduced.

For each source, form the exact relative centre (ideal source minus nominal
spacecraft). The existing L1 source-position arithmetic allowance epsilon also
bounds L2. Check the retained native anchor residual is inside that allowance,
but never use the smaller observed residual as the allowance. Obtain a lower
radius with the existing rational square-root enclosure, subtract epsilon,
then round downward. Require d>0 and exactly verify `(d+epsilon)^2 <= |r|^2`.
Thus the complete source ball and every comparison chord avoid the singularity.

The ideal point-gravity Jacobian has operator norm at most 2*GM/d^3 there.
Multiplication by epsilon gives an acceleration L2 error bound. Exact Fraction
arithmetic carries the formula through to an outward binary64 report. This is
an ideal-force change due to source representation only; evaluating that force
in native floating-point arithmetic is a different error channel.

The six sources are Sun, Mercury, Venus, Earth, Jupiter and Saturn. Moon and
Mars remain exclusively in Decision0057's harmonic-source channel. Assert the
source sets match the six nominal point intervals, preventing double counting.
Retain the exact relative centres as hex fractions, GMs, source allowances,
chord floors, epoch/state/model and SPK context together. Input data come from
the same live inventory; retained JSON is not a runtime ephemeris fallback.

## Scope

No ephemeris query or spacecraft arc is added, and shared budget checks surround
the six calculations. Portable mode does not invent the native fourth endpoint.
No changed native limits or numerical gates. Source arithmetic is conditional
numerical representation error, not astronomical uncertainty. The resulting
bounds do not cover spacecraft state uncertainty, native force arithmetic,
other force components or variation over the proposed future time interval.

## Verification

The [retained report](../../tests/data/m3_fourth_endpoint_point_source_bridge.json)
contains all six outward acceleration L2 allowances. The largest is Sun:
2.5261704864652886e-21 m/s^2. The other bounds range from
2.4504967715198563e-25 (Mercury) to 2.15034593034798e-22 (Jupiter)
m/s^2. These small source-channel bounds do not imply equally small total
force or trajectory errors. The added calculation took 0.0003039159346371889 s,
excluding prior resource/source/state work; no mission runtime guarantee.

8 focused variation controls pass in 0.56 s: signed and zero radial changes,
an exact transverse change and singular-chord rejection. Full pinned suite:
3217 passed in 465.47 s; native/portable inventory 144.62 / 46.90 s. The
suite is not one 300-second mission run. Ruff, strict OpenSpec, whitespace
and unchanged legacy checksum/import isolation pass.

All prior harmonic-source, rotation/force, point/source anchor, domain/
sensitivity, resource-context, endpoint/reference/error, clearance, lineage
and reuse reports match Decision0057's full JUnit output, excluding timing
fields only. Counts remain 13 native / zero portable arcs, native harmonic
requests/misses/hits 14 / 4 / 10. The new report is absent in portable mode.
Independent read-only Fraction replay checks epoch/state/source/GM/allowance
links, reconstructs all six exact relative centres, verifies positive floors
and their squared chord inequalities, then reproduces each outward result
directly as 2*GM*epsilon/d^3 without invoking the bound helper.

Reproduce through the existing native SPK inventory test. Logs:
`/private/tmp/ariadna-fourth-point-source-xuaqbO/full-suite.xml`. Production
code, coefficients, tolerances, caps and dependencies are unchanged.

## Next bounded step

Audit the same-epoch ledger of available anchor channels and explicitly missing
native harmonic/vector, light/relativity and rate terms. Assess the coupled
remaining error budget before selecting or timing a higher-degree prefix.
Do not treat these source bounds as a complete anchor, reuse old native-force
errors, reset carried radii, add a fifth arc or change production acceptance.
