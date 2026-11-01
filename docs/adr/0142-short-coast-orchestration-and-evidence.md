# 0142 — Prepare bounded short-coast orchestration and evidence

Date: 2026-11-01
Decision status: accepted preparation unit under ADR0137; scientific contract unchanged.
Implementation: R5.2e runner verified;37 new/81 focused and5132 full tests pass.
Scope / milestone: private M3 orchestration, injected preparation only; no R5 reference execution.
Base revision: `2fef4c5deb841f3ec83a78991f7c40da2d0320ef`, initially clean; runner/tests untracked during checks.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; composes [input/identity helpers](0141-short-coast-input-and-runtime-identity.md), [native adapter](0140-native-short-coast-adapter.md), [oracle](0138-independent-short-coast-oracle.md) under [ADR0137](0137-short-coast-earth-gravity-contract.md).

## Context and constraints

The remaining execution path must enforce ordering, shared timing and finite
partial evidence without combining the engines' dynamics. Complete this path
using injected tests, then implement the independent offline audit before any
reference study. This is not R5.2 completion or authorization to bypass that audit.
No new dependency, production code, candidate, phase, input, kernel or gate change.

## Options considered

- Separate timers per solve or continue B after a failed A: reject; violates the
  shared60s/first-failure contract and obscures available evidence.
- Reimplement numerical dynamics in the runner: reject; compose prepared adapters.
- Hash-bound adapter loading plus shared-budget orchestration/partial evidence:
  selected, tested with explicitly marked injected adapters only.

## Decision and rationale

[Runner](experiments/0142-short-coast-runner.py) hash-checks and loads the three
prepared modules using stdlib only. It reuses the existing R2 timed-call/retention
events with an explicit60s check. Fresh-process exclusive execution measures from
a baseline captured before remaining imports, includes setup/identities/body table /
solves/comparisons/serialization/flush, and rejects scientific modules loaded before
entry. Direct default reference mode requires that baseline. No execution CLI is
provided and no reference call is made during preparation.

Load bound inputs and initial identity, check R1's ordered kernel manifest, then
acquire the21 once-only raw geometric body states at the seven frozen epochs.
A shared oracle context accounts for those reads and all later RHS reads. Execute
A native normal/tighter then oracle normal/tighter, validate profiles/initial nodes /
counts/units and numerical gates, then do B's equivalent sequence. All native calls
share one four-attempt context; oracle solve attempts, returns and completions are
separate, and final RHS/query accounting requires exactly3*RHS+21<=30021 with
RHS<=10000. For actual reference mode, guard-read coverage is5424: three bodies
for301/601 retained states plus repeated initial checks across two models.
Internal native ephemeris reads are outside that Python count and not instrumented.

Retain each returned result before timed after-call checks, including raw full
native state/force histories. Preserve dedicated native/oracle returned-failure
arrays and last guard/body operands when validation fails. Store finite partial
JSON, with explicit markers for nonfinite/unsupported operands instead of replacing
scientific data. Native output label/profile/GM/inventory metadata and solver
count/profile/sample metadata are checked before interpretation.

For every node retain signed state differences and norms for native profile,
tighter native/oracle and oracle profile comparisons, with unchanged ADR0137
0.01m/1e-5m/s,0.001m/1e-6m/s gates. Retain both engines' signed B-minus-A vectors
and their signed discrepancy at0.02m/2e-5m/s; equal norms alone cannot pass a wrong
vector sign. Stop at the first failed gate, marking unavailable downstream checks.
At all eight seven-node profiles, record per-source/total direct fields and raw
spacecraft/body operands using oracle force arithmetic, without another state
query. These are explanatory force operands; the independent saved-file audit
must still recalculate them without sharing this force implementation. No new
cross-engine force acceptance tolerance is introduced by recording these fields.

Initial identity is retained as an independent value snapshot, so mutating a
reused provider object cannot hide drift. Compare final runtime/source/resource
identity and original ordered kernels after all comparisons. The runner/test files
are included in the extended identity. Resource/coefficient/build guarantees and
limitations remain those documented in ADR0141.

Only after all numerical/count/identity checks may the runner mark its restricted
component result passed. That is separate from the future offline audit and any
mission claim. Injected providers are labelled injected-test. Report flags always
deny mission accuracy and continuous safety; force omissions and constant2000kg
metadata are explicit. Guard minima are cumulative for the whole study, with
sampled native states/RHS coverage only.

Exclusive output never overwrites an existing artifact. If final serialization /
flush exceeds the budget, rewrite only the still-open reserved artifact as failed,
retain the first error as well as finalization overrun, and record actual observed
elapsed time without retrying science. Filesystem write/flush errors propagate to
the caller: no successful save or valid partial file can be promised on an
unwritable/full filesystem. Unexpected process termination/native crashes are not
transactionally recoverable by this cooperative Python runner.

## Evidence and verification

[37 new tests](../../tests/test_r5_short_coast_runner.py) use injected synthetic
body tables, states, solver returns and clocks, never real native integration or
SPICE body queries. They cover exact call ordering/counts, all profile/state/unit /
GM/sample failures, source hashes, initial/final identities including a mutable
provider, direct signed vectors, retained arrays/body data, first-error preservation,
clock/import baseline and finalization overruns, error/count stops, exclusive output,
fresh-process guards and write failure. The fake fields/trajectories are not R5
scientific evidence; injected mode is asserted explicitly. Existing input/identity
tests exercise the reused boundary, without propagating the reference.

Initial runner checks:28 passed in0.13s. Ruff initially reported eight E402 findings
because the process budget deliberately precedes imports; a narrowly explained
module exemption covers only that rule. Later review added explicit returned-oracle
failure retention, immutable identity comparison, first-error retention, native
labels/nonboolean step and completed-oracle count checks before full verification.
Final runner+input focused result:81 passed in1.44s (37 new+44 prior). No pytest
failure, numerical retry or tolerance/data substitution occurred.

[Full regression](experiments/0142-full-pytest.txt):5132 passed in647.31s, exit0.
Checkout status remained byte-identical throughout the full run; all260 tracked
production/test/example/environment/legacy/experiment files remain identical to
the base revision. Ruff and strict OpenSpec pass; links, finite JSON, digests and
diff were checked. [Checks](experiments/0142-runner-preparation-checks.json) retain
the measured revision, exact sources and verification scope. Full-suite native
call totals were not instrumented; the new37 runner tests use only injected data.
No R5 reference study has been launched; R5.2 remains incomplete.

Prepared SHA256:

- `docs/adr/experiments/0142-short-coast-runner.py`: `a1e6c74d7316d876f05c8d9527170ed633aeef86726dab91da9e2fdce96524ab`.

- `tests/test_r5_short_coast_runner.py`: `f0c6c5c7c0db83c6f52be3d5a4dd84a276442e20f23e0c521f73afb47d4bf332`.

## Consequences and revisit conditions

Next implement a separate zero-native saved-evidence auditor with independent
Decimal force/difference arithmetic and schema/provenance/failure checks. Verify
all preparation before the single R5.3; do not run it merely to debug integration
wiring. Ordinary preparation defects may be fixed with tests without replaying
science. A reference failure needing changed contract/data/gates requires stopping
and pausing automation for the needed user decision. Strict M3/task3.9, finite-burn
mission closure, continuous safety, UI qualification and M4–M6 remain open/deferred.
