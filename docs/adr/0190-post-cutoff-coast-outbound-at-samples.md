# 0190 — The post-cutoff coast passes checks and is outbound at samples

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted within the [ADR0188](0188-design-post-cutoff-lunar-coast.md) contract.
- Implementation: R5.43 complete.
- Verification: one real-ephemeris study and one independent offline audit passed.
- Scope: 600 s of unpowered model B after the archived simulated cutoff for `d0001-t0035`.
- Measured revision: `ba06f72fb1bbcb38434daf413a1291e6053a3d11`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-the-fixed-post-cutoff-lunar-coast),
  [design result](../../openspec/changes/refine-physical-trajectory/design.md#r543-real-ephemeris-post-cutoff-result-2026-11-14) and
  [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

R5.40 checks a 600 s parking coast. R5.43 instead starts from the
exact simulated nominal departure cutoff saved by ADR0079 and
ADR0098, at TDB s `978998315.9635216`, with constant mass metadata
`1351.7475727997967 kg`. The end epoch is `978998915.9635216` TDB s.
The engine stays off. The retained kernels supply geometric SSB/J2000
states, with no aberration correction. The only accelerations are
point-mass gravity from the Sun, Moon and Earth. There is no burn
replay, model A run, change to the boundary or new GM acquisition.

## Options considered

- Match the old B parking prefix: it starts at a different state
  and cannot check the motion after cutoff.
- Compare independent integrators from the shared cutoff and audit
  their sampled Moon-relative motion: selected by ADR0188. This
  separates a numerical disagreement from an inward model prediction.

## Decision and rationale

Accept sampled numerical agreement and the independent direction
classification `outbound-at-samples` for this interval. Two Tudat RK4
profiles (1.0 s and 0.5 s) and two SciPy DOP853 profiles (normal and
tighter) reached the 13 common nodes spaced 50 s apart. All 39
comparisons passed with the original gates.

| Comparison | Maximum position difference (m) | Gate (m) | Maximum velocity difference (m/s) | Gate (m/s) |
| --- | ---: | ---: | ---: | ---: |
| RK4 1 s vs. 0.5 s | 1.46556e-4 | 0.01 | 4.31753e-9 | 1e-5 |
| RK4 0.5 s vs. tighter DOP853 | 2.20330e-4 | 0.01 | 1.44933e-8 | 1e-5 |
| Normal vs. tighter DOP853 | 0 (rounded) | 0.001 | 7.80928e-10 | 1e-6 |

The largest cross-integrator differences occur at +600 s. Across
the 52 profile/node observations the Moon-relative radial speed
is positive, from +978.495 to +1167.059 m/s. Distance to the lunar
centre increases from 2,785.828 km to about 3,438.655 km in each
profile, a gain of about 652.827 km. The four net range signs
are positive. The study intentionally leaves the authoritative
outward status unavailable; the independent audit assigns it.

## Evidence and verification

- The study finished in 9.05254 s of its 60 s limit. It completed two
  native arcs and two adaptive solves, 5,412 native guard reads,
  4,496 adaptive RHS evaluations, 368 trials and 18,036 explicit
  adaptive state requests. The before/after runtime identities match.
- The audit finished in 5.72483 s of its 10 s limit. It reproduced
  39 numerical comparisons, 52 adaptive force/source observations,
  26 native telemetry rows, 52 direction rows and four net signs.
  It made zero native calls, kernel loads or spacecraft propagations
  and imported no scientific packages.
- The [manifest](experiments/0190/manifest.json) records the exact
  cutoff state, timings, comparison summaries and file hashes. The
  [study](experiments/0190/study.json.gz) and [audit](experiments/0190/audit.json.gz)
  are lossless archives of the original reports. The
  [study parent receipt](experiments/0190/study.parent-receipt.json)
  and [audit parent receipt](experiments/0190/audit.parent-receipt.json)
  bind both child receipts, the attempt markers and reports to the
  measured revision and preparation digest. Both finalization gates passed.
- Archive round trips, receipt chains, frozen input/source pins,
  local links, the diff and strict OpenSpec validation passed. The
  [R5.42](0189-prepare-post-cutoff-lunar-coast.md) results (52 focused,
  6,141 guarded regression tests passed, 494 skipped, and Ruff) apply
  to the unchanged code and were not rerun for this evidence commit.

## Consequences and revisit conditions

The one study and one audit authorized for R5.43 are consumed. The
integrators share the force model and source data; their agreement
establishes numerical consistency at the sampled epochs. Positive
radial motion at the samples is evidence of local departure in B.
Continuous outward motion, a finite-radius handoff, lunar escape,
cutoff accuracy, full-force mission accuracy and continuous safety
remain unverified. A future handoff study must name its event, force
model and independent check before any additional live run.
