# 0075 — Bind rounded polynomial inputs before moving the Mars evaluator

Date: 2026-09-16. Parent revision: `e23a663`. M3 task 3.9 stays open.
Status: stored fourth-endpoint input audit; no new force evaluation.

## Decision

The degree-120 evaluator accepts binary64 source and spacecraft positions.
The fourth-endpoint source archive retains exact rational SPK polynomial
positions and native residual bounds, but not the native position vectors.
Do not relabel a rounded polynomial position as a native readback. Instead,
audit that explicit rounded point against the already qualified source ball,
without changing or reducing its radius. This avoids another ephemeris query
and leaves the production direct-SPICE path unchanged.

The new test binds five existing evidence records by epoch, model, SSB/J2000
conventions, spacecraft state, source context, PCK/pool and rotation hashes,
coefficient hash/degree, GM and reference radius. It reconstructs the exact
relative position and squared radius used by both force-input bridges.
The live coefficient resource must still match its pinned hash. Historical
profiling geometry is explicitly different: its epoch is 1/16 s earlier.
No historical acceleration value is imported into the fourth-point evidence.

## Measured input check

Actual fourth epoch: TDB 978995455.3554223. Rounded ideal Mars source position:
`[-245060528270.93192, 35261267088.76203, 22783596668.40478] m`.

Exact subtraction before outward reporting gives an L1 rounding bound of
`4.241708265417352e-6 m`. This is inside the unchanged source-ball allowance
`0.0001648618821045329 m`. It is not a new astronomical uncertainty estimate,
nor a measurement of the production ephemeris error.

The existing full degree-120 stored-matrix source-force allowance is
`1.023753899662649e-8 m/s^2`. The stored-to-ideal PCK force allowance is
`1.5697109459316845e-10 m/s^2`. The rounded point lies in the former's domain;
the latter remains evaluated at the exact ideal-source centre. Therefore a
future arithmetic enclosure at the rounded point may use the triangle path:
stored matrix/rounded source -> stored matrix/ideal source -> ideal matrix/
ideal source. Add each existing allowance ONCE. The rounding is already
covered by the source ball; do not separately add it a second time or silently
replace the source allowance by the smaller observed rounding residual.

This path is for the ideal finite Mars field at the fixed nominal spacecraft
position. Native force-evaluator arithmetic, other bodies/forces, carried
spacecraft error and variation over time remain separate. The carried radii
`[0.00014951281615784107 m, 9.62662340905759e-7 m/s]` are retained as metadata,
not claimed to be included in the nominal force-input allowances.

Focused audit: 1 passed in 0.66 s. Evidence:
`tests/data/m3_fourth_mars_binary64_input_binding.json`. No force evaluations,
native queries or native arcs are added. The new code is test-only and uses
existing records and standard-library arithmetic, following Ponytail reuse.

Replay: 1 passed in 0.69 s. Full suite: 3486 passed in 531.27 s (native
inventory 143.15 s, portable 46.31 s, historical degree-100/120 profile
74.94 s). The audit report matches focused/replay/full-suite/retained data
exactly. Against the parent run, all 19 selected native, 6 portable, 5
fourth-point audit, 1 subdivision, prior interval-jet and prior bounded-force
reports match excluding timers. All previous degree-20/40/100/120 report
science and call counts also match. Native/portable arcs remain 13/0 and
harmonic reuse remains 14 requests, 4 misses and 10 hits. The suite combines
independent budgets; it is not one mission runtime. Ruff, strict OpenSpec and
whitespace checks pass. The legacy model remains unimported under `src` with
unchanged SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Next step

Use these explicitly bound fourth-point inputs for one bounded Mars degree-120
calculation under the existing deadline, with a separately counted coarse
degree-100-plus-tail consistency check if needed. Include the existing input
allowances without pretending that consistency is an exact full-vector oracle.
Do not create a new full-force reference or reset the carried error. Production
precision, acceptance allocations and native-call limits remain unchanged.
