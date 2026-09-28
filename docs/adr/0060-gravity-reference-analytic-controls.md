# 0060 — Check a gravity-only comparison anchor analytically

Date: 2026-09-15. Parent revision: `cb4fc85`. M3 task 3.9 remains open.
Status: analytic contract verified; no physical new-epoch reference qualified.

## Decision and implementation

Implement Decision0059's separate comparison convention in the test-only
`_gravity_reference_defect_m_s2_m_s3`. It reuses the existing full-force-anchor
helper's validation and gravitational rate assembly, then removes one S+R
charge algebraically. The result is D=E_g+S+R, with unchanged
J=E_j+h*K/2+T+W. E_g must refer to a gravity-only acceleration anchor.
The function's name and contract distinguish it from the old convention.
Do not pass an old full-force a0 and reinterpret its error as E_g.

The old helper, its callers and factor-two tests are unchanged. No public
option or production force switch is introduced. Full physical truth still
contains gravity, radiation pressure and Schwarzschild relativity. This
contract is for the fixed-mass thrust-off coast, not finite burns. Input
validation alone does not establish the caller's reference/source/domain
premises, as for the existing helper.

## Exact controls and whole-interval argument

32 manufactured cases combine zero/gravity-only/nongravity-only/mixed
channels, both signs, constant/reversing bounded nongravity, and zero/nonzero
incoming position/velocity errors. Use exact Fractions and h=1/8 s.
Let L=S+R, b=E_j+T+W and u=0 for constant forcing or 1 for reversal.
The gravity-only polynomial has q''=a0+j0*t. Full manufactured truth has
gravity a0+j0*t+sign*(E_g+b*t+K*t^2/2), plus
sign*L*(1-2*u*t/h). For signed residual z, the following identities hold:

    D+J*t-z = 2*u*L*t/h + K*t*(h-t)/2
    D+J*t+z = 2*E_g + 2*b*t + K*t*(h+t)/2 + 2*L*(1-u*t/h)

Every term is nonnegative for all 0<=t<=h. Both sides therefore enclose the
absolute residual even when reversal changes its sign. The executable checks
evaluate these exact identities at five rational epochs; the nonnegative
polynomial decomposition supplies the whole-interval argument, not sampling.
Constant forcing attains the bound at the endpoint and rejects omission of
either the nongravity norm or gravitational Taylor remainder when nonzero.

Independently integrate the full manufactured acceleration polynomial to
position and velocity, with signed nonzero initial errors. The existing
transport lemma encloses their differences from q and q' and returns the
unchanged incoming error pair at t=0. General full-force sensitivities and
geometric inclusion remain the live caller's obligations, not proven by
these state-independent manufactured forces.

Two additional sign cases keep g=0 and reverse l from sign*L to -sign*L.
An OLD full-force anchor q''=sign*L has endpoint residual 2L: the single
charge fails while the old helper's double charge attains it. A genuinely
new gravity-only anchor q''=0 has residual L. This prevents silently
relabelling the same old curve. Twenty-six rejection cases retain checks
for every negative/non-Fraction/boolean channel and invalid horizon.

## Verification

98 focused controls pass in 0.11 s: 60 new cases and 38 unchanged old
defect-channel cases. Full pinned suite: 3277 passed in 466.25 s;
native/portable inventory 144.75 / 46.87 s. The suite is not one
300-second mission calculation. Ruff, strict OpenSpec, whitespace and
unchanged legacy checksum/import isolation pass.

Read-only comparison with Decision0059's full JUnit run preserves all
existing anchor/bridge, domain/sensitivity, context, reference/error,
clearance, lineage and reuse data, excluding timing fields only. Native
counts remain 13 / zero portable arcs, with harmonic requests/misses/hits
14 / 4 / 10. No scientific fixture or native calculation was changed.
Reproduce with `tests/test_trajectory_gravity_reference.py` and the old
defect-channel controls in `tests/test_trajectory_error_transport.py`.
Local full-suite log: `/private/tmp/ariadna-gravity-reference-NhWFca/full-suite.xml`.

## Next bounded step

Assess the new-epoch gravitational jerk/rate channels and remaining coupled
budget before choosing an expensive harmonic prefix. A future gravity-only
curve must have its own acceleration coefficients and verified q'' bound,
position/velocity domain, source coverage and endpoint residual. Do not reuse
old full-force coefficients, old D/J or native arithmetic. These analytic
controls create no physical reference, native arc, new error allocation or
mission certificate. No targeting or production acceptance change.
