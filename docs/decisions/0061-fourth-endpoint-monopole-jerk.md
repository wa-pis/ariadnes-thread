# 0061 — Bind ideal monopole jerk at the fourth endpoint

Date: 2026-09-15. Parent revision: `29a8d9e`. M3 task 3.9 stays open.
Status: nominal derivative prerequisite, not a uniform defect-rate bound.

## Decision and method

Reuse `_fresh_monopole_jerk_intervals_m_s3` at the actual fourth endpoint
978995455.3554223 TDB seconds since J2000. Reconstruct all eight exact
source states from the same live reanchor report; its last three components
are derivatives of the POSITION polynomials, not independently stored
SPK type-3 velocities. Combine them with the actual nominal spacecraft
position/velocity and each live environment GM. Explicit epoch/coverage
binding retains the source interval ending at 978995455.4804223.

For relative r=spacecraft-source and v=spacecraft velocity-source derivative,
the existing interval helper encloses
`-GM*v/|r|^3 + 3*GM*r*(r dot v)/|r|^5`. It includes source motion; setting
source velocities to zero would be a different derivative. All eight bodies
must be present. Moon and Mars contribute ONLY their monopoles to this
derivative proposal; their nonmonopole fields and rotation still require
separate rate/remainder bounds. The production gravity inventory is unchanged.

Sum component intervals exactly. Form their exact midpoint, convert it once
to binary64, and bound its L1 error by the sum of interval half-widths plus
the COMPLETE midpoint rounding error. This also bounds L2. Outward reporting
is checked against every exact interval and the exact summed error. Do not
reconstruct this tight midpoint error from the wider serialized component
intervals, which include their own reporting roundoff.

Retain each body's intervals, all GMs, midpoint/error, actual nominal state,
source-context/epoch/frame/model links and one calculation timer together.
Data come from the current inventory, not saved JSON. No ephemeris query or
spacecraft arc is added; shared budget and native counters remain unchanged.
The report is emitted only where an actual native fourth endpoint exists.

## Interpretation

This is ideal nominal MONOPOLE jerk in m/s^3, not full gravitational jerk,
full-force jerk, or the uniform J in a D+J*t defect inequality. Its midpoint
could later be used as a reference coefficient only after that reference's
gravity acceleration anchor, domain and all defect channels are qualified.
The tiny midpoint interval width reflects mathematical/arithmetic enclosure,
not source uncertainty, spacecraft uncertainty or mission predictability.
Source/native arithmetic and carried errors are not included in these vectors.

## Verification

- Retained report: `tests/data/m3_fourth_endpoint_monopole_jerk.json`.
- Summed midpoint (m/s^3): `[-4.764591314473001e-7,
  -0.001279146854859377, 6.446849513688822e-10]`.
- Exact-interval plus midpoint-rounding L1 allowance:
  `1.4379857137182707e-20 m/s^3`; not physical uncertainty.
- Additional calculation: `0.009855791227892041 s`, zero additional
  ephemeris queries and zero additional native arcs.
- 46 focused jerk controls passed in 0.57 s. Full suite: 3277 passed in
  462.77 s (native inventory 143.63 s, portable 46.42 s). Suite duration
  includes separate tests, not one mission's shared 300 s budget.
- All 18 prior native and 6 prior portable selected scientific reports
  matched the parent run exactly after excluding calculation timers only.
  The new report is absent from the portable branch. Native/portable arc
  counts remain 13/0; harmonic reuse remains 14 requests, 4 misses, 10 hits.
- Read-only replay from retained exact source polynomials and endpoint
  reproduced all eight intervals, midpoint and error exactly; checked
  epoch, coverage, state, GM, model and source-context bindings.
- Ruff, strict OpenSpec validation, whitespace checks and unchanged legacy
  model SHA-256 passed. No production code or acceptance threshold changed.

## Next bounded step

Assess the uniform monopole Taylor remainder on the remaining interval:
bind the new relative velocities, covered source curvature, domain floors
and an explicit bound on the proposed reference acceleration. That last
premise must not be silently borrowed from a different reference. Then add
nonmonopole translation/rotation rate channels and compare their coupled
budget before expensive vector work. No new cubic or fifth native arc is
qualified here; no tolerance or production acceptance change.
