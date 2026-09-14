# 0032 — Transport the fresh reference defect to the native endpoint

Date: 2026-09-14. Parent revision: `9a6bd61`. Task 3.9 remains open.

## Implementation and scope

Use the existing `_coast_error_envelope` with Decision0031's outward D/J,
the original uniform domain position/velocity sensitivities, and the
outward incoming radii already reported by Decision0028. Check these
inputs do not shrink the exact incoming bounds. Recheck conditional
true-state domain closure with the rounded radii and the original domain
acceleration bound. The fresh reference inclusion has already been checked;
the convex product domain also contains their fixed-time chords.

The returned position/velocity bounds are relative to the fresh cubic.
Add the retained outward native-to-fresh endpoint residual exactly once to
obtain the conditional ideal-state versus nominal native endpoint bounds.
No old reference residual or anchor/source/PCK channel is added again.
The original shifted-cubic control, native endpoint and incoming handoff
remain unchanged. This result is additional evidence, not replacement of
the earlier control or permission to propagate farther.

Save the finite binary64 inputs and outward outputs in a separate
diagnostic so the exact rational calculation can be reproduced. Gate
flags use the conservative reported endpoint bounds and unchanged
0.001 m / 0.000001 m/s thresholds. A failed gate would be retained as a
scientific result, not hidden by changing a tolerance. Deadline checks
and counter/handoff invariants surround the calculation; no native query,
derivative evaluation or propagation is added.

The bound is conditional on the existing ideal SPK/PCK model and its
domain premises for the 1/16 s interval. It does not measure ephemeris
physical uncertainty, establish statistical confidence, qualify internal
native integration stages, or certify mission safety. Task3.9 remains open.

## Numerical result and decision

The retained `tests/data/m3_fresh_error_transport.json` matches the live
diagnostic and reproduces from its saved inputs. Fresh-reference endpoint
bounds are 0.00010533232877479514 m and 9.451859001789412e-7 m/s.
After adding the native residual once, the outward endpoint bounds are
0.00014951281615784107 m and 9.62662340905759e-7 m/s. Both gates pass.
The calculation takes 0.0001413340214639902 s.

The old shifted-cubic nominal bounds remain 0.00014951220569742958 m
and 9.436498377495054e-7 m/s. The fresh endpoint bound is slightly
looser in both components despite its smaller observed velocity residual.
This matches Decision0027's warning: a better-fitting reference is not
automatically a tighter certificate. Preserve the old control and do not
replace it, claim an accuracy improvement, or pursue tighter fresh anchors
merely because this additional construction exists.

This completes the bounded fresh-reference comparison. The next task3.9
step should audit remaining internal-stage and interval-composition
prerequisites before proposing any additional native arc or longer coast.
Passing either endpoint control alone does not resolve those prerequisites.

## Verification

All 715 focused error-transport tests pass in 0.30 s. Full pinned suite:
3112 passed in 500.78 s (native inventory163.70, portable66.70), unchanged
thirteen/zero native arcs. Ruff, strict OpenSpec, whitespace and legacy
isolation checks pass. Captured old shifted controls and fresh reference/
force/defect diagnostics retain their scientific values, excluding elapsed
times when comparing runs. No production, dependency, force-model,
scientific-tolerance or deadline change.
