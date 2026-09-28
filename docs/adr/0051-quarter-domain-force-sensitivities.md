# 0051 — Qualify quarter-domain illumination and force sensitivities

Date: 2026-09-14. Parent revision: `ee13e02`. M3 task 3.9 remains open.
Status: conditional force-domain premise, not a new endpoint certificate.

## Scope and calculation

Implement the next prerequisite from
[Decision0050](0050-quarter-interval-defect-budget.md) using the existing
quarter-second domain, live physical environment and covered one-second
source envelopes. There are no new ephemeris queries or native arcs.

First require strict apparent-sphere separation from Earth, Moon and Mars
over the ENTIRE observer/source envelopes. All three pass. An unresolved
illumination check fails before calling the fully-lit SRP Jacobian helper.
Only then compute the fixed-mass SRP position sensitivity at 2000 kg.

For each gravity source recompute its spatial operator bound on the new
distance floor. Point gravity uses 2*GM/r^3. Moon/Mars each combine that
monopole once with the existing finite-harmonic nonmonopole Frobenius bound,
at full degrees 200/120. Removing C00 from a copy for the bound does not
modify native coefficients. Orthogonal rotation preserves these norm bounds;
this is not a bound on time-dependent rotation defects.

Recompute Sun Schwarzschild position AND velocity sensitivities with the
new Sun-distance floor and relative-speed bound. Gravity and fully-lit,
fixed-mass SRP do not contribute spacecraft-velocity sensitivity. Sum the
eight gravity, SRP and Schwarzschild position contributions outward and
retain the separate velocity contribution. Model, domain, epochs, mass,
floors, illumination and per-force terms are reported together.

## Results and interpretation

Lx = 1.942174880062744e-6 s^-2 and Lv = 7.30562670187794e-15 s^-1.
For the remaining h=0.125 s, the outward feedback factor Lx*h^2/2+Lv*h
is 1.5173242163693528e-8 < 1. This meets a necessary lemma premise;
it does not supply a reference trajectory, D/J or native endpoint error.
The bounds hold uniformly at each covered epoch for states/chords inside
the declared domain; no future reference path is asserted to be inside it.

As EXACT SCALAR ACCOUNTING ONLY, combine these sensitivities with the saved
incoming radii and the new norm-only light/relativity D charge. Granting
zero anchor error, zero J and zero native residual gives the optimistic
formula output 9.7393355926452435e-7 m/s. Its remaining headroom is
2.6066440735475705e-8 m/s. Writing f=Lx*h^2/2+Lv*h, the anchor and J
coefficients in the velocity formula are h/(1-f) and
h*(Lx*h^3/6+Lv*h^2/2)/(1-f)+h^2/2 respectively.

The separate best-case intercepts are approximately 2.0853152271970628e-7
m/s^2 for anchor error OR 3.3365043803904957e-6 m/s^3 for J. Exact Fraction
checks reach the gate with either intercept alone and exceed it with both.
These are coupled budget diagnostics, not proven zero errors, accepted
allocations, outward constants, or a claim that a fifth arc can pass.

## Verification

155 focused illumination/Jacobian/operator controls passed in 0.72 s.
The portable inventory passed in 27.70 s; this new calculation took
0.19728150009177625 s, excluding earlier environment/source/domain work.
Full suite: 3217 passed in 462.17 s; native/portable inventory times
144.40 / 46.31 s. The added calculation took 0.2065451662056148 /
0.20578341698274016 s respectively under the existing shared timer.
These local measurements exclude earlier source/environment/domain work
and do not establish mission-scale performance.

The [retained native-mode report](../../tests/data/m3_quarter_second_force_sensitivities.json)
matches both portable runs exactly when excluding elapsed time. Existing
initial/carried quarter-domain reports, force/SPK contexts, endpoint binding,
cubic reference, error transport, short clearance, full coast controls,
exact four-arc lineage and harmonic reuse counts match Decision0049's full
output, excluding timing fields only. Counts remain 13 native / 0 portable
arcs and 14 requests / 4 uncached evaluations / 10 hits. Ruff, strict
OpenSpec, whitespace and legacy isolation pass. The old thresholds, domain
reports and source/native data are unchanged.

Reproduce through the existing SPK inventory test (portable/native-readback)
or the full pinned suite. Local JUnit captures are under
`/private/tmp/ariadna-quarter-sensitivity-ATtJ9p`; the linked JSON is retained
in the repository, not a runtime fallback.

## Next bounded prerequisite

Qualify a reference/source anchor at the fourth endpoint epoch, and bound
its full-force defect on the new interval. The preceding anchor at 0.0625 s
is not this endpoint at 0.125 s. Reuse covered source polynomials only with
the required reanchor checks; do not reuse old D/J, rotation or native
arithmetic results. Before expensive new harmonic/native work, assess which
anchor/rate channels can meet the coupled budget with measured cost.
No fifth arc, targeting, tolerance/cap change or production acceptance change
is authorized by this result. M3 and native-stage/finite-burn safety stay open.
