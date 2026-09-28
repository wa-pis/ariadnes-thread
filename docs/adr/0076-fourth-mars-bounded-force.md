# 0076 — Fourth-point Mars field with explicit input allowances

Date: 2026-09-16. Parent revision: `1eefacc`. M3 task 3.9 stays open.
Status: Mars-only diagnostic at the actual fourth nominal endpoint.

## Decision and method

Extend Decision0075's input audit rather than create a separate evaluator.
Keep the audited epoch/state/source/rotation bindings. Load the pinned Mars
coefficient resource once, checking both complete binary64 array hashes,
shape, GM and normalization radius against existing evidence and settings.
The rounded ideal-polynomial source point is NOT a native readback.

Under one unchanged 300 s budget, including setup and input checks, compute
one exact degree-100 prefix plus finite tail and one bounded degree-120 field
at 120 significant bits. The full vector must be consistent with the coarse
box and its L2 midpoint ball. Record whether the full box is contained, but
do not use their intersection to sharpen its error bound. This is a coarse
consistency control, NOT an independent exact full-degree oracle. No exact
degree-120 rerun, new native query, native arc or trajectory continuation.

The finite tail is exactly zero within the degree-120 ceiling. Let E_a be the
interval midpoint L2 bound including output rounding. Add the existing
stored-matrix source-ball bound E_s and ideal-source matrix bound E_r once:
`E_Mars = E_a + E_s + E_r`. This uses the triangle path established in 0075.
Compute the sum exactly from its Fraction bounds before outward reporting;
individually displayed allowances may be a further outward float step. Do
not add source rounding separately, reduce the existing source allowance, or
fold spacecraft carried error into this nominal-point result silently.

The earlier input-audit report remains unchanged and reports zero force
evaluations for that completed phase. The new force report separately counts
both subsequent evaluations and the one shared deadline, without resetting it.

## Focused result

Test: 1 passed in 34.30 s. Shared work: 33.70167 s, including setup, the
19.95453 s coarse evaluation and the 13.10200 s full evaluation. Single local
observations, not benchmark medians or a mission-runtime certificate.
Evidence: `tests/data/m3_fourth_mars_bounded_force.json`.

At TDB 978995455.3554223, SSB/J2000, the rounded acceleration is
`[-3.149870681072988, 0.0032025762414817425, -0.005310130131716032] m/s^2`.

| Error channel | Outward reported L2 bound (m/s^2) |
| --- | ---: |
| Arithmetic including midpoint rounding | 9.119276823149571e-17 |
| Source position allowance | 1.0237538996626492e-8 |
| PCK matrix allowance | 1.5697109459316848e-10 |
| Combined ideal finite Mars field | 1.0394510182412429e-8 |

The full stored-input box lies inside the coarse degree-100-plus-tail box,
whose L2 radius is 7.827781095508099e-6 m/s^2. Its printed component intervals
refer to stored inputs ONLY, not the source/PCK-expanded result. Display
rounding can widen those component intervals beyond the internal Fraction
box used to calculate E_a. Input allowances now dominate this Mars-only
diagnostic; no complete native-force or physical-model accuracy claim follows.

The full carried state radii remain
`[0.00014951281615784107 m, 9.62662340905759e-7 m/s]`, as metadata only.
No new reference trajectory is selected, and no error is reset. Native force
arithmetic, other gravity sources, SRP, relativity, whole-interval variation,
and model uncertainty beyond degree 120 are outside this result.

Replay: 1 passed in 36.13 s. Full suite: 3486 passed in 567.99 s (native
inventory 142.84 s, portable 46.42 s, this diagnostic 34.39 s). The new force
report matches focused/replay/full-suite/retained evidence excluding timers
only; shared work takes 33.70/35.51/34.39 s respectively. Suite time combines
independent budgets, not one mission's deadline. Test count is unchanged
because an existing test was extended.

Against the parent run, the earlier input audit, all 19 selected native and
6 portable reports, 5 fourth-point audits, 1 subdivision, prior interval-jet
and prior bounded-force reports are unchanged. All historical degree-20/40/
100/120 profile science and call counts also match excluding timers. Native
and portable arcs remain 13/0; harmonic reuse remains 14 requests, 4 misses
and 10 hits. Ruff, strict OpenSpec and whitespace checks pass. The legacy
model remains unimported under `src` and retains SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Next step

Qualify the corresponding lunar harmonic contribution at the same bound
endpoint before assembling a gravity-only reference candidate. Use an
explicit finite-tail bound where sufficient rather than assuming a full
degree-200 vector is necessary. Preserve all input and carried-state terms,
and count any new work against the unchanged deadline. Do not promote this
Mars-only value to a full-force anchor or start targeting. M3 remains open;
production precision, scientific thresholds and native-call limits do not
change. Ponytail reuse keeps production code and dependencies untouched.
