# 0013 — Apply the stored-matrix source bound to Moon and Mars

Date: 2026-09-14. Parent revision: `09fbc56`. M3 task3.9 remains open.

## Binding

Apply decision0012's qualified q^2*J*epsilon helper during the existing fresh
Moon/Mars harmonic control in `tests/test_trajectory_spk.py`. Use the same
already obtained source positions, rotation matrices and gravitational fields
as the retained harmonic replay. No additional source/rotation query, native
derivative, propagation or high-degree vector evaluation is introduced.

The surrounding decision0009 binding verifies the epoch, SSB/J2000, exact
source readback equality and conditional chain allowance. The existing replay
checks coefficient/array hashes and exact stored positions/matrices. Additional
assertions require the full 200x200 Moon and 120x120 Mars arrays and unchanged
GM/normalization radius from the pinned resources. The nominal spacecraft
position must equal the existing handoff exactly. Relative coordinates are
formed as exact Fractions; no rounded ideal source is substituted.

The source bound includes every loaded coefficient, including C00. It is
separate from the degree20 vector prefix/tail diagnostic. Neither field is
truncated for this calculation, and no six-point-body monopole is added here.
The helper proves a positive transformed source-comparison chord floor before
using the full-field spatial bound. Matrix orientation is held fixed, without
assuming that the stored matrix is exactly orthogonal.

Keep the exact error as a Fraction and round only the reported L2 allowance
upward. Verify native counters and the complete selected handoff are unchanged.
Record the calculation time within the original shared 300-second budget.
Two `fresh_harmonic_source_error` output records retain body, epoch, degree,
resource hash, source allowance and acceleration allowance in SI.

## Scope and next step

This completes only the fixed-epoch conditional source-position effect for
the two stored harmonic force functions. It does NOT supply native force
arithmetic, physical source uncertainty, matrix/PCK error, spacecraft-state
balls or interval variation. It is not a native vector-error observation.
Previous degree100/tail and midpoint enclosures remain unchanged and must
not be silently combined across different source or matrix conventions.

Next audit a single same-epoch gravity ledger: six ideal-polynomial point
vectors, two stored harmonic enclosures and their source-position allowances.
Choose an explicit common source convention and count each allowance once.
Keep missing matrix/native arithmetic and full-force terms visible; do not
extend the coast or claim an interval/mission certificate. Task3.9 stays open.

## Verification and retained result

All 109 focused source/distance checks passed in 0.52 s. Full pytest: 2923
passed in 496.44 s; native inventory 157.80 s, portable 56.48 s. Existing
thirteen/zero arcs and forty readbacks remain. Ruff, strict OpenSpec,
whitespace and unchanged legacy checksum/import isolation pass.

[Retained diagnostic](../../tests/data/m3_fresh_harmonic_source_errors.json)
matches both captured full-run records exactly. The outward L2 acceleration
allowances are 2.4557651586452085e-24 m/s^2 for Moon and
1.0237541896858474e-8 m/s^2 for Mars. Their calculation/report preparation
takes 0.8963999168481678 s and 0.32460795785300434 s respectively in this run.
Those costs lie inside the existing harmonic-probe timer; do not add nested
timers again or attribute the entire inventory timing difference to this code.
No production model, dependency, resource, scientific tolerance or limit changed.
