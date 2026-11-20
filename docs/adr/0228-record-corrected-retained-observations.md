# 0228 — Verify corrected retained observations without replaying the study

Date: 2026-11-20 (Europe/Samara)
Decision status: accepted
Implementation: complete for the single R5.59p diagnostic; verification passed below
Scope / milestone: M3, fixed retained interval observations only
Base revision: clean `918d13c3cf6be6acfc5336556c1a6d823f35e9d9`, synchronized `dev`/`origin/dev`
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves [ADR0226](0226-record-retained-trace-input-rejection.md)

## Context and constraints

The user explicitly requested one corrected [ADR0227](0227-admit-pinned-historical-json-encoding.md)
adapter run on the immutable real archives, followed by a separate saved-only audit.
This is the distinct R5.59p authorization, not a repeat of the consumed ADR0226
old-version dispatch. [ADR0224](0224-design-retained-cell-observations.md)'s reference,
nine raw input pins, three cells/midpoints, both signs/paths, gates and caps remain fixed.
The new runner intentionally inherits `stage=R5.59n` and the `0224-*` output paths;
those raw artifacts are preserved, with the distinct invocation identified here
and in the pre-dispatch [authorization](experiments/0228-retained-dispatch/dispatch.json).

## Options considered

- Stop at metadata/artificial qualification: preserves the unknown retained widths
  but does not execute the user's requested observation.
- Invoke the already qualified corrected dispatcher once and audit its first saved
  result once: selected under the explicit instruction and unchanged contract.
  Replays, formula changes, more cells and adjusted limits are outside this decision.

## Decision and rationale

One isolated outer CLI producer and one separate isolated saved-only auditor ran
with Conda Python3.12.14, `-I -S -B`, on the clean measured base. The audit bound itself
to the raw new completion digest. Both returned0; no retries or old scientific audit
replays occurred. The external invocation driver records its exclusive authorization
before dispatch and retains stdout, stderr, timing and output digests. Neither
scientific Python sources, historical evidence, contract nor `moon_to_mars.py` changed.

Accept the result as **observations-verified-attribution-unresolved**. The diagnostic
and audit pass their observation gates; this does not change ADR0221's inconclusive
continuous study or complete the failed original R5.59n task.

## Consequences and revisit conditions

The three default positive finite-cell speed widths reproduce the archived values;
the corresponding singleton widths are tiny in this arithmetic profile. Exact
fractions are retained in the report and [verification manifest](experiments/0228-verification.json).
The following decimal values are rounded display summaries, not new tolerances.

| Saved row | Cell speed width (m/s) | Singleton speed width (m/s) | Cell consumed-mass lower bound (kg) | Singleton consumed-mass lower bound (kg) |
| --- | ---: | ---: | ---: | ---: |
| 62 | 98.405626641 | 1.868e-89 | 1499.127855967 | 1504.651476838 |
| 94 | 96.231380793 | 1.792e-89 | 1499.117151541 | 1504.520286609 |
| 125 | 94.114771027 | 1.748e-89 | 1499.262399035 | 1504.546512864 |

The three selected positive singletons exceed the unchanged1500 kg consumed-mass
exclusion threshold; each whole positive cell remains unresolved below it. Both
arithmetic paths have this disposition: six positive finite-cell records reach
clearance and remain unresolved, while six negative finite-cell and all12singleton
records stop at mass exclusion. Non-reached clearance is expected, not missing data.
Across default positive cells, saved `_ellipse.radius` widths are3666.678–3801.163 m
and `_reverse.radius` widths9843.298–10284.870 m. These are interval widths of
same-unit intermediate quantities, not independent physical errors or additive
causal contributions. Generic primitive fields remain unclassified.

The observations localize finite-cell enclosure width along the saved calculation,
but do not separate genuine phase variation from dependency overestimation or prove
a dominant mechanism. Three singleton refusals do not exclude their neighborhoods.
No continuous certificate, eligible pair, physical continuity, trajectory accuracy
or mission safety follows. No SPICE, kernel, force or integration call, new direct
point or point-root construction outside the48 interval bound calls, R5.59i replay
or R5.60 occurred. Those bound calls do reconstruct signed interval geometry/roots. Keep automation PAUSED;
further formula/diagnostic work needs its own scoped decision, not an automatic retry.

## Evidence and verification

- [Attempt](experiments/0224-retained-trace-result/attempt.json), [report](experiments/0224-retained-trace-result/report.json), [receipt](experiments/0224-retained-trace-result/receipt.json), [completion](experiments/0224-retained-trace-result/completion.json) and [separate audit](experiments/0224-retained-trace-audit.json) retain their original bytes and source/method identities.
- 24 traced/control canonical matches, six actual saved-default matches and24 sampled
  containment records with16 applicable quantities each pass. Geometry/root parity
  uses the unchanged1 mm/1 µm/s gates; interval containment is checked exactly.
  There are48bounds,1248stage events and zero new direct points. Producer mass calls12
  include internal readback; the separate auditor performs six new cached mass calls
  and zero bounds/traces/conics/points. It is not a computation-free diagnostic.
- External full invocation times: producer1.129278666 s, auditor0.326211875 s;
  dispatcher times1.115021458 s/0.308045375 s include each worker and finalization.
  Receipt/completion elapsed0.984238125 s/0.990601625 s and audit pre-write0.251420500 s
  are separately labeled internal timings, not substituted for external totals.
- Authenticated historical artifacts2,280,855bytes; full source inventory2,504,838bytes.
  Five produced files total3,675,364bytes including the500-byte separate audit.
  The30 s/process,48bound,8192event and4 MiB source/evidence limits pass unchanged.
- [Dispatch measurement](experiments/0228-retained-dispatch/measurement.json),
  [driver](experiments/0228-retained-dispatch/invocation-driver.txt), producer/auditor
  [producer stdout](experiments/0228-retained-dispatch/producer.stdout)/[audit stdout](experiments/0228-retained-dispatch/audit.stdout)
  and the verification manifest preserve commands, raw pins, timings and counters.
  Independent read-only review verified the saved hash chain, summary digest,
  traced/control/historical identities, counters and branch dispositions without
  importing scientific helpers or invoking another auditor.
- No implementation changes: pytest and Ruff were not rerun. Reuse ADR0227's
  18 focused/6578 guarded full passes with494 explicit native/UI/prohibited-work
  exclusions; this is not fresh native or mission qualification. New JSON/digests,
  local links, clean diff and strict active-change OpenSpec validation pass.
