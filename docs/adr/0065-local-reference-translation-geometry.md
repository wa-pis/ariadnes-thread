# 0065 — Covered local geometry for reference translation

Date: 2026-09-15. Parent revision: `2764d9e`. M3 task 3.9 stays open.
Status: tighter conditional reference/chord geometry, not a true-state tube.

## Decision and proof

Retain the broad-domain results and add a separate local calculation for
Moon/Mars nonmonopole translation. Reuse Decision0062's reference family:
q(0), q'(0) are the actual fourth nominal state, and the prospective cubic
must satisfy the explicit uniform acceleration cap 4 m/s^2. No acceleration
anchor has been selected or certified by these retained-input audits.

For each exact position-polynomial source, define r=q-source,
V0=||r'(0)||_1 and A_rel=4+B, with B the covered source-curvature bound.
On 0<=t<=h=1/8 s, integration and the triangle inequality give

`||r(t)-r(0)||_2 <= V0*t + A_rel*t^2/2 <= rho`,
`rho = V0*h + A_rel*h^2/2`.

The ball centred at r(0) with radius rho is convex, so it also contains every
translation chord from r(0) to r(t). A dyadic lower square-root enclosure for
||r(0)||, minus rho and rounded DOWN, therefore gives a uniform lower distance
for the reference and these chords. Assertions check positivity, the exact
rounding inequality and `(reported_floor+rho)^2 <= r(0).r(0)`. Using just the
nominal radius would not satisfy that check for this nonzero displacement.

This ball does not include unknown true-state errors. The previously carried
errors and broad full-force state-sensitivity domain remain untouched. These
local floors may replace the broad floor in the REFERENCE translation term
only; they do not automatically qualify new full-force Lipschitz bounds,
native-stage safety, source/native arithmetic or a propagated error tube.

## Results

| Body | Relative displacement upper (m) | Old broad floor (m) | Local reference/chord floor (m) |
| --- | ---: | ---: | ---: |
| Moon | 5079.042108732082 | 221238394294.2555 | 221238449055.37964 |
| Mars | 187.5806225460353 | 3631133.108218859 | 3689312.39942185 |

Recompute the complete Moon200/Mars120 nonmonopole degree-map bound from
the same pinned fields at each new floor, with C00 removed from a copy only.
Mars's operator bound becomes 5.5081888961021043e-8 s^-2. Total translation
rate decreases from 1.1662837679384899e-4 to 8.265836017855932e-5 m/s^3,
about 29.1%, without changing the physical model or tolerances.

Preserving the same incoming velocity error, the optimistic translation-only
accounting value is still approximately 1.6084307798007537e-6 m/s, above the
unchanged 1e-6 m/s private gate. This is failure of this bound-based screen,
not a lower bound on physical/numerical error or a proof of impossibility.

## Degree-scaling cross-check

For fixed coefficients, degree n's Hessian bound scales exactly as d^(-n-3).
Rescale every previous exact degree bound by `(old_floor/local_floor)^(n+3)`
and verify that their exact sum equals a separate complete helper evaluation
at the local floor. This checks reuse before recomputing tail counterfactuals.

The optimistic omitted-prefix screen now first passes at 44 instead of 60:
cutoff43 gives approximately 1.0017623347367573e-6 m/s; cutoff44 gives
9.98850247794553e-7 m/s. These grant the omitted prefix zero translation cost
and omit the other positive error channels. They are not selected reference
degrees, force truncations or completed derivative/remainder qualifications.

## Verification and next step

The extended retained-input, curvature and degree-map controls passed:
153 tests in 2.38 s. New local-floor and complete-field-bound calculation
took 0.06561699998565018 s for Moon and 0.024219874991104007 s for Mars in
the focused run; subsequent degree rescaling is included in the degree-audit
timer and the same overall budget. No new queries or native arcs.
Separate replay passed in 1.98 s. Both runs and the full-suite report match
`tests/data/m3_fourth_conditional_local_translation.json` after excluding
timers only. All three preceding conditional reports remain unchanged.
Full suite: 3278 passed in 467.11 s (native inventory 143.78 s, portable
46.78 s). All 19 prior native and 6 prior portable selected scientific
reports match the parent run after excluding timers only. Inventory arc counts
remain 13/0 and harmonic reuse 14 requests, 4 misses, 10 hits.
Ruff, strict OpenSpec validation, whitespace checks and the unchanged legacy
SHA-256 passed. Suite duration covers separate tests, not one mission's
shared 300 s budget. No production, UI or dependency changes were made.

Geometry tightening helps but does not resolve the accounting. Next assess
the remaining direction-free norm conservatism versus a richer reference
derivative, starting with inexpensive bounded controls and cost estimates.
Any direction-aware replacement must cover the changing direction throughout
the interval and keep rotation/remainder channels; a sampled directional
value is not a uniform bound. Do not start a fifth native arc or adopt a
high-degree reference merely because an omitted-prefix counterfactual passes.
