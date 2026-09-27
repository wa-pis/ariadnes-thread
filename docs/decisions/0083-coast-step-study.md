# 0083 — Smaller coast steps agree, but differences do not decrease

Date: 2026-09-27. Base revision: `5e92d54` plus the D6 implementation and tests.
Status: diagnostic evidence, not absolute accuracy, target closure or safety.
The [retained report](experiments/0083-coast-step-study.json) records exact Python
source hashes, pinned 0079/0082 evidence digests, normalized input, resources,
settings, saved-mesh diagnostics, signed comparisons and separate wall time.

## Procedure

One live experiment after 181 focused tests passed; no retries or extra profiles:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.coast_diagnostic examples/m3_feasible_mission.toml docs/decisions/experiments/0079-research-reference.json docs/decisions/experiments/0083-coast-step-study.json --step-baseline docs/decisions/experiments/0082-identical-start-coast.json
```

All three full-force coasts use the same retained nominal departure-cutoff state,
mass and arrival-ignition epoch, fresh environments and no thrust. Only the local
maximum step changes: 21600, 10800, 5400 s. Coefficients remain rkdp_87, initial
step 75 s, minimum step 1e-5 s, relative tolerance 1e-13 and absolute tolerances
1e-5 m / 1e-8 m/s / 1e-11 kg. Production settings and D5's two-launch cap remain
unchanged. One cooperative 300 s deadline covers verification and all profiles;
it cannot preempt a native call. Output creation refuses to overwrite evidence.

## Observations

Three native arcs attempted and completed in 30.626274750 s, no retries.
The first endpoint exactly matches the retained D5 tighter endpoint in all seven
components; its baseline control passes before either refinement starts.

| Maximum step (s) | Saved intervals | Min / median / max interval (s) | Checked states |
|---|---:|---|---:|
| 21600 | 1553 | 3.227433085 / 21600 / 21600 | 3107 |
| 10800 | 2712 | 3.227433085 / 10800 / 10800 | 5425 |
| 5400 | 5036 | 3.227433085 / 5400 / 5400 | 10073 |

These describe saved epochs, not rejected trials or internal Runge–Kutta stages.
All three ordered epoch digests differ: the cap changes actually alter the mesh.
Checked-state counts include repeated evaluations, not unique saved epochs.

| Maximum-step pair (s) | Position difference (m) | Velocity difference (m/s) |
|---|---:|---:|
| 21600 / 10800 | 0.471287684 | 8.386595932e-8 |
| 10800 / 5400 | 1.500795688 | 2.700787788e-7 |
| 21600 / 5400 | 1.972055745 | 3.539388767e-7 |

Mass differences are exactly zero. All pairs pass the existing diagnostic
thresholds of 10 m / 1e-4 m/s / 1e-6 kg. Endpoints are not identical.
Signed vectors in each `i-j` report entry are endpoint i minus endpoint j.
The second adjacent difference divided by the first is 3.184457687 for position
and 3.220362361 for velocity: both increase, rather than decrease.

## Interpretation and decision

This same-start, same-method step experiment shows metre-scale sensitivity to
the tested caps. It does not resolve D5's 115.67 m disagreement between different
profiles, identify an accurate reference, or prove convergence. The increasing
adjacent differences prohibit a claim that smaller steps improved accuracy.
Roundoff and other numerical effects remain hypotheses, not diagnosed causes.
No tolerance, production profile, target command or scientific gate is changed.
The original large target miss is separate and remains unresolved.

Stop this bounded study here. A useful next scope decision is the smallest
research-only target-closure experiment addressing the seed geometry identified
in Decision 0080, with explicit bounds and acceptance checks before any run.
No optimizer, additional native study, UI integration or later milestone is
authorized by this record. Strict M3/task 3.9 and continuous safety remain open.

## Verification

181 focused tests passed in 3.53 s, including native nearly force-free coast
oracles for all three profiles (1e-6 m / 1e-9 m/s, exact constant mass), actual
native settings, unchanged D5 cap, failure stops, baseline rejection, deadline,
fresh environments, finite mesh/ratio handling and explicit unchanged results.
The toy oracle does not establish mission accuracy. Full suite: 3,655 passed in
644.15 s. Ruff, strict OpenSpec, whitespace and unchanged legacy SHA-256 pass.
Retained source hashes, finite JSON, launch budget and signed differences/norms
were checked independently without another native run. D6 is complete as a
diagnostic slice, not a convergence certificate or strict-M3 acceptance.
