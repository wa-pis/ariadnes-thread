# 0030 — Verify fresh defect channel arithmetic

Date: 2026-09-14. Parent revision: `787ae13`. Task 3.9 remains open.

## Implementation and independent oracle

Add `_fresh_reference_defect_m_s2_m_s3` to the existing error-transport
test module. It implements Decision0029's D/J assembly from seven
nonnegative exact rational channels and a positive finite binary64 horizon.
The function does not compute or certify physical inputs, source coverage
or domain closure; it is not yet connected to the live full-force probe.

Use a scalar manufactured force with a cubic reference q and two continuous
norm-bounded components s*S*(1-2*t/h), s*R*(1-2*t/h), where s is either
sign. They reverse over [0,h], attaining the full 2*S and 2*R changes.
The remaining polynomial force gives the exact signed defect:

    f-q'' = -s*(E0 + (Ej+T+W+2*(S+R)/h)*t + K*t^2/2)

For the implemented D/J pair the exact gap is:

    D+J*t-|f-q''| = 2*(S+R)*(1-t/h) + K*t*(h-t)/2 >= 0

Every term on the right is nonnegative on the entire horizon; sample
checks at zero, midpoint and endpoint verify this algebra, rather than
claiming samples alone prove an interval bound. At h the bound is attained.
Removing one copy of S+R or the K*h/2 rate channel then underbounds the
actual defect whenever the corresponding channel is positive.

Independently integrate the polynomial force to exact position/velocity
with a large position offset and signed incoming state error. Check the
existing envelope encloses that error and retains the incoming radii at
t=0. Cover gravity-only, norm-only and mixed channels, both signs and
zero/nonzero incoming errors: twelve analytic cases. Twenty-one allowance
rejections and five horizon rejections complete 38 new checks. These are
manufactured cases, not new spacecraft simulations or observations.

## Verification

All 38 focused checks pass in 0.07 s. Full pinned suite: 3112 passed in
495.77 s, native inventory 169.66 s and portable 56.42 s. The captured
fresh cubic diagnostic exactly matches its retained Decision0028 artifact.
Ruff, strict OpenSpec and whitespace checks pass. The legacy model hash
remains unchanged and no `src` import references it. Production code,
dependencies, force configuration, scientific tolerances and thirteen/zero
native arc counts remain unchanged. No new native calls or physical
interval qualification are introduced by these analytic controls.

## Next step

Bind the seven channels from the existing fresh native/reference probe
under Decision0029's cumulative-domain premises. Recompute fresh relative
speeds and curvature; do not copy the old D/J pair. Report the channels
before error transport and preserve all old controls, incoming radii,
scientific tolerances and native counts. No targeting or coast extension.
