# 0011 — Bind six point-force source-position errors

Date: 2026-09-14. Parent revision: `05f85d2`. M3 task3.9 remains open.

## Composition and independent check

Decisions0008–0010 supply conditional source allowances, exact same-epoch
consumer identity and nonsingular comparison-chord floors. Reuse these
contracts inside the existing fresh native control, without new helpers,
SPICE requests, derivative evaluations or propagation arcs.

For each of Sun, Mercury, Venus, Earth, Jupiter and Saturn, use the existing
GM, cached source position, nominal spacecraft position and chain allowance.
Recompute the downward distance floor at that same epoch with the existing
position-ball helper and verify its exact squared inequality. Do not reuse
an old-epoch floor or substitute a rounded ideal-polynomial coordinate.

For a(r) = GM*r/|r|^3 the Jacobian is
GM/|r|^3 * (I - 3*u*u^T), with u = r/|r|. Its radial eigenvalue is
-2*GM/|r|^3 and its two tangential eigenvalues are GM/|r|^3. Thus the induced
Euclidean norm is 2*GM/|r|^3. Integrating along the whole comparison chord,
which remains at radius at least d > 0, gives the existing bound

    |a(stored) - a(ideal)|_2 <= 2*GM*epsilon/d^3.

The implementation uses exact Fractions for this formula and rounds only the
reported allowance upward. The previous independent radial and transverse
analytic controls remain unchanged, including a case detecting a missing
factor two and rejection of singular floors.

Separately evaluate the existing exact point-force intervals at the stored
source coordinates. Compare with the already computed ideal-polynomial
intervals. If these intervals are [a,b] and [c,d] for a component, the maximum
possible absolute difference is max(|a-d|, |b-c|). Sum the squares for all
three components and require that sum <= the squared theoretical allowance.
All interval widths remain included; no empirical fit reduces epsilon.
This endpoint cross-check is not the proof for all chord points: that proof
is the distance-ball and Jacobian argument above.

The check requires exactly the six point bodies, preserves the selected
handoff and incoming error radii, and verifies unchanged native counters.
Its diagnostic records epoch, frame, GM, source allowance, floor and outward
L2 force allowance, plus elapsed time within the shared 300-second budget.

## Limits and next step

This bounds only the effect of conditional source-position arithmetic on
ideal point-force evaluation at a fixed nominal spacecraft state. It does
not bound native force arithmetic, physical ephemeris uncertainty, GM
uncertainty, spacecraft-state errors or time variation. No full-force sum
or trajectory envelope is modified.

Moon/Mars are intentionally excluded to avoid counting their monopoles
twice. Their source errors require the qualified harmonic spatial bounds
and stored rotation-matrix factors. PCK, SRP, relativity, incoming state balls
and interval/domain closure still need explicit composition. Task3.9 remains
open, with no coast extension or targeting qualification.

## Verification and retained result

All 137 focused distance/point-vector/point-variation checks passed in 0.62 s.
Full pytest: 2887 passed in 467.80 s. Native inventory 141.88 s, portable
47.90 s; the existing thirteen/zero arcs and forty source-readback assertions
pass. Added binding/calculation/report preparation takes 0.0009616250172257423 s
in this run; this is an observation, not a timing guarantee. Ruff, strict
OpenSpec, whitespace and legacy checksum/import isolation pass.

[Retained diagnostic](../../tests/data/m3_fresh_point_source_errors.json)
exactly matches captured full-run output. The largest of these six conditional
source-position effects is the Sun allowance, 2.526170485809471e-21 m/s^2.
Its small size does not bound other omitted errors or justify dropping them.
No production code, resource, dependency, scientific tolerance or limit changed.
