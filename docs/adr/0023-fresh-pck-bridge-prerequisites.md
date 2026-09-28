# 0023 — Audit the fresh PCK bridge prerequisites

Date: 2026-09-14. Parent revision: `c65e51b`. M3 task 3.9 remains open.

## Existing code and reusable evidence

`_check_pinned_pck_rotation_rates` in `tests/test_trajectory_spk.py` reads
and hashes ten relevant text-PCK pool arrays, rejects binary overrides and
unsupported frame/periodic settings, and builds exact RA/DEC/PM intervals.
Its phase and polynomial evaluations use `start_tdb_s`, currently
978995455.2304223. Its returned rate bounds cover the requested interval,
but its returned angle intervals describe only that original epoch.

The fresh harmonic snapshot is at 978995455.2929223 TDB s, exactly 1/16 s
later. It already retains both J2000-to-body-fixed matrices and the PCK
file identity. `_pck_matrix_error_bound` can compare those stored matrices
to exact fresh Euler-angle intervals without another orientation query.
Its entrywise L1 error also bounds the operator norm; it does not assume
the rounded stored matrix is exactly orthogonal.

## Required coordinate order

Let A be a stored matrix, Q the ideal PCK rotation, r_s the relative vector
using stored source coordinates and r_i the one using exact SPK polynomials.
Decision0022's harmonic target is A.T*g(A*r_i). Its existing source channel
already bridges A.T*g(A*r_s) to that target at fixed A.

The next rotation channel must therefore bridge

    A.T*g(A*r_i) -> Q.T*g(Q*r_i).

`_stored_matrix_force_error_bound_m_s2` accepts the squared radius of the
same relative vector on both sides. Use the exact fresh polynomial relative
vector already available in the inventory, or separately qualify an entire
source-ball radius bound. Passing the stored radius |r_s|^2 with the current
source channel would mix two different paths. The older prefix-composition
control instead rotates first and shifts the source under Q; its source
channel must not be substituted for the current fixed-A channel silently.

Keep C00 and the full Moon200/Mars120 arrays in this matrix bridge. C00 is
invariant under an exact proper rotation, but not under a rounded matrix's
possible nonorthogonality. The existing helper explicitly retains this
effect and requires a matrix-error bound smaller than one.

## Next bounded implementation

Extract the existing pure PCK angle evaluation into a helper accepting the
already pinned pool arrays and an explicit epoch. Preserve the original
rate/native controls and reuse the same arrays at the fresh epoch rather
than rerunning the wrapper's two BODEUL and twenty-six SXFORM calls.
Compare new intervals to the already retained fresh matrices with
`_pck_matrix_error_bound`; preserve epoch, pool/file hashes and matrix bits.
Test original-epoch parity and fresh-epoch evaluation before applying a
full-field force bridge at r_i. No new native query is needed for this step.

After that bridge, the retained native acceleration is an observation to
compare against the independent reference enclosure, never its oracle.
Incoming spacecraft error balls and time/domain closure remain separate.

## Verification scope

This is a read-only code/data audit followed by documentation updates, not a
new numerical qualification or a fix to the currently scoped assembly.
Strict OpenSpec and whitespace checks pass; full pytest was not rerun.
Latest implementation evidence remains 3029 passed in 473.75 s, native
152.97 s, portable 50.68 s, from decision0022. No model, limit or tolerance
changes and no additional SPICE calls or propagation arcs in this audit.
