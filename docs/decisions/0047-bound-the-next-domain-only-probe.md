# 0047 — Bound the next domain-only probe before propagating

Date: 2026-09-14. Parent revision: `cf33120`. M3 task 3.9 remains open.
Status: accepted investigative scope; proposed domain NOT yet qualified.

## Finding: a fixed spatial anchor limits the present closure estimate

The retained first nominal state in
[`m3_nominal_four_arc_lineage.json`](../../tests/data/m3_nominal_four_arc_lineage.json)
has SSB velocity L1 upper speed 30524.817975204583 m/s. This is a sum of
absolute components, not the Euclidean speed or Mars-relative speed.
The existing fixed-anchor reach uses speed*h + A*h^2/2 for this exact
synthetic initial state, with a nonnegative acceleration-norm bound A.

Its speed term alone exceeds the current 4000 m radius at h=0.25 s:
7631.204493801146 m. Strict closure with this formula already requires
h < 4000/speed = approximately 0.13104091245520985 s, even before acceleration.
This is an obstruction to this sufficient estimate, NOT a lower bound on
actual displacement, an actual domain exit, a collision or mission failure.
It explains why changing only endpoint defect accounting cannot extend the
current fixed domain. Moving-reference domains are a possible later option;
they need their own source-distance and closure argument, not a frame rename.

## A bounded next question

Test only the initial exact synthetic Mars state over a cumulative 0.25 s,
with an 8000 m position radius and 1 m/s velocity radius about its original
state. These are proposed domain parameters, NOT changed accuracy tolerances.
This is not a fifth native arc or a transported numerical handoff.

For the same scalar reach formula, the independently derived constraints on
a NEW uniform acceleration bound are:

- Position: A < 2*(8000-speed/4)/(1/4)^2 = approximately
  11801.456198363343 m/s^2.
- Velocity: A < 1/(1/4) = 4 m/s^2; this stricter condition also makes the
  position reach less than 7631.329493801146 m, hence less than 8000 m.

These exact Fraction inequalities were checked from the retained state.
No new A was evaluated. In particular, the old 3.1988547363058646 m/s^2
on the 4000 m / 0.125 s domain cannot certify the larger domain.

## Reuse boundary and minimal calculation

Read-only source audit: `tests/test_trajectory_spk.py`,
`_check_conditional_full_force_coast_domains`; `src/space_nav/trajectory.py`,
the distance, gravity, thrust/SRP, Schwarzschild, sum and reach bounds.

The inventory ALREADY computes conservative source reach envelopes for
1/64, 1/32, 1/16, 1/8 and 1 s. The existing one-second envelopes can bound
source positions on its initial quarter-second subset. They include the
source arithmetic allowances and conservative record-join terms already;
do not add those same errors again. Use the existing live environment and
these envelopes, not new ephemeris calls or copied scalar force results.

Recompute all eight distance floors using the 8000 m spacecraft radius and
the covered ONE-SECOND source envelopes. Require every floor to exceed its
pinned guard. Recompute the eight gravity-norm bounds (including Moon 200
and Mars 120), fully lit SRP upper bound and Sun Schwarzschild upper bound
using the new 1 m/s velocity radius. Coast thrust is zero and mass remains
2000 kg above dry mass 1000 kg. Sum outward, then test strict position AND
velocity closure over 0.25 s. Check epoch containment and shared budget
before and after the calculation.

The existing gravity norm bound is rotation invariant. The existing SRP
norm bound applies also in shadow because shadow does not increase it.
Thus this DOMAIN-ONLY calculation does not need new harmonic vector replay,
PCK rotation-defect channels, fully-lit sensitivity proofs, Jacobians, D/J
transport or native endpoints. Those remain necessary where used by the
separate reference/native accuracy argument; they are not deleted or
silently extended. Preserve all existing resource and model checks.

## Cost and verification limits

The parent full-suite observation was 3217 passing tests in 465.22 s;
native inventory 144.78 s, portable inventory 50.23 s. Its 14 harmonic-error
requests comprised 4 uncached evaluations and 10 exact-input hits, with
13 native arcs. These whole-test timings neither measure the proposed
calculation nor establish a per-arc cost or mission-scale runtime margin.
No new performance estimate is inferred from them.

The proposed check uses existing finite coefficient-norm sums instead of
the expensive exact native harmonic-vector oracle. Measure its own elapsed
time within the EXISTING inventory budget; do not reset the 300 s clock.
Require zero additional native arcs and zero additional ephemeris queries,
and report failure/unresolved closure without altering the old controls.
Only after a passing domain-only probe should another numerical endpoint
or enlarged-interval defect certificate be considered.

This commit changes documentation only. Exact read-only scalar checks,
Ruff, strict OpenSpec, whitespace and legacy isolation checks pass. The
runtime/tests match the parent; the full suite was not rerun for prose.
No production acceptance/allocation, native cap, force model, UI or accuracy
gate changes. Task 3.9 and native-stage/finite-burn safety remain open.
