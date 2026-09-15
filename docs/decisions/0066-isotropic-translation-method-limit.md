# 0066 — Stop geometry-only tuning of the current translation formula

Date: 2026-09-15. Parent revision: `04e31a5`. M3 task 3.9 stays open.
Status: obstruction for one bound-accounting method, not for the trajectory.

## Decision

Before further geometry/speed tightening, test whether it can possibly make
the existing whole-degree isotropic translation ledger pass. Keep the same
Mars120 coefficients, fourth nominal state, incoming velocity error and
h=1/8 s. No new reference, native arc, source query or force change.

## Method-output lower bound

Write the degree-sum formula as `L(d)=sum_n C_n/d^(n+3)`, with nonnegative
`C_n=GM*R^n*(n+1)*(n+2)*sqrt((2n+1)*Q_n)` and Q_n the exact squared
coefficient norm. Every valid uniform distance floor must satisfy
`d <= ||r(0)||`; every valid initial-speed upper bound satisfies
`V >= ||r'(0)||`. Thus this specific translation charge
`L(d)*(V+A_rel*h/2)`, for nonnegative A_rel, cannot be smaller than
`L(||r(0)||)*||r'(0)||`.

Compute a rigorous LOWER enclosure of that expression: use a dyadic UPPER
enclosure of the initial radius in the denominator, LOWER square-root
enclosures for the coefficient norms, and a LOWER enclosure of the initial
Euclidean speed. All products and sums are exact fractions; final lower
reports round downward. Independent complete upper calculations from
Decision0065 bracket the result. No Frobenius factor or force-direction
assumption is introduced.

The resulting bounds are:

- Initial radius upper: 3689499.9800443975 m.
- Initial relative speed lower: 1500.0004657397433 m/s.
- Degree-formula lower: 5.5027478400685614e-8 s^-2.
- Translation-formula lower: 8.25412432295121e-5 m/s^3.
- Velocity ACCOUNTING lower, retaining the incoming error and otherwise
  charging only this term: 1.6075158036363222e-6 m/s.

That last value already exceeds the unchanged 1e-6 m/s private gate. Even
perfect radius/speed tightening cannot make THIS formula pass for these
fixed inputs and horizon. It is close to the last local-geometry accounting
value, 1.6084307798007537e-6 m/s, so further geometry-only effort on this
formula is not justified as a route to this gate.

## What this does not prove

This is a lower bound on an upper-bound FORMULA, never a lower bound on the
actual force change or trajectory error. It does not rule out sharper
coefficient/direction-aware bounds, another reference that captures varying
forces, or a different interval length. The omitted anchor, rotation,
monopole-remainder, source/native and feedback channels remain unresolved.
It does not justify resetting carried errors or relaxing a tolerance.

## Verification

Four manufactured degree cases (0, 2, 60, 120) use exact square-root oracles
to test monotonicity and equality at the limiting radius/speed, with both
smaller floors and larger speeds. These and existing degree-map/retained-input
controls passed: 87 tests in 2.26 s. Separate replay: 5 passed in 1.98 s.
Both runs and the full-suite report match
`tests/data/m3_fourth_isotropic_translation_method_limit.json` after excluding
its timer only. All four preceding retained-input reports remain unchanged.
Full suite: 3282 passed in 459.87 s (native inventory 141.54 s, portable
46.22 s). All 19 prior native and 6 prior portable selected scientific
reports match the parent after excluding timers only. Inventory arc counts
remain 13/0; harmonic reuse remains 14 requests, 4 misses, 10 hits.
Ruff, strict OpenSpec validation, whitespace checks and the unchanged legacy
SHA-256 passed. Suite time covers separate tests, not one mission's shared
300 s budget. Existing dyadic machinery is reused with no production, UI or
dependency changes; budget checks retain zero native calls in this audit.

## Next bounded step

Compare the accounting benefit and verification cost of shorter reference
intervals versus a richer or direction-aware reference, using bounded analytic
controls before native propagation. Any subdivision comparison must retain
cumulative state error and all repeated anchor/residual costs; a passing
single shortened interval is not a passing composition. Do not select a new
native limit, degree prefix or physical reference from this method obstruction.
