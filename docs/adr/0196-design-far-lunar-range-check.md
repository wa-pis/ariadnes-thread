# 0196 — Design the 18,374 km lunar range check

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted for a bounded research design.
- Implementation: R5.49 design complete; R5.50 preparation and R5.51 live check pending.
- Verification: saved evidence and design arithmetic only.
- Scope: unpowered model B, candidate `d0001-t0035`, from the audited R5.48 endpoint.
- Base revision: `8be85d134ec82320d417c844a33e9430fa43a08b`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-the-18374-km-lunar-range-marker), [design](../../openspec/changes/refine-physical-trajectory/design.md#r549-design-the-far-lunar-range-check-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[ADR0195](0195-prospective-lunar-range-marker-bracketed.md) independently
bracketed 3,474.8 km and ended near 3,497.2 km. The new question is whether
the same unpowered model brackets **18,374,000 m from the lunar centre**
on an agreed interval. [ADR0105](0105-local-finite-burn-contract.md)
chose that radius as ten times its parking-orbit radius. We reuse only
the radius: ADR0105's target was a six-state at its own fixed epoch.
This experiment imposes neither that epoch nor that target and does not
change the interfaces in [ADR0135](0135-fixed-orbit-boundary-contract.md).

## Options considered

- Find a crossing by propagating until the event: cheaper if it is
  early, but leaves the horizon and evidence size dependent on the result.
- Chain short runs or replay from cutoff: repeats or introduces
  intermediate restarts and can obscure accumulated numerical differences.
- Continue once from the audited end on a fixed interval with the
  existing four numerical profiles: selected. Keep the force model and
  tolerances fixed and qualify the larger evidence pipeline before live work.

## Decision and rationale

Restart all profiles from the archived **terminal** tighter RK4 state at
`978998965.9635216` TDB s since J2000 (+650 s from simulated cutoff),
with `1351.7475727997967 kg` of constant mass metadata. Bind the six
binary64 words across raw history, native sample and audited mesh and
common operands. Bind the terminal Moon/SSB state against both archived
paths, and record the signed deltas from the other three archived endpoints.
Before propagation check the new initial common Moon state bit for bit.
Retain the Sun/Moon/Earth direct point-mass model B, geometric SPICE,
SSB/J2000, SI/TDB, ordered kernels, GMs and sampled exclusion guards,
zero thrust and mass flow. This continues only tighter RK4 from its own
endpoint. There is no A run, search, parking/burn/prefix replay or force switch.

### Physical interval

Recorded range and radial speed at restart are 3,497,227.570749 m
and +1,175.723494 m/s. The remaining range is 14,876,772.429251 m.
Dividing by the current radial speed gives 12,653.292 s. As a second
planning check, use the *osculating two-body Moon* state: from
Moon-relative position and velocity compute specific energy
`E = |v|²/2 - mu/r` and angular momentum `h = |r × v|`.
With positive `E`, use `a = mu/(2E)`, `e = sqrt(1+2Eh²/mu²)` and
`u(r) = acosh((1+r/a)/e)`. Subtract
`sqrt(a³/mu)·(e·sinh(u)-u)` at the two radii to get 13,261.948 s.
Neither calculation propagates model B or bounds its crossing time.

Fix **16,000 simulated seconds** (4 h 26 min 40 s), 20.6% above
the second estimate, ending at `979014965.9635216` TDB s. The closed
interval lies strictly inside the retained Sun, Moon and Earth Type 2
record intervals; this is a metadata precheck, with over 69,834 s to
the nearest upper record boundary. Do not extend the interval or end
at the marker.

### Numerical evidence and marker verdict

Use RK4 steps of 1 and 0.5 s, the unchanged DOP853 profiles (maximum
steps of 5 and 2.5 s; initial steps of 1 and 0.5 s), and 321 shared
epochs at 50 s spacing including both ends. Keep the R5.48
state gates: 0.01 m and 1e-5 m/s for RK4 step and tighter cross-engine
comparisons; 0.001 m and 1e-6 m/s for the adaptive step comparison.
Retain and independently replay all arithmetic, sources and trial
evidence required by R5.48, including every adaptive RHS and output,
all sampled native guards, and native coepoch force telemetry. For the
expensive adaptive source/force comparison, take each profile's 321
outputs, first seven completed RHS (including a nonzero time residual
among those seven), and first completed callback by ordinal in each
of the 314 windows `(300+50j, 350+50j]`, `j=0..313`. This extends
the [R5.43](0190-post-cutoff-coast-outbound-at-samples.md) later-window
rule. Keep rejected/dense callback linkage; missing or overlapping
selected callbacks fail the evidence gate. Require 963 comparisons,
642 native telemetry rows and 1,284 adaptive observations.

Audit 1,284 common and 48,002 native mesh directions with exact signs
and independent Decimal reconstruction (same 1e-6 m and 1e-9 m/s
arithmetic gates). Accept `marker-bracketed` only if all six grids have
exactly one strict below-to-above adjacent pair with positive endpoint
radial signs, no inward pair or equality, the four common intervals
are identical, and both native brackets are contained in that common
interval and overlap by positive width. Expected numerical agreement
and the marker are separate verdicts. Complete no-crossing or conflicting
evidence is `marker-not-established` with reason (including a crossing
that straddles different reporting cells). Failed required evidence,
numerics or finalization yields an `unavailable` marker. Preserve
all individual brackets and signs. Do not interpolate an event time,
move the grid or add marker-only source calls.

### Work, time and storage limits

The step ceilings plus first steps require at least 9,602 successful
adaptive steps. At 12 new step RHS evaluations per step plus one
initial RHS evaluation for each profile, at least 115,226 RHS calls
are required even before rejections and dense-output callbacks.
The 600 s R5.43 used 4,496 RHS and 368 trials; multiplying by
`16000/600` gives about 120,000 RHS and 9,813 trials. Choose hard
combined caps of **160,000 RHS attempts and 13,000 trial attempts**
(about 33% and 32% above those projections), counting rejected and
dense work where applicable. Two native arcs and two adaptive solves
are the maximum; also at most one pool setup, 30 inventory calls and
zero new GM reads. Exactly `3 × (48,002 + 2) = 144,012` native guard
reads include the two preflight groups. The adaptive maximum is
`4 × (160,000 + 321) = 641,284` explicit reads, or **785,296** including
native guards. This excludes internal Tudat calls; the arc cap,
fixed step counts and watchdog still apply. Cap sampled SPK polynomial
evaluations at `6 × 1,284 = 7,704` in each phase. Record and check
attempt/return/complete counts, stopping before the first over-cap call.

Measured R5.43 parent times were 9.05 s study and 5.72 s audit;
R5.48 took 5.71 s and 1.59 s. Linear duration scaling from R5.43
gives about 241 s and 153 s. Setup is visible in the short run;
serialization and replay also change with trace size. Use
**480 s study and 300 s audit** as hard wall limits, roughly twice the
scaled reference, pending a capacity test. They include setup, run,
shard closure, integrity checks and receipts, under separate
monotonic parent watchdogs. They are termination budgets, not
performance guarantees or changes to production limits. At full
cap, preparation must measure synthetic producer/finalization and
independent audit paths in at most **360 s and 225 s**, respectively
(25% of each limit left unspent), with ≤2 GiB peak RSS per process.
Exercise real serialization, hashing, compression and arithmetic
replay on artificial cap-sized operands rather than extrapolating a
small fixture. A miss blocks live launch and requires a new reviewed
contract, not a larger timeout at launch.

R5.43's study was 39.4 MB raw and 7.73 MB gzip. Naive scaling alone
is 1.05 GB raw and 206 MB compressed before the extra mesh evidence.
Use bounded lossless shards (≤16 MiB raw per shard, **2 GiB raw and
512 MiB compressed combined** for study and audit, plus at most
1 MiB in total for manifests/receipts). Deduplicate identical immutable
operands by reference only; preserve nonidentical and partial records.
Check ≥4 GiB free on each working and retention volume at preflight;
do not keep a second full raw copy on the same volume.
Measure capacity with representative distinct synthetic data at the
work caps; separately test size overruns. Process shards in order
without reconstructing a giant JSON object. Bind raw and compressed
hashes, lengths, order, record keys/counts and phase/checkout receipts.
Before live approval, name a durable locally retained destination
and verify lossless readback there. Commit the small manifest and
summary; retain the full lossless shards outside Git with verified
restoration. A manifest without available evidence cannot certify a pass.

## Consequences and revisit conditions

R5.50 prepares a private longer study and isolated stdlib audit on
synthetic or metadata fixtures only. Reuse pinned primitives as
applicable; the existing helpers' 300/600 s guards and 50 s sampling
contract must stay intact, so duration-aware orchestration is private
to this experiment. Keep source/model/force gates and tolerances
unchanged. Verify synthetic success, complete negative verdicts,
corrupt or interrupted archives, cap and late receipt failures and
full-cap feasibility before requesting separate R5.51 authorization.

R5.51 is one future study and one independent saved-data audit, with
zero scientific imports, kernel calls or integration in the audit.
Prefix failures preserve the first safely committed shards and cause;
incomplete, absent or late receipts cannot certify a result. The
attempt is consumed on success, a qualified negative result or
technical failure; no automatic retry. Agreement means sampled
numerical consistency in model B, not a physical limit on error, a
unique crossing, a sphere of influence, lunar escape, burn closure,
a transfer handoff, continuous clearance or strict M3 qualification.

## Evidence and verification

The [design inputs](experiments/0196-design-inputs.json) bind the
archive manifests, exact restart, retained record metadata and
arithmetical bounds. Verified both saved archive digests and original
report bytes against their manifests, receipt bindings for R5.48,
endpoint words, coverage metadata, exact grids, count and time
arithmetic, local links, diff and strict OpenSpec. No new ephemeris,
kernel, force or SPK polynomial evaluations, runtime tests or
propagation. Full-cap timings and physical results remain unmeasured.
