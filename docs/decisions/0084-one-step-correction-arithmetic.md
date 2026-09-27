# 0084 — Test correction arithmetic before native targeting

Date: 2026-09-28. Base revision: `3c632cd` plus D7.1 implementation and tests.
Scope: pure six-control arithmetic; no new native mission experiment.

## Decision

Implement the D7 formulas in a private module, reusing the existing finite-value
and burn-control validators and installed NumPy. Do not add an optimizer library,
change production propagation, or attach the arithmetic to the research runner
before D7.2 implements its separate budget and failure lifecycle.

The input is six signed SI terminal residual components and six ordered probe
residuals. Scale position by 1000 m and velocity by 0.01 m/s. Forward increments
are (1e-5 rad, 1e-5 rad, 1 s) for each burn; trust scales are
(0.25 rad, 0.25 rad, 600 s). Preserve probe-major raw SI residual changes and
residual-row/control-column scaled Jacobian for later evidence. Solve using
NumPy least squares with rcond=1e-12, retaining rank and singular values.
Rank deficiency produces no command step. Invalid/nonfinite inputs, arithmetic
overflow or a failed solve raise rather than generating a fallback command.

Cap the scaled step to unit infinity norm. The existing control gate validates
the seed and updated command, including azimuth wrapping, elevation, positive
burn/coast duration and analytic propellant bounds. This is not sampled or
continuous safety evidence: native guards remain the future composer's job.

Report closure (1000 m and 0.01 m/s) separately from scaled-score improvement.
A lower score can accompany a larger position miss. Zero or nonfinite score
ratios have an explicit unavailable reason; no NaN/Infinity is serialized.
No public API, integrator, model, tolerance, UI or dependency change.

## Evidence and limits

44 focused tests pass in 0.09 s, including existing control regressions. A coupled,
column-permuted triangular linear fixture has a prescribed exact solution,
independent of another least-squares computation. Both an uncapped and a capped
update match within 2e-6 in each command component (rad or s); the dimensionless
Jacobian matches within 2e-9. Additional checks exercise rank cutoff, zero rank,
nonfinite solver output, overflow, command gates and closure/improvement edges.
These are arithmetic tests, not measured trajectory sensitivities or accuracy.

Full suite: 3,670 passed in 590.78 s. During the run, the oracle assertions were
made strictly absolute (relative tolerance zero); the final 44-test focused run
also passes those stricter checks. Runtime code was unchanged during the run.
Ruff, strict OpenSpec, whitespace and unchanged legacy SHA-256 pass.
D7.1 is complete; D7.2 orchestration and D7.3's single bounded live experiment
remain unimplemented. Strict M3/task 3.9 remain open.
