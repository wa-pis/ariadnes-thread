# 0068 — Bound significands before another harmonic evaluation

Date: 2026-09-15. Parent revision: `08e0c7b`. M3 task 3.9 stays open.
Status: test-only arithmetic prerequisite, not force/runtime qualification.

## Decision

Following Decision0067, first test outward binary rounding with the standard
library `Fraction`. Do not introduce an interval class, dependency, production
evaluator or new native arc. Exact rational harmonic calculations can grow
large intermediate integers; limiting stored significands is a candidate
way to control that growth, but its practical benefit remains unmeasured.

For nonzero exact x, choose e=floor(log2(abs(x))) using integer bit lengths
and an exact comparison. With p significant bits, set s=2^(e-p+1) and return
`[floor(x/s)*s, ceil(x/s)*s]`. Integer floor/ceiling work for either sign.
Zero maps exactly to zero. The enclosure follows directly from floor/ceiling;
its width is at most s, hence at most abs(x)*2^(1-p).

The endpoints have at most p significant binary digits after removing trailing
zero bits. Exponents remain unbounded: this is NOT a global bound on numerator
or denominator storage. Nor does rounding bound the accumulated interval width.
Exact arithmetic must still form each operation before rounding its endpoints.

## Verification

The new isolated test file has 71 passing controls (0.05 s): five precisions
(1/24/53/80/120 bits), signed rationals, exact dyadics, zero, large and small
exponents, invalid inputs, and cancellation. Check enclosure, sign symmetry,
endpoint representability/idempotence and the independent relative-width bound.

Sixteen manufactured degree-120 Horner calculations use four-corner interval
multiplication and outward-rounded endpoints. Compare with an independent
exact rational point calculation after EVERY recurrence step. Negative inputs
and zero are included. A 1/1000 dimensionless width check is only a sanity
check for these chosen polynomials, not a physical tolerance or allocation.
The cancellation control explicitly preserves uncertainty when two occurrences
of the same interval are treated independently.

This is not the harmonic recurrence. There is no physical-state accuracy
claim, full-field anchor, force derivative, measured acceleration enclosure
or speedup claim. No native queries or integrations run in these controls.
The full suite is not rerun for this isolated test-only addition; the parent
revision's 3343-test result remains historical evidence, not a result for
this revision. Replay together with the existing subdivision controls: 132
passed in 0.14 s. Repository-wide Ruff and strict OpenSpec validation passed,
as did whitespace checks. The legacy SHA-256 remains
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`,
and no legacy-model imports occur under `src`.

## Next step

Compare bounded interval evaluation of a SMALL harmonic recurrence with the
existing exact oracle, including nonpolar coordinates and derivative jets.
Measure enclosure width and cost before attempting a larger degree. Reuse
the existing recurrence rather than writing another physical model. Normalized
force assembly, square roots/division, source/PCK allowances, cancellation,
deadline accounting and full-degree performance remain separate obligations.
No production thresholds, reference family or native partition are changed.
