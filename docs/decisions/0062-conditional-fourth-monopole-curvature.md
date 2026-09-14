# 0062 — Conditional fourth-anchor monopole Taylor remainder

Date: 2026-09-15. Parent revision: `ab716c9`. M3 task 3.9 stays open.
Status: retained-input conditional family audit, not a selected live reference.

## Decision

Before constructing an expensive gravity vector, bound the monopole remainder
for an explicitly defined family of prospective cubic references. Reuse the
existing curvature and recentered-domain helpers; add no propagation or source
query. This is a reproducible test over retained evidence, not a new live
inventory measurement or authentication of those artifacts.

At the fourth nominal endpoint let q(0), q'(0) equal the saved spacecraft
state and q''(t)=a0+j0*t, where j0 is Decision0061's binary64 midpoint.
For h=1/8 s impose the SUFFICIENT family condition

`||a0||_2 <= 4 - h*||j0||_1`.

Then `||q''(t)||_2 <= 4 m/s^2` throughout the interval. The value 4 defines
this conditional family; it is neither an inferred acceleration of an
unconstructed reference nor a changed production limit or error allocation.
The sufficient anchor-norm cap is approximately 3.9998400470051654 m/s^2.
The retained full-gravity norm leaves approximately 0.7122640475196665 m/s^2
for anchor error in this DOMAIN-only sufficient condition. This large margin
is emphatically not an acceptable error for endpoint accuracy. Any actual
anchor must establish its own norm and much tighter defect budget.

## Domain and remainder argument

Compute offsets from the original domain centre using exact binary64 state
fractions. With acceleration cap 4, all references in this family have reaches
at most 7631.309654059291 m and 0.8945295566804817 m/s, strictly inside the
existing 8000 m / 1 m/s domain. Zero initial reference errors describe the
definition of q, not a reset of the carried true-state errors. The already
qualified true-state domain and this reference domain are convex; the shared
floors are consequently applicable to their position chords.

For each body, use its exact position-polynomial derivative at the new epoch,
its covered source-curvature bound B, and the existing whole-domain floor d:

`A_rel = 4 + B`, `V_rel = ||q'(0)-source'(0)||_1 + A_rel*h`,
`K_i = 24*GM*V_rel^2/d^4 + 2*GM*A_rel/d^3`.

The existing analytic chain-rule controls justify this bound on the second
time derivative of monopole acceleration. Taylor's theorem then gives
`||g_i(q(t),t)-g_i(q(0),0)-g_i'(0)*t|| <= K_i*t^2/2`.
Since t<=h, it contributes at most `(h*sum(K_i)/2)*t` to a D+J*t ledger.
Source motion is included; SPK type-3 stored velocities are not substituted
for position-polynomial derivatives. All eight bodies participate, with
Moon/Mars monopoles only in this calculation.

Summed curvature is bounded by 2.0480478798265908e-5 m/s^4; its rate charge
is bounded by 1.2800299248916192e-6 m/s^3. Decision0061's midpoint-rounding
allowance remains a separate 1.4379857137182707e-20 m/s^3 channel. Neither
number includes nonmonopole translation/rotation, source/native arithmetic,
the gravity acceleration anchor, or native endpoint residuals.

This rate charge already exceeds Decision0059's optimistic degree115 scalar
rate allowance (about 8.53e-7 m/s^3), under that ledger's other assumptions.
This shows that this conservative bound does not resolve that screen, not
that the true error exceeds tolerance. It does not select a higher prefix,
prove impossibility, or justify changing a tolerance.

## Verification

`tests/test_trajectory_fourth_curvature.py` checks source/endpoint coverage,
frame, state, model, GM and source-context consistency, records input hashes,
proves conditional domain inclusion, and reports outward upper bounds.
Its scalar sufficient caps are explicitly approximate, not rounded guarantees.
The new audit and existing independent curvature controls pass: 71 tests in
0.09 s. A separate replay passed in 0.07 s; both reports and the full-suite
report match `tests/data/m3_fourth_conditional_monopole_curvature.json` exactly.
Full suite: 3278 passed in 475.62 s (native inventory 148.09 s, portable
49.88 s). All 19 prior native and 6 prior portable selected scientific
reports match the parent run after excluding timers only. Inventory arc counts
remain 13/0; harmonic reuse remains 14 requests, 4 misses, 10 hits.
Ruff, strict OpenSpec validation, whitespace checks and the unchanged legacy
SHA-256 passed. The full suite consists of separate tests, not one mission's
shared 300 s budget.

## Next bounded step

Assess fresh nonmonopole translation and rotation rate bounds on this same
conditional reference family and couple all charges before selecting or
evaluating a gravity anchor. Any later live consumer must rebind inputs and
verify that its actual reference satisfies this family's premise. No fifth
arc, complete uniform J, native-stage safety or mission-scale certificate
is established here. Production code, UI and scientific tolerances stay intact.
