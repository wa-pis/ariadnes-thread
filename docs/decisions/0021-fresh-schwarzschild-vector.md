# 0021 — Enclose the fresh Schwarzschild vector

Date: 2026-09-14. Parent revision: `2d23e46`. M3 task 3.9 remains open.

## Signed formula and preserved controls

Extract `_schwarzschild_intervals_m_s2` from the existing anchor-error
helper in the test suite. Preserve its exact binary64-to-Fraction state
conversion and dyadic square-root enclosure. For r = spacecraft - Sun,
v = spacecraft velocity - Sun velocity, mu = GM_Sun and c = 299792458 m/s,
the PPN beta = gamma = 1 formula is

    a_i = 4*mu^2*r_i/(c^2*|r|^4)
          + mu*(-|v|^2*r_i + 4*(r.v)*v_i)/(c^2*|r|^3).

The first term is rational. Evaluate the second term at both enclosing
radius endpoints and keep their minimum/maximum for each signed component.
The old error API reduces these intervals to its original L1 distance from
the supplied observation; existing exact-geometry, irrational-radius and
native anchor comparisons remain regressions. There is no subtraction of
the native total force to manufacture an independent component.

## Fresh input and source-state bridge

Pin the retained light, Sun GM and velocity-binding artifacts by SHA256.
Require the same fresh epoch, SSB/J2000/model and full Sun state; require
the qualified type2 derivative convention and matching velocity allowance.
The spacecraft state and GM are fixed exact stored inputs.

Reuse the existing distance-floor helper with the Sun position allowance
and zero spacecraft uncertainty. Verify the exact squared inequality
(d + epsilon_p)^2 <= |r|^2. Thus every point of the stored-to-ideal source
chord stays at distance at least d. Use V = |v|_1 + epsilon_v; the triangle
inequality bounds the relative L2 speed over that entire chord.

The existing analytically qualified Schwarzschild Jacobian bound gives
J_position*epsilon_p + J_velocity*epsilon_v. The source allowances are L1
bounds and therefore valid L2 radii. Add that source-state allowance once
to the signed-box midpoint L2 rounding allowance. The resulting ball targets
the exact Sun position polynomials and their derivatives at the fixed
nominal spacecraft state, consistently with the other ideal-source forces.
Do not re-add this source allowance when composing the later total.

## Verification and limitations

Eight signed-component examples include negative/zero forces and a common
large position/velocity offset. Twelve axis/sign source perturbations retain
both radius interval widths in their L2 comparison against the existing
variation bound. Five invalid-GM controls and one pinned fresh case are
added; the prior error/Jacobian tests remain intact. All 103 focused checks
pass in 0.51 s. Full suite: 3016 passed in 473.52 s, native inventory
152.63 s, portable 50.87 s. The thirteen/zero arc assertions and forty
readbacks remain unchanged. Ruff, strict OpenSpec, whitespace and legacy
checksum/import isolation pass.

[Retained result](../../tests/data/m3_fresh_schwarzschild_vector.json)
matches the full-run diagnostic exactly. Midpoint is
(-4.017496453235729e-11, 6.375567429189403e-12, 4.030281723374813e-12)
m/s^2. The outward L2 allowance is 3.293019657772923e-27 m/s^2, composed
before rounding from midpoint and source-state channels (reported separately
as 2.9165445267917088e-27 and 3.764751309812138e-28 m/s^2). These are
conditional numerical bounds, not physical parameter uncertainty.

No production API, native query, arc, force setting, dependency, tolerance
or runtime limit changes. This bound is numerical, not uncertainty in the
astronomical observations or spacecraft parameters. PCK/native arithmetic,
incoming spacecraft error balls and time/domain closure remain separate.
Next compose the retained gravity, SRP and Schwarzschild vectors and their
named error channels once at the common fresh state; this is still not a
complete trajectory-safety or mission-accuracy certificate.
