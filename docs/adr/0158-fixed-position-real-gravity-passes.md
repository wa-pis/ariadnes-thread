# 0158 — Fixed-position real-source gravity passes

Date: 2026-11-08
Decision status: accepted; retain the unchanged ADR0156 experiment and its measured result.
Implementation: R5.10 prepared; R5.11 execution and separate saved-data audit complete.
Scientific verification: fixed-position same-polynomial force arithmetic only.
Scope / milestone: M3 R5.11; no trajectory propagation or mission qualification.
Base revision: `1c3921c686f720eba23cdc29e035a054b0fc4c97`, clean `dev` for both launches.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [ADR0156](0156-fixed-state-real-gravity-contract.md) using the tested [ADR0157](0157-prepare-fixed-state-gravity-check.md) bytes, preserving historical failures and evidence.

## Context and constraints

After verified R5.10 preparation, the user authorized continuing. The next bounded
question is whether compensated direct point gravity at one frozen spacecraft
position agrees with high-precision evaluation of the same source polynomials.
It does not ask whether a moving spacecraft reaches Mars. Keep the original
operands, force gates, counts and10s study/audit budgets; no retry or integration.
Automation `ariadna-m3` remains PAUSED.

## Options considered

- Repeat preparation tests or the successful source-time experiment: unnecessary;
  all eight tested source/test hashes and338 older protected files still match.
- Start a corrected integration: premature; moving-spacecraft drift/correction
  assembly needs a separate contract and verification first.
- Execute the already prepared fixed-position study once, then audit its saved
  result in another process: selected under the unchanged ADR0156 requirements.

## Decision and rationale

Retain one study and one audit, both passed. Each fresh pinned Conda Python3.12.14
process used `-I -S -B`, a parent monotonic timestamp captured immediately before
child creation, and unchanged default clock/adapters. Checked source bytes were
compiled directly; eight source/test hashes and the ADR0157 verification-manifest
hash were bound before importing the study or auditor. This includes child startup,
imports, input reads/hashes and result serialization/flush in the elapsed interval.
The invocation has no retry loop and uses new exclusive evidence/receipt paths.

Both runs use the exact0136/0148 initial endpoint and ADR0155's21 source rows:
one unchanged X, seven source times, Sun/Earth/Moon data, and Sun/Moon[/Earth]
force summation order. SSB/J2000/TDB/NONE, the frozen R5 GMs (including the harmonic
lunar coefficient), original13-kernel provenance and Type2/frame/centre/coverage
checks remain intact. The underlying source is INPOP19a; no DE440 substitution,
new kernel-pool query, native call or source acquisition occurred.

| Completed work per process | Attempted | Completed |
|---|---:|---:|
| Source rows |21|21|
| Decimal reference fields |168|168|
| Binary64 candidate/control fields |63|63|
| Model totals, seven A and seven B |14|14|

All140 required gate flags pass:35 source/model cases, two gates, two precision
profiles. All147 source exterior-domain flags pass. The independent auditor
reconstructs raw operands, fields, signed contributions and sums rather than
trusting saved flags; its result binds the exact study SHA256. Its shared pure
reference remains independent of candidate arithmetic, not an independent
astronomical ephemeris or a second implementation of the reference formula.

The following ratios use100-digit saved gates; each is the maximum error divided
by its own unchanged envelope across seven samples, not a physical error budget.

| Source/model | Returned-geometry error/envelope | Overall error/envelope |
|---|---:|---:|
| Sun |3.73081e-5|3.92302e-5|
| Earth |2.70821e-5|0.00455764|
| Moon |1.36502e-5|0.628793|
| A, Sun/Moon |1.34119e-5|0.626164|
| B, Sun/Moon/Earth |1.08480e-5|0.625110|

The worst source overall comparison is Moon row5 at offset
`2.9802322387695312e-8s`:9.13154381959e-12 versus1.45223454636e-11m/s^2.
The largest total overall discrepancy is9.13158667163e-12m/s^2, B at that same
offset. Maximum returned-geometry errors are1.97897756807e-16m/s^2 for sources
and1.76479369085e-16m/s^2 for totals. Source and total envelopes retain their
original norm scales; totals use the sum of constituent source norms.

Across sources, maximum signed-contribution norms are native-source discrepancy
9.13150627357e-12, residual rephasing1.39950618493e-23, relative assembly
1.82893243837e-16 and field evaluation1.97897756807e-16m/s^2. These maxima may
come from different rows and must not be added as signed attribution. The native
source discrepancy dominates here and stays included in the overall gate; no
floor subtraction or extra allowance was used. It measures arithmetic against the
same polynomials, not astronomical uncertainty.

Reference vectors converge at80/100 digits: the worst precision difference is
1.47769e-19 of its relative1e-60 limit. All gate classifications are stable and
all saved vector-telescoping residuals are zero at both profiles. Uncorrected and
wrong-sign controls pass all seven Sun/Earth samples; for Moon and each A/B total,
both pass only offset zero and fail at the six nonzero offsets. These diagnostic
outcomes neither change required gates nor prove universal improvement.

Total child-process intervals including startup and exit are0.4372044578194618s
for the study and0.3446695418097079s for the audit, each below its10s budget.
The smaller pre-flush values,0.31602774979546666s and0.33023275015875697s,
are retained separately and are not total execution times. Both finalization
gates pass. Zero scientific imports, native calls, kernel loads, GM acquisitions,
spacecraft propagations or R5 replays occurred.

## Consequences and revisit conditions

R5.11 completes the fixed-X force check. Seven source times at a repeated X are
not seven trajectory states; only elapsed zero matches the saved spacecraft
epoch. No moving-spacecraft drift/correction adapter, corrected integration,
Earth-force trajectory sensitivity, historical R5-failure cause, full-force /
finite-burn feasibility, independent ephemeris truth, continuous safety or strict
M3/task3.9 closure is established. The original failed R5.3 remains failed.

The next narrow question is whether moving-spacecraft drift/correction assembly
preserves these arithmetic properties. Specify fixed inputs, an independent
reference, measurable gates and a work budget before preparing or executing it.
This record authorizes no new solve, R5 replay, optimizer expansion or automation
resumption. Keep this successful experiment immutable and do not repeat it on
unchanged data/code.

## Evidence and verification

- [Exact invocation](experiments/0158-fixed-gravity-invocation.txt),
  [study process receipt](experiments/0158-study-receipt.json),
  [audit process receipt](experiments/0158-audit-receipt.json).
- [Raw fixed-position study](experiments/0158-fixed-gravity-study.json),
  [separate saved-data audit](experiments/0158-fixed-gravity-audit.json),
  [derived result summary](experiments/0158-result-summary.json).
- [Digests, frozen source/protected files and document checks](experiments/0158-verification.json).

Read-only saved-vector review reconciles all source/model gate norms, signed
sums, cancellation scales, precision/telescoping checks and receipt bindings.
The review calculates norms of retained vectors only, with no additional force
study, audit replay or native call. Historical inputs/evidence and
`moon_to_mars.py` remain byte-identical.

This stage adds evidence/documentation only. Reuse ADR0157's221 focused/5630 full
passing tests and repository-wide Ruff on exactly unchanged tested code; runtime
tests and Ruff were not rerun. Finite/duplicate-free JSON, input/helper/artifact
digests, local links, protected-file comparisons, clean diff and strict OpenSpec
are checked for this stage before commit. No scientific gate or dependency changes.
