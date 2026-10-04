# 0099 — Test two fractions of the retained central correction

Date: 2026-10-04
Decision status: accepted (user approved the bounded D12 experiment).
Implementation: specification complete; runtime implementation and study pending.
Scope / milestone: M3 research D12, not production targeting.
Base revision: `00a5802561d098e58f612455afa1a7ffd6c7d962`, pushed to origin/dev.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [0098](0098-central-correction-does-not-improve.md).

## Context and constraints

D11's full central-matrix step worsened the measured score by 23.46%, despite
a predicted 0.85% decrease. D8's unsuccessful fractions used a different,
forward-matrix direction; they do not measure this central direction's fractions.
The bounded question is whether either half or quarter of D11's retained step
improves the original seed. No success or local validity is assumed.

## Options considered

- Recompute derivatives or introduce iteration: deferred; changes the question
  and expands scope before two explicit smaller steps have been measured.
- Stop targeting research: valid if these trials also fail; preserve negative
  evidence rather than automatically creating an endless damping ladder.
- Reuse the existing damping schedule with the central step: selected; only two
  fractions, no new solve, unchanged dynamics and scientific gates.

## Decision and rationale

Bind pinned 0079 and 0098. The latter SHA256 is
`b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057`;
0079 is `17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235`.
Verify scenario, candidate, seed, fixed target, runtime/resources/settings,
0079/0095 historical identities, completed baseline and alpha=1 trial,
not-improving outcome, no selected/tighter run and finite rank-six correction.
Reconstruct their raw residuals and improvement, validate the retained 6x6
matrix and capped-step/trust-unit/prediction consistency algebraically, without
calling a solver or launching derivative probes. Imported source hashes remain
historical; current source hashes are separate.

Replay a fresh nominal baseline against 0079 and 0098, all four identical
epochs/frames and masses within 10 m / 0.0001 m/s / 0.000001 kg. Mismatch stops
before fractions. If both 1000 m and 0.01 m/s closure gates already pass, report
baseline-closed and skip both. Otherwise try seed+0.5*dx and, only after a
completed non-improving half step, seed+0.25*dx. Neither command is chained from
the preceding trial. Use canonical angles, time/window/mass gates, fixed target,
unchanged nominal settings and fresh native environments.

Reuse sufficient decrease S_trial <= S_base*(1-1e-4*alpha), or both closure gates.
Record each threshold, raw/scaled residuals, physical misses, score ratio and
optional r_base+alpha*J*(dx/T) prediction; predictions cannot select commands.
The first empirical improvement selects exactly one frozen canonical-command
tighter repeat with the same initial/target states. Skip remaining fractions.
Compare all four boundaries at the existing gates. Disagreement or failure
retains nominal improvement separately and never resumes the fraction schedule.

One cooperative 300-second clock covers verification through reporting: at most
3 controls, 4 evaluations, 12 native launches. Count nominal commands before
analytic validation; frozen tighter evaluation adds no control attempt. Any
replay/analytic/event/native/nonfinite/deadline failure stops immediately.
Preserve finite exclusive-output evidence, completed diagnostics, explicit
skipped/unavailable reasons and counters; no unfinished endpoints, retry,
extra fractions, re-probes, new solve or automatic budget expansion.

## Consequences and revisit conditions

Reuse existing damping gates/composer rather than duplicate dynamics or add an
optimizer framework/dependency. Existing D4–D11 behavior must remain unchanged.
This only enables a research test; improvement is not closure, numerical
accuracy, continuous safety or strict M3 qualification. Task 3.9 stays open,
UI unchanged and automation paused. If neither fraction improves, stop and
review the approach; this contract authorizes no automatic further experiment.

## Evidence and verification

The question is based on immutable D11 evidence, not a new native observation.
This specification stage checks pinned hashes, local links, strict OpenSpec,
diff and unchanged legacy checksum; no runtime tests or native study are run.
D12.2 requires independent seed/fraction/threshold/prediction oracles, retained
algebra validation, replay/resource/closed/failure cases, both selection branches,
frozen tighter/no-fallback behavior, 3/4/12 counters, shared deadline, exclusive
finite output and unchanged D4–D11 regressions. Complete the full suite before
D12.3's single native study and independently verify its evidence afterward.
