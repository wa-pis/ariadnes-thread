# 0131 — Screen omitted gravity without propagating invalid endpoints

Date: 2026-11-01
Decision status: accepted bounded design under the user's autonomous-continuation authorization; not separately user-reviewed numerical parameters.
Implementation: R3.1 design and offline endpoint-domain audit complete; R3.2 preparation and R3.3 native screening not started.
Scope / milestone: current M3 research demonstration, local force screening only.
Base revision: `b794ebfadbe74409109b0f79f4a36a3528a6582d`, clean before this stage.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/omitted-gravity-screening/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; preserves [R2 evidence](0129-reference-coast-verification-passes.md), [full regression](0130-full-regression-after-reference-verification.md) and [finite-radius departure work](0102-consistent-lunar-departure-design.md).

## Context and constraints

Numerical agreement of the Sun-only reference does not establish the magnitude
of omitted gravity. However, simply adding lunar/Martian exterior gravity to
its endpoints would evaluate a physically inadmissible state: M2 represents
body-centre encounters, not finite-radius parking or capture states.

[The new offline endpoint audit](experiments/0131-endpoint-domain-audit.json),
SHA256 `5f934404dd0a0da11bc1586b28adf3504307361075b20fceb550407cadd4063a`,
recomputes original spacecraft-minus-body positions at the two exact epochs:

- Node0, Moon: distance0.00033742285747521945m, inside1737400m exclusion sphere.
- Node120, Mars: distance0.002428833056893391m, inside3396190m exclusion sphere.

Binary64 hypot agrees with independent80-digit Decimal differences/sqrt within
1e-18m. Both findings are expected limitations of the declared ideal reference,
not a failed R2 check or evidence of a physical trajectory through either body.
The tiny nonzero distances are conversion residuals; do not use them as physical
radii, add epsilon, clip forces or extrapolate a point-mass field into an interior.
No native imports, queries, spacecraft propagation or runtime changes occurred.

## Options considered

- Propagate the unchanged body-centre reference with full gravity: reject;
  exterior endpoint fields and mission boundary conditions would be invalid.
- Immediately resume finite-burn targeting: defer; the user asked for bounded
  verification, and a new outer-transfer/capture match is not specified.
- Screen local omitted point-mass gravity at three fixed retained epochs, explicitly
  classify inadmissible terms and check arithmetic independently: selected.
  This is a prerequisite diagnostic, not trajectory refinement or a safety test.

## Decision and rationale

### Frozen question and data

Question: what are the local Earth/Moon/Mars third-body acceleration terms at
retained nodes0,60,120, and where are those exterior force evaluations admissible?
Do not ask whether a trajectory reaches Mars, is safe or is accurate to a specified
miss distance. A local acceleration is not an integrated trajectory error.

Bind unchanged ADR0119 run1/candidate d0001-t0035 and its original digest
`3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0`,
and ADR0129 raw evidence digest
`e2c5d077285fe0218d1c93f3000f319048006eb55477d680f83041f6c70ce9d7`.
Use only the three original numeric TDB epochs and their stored SI/SSB/J2000
spacecraft and Sun states. No new spacecraft initial/target state, fitting,
resampling, interpolation, Lambert solution, integration or maneuver is involved.
Preserve original scenario, GM values and every historical artifact.

Use retained Sun/Moon/Mars GM, respectively1.327124400420322e20,
4902800205346.301 and42828375010399.99m^3/s^2; obtain Earth GM once from the
pinned SPICE provider. Reuse the original Moon node0 and Mars node120 states.
Acquire only the missing exact-epoch SSB/J2000/NONE body states, in this order:
Earth0, Mars0, Earth60, Moon60, Mars60, Earth120, Moon120. Exactly seven possible
new body-state calls plus one possible Earth-GM read; no Sun requery or extra body.
Keep actual labels, raw coordinates, source call order/counters and all operands.

For exterior-domain screening use the existing pinned collision resource's
conservative maximum radii: Sun696000000m, Earth6378136.6m, Moon1737400m,
Mars3396190m. These are declared exclusion spheres, not new measured radii or
terrain/atmosphere models. In particular the Mars guard differs from M2's3389500m
orbital-shape radius; do not substitute one silently. Preserve original ordered13
kernel name/hash manifest, including the pinned pck00010 resource, before/after.
Freeze ADR0128's Python/scientific versions, actual imports/build/binary/source
identities and current prepared-runner hashes. No resource replacement or reload.

### Explicit frame and independent arithmetic

Let x be spacecraft-minus-Sun position, b be body-minus-Sun position, and d=b-x.
For each body B in Earth/Moon/Mars evaluate, only outside its exclusion sphere,

```
a_B = mu_B * (d / norm(d)^3 - b / norm(b)^3)     [m/s^2]
a_Sun = -mu_Sun * x / norm(x)^3
```

This is Sun-relative point-mass differential gravity: the indirect term subtracts
the body's acceleration of the Sun. It is not direct SSB acceleration and not
a claim that three bodies reproduce the second derivative of the full SPICE Sun
track. SI, TDB seconds since J2000 and J2000 axes are explicit at every boundary.

Require finite nonboolean positions/GM, positive GM and nonzero norms. Admit a
body term only if norm(d)>its guard and norm(b)>its guard; require the spacecraft
outside the Sun guard as well. Inside/on a guard, record `inadmissible` with raw
distance and reason and no acceleration value for that term. Such a term must
not be included as zero. Rows0/120 are expected to be partially inadmissible;
this expected classification is not a numerical failure. All three middle-node
terms must be admissible; otherwise stop unavailable for scope review.

For each admitted term compute binary64 arithmetic using stdlib math and compare
with a separately implemented80-digit Decimal oracle. Convert exact stored
binary floats with Decimal.from_float; use direct/indirect unit vectors divided
by squared distances, rather than sharing inverse-cube/vector helpers. Each
signed component difference must be <=max(1e-15m/s^2,1e-11*norm(a_Decimal)).
These are arithmetic gates, not thresholds of physically negligible perturbation.

Retain signed direct, indirect and differential vectors, distances, numeric
errors, and each individual norm divided by norm(a_Sun). For the fully admitted
middle row also retain the vector sum, norm of that sum, sum of individual norms
and their solar ratios, so cancellation cannot hide a large individual term.
For partially inadmissible endpoint rows keep valid individual terms but no
three-body sum or total ratio. Do not turn these samples into a whole-arc bound,
constant-acceleration displacement estimate or propagated miss-distance estimate.

Before native work, test independent closed-form collinear inputs (for example
mu8, x=(1,0,0), b=(3,0,0) gives a=(10/9,0,0) in synthetic units), tilted/rotated
and translated-frame inputs, sign/indirect-term corruption, small differential
cancellation, exact guard boundaries and both retained endpoint classifications.
Synthetic-unit fixtures must be distinct from the real SI screening contract.
Verify all wrong-body/epoch/unit/frame/GM/hash/shape/bool/nonfinite/domain and
call/deadline/error/partial-output paths, without scientific imports or queries.
A separate offline audit must re-evaluate available Decimal terms, identities,
classifications, sums, ratios and gates from saved data before completion.

### Single bounded screening, after verified preparation

One fresh-process cooperative30s budget includes scientific imports, frozen-input
checks, pure checks, identities/inventories, at most seven body-state queries and
one Earth-GM query, arithmetic, final identities and exclusive evidence-file
serialization/flush. Zero native spacecraft propagations, searches or integrations.
Record attempted and completed counts separately; preserve returned raw data
before checking the after-call deadline. Initial/final inventories and source/
resource/build identities must agree. Check time before/after calls and at final
flush; non-preemptible overrun is failed and retained, never bounded success.

Reserve a new exclusive artifact before native work. Stop on first unexpected
unavailable input, missing coverage, mid-row domain failure, arithmetic mismatch,
identity drift, resource/provider failure or overrun, without retries, replacing
nodes/bodies/data or changing tolerances/budget. Output finite explicit partial
failure evidence; do not fabricate absent terms or certify physics. If resolving
failure needs a new contract or user action, pause automation and explain it.

## Evidence and verification

Primary equation source: [Tudat third-body accelerations](https://docs.tudat.space/en/stable/user-guide/state-propagation/propagation-setup/translational/third-body-acceleration.html),
sections Third-body perturbation and Direct gravitational acceleration. The
reviewed live page now identifies1.1.0; use its mathematical difference of fields
only, not an API upgrade or evidence of the pinned1.0.0 implementation's behavior.
The explicit Newtonian inverse-cube equation and Decimal rearrangement above are
algebraic specializations. No new API or native behavior is claimed verified.

The offline endpoint audit is the only new numerical evidence at this stage.
R3.2 oracle/runner/tests and the native force-screening outcome remain unimplemented.
Strict OpenSpec and diff checks pass; all157 changed-document local links resolve,
231 previously tracked protected runtime/test/example/environment/legacy/evidence
files are unchanged, and source/digest/Decimal arithmetic checks pass.
CURRENT_STATE remains under60 lines. No unchanged
runtime suite is rerun; ADR0130's4852-test result remains prior regression evidence.

## Consequences and revisit conditions

The next heartbeat may prepare this specified private diagnostic under the user's
bounded-continuation authorization; execution follows only verified preparation.
No user participation is currently needed. Even a passing screening would measure
only three bodies at three epochs: Venus/Jupiter/other planets, harmonics, SRP,
shadows, relativity, thrust, mass and uncertainty are not covered or bounded.

Finite-radius lunar escape/outer-transfer/Mars arrival matching must be designed
before a physical complete-coast refinement; old D13/D17 results do not supply
that mission automatically. Preserve R1/R2 validity at their declared scope,
strict M3/task3.9, mission safety and UI status unchanged. Do not infer that the
three-body sum is the total missing force or that a small sample proves safety.
