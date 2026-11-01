# 0150 — Trace synthetic solver attempts and localize first observed failures

Date: 2026-11-01
Decision status: accepted bounded synthetic diagnosis under the user's instruction to proceed and use binary search.
Implementation: verified private diagnostic; one synthetic demonstration and offline checks complete.
Scientific status: synthetic numerical mechanism observed; actual R5 causality and physical sensitivity remain unverified.
Scope / milestone: M3 R5 numerical diagnosis; no SPICE/Tudat or failed-reference replay.
Base revision: `bc5f1d7c0e5581f07f4584e31ab9ddc0375c5ebf`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [precision diagnosis](0149-oracle-time-precision-diagnosis.md); ADR0137 reference contract remains unchanged.

## Context and constraints

The user authorized the synthetic diagnosis and requested checking each step and
binary search for the deviation point. Local error and rejected-step events are
not monotone in time. Reintegrating arbitrary prefixes changes adaptive history;
it cannot safely locate the first historical failure. Record one trace per fixed
synthetic case and binary-search monotone prefix-any-failure flags instead.
This localizes the first observed record, not a continuous physical boundary or
the cause/location of the already failed R5 experiment.

## Options considered

- Bisect raw error(t) or rerun successively shortened R5 arcs: reject;
  nonmonotone predicate and unauthorized reference repetition.
- Copy or change SciPy's step controller: reject; would perturb the mechanism
  being diagnosed and create another solver implementation.
- Observe the pinned DOP853 error-estimate hook, reconcile actual step outcomes,
  and search retained prefixes: selected; numerical decisions remain unchanged.

## Decision and fixed synthetic contract

Use only installed pinned SciPy1.17.1/NumPy1.26.4 and stdlib. The sole private
helper is0150-synthetic-step-diagnostic.py, outside production APIs. Synthetic
body B(s)=B0+Vs has B0=(-47000000000,128000000000,55000000000)m and
V=(31246.224457,0,0)m/s. Its single point field has mu4902800121846.8m^3/s^2.
An initially circular relative orbit has radius1837400m, starts on positive x,
positive y tangential speed sqrt(mu/r) subject to binary64 construction, and
zero corrections q. No real body state, spacecraft candidate, ephemeris or
mission solution is acquired. Exact relative circular formulas with Decimal
sine/cosine provide an independent analytic check; document tiny initial binary64
speed rounding separately from the1e-6m/1e-8m/s analytic diagnostic gates.

Compare three fixed10s cases with identical intended translating-body physics:
relative force evaluation; absolute positions with local body time; absolute
positions with body time float(t0+s)-t0 at t0=978995455.2304223s. Preserve normal
R5 local solver settings rtol1e-12, atol(1e-7m x3,1e-10m/s x3), first_step1s,
max_step5s. These synthetic arms do not replace any frozen R5 force model.

Cap each case at3000 completed force evaluations and300 retained trial records, all three
at9000 RHS and a shared10s cooperative process/import/compute/JSON/flush budget.
Preserve finite partial traces on cap/error; do not tune to force an event. Tests
use separate bounded analytic fixtures and do not consume or repeat R5 science.
Every RHS records q/time, absolute-time rounding residual, computed acceleration,
independent Decimal relative field and its vector discrepancy using the existing
force envelope max(1e-15m/s^2,1e-11 times reference magnitude). Each trial records
start/end/h, scales, normalized E5/E3 components, original error norm and controller
decision. Check the final accepted trial against actual solver.t/y after step().
Separate callback attempts, completed force records and SciPy nfev; constructor
failure leaves nfev unavailable. A cap is checked before the next force record or
trial record; the trial-record cap can follow computation of that unrecorded trial.
An exception inside step() leaves a trial incomplete, not a fabricated decision;
a failure after a saved accepted endpoint is labeled by phase instead.
At every accepted endpoint check the independent analytic correction solution.

Find separately first force-envelope failure, first rejected trial and first
accepted analytic-gate failure. Build cumulative failure flags and binary search
those flags, retaining search probes/index/preceding record and observed interval.
A control rejection is not physical/global error. No observed event is a valid
result. Searching the trace requires no additional integration or source queries.

Verify tracing versus vanilla DOP853 exact t/q/nfev parity on the deterministic
relative fixture, analytic and Decimal checks, nonmonotone-event binary search,
input/cap/deadline/partial/exclusive-output paths, focused/full pytest, Ruff,
strict OpenSpec and protected files. Only then retain one three-case demonstration.
Automation remainsPAUSED; the user authorized this manual synthetic diagnostic,
not resuming the schedule, another R5 attempt, weaker scientific gates or new stack.

## Evidence and verification

At base `bc5f1d7`, the new helper/test were untracked and exact source hashes and
checkout status are retained in [verification](experiments/0150-verification.json).
[30 focused tests](experiments/0150-focused-pytest.txt) pass in0.31s;
[5285 full tests](experiments/0150-full-pytest.txt) pass in659.94s with checkout
status unchanged throughout. Ruff and strict OpenSpec pass. All290 previously
tracked production/test/example/environment/legacy/experiment files match HEAD.
New focused tests and the retained demonstration use no SPICE/Tudat; the full
suite includes existing native tests. A separate read-only review found no
remaining material controller, counter, failure-phase or search issues.

One [exact invocation](experiments/0150-synthetic-invocation.txt) runs the three
fixed cases; [raw trace](experiments/0150-synthetic-trace.json) and
[output](experiments/0150-synthetic-output.txt) retain all operands and attempts.
All cases finish10s with2523 total completed RHS, well below9000;
elapsed before flush0.44547345815226436s with finalization passed. Zero body
queries, native propagations or R5 reference replays. No retry, tuning or profile
change. Raw runtime/source identities are in each case. Synthetic coordinates
and borrowed epoch spacing are an arithmetic fixture, not acquired mission states.

| Case | RHS | Accepted / rejected trials | Max analytic position / velocity error |
| --- | ---: | ---: | --- |
| Relative | 37 | 3 / 0 | 1.42110e-14m /5.32909e-15m/s |
| Absolute, local body time | 73 | 6 / 0 | 7.58030e-10m /1.77035e-10m/s |
| Absolute, rounded body time | 2413 | 137 / 64 | 2.12546e-8m /5.90422e-9m/s |

Only the rounded-time arm exceeds the force-consistency envelope. Binary prefix
search finds its first bad RHS in callback order at zero-based index1,
s=0.05260015195876773s (preceding index0 at0s passes). Body-time residual is
-6.6188019093305073e-9s; force discrepancy3.2563990605650234e-10m/s^2 exceeds
1.4522345445836665e-11m/s^2. Its first attempted trial[0,1]s is rejected with
error norm15.733943746271663>1. Later retries contain a bad force evaluation at
s=0.033544769276316236s/index13: callback order is not sorted elapsed time.
Neither value is an exact continuous first crossing. No accepted endpoint fails
the1e-6m/1e-8m/s analytic gates in any arm.

The same intended translating-body physics requires about65.2 times as many RHS
in the rounded-time arm as the relative arm, or33.1 times as many as the
absolute-local arm. This demonstrates synthetic field noise and controller cost;
it does not show trajectory failure under these gates or prove why historical R5
hit its cap. Tiny initial binary64 speed rounding is shared by all arms; the
circular comparison is a diagnostic reference, not a rigorous global error bound.

A separate [stdlib-only offline invocation](experiments/0150-offline-audit-invocation.txt)
[passes saved-row verification](experiments/0150-offline-audit.json):80-digit
Decimal fields/phase residuals/force flags, independent trigonometric endpoint
gates, scaled E5/E3 norms, all trial decisions/counters/accepted times, direct
scan versus binary probes and preceding records. This does not reintegrate or
validate unsaved mission dynamics. Artifact digests bind both sources and raw
logs; original290 protected files and all prior scientific gates remain unchanged.

## Consequences and revisit conditions

This can distinguish synthetic coordinate/time mechanisms and identify first
observed failures while checking each trial. It does not establish actual R5
accepted/rejected history, Earth sensitivity, independent mission accuracy,
continuous safety, strict M3 completion or readiness for deferred milestones.
Any actual mission/reference rerun or changed profile still needs its own contract.
