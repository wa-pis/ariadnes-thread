# 0077 — Lunar contribution with an explicit finite tail

Date: 2026-09-16. Parent revision: `af642c3`. M3 task 3.9 stays open.
Status: Moon-only nominal fourth-point diagnostic; no gravity sum yet.

## Decision

Parameterize the existing fourth-point input/force test for Mars and Moon,
preserving the Mars algorithm and report fields. Each case keeps its own
existing 300 s diagnostic budget; no combined mission-budget claim follows.
The Moon case checks the same endpoint/source/rotation/force-input bindings,
plus the live pinned degree-200 resource, complete coefficient-array hashes,
GM and reference radius. It explicitly rounds the exact polynomial source
position to binary64 and checks membership in the existing source ball.

Use exact rational prefix recurrences through degrees 2 and 4, with the
existing square-root enclosures. Both evaluations include bounds for ALL
omitted coefficients through the degree-200 model ceiling. Degree 2 is a
coarse consistency control; degree 4 supplies the reported midpoint. No
full degree-200 vector is evaluated, and no field coefficients are discarded
without a bound. Agreement between coarse/fine boxes is not an independent
exact full-field oracle and is not used to tighten the reported error.

The helper expands each prefix by a norm-bounded tail for its returned box.
Undo that expansion using the EXACT Fraction tail before computing the
prefix midpoint error. Then add the tail norm ONCE, plus the existing source
and matrix allowances ONCE each. The generalized Mars branch has zero tail
and must reproduce all previous scientific values. Its input/force report
names remain unchanged even though the test itself now has Mars/Moon IDs.

## Focused evidence

Moon test: 1 passed in 1.30 s. Shared work including setup takes 0.70853 s;
degree-2-plus-tail evaluation 0.04423 s, degree-4-plus-tail 0.04590 s. These
are single local timings, not a mission runtime or precision policy.
Evidence: `tests/data/m3_fourth_moon_bounded_force.json` contains both input
and force reports.

At TDB 978995455.3554223, SSB/J2000, nominal lunar acceleration is
`[8.961377289910998e-11, 4.2202126527480255e-11, 1.4889631992837298e-11] m/s^2`.

| Channel | Outward reported bound |
| --- | ---: |
| Source position rounding, L1 (m) | 1.1229831428572507e-5 |
| Existing source-ball radius (m) | 8.934704095652991e-5 |
| Prefix arithmetic and midpoint L2 (m/s^2) | 2.640227316012839e-27 |
| Finite degrees 5–200 tail norm (m/s^2) | 4.286375449937509e-39 |
| Existing source-force L2 (m/s^2) | 2.455765363926255e-24 |
| Existing matrix-force L2 (m/s^2) | 7.969250975249057e-23 |
| Combined ideal finite lunar field L2 (m/s^2) | 8.215091534373284e-23 |

The degree-4-plus-tail box is inside the degree-2-plus-tail box. The coarse
midpoint radius is 2.7489868561560062e-27 m/s^2. Input allowances dominate,
and even the smaller prefix already had a tiny finite-tail error here; this
does not select a mission-wide truncation degree. All source rounding is
covered by the existing source ball, not counted again as a separate force
error. The matrix bridge is still at the exact ideal-source centre.

One coefficient load per case, zero new native queries/arcs. The carried
state radii remain `[0.00014951281615784107 m, 9.62662340905759e-7 m/s]` and
are not included in the nominal-point field bound. Native force arithmetic,
other forces, time variation and model error beyond degree 200 are excluded.
Printed component intervals include the finite tail but not source/PCK
allowances, and have their own outward binary64 display rounding.

Replay of both cases: 2 passed in 34.54 s. Full suite: 3487 passed in 569.60 s
(native inventory 143.52 s, portable 46.55 s, fourth-point Mars 34.55 s).
Both lunar reports match focused/replay/full-suite/retained evidence excluding
timers only. Lunar shared work is 0.70853/0.14288/0.14681 s respectively;
setup state affects these local timings. Mars input and force reports match
the parent in both replay and full suite, excluding timers. One additional
case accounts for the test-count increase.

All 19 selected native, 6 portable, 5 fourth-point audit, 1 subdivision,
prior interval-jet and prior bounded-force reports also match the parent.
Historical degree-20/40/100/120 report science and call counts are unchanged.
Native/portable arcs remain 13/0; harmonic reuse remains 14 requests, 4 misses
and 10 hits. The full suite combines independent budgets, not one mission's
deadline. Ruff, strict OpenSpec and whitespace checks pass. The legacy model
remains unimported under `src`, with unchanged SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Next step

Assemble a gravity-only nominal diagnostic from these two harmonic terms and
the six already bound point-mass terms at the same epoch/state. Audit all
input allowances, exact interval summation and final output rounding; do not
double count Moon/Mars monopoles or add them again as point sources. That
sum will still not qualify a new full-force reference, its interval defect,
carried-state transport or mission runtime. No native propagation, production
precision, scientific threshold or acceptance allocation changes. Ponytail
reuse avoids a second evaluator and an unnecessary exact degree-200 vector.
