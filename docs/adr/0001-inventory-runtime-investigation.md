# 0001 — Investigate the inventory deadline before optimization

Date: 2026-09-13

Milestone: M3, `refine-physical-trajectory`, task 3.9.

Status: accepted investigative direction; optimization not implemented or validated.

## Question and constraints

The existing native inventory test reaches its shared 300 s deadline during
verification of the new midpoint error bound. What should be investigated without
weakening the scientific contract?

Keep the deadline, native controls, force models, kernels and numerical tolerances
unchanged. This is ground-based engineering verification, not flight qualification.
See the [roadmap](../../openspec/ROADMAP.md) and
[active tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).

## Evidence and provenance

Measured base: `fd4dafd973d81a0c773112145d8da4ff3b16675d`.
Environment: the base revision's [environment.yml](../../environment.yml),
Conda `space-nav`, Python 3.12.14. Test data are synthetic diagnostic fixtures,
not operational spacecraft telemetry.

The working tree also contained uncommitted midpoint tests and a norm docstring
clarification. The native inventory test and production modules matched the base.
The full-suite counts below therefore describe that dirty tree, not a clean checkout
of the base. This documentation commit deliberately excludes the unfinished code;
the exact dirty test snapshot was not archived with these observations.

1. [Unprofiled full-suite observation](../../tests/data/m3_midpoint_suite_deadline_observation.json):
   2803 passed, one failed, 623.04 s overall. The native inventory reached the
   300 s deadline after 12 arcs. Separately, 712 focused controls passed in 0.43 s.
   Procedure: `conda run -n space-nav python -m pytest -q --tb=short --durations=5 -p no:cacheprovider`.
2. [Bounded profile](../../tests/data/m3_inventory_runtime_profile.json): one
   stdlib `cProfile.Profile` enabled immediately around `pytest.main` for
   `tests/test_trajectory_spk.py::test_loaded_spk_chain_coverage_contains_candidate_interval[native-readback]`,
   with `-q --tb=short --show-capture=no -p no:cacheprovider`. The unchanged
   deadline was reached after 8 arcs; pytest elapsed time was 300.93 s.
   The generic harmonic error function was called 12 times, recording 204.20 s
   inclusive profiler time. `math.gcd` recorded 141.67 s self time.

Only selected profiler statistics were retained, not a complete raw profile or
machine-load trace. Instrumentation includes pytest setup, adds overhead, and
changes how far the test gets. Inclusive times overlap; generator counts are
resumptions. Suspicious native-wrapper time attribution prevents treating these
numbers as an additive wall-time breakdown. They are not a speed benchmark.

## Interpretation

Observation: exact-rational harmonic verification is a substantial profiling
hotspot. Repeated calls occur in the inventory's control loops.

Hypothesis, not yet established: some calls have identical scientific inputs and
could safely reuse a result within one invocation. Call counts alone do not prove
duplicate inputs or any achievable speedup.

Mathematical condition: reuse of a deterministic pure calculation on exactly the
same validated inputs preserves its result. Applying that argument here still
requires proving that the key includes every dependency and that no mutable input
or external state is omitted. It does not establish physical correctness of the
underlying calculation or qualify a trajectory.

## Decision and alternatives

Measure exact duplicate inputs before implementing invocation-local reuse. Keep
the midpoint implementation incomplete until full verification passes.

- Do not increase the deadline or loosen tolerances to obtain a green run: that
  changes acceptance conditions without addressing the measured work.
- Do not retry solely for a pass: a passing timing sample would not resolve the
  observed deadline variability.
- Do not replace exact arithmetic with floating point: that needs a separate
  error argument and is not justified by this profile.
- Do not introduce a global cache or new dependency: reuse across invocations
  adds invalidation and provenance obligations unnecessary for this experiment.

## Next checks

1. WHEN keys include identical GM/radius plus byte-identical coefficient arrays,
   positions, rotation and observed terms (including array shape/dtype), THEN
   count exact duplicates within one inventory invocation. If none occur, reject
   this optimization and investigate another measured hotspot.
2. WHEN local reuse is implemented, THEN verify exact uncached-result parity,
   misses for changes to each dependency, preserved input validation and deadline
   checks, and no change in native control count. Keep cached values immutable or
   isolated from caller mutation.
3. WHEN evaluating performance, THEN record an unprofiled comparison with input
   provenance and unchanged limits; report observed time rather than a guarantee.
   Require focused checks, full pytest and strict OpenSpec validation before
   declaring implementation complete. Preserve any failed run.

No scientific constants, arithmetic allowances or trajectories changed in this
decision. M3 and task 3.9 remain open.
