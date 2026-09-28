# 0016 — Audit fresh SRP and Schwarzschild prerequisites

Date: 2026-09-14. Reviewed revision: `ed3c615`. M3 task3.9 remains open.
Status: prerequisite audit, not a new force calculation or certificate.

## Available evidence and missing bindings

Decision0015 assembles gravity at exact position polynomials, fixed nominal
spacecraft state and stored harmonic matrices. The old SRP and Schwarzschild
helpers in [test_trajectory_spk.py](../../tests/test_trajectory_spk.py) return
L1 errors around supplied observations, not independent signed reference
vectors. Their old anchor is not the fresh epoch 978995455.2929223 TDB s.
No subtraction from the observed native total supplies the missing forces.

The existing fresh readbacks retain positions for all eight bodies. The
fresh harmonic replay retains spacecraft position, velocity and mass, but
does not retain a complete SRP input contract (area, Cr, occultor/source shape
radii) or the fresh cached Sun velocity with its representation/error binding.
Do not infer optical radii from collision spheres or harmonic normalization
radii: use the actual configured shape-model radii used by the SRP model.

## SRP: reuse the existing solar vector after proving full light

With r = spacecraft minus Sun, the configured fully lit cannonball model is

    a_SRP = L*area*Cr/(4*pi*c*mass) * r/|r|^3,
    a_Sun_gravity = -GM_Sun * r/|r|^3.

Thus a_SRP = -k*a_Sun_gravity with positive
k = L*area*Cr/(4*pi*c*mass*GM_Sun). Reuse the existing ideal-source Sun
component intervals; a second radius calculation is unnecessary. Enclose k
using the existing rational pi bounds, exact binary64 parameter values and
c=299792458 m/s. Signed interval multiplication must keep all endpoint
combinations, including negative and zero components. This preserves the
chosen ideal-source convention without another source-position bridge.

This identity is conditional on full illumination. At the fresh epoch,
reapply `_apparent_spheres_strictly_disjoint` for Moon, Earth and Mars using
the existing cached positions, configured shape radii and source/occultor
position-error balls. Observer radius is zero only for the explicitly fixed
nominal state. Positive results for all three cover the ideal positions in
those balls; an unresolved disc relation must not be treated as full light.
Old full-light flags, old interval domains or a sampled shadow value are not
substitutes for this new applicability check.

Record L from `SUN_LUMINOSITY_W`, the actual spacecraft SRP area and
reflectivity coefficient, preserved coast mass and all four shape radii.
Require same epoch/SSB/J2000 and unchanged configuration/counters. Reuse
already cached inputs; do not issue fresh queries because earlier code kept
only part of an available state. A separate SRP source bridge may later be
needed for a stored/native comparison, not for the ideal-source vector itself.

## Schwarzschild: bind the velocity convention explicitly

The existing PPN=1 helper uses both relative position and relative velocity.
Its exact rational potential contribution and square-root-enclosed velocity
contribution can be exposed as signed component intervals while retaining the
current observation-error API and its exact L1 reduction.

Before fresh application, retain the complete cached six-component Sun state
at the already executed derivative probe. Position binding is already tested;
the discarded last three components must be retained without a new query.
Audit the actual selected Sun chain's SPK representation and guarded cores.
Type2 differentiates position coefficients, whereas Type3 uses independent
stored velocity coefficients. The generic fresh polynomial slope is therefore
not automatically the velocity required by the SPICE force-state contract.
This audit does not assert that the Sun chain is Type3 or that its two
representations differ: selection/readback evidence must establish that fact.

`chain_velocity_bounds_m_s` includes per-record velocity arithmetic, centre
addition and km/s-to-m/s conversion. Do not copy its old numerical argument
to the fresh epoch without checking selected-record coverage and same consumer
identity. Reuse the established representation when those premises hold;
otherwise preserve the failed binding instead of fitting an error allowance.
Keep PPN beta/gamma resets, GM, c and the nominal spacecraft state explicit.

## Selected next bounded step

Retain the missing fresh SRP parameters/radii and complete cached Sun state
during the existing probe; verify the three source-ball full-light predicates,
exact epoch/state/configuration bindings and unchanged native counters.
Preserve the snapshot so later vector composition needs no repeated query.
An unresolved predicate remains a scientific failure to investigate.

Then qualify SRP signed interval scaling and the Schwarzschild signed-vector
contract with analytic controls before composing either with gravity.
No full-force sum, PCK error, spacecraft-state domain, force variation or
trajectory certificate is produced by this prerequisite audit. Task3.9 stays
open; no extra high-degree evaluation, coast extension or targeting.

## Audit verification

Traced both anchor helpers, SRP configuration/illumination calls and the
velocity-chain arithmetic construction; verified local links and strict
OpenSpec. No executable code, scientific input or resource changed, and no
new native work was requested. Full pytest was not rerun for this documentary
step; latest implementation remains 2946 passed in 483.22 s.
