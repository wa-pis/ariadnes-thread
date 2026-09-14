# 0053 — Bind six point forces to the fourth endpoint

Date: 2026-09-14. Parent revision: `e87904e`. M3 task 3.9 remains open.
Status: nominal point-force prerequisite only; no fifth native arc.

## Decision and scope

Continue Decision0052 by passing its live exact source states and covered
epochs into the existing coast inventory. After the fourth native endpoint
and its lineage/carried domain have been checked, reuse
`_fresh_point_gravity_intervals_m_s2` with that actual endpoint and the live
environment's gravitational parameters. Do not load saved source JSON as a
runtime fallback or construct another spacecraft propagation.

The helper requires the source epoch to equal the endpoint epoch and source
coverage to contain the proposed remaining interval. Its six sources are Sun,
Mercury, Venus, Earth, Jupiter and Saturn. Moon and Mars are deliberately absent:
their monopoles belong to the harmonic fields, exactly once. Exact rational
source coordinates retain their hexadecimal numerator/denominator encoding
across the in-memory handoff. Outward float interval reports are checked against
every exact component bound before serialization.

The source anchor is 978995455.3554223 TDB seconds since J2000; coverage ends at
978995455.4804223. Acceleration components are in m/s^2, in SSB/J2000. These are
nominal ideal-polynomial point forces at the anchor, NOT uniform force bounds
throughout that interval. Source arithmetic and the incoming spacecraft error
ball are not part of these component intervals. The full carried error pair is
reported separately as metadata, unchanged, rather than silently reset.

The report is emitted only in native-control mode because it requires the
actual retained endpoint. Portable mode still checks the source anchor but must
not fabricate a spacecraft endpoint. Shared budget checks and the unchanged
native counters surround the additional calculation.

## Verification

56 focused point-vector/binding controls pass in 0.72 s. Full pinned suite:
3217 passed in 524.51 s; native/portable inventory 161.59 / 52.47 s. The full
suite is not a single 300-second mission run. The added point calculation
itself took 0.0013092500157654285 s in this run, excluding earlier source,
environment and endpoint work; this is an observation, not a runtime guarantee.

The [retained report](../../tests/data/m3_fourth_endpoint_point_gravity.json)
contains all eighteen outward component intervals and the exact binary-float
nominal endpoint, six live GMs, source-context link and carried error metadata.
That pair remains 0.00014951281615784107 m / 9.62662340905759e-7 m/s.

Read-only comparison against Decision0052's full JUnit output preserves all
prior source/domain/sensitivity, force-context, endpoint/reference/error,
clearance, coast-domain, lineage and reuse reports, excluding timing fields
only. The new report is correctly absent in portable mode. Counts remain
13 native / zero portable arcs; native harmonic reuse remains 14 requests,
4 uncached evaluations and 10 hits. Ruff, strict OpenSpec, whitespace and
legacy checksum/isolation checks pass. No production code or dependencies changed.

Reproduce with the existing native SPK inventory test; analytic controls are
in `tests/test_trajectory_point_vector.py`. This run's JUnit log is under
`/private/tmp/ariadna-fourth-point-c2j7y2/full-suite.xml`.

## Next bounded step

Qualify the remaining Moon/Mars harmonic anchor contributions and their
arithmetic/resource premises at this endpoint. The old harmonic vector error
must not be transplanted. Light/relativity and the new reference's coupled D/J
channels also remain separate prerequisites. This result does not qualify a
full-force reference, native stages, targeting or mission safety; no scientific
tolerance or production acceptance rule changes.
