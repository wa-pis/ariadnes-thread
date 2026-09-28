# 0063 — Fourth-reference nonmonopole translation screen

Date: 2026-09-15. Parent revision: `de5a0a4`. M3 task 3.9 stays open.
Status: conditional-family bound fails an optimistic accounting screen;
not an observed trajectory error or an impossibility result.

## Decision and scope

Extend Decision0062's retained-input audit with the existing whole-degree
operator-norm bound for Moon200 and Mars120. Load the pinned coefficient
resources, verify hashes, degrees, normalization radii and GM against the
retained force context. Remove C00 from a COPY only; retain C20 and all other
degrees/orders. The loaded full field is unchanged. This computes bounds,
not an exact high-degree acceleration vector or another spacecraft arc.

Reuse the explicit reference-family condition and domain inclusion from
Decision0062. Source derivatives and curvature, epoch/coverage and the actual
fourth nominal state remain the same. The assumptions still need verification
by any future live consumer; no selected acceleration anchor exists here.

## Translation argument

Let H(Q,r) be the ideal nonmonopole acceleration at orthogonal orientation Q,
and r(t)=q(t)-source(t). Split its change as

`H(Q(t),r(t))-H(Q(0),r(0))`
`= H(Q(t),r(t))-H(Q(t),r(0)) + H(Q(t),r(0))-H(Q(0),r(0))`.

Only the FIRST term is bounded in this step. A whole-degree operator bound L
is invariant under ideal orthogonal coordinate changes. The relative chord
lies in the difference of the qualified spacecraft and source envelopes,
so the same distance floor applies. With V0 from the exact source derivative
and A_rel=4+B from the explicit reference-family/source-curvature bounds,

`||r(t)-r(0)|| <= V0*t + A_rel*t^2/2`,
`||translation change|| <= L*(V0+A_rel*h/2)*t`, for `0<=t<=h`.

No rotation rate is needed to bound that first term uniformly over Q(t).
The SECOND term, native/source arithmetic, anchor error and native endpoint
residual remain separate missing channels. An ideal orthogonal-map bound
does not automatically apply to a stored nonorthogonal native matrix.

## Measured bound and accounting result

At h=0.125 s the retained whole-domain floors give:

| Body | Nonmonopole L (s^-2) | Displacement-rate bound (m/s) | Translation-rate bound (m/s^3) |
| --- | ---: | ---: | ---: |
| Moon | 7.292657858566036e-35 | 40632.336869856656 | 2.963177307858626e-30 |
| Mars | 7.771883311482942e-8 | 1500.6449803682824 | 1.1662837679384899e-4 |

The exact calculation sums before outward rounding; the total outward rate
is 1.1662837679384899e-4 m/s^3. Moon is included even though its contribution
is below the displayed sum's binary64 resolution. This is the chosen
whole-degree bound, not a claim of optimality among available bounds.

Preserve incoming velocity error 9.62662340905759e-7 m/s. Even an optimistic
scalar ledger that charges ONLY this translation rate gives
`v_in + T*h^2/2 = approximately 1.8738215346077041e-6 m/s`, above the unchanged
1e-6 m/s private gate. This ledger omits gravity-anchor error, midpoint error,
monopole curvature, rotation, bounded light/relativity, state feedback and
native residuals; adding nonnegative charges cannot fix this chosen screen.

This is NOT a lower bound on physical or numerical error. A tighter bound,
a reference capturing more of the changing force, or another interval length
could change the accounting. We do not adopt any of those alternatives or
alter scientific tolerances/production limits here. Increasing an anchor's
harmonic prefix alone does not remove this translation-rate charge.

## Verification and next step

The extended `tests/test_trajectory_fourth_curvature.py` and independent
degree-map controls passed: 83 tests in 2.17 s. The focused calculation took
1.0425624169874936 s, with zero ephemeris queries and zero native arcs.
Separate replay passed in 1.51 s. Both runs and the full-suite run reproduce
`tests/data/m3_fourth_conditional_nonmonopole_translation.json` after excluding
its timer only; the prior conditional curvature report is unchanged.
Full suite: 3278 passed in 471.17 s (native inventory 148.04 s, portable
46.80 s). All 19 prior native and 6 prior portable selected scientific
reports match the parent run after excluding timers only. Inventory arc counts
remain 13/0; harmonic reuse remains 14 requests, 4 misses, 10 hits.
Ruff, strict OpenSpec validation, whitespace checks and the unchanged legacy
SHA-256 passed. The suite consists of separate tests, not one mission's shared
300 s budget. No production, UI, dependency or acceptance change was made.

Before calculating rotation channels or an expensive new gravity vector,
identify which degree components and norm relaxations dominate this
translation bound. Compare bounded analytic ways to tighten it or capture
the leading nonmonopole derivative in the reference. Any replacement must
retain a complete remainder and source/rotation argument; no cancellation
may be inferred by subtracting unrelated norm upper bounds. No fifth native
arc, targeting run or complete full-force J is qualified by this screen.
