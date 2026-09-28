# 0014 — Choose a common source convention before gravity assembly

Date: 2026-09-14. Reviewed revision: `d7f7afe`. M3 task3.9 remains open.
Status: accepted assembly ledger, not a computed gravity or full-force bound.

## Target and provenance

Choose an explicit mathematical target: eight gravity contributions at the
exact source-position polynomials and fixed nominal spacecraft position,
with the stored Moon/Mars matrices held fixed. Epoch 978995455.2929223 TDB
seconds since J2000, SSB/J2000, SI. This does not assert exact physical
ephemerides, ideal PCK orientation or equality with native force arithmetic.

The alternative all-stored-source target is also meaningful, but would need
point-source bridges instead of harmonic-source bridges. Do not mix these
two target conventions within one uncertainty sum.

[Assembly inputs](../../tests/data/m3_gravity_assembly_inputs.json) pin the
existing point-vector, Mars midpoint, harmonic-source-error and replay files
by SHA256. The retained Moon box is copied exactly from the latest 2923-test
run's `fresh_harmonic_vector_enclosure` output and checked against its stored
position/matrix replay. No new force evaluation or native query is performed.

## Error ledger for the chosen target

| Contribution | Retained representation | Additional allowance here |
| --- | --- | --- |
| Sun, Mercury, Venus, Earth, Jupiter, Saturn | Six outward component boxes at exact source polynomials, decision0007 | None for changing source convention: they already use the target coordinates. Keep their interval/serialization widths. |
| Moon, full degree200 | Stored-source outward degree20-plus-tail component box | Add the decision0013 Moon source-position L2 allowance once. The tail is already in this box. |
| Mars, full degree120 | Decision0004 binary64 midpoint plus separate L2 bound | Add the decision0013 Mars source-position L2 allowance once. The midpoint bound already includes its degree100 prefix rounding and higher-degree tail. |

Decision0011's six point-source allowances are NOT zero or discarded. They
remain a separate bridge to stored-source/native-input conventions; they are
not needed to enclose a point vector already evaluated at the target source.
Similarly, do not add another Moon/Mars monopole: their full harmonic fields
already contain C00. The inventory is six point fields plus two harmonic fields.

## Proposed conservative composition

Let B be the exact componentwise sum of the six retained point boxes, the
retained Moon box and the singleton Mars midpoint. Parse each binary64
endpoint as an exact Fraction; sum without intermediate binary64 rounding.
Let m be a rounded midpoint of B and R_box its qualified Euclidean midpoint
error, including that final rounding. Then a sufficient gravity-only bound is

    R_gravity = R_box + R_Mars_midpoint + E_Moon_source + E_Mars_source.

Each scalar is an L2 upper bound; the triangle inequality is sufficient.
The retained Mars bound 7.82777879292353e-6 m/s^2 already includes its tail
7.827778792894826e-6 m/s^2. Do not add the latter again. Do not recover a
prefix by subtracting rounded JSON tails from rounded boxes. The Moon box
likewise keeps its tail and serialization widths without another tail term.

An implementation may reuse the existing midpoint helper with zero tail
for B, then add the three explicit scalar allowances. Keep the target and
channel names in its diagnostic instead of calling this a full-force bound.
No numerical aggregate is computed or accepted in this audit.

## Verification required before implementation completion

WHEN assembling retained data, THEN reject wrong hashes, epoch/frame,
body sets, coefficient/replay identity, invalid intervals and negative or
nonfinite allowances. Verify exact input summation and outward final rounding.
Use independent corner/direction controls for box-plus-L2 composition and
an exactly solvable cancellation case to detect rounding lost in summation.
Keep Mars/Moon tails and source allowances in explicit once-only channels.
Run focused and full tests, Ruff and strict OpenSpec for that implementation;
no new native query or degree100/120 evaluation is required solely for assembly.

SRP, relativity, PCK/matrix errors, native force arithmetic, incoming state
balls and interval variation remain outside this ledger. Their absence is
not zero. The fresh observed total acceleration is not an independent oracle
for this gravity-only target. No coast extension, targeting or safety claim.

## Audit verification

Checked artifact epoch/frame agreement, Moon box and replay identity against
captured output, exact input hashes, local links and strict OpenSpec. Only
documentation and a retained-input JSON are added; no executable code changes.
Full pytest was not rerun: latest implementation remains 2923 passed in
496.44 s, native inventory 157.80 s with thirteen arcs. Task3.9 stays open.
