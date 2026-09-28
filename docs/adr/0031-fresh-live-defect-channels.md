# 0031 — Bind fresh defect channels to the existing physical probe

Date: 2026-09-14. Parent revision: `9cc37f7`. Task 3.9 remains open.

## Implementation and provenance

Use the tested Decision0030 channel assembler inside the existing fresh
nominal native/reference probe. Bind its epoch, duration, initial state and
model to Decision0028. Assert containment in the existing fresh guarded
source interval, original source-polynomial coverage and PCK time domain.
Reuse the already checked 4000 m / 0.5 m/s cumulative domain; do not move
its centres or infer closure from the newly returned D/J values.

Recompute all eight relative source speeds from the fresh ideal polynomial
derivatives. Retain the original uniform source acceleration bounds and
verify fresh/old derivative differences against their elapsed-time bound.
Use the fresh reference acceleration bound plus each source acceleration
bound in the existing monopole curvature helper. Recompute Moon/Mars
nonmonopole translation rates with the qualified degree-map Jacobians.

Reuse partitioned rotation variation only as its previously checked
linear rate: divide by the ORIGINAL cumulative 1/8 s duration, not the
fresh 1/16 s interval. Keep the uniform SRP and Schwarzschild norm channels
separate; the assembler doubles these changes in D. The anchor channel
uses the already qualified native-to-ideal full-force error; the jerk
channel retains its ideal-monopole enclosure/rounding allowance.

Round the seven exact nonnegative channels upward to binary64 before
assembly and check every rounding inequality. The saved inputs therefore
reproduce the exact rational D/J assembly without retaining enormous
intermediate polynomial fractions. Round the returned D/J upward again
for reporting. Do not add source/PCK anchor errors a second time.

The added loop checks the shared deadline and preserves the native
control/evaluation/arc counters and incoming handoff. Its timer is inside
the existing full probe, outside the earlier harmonic-only timer. There
are no additional SPICE, derivative or propagation calls.

## Captured numerical evidence

The retained `tests/data/m3_fresh_defect_channels.json` matches the live
diagnostic exactly. For h=0.0625 s its outward D is
7.943095084820736e-6 m/s^2 and J is 0.00011082532101285457 m/s^3.
Nonmonopole translation contributes 8.72535388619181e-5 m/s^3 and
rotation 2.3007359855671667e-5 m/s^3; monopole curvature is
1.8061513448472072e-5 m/s^4 before multiplication by h/2.
The added computation takes 0.0007749160286039114 s. These are conditional
model bounds, not measured physical errors or a statistical confidence level.

All 38 focused channel tests pass in 0.07 s. Full pinned suite: 3112
passed in 553.58 s (native inventory198.76, portable84.60), unchanged
thirteen/zero arcs. Ruff, strict OpenSpec, whitespace and legacy isolation
checks pass. No production code, dependencies, force model, tolerance or
deadline change. Saved channel inputs reproduce the reported outward D/J;
prior fresh reference/force and longer shifted controls retain their
scientific data, excluding elapsed times in run comparisons.

## Scope and next step

This binds a conditional D+J*t acceleration-defect bound along the fresh
reference on the existing ideal SPK/PCK domain. It does not yet transport
incoming position/velocity errors, qualify native internal stages, extend
the coast or certify a mission. The previous shifted-cubic control remains
unchanged. The historical Decision0028 diagnostic still states its own
reference-only scope; this separate diagnostic supplies the new channels.

Next use the existing error envelope with this pair, uniform domain Lx/Lv
and unchanged incoming radii; add the retained native-to-fresh endpoint
residual exactly once. Report gate success or failure without modifying
scientific tolerances or interpreting agreement as mission safety.
