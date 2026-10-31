# 0127 — Specify independent verification of the retained reference coast

Date: 2026-10-31
Decision status: proposed detailed contract; user explicitly accepted R2 priority.
Implementation: R2.1 contract and eight offline algebraic checks complete; verifier preparation and native execution not started.
Scope / milestone: R2 actual-reference ideal coast, within active M3; no new dynamics.
Base revision: `b5df9f2b597b45b6e683b149d38232ebc322271e`, clean before this documentation stage.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/reference-coast-verification/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; details the now-selected [0126 scope](0126-propose-reference-coast-verification.md), preserving R1 and prior evidence.

## Context and constraints

The user selected independent numerical verification of the actual reference
coast. R1.2's synthetic ellipse does not cover its initial phase or SSB translation;
R1.4's OEM checks cover serialization. This contract defines a distinct check of
unchanged retained data. Priority acceptance is not acceptance of this newly
written detailed contract or an instruction to launch native work.

Bound R2.1 to primary-source equation review, offline synthetic initial-state
algebra and specification. Zero SPICE/native calls, production changes, new
trajectory propagation, dependencies or downloads of mission/kernel data here.

## Options considered

- Use the synthetic oracle unchanged: reject; its fixed periapsis input does not
  represent this reference's actual initial Cartesian state and phase.
- Repeat the production adapter or two Tudat profiles: reject as independent proof.
- Derive ellipse geometry from the original Cartesian seed and solve the elliptic
  time equation independently with stdlib arithmetic: selected contract proposal.
  Do not add an operational dynamics backend or widen to arbitrary conics.

## Decision and rationale

### Frozen input and independent initial condition

Comparison ID `r2-reference-coast-v1`; oracle ID `cartesian-ellipse-bisection-v1`.
Use unchanged `0119-m2-reference.json`, SHA256
`3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0`,
run1, candidate `d0001-t0035`, all121 retained SI/SSB/J2000 states and numeric
TDB epochs. Recheck scenario/selection/count/grid identities and each epoch
`departure_epoch_tdb_s + flight_time_s*k/120` exactly, k=0..120; endpoint epochs
must equal the retained Moon/Mars body epochs and candidate boundaries.
Use literal retained Sun GM `1.327124400420322e20 m^3/s^2`; do not remeasure it.

The Sun track is absent from the old artifact. In a separately instructed study,
read **only Sun** in SSB/J2000/NONE at each exact stored TDB epoch, at most121
provider calls, once per node in order. Keep full returned six-states and labels.
UTC labels are descriptive, never converted back into numeric propagation epochs.
No new Moon/Mars/GM query, planner, sampler, native spacecraft propagation or
historical mission download. The provider may perform its existing UTC-label
conversion per returned state; inventory/time-label calls are not misreported as
spacecraft propagations or extra Sun-state samples.

Require a fresh process and the original complete ordered13-kernel name/SHA256
manifest, before and after the study. Unknown/extra/reordered/missing/drifted
resources or incompatible versions are unavailable, not an admitted substitute.
Freeze Python3.12.14, TudatPy1.0.0, tudat-resources2.4, NumPy1.26.4,
SciPy1.17.1 and SpiceyPy8.2.0; capture actual versions, imports, source/build/native
binary hashes, source revision/dirty paths and unchanged `environment.yml`.
No pool editing or hidden standard-kernel reload after the initial inventory.

Derive the original spacecraft seed from the retained Moon departure-body state
and candidate excess velocity, **not from the propagated first spacecraft node**:

```
r0[i] = Moon.position_m[i] - Sun0.position_m[i]
v0[i] = (Moon.velocity_m_s[i] - Sun0.velocity_m_s[i])
        + candidate.departure_v_infinity_m_s[i]
```

Keep those binary64 operation orders, all raw operands and the resulting seed.
For node k, use `dt = stored_epoch[k] - stored_epoch[0]` in both comparison labels;
never regenerate nominal durations or fit a later state/endpoint. The first
saved spacecraft state is a comparison datum, including the adapter's zero-time
conversion roundoff. Subtract each matching Sun state from the saved state for
the Sun-relative comparison; add it to the independent state for the SSB check.

### Independent equations and admitted numerical domain

Oracle arithmetic uses only stdlib `math`, plain vectors and finite binary64
numbers. No Tudat/SPICE/NumPy/SciPy propagation or element conversions, production
sampler, native returned spacecraft states as seed, fitted elements or shared
writer/conversion helpers. The resource provider remains separate from the oracle.

For the frozen initial r0,v0, with dot products accumulated by `math.fsum`:

```
R = norm(r0); h = cross(r0,v0); H = norm(h)
a = 1 / (2/R - dot(v0,v0)/mu)
evec = cross(v0,h)/mu - r0/R; e = norm(evec)
P = evec/e; W = h/H; Q = cross(W,P)
beta = sqrt(1-e*e); n = sqrt(mu/a**3)
E0 = atan2(dot(r0,Q)/(a*beta), dot(r0,P)/a + e)
M0 = E0 - e*sin(E0)
```

Require finite six-vectors, R>0, H>0, negative specific energy,
`1e9 <= a <= 1e13 m`, `1e-6 <= e <= 0.95`, and orthonormal/right-handed P,Q,W
within1e-12 absolute dot/norm/component tests. These are the private verifier's
admitted numerical domain, not revised mission constraints or a measured claim
about the reference. Reject unsupported/ill-conditioned inputs without changing
candidates or clamping/renormalizing inferred geometry to make a test pass.

At every dt solve `E-e*sin(E)=M`, where `M=remainder(M0+n*dt,2*pi)`, using at
most64 bisections on [-pi,pi]. Require bracket width and absolute equation
residual each<=2e-14rad; exact-root collapse is allowed, unmet stagnation fails.
Evaluate each state from this same seed, never from the previous returned state:

```
Edot = n/(1-e*cos(E))
r = a*(cos(E)-e)*P + a*beta*sin(E)*Q
v = -a*sin(E)*Edot*P + a*beta*cos(E)*Edot*Q
```

The derivative is >=1-e>=0.05 on this domain, giving a unique elliptic root.
The phase-bracket contribution to position is at most a*2e-14<=0.2m;
this is not a bound on libm, geometry recovery or complete floating arithmetic.

### Frozen acceptance gates and pure preparation checks

Every returned Sun state must have exact body/origin/orientation/epoch identity.
All121 pairs must have exact epoch/dt alignment and finite six-state data. In
**both** Sun-relative and re-added SSB coordinates require Euclidean position
<=1m and velocity<=1e-6m/s. These reuse the R1.2 numerical gates; the tighter OEM
wire tolerances remain separate and unchanged. No averaging hides a bad node.

For independent and saved Sun-relative states, relative specific-energy and
vector-angular-momentum errors against r0,v0 must each be<=1e-12:
`abs(epsilon-epsilon0)/abs(epsilon0)` and `norm(h-h0)/norm(h0)`.
Record signed differences/norms at every node, including the initial residual.
These supplement phase comparison, not replace it or certify continuous accuracy.

Before any native study, preparation must verify a=149597870700m, e=0.2,
mu as above, P=(0.36,0.48,0.8), Q=+/-(-0.8,0.6,0), each initial phase
E0=0,+pi/2,pi,-pi/2. Closed-form sine/cosine values produce8 initial fixtures.
Recover a/e/phase/basis and reconstruct each seed within0.01m/1e-8m/s,
relative a error and absolute e error each<=1e-12 and wrapped phase error<=2e-14rad.
Also test forward phase/half-period/full-period times with independent closed-form
expected states, phase wrap, no-thrust energy/h conservation and tilted/retrograde
orientation. A full native-free preparation suite must reject bool/nonfinite,
shape/order/count/GM/frame/time/resource/source errors, domain failures, wrong
translation/phase/units, first mismatch, 122nd-read attempts and every budget edge.

### One bounded evidence run, after verified preparation

One shared cooperative **30s** wall-clock budget begins before scientific imports,
source/resource setup and pure checks and includes all121 possible Sun reads,
comparisons, final provenance checks and evidence finalization. Check it before
and after every top-level call and before publishing success. Record actual
non-preemptible overrun and returned data as failed, not bounded success.

Reserve an exclusively created new output artifact before the first native read.
Increment attempted count before each provider invocation, completed count only
on its return; retain returned data before the after-call deadline gate. Stop at
the first failed/unavailable input, domain, identity, numeric/root/invariant gate,
resource error or overrun. No retries, additional points or changed tolerance,
budget, candidate, epoch or GM. Native spacecraft propagation count must be0.

Output includes fixed contract/reference IDs/hashes, original inputs and all seed
operands, complete Sun track or explicit partial count, both frame comparisons,
root/invariant/translation diagnostics, actual source/resource/build identity,
call order/counts/timings, status/error stage/node and a finite partial result.
Unavailable tooling/resource/domain stays unavailable; numeric mismatch/overrun
is failed. Incomplete nodes have no fabricated endpoint or successful verdict.
A separate stdlib offline audit must recalculate arithmetic/identities/gates
without any new native read; audit disagreement leaves R2 unverified.

## Consequences and revisit conditions

A passing result would independently check this one retained ideal coast and its
frame/epoch arithmetic. The Sun ephemeris is a shared input, not independently
validated planetary truth. Search optimality, all Lambert cases, scalar burn
physics, mass evolution, real lunar escape, finite burns, capture, uncertainty,
continuous safety and M3/M6 remain outside this contract. UI qualification/status
contracts, dependencies, production physics and all historical artifacts remain
unchanged; automation stays paused. A failure stops for review, not auto-tuning.

Accept this detailed contract before R2.2 preparation; verify preparation and
receive a separate execution instruction before R2.3 native work. Unsupported
reference conics or insufficient resources require a new reviewed contract,
not silent fallback. No new study was launched by recording these equations.

## Evidence and verification

Primary sources reviewed for this contract:

- [NASA/TM2018-219992](https://ntrs.nasa.gov/api/citations/20180008672/downloads/20180008672.pdf),
  section3.2 equations2/3/11: h/e-vector/semimajor-axis relations (extracted text;
  screenshot service unavailable). We use vector basis/atan2 instead of its node angles.
- [NAIF OSCELT](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/oscelt_c.html):
  initial-phase convention and near-circular/parabolic/degenerate warnings; no call
  to that routine is permitted in the oracle.
- [NAIF ELLTOF1.2.0](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/elltof.html):
  radian elliptic time equation; [JPL orbital-plane equations](https://ssd.jpl.nasa.gov/planets/approx_pos.html).
  Use neither planetary fitted elements, degree-valued solving nor its ecliptic rotation.
  Velocity and initial-phase vector formulas above are algebraic derivations.

Eight offline initial-state algebra checks using binary64 sine/cosine at the
listed phases pass, without elapsed propagation or native imports: maximum reconstruction0.0001154536891969418m /
1.3612070276481759e-11m/s; wrapped phase1.5543122344752192e-15rad;
eccentricity3.885780586188048e-16 and semimajor-axis9.1552734375e-5m.
These are synthetic initial algebra checks, not reference-coast evidence or a
prepared verifier. The actual reference's admitted-domain membership is unverified
until its Sun-relative seed is available in the separately authorized study.

Pinned source identities:
- `src/space_nav/explorer.py`: SHA256 `0e151f806a8467adc11f88aa86b9721330e20c140c89d7583fbdfbf74b3b81b1`.
- `src/space_nav/ephemeris.py`: SHA256 `70535eb56881ffbc197903e53b675716128ea4630fb4d377bcf63b1a5d56bfea`.
- `environment.yml`: SHA256 `c2948772bfbe09677354f803d9ba79e4c78eb44c5916c98b8d58126832c0e4b7`.

Strict OpenSpec and diff checks pass; all148 local links in the nine changed
documents resolve. All225 tracked runtime/test/example/environment/legacy/evidence
files remain byte-identical to the base; pinned source/reference hashes match.
CURRENT_STATE remains under60 lines. Full runtime tests are not rerun for unchanged
code; R1.4's4766-test result is prior evidence only. No claim
of R2.2 preparation, actual Sun reads or R2.3 numerical success.
