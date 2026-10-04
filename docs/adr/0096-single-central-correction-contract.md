# 0096 — Test one correction using retained central columns

Date: 2026-10-04
Decision status: accepted (bounded D11 contract following the user's continuation).
Implementation: specification complete; runtime implementation and live study pending.
Scope / milestone: M3 research D11; no solve or propagation in this planning stage.
Base revision: `fa62e7124576bd3c0c6b12d81ebaaadcfc65a2c5`, clean before planning.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [0095](0095-central-columns-match-local-response.md).

## Context and constraints

D10's central matrix reproduces two measured nominal slopes along the old D7
direction much better than forward differences. That observation does not
validate a different direction produced by solving with the central matrix.
The next question is whether one such correction improves a propagated endpoint.
Preserve the original seed, fixed target, model, settings and strict M3 gates.

## Options considered

- Begin iterative targeting or add a damping ladder: deferred; these expand
  scope before one new-direction trial has been measured.
- Repeat all derivative probes: deferred; retained D10 data is bound to the same
  seed/resources/settings and can be checked without new native probes.
- Replay the baseline, solve once, test once, then conditionally check tighter:
  selected; isolates the matrix change while reusing existing solve/cap semantics.

## Decision and rationale

Bind 0079 and completed 0095, whose SHA256 is
`8be4356f4c339eaad9ca30ce2f49786d7e65498ae731fc468d8810836a97fb55`.
Validate scenario, candidate, seed, target, runtime/resources/settings, historical
reference identities, thirteen completed nominal runs, six ordered finite central
columns and two passing <=0.10 D10 consistency checks. Reconstruct central
columns from retained raw endpoint residuals and the original probe/trust scales,
checking their recorded values, rather than accepting an unlabelled matrix.
Imported D10 source identity remains separate from current implementation hashes.

Replay one nominal baseline and compare all four boundaries/masses against
0079 and 0095 with identical epochs/frames and unchanged 10 m / 0.0001 m/s /
0.000001 kg gates. Any mismatch stops before a solve. If both closure gates
(1000 m and 0.01 m/s) already pass, report baseline-closed without solve or trial;
this is not strict M3 qualification.

Form J with residual rows and retained central-control columns. With the fresh
scaled residual r, solve J*z=-r once using NumPy least squares and rcond=1e-12.
Require finite values and rank six; rank loss stops with no fallback. As in D7,
cap z by max(1,norm_inf(z)), then multiply by T=(0.25 rad,0.25 rad,600 s) twice
to obtain physical dx. Record singular values, uncapped/capped vectors, divisor,
J*(dx/T), signed linear predictions and predicted score. Zero step or no strictly
lower predicted score stops before the trial with an explicit reason.

Try x_seed+dx once (alpha=1), through existing canonical command, window and
analytic propellant gates. Do not move the target or regenerate derivatives.
Evaluate in fresh matched nominal dynamics. Accept empirical improvement only
when S_trial <= S_baseline*(1-1e-4), or both unchanged closure gates pass. Retain
position and velocity misses, scaled scores/ratio, prediction-versus-observation
and the actual threshold separately. If not improving, stop without tighter.

Only an improving nominal trial receives one fresh tighter repeat with exactly
frozen canonical commands and initial/target states. Compare all four boundaries
using existing thresholds; failed/unavailable agreement remains distinct from
nominal improvement. No alternative command follows a tighter failure.

Use one cooperative 300-second clock from verification through reporting, at
most two control attempts, three evaluations and nine native launches. Count
each nominal command before analytic validation; the frozen tighter evaluation
does not add a control. Any analytic/native/event/nonfinite/deadline failure stops
the invocation, retaining completed diagnostics and no unfinished endpoint.
No retries, extra fractions, re-probes, second solve or automatic budget increase.

## Consequences and revisit conditions

This is a single research update, not production targeting or a validated new
Jacobian. A negative trial is useful evidence; linear agreement need not persist
at the full capped step. Improvement does not imply endpoint closure, numerical
accuracy or continuous safety. Strict M3/task 3.9 stay open, the UI and paused
automation remain unchanged. Agree any further targeting/damping work only
after this one study's evidence. Reuse existing gates/composer and matrix-solve
arithmetic where possible, without new dependencies or an optimizer framework.

## Evidence and verification

The contract uses D10's retained diagnostic, not a new native observation.
Pinned 0079/0095 and immutable legacy hashes, strict OpenSpec, local links and
diff checks pass. Independent synthetic full-rank algebra verifies solve sign,
column order, trust-unit conversion, cap and predicted decrease. Runtime code
and tests were not changed or rerun in this documentation stage.
D11.2 must verify independent linear oracles, rank/zero/nonfinite cases, cap,
predicted-decrease guard, unchanged improvement/closure gates, replay/resource/
matrix mismatches, counters/deadlines, selection/tighter/abort paths and D4–D10
regressions, then run the full suite before D11.3's single native study.
