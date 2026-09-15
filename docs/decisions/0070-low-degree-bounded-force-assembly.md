# 0070 — Enclose normalized finite-field acceleration at stored geometry

Date: 2026-09-15. Parent revision: `d031259`. M3 task 3.9 stays open.
Status: low-degree manufactured-field arithmetic, not a mission anchor.

## Decision

Add an optional significand precision to the existing TEST-ONLY harmonic-term
interval evaluator. Its default exact-Fraction path and physical formulas are
unchanged. Reuse the interval polynomial recurrence from Decision0069 rather
than implementing a second gravity recurrence.

Keep subtraction of stored positions, multiplication by the stored matrix,
power-of-two coordinate scaling, squared radius q and initial radial factors
EXACT. This small fixed geometry calculation does not grow with degree.
Round coordinate enclosures and the initial radial factors outward before
the recurrence. Repeated radial-factor powers, coefficients, derivatives and
transpose projection then use bounded-significand interval arithmetic.

No general interval division or new square-root implementation is needed.
Reuse the existing positive rational root bounds with 100 relative guard bits.
For positive normalization squared N and q, form the outward interval
`[sqrt_lower(N)/sqrt_upper(q), sqrt_upper(N)/sqrt_lower(q)]`, then multiply
the signed projected polynomial interval by it using four corners. The root
guard precision remains 100 independently of the chosen recurrence precision.
Increasing the latter alone cannot eliminate root-enclosure width.

The returned components are J2000 acceleration enclosures in m/s^2 for exact
stored inputs. The nonorthogonal test matrix means the specified stored-matrix
operation, NOT an ideal rigid rotation. Source/epoch uncertainty, ideal-to-native
PCK mismatch, native force arithmetic and omitted physical force channels
are not silently included in these intervals.

## Controls and observations

Thirty-six finite-field cases cover degrees 0/2/8, identity/proper signed
permutation/stored shear-scale matrices, and 24/53/80/120 significant bits.
Use explicitly manufactured cosine/sine coefficients, a fixed GM/reference
radius and stored positions. These are NOT the pinned lunar/Martian fields.
The retained JSON records every input and coefficient rule.

For each case, verify every interval contains the WHOLE prior exact-rational
oracle interval, not just an overlapping interval or sampled midpoint. There
are 1,872 term-component comparisons and 36 summed vectors. Sum both endpoints
exactly, then include the complete binary64 midpoint conversion error in the
reported L1 radius: sum over axes of max(abs(mid-lo),abs(mid-hi)). This is an
arithmetic enclosure for the manufactured finite field, not astronomical
uncertainty or a trajectory defect allowance.

Additional controls: nine squared-ratio certificates for positive root factors;
six independent monopole vectors; the existing eight degree-three signed-axis
oracles also run with bounded arithmetic; seven precision/singularity/nonfinite/
deadline rejection cases. The focused run passed 54 tests in 1.45 s.

At degree 8, the focused exact evaluations took about 0.00322–0.00340 s;
bounded evaluations took about 0.04998–0.06193 s. Again, this is SLOWER at small
degree; single-run observations do not establish scaling or a speedup.
For the identity case, the midpoint L1 arithmetic radii were approximately
3.6026e-7, 1.0448e-15, 1.46464e-16 and 1.46464e-16 m/s^2 at the four precisions.
The last two are dominated by binary64 midpoint rounding, not identical
underlying interval widths. These numbers choose no physical precision,
truncation or error allocation for the real mission.

Evidence: `tests/data/m3_low_degree_bounded_force.json`. Per-evaluation timers
cover term generation and geometry, but comparison/summation/report work is
outside those timers and inside the common 300 s test budget. No ephemeris
queries or native arcs are added. No production, UI or dependency changes.

Replay: 54 focused tests passed in 1.54 s. Full suite: 3473 passed in
465.21 s (native inventory 143.33 s, portable 46.48 s). All 36 new cases match
focused/replay/full-suite/retained data after excluding elapsed timers only.
Against the parent full run, 19 selected native, 6 portable, 5 fourth-endpoint
audit, 1 subdivision and the prior 16-case interval-jet report are unchanged
after excluding timers only. Native/portable arc counts remain 13/0; harmonic
reuse remains 14 requests, 4 misses and 10 hits. Suite duration covers separate
tests, not one mission's shared 300 s budget. Repository-wide Ruff, strict
OpenSpec validation and whitespace checks pass. The legacy model is unimported
under `src` and retains SHA-256
`4f0bb03da0eef3a7b91f63bb2b1e5906554379b2f767797fa2f32a5289b7fedf`.

## Next step

Measure a bounded MODERATE-degree evaluation against the existing exact
oracle at retained pinned-field geometry. Check width and cost before trying
higher degrees; do not rerun the known over-budget exact full-degree vector.
A truncated moderate-degree comparison is not a full-field anchor: any later
physical ledger must still include omitted degrees and all source/PCK/native
input allowances, carry-in errors, force variation and shared runtime costs.
Task 3.9 remains open; no threshold, reference or native partition is selected.
