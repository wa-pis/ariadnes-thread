# 0112 — Implement bound-aware local targeting

Date: 2026-10-16
Decision status: accepted
Implementation: complete; focused/native and full regression verification pass.
Scope / milestone: M3 research D16.2 only; no D16.3 retained-reference execution.
Base revision: `065f3efabdbc13937dcdbe7632dd28e0f28a24ba`, clean before this stage; this commit introduces the runtime, tests and explicit dependency pin.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [0111](0111-bound-aware-local-targeting.md), preserving D14/D15 and immutable evidence.

## Context and constraints

D15 reduced the error but did not close the fixed local boundary conditions.
Its unconstrained corrections requested unavailable ignition/duration values.
Implement the separately approved bound-aware attempt, without changing thrust,
fuel reserve, steering chart, target state/epoch, integration settings or force
model. Synthetic convergence tests implementation behavior, not the real branch's
reachability, global optimality, mission feasibility or continuous safety.

## Options considered

- Modify D15 or duplicate its native propagator: rejected; historical behavior
  and evidence must remain reproducible, and no second physical implementation
  is needed.
- Introduce a private D16 orchestration module reusing D15's physical domain,
  endpoint/guidance helpers and native evaluator: selected. Only the solver,
  stencil orchestration, evidence and separately bounded counters are new.

## Decision and rationale

[bounded_local_targeting.py](../../src/space_nav/bounded_local_targeting.py)
binds all three pinned 0104/0107/0110 inputs before work, reconstructs the domain
and retained command/residual/mass evidence, and explicitly selects accepted
0110 proposal 52. The original command constructor remains authoritative.
Check that the complete timing box permits at least one second of coast and
that all timing corners pass the existing window/mass checks. An unsupported
coupled box stops rather than being clipped or silently repaired.

Use installed Conda SciPy 1.17.1, now explicit in
[environment.yml](../../environment.yml); no installation or dependency upgrade
was required. Python 3.12.14, NumPy 1.26.4 and TudatPy 1.0.0 remain unchanged.
TRF/exact/linear uses the frozen tolerances, physical-to-solver transformation
and fixed residual scales of 0111. No dynamic scaling, penalty residual, second
seed, solver fallback or uniform D15 step cap is introduced.

For each Jacobian preflight all twelve fixed-step probes, preferring central,
then second-order forward, then backward pairs. Reuse the completed center;
differentiate scaled residuals and multiply columns by the physical control
scales. Retain matrices, stencils, raw endpoints and SVD diagnostics. Rank loss
is diagnostic, not a physical impossibility test or an automatic success.

The first objective request reuses the exact replay once; subsequent identical
requests still propagate afresh. SciPy may move an initial point off a bound:
reject any altered initial request instead of silently changing the warm start.
Raise a dedicated completion signal from the objective on first physical
closure, before SciPy can request another Jacobian. A closed probe is never
eligible. Repeat exactly that command once with the original tighter profile;
require both norm gates and endpoint/mass agreement. No correction resumes after
a tighter failure. Optimizer termination without physical closure remains
stationary-unclosed or stagnated-unclosed, never local-qualified.

A separate shared 300-second clock begins before binding. Count all objective
requests, Jacobian attempts/completions, evaluations and attempted/completed
native arcs independently of SciPy. Respect 40 requests, 20 twelve-probe batches,
280 nominal evaluations and one reserved tighter evaluation: 281 total / 562
launches. Reject an unaffordable batch before its first probe. Native callback
exceptions are wrapped by the existing boundary; keep the budget stop reason
separately so deadline exhaustion is not misclassified as a generic native error.
No continuation follows an incomplete arc; a completed cutoff survives coast
failure. Preserve best eligible objectives separately from accepted optimizer
iterates and probes. The runner returns finite evidence but writes no files.

Adding an explicit dependency changes the environment file's bytes, not the
previous harmonic experiment. Preserve its original bytes in
[m3_fresh_harmonic_environment.yml](../../tests/data/m3_fresh_harmonic_environment.yml)
and keep all historical JSON/hashes unchanged. Its replay test validates that
archived environment; the environment test separately requires that today's
file differs only by the approved SciPy pin and verifies installed versions.
The fresh native replay still reports today's environment hash and compares all
scientific fields exactly against the immutable snapshot; it separately verifies
the historical hash rather than relabelling the old experiment.
This is explicit compatibility accounting, not a fabricated fresh native run.

## Consequences and revisit conditions

D14/D15 source, controls, profiles and budgets remain unchanged. No public API,
CLI, UI or full-force trajectory changes. The clock remains cooperative and
cannot preempt a blocked native call. Earth/Sun, harmonics, SRP, relativity,
Mars capture and hardware slew/continuous-safety qualification remain absent.
Strict M3/task 3.9 stays open; automation remains paused.

D16.3 needs a separate user instruction for exactly one retained-reference
study. Only that evidence can show whether this attempt closes the real local
target. Do not expand bounds, alter fuel/epoch, add nodes or automatically retry
on an unclosed or failed result.

## Evidence and verification

[D16 tests](../../tests/test_bounded_local_targeting.py) use independent linear,
quadratic and nonsymmetric coupled roots with real installed SciPy; second-order
analytic derivatives cover all three stencils, units and common-parent commands.
They test bound-active unattainable targets, rank-zero stationarity, exact replay,
single initial cache, adjusted-seed rejection, early closure, closed probes,
separate objective/iterate evidence, status semantics, counters, preflight,
late/failed outputs and frozen tighter repeats. Actual synthetic native adapter
parity and callback-deadline tests reuse the original TudatPy path, not the
retained Moon-to-Mars reference.

Unchanged D15/D14 tests retain the independent rotation/chart/Decimal mass/time
and 128-point Gaussian acceleration-integral oracles for both native profiles
(0.001 m / 1e-6 m/s / 1e-6 kg). D16 reuses those calculations rather than
reimplementing them. Pure binding tests check retained hashes, every saved
command/residual/mass and the 1756.635988 s full-box coast margin without
propagating the reference.

Final verification: 98 new D16 tests; 366 focused/native/environment/regression
tests pass in 3.16 s. Full regression: 4,330 tests pass in 604.70 s using
`conda run --no-capture-output -n space-nav python -m pytest -q`.
Ruff, strict OpenSpec, local links, whitespace, six preserved D15 source hashes
and immutable legacy/0104/0107/0110/0111/historical-environment checks pass.
Conda reports SciPy 1.17.1 build `py312h4519d97_1` from conda-forge/osx-arm64;
Python/NumPy/TudatPy/resource/SPICE pins remain unchanged. All old experiment
JSON and D14/D15 runtime files remain byte-for-byte unchanged.
D16.2 is complete. D16.3 is not executed by these tests and remains unchecked;
no real-branch convergence, strict M3 completion or automation restart is claimed.
An intermediate full run was deliberately interrupted after 2,628 passing tests
to update the second environment-hash comparison; the replacement full run uses
all final runtime/test files. No historical JSON or scientific tolerance changed.
