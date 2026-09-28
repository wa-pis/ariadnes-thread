# 0057 — Bind harmonic source arithmetic at the fourth endpoint

Date: 2026-09-14. Parent revision: `f1bee29`. M3 task 3.9 stays open.
Status: fixed-state source-arithmetic channel only, not full-force qualification.

## Decision and method

Reuse `_stored_harmonic_source_error_bound_m_s2` for the full Moon200 and
Mars120 fields at the actual fourth endpoint. The helper applies to a ball
about either a stored source or an ideal polynomial centre; clarify that
docstring without changing the mathematics or existing callers.

This caller centres the source ball on the live exact SPK position polynomial
from Decision0052. Its radius is the existing outward native-position L1
allowance, which also bounds L2. The already retained anchor readback must
lie inside that allowance. Do not replace the allowance by the smaller
observed residual. The relative centre is spacecraft minus ideal source,
formed with exact fractions from the actual fourth nominal spacecraft state.

Hold the NEW stored matrix A from Decision0055 fixed. The helper bounds the
operator norm by N=sum(abs(A_ij)), maps the source ball into the fixed frame,
and establishes a positive chord floor `|A r|_lower - N*source_error`.
It bounds the complete field Jacobian on that chord and returns
`N^2 * jacobian_bound * source_error` in m/s^2. Both factors of N are
required: the source displacement is transformed on input and force on output.
No exact orthogonality is assumed. Keep the conservative existing matrix norm;
do not silently replace it by a sharper bound in this step.

The earlier same-probe field checks still bind full degree/order, coefficient
hash, GM, normalization radius and C00. Retain those field and matrix digest
links, the exact relative centres as hex fractions, source allowances, epoch,
model, SPK context and actual nominal spacecraft state in one report.
No saved JSON is used as a runtime resource fallback.

## Composition boundary

This bounds the difference between native-source and ideal-source evaluation
of the SAME stored-matrix field at one nominal spacecraft state. Decision0056
separately changes that matrix at the ideal-source radius. These channels have
compatible intermediate states, but this step does not yet assemble a full
force ledger or claim its missing terms are zero. Native harmonic arithmetic,
prefix/tail enclosures, six point-source channels, light/relativity, carried
spacecraft errors and time variation remain distinct obligations.

The source allowance is conditional numerical representation error, NOT
astronomical observational uncertainty. Neither it nor the new force bound
is a mission-wide uncertainty estimate. No queries, vector evaluations or
spacecraft propagations are added. Shared timer and native counters remain.

## Verification

The [retained report](../../tests/data/m3_fourth_endpoint_harmonic_source_bridge.json)
gives outward acceleration L2 allowances 2.4557653639262546e-24 m/s^2
for Moon and 1.023753899662649e-8 m/s^2 for Mars. Source-position L1
allowances remain 8.934704095652991e-5 m and 0.0001648618821045329 m,
respectively. These are numerical channel bounds, not measured force errors.
The added calculation took 0.20778370811603963 s under the shared timer,
excluding prior resource/source/state/matrix work; no mission-cost guarantee.

36 focused source-bound controls pass in 0.61 s, including signed/zero
source shifts, scaled zonal fields, both matrix factors, invalid input,
unresolved chords and deadline rejection. Full pinned suite: 3217 passed
in 466.19 s; native/portable inventory 144.54 / 46.81 s. The suite is not
one 300-second mission calculation. Ruff, strict OpenSpec, whitespace and
unchanged legacy checksum/import isolation pass.

Prior matrix/force bridges, point/source anchors, domain/sensitivity,
resource-context, endpoint/reference/error, clearance, lineage and reuse
reports match Decision0056's full JUnit output, excluding timings only.
Counts remain 13 native / zero portable arcs and native harmonic requests/
misses/hits 14 / 4 / 10. The new report is absent in portable mode. Read-only
replay checks epoch/state/source/matrix digest and allowance links, exactly
reconstructs both relative centres, reloads pinned coefficients and reproduces
both force bounds bit-for-bit without spacecraft propagation.

Reproduce through the existing native SPK inventory test. Logs are under
`/private/tmp/ariadna-fourth-source-force-zhnLDX/full-suite.xml`. Production
code, coefficients, tolerances, caps and dependencies are unchanged.

## Next bounded step

Bind the six point-gravity source-arithmetic channels to this same endpoint
and exact source centres using their existing allowances. Then assess the
remaining anchor/rate budget before expensive vector work. Do not transplant
old native-force arithmetic, reset incoming errors, change tolerances,
start a fifth arc or open targeting. M3 and interval safety stay open.
