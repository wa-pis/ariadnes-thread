# 0024 — Evaluate fresh PCK angles and matrix errors

Date: 2026-09-14. Parent revision: `fbb8fb2`. M3 task 3.9 remains open.

## Reuse the same pinned input path

Extract `_pck_angle_intervals_deg` from the existing PCK rate control in
`tests/test_trajectory_spk.py`. It accepts the ten supported pool arrays
and an explicit finite binary64 TDB epoch, validates their names, sizes
and finite float coefficients, and preserves exact Fraction polynomials,
degree-based trigonometric enclosures and prime-meridian wrap rejection.
Pole polynomials and periodic phases use Julian centuries; PM uses days.
Lunar RA/PM corrections use sine and DEC corrections use cosine.

The original wrapper retains all pool hashes, override/frame checks, rate
bounds and native readbacks. It returns the already read arrays as a fourth
private result. The fresh probe rechecks the same pool hash and evaluates
the pure helper at 978995455.2929223 TDB s. It does not run BODEUL, SXFORM,
or another rotation getter again. Existing fresh rotation evaluations supply
the matrices for `_pck_matrix_error_bound`.

For each body, report its matrix, epoch/frame, file/pool hashes and an
outward matrix-entry L1 error against the ideal text-PCK rotation. This
also bounds operator error. Require the allowance to be finite and below
one, preserving the later force-bridge prerequisite. No assertion of exact
orthogonality is made for the stored matrices.

## Verification

Twenty-five pure controls cover signed polynomials at negative/zero/positive
epochs, day/century units, signed lunar periodic terms at four quadrants,
fresh PM advancement, malformed inputs, wrap-crossing rejection and deadline
expiry. Together with existing trigonometric/PCK/matrix controls, all 72
focused tests pass in 1.54 s. Full suite: 3054 passed in 474.83 s, native
inventory 153.46 s, portable 51.11 s. Ruff, strict OpenSpec, whitespace and
legacy checksum/import isolation pass. Thirteen/zero arcs remain unchanged.

Original-epoch PCK diagnostics match the previous full run exactly in both
inventory variants. [Retained fresh matrix errors](../../tests/data/m3_fresh_pck_matrix_errors.json)
match the captured native-run reports exactly; both matrices, epoch and PCK
hash match the historical harmonic replay. The dimensionless entry-L1
allowances are 9.340662146646177e-13 (Moon) and 1.7882615809008832e-11
(Mars). Shared angle evaluation took 0.30147 s; matrix comparisons took
0.07349 s and 0.05797 s. These are numerical matrix enclosures, not angular
measurement uncertainty or acceleration-error bounds.

## Scope and next step

The shared angle-evaluation timer is repeated in both body reports but must
be counted once; individual matrix timers are separate. All are nested
within the existing harmonic probe timer, not additional elapsed totals.
There are no additional native queries or propagation arcs, no production
or dependency changes, and no tolerance or limit changes.

Next apply the existing full-field matrix-to-force bound at the exact
ideal-source relative vector, as decision0023 requires. Keep Moon degree200,
Mars degree120 and C00. The current aggregate remains fixed-stored-matrix;
these new dimensionless matrix errors are not acceleration errors and are
not added directly to its m/s^2 allowance. Native-reference binding,
incoming state balls and time-domain closure remain open.
