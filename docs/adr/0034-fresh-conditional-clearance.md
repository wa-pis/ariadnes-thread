# 0034 — Bind interval clearance to the existing domain certificate

Date: 2026-09-14. Parent revision: `d1d312a`. Task3.9 remains open.

## Implementation

Follow Decision0033 in the existing fresh probe, after rounded incoming
error transport/domain checks. Require the complete eight-body set and
match collision guard radii to the environment's verified PCK resource.
Retain its pinned SHA256. Reassert source/PCK coverage and the conditional
true-state position/velocity inclusion for the same cumulative domain.

For each body subtract its collision guard radius from the existing
uniform relative distance floor using exact rational arithmetic. Round
the margin downward, and require a finite positive result no greater than
the exact margin. Since the conditional ideal trajectory remains in the
domain and each source remains in its covered reach, the positive margins
apply throughout the fresh interval, not merely at the native endpoint.

Report both floor and guard radius so each margin can be independently
recomputed. Include the interval, original cumulative domain/time origin,
source/PCK coverage, model identity, incoming error radii and thrust-off
coast mass/dry mass. Do not use harmonic or orbit radii as collision guards.
No endpoint tolerance is used to infer clearance.

The calculation preserves the handoff and native counters and checks the
shared deadline. It adds no SPICE, derivative or propagation call. Its
timer is inside the existing full probe, separate from prior sub-timers.

## Captured evidence and verification

The retained `tests/data/m3_fresh_conditional_clearance.json` matches the
live diagnostic. All eight margins are positive; the minimum is Mars at
283007.82847962243 m above its 3396190.0 m collision guard, using a
3679197.8284796225 m distance floor. This is a conservative domain margin,
not measured altitude or a new nominal closest-approach result. The fresh
interval spans 978995455.2929223 to 978995455.3554223 TDB s inside the
unchanged cumulative domain. Added arithmetic takes 0.00003079092130064964 s.

All 715 focused error-transport tests pass in0.30 s. Full pinned suite:
3112 passed in502.97 s (native164.95, portable68.35), unchanged thirteen/
zero native arcs. Ruff, strict OpenSpec, whitespace and legacy isolation
pass. Retained margins reproduce by downward rounding exact floor-minus-
guard differences; previous fresh and shifted scientific controls are
unchanged apart from elapsed-time fields. No production, dependency,
force-model, scientific-tolerance or deadline change.

## Limits and next step

This is conditional ideal-coast clearance from the eight configured
collision spheres over the existing 1/16 s interval. It is not a native
internal-stage certificate, a finite-burn dry-mass proof, a general
ephemeris physical-uncertainty statement or mission safety. Previous
reference/defect/endpoint controls remain unchanged; no coast is extended
and no production safe-result reader is invoked.

Next audit the interval-screening/native-rejection composition boundary
in the existing analytic controls and production readers before proposing
new native work. In particular, conditional physical-path clearance and
handling of rejected numerical trial states are different obligations.
Preserve incoming uncertainties and account for all discarded parents and
attempts; task3.9 remains open.
