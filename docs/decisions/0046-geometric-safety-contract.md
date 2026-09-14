# 0046 — Separate geometric clearance from accuracy

Date: 2026-09-14. Parent revision: `532f812`. M3 task 3.9 remains open.
Status: accepted analytic evidence; no production acceptance change.

## Question and sufficient conditions

Following [Decision0045](0045-tolerance-purpose-and-step-limit-audit.md),
what does a conditional collision-clearance certificate actually need?
Reuse the existing domain enclosure, not another chord model or status API.

For a single shared interval and pinned force/resource context:

1. The initial true-state enclosure must lie inside the declared position
   AND velocity domain. Burns additionally require a valid mass domain.
2. Source envelopes must cover the entire interval, including source
   representation errors and motion. All force bounds must be uniform on
   that domain and interval, not sampled only at its anchor.
3. A first-exit argument must close the transported state inside that domain
   throughout the interval. Strict inclusion is required by the existing
   closure controls. A mass lower bound must remain valid for mass-dependent
   forces; position closure alone does not establish it.
4. For EVERY collision body, the outward-rounded lower distance between the
   spacecraft domain and the source envelope must strictly exceed the pinned
   guard radius. Include each source/spacecraft allowance once. The existing
   physical control has eight guards; the analytic family below has one.

Under these premises, every covered ideal-model position avoids every guard.
This is a sufficient condition, not a necessary test of physical clearance.
Missing coverage or failed closure/floor leaves clearance unresolved (or
raises the existing input/resource error), never automatically safe or an
impact. An independently observed initial impact remains an impact.
Completed native integration and endpoint agreement do not supply these
whole-interval premises. Native-stage safety remains a separate open issue.

Accuracy regressions, integrator settings, arc continuity and full-command
nominal/tighter validation remain independent, unchanged gates. No numerical
agreement value is substituted for a rigorous enclosure radius. These bounds
are conditional on the declared model, not astronomical uncertainty estimates.

## Analytic evidence

`tests/test_trajectory_distance_bound.py` adds 16 cases combining two initial
error pairs, two velocity-domain radii and four guard choices. In SI units,
for 0 <= t <= h = 1/2, the worst signed family is
ship(t) = 10 - ep - (1 + ev)t - t^2, body(t) = eb + t/2,
with eb = binary64(0.05). Fractions retain the input binary64 values exactly.
Acceleration -2 is uniform; the independent minimum separation is
10 - ep - eb - (3/2 + ev)h - h^2. The difference at any earlier t factors as
(h-t)(3/2 + ev + h+t), proving the minimum without a sampling assumption.

The existing position-reach and distance-floor helpers are composed with
the existing position/velocity closure helper. A 7 m guard is certified
only with the closed domain, for both small and larger initial error radii.
The larger radii exceed the example's separate 0.001 m / 1e-6 m/s accuracy
gate. This does NOT pass a failed physical endpoint regression. An 8 m
guard and equality to the computed floor remain unresolved even though the
exact path is clear. A 10 m guard has an independently known initial impact.
A failed velocity closure cannot be bypassed by positive position clearance.

Existing controls cover velocity-dependent force, singular domains,
first-exit closure, mass-floor failure and expired/invalid inputs. No new
production helper, dependency, source query, physical interval or native arc
is introduced. Decision0034's retained physical clearance is not extended.

## Verification

Focused distance/mass suite: 122 passed. Full pinned-environment suite:
3217 passed in 465.22 s (native inventory 144.78 s; portable 50.23 s).
The complete suite is not one 300-second mission calculation. Exact
scientific comparison with Decision0044's full-suite output preserves the
force/SPK contexts, endpoint binding, cubic reference, error transport,
conditional clearance, full-force domains and four-arc lineage; only timing
fields are excluded. Existing counters remain 13 native arcs / 0 portable.
Ruff, strict OpenSpec and whitespace checks pass. The legacy model checksum
is unchanged and the new package still does not import it.

Local verification output: `/private/tmp/ariadna-geometric-contract-WathDf/full-suite.xml`.
This temporary log is not a retained repository artifact; the checked-in
analytic tests and existing physical fixtures provide repeatable evidence.

## Next bounded prerequisite

Assess which existing force/domain bounds can be recomputed on a proposed
larger interval and what their resource cost is, before attempting that
interval. Do not reuse old D/J coefficients or source coverage as an
unproved extension of spacecraft closure. Require explicit review and user
approval for any production acceptance/allocation change. Task 3.9, finite
burns, native-stage protection and mission-scale runtime remain unqualified.
