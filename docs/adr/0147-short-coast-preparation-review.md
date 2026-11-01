# 0147 — Review short-coast preparation before reference execution

Date: 2026-11-01
Decision status: accepted bounded preparation review; ADR0137/0143 contracts unchanged.
Implementation: aggregate R5.2/R5.2g preparation reviewed and complete; reference study remains unexecuted.
Scope / milestone: M3 R5.2 aggregate readiness only; no R5.3 reference propagation.
Base revision: `a20cbf052433d1c3d9ad2dbb61437a05e1fac106`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [offline orchestration](0146-offline-audit-orchestration.md).

## Context and constraints

R5.2 units are fixture/component-tested, including5255 full tests at the unchanged
prepared sources. Parent completion still requires an aggregate review. Verify
source pins, fixed inputs, engine independence, native synthetic coverage, evidence
schemas and the remaining once-only execution prerequisites. No new algorithm,
scientific input, gate, kernel selection or dependency is introduced.

## Options considered

- Infer readiness from the latest test count alone: reject; component schemas
  and the runtime/file-check boundary must agree.
- Run the reference as a readiness probe: reject; consumes the once-only study.
- Static review plus one bounded current-runtime snapshot/file-verifier check:
  selected; no body-state or spacecraft-propagation request.

## Decision and rationale

Review ADR0137/0138/0140/0141/0142/0143/0144/0145/0146 and their prepared sources,
tests and immutable receipts. Compose the existing runner identity producer and
independent file verifier in a fresh pinned Python process, under a separate10s
cooperative import/input/identity/hash/output/flush budget. Acquire exactly two
runtime snapshots and require canonical equality, check the original13-kernel
manifest and verify one snapshot against current files using real defaults.
Do not invoke execute/run/solve_model/integrate or any body-state provider.
Runtime import/kernel inventory initialization is allowed; this is neither a
zero-native-import check nor a scientific reference run. Save the invocation,
finite receipt, actual elapsed time and first error without automatic retries.
No checkout mutations during the snapshot pair; write live output outside it.

## Evidence and verification

[The single readiness check](experiments/0147-runtime-file-readiness.json) passed
with two identical snapshots; elapsed sample before flush1.2859516250900924s,
with the post-flush10s deadline check passing. The current-file verifier accepted
43 source files, the native binary,9 module files and5 Conda records. The original
ordered13-kernel manifest matched. This performed scientific imports/kernel
inventory initialization, but no body-state requests or spacecraft propagation.
Git status stayed identical during the pair; the pending new ADR was recorded as
untracked, and all live output stayed outside the checkout. Preserve the exact
[invocation](experiments/0147-readiness-invocation.txt) and
[output](experiments/0147-readiness-output.txt); no retry occurred.

[Review receipt](experiments/0147-preparation-review-checks.json) binds all14
prepared helper/test hashes from seven unit receipts, rehashes all seven passing
full logs and verifies six source/input pin maps. All277 protected tracked files
remain identical to the base. No production, test, environment, kernel or earlier
evidence bytes changed. Preparation added319 tests across the seven units;
[latest full regression](experiments/0146-full-pytest.txt) passed5255 in647.52s.
Reuse it and its Ruff result on exactly these source/test hashes; full pytest,
focused/native synthetic tests and R2 are not repeated in this documentation stage.
Strict OpenSpec, local links, finite JSON, retained digests and diff checks pass.

The reviewed interfaces bind the same initial state/epochs/input bytes and exact
native versus correction-coordinate profile meanings. Source review and retained
analytic tests distinguish separate native RK4/SciPy DOP853 dynamics; shared SPICE
inputs do not establish independent ephemeris truth. Native test coverage includes
actual line/circular/three-source Decimal comparisons and epoch-zero ephemeris
parity, with four synthetic native arcs per native test-file invocation; total
other full-suite native calls remain uninstrumented. Producer/consumer identity
schemas now have a real current-environment compatibility check, beyond fixtures.
Call ledgers, error retention, raw array parity, independently recomputed forces /
signed differences, source/file checks, finite exclusive output and cooperative
budgets are covered in the retained component tests. This is empirical readiness,
not formal verification of all code paths or actual reference agreement.

## Consequences and revisit conditions

R5.2/R5.2g preparation is complete. The next eligible bounded stage is exactly one
ADR0137 reference study in a fresh pinned process and the separate fresh zero-native
ADR0143 audit, using exclusive outputs and unchanged sources/data/gates. Do not
prewarm that process or replay synthetic/reference trajectories as another readiness
probe. Retain the measured revision and failure data; no fifth native/oracle call,
repeat study, changed tolerance or force substitution is authorized. The actual
study/audit results remain unmeasured. A readiness pass cannot assert actual
reference numerical agreement, Earth-force sensitivity or historical-memory truth.
Strict M3/task3.9, whole-mission accuracy, finite burns and continuous safety remain
open. Ordinary preparation defects require checked fixes; changed scientific
inputs/gates or required user action must pause automation.
