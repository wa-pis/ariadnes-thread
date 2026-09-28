# 0015 — Assemble the common-source gravity reference

Date: 2026-09-14. Parent revision: `9b96331`. M3 task3.9 remains open.

## Implementation and proof

Implement decision0014 in `tests/test_trajectory_gravity_assembly.py`, using
only retained data. The target remains exact source-position polynomials at
the fixed nominal spacecraft state with stored harmonic matrices held fixed.
This is a test-local gravity reference, not a production API or full-force
certificate. No resource loading, native query, propagation or harmonic
evaluation is requested by this new assembly.

Verify the four input hashes, common epoch/SSB/J2000 labels, units, selected
source/matrix conventions, body sets, full harmonic degrees and resource/
replay identities before composition. Decode every finite binary64 endpoint
as an exact Fraction. Sum six point boxes, the tail-inclusive Moon box and
the singleton Mars midpoint componentwise, without intermediate float sums.

Reuse the qualified midpoint helper with zero extra tail for the aggregate
box. Preserve its final-rounding L2 allowance and exactly three additional
channels: Mars midpoint, Moon source bridge and Mars source bridge. The
channel-name contract rejects an extra tail. Their exact rational sum is an
L2 bound by the triangle inequality; report its binary64 value rounded upward.
Keep each channel visible. Individually outward-rounded display channels may
sum to slightly more than the separately outward-rounded exact total.

No six-point-source bridge is needed for this chosen ideal-source target.
Those previously verified allowances remain applicable to the separate
stored-source convention. Moon/Mars C00 and already included tails are not
added again. See decision0014 for the target-choice argument.

## Independent controls and rejection checks

Three shifted-box controls exercise independent corners and rational unit
directions for the scalar error balls. An exact cancellation test sums
2^60, 1 and -2^60 and must retain one with zero error: naive sequential
binary64 summation would lose it. Existing midpoint controls verify rounding
and nonrepresentable centres separately.

Six composition cases reject missing bodies, an extra tail, negative or
inexact allowances, wrong shape and reversed intervals. Eleven retained-data
cases reject a bad hash, epoch, orientation, origin, missing point body,
midpoint shape, coefficient identity, replay identity, nonfinite/negative
allowance and reversed Moon interval. Mutated semantic cases refresh their
test-only hash so they reach the intended semantic check. An expired budget
is rejected before composition. The retained-data case checks outward total
rounding and zero native counters.

The loader is an internal reader for the pinned diagnostic artifacts, not a
general untrusted mission format or a new integrity/authentication service.
No production code or dependencies are introduced.

## Limits and next step

The result excludes PCK/matrix uncertainty, native force arithmetic, SRP,
relativity, incoming spacecraft-state balls and variation over time. It is
not compared with the observed native total as an independent oracle.
Do not convert this instantaneous gravity-only radius into a trajectory
certificate or assume omitted terms are zero.

Next inspect and bind independent fresh SRP and Schwarzschild vector/error
contributions, including illumination and Sun velocity conventions. Keep
PCK/native arithmetic and state/interval-domain obligations explicit before
assembling a full-force reference. No targeting or coast extension follows.

## Verification and result

All 58 focused assembly/midpoint checks passed in 0.53 s. Full pytest: 2946
passed in 483.22 s; native inventory 156.21 s, portable 56.27 s. Existing
thirteen/zero arcs remain. Ruff, strict OpenSpec, whitespace and unchanged
legacy checksum/import isolation pass. No production/dependency/limit changes.

[Retained result](../../tests/data/m3_gravity_only_assembly.json) matches the
full-run output exactly. Gravity midpoint: (-3.1477508833955574,
0.0029787902709335133, -0.005506762351085002) m/s^2. The outward L2 allowance
is 7.8380163348378e-6 m/s^2. Four reported channels distinguish box/midpoint
rounding, Mars midpoint enclosure and the two harmonic source bridges.
This is a conditional instantaneous gravity enclosure under the stated
source/matrix convention, not a measured error of the native trajectory.
