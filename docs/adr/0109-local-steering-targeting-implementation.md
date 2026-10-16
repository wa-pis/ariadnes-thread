# 0109 — Implement bounded local steering targeting

Date: 2026-10-16
Decision status: accepted
Implementation: complete; focused/native and full regression verification pass.
Scope / milestone: M3 research D15.2; no D15.3 reference-case execution.
Base revision: `89bb3c1cc803d7ab9f22b2f23ac28a9a5e717e8d`; runtime/tests are introduced with this record.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [0108](0108-bounded-local-steering-targeting.md), preserving D14 and immutable 0104/0107 evidence.

## Context and constraints

D14's measured miss does not establish whether a steered command can satisfy
the fixed local boundary conditions. Implement the accepted six-control test
without widening its bounds, moving its target, changing profiles/dependencies,
adding a production optimizer or running the retained reference experiment.
Passing synthetic tests establishes implementation behavior, not reachability.

## Options considered

- Modify D14's fixed-command orchestration/budget: rejected; it must retain its
  four-arc behavior and independently reproducible comparison.
- Duplicate the native environment/integrator: rejected; unnecessary second
  implementation of the same Moon-only physics and state/mass guards.
- Add a private targeting module and an optional private direction callback to
  the existing native arc: selected. No public API, CLI, UI or dependency change.

## Decision and rationale

[local_targeting.py](../../src/space_nav/local_targeting.py) binds both pinned
reference hashes and reconstructs the complete D13 branch through D14. Validate
the old command, launch window, model/frame/units, resources, profiles, both
retained endpoints/masses/residuals and agreement before any native work.
Keep historical source hashes separate from the current source hashes. Save
current kernel metadata/runtime versions; never silently substitute ephemerides.

Freeze the D14 six-state target and absolute match epoch. Construct an immutable
domain from the original circular state/window/reserve. Every command recomputes
its analytic cutoff mass and provisional arrival reserve. Mass is not a seventh
target constraint. Apply the fixed ignition/duration/slope bounds and minimum
one-second coast without clipping, including floating-point mass-bound equality.

Use the deterministic least-aligned-axis basis and normalized two-node chart of
0108. Slopes are dimensionless, not angles. Guidance reads native relative burn
time and propagated mass; thrust magnitude/Isp remain fixed. RK trial stages can
extend beyond the exact endpoint: extend the same smooth chart for those internal
stages rather than clamping it. Accepted histories still end exactly at cutoff;
the separate coast has zero thrust/mass flow and exact handoff.

Absolute epochs have finite floating-point resolution. Rotate parking phase by
the actual representable ignition shift, not an unrepresentable control delta.
Preserve the baseline's exact initial-state/relative-time arithmetic for replay;
new commands compute their remaining coast time from the frozen absolute epoch.
A full proposed update that changes no physical ignition/duration/slope is an
`unrepresentable-update` stop. No changed epoch, target refit or hidden precision
default is used to manufacture closure.

The private corrector follows exactly four central-probe iterations, fixed
residual/control scales, NumPy least squares/rcond/rank/condition gates, one
infinity-norm cap and the prescribed four damping fractions. Preflight the
complete central stencil before native probes, recording all unavailable entries
if any member is infeasible; do not propagate half a derivative or change h.
Finite probes are not eligible commands, even if one closes. Every trial is
relative to the same accepted parent; analytic infeasibility consumes its proposal
slot but no native work. Nonfinite data, native failures and guards stop the
entire study. No fallback solve, retry or new seed is introduced.

First nominal closure triggers one frozen tighter repeat. Qualify locally only
if both norms close and the endpoint agreement/mass/coast checks pass. A failed
tighter repeat cannot resume iteration or become nominal-only success. Exhaustion
retains the last accepted command as `not-converged`, without a tighter run.

Use a separate 65-proposal / 66-evaluation / 132-launch budget, sharing one
300-second clock from before binding/preparation. Count evaluations and native
attempts before entry; prevent retries after an incomplete arc. Check deadlines
in native callbacks and after returned outputs. Preserve completed cutoff data
if coast fails. Diagnostics retain proposal IDs/parents, command units/epochs,
residuals, profiles, matrices, solve/cap/prediction, fractions/acceptance arithmetic,
provenance and counters. Unavailable fields remain explicit; this code writes no
evidence files and never overwrites retained JSON.

## Consequences and revisit conditions

The D14 default callback and four-arc path remain compatible. The new model is
`local-moon-point-mass-steered-burn-v1`, not the full-force mission model.
Local success would not establish Mars capture, hardware slew authority, global
optimality or continuous collision safety. Earth/Sun, harmonics, SRP, relativity
and outer matching remain absent. The clock is cooperative, not a way to preempt
a blocked native call. Strict M3/task 3.9 remain open; automation remains paused.

After implementation verification, D15.3 may execute exactly one separately
authorized retained-reference study. Its measured rank, response, closure and
runtime decide the next action; synthetic convergence is not permission to
expand the schedule or promise real-branch controllability.

## Evidence and verification

[Tests](../../tests/test_local_targeting.py) add independent orthonormal-basis,
chart/rate, Rodrigues rotation, Decimal mass/reserve, fixed-epoch and synthetic
linear/quadratic derivative/solve oracles. Cover exact rank/condition/decrease
thresholds, replay/binding mismatch, domain edges/empty intersections, sub-ULP
ignition/update behavior, common-parent ordering, skipped trials, closed probes,
zero/nonfinite prediction, no-step/iteration-cap outcomes, frozen tighter
success/failure, partial evidence, guards, clocks and counters. A synthetic
worst-case four-iteration schedule uses exactly 65 proposals/130 arcs without
closure; budget checks permit only one final repeat up to 66/132.

Native synthetic qualification integrates a 200-second smooth variable-mass burn
and 800-second coast against independent 128-point Gaussian acceleration/time-
weighted integrals, within 0.001 m / 1e-6 m/s / 1e-6 kg for both unchanged profiles.
Zero steering is bitwise equal to the D14 native path for both profiles. Real
native stage tests reject impact, dry mass, invalid directions and expiry.
These are synthetic adapter checks, not propagation of the retained mission.

An initial deliberately fast 20-second steering test produced nominal velocity
error about 2.98e-6 m/s against the integral, exceeding that oracle's 1e-6 m/s
check. Per-step tolerances are not global-error guarantees. The retained domain
has duration >=2105.14 s; the final synthetic qualification uses a resolved
200-second schedule. No integrator setting or numerical tolerance was loosened;
the frozen tighter gate remains mandatory for any eventual local success.

Final focused verification: 301 tests pass in 2.57 s, including 119 new D15 tests,
D13/D14 and research propagation regressions. Full regression: 4,231 tests pass
in 602.73 s. Ruff, strict OpenSpec, local links, diff checks and unchanged
legacy/0104/0107 SHA256 checks pass. D15.2 is complete; D15.3 remains unchecked.
An intermediate full run was deliberately interrupted after the epoch-resolution
fix; the successful replacement full run tested the final runtime/test files.
Subsequent edits only record verification in documentation; no retained-reference
targeting study, strict M3 qualification or automation restart occurred.
