# 0085 — Wire one correction through the existing research propagator

Date: 2026-09-28. Base revision: `596ceef` plus D7.2 implementation and tests.
Status: orchestration verification, not a live targeting result.

## Decision

Extract the existing three-arc composition body behind the unchanged D4 entry
guard. Reuse its native force/integrator/engine adapters, mass handoff, sampled
collision/dry-mass guards and failure handling. D7 has a private standalone
driver and local budget; D4's six-arc and D5/D6's two/three-arc limits remain
unchanged. No second dynamics implementation, new dependency or UI/API change.

The D7 driver verifies pinned Decision 0079, normalized scenario, reproduced
candidate, runtime/kernels, environment resources, rebuilt boundaries/target,
prescribed seed and integrator settings. Baseline boundary drift must pass before
probes start. Every subsequent run gets a fresh resource-matched native
environment; none may reuse an earlier native body system.

Run roles are baseline, probe-0 through probe-5, trial, and optional tighter.
Only the trial can be selected for the frozen tighter comparison, and only when
it improves according to D7.1. Probes never become commands. Already-closed
baseline, rank deficiency, non-improvement and failure stop the sequence;
no alternate seed, backward probe, damping retry or second correction occurs.

One cooperative 300-second clock covers verification and all evaluations. At
most eight commands, nine three-arc evaluations and 27 native launches are
allowed. Commands count before analytic rejection; launches count immediately
before native calls. Completed arcs count only after checks. A native failure
retains local attempted/completed counts without partial endpoints. Earlier
completed runs remain diagnostic evidence, never a partial successful mission.
The clock cannot preempt a native call; expired output is rejected on return.

Reports keep ordered controls with units, per-run residuals and sampled-check
coverage, raw finite-difference/solve diagnostics, reference/resource/source
identity, rejection reasons/counts, separate wall time and explicit unverified
continuous safety. An improved nominal result survives an unavailable or failed
tighter comparison as an unvalidated observation. Output files are exclusive;
the diagnostic cannot overwrite retained evidence.

## Verification and next action

266 focused tests passed in 9.47 s, including native burn/coast regressions and
old budget contracts. Manufactured orchestration checks all nine failure
positions, preparation identity mismatches, baseline drift, rank loss, rejected
probes/trial without launches, a shared deadline, reused environment rejection,
unchanged frozen commands and a failed tighter comparison. Shared-composer tests
check mass/collision/history/native failures and local counters across runs.
The test trajectories are manufactured, not a prediction of target improvement.

Full suite: 3,704 passed in 603.96 s. Ruff, strict OpenSpec, whitespace and the
unchanged legacy SHA-256 pass. Diagnostic CLI help also returns successfully.
No D7 mission experiment was run. D7.2 is complete as orchestration; D7.3 is
the next step: one live invocation under the specified limits, retaining its
result even if it fails. Strict M3/task 3.9 remain open; do not archive the change.

Prepared invocation (not executed in this step):

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment examples/m3_feasible_mission.toml docs/decisions/experiments/0079-research-reference.json NEW_EVIDENCE.json
```

Exit 1 means an aborted study; exit 0 only means the bounded study returned a
completed diagnostic outcome, which can be non-improvement or disagreement.
Neither exit code certifies a valid mission.
