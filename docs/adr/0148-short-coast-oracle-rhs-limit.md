# 0148 — Short-coast reference stops at the oracle RHS limit

Date: 2026-11-01
Decision status: accepted negative evidence; ADR0137/0143 gates unchanged.
Implementation: one R5.3 study attempted and offline-audited; scientific result incomplete, no retry.
Scope / milestone: M3 restricted300s parked-state comparison; no mission claim.
Measured revision: `24154beaa354422d89c4e23d71e1fa687e875d9d`, clean throughout study and offline audit.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [completed preparation](0147-short-coast-preparation-review.md) under [ADR0137](0137-short-coast-earth-gravity-contract.md).

## Context and constraints

R5.2 was verified. Execute exactly the frozen reference once: unchanged R1/0098
initial state, exact epochs, sources/GMs/kernels and profiles; four-native /
four-oracle maxima,10000 total RHS and30021 oracle/node state-read caps,60s
shared study and10s separate zero-native audit. Preserve failures and prohibit
repetition or changed contract without a separately justified decision.

## Options considered

- Retry or raise the cap automatically: reject; consumes unauthorized science
  and conceals the first result under a changed contract.
- Treat native-only agreement as independent verification or Earth sensitivity:
  reject; neither independent oracle nor model B completed.
- Retain raw partial evidence, check what is available and pause automation:
  selected under the user instruction and existing scientific contract.

## Observation and decision

[Study](experiments/0148-short-coast-study.json) stopped at A oracle normal with
OracleError: oracle RHS cap10000. The elapsed sample before flush was
1.8111813748255372s; finalization passed. This is the evaluation-count cap,
not the60s wall-time limit. Exactly two native arcs were attempted, returned and
completed: A RK4 h1s and h0.5s, each from the frozen initial state. Their complete
301/601 raw state/force histories and seven samples each are retained.

All21 once-only body-table reads completed. Native retained-state guard reads
were2712 attempted/returned, separately from native internal ephemeris work.
A normal oracle solve was attempted once, with10000 RHS attempted/completed and
30021 oracle/node body reads attempted/completed. It returned no completed solve;
no tighter oracle or B model ran. The last retained successful body query is
Earth at t0+48.605000138282776s. This is not an accepted-step endpoint, integrated
coverage guarantee or solver trace. Counts of accepted/rejected solver steps
and all internal states were not retained, so the root cause is not established.

No numerical comparison rows or signed B-minus-A differences are available.
No independent agreement, Earth-force sensitivity, target accuracy, mass/reserve,
mission feasibility or safety result can be inferred. Initial source/runtime/kernel
identity is retained; the final identity stage was not reached. No final-snapshot
equality is claimed for this failed reference, despite the earlier readiness pair.

The separate [audit](experiments/0148-short-coast-audit.json) reports partial,
study_verified=false in0.07836870802566409s before flush; finalization passed.
It checked the two available native raw profiles,14 node-force rows,26 call events
and the initial snapshot's current43 sources/native binary/9 modules/5 Conda
records. The failed oracle operand is explicitly unavailable. There were zero
native imports/body queries/propagations in the offline audit and no second audit.
A process exit0 means evidence was saved, not that the scientific study passed.

For context only, [post-hoc saved-array Decimal subtraction](experiments/0148-failed-study-checks.json)
finds maximum native h0.5-minus-h1 norms0.00019301011109426145m and
3.438942231775422e-08m/s across seven nodes. It adds no native work and does not
replace the missing native/oracle/profile/model checks or complete R5.3.

Automation ariadna-m3 was updated through automation_update to statusPAUSED,
preserving its prompt and five-minute schedule. The saved automation file confirms
PAUSED. No next study, cap/profile change or automatic retry is authorized here.
The next user decision concerns a separately specified diagnosis/new contract
before another scientific execution. Recommend examining numerical representation
and force-evaluation/error-control behavior first, without assuming the cap alone
should be increased. That is a proposed investigation, not a measured root cause.

## Evidence and verification

[Invocation](experiments/0148-execution-invocation.txt),
[study output](experiments/0148-study-output.txt),
[audit output](experiments/0148-audit-output.txt) and
[check receipt](experiments/0148-failed-study-checks.json) preserve exact paths,
source revision, exclusive files, counts, scope and artifact hashes. Both processes
ran once with the pinned Conda Python. Live evidence stayed outside the checkout;
Git status remained byte-identical and empty across both. All281 tracked protected
code/test/example/environment/legacy/experiment files remain identical to the base.

The runtime/test/environment bytes are unchanged. Reuse the5255 full passing
tests and Ruff result from ADR0146, source identities reviewed in ADR0147; do not
repeat tests or reference work for evidence-only documentation. Finite/strict JSON,
source/evidence hashes, local links, diff and strict OpenSpec pass. Partial audit
acceptance verifies only available saved consistency; the scientific completion
gates remain unpassed. Historical raw JSON and moon_to_mars.py remain unchanged.

## Consequences and revisit conditions

The once-only execution is consumed and the failure is retained. R5.2 preparation
remains complete; R5.3 and scientific R5 success remain incomplete. Pause for a user
choice before revising the experimental contract or running new science. No
optimizer restart, full-force/finite-burn/escape/capture/continuous-safety claim,
strict M3/task3.9 closure, UI qualification or M4–M6/ML work is implied.
