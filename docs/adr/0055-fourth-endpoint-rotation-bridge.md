# 0055 — Recompute the fourth-endpoint rotation bridge

Date: 2026-09-14. Parent revision: `bfb374a`. M3 task 3.9 stays open.
Status: dimensionless matrix qualification only, not a force-error certificate.

## Decision and scope

The ideal rotation-invariant harmonic-tail audit in Decision0054 cannot be
substituted into a stored-matrix vector calculation without bounding that
matrix's difference from the ideal text-PCK rotation. Reuse the existing
`_pck_angle_intervals_deg` and `_pck_matrix_error_bound` at the actual fourth
endpoint epoch, 978995455.3554223 TDB seconds since J2000.

The native inventory already validates the PCK pool, supported frame mapping,
absence of overriding models and file identity. Recheck the selected pool
digest and reuse those inputs. Read the live Moon and Mars rotation models
once each at the explicit new epoch; these are two additional rotation queries,
not ephemeris position queries or spacecraft propagations. Evaluate exact
polynomial/trigonometric angle intervals and compare each newly read matrix
with their ideal rotation enclosure. Do not transfer the previous epoch's
matrix, allowance or native force error. No saved JSON is a runtime fallback.

The existing matrix helper bounds the sum of absolute entry errors e, which
also bounds the Euclidean operator error. For ideal orthogonal R and stored Q,
the triangle and reverse triangle inequalities give, for every vector x:

`(1-e)||x|| <= ||Qx|| <= (1+e)||x||`.

Thus all singular values of Q are in [1-e, 1+e]. Check e < 1 and outwardly
round both endpoints with exact Fraction comparisons. This supplies a sharper
dimensionless operator upper bound and a positive lower stretch bound; it
does not assume Q is exactly orthogonal. Its transpose has the same singular
values. These statements do not yet quantify acceleration error from rotating
both inputs and outputs of a nonlinear harmonic field.

Report both matrices, entry-L1 allowances, singular-value/operator bounds,
epoch, frames, model ID and file/pool hashes together. Native mode emits the
report after validating the actual fourth-endpoint handoff; portable mode
does not invent that endpoint. Preserve the shared deadline and propagation
counters. One combined timer covers both angle and matrix calculations, with
no repeated shared-angle charge.

## Verification

The [retained report](../../tests/data/m3_fourth_endpoint_rotation_bridge.json)
gives dimensionless entry-L1 allowances 1.98899895618367e-13 (Moon) and
1.206005056117713e-11 (Mars). Their reported singular-value ranges are
[0.9999999999998009, 1.0000000000001992] and
[0.9999999999879399, 1.0000000000120604], respectively. The combined added
calculation took 0.4351144579704851 s under the existing shared timer;
this excludes prior environment/source/endpoint work, not a mission-cost bound.

49 focused PCK angle/matrix controls pass: 24 existing matrix/trigonometric/
resource controls in 1.61 s and 25 pure angle controls in 0.80 s. Full suite:
3217 passed in 488.91 s; native/portable inventory 152.21 / 48.75 s. The
suite is not one 300-second mission run. Ruff, strict OpenSpec, whitespace
and unchanged legacy checksum/import isolation pass.

Read-only comparison with Decision0054's JUnit output preserves all prior
source, point-force, domain/sensitivity, resource-context, endpoint/reference/
error, clearance, lineage and reuse reports, excluding timing fields only.
Counts remain 13 native / zero portable arcs, native harmonic requests/misses/
hits 14 / 4 / 10. The new report is absent in portable mode as required.
An independent exact rational Gram-matrix row-sum check of Q^T Q-I verifies
that each saved singular-value interval contains the corresponding Gershgorin
enclosure. This checks the reported bounds for stored Q, not its agreement
with the ideal PCK rotation, which is the separate angle/matrix argument.

Reproduce through the existing native SPK inventory test. This run's JUnit
log is `/private/tmp/ariadna-fourth-rotation-RG1uk8/full-suite.xml`. No new
force calculation, spacecraft arc, dependency or production code was added.

## Next bounded step

Use these same-epoch matrices and their dimensionless allowances with the
actual fourth spacecraft state, exact source positions and full Moon200/Mars120
coefficient identities to bound matrix-induced force error. Count C00 once;
keep source arithmetic and the carried state ball separate. Only after that
bridge and the remaining anchor/rate budget are assessed should a higher
harmonic prefix be chosen or timed. No fifth arc, targeting, new tolerance,
production acceptance change or interval-wide rotation certificate follows.
