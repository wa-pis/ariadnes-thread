# 0115 — Implement smooth quadratic steering targeting

Date: 2026-10-17
Decision status: accepted
Implementation: complete; focused/native and full regression verification pass.
Scope / milestone: M3 research D17.2 only; no retained-reference D17.3 execution.
Base revision: `e3e188cdd7046b011cd5f2a7da846427359fa691`, clean before this stage; this commit contains the implementation and its tests.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [0114](0114-quadratic-steering-freedom.md) without changing previous experiments.

## Context and constraints

The saved D16 response motivated additional steering freedom, not additional
fuel or a relaxed target. Implement the approved quadratic chart separately,
preserving the original physical domain, point-Moon dynamics, target six-state
and absolute epoch, profiles and closure/agreement thresholds. Synthetic root
convergence verifies implementation behavior; it does not establish that the
retained lunar branch is reachable with this guidance.

## Options considered

- Modify D16 or duplicate its physical propagation: rejected; old behavior and
  its evidence must remain reproducible, and a second mass/gravity model adds
  no value to this experiment.
- Add one private D17 orchestration module using the existing physical domain,
  endpoint checks and native burn/coast adapter: selected. No new dependency,
  public interface, UI control or general optimization framework is required.

## Decision and rationale

[bezier_local_targeting.py](../../src/space_nav/bezier_local_targeting.py)
implements eight physical controls and six residual components. Validate all
six slope coefficients, then project the endpoint controls into the unchanged
domain constructor. A normalized quadratic Bernstein chart adds two middle
control-point slopes, not midpoint-time directions. Convex weights bound the
complete physical chart; extend the same polynomial through native trial
stages without clamping, a guidance kink or a third arc. The rate upper bound
is recorded as a diagnostic, not a hardware constraint.

Bind pinned 0104/0107/0110/0113 inputs and reconstruct every retained command,
endpoint, residual and mass check. Select accepted interior proposal 158 only.
First replay its old two-node model, then the embedded quadratic model. The
old replay must match the saved endpoint, and the new replay must match both
saved and fresh old endpoints within 1 m / 0.001 m/s / 1e-6 kg. Keep reference
and new-model identities separate. Only the new seed may qualify or supply
the single exact initial objective cache; later requests are fresh evaluations.
SciPy's initial request must reconstruct the seed exactly, not silently move
it from a bound. Any mismatch stops before derivatives.

The binder explicitly accounts for historical version differences: D15's
saved runtime lists NumPy/TudatPy, whereas D16 additionally records SciPy
1.17.1. Compare the shared historical versions and the explicit D16 SciPy pin;
do not demand identical dictionaries or rewrite historical evidence. Today's
source hashes and versions remain separate from retained source provenance.

Reuse pinned SciPy TRF/exact/linear with the frozen scales/tolerances and serial
calls. Preflight all sixteen fixed-step commands before any derivative launch,
using central, forward or backward second-order pairs as specified. Store the
6x8 matrix, six singular values, eight-component measured gradient and its
parent ID. Strict physical bound comparisons and both margin vectors identify
face-free columns; store their row-rank diagnostics separately from the full
matrix. These are not a full feasible-tangent-cone, reachability or final
optimizer-stationarity certificate. No rank-eight gate or extra residual exists.

The first eligible seed/objective closure stops before another Jacobian and
permits exactly one frozen tighter repeat. Both profiles must close and agree,
with analytic cutoff mass and exact coast mass. Reference replays, probes,
optimizer success and lower score alone cannot qualify. A tighter failure
ends the study; there is no resumed correction or alternate command.

Count independently: two nominal replays, at most 40 objective requests
including one cache hit, 40 batches of sixteen probes, 681 nominal evaluations,
682 total evaluations and 1364 attempted native launches, with the tighter pair
reserved. One cooperative 300-second clock starts before binding. Preflight a
whole batch's affordability, count attempts before entry, stop after an
incomplete arc, and preserve a completed cutoff on coast failure. Record best
eligible objectives, accepted iterates and measured Jacobian parents separately;
do not invent a returned solver status or active mask after interruption.

## Consequences and revisit conditions

D14/D15/D16 source, native profiles, target/time, force and fuel model remain
unchanged. No dependencies, public API, CLI or UI change. The cooperative clock
cannot preempt a blocked native call. Earth/Sun, harmonics, radiation pressure,
relativity, Mars capture, whole-interval safety and hardware qualification remain
outside this local experiment. Strict M3/task 3.9 stays open; automation stays
paused. The existing Streamlit interface does not expose this private experiment.

D17.3 requires a separate user instruction for one retained-reference study.
Only that result can measure real-branch closure. Stop for scope review if it
does not close; do not automatically add nodes, widen bounds, change the target
or fuel, increase the budget, select another seed or rerun.

## Evidence and verification

[Solver tests](../../tests/test_bezier_local_targeting.py) use independent coupled
linear/quadratic 6x8 residuals with real SciPy and an unattainable active-bound
target. They check all stencil formulas, scaling, full/free ranks, gradient
parent/margins, role eligibility, both replay gates and three endpoint
comparisons, initial cache, adjusted-seed rejection, first closure, closed
probes, frozen tighter checks, honest termination and every independent budget.
Pure retained binding and injected runner tests exercise provenance without
propagating the actual retained reference. A constant-residual provenance test
accepts the actual optimizer stop reason: rounding at large physical endpoints
can yield xtol rather than gtol. Neither is relabelled physical closure.

[Physics tests](../../tests/test_bezier_local_physics.py) independently use de
Casteljau interpolation, all 64 slope-box corners, rotated bases, physical-curve
envelopes, smooth rate, polynomial extrapolation, linear embedding, actual-time
circular rotation, frozen target epoch and Decimal mass. Native nonzero-curvature
burn/coast tests use a manufactured negligible-gravity case and independent
256-point Gaussian acceleration integrals with variable mass in BOTH unchanged
profiles: 0.001 m / 1e-6 m/s / 1e-6 kg. Native old-chart parity also exercises
non-negligible gravity. Impact/dry-mass/deadline guards and partial-cutoff
retention are checked through the existing TudatPy boundary.

The two new test files contain 258 passing cases. Combined local/native and
environment regression: 607 tests pass in 3.38 s. Ruff over all source/tests and
strict OpenSpec pass. Independent read-only review found no blocking defects.
Seven prior source hashes, five retained research hashes (0104/0107/0110/0113/0114),
legacy, environment/package pins and the historical environment remain unchanged.
Python 3.12.14, NumPy 1.26.4, SciPy 1.17.1, TudatPy 1.0.0, SpiceyPy 8.2.0 and
tudat-resources 2.4 are installed as before. SciPy retains Conda build
`py312h4519d97_1`; the actual 13-kernel SPICE inventory/hashes match retained D16,
and the installed lunar coefficient resource hash also matches its binding.
Full regression: 4,588 tests pass in 626.08 s using
`conda run --no-capture-output -n space-nav python -m pytest -q`.
The verified new runtime SHA256 is
`88621f68d2efee4d4f456617dd3b169964a813fd6fc713c7143b2cda01d6bd7f`;
runtime/tests were unchanged throughout that full run. Local documentation links
and whitespace checks pass. D17.2 is complete. No retained-reference D17.3 native
study was executed; these tests make no claim of real-branch closure or strict
M3 qualification.
