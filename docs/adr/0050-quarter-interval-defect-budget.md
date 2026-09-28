# 0050 — Account for the quarter-interval defect budget before another arc

Date: 2026-09-14. Parent revision: `d4e27ac`. M3 task 3.9 remains open.
Status: accepted prerequisite audit; no new reference/endpoint qualified.

## Question and evidence

The [carried-domain check](0049-carry-fourth-endpoint-into-quarter-domain.md)
establishes geometric inclusion, not reference accuracy. What would the
existing error-envelope formula require over the remaining h=0.125 s if we
retain the private 0.001 m / 1e-6 m/s endpoint regressions? As clarified in
Decision0045, those controls are not a new whole-mission absolute-error rule.

Read-only inputs: `m3_quarter_second_carried_domain.json` for the carried
errors and duration; `m3_quarter_second_initial_domain.json` for the NEW
domain's SRP and Schwarzschild norm bounds. Source audit:
`_coast_error_envelope` and `_fresh_reference_defect_m_s2_m_s3` in
`tests/test_trajectory_error_transport.py`, and their live consumers in
`tests/test_trajectory_spk.py`. Exact Fraction arithmetic uses the saved
binary64 inputs and exact decimal acceptance thresholds.

## Necessary accounting, not sufficient accuracy

For nonnegative qualified sensitivities and feedback below one, the returned
velocity enclosure is at least v0 + h*D + h^2*J/2. A native/reference endpoint
residual is another nonnegative charge. With v0=9.62662340905759e-7 m/s,
the remaining headroom is 3.7337659094240899e-8 m/s.

Thus, even granting zero sensitivity feedback and zero native residual,
necessary individual ceilings are approximately D <= 2.9870127275392719e-7
m/s^2 OR J <= 4.7792203640628351e-6 m/s^3 when the OTHER channel is zero.
They cannot both be spent independently: the coupled inequality is
h*D + h^2*J/2 <= headroom. This is a lower bound on this conservative
formula's OUTPUT, not a lower bound on the physical error.

For the existing norm-only light/relativity treatment, the newly qualified
domain already supplies D_light = 2*(SRP + Schwarzschild) = approximately
8.9879131758830856e-8 m/s^2. This consumes 1.1234891469853857e-8 m/s,
leaving 2.6102767624387042e-8 m/s before anchor error, J, feedback and native
residual. Accordingly the separate best-case ceilings after this charge are
anchor error <= 2.0882214099509634e-7 m/s^2 OR J <=
3.3411542559215414e-6 m/s^3, again not simultaneous allocations.

The position allowance after only p0+h*v0 is approximately
0.00085036685104954569 m. That remaining position margin does not pay a
velocity overrun. All printed decimals here are explanatory approximations,
not new outward-rounded constants or production acceptance parameters.

Exact checks reproduced these values and confirmed that spending either
post-light intercept alone exactly reaches the velocity gate, whereas
spending both exceeds it. The light charge is a choice of conservative
bounding method, not an unavoidable physical error or a proof that improved
light treatment is impossible. No previous D/J value is applied outside
its old interval, and no native residual is predicted from a prior arc.

## Missing premises and bounded next work

The quarter-domain proof uses rotation-invariant gravity norms and SRP
bounded by full illumination, valid even in shadow. It does NOT establish
the fully-lit premise required by the existing smooth SRP Jacobian, nor
new full-force sensitivities. Old short-domain lit/rotation/derivative
results cannot be silently transferred to the larger box.

Next use the existing live domain/source inputs to check all three
occultors' whole-domain illumination and recompute uniform position and
velocity sensitivities under the shared timer, with no new native arc.
Then evaluate the coupled budget, including feedback, without inventing
unqualified anchor or J values. If full illumination cannot be established,
the current lit-Jacobian path is unresolved; do not call its helper anyway.
After those premises, qualify a reference anchored at the FOURTH endpoint,
its source reanchor, both paths/chords, and all D/J channels on this interval
before considering another propagation. Current cubic/anchor evidence is
at the previous handoff epoch, not automatically at the new one.

## Verification and limits

Exact read-only scalar checks and source/artifact audit; Ruff, strict
OpenSpec, whitespace and legacy isolation pass. Documentation only: no
code or fixture changed, and no full-suite rerun. The unchanged parent
runtime has 3217 passing tests. No numerical cap, tolerance, force model,
allocation or production acceptance changed. Task 3.9, native-stage safety,
finite burns and mission-scale runtime remain open.
