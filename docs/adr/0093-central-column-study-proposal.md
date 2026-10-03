# 0093 — Propose a bounded central-column sensitivity study

Date: 2026-10-04
Decision status: proposed (D10 scope; requires approval before implementation).
Implementation: not started; specification and documentation verified separately.
Scope / milestone: M3 research D10; no propagation in this stage.
Base revision: `022cd79c13265fd09fc339aacc59e459d0af99ca`, clean before planning.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [0092](0092-local-response-disagrees-with-jacobian.md).

## Context and constraints

D9 measured central directional slopes that differ from D7's forward-difference
prediction by 0.303–0.312 of its norm. Differences between the two tested scales
and integration profiles are much smaller. ADR 0089 also observes cancellation
by approximately 219 among individual column contributions. Neither observation
identifies the cause or establishes a trustworthy derivative.

The next question is narrowly defined: does replacing the six forward columns
with central columns at the same probe increments reproduce D9's nominal
directional response? Keep the seed, target, model, integrations and numerical
gates unchanged. No new correction solve, trial selection or operational API.

## Options considered

- Repeat directional damping: rejected for this step; it does not identify
  contributions to the inaccurate local prediction.
- Recompute all columns at two scales and both profiles: deferred; 50 evaluations
  would increase cost without first testing the forward-versus-central hypothesis.
- Central columns at the original increments, nominal profile only: proposed;
  thirteen evaluations give an independent full matrix and allow comparison
  with already retained nominal D9 slopes, with a bounded compute budget.

## Decision and rationale

Propose one baseline followed by +h_i and -h_i for each of six controls, in
departure then arrival azimuth/elevation/duration order. Use original
h=(1e-5 rad,1e-5 rad,1 s) repeated twice. Each command is independently formed
from the seed and gets a fresh matched environment. This is thirteen controls,
thirteen three-arc evaluations and at most thirty-nine native launches under
one cooperative 300-second clock. No tighter runs or automatic second study.
The deadline is a cap, not a promise that this study will finish on this machine.

Bind immutable 0079, 0086 and 0092 hashes and their scenario/candidate/runtime,
resource/settings/target/seed identity. Require a nominal baseline replay and
positive-probe replay against the corresponding retained D7 runs. Replay uses
the existing 10 m / 0.0001 m/s / 0.000001 kg boundary thresholds, not new tolerances.
Any replay mismatch or existing analytic/native/event/deadline failure stops.

Use the existing dimensionless residual and trust scales. For each column:
C_i=(r(+h_i)-r(-h_i))*T_i/(2*h_i),
F_i=(r(+h_i)-r(0))*T_i/h_i, and
E_i=((r(+h_i)-r(0))+(r(-h_i)-r(0)))*T_i/(2*h_i).
Here C_i names a Jacobian column, not D9's curvature statistic.
F_i-C_i=E_i is an arithmetic identity, not proof of a quadratic physical model.
Report signed columns and contributions E_i*z_i, z=retained_step/T, so their
sum explains the measured forward-versus-central directional difference.
Also retain column changes from the historical matrix and cancellation metrics.

Compare g_c=sum(C_i*z_i) with both retained D9 nominal slopes, dividing each
discrepancy norm by G=norm(g_D7)>0. Both <=0.10 checks are required for nominal
directional consistency at these increments. Keep D9's fixed normalization
instead of choosing a favorable denominator from the new matrix. Zero g_c is
recorded, not divided by or used to select a maneuver. No rank/least-squares
solve is needed. Nonfinite derived values stop; unavailable ratios use null
and a contextual reason rather than nonfinite JSON.

## Consequences and revisit conditions

This is a proposed diagnostic, not a repair or accepted new targeting model.
A pass would support central directional consistency only at the sampled seed,
increments and nominal profile. It would not validate every column, cross-profile
derivatives, convergence, absolute accuracy, safety or strict M3 completion.
Failure or timeout is retained without another scale, larger budget or retry.
Implementation and the single live study remain separate tasks after approval.
Reuse existing preparation, command gates and composer; add no dependencies.
UI, production physics, historical artifacts and paused automation are unchanged.

## Evidence and verification

This proposal uses retained D7 and D9 only. D9 evidence SHA256 is
`164760a35451b3e8cf43bf2213e8466a331dbcb85004249e134e9daefa1a7374`.
The original probe/trust increments are confirmed in `research_correction.py`.
Strict OpenSpec, local links, diff and immutable legacy checksum checks pass.
The three pinned artifact hashes also pass. An independent synthetic quadratic
calculation verifies central columns, known even bias and both forward/central
identities within 1e-10 absolute scaled units; this checks the written formulas,
not an unimplemented native driver or physical derivatives.
No runtime code changed, no native experiment ran and runtime tests were not
rerun. D10 implementation must verify independent linear/quadratic column
oracles, the forward/central identity, cancellation and threshold edge cases,
reference/replay failure paths, ordering, shared counters/deadline and unchanged
D4–D9 behavior, followed by the full suite before a live study.
