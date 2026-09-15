# 0078 — Eight-source nominal gravity with one final rounding

Date: 2026-09-16. Parent revision: `efdb644`. M3 task 3.9 stays open.
Status: stored nominal gravity diagnostic, not a selected trajectory reference.

## Decision and construction

Combine the six existing point-mass intervals with the Mars and Moon harmonic
midpoint/error balls from Decisions0076–0077. Bind every record to the same
fourth epoch, spacecraft state, source context and SSB/J2000 conventions.
Check all five underlying harmonic input hashes against the current records.
Point-force GM values must match their source bridges. Require exactly the
eight physical sources, with disjoint point and harmonic sets: Moon and Mars
already include C00 and MUST NOT also be added as point sources.

Convert the OUTWARD stored point intervals to Fractions; their JSON display
widths are retained, not replaced by reconstructed exact values. Use the
existing midpoint helper to include per-point midpoint rounding. Preserve
the six point-source allowances conservatively, once each. The point boxes
already describe ideal polynomial centres, so these extra source margins
are not necessary to enclose that ideal point value; retaining them preserves
the declared input ledger, not a claim that this sum is the tightest bound.
The two harmonic radii already contain their tails, input allowances and
midpoint rounding; do not add those channels a second time.

Sum all eight binary64 midpoint vectors as exact Fractions. Round the final
vector once and add its L2 rounding radius to the exact sum of the input
radii, using the existing helper. This is the triangle inequality for balls,
not componentwise square-root-of-sum-of-squares of unrelated source errors.
Keep the full inherited spacecraft error as metadata, not silently inside
the nominal gravity radius and never reset to zero.

## Controls and evidence

Three manufactured cases cover cancellation, nonzero final rounding and a
zero-centred sum. All permutations agree. Aligned and 3-4-5 uncertainty
directions remain inside the resulting L2 radius. Five rejection cases cover
an empty set, malformed vectors, nonfinite centres and invalid radii.
The first control mistakenly assumed built-in `sum` performed sequential
float addition; the pinned Python returned 1 rather than 0 for the cancellation
example. The control was corrected to explicit `(a+b)+c`; the algorithm,
enclosure assertions and scientific tolerances were not weakened.

Focused: 9 passed in 0.53 s; replay: 9 passed in 0.54 s.
Evidence: `tests/data/m3_fourth_endpoint_gravity_sum.json`.
Stored-data assembly and checks take 0.00081454 s in the focused observation.
This EXCLUDES generating the previously retained force/input evidence. Zero
new force evaluations, native queries or native arcs; no mission timing claim.

At TDB 978995455.3554223, the nominal J2000 acceleration is
`[-3.14775121720601, 0.002898749565674243, -0.005506634713063707] m/s^2`.

| Error component | Outward reported L2 bound (m/s^2) |
| --- | ---: |
| Sum of all eight input radii | 1.0394510182853207e-8 |
| Final summation/output rounding | 1.6064541573869645e-16 |
| Combined ideal nominal gravity | 1.0394510343498623e-8 |

The retained six point-source margins total 2.765507619020795e-21 m/s^2 and
are ALREADY included in the first row. Mars input uncertainty dominates.
Per-body displayed radii receive a separate outward float step, so adding
those printed numbers need not reproduce the exact pre-reporting sum.
Source/model uncertainty beyond the declared finite resources, native force
arithmetic, SRP, relativity, carried-state and time-domain variation are not
qualified by this gravity sum.

Full suite: 3496 passed in 565.39 s (native inventory 142.62 s, portable
46.24 s, fourth-point Mars diagnostic 33.93 s). The nine new cases account
for the count increase. The gravity report matches focused/replay/full-suite/
retained evidence excluding timers only; assembly/check time is about
0.000815/0.000764/0.000763 s. Generation of the input evidence is excluded.

Against the parent run, all 19 selected native, 6 portable, both Mars and
Moon input/force reports, 5 fourth-point audits, 1 subdivision, prior interval-
jet and prior bounded-force reports remain unchanged. Historical degree-20/
40/100/120 science and call counts also match excluding timers. Native and
portable arcs remain 13/0; harmonic reuse stays 14 requests, 4 misses and
10 hits. Full-suite duration combines independent budgets, not one mission
deadline. Ruff, strict OpenSpec and whitespace checks pass. The legacy model
remains unimported under `src` with unchanged SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Next step

Bind a gravity-only reference candidate to this actual fourth state, gravity
vector and the already qualified monopole-jerk coefficient; verify its existing
conditional reference-domain premises without changing the carried error.
Audit every missing full-force defect/variation channel before any new native
arc or safety claim. A gravity value at one epoch does not validate an interval
or satisfy the remaining runtime gate. M3 stays open; no production reference,
tolerance, allocation or native-call limit changes. Ponytail reuse keeps the
sum test-only, without new dependencies or another force implementation.
