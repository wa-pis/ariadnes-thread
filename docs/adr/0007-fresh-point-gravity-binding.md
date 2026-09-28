# 0007 — Bind six point forces to the fresh handoff

Date: 2026-09-13. Base revision: `f617b93`. M3 task3.9 remains open.
Status: accepted and verified bounded application (verified 2026-09-14 local).

## Decision and contract

Apply [the pure interval helper](0006-point-gravity-intervals.md) to Sun,
Mercury, Venus, Earth, Jupiter and Saturn at the existing nominal Mars handoff.
Reuse exact reanchored source polynomials and the GM values already accessed
by the monopole-jerk probe. No new native queries, rotations, force readbacks
or propagation arcs are needed. Moon/Mars gravity is not added a second time.

The binding requires the same source/reference epoch, valid coverage, exact
six-component rational states and matching six-body/GM sets. It checks the
shared budget before, between bodies and after assembly. Invalid data or an
expired budget raise without returning partial results. Source positions are
not converted to binary64; only reported interval endpoints are rounded outward.

The mathematical contract is acceleration GM*r/|r|^3 for exact source-minus-
spacecraft positions in SI/SSB/J2000. Source velocity entries do not participate
in the instantaneous acceleration. Epoch coverage is an input validity check,
not a whole-interval force-error certificate.

## Evidence

New moving-source controls use six analytical 3-4-5 radial geometries at two
absolute epochs and three offsets, including fractional coordinates. Other
controls reject epoch/coverage mismatch, malformed or rounded states, missing
or extra source/GM entries, invalid GM and expired budgets. Existing pure
interval and jerk-binding checks remain unchanged.

Reproduce focused checks:

```sh
conda run -n space-nav python -m pytest -q tests/test_trajectory_point_vector.py tests/test_trajectory_spk.py -k 'point_vector or point_binding or point_gravity_anchor or fresh_jerk_binding'
```

The native inventory applies the binding once to the preserved handoff at
978995455.2929223 TDB seconds since J2000, with source coverage ending at
978995455.3554223. It checks finite outward reporting and unchanged native
counters and handoff. The model and all scientific parameters remain unchanged.

## Limits and next step

[Retained intervals and timings](../../tests/data/m3_fresh_point_gravity_intervals.json):
74 focused tests pass in 0.66 s; all 2879 tests pass in 500.09 s. The 22 new
binding cases supplement the previously verified pure helper. Native inventory
takes 149.77 s and portable inventory 46.18 s under unchanged limits. All
thirteen/zero native arc assertions and ten harmonic-reuse hits remain. New
six-vector calculation/report preparation takes 0.0007207081653177738 s in this
run, with no added native queries/arcs. Timing is an observation, not a guarantee.
Ruff, strict OpenSpec and unchanged legacy checks pass.

These six nominal ideal-polynomial vectors fill one ledger gap, not the entire
error budget. Source arithmetic, bridges to stored Moon/Mars geometry, incoming
state radii, radiation pressure, relativity and domain/variation proofs remain.
Do not subtract these vectors from a native total to infer independent remaining
components, reset handoff uncertainty or extend the trajectory.

Next establish an explicit source-geometry bridge at this same handoff before
combining point and harmonic forces: identify which existing chain-position
allowances cover the fresh epoch and bound the induced force difference on
verified nonsingular chords. Reuse existing data; reject missing coverage and
never substitute a previous epoch's radius floor without proof.
