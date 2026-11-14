# 0195 — Bracket the prospective 3,474.8 km lunar range marker

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted within [ADR0193](0193-design-lunar-range-extension.md).
- Implementation: R5.48 complete.
- Verification: one authorized real-ephemeris study and one independent offline audit passed.
- Scope: 50 s of unpowered model B from the archived R5.43 tighter RK4 endpoint for `d0001-t0035`.
- Measured revision: `b5ee65d1d1bba162790d52ec79fd9cb922438c9b`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-a-prospective-lunar-range-marker), [design result](../../openspec/changes/refine-physical-trajectory/design.md#r548-real-ephemeris-lunar-range-result-2026-11-14), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[ADR0190](0190-post-cutoff-coast-outbound-at-samples.md) ended below the
prospective 3,474,800 m marker. R5.48 starts all four profiles bit for
bit from its saved tighter RK4 six-state at 978998915.9635216 TDB s
since J2000, with mass metadata 1351.7475727997967 kg. It stops 50 s
later with the same Sun/Moon/Earth point-mass forces, pinned
ephemerides and zero thrust and mass flow. No archived arc, burn,
model A or optimizer was rerun.

## Options considered

- Use the saved archive alone: it does not reach this marker.
- Rerun the preceding coast or extend until a crossing is found:
  either changes the agreed experiment.
- Run the fixed continuation once and independently reconstruct the
  sampled brackets: selected by ADR0193.

## Decision and rationale

Accept `numerical_status=passed` and `marker-bracketed` for the
fixed model B extension. Relative to restart, the four common-grid
brackets are +30–35 s. The 1 s and 0.5 s RK4 meshes bracket the
marker at +30–31 s and +30.5–31 s, respectively. Their overlap is
+30.5–31 s (978998946.4635216–978998946.9635216 TDB s). All 196
audited sampled radial signs are positive, and no sampled equality
or inward pair was found. The Moon-centred range grows from
3,438.655 km to about 3,497.228 km in each profile.

| Comparison | Max position (m) | Gate (m) | Max velocity (m/s) | Gate (m/s) |
| --- | ---: | ---: | ---: | ---: |
| RK4 1 s vs. 0.5 s | 3.81470e-5 | 0.01 | 9.03518e-11 | 1e-5 |
| RK4 0.5 s vs. tighter DOP853 | 6.15101e-5 | 0.01 | 2.06445e-10 | 1e-5 |
| Normal vs. tighter DOP853 | 0 at stored precision | 0.001 | 1.22431e-10 | 1e-6 |

## Evidence and verification

- The study finished in 5.71041 s of 60 s. Two RK4 arcs and two DOP853
  solves completed with 500 RHS evaluations, 36 trials, 2,044 explicit
  adaptive state reads and 462 native guard reads. The 2,506 explicit
  reads exclude Tudat's internal lookups. Before/after runtime
  identities match. One pool setup, 30 inventory calls, zero new GMs.
- The isolated stdlib audit finished in 1.59324 s of 10 s. It verified
  all 33 numerical comparisons, 36 adaptive force/source observations,
  22 native telemetry rows, both guard histories and the direction
  arithmetic and signs for 44 common and 152 native-mesh rows. It used
  no scientific imports, native calls, kernel loads or propagation.
- The [manifest](experiments/0195/manifest.json), [study archive](experiments/0195/study.json.gz),
  [audit archive](experiments/0195/audit.json.gz) and parent receipts for
  [study](experiments/0195/study.parent-receipt.json) and
  [audit](experiments/0195/audit.parent-receipt.json) retain the original
  evidence and bind it to the preparation and measured revision. Both
  finalization gates, archive round trips and digest chains passed.
- Local links, evidence readback, source pins, diff and strict OpenSpec
  passed. The [R5.47](0194-prepare-lunar-range-extension.md) results
  (21 focused, 6,186 guarded passed, 494 skipped, and Ruff) apply to the
  unchanged implementation; the tests were not rerun for this result.

## Consequences and revisit conditions

The two authorized phases are consumed. This is an independently
audited numerical bracket within the shared model and the simulated
restart. No time was interpolated. An exact, first or unique physical
crossing, lunar escape, a physically valid handoff, continuous safety,
full-force mission accuracy and strict M3 remain unverified. Any
further live study needs a distinct question and a bounded contract.
