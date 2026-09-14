# 0028 — Construct a separate fresh cubic reference

Date: 2026-09-14. Parent revision: `e7d23cb`. M3 task 3.9 remains open.

## Decision and theoretical scope

Follow Decision0027 without replacing the passing shifted-cubic control.
Construct q(t) = p0 + v0*t + a0*t^2/2 + j0*t^3/6 from the existing fresh
nominal handoff, observed native acceleration qualified in Decision0026,
and the independently enclosed ideal-monopole jerk midpoint. Retain the
jerk enclosure and binary64 midpoint rounding allowance separately. This
jerk is not the complete derivative of all forces.

Use exact rational arithmetic in the existing cubic/reach helpers. The
uniform reference acceleration bound is ||a0||_1 + h*||j0||_1. Check it
against the original cumulative domain acceleration bound; check position
and velocity reaches against the same old-centred 4000 m / 0.5 m/s domain.
The existing conditional true-state reach includes the unchanged incoming
error radii. Both paths lie in this convex product domain, so their
fixed-time chords do too, conditional on the existing true-state premises.

Report exact rational endpoint coordinates and outward-rounded L1 residuals
against the already computed nominal native endpoint. Residuals measure
agreement of two approximations, not distance to the ideal solution.
No incoming errors are reset; no error envelope consumes the fresh
coefficients yet. No old D/J pair is reused and no new defect rate is
assumed zero. Production code, native query/arc counts, deadline and all
scientific tolerances remain unchanged.

## Measured evidence

The retained `tests/data/m3_fresh_cubic_reference.json` matches the captured
live diagnostic. Duration is 0.0625 s from 978995455.2929223 TDB s.
Reference acceleration is bounded by 3.1563164125323384 m/s^2, below the
existing 3.1988547363058646 m/s^2. Reference reaches are
3815.6269057625564 m and 0.39453704896547703 m/s, inside the unchanged
domain. Incoming radii remain 0.00010529778787867129 m and
2.3227467748483292e-7 m/s.

Native endpoint residuals are 4.4180487383045916e-5 m and
1.7476440726817778e-8 m/s. The old shifted-cubic velocity residual is
5.3048424038699204e-8 m/s: the fresh reference agrees more closely with
this native endpoint, but this does not establish a tighter ideal-state
error bound. Existing shifted-cubic nominal/tighter endpoint bounds and
incoming radii remain unchanged.

Full pinned suite: 3074 passed in 494.64 s; native inventory 169.41 s,
portable 55.86 s. Existing thirteen/zero native arcs remain unchanged.
Ruff, strict OpenSpec and whitespace checks pass. The legacy model hash
is unchanged and `src` does not import it. No dependency or production
change. Reused existing analytic cubic/reach controls; the live regression
adds coefficient binding, exact endpoint, domain and preservation checks.

## Next prerequisite

Derive a uniform full-force defect-rate enclosure for this particular
reference, including monopole jerk error/curvature and omitted harmonic,
rotation, SRP and Schwarzschild variation on the already covered domain.
Only then transport the unchanged incoming radii and add the native
endpoint residual once. Do not extend the coast or infer mission safety.
