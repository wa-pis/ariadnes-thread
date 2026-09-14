# 0042 — Link nominal force inputs to the retained endpoint

Date: 2026-09-14. Parent revision: `b74b875`. Task 3.9 remains open.

## Reuse, not recomputation

The existing live probe already has the harmonic replay, lighting inputs,
pinned force reference, selected PCK inputs, body gravitational parameters,
collision guards and relativity resource. Retain `fresh_force_context`
from those values, and link it by digest from the same native endpoint
report that already references the selected SPK context. This adds no
force evaluation, rotation query, SPICE state request or propagation arc.
The existing budget and native-counter checks still enclose the block.

The context includes all eight actual GM values, the configured Sun-only
Schwarzschild flags and PPN values, the formula's speed-of-light constant,
collision guard radii, dry mass and disabled thrust. The referenced
harmonic report contains actual coefficient/resource hashes, normalization
radii, matrices and environment identity. The lighting report retains
area, reflectivity, luminosity, current-mass convention, occultors and
optical geometry. The force reference retains its fixed-state assembly.

Object digests use the pinned Python sorted JSON representation, as in
Decision0041. They are not raw-file hashes: for example, the existing
force-reference file hash remains unchanged while its normalized object
digest is `44eb71a5eadf0fc2270e9d5a6eb8bf74e7ae2b526f8c520bd54fec2e5b4595e0`.
The selected PCK-input digest is not an inventory of every kernel-pool key.

## Shared checks

Live and offline checks require the same start/end, model/frame/time and
initial seven-state. Harmonic, lighting and force-reference snapshots must
refer to that initial epoch, state and mass, and match their linked object
digests. The PCK file agrees across harmonic, light and clearance evidence;
the selected PCK inputs retain their existing pinned digest. Moon/Mars GM
values agree with the harmonic resource, all eight GMs are positive/finite,
and collision guards/dry mass agree with the clearance report. The nominal
coast keeps thrust off and the existing Sun-only PPN=1 convention.

Twelve new offline cases cover replay, three independently changed links,
five incompatible context fields and three incompatible relativity settings.
The latter eight recompute the outer digest to exercise semantic checks,
not just digest mismatch. All 35 focused tests pass in 0.08 s; the existing
standalone native inventory passes in 123.82 s. No new scientific result
is inferred from the extra provenance checks.

Final verification: all 3183 tests pass in 469.03 s (native inventory
146.56 s, portable 50.71 s), retaining thirteen/zero arcs. Focused/full
force and SPK contexts, endpoint binding and old fresh error/clearance
reports reproduce their artifacts excluding explicit timing fields.
The old endpoint values match after removing only the new force-context
digest; all previous coast-domain science and harmonic/light inputs are
unchanged. Ruff, strict OpenSpec, whitespace and legacy checksum/import
isolation checks pass. No deadline, tolerance or native-count revision.

## Boundaries and next priority

This is a nominal-coast input association, not external authenticity,
native-stage safety, finite-burn qualification or a guarantee that the
inputs remain valid on a longer interval. Coordinated edits are not
prevented by self-contained hashes. Existing force, source-arithmetic,
PCK and domain arguments still supply the scientific premises; their
scope is not enlarged by linking them.

Selected source records and these force inputs are now linked to the
retained endpoint. Next inspect the physical two-interval state/error
handoff and the remaining numerical/runtime scalability gap. Do not keep
adding generic provenance layers without a concrete mismatch. Preserve
the old tighter endpoint control, all incoming uncertainty, native limits
and the 300-second operation budget. No coast extension or targeting is
enabled; task 3.9 remains open.
