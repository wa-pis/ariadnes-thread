# 0151 — Attribute the first synthetic rejection at frozen stages

Date: 2026-11-01
Decision status: accepted under the user's instruction to continue diagnosis.
Implementation: bounded offline arithmetic audit complete; application/helper/test/environment unchanged.
Scientific status: timestamp noise explains the first frozen synthetic estimator rejection; historical R5 causality remains unproven.
Scope / milestone: M3 R5 diagnosis; saved ADR0150 synthetic data only.
Base revision: `04f7fa5c4a77a4eef5d9bb620a7c02d7c7396b8a`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [ADR0150](0150-synthetic-step-trace-and-binary-localization.md), preserves ADR0137/0148.

## Context and constraints

ADR0150 observes a first rounded-time trial rejection on[0,1]s with normalized
error15.733943746271663; controls accept their first trials. It does not yet
separate timestamp noise, reconstructed geometry and scalar field arithmetic
inside that estimator. The user asked to investigate further. Use retained
operands rather than acquire states or rerun a trajectory. Raw failure flags
are not monotone in elapsed time; this step does not refine a continuous root.

## Options considered

- Raise caps, change tolerances or rerun R5: reject; no diagnosis or justified
  revised reference contract.
- Add three more integrations: defer; saved stages already answer a smaller
  attribution question without changing adaptive history.
- Reconstruct only the first trial in each retained synthetic arm and decompose
  its field and embedded error vectors: selected; fixed, bounded and checkable.

## Decision and fixed offline contract

One stdlib-only invocation uses the first13 RHS records and first trial from
exactly the three ADR0150 arms:39 saved stage operands, no new solve or source
query. Preserve s, q, h=1s, scales, initial states, epochs, mu, translation and
controller settings. Bind the0150 raw trace/helper/test/verification and local
installed rk/coefficient sources by hashes; verify installed sources against
retained0148 runtime identities. Read coefficients through literal AST parsing,
never execute/import SciPy or any evidence-provided code. Rebuilt binary64 E3/E5
byte hashes must match retained0148 metadata. K0 is the initial saved derivative;
K1..K12 are the following12 callbacks. No retry-stage reuse inference is needed
because only the first trial is selected. Check stage abscissae, nfev=13 and
original scale construction before interpreting any result.

At80 and100 Decimal digits compute, at each frozen s,q:

1. Reference field from exact binary64 local relative operands.
2. Clock field from that separation plus V*((t0+s rounded)-t0-s) in the
   rounded arm, zero actual clock shift in both controls.
3. Geometry field from the exact operands of the replayed binary64 separation.
4. Saved actual force; never query a source for a replacement.

Signed differences clock-reference, geometry-clock and actual-geometry telescope
into actual-reference at fixed state. This ordering assigns mixed terms to the
geometry residual; it is an attribution convention, not a universal causal split.
The control's logged hypothetical absolute-time residual is not an actual clock
shift. Verify each retained Decimal reference and phase residual and the saved
actual field against the unchanged source formula at its reconstructed geometry.
For linear translation only, removing the clock displacement restores
the reference separation algebraically (check within1e-60m at Decimal precision); this identity is not a real-ephemeris implementation.

Replace only the acceleration components of each fixed K vector at the four
levels; retain observed q-velocity derivatives and scales. Apply the pinned
E5/E3 coefficients and original nonlinear norm. Retain signed vector contributions;
scalar norms are nonlinear and SHALL NOT be added as causal percentages.
Reconstruct actual logged E5/E3 within a separately declared arithmetic bound:
u=2^-53, gamma32=32u/(1-32u), component bound gamma32*sum(abs(Ki*Ei))/scale
plus u*abs(saved scaled component). This conservative normal-number dot/division
bound covers13 products/12 sums/division and possible input rounding. It does
not relax any force/state/scientific gate. Bound hypothetical scaled vectors
similarly; report norm diagnostic intervals from their component boxes, padded
by1e-40 for Decimal arithmetic. A box spanning1 is ambiguous. Compare80/100-digit
vectors/norms within1e-40 absolute; otherwise retain failure, no interpretation.
These are arithmetic diagnostics, not physical/global error bounds.

Use a shared5s cooperative process/import/read/hash/arithmetic/JSON/flush budget,
39 saved stage operands at two precisions and at most234 Decimal field evaluations.
Preserve finite exclusive partial evidence on failure; no tuning or repeated
scientific attempt. The one-off invocation is retained as text, not a production
adapter or new imported/test helper. Check analytic radial/sign and zero-shift
identities before the39-row audit. Reuse5285 tests/Ruff because runtime/helper/
test/environment bytes stay unchanged; verify protected files, artifact identities,
finite JSON, local links, diff and strict OpenSpec. Automation remainsPAUSED.

## Consequences and revisit conditions

A smaller frozen-stage norm after removing clock noise explains contamination
of the saved estimator, not the trajectory or decisions of a corrected solver.
Saved q/scales already reflect the original noisy stages. Actual R5 rejection
history and physical Earth sensitivity remain unavailable. No mission/M3/safety
claim. Relative coordinates alone cannot preserve sub-ULP time through a scalar
binary64 SPICE boundary. Future compensated rephasing/interpolation needs its own
approximation/velocity-consistency/error/identity/native-budget contract; no such
replacement or real-state run is implemented or authorized by this audit.

## Evidence and verification

One [retained invocation](experiments/0151-frozen-stage-invocation.txt) passes in
0.06713104108348489s before flush, with finalization passed. [Raw evidence](experiments/0151-frozen-stage-audit.json)
and [output](experiments/0151-frozen-stage-output.txt) retain39 fixed first-trial
operands at80/100 digits and234 Decimal field evaluations, no new scientific
imports/source requests/integrations. Literal coefficient E3/E5 byte hashes match
the previous runtime; stages/counters/scales, radial/sign/zero-shift/rephasing
identities, signed telescoping and observed estimator arithmetic bounds pass.
Maximum80/100 vector/norm/box/field discrepancy4.657321750934311e-69 is below1e-40.
A separate read-only review confirms saved coefficients, vectors/norms/boxes and
interpretation without scientific imports, queries or integration.

For the rounded-time first trial, only acceleration components change between
these frozen-state estimator reconstructions. The original observed norm is
15.733943746271663; exact-operand dot reconstruction differs slightly through
floating dot arithmetic, and the observed value lies inside the actual-field box.

| Frozen field level | Reconstructed norm | Arithmetic diagnostic box | Relative to1 |
| --- | ---: | --- | --- |
| Local reference | 0.0288928303 | [0.0288927830,0.0288929932] | below |
| Add clock displacement | 15.6792395082 | [15.6791416553,15.6793373611] | above |
| Add geometry arithmetic | 15.7339419039 | [15.7338440537,15.7340397540] | above |
| Saved actual field | 15.7339434170 | [15.7338455668,15.7340412671] | above |

Rounded table values are summaries; raw Decimal endpoints are authoritative.
Thus the clock term alone is sufficient to push this frozen-stage estimator
above1. It is not a causal percentage or a corrected integration result.
Largest first-trial clock field contribution is2.523444833734445e-9m/s^2;
geometry residual1.008366290542493e-11m/s^2 and field-arithmetic residual
4.810854319625758e-16m/s^2. Ordering/mixed-term convention is as specified above.
Signed scaled velocity-x contributions are:

| Contribution | E5[vx] | E3[vx] |
| --- | ---: | ---: |
| Clock | +40.26648177 | -126.84108409 |
| Geometry | +0.13955590 | -0.40719465 |
| Field arithmetic | +0.0000038884 | -0.0000123388 |

Position-derivative components are frozen in all levels; notably E5[x]=0.08483415
and E3[x]=0.55906871 retain earlier stage contamination. Clock-free reference
norms of the relative and absolute-local controls also have boxes below1; their
actual observed first trials were already accepted. No trajectory has been
recomputed, no actual controller decision changed and no continuous root located.

[Verification](experiments/0151-verification.json) binds all raw artifacts and300
protected tracked source/test/example/environment/legacy/experiment files, all
unchanged from04f7fa5. Reuse5285 full tests/Ruff from ADR0150 on identical runtime/
helper/test bytes; no full-suite repetition. Strict OpenSpec, finite JSON, hashes,
local links and diff checks pass. Automation remainsPAUSED.

The next useful contract is a minimal compensated-time candidate: after a query
at rounded t_hat, assemble B(t_hat)+V(t_hat)*delta, delta=exact(t0+s)-t_hat,
directly into compensated relative separation. This cancels the clock displacement
algebraically for this linear fixture (the audited1e-60m check passes). Real
SPICE use still requires verified velocity/position consistency, an acceleration
bound for the Taylor remainder, coordinate arithmetic, unchanged kernel identity
and a finite new sampling/propagation budget. This record authorizes no such
replacement or R5 repeat. Relative coordinates alone or passing Decimal to a
binary64 epoch boundary do not address that remaining approximation contract.

Installed source is authoritative for this pinned checkout. Primary interface references: [NAIF spkezr](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkezr_c.html)
accepts a SpiceDouble epoch in TDB seconds past J2000; [SciPy1.17.1 rk.py](https://github.com/scipy/scipy/blob/v1.17.1/scipy/integrate/_ivp/rk.py)
defines the stored-stage E5/E3 norm and step acceptance. Local hashes, not online
file contents, bind the actual arithmetic audit.
