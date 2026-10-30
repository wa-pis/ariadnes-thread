# 0120 — Specify an independent elliptic coast benchmark

Date: 2026-10-30
Decision status: accepted (user approved the contract and requested preparation on 2026-10-30; execution remains separate).
Implementation: private oracle/runner preparation verified in [ADR 0121](0121-elliptic-benchmark-preparation.md); native comparison not executed.
Scope / milestone: small M2 coast-component benchmark for R1.2; not a mission replay.
Base revision: `08e3fd19bb80b16d74952d4d1286a77763349685`, clean before this planning stage.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [0119](0119-positive-ideal-m2-reference.md).

## Context and constraints

R1.1 established a repeatable positive *ideal* reference, not independently checked
propagation. The existing [coast adapter](../../src/space_nav/explorer.py) converts
Cartesian states to elements, propagates with Tudat and converts back. Existing
[circular-orbit tests](../../tests/test_explorer.py) are useful component evidence,
but do not cover varying radius/speed on a non-axis-aligned eccentric orbit.

Check this adapter before expanding the demonstrator. Freeze one synthetic case
at its actual scope; do not pretend to validate the entire Moon-to-Mars transfer,
SPICE origin translation, Lambert targeting, scalar burns or finite thrust.

## Options considered

- Treat repeated Tudat profiles or existing circular tests as the new benchmark:
  reject; repetition is not a new independent eccentric-coast comparison.
- Add GMAT or replay a historical mission now: defer; both require new tooling
  or unresolved force/event/uncertainty contracts disproportionate to this check.
- Independently implement eccentric-anomaly bisection and Cartesian equations
  with Python's standard library: selected proposal. No new runtime dependency,
  production dynamics engine or generic oracle interface.

## Decision and rationale

### Frozen physical problem

Benchmark ID: `r1-elliptic-coast-v1`; oracle ID: `kepler-bisection-cartesian-v1`.
Test the unchanged `explorer.propagate_two_body(initial, elapsed_s, gm_m3_s2)`.
Every invocation starts from the same six-state, not the previous returned state.
The only acceleration is `-mu*r/|r|^3`, in a synthetic Sun-centred inertial frame
with J2000-oriented axes; **not SSB**. This internal adapter benchmark does not
alter the canonical SI/SSB/J2000 public-state contract.

| Fixed input | Value / rationale |
|---|---|
| mu | `1.327124400420322e20 m^3/s^2`, the binary64 Sun GM retained in ADR 0119 |
| Semimajor axis a | `149597870700.0 m`; explicit solar-system length scale, not a fit to a planet |
| Eccentricity e | `0.2`; noncircular, with varying speed/radius, away from singular limits |
| Periapsis basis P | `(0.36, 0.48, 0.8)` along J2000-oriented axes |
| Transverse basis Q | `(-0.8, 0.6, 0.0)`; orthogonal unit vectors give a non-axis-aligned plane |
| t0 | `978995455.2304223` TDB seconds since J2000, copied only as an epoch label from R1.1; synthetic periapsis, not its actual trajectory state |
| Commands / omitted forces | No thrust or impulses, no other bodies, SRP or relativity; no fitted parameters |
| Mass | Not a state of this six-component adapter; mass evolution/error **not modelled**, reported unavailable, not fabricated as zero |

Generate the initial state once in binary64 from
`r0=a*(1-e)*P`, `v0=sqrt(mu*(1+e)/(a*(1-e)))*Q`, then freeze it for both paths:

```
r0_m   = (43084186761.6, 57445582348.799995, 95742637248.0)
v0_m_s = (-29182.918856121985, 21887.189142091487, 0.0)
```

These literals are the authoritative shared Cartesian input. The oracle's
analytic ellipse represents that input to binary64 construction roundoff; retain
the zero-time residual, not a fitted replacement state/eccentricity/rotation.
Use `n=sqrt(mu/a**3)`, `T=2*pi/n` (about `31558196.01538372 s`). Freeze 17 epochs
`epoch_k=t0+k*T/16`, k=0..16, and pass **`elapsed_k=epoch_k-t0` to both paths**.
Epoch rounding must not produce different propagation durations. The period
above is descriptive; recompute it using the fixed formula and retain its actual
binary64 value and all epochs/elapsed times. No UTC conversion is tested here.

### Independently implemented oracle

Use only `math` and plain arithmetic, not Tudat, SPICE, NumPy/SciPy, production
propagation/element conversion or returned native states. Sharing the frozen
inputs/GM is necessary, not shared propagation. The reference equations are
documented by [JPL SSD](https://ssd.jpl.nasa.gov/planets/approx_pos.html) for
orbital-plane coordinates and [NAIF ELLTOF](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/elltof.html)
for the elliptic time equation (documentation v1.2.0). Use radians throughout;
do not copy the SSD page's degree-valued solver, planetary fits or accuracy table.

For each actual elapsed time, set `M=remainder(n*elapsed, 2*pi)` and solve
`E-e*sin(E)=M` by bisection on `[-pi,pi]`. Its derivative is at least `1-e=0.8`,
so the root is unique. Limit to 64 updates, require final bracket width and
absolute equation residual each <=`2e-14 rad`; an exact root can collapse the
bracket. Binary64 stagnation without those bounds is failure, not a retry.

With `s=sqrt(1-e*e)` and `Edot=n/(1-e*cos(E))`, compute
`x=a*(cos(E)-e)`, `y=a*s*sin(E)`,
`xdot=-a*sin(E)*Edot`, `ydot=a*s*cos(E)*Edot`, then
`r=x*P+y*Q`, `v=xdot*P+ydot*Q`.
Velocity follows by differentiating these coordinates; no native velocity oracle
or finite-difference derivative is used. The bracket contribution to position
error is bounded by `a*2e-14 <0.003 m`; that is not a formal libm error bound.

### Acceptance and failure semantics

- Every aligned pair must have finite six-state data, identical numeric GM,
  six-state input and elapsed seconds, and exactly identical epoch labels (0 s
  alignment difference). Use the rounded elapsed value above, not nominal k*T/16.
- At all 17 epochs require Euclidean position difference <=**1 m**, velocity
  difference <=**1e-6 m/s**. These predeclared numerical gates are 100/1000 times
  tighter than the M2 endpoint gates, not real-world ephemeris accuracy claims.
- In each path require relative specific-energy error and vector angular-momentum
  error <=`1e-12` against the shared initial six-state:
  `abs(epsilon-epsilon0)/abs(epsilon0)` and `norm(h-h0)/norm(h0)`.
  These invariants supplement state comparison; they cannot alone verify phase.
- Before native work, verify the pure oracle at elapsed 0, T/2 and T against
  periapsis/apoapsis/recurrence closed forms, within `0.01 m` and `1e-8 m/s`.
  Verify rotation, radian/second conventions, root/finite/shape failures, mismatch
  detection and exact launch/deadline guards with native-free self-checks.
- Missing resources/versions or errors yield failed/unavailable evidence, never
  a penalty trajectory, looser tolerance, new a/e/GM, fitted phase or automatic retry.
  Mass error remains null/not-modelled: R1.1 ideal rocket accounting is separate.

### Bounded execution and evidence

After contract acceptance, implement and check a private evidence script. Only
a separate user execution instruction permits **one** study: at most 17 adapter
invocations (17 Kepler propagations and 34 visible element conversions), in epoch
order, under one cooperative **30 s** wall-clock budget including scientific
imports, provenance, oracle self-checks and comparisons. No planner search,
`sample_transfer`, SPICE request, historical download or native test launch.
Check before/after calls; stop at the first error, mismatch or exhaustion.
A non-preemptible overrun fails with actual time; preserve returned raw data
before the post-call check. On success all 17 pairs must pass; no replay/tighter run.

Bind [R1 evidence](experiments/0119-m2-reference.json), SHA256
`3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0`,
and adapter source SHA256
`0e151f806a8467adc11f88aa86b9721330e20c140c89d7583fbdfbf74b3b81b1`.
Pin Python 3.12.14, TudatPy 1.0.0 and the unchanged Conda environment. Record
actual module/import paths, version/build metadata, source/runner/environment
hashes and measured revision/dirty state. No kernel is needed/loaded for this
synthetic problem: the authoritative GM is the hash-bound earlier SPICE value,
not a new ephemeris query or independently measured gravitational constant.

Retain new finite JSON with inputs, actual times, oracle root diagnostics,
both raw six-states and signed component differences/norms, invariants, per-point
status, attempted/completed call counts and timings, including partial failures.
Use exclusive creation; preserve all previous evidence. Audit retained arithmetic
without native calls. R1.2 remains open until this declared comparison passes.

## Consequences and revisit conditions

This checks a synthetic inclined eccentric *coast component*, not arbitrary
conics, the full R1.1 coast or its Sun-to-SSB translation, optimization, reserve,
finite burns, navigation uncertainty or mission safety. A failure stops for
diagnosis and a reviewed new contract; it cannot automatically expand compute
or weaken these gates. Success permits R1.3 profile design, not M3 closure.
Public API/UI/exporters, dependencies, strict M3/task 3.9, automation and historical
missions stay unchanged. No independent finite-thrust/GMAT/M6 claim is permitted.

## Evidence and verification — original planning stage

Read the adapter and existing circular tests; checked official JPL/NAIF equations
on 2026-10-30. Native-free input arithmetic reproduces the literal six-state,
period and orthonormal basis. Strict OpenSpec, local links, diff/scope and legacy/
historical-evidence hashes are checked for this planning stage. No runner/oracle
implementation, native propagation or new scientific pass is claimed. Runtime
tests were not rerun in that stage. User acceptance and the native-free preparation
were subsequently recorded in ADR 0121; separately instructed execution is pending.
