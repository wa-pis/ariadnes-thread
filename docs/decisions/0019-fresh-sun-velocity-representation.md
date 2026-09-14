# 0019 — Audit fresh Sun velocity representation

Date: 2026-09-14. Parent revision: `559b827`. M3 task3.9 remains open.

## Observed selection

A read-only probe in the pinned `space-nav` environment loaded the standard
kernels and called `spksfs(10, 978995455.2929223, 256)`. The selected `Sun`
segment is type2, target10, center0, frame1 (SSB/J2000), in
`inpop19a_TDB_m100_p100_spice.bsp`, SHA256
`01f095b148ef1e5aad6f95213c188ca5b0d8a58901d19a95b0c11082b1d3a0c6`.
Segment coverage is [-3234816000, 3234816000] TDB s.

Reading its directory and record gives zero-based record index3048,
midpoint979430400 TDB s and radius691200 s. The existing 16-ULP guard is
1.9073486328125e-6 s. Both the original anchor978995455.2304223 and its
one-second interval fit inside that guarded record; the fresh anchor and
its following 1/16 s therefore fit too. A fresh `spkssb` state converted
from km/km/s to SI matched all six binary64 values in
`tests/data/m3_fresh_light_inputs.json` exactly.

This was a separate diagnostic state query, not a new inventory query or
propagation arc. The first probe failed because SpiceyPy does not expose
`dafhfn`; the successful probe resolved the file from `kdata` by handle.
No kernel, scenario, state snapshot or production code changed.

## Decision and next executable check

For this selected Sun record, the exact derivative of its position series
is the appropriate ideal velocity target. The existing inventory already
has type2 differentiated-series arithmetic bounds and a one-link Sun chain
velocity allowance. This does not generalize to type3: its separately
stored velocity coefficients must be evaluated instead.

Next retain the Sun velocity from the existing full `spkssb` readback at
the fresh epoch (currently only its position is kept), assert the selected
type2/center/frame and same guarded core, and require exact equality with
the cached Sun velocity. Compare its exact L1 difference from the fresh
polynomial derivative against the existing uniform chain velocity bound.
Retain the representation and allowance with the input identity so later
Schwarzschild composition cannot silently substitute another convention.
Do not add another ephemeris query to the inventory for this check.

## Verification scope

The standalone selection, coverage and six-component equality assertions
passed. This is an observed prerequisite, not yet a regression assertion
binding the fresh cached velocity to a qualified error allowance. No
Schwarzschild vector or complete force certificate is claimed. PCK/native
arithmetic, incoming state balls and interval closure remain open.

Documentation only: strict OpenSpec validation and whitespace checks pass;
the full suite was not rerun. Latest implementation evidence remains
2990 passed in474.67 s from decision0018.
