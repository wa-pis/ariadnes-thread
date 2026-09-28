# 0052 — Reanchor covered source records at the fourth endpoint

Date: 2026-09-14. Parent revision: `e672c71`. M3 task 3.9 remains open.
Status: source-anchor prerequisite only; no new spacecraft reference or arc.

## Scope and method

The next spacecraft reference needs sources at 978995455.3554223 TDB seconds,
the retained fourth endpoint, rather than the old anchor at 978995455.2929223.
Reuse the eleven position records already selected for the guarded one-second
source interval. Re-evaluate their exact position polynomials and derivatives
with `_spk_position_affine_data` at the new epoch for a 0.125 s interval ending
at 978995455.4804223. No new record selection, kernel loading or ephemeris query.

For every link, explicitly check that the new interval fits the SAME record's
16-ULP guarded core. The record-wide curvature bound must equal the original
one. Exact Fraction comparisons bound the reanchor's position and slope changes
by curvature*offset^2/2 and curvature*offset respectively. Compose the existing
chains to SSB for all eight bodies and repeat these checks after composition.

Retain positions/slopes as exact hexadecimal numerator/denominator pairs,
with curvature and native arithmetic allowances alongside them. The source
context digest remains b00e888032a19081c8bbfd13ca73549af21224916ed997e4714fa68af7ce8cd5:
it identifies the same selected records/resources and their one-second covered
source domain, not a newly qualified spacecraft force vector.

The existing inventory already reads all eight native positions at this epoch.
Reuse those eight readbacks to check the new exact polynomial anchor against
the unchanged chain arithmetic allowances. Also reuse the Sun velocity readback
and its type-2 derivative allowance. Other slopes are derivatives of POSITION
polynomials, not a substitution for SPK type-3 stored velocity fields.

## Evidence and limits

All eight anchor comparisons pass. The largest observed position difference
is 0.00020471402783933218 m for Saturn; the Sun velocity difference is
3.6020604412106924e-16 m/s. These are conservative outward L1 reports of
numerical representation differences, NOT astronomical uncertainty estimates.
There is no new native readback at the interval's end; whole-interval source
coverage and curvature use the already qualified record/core argument.

Work added: eleven exact affine evaluations, eight reused position comparisons
and one reused Sun velocity comparison. Existing source readbacks remain forty;
additional ephemeris queries and native arcs are zero. Shared budget checks
remain in the polynomial evaluations and around report construction. No isolated
wall-time estimate is inferred for future harmonic or full-force evaluation.

The source epoch coincides with the fourth endpoint by the common exact
initial epoch plus 1/8 s; the next full-force consumer must still bind these
sources to the actual spacecraft state, force resources and new reference.
This result does not create that reference, supply its D/J channels, qualify
native stages or extend the numerical four-arc chain.

## Verification

23 focused SPK affine controls pass in 0.66 s; portable inventory passes
in 30.44 s. Full suite: 3217 passed in 508.00 s; native/portable inventory
157.05 / 50.63 s. The whole suite is not one 300-second mission calculation,
and these observations are not an isolated timing of the eleven new source
evaluations or an estimate of full-force reference cost.

The [retained native-mode report](../../tests/data/m3_fourth_endpoint_source_anchor.json)
is exactly equal across both full-suite modes and the focused portable run.
All 48 exact position/slope values round-trip through the hexadecimal format.
Read-only checks also bind its epoch to the saved fourth endpoint, its end to
the quarter-domain end and its source-context digest to the existing context.
Prior quarter-domain, carried-ball and force-sensitivity reports, source/force
contexts, endpoint/cubic/error/clearance data, all coast controls, exact lineage
and reuse counts match Decision0051's full output, excluding timing fields only.
Counts remain 13 native / zero portable arcs and 14 harmonic-error requests /
4 uncached evaluations / 10 hits. Ruff, strict OpenSpec, whitespace and legacy
isolation pass. No production model, thresholds, caps or legacy model changed.

Reproduce via the existing SPK inventory test or full pinned suite. Local
JUnit logs are under `/private/tmp/ariadna-fourth-source-YGjVYG`; the linked
JSON is retained evidence, not a runtime replacement for kernels.

## Next bounded step

Use these exact source anchors with the retained fourth spacecraft endpoint
to construct/check the inexpensive point-gravity portion of a fresh force
anchor. Keep Moon/Mars monopoles inside their harmonic fields exactly once.
Do not transfer the preceding harmonic native-arithmetic result or claim
a full-force error from point gravity alone. Qualify remaining anchor/rate
channels against the coupled budget before any new native propagation.
