# 0059 — Audit the fourth-anchor ledger before more vector work

Date: 2026-09-15. Parent revision: `52d9dad`. M3 task 3.9 remains open.
Status: documented channel audit and scoped analytic experiment only.

## Available and missing evidence

All new anchor records refer to 978995455.3554223 TDB seconds since J2000,
SSB/J2000 and the same fourth nominal spacecraft state. Their scope is not
the older reference at 978995455.2929223. The remaining horizon is 0.125 s.

| Component | Available evidence | Still missing for a new reference |
|---|---|---|
| Six nominal point forces | Decision0053 exact-polynomial component intervals | Chosen reference coefficients and any native-anchor comparison |
| Six point-source arithmetic effects | Decision0058 | Native point-force arithmetic if a native anchor is used |
| Moon200/Mars120 source arithmetic | Decision0057, new stored matrices | Native harmonic arithmetic and complete vector enclosure |
| Stored-to-ideal PCK force conversion | Decision0056; matrix inputs in Decision0055 | Combined same-state gravity ledger, not just separate channels |
| Harmonic prefix remainder | Decision0054 ideal-frame norm-only screen | Evaluated prefix, stored-matrix/tail consistency and rounding |
| SRP and Sun Schwarzschild | Quarter-domain norms and sensitivities, Decisions0048/0051 | New nominal vectors only if the reference anchor includes them |
| Reference jerk, D/J | Existing analytic lemmas and covered source derivatives | New-epoch jerk, curvature, nonmonopole/rotation rates, reference/chord inclusion |
| Endpoint comparison | Four-arc state and carried errors | Any new reference comparison and endpoint residual |

The ten currently bound gravity-input error channels (six point-source,
two harmonic-source and two PCK-force) have compatible fixed-state
intermediates. Their conservative sum is approximately
1.0394510091222506e-8 m/s^2. Subtotals: 2.7655076190207946e-21 point-source,
1.0237538996626492e-8 harmonic-source and 1.5697109459324815e-10 PCK-force.
This is NOT the full anchor error, nor an unavoidable physical error floor.
Depending on how a reference is constructed, not every native-input conversion
must be charged there; charge each only on an explicitly corresponding path.

## Current-reference budget screen

Preserve the exact carried pair 0.00014951281615784107 m /
9.62662340905759e-7 m/s, the quarter-domain Lx/Lv and the unchanged control
gate. For the existing full-force-anchor convention, keep D_light=2*(S+R).
Charging the above ten bounds while granting zero OTHER anchor error, J and
native endpoint residual gives a formula output 9.752328730456419e-7 m/s.
Remaining separate intercepts are approximately 1.9813701262848377e-7 m/s^2
for other anchor error OR 3.1701922180897708e-6 m/s^3 for J, not both.

Adding Decision0054's optimistic IDEAL-frame Mars degree115 tail leaves only
1.0441319123321644e-9 m/s, or J<=1.336488834265924e-7 m/s^3 if all other
missing channels vanish. Degree119 leaves 2.003778192408359e-8 m/s, or
J<=2.5648360603381126e-6 m/s^3 on the same optimistic terms. These are
scalar planning screens, not permission to substitute ideal-frame tails
into a stored-matrix helper, choose a prefix, assume missing terms zero,
or conclude that the actual trajectory fails. Higher prefix degree alone
does not resolve the unqualified time-rate and residual channels.

## Smaller analytic experiment: a gravity-only reference anchor

A comparison polynomial need not include every physical force in its
coefficients. Keep the TRUE force f=g+l, with g all eight gravity fields
and l the unchanged SRP plus Schwarzschild terms. This is the current
fixed-mass, thrust-off coast only; it is not a finite-burn force split.
Suppose a separately
constructed polynomial q has a GRAVITY-only acceleration anchor and satisfies
`||g(t,q,q')-q''|| <= E_g + J_g*t` on its qualified domain. If the existing
uniform norms give `||l(t,q,q')|| <= S+R`, then triangle inequality gives

`||f(t,q,q')-q''|| <= E_g + (S+R) + J_g*t`.

Only this different reference construction permits a single norm charge.
The existing full-force-anchor helper and reversal counterexample still
require 2*(S+R); do NOT change its factor to one or merely relabel its a0.
The true propagation model still includes all forces, and Lx/Lv must remain
full-force sensitivities for truth/reference state differences. Both paths,
their chords, q'' bound and gravity-rate channels still need qualification.
This does not remove the need to compare a new q with the native endpoint.

As an optimistic comparison only, charging the same ten gravity-input bounds
and S+R gives 9.696154272254801e-7 m/s, before other anchor/J/native errors.
Its separate remaining anchor/J intercepts are 2.430765785078992e-7 m/s^2
and 3.889225275797105e-6 m/s^3. With the ideal degree115 tail, the remaining
J intercept is only 8.526819411339266e-7 m/s^3. This is not a success claim;
it identifies a cheaper reference-construction experiment worth checking
before computing new light vectors or an expensive harmonic prefix.

## Next bounded work and acceptance

Add exact manufactured controls for the gravity-only comparison convention,
not a new production force model or public option. WHEN the reference anchor
excludes bounded nongravity forces, THEN the single norm charge must enclose
the entire constructed interval and preserve nonzero incoming errors. Cover
signed constant and reversing bounded forces, gravitational Taylor remainder,
zero channels, and independent integrated position/velocity. WHEN the reference
instead includes the initial nongravity force, THEN the existing counterexample
must still reject the single charge. Preserve the old helper and old numerical
certificates; no live new-epoch D/J, vector evaluation or fifth arc yet.

## Reproduction and verification

Read the three `m3_fourth_endpoint_*_bridge.json` reports for rotation-force,
harmonic-source and point-source. Sum their `acceleration_l2_allowance_m_s2`
as exact Fractions. With h=1/8, f=Lx*h^2/2+Lv*h and current S/R, evaluate
the existing `_coast_error_envelope` for D=sum+2*(S+R) or the explicitly
hypothetical sum+(S+R). The anchor coefficient in its velocity output is
h/(1-f); the J coefficient is
`h*(Lx*h^3/6+Lv*h^2/2)/(1-f)+h^2/2`. Divide the remaining velocity margin
by the respective coefficient. Tail screens add the relevant nominal-anchor
row from `docs/decisions/experiments/0054-harmonic-tail-budget.json` to D.
All decimals above are explanatory approximations, not new outward constants.

Read-only checks confirm that all ten channels share the same epoch, state,
model, frame/time and SPK context; Moon/Mars source and rotation-force reports
also share matrix and coefficient identities. Exact scalar calculations
reproduce the stated subtotals and separate intercepts. The existing 38
defect-channel controls pass in 0.08 s, including the factor-two reversal.
These are OLD-convention controls, not validation of the proposed new one.

Full pinned suite: 3217 passed in 466.14 s; native/portable inventory
144.63 / 46.74 s. Existing anchor, bridge, domain/sensitivity, context,
reference/error, clearance, lineage and reuse reports match the parent
JUnit run excluding timing fields only. Counts remain 13 native / zero
portable arcs, native harmonic requests/misses/hits 14 / 4 / 10. The suite
is not one 300-second mission run. Ruff, strict OpenSpec, whitespace and
unchanged legacy checksum/import isolation pass. Local logs:
`/private/tmp/ariadna-fourth-ledger-1Bljpf/full-suite.xml`.
This change edits documentation only: no runtime, tests, numerical fixtures
or dependencies. M3, new-reference qualification and mission safety remain open.
