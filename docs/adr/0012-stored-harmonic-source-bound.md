# 0012 — Bound harmonic source errors through a stored matrix

Date: 2026-09-14. Parent revision: `838e0f9`. M3 task3.9 remains open.

## Missing contract and minimal implementation

Decision0011 covers only six point sources. The stored harmonic evaluator
instead computes A.T*g(A*r), where r is spacecraft minus source and A is the
stored inertial-to-fixed matrix. It is not sufficient to apply an ideal
rotation bound while silently treating A as exactly orthogonal. The existing
matrix-error helper addresses changes in A, not source motion with A fixed.

Add one test-local source-error helper in
`tests/test_trajectory_harmonic_source.py`, reusing the existing exact-root and
full harmonic Jacobian bounds. No production API, dependency or native call.

Let q = sum_ij |A_ij|. Then ||A||_2 = ||A.T||_2 <= ||A||_F <= q, without
orthogonality. If the source error is at most epsilon in L2, its transformed
displacement is at most q*epsilon. Every point of the transformed source
comparison chord stays at distance at least

    d = lower_bound(|A*r|_2) - q*epsilon.

Use exact rational A*r, the existing dyadic square-root enclosure and a
downward binary64 conversion. Reject d <= 0 or an unrepresentable positive
floor as unresolved. If J bounds the field Jacobian throughout |y| >= d,
then the source effect in inertial coordinates is at most

    ||A.T * (g(A*r + A*delta) - g(A*r))||_2 <= q^2 * J * epsilon.

The existing full-field Frobenius Jacobian bound is a sufficient operator
bound. Keep all coefficients, including C00; this is a source translation,
not a rotation-only estimate. The final allowance is an exact Fraction.
This deliberately conservative matrix bound avoids a new singular-value
routine. Tighten it only if measured composition needs that improvement.

## Independent controls

Twenty-seven scaled zonal-field cases combine degrees 0,2,8, matrix scales
1/2,1,2 and source shifts -1/128,0,1/128 m. Their exact squared pole-force
differences follow the analytic law A.T*g_n(A*r)=s^(-n-1)*g_n(r) for A=s*I.
Zero shifts must give zero allowance.

A separate anisotropic monopole uses A=diag(16,1,1), r=(0,0,2) and an x shift
epsilon=1/4096. The changed x acceleration has exact square
(256*epsilon)^2 / (4+(16*epsilon)^2)^3. It fits the bound, but exceeds the
bound with one of the q=18 factors removed. Thus the test catches a missing
input or output matrix factor without relying on a harmonic evaluator.

Seven cases reject negative/inexact errors, inexact positions, malformed or
nonfinite matrices, zero transformed separation and overlapping domains.
One case rejects an expired shared budget. These are pure analytic controls,
not empirical qualification of the Moon/Mars resource matrices.

## Next step and limits

Bind this helper to the existing fresh Moon/Mars positions, stored matrices,
full coefficient arrays and conditional source allowances. Verify epoch,
resource identity, no truncation and unchanged shared-budget/native counters;
retain measured allowances. No new high-degree vector evaluation is needed
for a norm bound. Do not evaluate a degree120 vector or extend the coast.

The helper holds A and the spacecraft state fixed. PCK/matrix uncertainty,
native force arithmetic, incoming spacecraft error balls, SRP, relativity
and interval/domain closure remain separate obligations. Neither this lemma
nor the analytic cases complete task3.9 or certify a mission trajectory.

## Verification

All 36 focused cases passed in 0.50 s. Full pytest: 2923 passed in 457.16 s;
native inventory 141.40 s, portable 45.28 s. Existing thirteen/zero arc
assertions remain unchanged. Ruff, strict OpenSpec, whitespace and legacy
checksum/import isolation pass. No new native query/arc or production change.
Only the pure lemma and analytic controls are qualified here, not live
Moon/Mars source allowances or a complete trajectory error bound.
