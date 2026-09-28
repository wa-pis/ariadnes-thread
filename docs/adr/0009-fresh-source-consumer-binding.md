# 0009 — Bind fresh source readbacks to cached force inputs

Date: 2026-09-14. Parent revision: `b26ec5a`. M3 task3.9 remains open.

## Decision and runnable evidence

Follow decision0008 with a narrow extension of the existing native inventory
in `tests/test_trajectory_spk.py`. Retain the eight native position vectors
already queried at the fresh handoff, as exact Fractions of their binary64
values. Do not repeat their SPICE requests.

After the existing fresh derivative evaluation, read the eight cached body
states. Require exact equality with the retained readbacks and an exact L1
distance from each ideal source polynomial no larger than its existing chain
allowance. Require matching body sets, SSB/J2000, the handoff epoch and the
covered endpoint. The existing inventory checks that the loaded kernel list
is unchanged across the operation. Existing guarded-core assertions remain
the coverage prerequisite; this patch does not invent a new coverage proof.

The Moon and Mars harmonic calculations separately assert that their copied
source positions equal the same retained vectors. Failed identities stop the
test; there is no fitted epsilon, fallback or substituted source position.
The new diagnostic `fresh_source_consumer_binding` retains positions,
allowances, epoch and coverage labels in the test output.

This is test-local plumbing and assertions, not a new public API or runtime
validation feature. The existing native/portable inventory is the runnable
check; no separate helper or duplicate native control is introduced.

## Limits and next step

These are conditional arithmetic allowances for the pinned source model,
not physical ephemeris uncertainty. Equality checks applicability to the
cached consumer; it does not prove every internal force arithmetic operation.
No additional SPICE query, derivative evaluation or propagation is requested.
The thirteen/zero native arc assertions and forty source readbacks remain.

Next qualify positive separation floors over the source-position comparison
chords before applying point or harmonic spatial sensitivities. Incoming
spacecraft error balls, PCK errors, SRP, relativity and interval/domain closure
remain separate obligations. No coast extension or full-force certificate.

## Verification

Both focused native/portable inventory cases passed in 169.37 s. Full pytest:
2879 passed in 457.53 s; native inventory 139.79 s, portable 41.44 s. The
existing thirteen/zero arc and forty readback assertions pass. Ruff, strict
OpenSpec, whitespace and unchanged legacy checksum/import isolation pass.
No production code, resources, scientific tolerances or limits changed.

[Retained diagnostic](../../tests/data/m3_fresh_source_consumer_binding.json)
matches the full-run captured JSON exactly. This is measured identity at one
qualified handoff, not a statistical or full-mission claim.
