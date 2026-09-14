# 0056 — Convert fourth-endpoint matrix error to force error

Date: 2026-09-14. Parent revision: `21d3646`. M3 task 3.9 stays open.
Status: one fixed-state force-error channel, not a full-force certificate.

## Decision and method

Decision0055's matrix errors are dimensionless. Reuse the existing
`_stored_matrix_force_error_bound_m_s2` to bound their acceleration effect
at the same fourth endpoint, without new rotation or ephemeris queries.

For each body, reconstruct the exact source position from the live reanchor
report and subtract it from the actual fourth spacecraft position using
Fractions. Retain the exact squared radius as hexadecimal numerator and
denominator. Bind the field to its validated coefficient hash, GM, normalization
radius and complete degree/order (Moon200, Mars120); verify C00=1 is present.
The new vector prefix is not evaluated, and no coefficients are discarded.

For stored matrix A and ideal orthogonal Q with ||A-Q|| <= e < 1, reuse the
split `(A-Q)^T g(Ar) + Q^T [g(Ar)-g(Qr)]`. The full straight chord from Qr
to Ar stays outside `(1-e)|r|`; the helper outwardly bounds the field norm
and spatial Jacobian there. The resulting Euclidean acceleration-error bound
is `e * (acceleration_bound + jacobian_bound * radius_upper)`, in m/s^2.
Do not omit C00: unlike two ideal rotations, a nonorthogonal stored matrix
can alter the monopole. Do not cap this error by a pure-rotation estimate.

Use the NEW reported matrix allowance, already outward rounded. Link each
force record to the complete corresponding matrix report with its normalized
JSON SHA256, plus the epoch/model, PCK pool/file and SPK context identities.
Retain the actual spacecraft state. This is same-probe consistency, not
external authentication. Saved JSON never substitutes for live resources.

## Scope

This bounds only replacing the stored matrix by the ideal text-PCK rotation
at the exact ideal-source radius and fixed nominal spacecraft state. Source
position arithmetic, native harmonic arithmetic, prefix/tail enclosure,
carried spacecraft errors, light/relativity and force variation over time
remain separate obligations. Do not add a dimensionless matrix error directly
to acceleration, or count this channel twice in a later ledger.

Both computations use the existing shared timer. No new rotation query,
ephemeris query, vector evaluation or spacecraft arc is added; the preceding
matrix bridge's two rotation queries remain separately recorded.

## Verification

The [retained report](../../tests/data/m3_fourth_endpoint_rotation_force_bridge.json)
gives outward L2 acceleration allowances 7.969250975249056e-23 m/s^2 for
Moon and 1.5697109459316845e-10 m/s^2 for Mars. These are bounds for this
specific matrix-error channel, not observed acceleration discrepancies or
the full anchor error. The added calculation took 0.2707736250013113 s,
excluding earlier resource/source/endpoint/matrix work; no runtime guarantee
or mission-scale estimate follows.

18 focused matrix-force controls pass in 0.58 s, covering nonorthogonal
dilation, proper rotation, monopole scaling, invalid bounds and deadlines.
Full pinned suite: 3217 passed in 464.56 s; native/portable inventory
143.76 / 46.61 s. The suite is not one 300-second mission calculation.
Ruff, strict OpenSpec, whitespace and unchanged legacy checksum/isolation pass.

All prior rotation, point-force, source, domain/sensitivity, resource-context,
endpoint/reference/error, clearance, lineage and reuse reports match the
parent JUnit output, excluding timing fields only. Counts remain 13 native /
zero portable arcs and native harmonic requests/misses/hits 14 / 4 / 10.
The new force report is correctly absent in portable mode. Read-only replay
checks its epoch/state/source/matrix digest links, exactly reconstructs both
squared radii from the retained source/endpoint, reloads the pinned coefficient
files, and reproduces both force allowances bit-for-bit without native arcs.

Reproduce with the existing native SPK inventory test. Full JUnit evidence:
`/private/tmp/ariadna-fourth-rotation-force-1fWoZw/full-suite.xml`. Production
code, coefficients, tolerances, native caps and dependencies are unchanged.

## Next bounded step

Bind the source-position arithmetic channel at this same nominal state and
matrix using existing source allowances, keeping Moon/Mars full fields.
Then reassess the remaining anchor and rate budget before selecting or timing
an expensive vector prefix. Do not reuse preceding-epoch native arithmetic,
reset carried errors, start a fifth arc, change tolerances or open targeting.
