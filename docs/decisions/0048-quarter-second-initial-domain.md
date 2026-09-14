# 0048 — Qualify the quarter-second initial-state domain

Date: 2026-09-14. Parent revision: `f3a080f`. M3 task 3.9 remains open.
Status: conditional ideal-domain evidence, not numerical-arc acceptance.

## Scope and method

Implement the bounded probe from
[Decision0047](0047-bound-the-next-domain-only-probe.md) inside the existing
SPK inventory. Reuse its live physical environment and already qualified
one-second source reaches; recompute all eight distance floors and gravity
norms for an 8000 m position domain, 1 m/s velocity domain and 0.25 s duration.
Recompute SRP and Schwarzschild bounds on those new floors and velocities.
The sum includes both complete harmonic fields and every other declared force.

This uses the original EXACT synthetic initial state at 978995455.2304223 TDB
seconds, with zero initial error by definition of that control. It is not a
measured spacecraft state or the outgoing error ball of the retained four
native arcs. The domain is fixed about that original position and velocity.
Coast mass is 2000 kg above dry mass 1000 kg, with thrust disabled.

The source envelopes include their existing motion, arithmetic and conservative
join allowances exactly as computed by the inventory. Their one-second interval
contains this quarter-second interval. Rotation-invariant gravity norms and a
fully lit SRP upper bound do not require a new rotation-defect or fully-lit
sensitivity calculation. This does not remove those premises from the separate
reference/error-transport checks, which are unchanged.

No ephemeris request or native propagation is added by the new calculation.
The shared budget is checked before/within/after it; operation counters must
remain unchanged. Its report is printed before the final closure assertion so
a failed scientific gate remains visible rather than being relabeled safe.

## Results

The recomputed acceleration bound is 3.2875760444250655 m/s^2, below the
strict 4 m/s^2 closure threshold derived independently in Decision0047.
The outward position reach is 7631.307230552536 m < 8000 m; the velocity
reach is 0.8218940111062665 m/s < 1 m/s. All eight domain-to-source floors
strictly exceed their pinned collision guards. The smallest outward-lower
clearance is 234943.10821885892 m, for Mars.

Consequently this declared initial-state ideal-coast enclosure avoids all
eight guard spheres throughout its covered 0.25 s interval. The smaller
clearance than the prior short-domain result reflects the larger conservative
envelopes; it is not a measured spacecraft altitude or an observed approach.
The larger domain radius is not a relaxed endpoint accuracy tolerance.

This does NOT qualify native internal stages, a fifth numerical arc, an
endpoint error, finite burns or mission-scale safety. The retained numerical
lineage still ends at 0.125 s and its accuracy regressions are unchanged.
Old D/J coefficients and source-dependent derivatives are not extended.

## Verification

Focused distance/mass/transport controls: 837 passed in 0.35 s. The portable
inventory passed in 29.29 s; its new calculation took 0.20326595893129706 s.
This local timer excludes earlier resource setup and source-envelope work;
it is not a mission runtime estimate. Full suite: 3217 passed in 463.75 s,
with native/portable inventory times 144.60 / 47.90 s. The new calculation
took 0.21679204190149903 / 0.2174003329128027 s respectively. No per-mission
performance claim follows from those local observations.

The new scientific report is exactly equal across the focused portable and
both full-suite modes when excluding elapsed time. The
[retained report](../../tests/data/m3_quarter_second_initial_domain.json)
is the full-suite native-mode output. Existing force/SPK contexts, endpoint
binding, cubic reference, error transport, short-domain clearance, all prior
coast domains, exact four-arc lineage and reuse counts match Decision0046's
full output, excluding timing fields only. Counts remain 13 native / zero
portable arcs; harmonic-error reuse remains 14 requests / 4 evaluations /
10 hits. Ruff, strict OpenSpec, whitespace and legacy-isolation checks pass.

Reproduce with the existing inventory test in `tests/test_trajectory_spk.py`
(portable and native-readback parameters) or the full pinned-environment
suite. JUnit captures for this run are local temporary files under
`/private/tmp/ariadna-quarter-domain-UgzB5a`; the JSON above is committed.

## Next bounded prerequisite

Using the new domain's force bound, check closure from the existing fourth
native endpoint AND its carried error ball over the remaining interval.
Require exact epoch/state linkage and include offsets and incoming errors
without reset. This is still a domain check, not a new native arc. Before
any subsequent propagation, separately qualify its reference/defect bounds
and preserve the unchanged accuracy gates. No production acceptance or
allocation change without the required review and user approval.
