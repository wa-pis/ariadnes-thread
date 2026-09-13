# 0006 — Expose signed point-gravity intervals

Date: 2026-09-13. Base revision: `d644af2`. M3, task3.9.
Status: accepted and verified pure-helper implementation; task3.9 remains open.

## Decision and alternatives

[The ledger](0005-fresh-full-force-ledger.md) identifies six missing fresh
point-gravity vectors. Expose component intervals from the existing point-force
error arithmetic and retain the old comparison API by reducing those intervals.
Do not infer components by subtraction from a native total, introduce another
gravity model or silently round exact source-polynomial positions.

The input is source-minus-spacecraft position as three exact Fractions and
explicit positive finite GM. The output is three signed exact intervals in
m/s^2, J2000 orientation. The pure helper has no epoch binding, source error,
incoming state ball or whole-interval guarantee.

## Argument and verification scope

Let s=sum(r_i^2)>0. The existing guarded square-root helper encloses sqrt(s).
Evaluating GM*r_i/(s*sqrt(s)) at both positive root endpoints and sorting
them handles positive, negative and zero components without changing arithmetic.
Reducing max distance to each interval endpoint reproduces the old L1 error.

Independent controls use rational-radius analytic solutions and
a_i^2*s^3=GM^2*r_i^2 for irrational radii. They include both signs, zero
components, non-dyadic rational scaling, 2^600 and 2^-600 geometry, invalid
GM/coordinates, singularity and exact parity with the original error reduction.
See [new controls](../../tests/test_trajectory_point_vector.py) and the
[unchanged-interface comparison](../../tests/test_trajectory_spk.py).

No production code, kernels, coefficients, tolerances, native limits or legacy
educational model changed. Existing native controls still use the old comparison
API, now reduced through the shared interval helper. No native query or arc was
added; the previous function's arithmetic was extracted, not replaced by a new
physical law. The work also repairs the journal index after the prior path issue.

Reproduce focused checks:

```sh
conda run -n space-nav python -m pytest -q tests/test_trajectory_point_vector.py tests/test_trajectory_spk.py -k 'point_vector or point_gravity_anchor'
```

## Next step

Verification: 42 focused tests pass in 0.62 s (34 new cases and 8 existing
point-force checks); all 2857 tests pass in 466.49 s. Native inventory takes
139.06 s and portable inventory 40.51 s; existing thirteen/zero native-arc
assertions pass. Ruff, strict OpenSpec and unchanged legacy-file hash pass.
These timings are observations, not a performance guarantee. No scientific
values or tolerances changed. The previous complete baseline was 2823 tests;
the 34 additional cases qualify the pure interval helper only.

Bind this pure helper to the six point-gravity bodies at the existing handoff,
using exact fresh source-polynomial positions and the preserved nominal state.
WHEN epoch/coverage, state shape or body/GM sets mismatch, THEN reject before
composition; verify independent moving-source examples and unchanged native
query/arc accounting. Keep Moon/Mars monopoles inside their harmonic terms.
Source arithmetic bridges, SRP, relativity, state-ball and domain gaps from the
ledger remain separate. Task3.9 is not completed by this helper.
