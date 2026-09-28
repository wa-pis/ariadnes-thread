# 0027 — Audit fresh reference and transport prerequisites

Date: 2026-09-14. Parent revision: `f5a3b6f`. M3 task 3.9 remains open.

## Existing control is not missing or failing

Read back the latest full-run inventory, specifically its
`conditional_longer_*` fields (the generic `conditional_adjacent_*` fields
are null for this longer case). The existing shifted-cubic control covers
978995455.2929223 to 978995455.3554223 TDB s, a duration of 1/16 s within
the original cumulative 1/8 s domain. Its incoming radii are
0.00010529778787867129 m and 2.3227467748483292e-7 m/s.

The conditional true-state reaches are 3815.627094157525 m and
0.3971959264759999 m/s inside the old 4000 m / 0.5 m/s product domain.
The shifted reference also fits that domain. Its nominal native endpoint
bounds are 0.00014951220569742958 m and 9.436498377495054e-7 m/s, passing
the existing gates. The tighter run is a comparison control, not proof of
mission safety. Preserve these results; fresh reanchoring is an additional
control, not a repair of a failed existing endpoint certificate.

## A point error is not a time-varying defect bound

`_coast_error_envelope` requires |f(t,q,q')-q''| <= D+J*t over the entire
interval and compatible uniform state sensitivities on both paths/chords.
Decision0026 supplies a fresh pointwise acceleration error only. The old
shifted cubic's D/J belong to its own coefficients and time origin. Neither
J=0 nor substitution of the new D while keeping old J is justified merely
by passing endpoint checks or sharing a nominal state.

The old shifted-cubic D is 7.052136533339981e-6 m/s^2, whereas the freshly
qualified native-force bound is 7.853215960348902e-6 m/s^2. Thus the new
anchor is not automatically a tighter bound. Any benefit must be measured
with its own reference coefficients, defect-rate enclosure and endpoint
residual, preserving all previous controls and scientific tolerances.

## Minimal next implementation

Use `_cubic_reference_endpoint` with the existing fresh nominal state,
fresh observed acceleration and already computed fresh monopole-jerk
midpoint. Retain its rounding/enclosure allowance. That jerk models selected
monopoles only; it must not be relabelled as the complete force derivative.
Keep the old shifted reference unchanged.

First check the new reference's acceleration/reach against the same
cumulative domain using `_recentered_coast_reaches_m_m_s`; retain the original
centres, source/PCK coverage, illumination and current domain constants.
The already passing true-state reach is reusable only within that domain;
the new reference and fixed-time chords need their own inclusion check.
Use named fresh coefficients so later midpoint calculations cannot overwrite
them accidentally. This construction needs no new propagation or SPICE call.

Then derive or explicitly rebind a uniform defect rate for this reference:
include monopole curvature and jerk error, all omitted harmonic variation,
rotation, SRP and Schwarzschild effects on the covered domain. Only after
that may the error envelope consume the new D/J and the unchanged incoming
position/velocity radii. Add the native-to-new-reference endpoint residual
once, using the existing adjacent endpoint, rather than launching another arc.

## Verification scope

This is a read-only code/captured-result audit and a documentation change.
Strict OpenSpec and whitespace checks pass; full pytest was not rerun.
Latest implementation remains 3074 passed in 497.09 s, native170.93 s and
portable56.58 s. No new numerical certificate, native call, dependency,
model, limit or tolerance change. Domain closure and native-stage/mission
safety are not inferred from this audit; task3.9 remains open.
