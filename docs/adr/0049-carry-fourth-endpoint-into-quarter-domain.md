# 0049 — Carry the fourth endpoint into the quarter-second domain

Date: 2026-09-14. Parent revision: `8e1059c`. M3 task 3.9 remains open.
Status: conditional domain handoff evidence, not a fifth native arc.

## Scope

[Decision0048](0048-quarter-second-initial-domain.md) closes an ideal domain
from an exact synthetic initial state. Check whether the already qualified
FOURTH native endpoint and its complete fresh error ball fit that SAME
domain throughout the remaining 0.125 s. No fifth propagation, new force
evaluation or ephemeris request is required for this domain-only question.

The live probe now retains its quarter-domain report in memory. After the
existing exact four-arc lineage check, require matching model/frame/time,
original epoch and initial state. The existing lineage check binds the last
state and epoch to the fresh endpoint report and preserves all prior errors.
Require equal coast mass and use the fresh report's outward outgoing error
radii without resetting them or substituting the old shifted-reference pair.

The new domain spans 978995455.2304223 to 978995455.4804223 TDB seconds.
The fourth native endpoint is at 978995455.3554223; the exact difference to
the domain end is 1/8 s. Its incoming radii for this continuation are
0.00014951281615784107 m and 9.62662340905759e-7 m/s. These retain the
unchanged short-control accuracy gate, not a new mission-level allocation.

## Reused closure argument

Compute L1 position and velocity offsets from the domain's original state
using exact Fractions of the stored binary64 values. Together with the
carried errors, both initial balls must lie strictly inside the original
8000 m / 1 m/s domain. Reuse `_recentered_coast_reaches_m_m_s` with the
NEW quarter-domain uniform acceleration bound 3.2875760444250655 m/s^2:

P = position_offset + incoming_p + (native_speed + incoming_v)*h + A*h^2/2;
V = velocity_offset + incoming_v + A*h.

The position offset is 3815.6269340515137 m; velocity offset is
0.3945295566804816 m/s. The resulting conservative reaches are approximately
7631.304237880287 m and 0.8054775248959558 m/s, strictly inside both radii.
These are reaches relative to the domain anchors, NOT new endpoint-error
radii. The quarter-domain's eight source/guard separation results therefore
apply to this carried ball on the covered remainder, conditional on the
same declared ideal force model. No astronomical uncertainty claim follows.

Fraction calculations retain the incoming binary64 upper bounds exactly;
reported reaches round outward. Source/spacecraft errors are not reset or
added again inside the acceleration bound. Existing operation counters must
still equal 13, with shared budget checks before and after this calculation.
The portable inventory has no native endpoint and emits no carried report.

## Verification

Read-only exact recomputation from the retained domain and endpoint artifacts
closes both bounds. Focused lineage/error-transport tests: 733 passed in
0.85 s. Full suite: 3217 passed in 463.10 s; native/portable inventory
145.37 / 46.14 s. The carried-domain calculation took 0.0002551248762756586 s
inside the existing shared budget, excluding earlier source/domain/lineage
work. This is not a mission-runtime measurement.

The [retained live report](../../tests/data/m3_quarter_second_carried_domain.json)
matches an independent exact scalar recomputation from the previous saved
domain/endpoint artifacts, including outward rounding of both reaches.
The portable mode emits no carried-domain report. Its initial-domain report
still equals the native mode's scientific values. The prior initial domain,
force/SPK contexts, endpoint, cubic, error transport, short clearance, all
coast controls, four-arc lineage and harmonic reuse counts are unchanged
from Decision0048 when excluding timing fields only. Counts remain 13 native
and zero portable arcs. Ruff, strict OpenSpec, whitespace and legacy isolation
pass. Local full-suite JUnit output is under
`/private/tmp/ariadna-quarter-handoff-7hUMZk`; the report above is committed.

## Limits and next step

This qualifies only the state/error-ball domain prerequisite. The nominal
native chain remains four arcs totaling 0.125 s. No position or velocity at
0.25 s has been numerically propagated or assigned an endpoint-error bound.
The previous D/J and sensitivity values remain limited to their old domains.
Before a fifth arc, derive interval-specific reference/defect prerequisites
on the new domain and assess their error budget with the carried radii.
Preserve every accuracy gate, operation cap and shared 300 s budget.
Production acceptance/allocation changes still require review and approval;
native-stage safety, finite burns and task 3.9 remain open.
