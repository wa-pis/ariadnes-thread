# 0017 — Capture fresh full-light inputs and the cached Sun state

Date: 2026-09-14. Parent revision: `0d59d71`. M3 task3.9 remains open.

## Bounded implementation

Implement decision0016's input prerequisite inside the existing fresh
derivative probe in `tests/test_trajectory_spk.py`. Retain all six Sun state
components from the same cached body-state accessor whose position was
already checked. Do not issue a second SPICE query or derivative evaluation.
Require finite values and exact position equality with the qualified fresh
source readback. Verify binary64 JSON round-trip for the complete Sun state.

Read Sun/Moon/Earth/Mars radii from the configured shape models, not collision
guards or harmonic normalization radii. Reapply the existing exact disc
disjointness predicate for all three configured occultors at the fresh epoch.
Use the existing Sun and occultor position-error balls and the fixed nominal
observer (zero observer error here). All three predicates must be true;
otherwise stop the check as unresolved, without assuming full light.

The enclosing source balls cover the exact position-polynomial anchors
under their existing conditional arithmetic/coverage premises. Therefore the
clear-disc proof applies to those anchors as well as the retained readbacks.
This supports the common ideal-source convention of the gravity assembly.
No whole-interval or incoming-spacecraft-ball illumination proof follows.

Require the retained SRP resource to match configured luminosity, spacecraft
area, reflectivity, mass and occultor list. Preserve the handoff and native
counters. Record the physical model identifier, nominal state/mass, full
cached Sun state, shape radii, four source positions/allowances, clear-disc
results, SRP resource and PCK hash. The existing shared timer remains active.

## Limits and next step

The snapshot contains inputs and a full-light applicability proof, not a new
SRP force vector. Next scale the existing ideal-source solar-gravity intervals
by the signed positive SRP factor with rational pi bounds; qualify signs,
zero components, parameter scaling and interval rounding before assembly.

The Sun velocity is explicitly only a cached native readback. Its selected
SPK representation, guarded coverage and conditional velocity-error bridge
remain unqualified at the fresh epoch. Do not silently equate it to the
position-polynomial slope. Retaining it avoids a later redundant query.

PCK/matrix error, native arithmetic, Schwarzschild vector composition, incoming
state balls and time/domain closure remain open. No additional propagation,
high-degree evaluation, coast extension or full-force certificate.

## Verification and retained snapshot

All 80 focused SRP/disc checks passed in 0.51 s. Full pytest: 2946 passed
in 476.99 s; native inventory 152.57 s, portable 54.26 s. Existing thirteen/
zero arcs and forty source readbacks remain. Ruff, strict OpenSpec, whitespace
and unchanged legacy checksum/import isolation pass.

[Retained snapshot](../../tests/data/m3_fresh_light_inputs.json) matches the
captured full-run record exactly. All three source-ball full-light predicates
are true. Calculation/record preparation takes 0.000185416080057621 s in this
run, nested inside the existing harmonic-probe timer; do not add it again.
The optical radii retain their exact binary64 values, including Moon
1737400.0000000002 m rather than a rounded orbital-radius constant.
Sun velocity is still readback-only, as explicitly labelled in the snapshot.
No production code, model, resource, dependency, tolerance or limit changed.
