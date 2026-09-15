# 0074 — Full finite Mars field without an exact degree-120 rerun

Date: 2026-09-15. Parent revision: `9706104`. M3 task 3.9 stays open.
Status: stored-input interval evaluation and consistency controls only.

## Decision and verification contract

Extend the existing degree-100 test with ONE bounded full degree-120
evaluation at each of 80 and 120 significant bits. Reuse the current helper,
coefficient load, historical geometry and one unchanged 300 s deadline.
No exact degree-120 calculation is attempted. The earlier exact degree-100
evaluation and three bounded degree-100 evaluations still count in this same
budget. Prior degree-20/40/100 reports and their checks remain unchanged.

The normalized finite-field interval recurrence already has manufactured
low-degree exact controls (Decision0070) and exact stored-prefix containment
through degree 100 (Decision0073). Here the exact degree-100 prefix plus its
independently bounded finite tail supplies a COARSE consistency enclosure.
Both full boxes must intersect that box, and the midpoint distance must be
consistent with the sum of their L2 radii. The two precision boxes must also
intersect. Full containment in the coarse box is recorded, not assumed.
These checks can reject inconsistency, but agreement does NOT constitute an
independent exact full-vector oracle or establish a general high-degree error
guarantee by itself. No coarse intersection is used to tighten the new bound.

The full helper must return an exactly zero omitted-term tail WITHIN the
degree-120 model. This says nothing about physical terms beyond that ceiling.
The midpoint L2 bound includes output rounding. Displayed component endpoints
are rounded outward separately, so their binary64 box can be wider than the
internal box used for that bound. Finite outward endpoints are checked against
the exact interval endpoints. Input/source/PCK uncertainty is not included.

## Focused evidence

The extended test passed in 79.71 s; shared work took 78.99797 s, including all
six evaluations and setup. One coefficient load; no new ephemeris queries or
native arcs. Evidence: `tests/data/m3_mars_degree120_bounded_evaluation.json`.

| Significant bits | Single evaluation (s) | Midpoint L2 arithmetic bound (m/s^2) |
| --- | ---: | ---: |
| 80 | 13.600751 | 1.0167694815830047e-7 |
| 120 | 14.205080 | 2.0790052437005834e-16 |

Both boxes lie entirely inside the coarse degree-100 enclosure, whose L2
radius is 7.82777879292353e-6 m/s^2. Both rounded midpoints are identical:
`[-3.149870333124269, 0.00328261985255092, -0.005310261738951611] m/s^2`.
Identical midpoints do not mean identical error bounds: the 80-bit enclosure
has grown roughly three orders of magnitude from its degree-100 counterpart.
No 53-bit full evaluation was added after its already poor degree-100 bound.

These are single local observations, not repeated benchmark medians. There
is no measured full-degree exact runtime comparison in this step. The old
over-budget exact experiment is not rerun, and timing is not extrapolated to
the full mission. All calculations use the historical snapshot at TDB epoch
978995455.2929223, SSB/J2000, with pinned resource/array/model hashes. This is
NOT the actual fourth endpoint.

Replay passed in 74.30 s. Full suite: 3485 passed in 529.31 s (native inventory
134.26 s, portable 44.89 s, extended profile 72.28 s). Both new cases match
focused/replay/full-suite/retained evidence after excluding timers only.
Shared work takes 79.00/73.70/72.28 s respectively, below the unchanged 300 s
limit. The full-suite duration combines independent tests, not one mission's
budget. Test count is unchanged because an existing test was extended.

Against the parent run, all 19 selected native, 6 portable, 5 fourth-point
audit, 1 subdivision, prior interval-jet and prior bounded-force reports are
unchanged. All existing degree-20/40/100 profile science and call counts,
including their three bounded comparisons, match excluding timers. Native
and portable arcs remain 13/0; harmonic reuse remains 14 requests, 4 misses
and 10 hits. Ruff, strict OpenSpec and whitespace checks pass. The legacy
model remains unimported under `src`, with unchanged SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Consequences and next step

The finite Mars truncation remainder can now be removed at this historical
stored geometry, at a measured cost and with an explicit arithmetic enclosure.
This does not remove source/PCK/native input errors, other force channels or
reference-transport costs; no working force anchor or production precision is
selected. No tolerances, allocations, native-call limits or production code
change. Ponytail reuse avoids a new evaluator or dependency.

Next audit the inputs and missing error terms needed to bind this evaluator
to the actual fourth endpoint, then perform only the justified bounded check.
Do not silently reuse the historical vector at the new epoch or promote it to
a full-force reference. Task 3.9 and the mission-scale runtime gate remain open.
