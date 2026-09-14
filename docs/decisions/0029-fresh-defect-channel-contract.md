# 0029 — Separate fresh defect channels before transport

Date: 2026-09-14. Parent revision: `ea45b98`. Task 3.9 remains open.

## Finding from the existing implementation

The old cubic does not use a time derivative for every force. In
`_check_conditional_full_force_coast_domains`, its constant defect includes
`prefix_full_error_m_s2 + 2*(srp + relativity)`. Its rate includes monopole
curvature/jerk error, nonmonopole translation and rotation. Therefore the
old rate cannot accompany the fresh pointwise error by direct substitution:
that would silently discard the norm-only allowance for two force changes.
This is a prerequisite clarification, not a discovered failure in the
existing shifted-cubic certificate, which retains those channels.

## Minimal sufficient fresh contract

Let q be the fresh cubic from Decision0028, h its 1/16 s horizon, a0 its
observed acceleration, and j0 its retained monopole jerk. All norms below
are L2 with compatible operator bounds; exact L1 upper bounds may replace
vector norms. Let E0 bound ||f(0,q0,v0)-a0|| as in Decision0026. Let S and
R uniformly bound the ideal SRP and Schwarzschild acceleration norms over
the same cumulative domain, including the fresh anchor.

For ideal source i, bind its fresh polynomial velocity v_i0 and uniform
polynomial acceleration bound B_i. Let A bound ||q''|| throughout the
fresh interval, V_i0 >= ||v0-v_i0||, and d_i be the existing qualified
relative distance floor. Define:

    A_i = A + B_i
    V_i = V_i0 + A_i*h
    displacement_i(t) <= V_i0*t + A_i*t^2/2
    K_i = 24*GM_i*V_i^2/d_i^4 + 2*GM_i*A_i/d_i^3

The existing `_point_mass_force_curvature_bound_m_s4` supplies K_i. For
Moon/Mars let L_i bound the nonmonopole spatial Jacobian, and W_i bound
the acceleration variation per second due solely to rotation. Let E_j
be the fresh ideal-monopole jerk midpoint/enclosure allowance, including
midpoint rounding. A sufficient pair is:

    D = E0 + 2*(S + R)
    J = E_j + h*sum_i(K_i)/2
        + sum_Moon,Mars(L_i*(V_i0 + A_i*h/2) + W_i)

Here D has units m/s^2 and J has units m/s^3. Decompose f(t,q,q')-q'' into
the initial full-force error, monopole Taylor remainder and jerk mismatch,
nonmonopole translation/rotation changes, and the two remaining force
changes. The triangle inequality bounds the last two by 2*S and 2*R;
t^2 <= h*t bounds the Taylor and displacement terms for every 0 <= t <= h.
Consequently ||f(t,q,q')-q''|| <= D+J*t on this interval, provided every
domain/source premise below is rebound. This derivation does not establish
a numerical J or an endpoint certificate by itself.

## Rebinding requirements and next implementation

- Use named fresh coefficients and the unchanged incoming error radii.
  Recompute V_i0 from the fresh source derivatives, not the old epoch.
  The selected source-polynomial acceleration bounds cover both epochs;
  assert fresh interval containment in their existing guarded records.
- Reuse the cumulative domain floors and uniform force/Jacobian bounds
  only after Decision0028's reference/conditional true-state inclusion
  and the original source/PCK coverage are checked. A smaller fresh
  duration does not license resetting the domain centre or distance floor.
- For W_i use the existing partitioned rotation bound divided by the
  ORIGINAL cumulative duration, not by the fresh half-duration. The code
  explicitly checks both partition branches are linear in elapsed time;
  the PCK angular/pole rates and radii must cover the entire subinterval.
  Do not divide a capped endpoint-only rotation bound by elapsed time.
- Reuse full nonmonopole degree-map Jacobians with C00 excluded there;
  all eight monopoles remain in the separate curvature/jerk sum.
- E0 already includes source arithmetic and ideal-PCK anchoring channels.
  Do not add them again to E0, or to ideal-polynomial motion terms. E_j
  is a nominal ideal-monopole allowance, not a full-force derivative error.
- First add a small exact manufactured control with a norm-bounded force
  reversal to expose a missing factor two, plus a quadratic monopole
  remainder. Then bind/report these channels in the existing live probe
  without a new native call. Only then apply `_coast_error_envelope` with
  uniform Lx/Lv and add the existing native-to-fresh endpoint residual once.

The constant norm-only channels deliberately trade tightness for reuse of
already qualified bounds. Derivative-based SRP/relativity refinement is
unnecessary unless the measured fresh endpoint gate actually needs it.
No prediction of gate success follows from the smaller observed residual.

## Verification scope

Read-only inspection of the cubic, curvature, rotation and transport
implementations and the retained previous full-run output. Documentation
only: strict OpenSpec and whitespace checks pass. No test code, numerical
data, native calls, dependencies, scientific tolerances or production code
changed. Full pytest was not rerun; the latest implementation evidence
remains 3074 passed in 494.64 s (native169.41, portable55.86). No mission
safety or new interval qualification is claimed.
