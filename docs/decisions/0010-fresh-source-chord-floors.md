# 0010 — Reuse position-ball separation for fresh source chords

Date: 2026-09-14. Parent revision: `5faad08`. M3 task3.9 remains open.

## Decision and argument

No new distance helper is necessary. Decision0009 binds the stored source
anchor b to the exact polynomial source p with |p-b|_1 <= epsilon. Therefore
|p-b|_2 <= epsilon. For every t in [0,1], the comparison chord
b+t(p-b) stays in the ball centred at b with radius epsilon. With the nominal
spacecraft position x fixed, reverse triangle inequality gives

    |x - (b+t(p-b))|_2 >= |x-b|_2 - epsilon.

The existing `_relative_distance_lower_bound` already accepts binary64
anchors and declared position-ball radii, and rounds its result downward.
Use the stored b, not a rounded conversion of exact p. Both b and x are
exactly represented by the retained binary64 inputs. This avoids introducing
an unaccounted conversion error or a second nearly identical helper.

Eight new cases in `tests/test_trajectory_distance_bound.py` bind the existing
source and harmonic replay artifacts by epoch, body set, frame and origin.
They call the existing helper with spacecraft radius zero and source radius
epsilon, require d > 0, and independently verify using exact Fractions:

    (d + epsilon)^2 <= sum_i (x_i - b_i)^2, with d + epsilon > 0.

This squared check does not invoke the helper's Decimal square root. Combined
with the argument above, it proves a floor for every chord point, not merely
sampled endpoints. Existing tests cover outward rounding, translated rational
geometry, irrational norms, zero/overlapping balls, invalid input and deadlines.
The new replay cases request no SPICE state, derivative or propagation.

## Observed floors

All values are metres and rounded downward; these are source-error comparison
domains at the retained epoch 978995455.2929223 TDB seconds since J2000.

| Body | Positive distance floor (m) |
| --- | ---: |
| Sun | 248443929582.4009 |
| Mercury | 198573435578.0432 |
| Venus | 354660245735.4243 |
| Earth | 221235955438.04004 |
| Moon | 221238455325.95724 |
| Mars | 3689499.994800644 |
| Jupiter | 796044507652.3591 |
| Saturn | 1435701713894.6316 |

## Scope and next step

The source-ball premise remains conditional on the pinned arithmetic and
guarded-core audit in decision0008 and consumer binding in decision0009.
These floors do NOT include the incoming spacecraft error ball, motion over
the next time interval, collision certification or native integration stages.
The coverage-end label does not make a fixed-epoch floor an interval floor.

Next compose the six point-source errors with their qualified spatial bound
2*GM*epsilon/d^3 at this epoch. Moon/Mars need harmonic spatial bounds and
stored-matrix factors; their C00 terms must not be counted twice. PCK errors,
SRP, relativity, state balls and interval/domain closure remain open. Do not
promote positive source chord floors to full-force or mission qualification.

## Verification

All 73 focused distance tests passed in 0.05 s. Full pytest: 2887 passed in
475.30 s; native inventory 143.06 s, portable 43.40 s, with existing thirteen/
zero arc assertions unchanged. Captured output reproduces all eight table
values. Ruff, strict OpenSpec, whitespace and unchanged legacy checksum/import
isolation pass. No production code, dependency, force model or limit changed.
