# 0054 — Use anchor geometry before choosing a harmonic prefix

Date: 2026-09-14. Parent revision: `86d59c2`. M3 task 3.9 stays open.
Status: bounded prerequisite audit, not a new harmonic vector qualification.

## Question and decision

Decision0053 binds six nominal point forces to the fourth spacecraft endpoint.
Before evaluating the remaining expensive Mars harmonic vector, check whether
the chosen prefix-plus-tail method can fit Decision0051's optimistic anchor
intercept. Do not transplant the old degree100 error, or start a degree120
exact-vector calculation merely because a coarse bound is too large.

Reuse the existing rotation-invariant finite-field norm with degrees through
the prefix zeroed. Load the pinned Moon200/Mars120 coefficients and verify
their hashes, GM and normalization radii. Compare two independently labelled
distance floors: the already qualified quarter-domain floor, and the downward
rounded exact-polynomial distance at the fourth nominal endpoint. The latter
is formed with exact fractions from Decision0052's source coordinates and
Decision0040's actual terminal state. It covers the anchor only, not its error
ball or future trajectory. Both use ideal orthogonal frames: the stored native
rotation matrix, source/native arithmetic and their bridging errors are absent.

Keep the existing h=1/8 s, carried errors, quarter-domain sensitivities and
norm-only light charge. Grant zero J, zero native residual and zero other anchor
errors ONLY for scalar accounting. For each tail B, evaluate the existing
error formula with D=D_light+B. Its monotonicity means that this chosen B cannot
be used unchanged in that formula when even the optimistic result exceeds the
gate. This is not a lower bound on actual force error or proof that a better
bound cannot work. The common separate anchor intercept is approximately
2.0853152271970628e-7 m/s^2; it is not an accepted allocation.

## Results

The Mars whole-domain floor is 3631133.108218859 m; the nominal-anchor floor
is 3689499.9800443966 m. Every tested degree100..119 tail from the broad
domain exceeds the intercept; degree120 has zero omitted finite-model tail
by definition, without evaluating a vector. At the nominal anchor:

| Prefix degree | Omitted-tail upper bound, m/s^2 | Optimistic velocity formula, m/s |
|---|---|---|
| 100 | 1.6220347347338589e-6 | 1.1766879041826974e-6 |
| 114 | 2.3210870109810707e-7 | 1.002947147342018e-6 |
| 115 | 1.897839574565694e-7 | 9.976565543065503e-7 |
| 119 | 3.783475966812e-8 | 9.786629042947988e-7 |

Degree115 is the first tested prefix passing this optimistic scalar screen.
It leaves only about 2.34e-9 m/s for all remaining effects under this formula.
It is NOT selected as a sufficient reference or authorized error allocation.
The ideal rotation norm used here also differs from the older stored-matrix
tail wrapper, which multiplies by the sum of absolute matrix entries. Its
results must not be substituted into that wrapper without a checked bridge.

The Moon's omitted degree3..200 norm at the nominal anchor is only
2.2689821393132474e-29 m/s^2 for the selected remote-Moon geometry. That says
nothing about the low-degree vector/native arithmetic or near-Moon cases.
This calculation does not remove any terms from the production force model.

## Reproduction and verification

Run the [read-only audit](experiments/0054-harmonic-tail-budget.py) from the
repository root with the pinned `space-nav` Python. It emits JSON and checks
the hashes/frame/epoch/model links, exact intercept comparisons, monotone tails,
the first fitting cutoffs (120 domain / 115 anchor), and zero native counters.
The [retained report](experiments/0054-harmonic-tail-budget.json) contains all
44 cases and input file hashes. Approximate scalar outputs are explicitly
labelled; tail values originate from the existing outward-rounded norm helper.
No PCK query, harmonic-vector evaluation or spacecraft propagation is added.

The initial interactive audit passed a Fraction duration where the existing
error helper requires a float. Its assertion stopped the audit before loading
fields. The corrected call passes exactly representable 0.125; no API or
validation was weakened. The retained script completes in about 1.38 s,
including its input/resource work, not a measurement of future vector cost.
Two runs of the retained audit reproduce all scientific fields exactly,
excluding elapsed time. Full suite: 3217 passed in 484.71 s, native/portable
inventory 154.36 / 50.16 s. Prior source, point-force, domain, sensitivity,
force-context, endpoint, reference/error, clearance, lineage and reuse reports
match the parent run, excluding timing fields only. Counts remain 13 native /
zero portable arcs, with native harmonic requests/misses/hits 14 / 4 / 10.
Ruff (including the audit script), strict OpenSpec, whitespace and unchanged
legacy checksum/isolation pass. Logs: `/private/tmp/ariadna-harmonic-budget-FiNdjw`.
The suite duration is not the runtime of a single 300-second mission run.

## Next bounded step

Check the new-epoch rotation-matrix bridge and an attainable remaining
anchor/rate budget before choosing or timing a higher-degree vector prefix.
Investigate a tighter matrix norm or coefficient-wise tail evaluation only
with independent controls and measured cost. Do not infer that degree115 is
enough, that degree120 is required, or that old native-arithmetic errors apply.
No fifth native arc, new tolerance, production acceptance change or targeting.
