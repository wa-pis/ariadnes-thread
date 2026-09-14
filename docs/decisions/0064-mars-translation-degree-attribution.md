# 0064 — Attribute the Mars translation bound before reference changes

Date: 2026-09-15. Parent revision: `1d47cb7`. M3 task 3.9 stays open.
Status: conditional bound attribution and optimistic counterfactuals only.

## Decision

Reuse the pinned Mars120 coefficients and Decision0063's conditional geometry.
Recompute each degree's operator bound with the existing helper and verify
that their exact sum equals the previous whole-degree bound. Separately
remove C20 from a coefficient COPY and bound the remainder directly. Never
subtract a C20 norm upper bound from an unrelated whole-field upper bound.
The actual physical field, sources, reference-family premise and tolerances
are unchanged. No new source query, vector evaluation or spacecraft arc.

For the C20-free remainder compare the whole-degree operator bound with the
existing symmetric-trace-free reduction of a genuine Frobenius bound.
Exterior harmonic Hessians satisfy those premises. The trace-free factor
is not applied to the sharp C20 operator bound or another operator bound.
The candidate full bound is the minimum of the original degree sum and
sharp C20 plus the independently bounded remainder. This is a comparison
of these specific proven bounds, not an optimization over all possible ones.

## Findings

At the existing 3631133.108218859 m floor:

- Whole nonmonopole degree sum: 7.771883311482942e-8 s^-2.
- Degree 2 contributes 1.8485673064084272e-8 s^-2, approximately 23.7853%
  of that additive bound. This fraction is not a fraction of the physical
  acceleration or of the actual numerical error.
- Isolated C20 bound: 1.8371363390228482e-8 s^-2.
- Independently recomputed C20-free remainder: 6.128574764117423e-8 s^-2.
- The compared C20/remainder construction does not improve the full bound;
  the original degree sum remains selected by the diagnostic.
- Even granting zero translation cost to C20 leaves an optimistic velocity
  accounting value of 1.6811635093889262e-6 m/s, above the 1e-6 m/s private
  gate. The full unchanged charge gives 1.8738215346077041e-6 m/s.

Thus an isolated-C20 reference refinement is not justified as the sole
solution by this accounting. Higher degrees collectively dominate the bound.
This does not prove they dominate actual force variation along the motion.

## Prefix counterfactual

For every cutoff from 0 through 120, sum only the original additive degree
bounds above that cutoff and repeat Decision0063's optimistic scalar ledger.
Incoming error is preserved; all other charges are still omitted. These
counterfactuals grant the entire omitted prefix zero translation cost; they
do NOT claim that merely adding its instantaneous derivative to a reference
would do so. Its Taylor remainder, rotation, anchor and native errors would
still need qualification in any actual construction.

The first passing counterfactual is cutoff 60: the remaining degree sum is
bounded by 3.1171103589409505e-9 s^-2 and the optimistic velocity accounting
is approximately 9.992066847604365e-7 m/s. This tiny margin ignores the other
positive channels. It is not a selected truncation, production force removal,
an implementable reference or a full error certificate. Exact tail sums are
monotone; cutoff120 has exactly zero retained tail. Outward JSON serialization
may report an exact zero as the smallest positive binary64 number; all sums
and pass/fail comparisons use exact fractions, not those serialized endpoints.

## Verification

The extended retained-input test and existing independent degree-map, C20
and trace-free controls passed: 256 tests in 2.37 s. Additional attribution
calculation took 0.25672812503762543 s in the focused run. Shared test budget
checks include the added work; all native counters remain zero in this audit.
Separate replay passed in 1.94 s. Both runs and the full-suite report match
`tests/data/m3_fourth_mars_translation_degree_audit.json` after excluding
the timer only. Both preceding conditional reports remain unchanged.
Full suite: 3278 passed in 466.00 s (native inventory 143.27 s, portable
46.32 s). All 19 prior native and 6 prior portable selected scientific
reports match the parent run after excluding timers only; inventory arc counts
remain 13/0 and harmonic reuse 14 requests, 4 misses, 10 hits.
Ruff, strict OpenSpec validation, whitespace checks and the unchanged legacy
SHA-256 passed. Suite duration covers separate tests, not one mission's
shared 300 s budget. No production, UI or dependency changes were made.

## Next bounded step

Before paying for a high-degree reference derivative, assess how much of this
bound comes from the broad whole-domain distance floor and the direction-free
operator-norm estimate. Compare a rigorously covered local source/reference
geometry with the current envelope; any tighter floor must include the whole
conditional curve and the relevant chords, not just the nominal anchor.
Use the resulting budget screen to decide whether direction-aware or richer
reference work is warranted. Do not choose cutoff60, add a fifth native arc,
or change scientific tolerances from this attribution alone.
