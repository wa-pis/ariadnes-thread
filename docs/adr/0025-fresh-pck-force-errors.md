# 0025 — Bound fresh PCK effects on the full harmonic forces

Date: 2026-09-14. Parent revision: `83c9e9b`. M3 task 3.9 remains open.

## Same source coordinates on both sides

Apply the existing `_stored_matrix_force_error_bound_m_s2` inside the fresh
inventory probe. Reuse the already qualified outward matrix-entry L1
allowance as an operator bound. Compute r_i exactly from the nominal
spacecraft position minus the fresh exact source-polynomial position,
using Fractions already in memory, then pass its exact squared radius.
No new source or orientation query is required.

For stored A and ideal orthogonal Q, the helper encloses
|A.T*g(A*r_i) - Q.T*g(Q*r_i)|_2. Its lower-radius construction covers the
entire chord from Q*r_i to A*r_i. It includes both input-coordinate and
output-matrix effects; A is not assumed exactly orthogonal. This respects
decision0023's source-then-rotation path rather than mixing it with the
older rotation-then-source controls.

Use the full pinned Moon200 and Mars120 coefficient arrays, including C00.
Check resource hash, degree/order, array shape, GM and normalization radius
through the existing handoff checks; explicitly retain C00=1 and S00=0.
The existing high-degree vector cutoff and tail remain unchanged. This new
calculation is a full-field norm/Jacobian bound, not an expensive new full
degree120 reference-vector evaluation.

## Retained channels and controls

Report a separate L2 acceleration allowance per body together with matrix
allowance, resource identity, exact rational squared radius, epoch/frame
and zero additional native counters. The squared radius round-trips as an
exact Fraction string; no binary64 radius substitution is made. Timers are
nested within the existing harmonic probe and must not be added to it again.
The preserved handoff and native counters must remain unchanged.

Six analytic controls use degrees 0/2/8 and nonorthogonal scalings 7/8 or 9/8.
At an ideal radius 1/4, the exact zonal force difference is enclosed by the
correct-radius bound but exceeds the bound evaluated at the old radius 1.
The degree 0 case prevents silently dropping the rounded-matrix monopole
effect. Together with existing matrix/source controls, all 87 focused tests
pass in 3.44 s. Full suite: 3060 passed in 473.03 s, native inventory
158.26 s, portable 44.25 s. Ruff, strict OpenSpec, whitespace and legacy
checksum/import isolation pass. Thirteen/zero arcs remain unchanged.

[Retained force errors](../../tests/data/m3_fresh_pck_force_errors.json)
match captured output exactly. Moon's L2 allowance is
3.7424896523222953e-22 m/s^2, Mars's is 2.3275638314181238e-10 m/s^2.
The calculations took 0.63937 s and 0.23372 s inside the existing probe.
Epoch, PCK identity and matrix allowances match decision0024; the previous
common-force output remains exactly unchanged. These are conditional
numerical force bounds, not astronomical orientation uncertainty.

## Next step and limits

Keep these new PCK channels separate until adding each once to the retained
common-force enclosure. That changes its harmonic target from fixed stored
matrices to ideal PCK rotations, with no extra source bridge or harmonic
tail. Then bind the retained native acceleration as an observation against
the independent enclosure. Do not use it to manufacture missing forces.
Native force arithmetic across a domain, incoming spacecraft error balls
and time-domain closure remain open. This is not a mission or trajectory
safety certificate; no production model, tolerance, limit or dependency changes.
