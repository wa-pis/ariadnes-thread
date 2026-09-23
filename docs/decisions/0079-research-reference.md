# 0079 — Fixed-seed research mission completes but fails agreement

Date: 2026-09-24. Status: accepted diagnostic evidence, not mission qualification.
Scope: D4.4 only. Base revision: `2aca9f6`, with the new experiment entrypoint
and tests uncommitted during the measurement. Exact Python source hashes and
scenario hash are retained in the [JSON evidence](experiments/0079-research-reference.json).

## Question and procedure

Can one fixed analytic seed complete the real full-force three-arc composition
and its tighter replay within the original 300-second budget, and do they agree?
Run once, without retries, optimizer, changed tolerances or simplified forces:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.research_experiment examples/m3_feasible_mission.toml docs/decisions/experiments/0079-research-reference.json
```

The entrypoint refuses an existing output; a separately authorized reproduction
must use a new filename. It searches the supplied scenario afresh and selects
`d0001-t0035` only if it is on that search's Pareto front. No cached candidate
values are imported. The shared clock starts before that search and covers
resource preparation and both profiles; the deadline is cooperative, not a hard
native-call interrupt. Boundary/seed construction uses the loaded harmonic GMs.
The report records normalized inputs, pinned resource/model metadata, commands,
integrators, guard coverage, counters and source identity. No production CLI or
UI integration was added.

## Observations

- One experiment, six attempted and six completed arcs, zero automatic retries.
- Measured elapsed budget time: 20.101860458 s; serialization is excluded.
- Both profiles completed. Numerical agreement is **false**; exit code 1 is the
  intended disagreement signal, not an uncaught exception.
- Departure-cutoff differences: 0.012750901 m and 0.000008625916 m/s.
- Arrival-ignition differences: 1751.032853 m and 0.000313457666 m/s.
- Arrival-cutoff differences: 1751.286621 m and 0.000321787419 m/s.
- Maximum mass difference: 8.162715e-11 kg. Position/velocity exceed the unchanged
  10 m / 0.0001 m/s gates; mass passes the 0.000001 kg gate.
- Nominal terminal miss: 197851062193.609 m; velocity residual 31160.146688 m/s.
  Tighter miss: 197851060706.146 m; velocity residual 31160.146389 m/s.
- Nominal/tighter checked-state counts: 971 / 8555, including repeated evaluations.
- Native runtime emitted a deprecation warning for the existing custom mass-rate
  adapter; this experiment did not change that adapter.

## Interpretation and decision

This demonstrates bounded execution and honest disagreement reporting, not a
Moon-to-Mars solution. The analytic impulsive seed does not close the finite-burn
target. Its miss is about 198 million km. Neither numerical agreement nor real
accuracy may be inferred from integration completion. The comparison discrepancy
needs a separate bounded diagnosis; no cause is established by this experiment.
No detected sampled collision does not exclude between-check impacts, small
bodies or debris. Continuous safety is explicitly false/unverified.

Retain the failed qualification result rather than adjusting tolerances or
automatically repeating. D4.5's independent reproducibility evidence remains
open: the tighter profile is not a second identical-input experiment. Any further
live run requires a separate bounded work decision. Strict M3, task 3.9, target
closure, optimizer and UI integration remain unfinished.

## Verification

130 focused checks passed in 1.84 s before the live experiment. Full suite:
3,604 passed in 607.53 s. Ruff, strict OpenSpec, whitespace and unchanged legacy
SHA-256 passed. Stored source/scenario hashes and position differences were
checked against current files and retained states without another native run.
