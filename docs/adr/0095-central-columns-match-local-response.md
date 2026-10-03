# 0095 — Retain central directional consistency without selecting a correction

Date: 2026-10-04
Decision status: accepted (retain diagnostic result, not a production Jacobian).
Implementation / verification: D10.3 complete; both nominal consistency checks pass.
Scope / milestone: one M3 research central-column study; evidence and documentation only.
Measured revision: `812ebebe2d0157538794d2ea8609b2cb797b789e`, clean before execution.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; completes [0093](0093-central-column-study-proposal.md) and [0094](0094-central-column-implementation.md).

## Context and constraints

D9's measured local directional slopes disagreed with the retained forward
Jacobian by 0.303–0.312 of its predicted directional norm. D10 asks whether
central columns at the original D7 increments reproduce the already retained
nominal response. Preserve seed, target, physics, settings and scientific gates;
do not solve a new correction or select any of the thirteen diagnostic commands.

## Options considered

- Promote the new matrix directly to production targeting: rejected; a test
  of one direction at one seed/profile does not validate every matrix column.
- Run more increments/profiles immediately: deferred; the approved single
  study is complete, and further work requires a new bounded scope.
- Preserve the measured improvement and its limitations: selected; it gives
  evidence for a better local prediction without claiming mission qualification.

## Decision and rationale

Retain [the complete finite JSON](experiments/0095-central-column-study.json).
One invocation completed **13 controls, 13 nominal evaluations and 39 native
arcs in 27.934500875 s**, below the shared 300-second cap. All four boundaries
and masses replay exactly against three nominal baselines and all six retained
positive probes. There were no tighter runs, retries, new solve or selected alpha.

Both central-direction consistency criteria pass at the unchanged <=0.10
threshold. The denominator is the fixed retained D7 directional norm
G = 1412401.0993820347, not the new central norm or physical endpoint position.
Thus the percentages below concern this scaled diagnostic, not mission accuracy.

| Retained D9 nominal slope | Forward prediction discrepancy / G | Central prediction discrepancy / G |
|---|---:|---:|
| alpha=2^-14 | 0.3102191512 | 0.0057254112 |
| alpha=2^-15 | 0.3027503512 | 0.0135842344 |

The central prediction norm is 1175785.5184939296. The recomputed forward
columns and directional sum reproduce the historical ones exactly. The
forward-minus-central directional difference is explained algebraically by
the summed even-column contributions, whose norm is 446036.4803523545,
or 0.3158001509*G. It is not a validated physical derivative error estimate.
The largest individual even contribution comes from departure burn duration:

| Control | Even directional contribution norm (dimensionless scaled residual) |
|---|---:|
| Departure azimuth | 1837.651718 |
| Departure elevation | 25274.564411 |
| Departure duration | 465191.443843 |
| Arrival azimuth | 0.117635 |
| Arrival elevation | 0.053521 |
| Arrival duration | 0.733181 |

These are contribution norms, not additive percentages; signed vectors in the
artifact show their cancellation. Sum-of-central-contribution norms divided
by central-direction norm is still **264.017827**, versus forward 219.452451.
The maximum absolute directional identity defect is approximately 7.4e-9
scaled units, consistent with floating-point arithmetic in the recorded sums.

The evidence supports the central construction for this nominal local direction
at these increments. It is consistent with important forward-difference bias,
particularly in departure duration. The even terms also contain numerical
effects; this single-profile study does not uniquely isolate a physical cause,
prove column-wise accuracy, or validate a new corrective maneuver.

## Consequences and revisit conditions

D10 is complete as a bounded diagnostic. Keep the matrix as research evidence,
not an automatically accepted production sensitivity model. The large target
miss remains: no new optimized trajectory has been computed in this stage.
Strict M3, task 3.9 and continuous safety remain unresolved; UI and paused
automation are unchanged. A possible next question is whether one explicitly
bounded correction using this matrix improves a propagated endpoint; agree its
rank, trust/damping, replay, stop and verification contract before implementing
or launching it. Do not automatically repeat D10 or start that next experiment.

## Evidence and verification

Invocation in the pinned Conda environment from the repository root:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment \
  examples/m3_feasible_mission.toml \
  docs/adr/experiments/0079-research-reference.json \
  docs/adr/experiments/0095-central-column-study.json \
  --column-references docs/adr/experiments/0086-targeting-study.json \
  docs/adr/experiments/0092-local-response-study.json
```

Exit code 0 records experiment completion; diagnostic consistency is separately
true. Evidence SHA256:
`8be4356f4c339eaad9ca30ce2f49786d7e65498ae731fc468d8810836a97fb55`.
TudatPy emitted its existing mass-rate API deprecation warning; no dependency
or runtime setting was changed in response.

Independent inline verification with JSON/hashlib/NumPy/math, without importing
D10 implementation, checks finite serialization, all three pinned references,
every current source hash, both historical source maps, scenario/candidate/
runtime/resources, thirteen independent commands, profile/settings/fixed target,
raw SI and scaled residuals and scores, exact three baseline and six positive
boundary/mass replays, six central/forward/even columns, historical differences,
contributions, column/directional identities, compensated sums and cancellation,
both fixed-denominator threshold checks, 13/13/39 counters, elapsed budget and
absence of solve/selection/retry. Vector formulas reproduce the recorded values
exactly; independent NumPy multiplication verifies retained g within 1e-7
absolute scaled units. Prior evidence and legacy SHA256 are unchanged.

72 focused D10 tests pass. Ruff, strict OpenSpec, documentation links and diff
checks pass. No runtime code changed after D10.2, so this evidence-only stage
reuses its 3,856 passing full-suite tests in 578.59 s instead of rerunning them.
None of these checks certifies absolute physical accuracy or strict M3 readiness.
