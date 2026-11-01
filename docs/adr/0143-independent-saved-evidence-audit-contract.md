# 0143 — Define the independent saved-evidence audit

Date: 2026-11-01
Decision status: accepted bounded preparation design; ADR0137 physics and gates unchanged.
Implementation: design verified; auditor implementation/tests not started; R5.2 incomplete.
Scope / milestone: M3 R5.2f, private zero-native post-processing, no reference run.
Base revision: `5b5266798e1004546deabc01c8f4fd2dee521720`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements the audit obligation of [ADR0137](0137-short-coast-earth-gravity-contract.md), following [verified orchestration](0142-short-coast-orchestration-and-evidence.md).

## Context and constraints

The runner now passes5132 full tests. Its explanatory node forces use the oracle
force function; its passed flag alone is not an independent audit. Saved native
samples also contain actual acceleration telemetry, distinct from those explanatory
fields. An offline auditor must check the operands and both outputs without
importing the runner, adapters, production package or scientific libraries.
No new search, propagation, dependency, kernel load or scientific experiment.
This is the interface/arithmetic design step before implementation, not R5.2 completion.

## Options considered

- Reuse runner comparison/force functions: reject; a common arithmetic mistake
  could validate itself and native telemetry would remain unchecked.
- Replay ephemerides or integration: reject; violates the zero-native audit role
  and confuses saved-data consistency with independent physical observations.
- One stdlib-only private auditor, independent Decimal arithmetic and explicit
  saved-file provenance checks: selected; no generic validation framework.

## Decision and rationale

### Input and result boundary

Implement a single private `0144-short-coast-audit.py` with read-only
`audit_file(path)` and exclusive-output `execute(input_path, output_path)`.
No public package/CLI/UI change. Parse duplicate JSON keys, nonfinite constants,
boolean numbers, wrong vector shapes and numeric epoch-key collisions as errors.
Do not execute or import code named by the evidence. A fresh-process check shall
prove no NumPy/SciPy/SpiceyPy/TudatPy/space_nav import, no body query and no propagation.

For complete success require adapter_mode=reference, the frozen ADR0137 identity /
units/omissions/mass labels, exact four input hashes, complete scenario/candidate /
initial boundary equality against the immutable files, seven epochs and initial
six-state, all eight profiles,56 force rows,14 numerical rows and seven signed
model rows. Synthetic test fixtures may exercise the validator's internal
arithmetic/schema functions, but injected-test evidence must never verify R5.
Successful file audit must bind actual frozen inputs; tests may not bypass this
entry-point check by relabelling injected data as reference.

Use three audit outcomes: passed (complete evidence verified), partial (a declared
failed study, available checks only), rejected (malformed, inconsistent or falsely
successful evidence). Report source-study status and study_verified separately;
only passed+source passed may set study_verified=true. Never promote partial
output. An expected false numerical gate in a failed study is retained as false;
it is not itself evidence corruption. Missing downstream data are unavailable.
Nonfinite markers may be retained as failed operands but cannot enter arithmetic.

### Independent arithmetic without changing physical gates

Convert saved finite binary64 operands with Decimal.from_float, not decimal text
rounding. Compute direct inertial point gravity independently as
`mu*delta/(sum(delta^2)*sqrt(sum(delta^2)))` in local80-digit and100-digit contexts.
Require the two force calculations to agree within relative1e-60 in vector norm
(zero must remain zero); retain their signed component discrepancies. This checks
arithmetic stability, not the integration error or physical model completeness.

Compare saved per-source fields and native node telemetry to the100-digit result
using the already established [ADR0132](0132-gravity-screening-preparation.md)
force-arithmetic envelope max(1e-15m/s^2,1e-11 times the reference vector norm).
For a total use the sum of individual reference norms as its scale, preserving
cancellation; also check native total/source consistency within its existing
1e-12m/s^2 gate. These are saved-force consistency checks only. They do not alter
any position, velocity, sensitivity or mission gate. Reject indirect-origin terms,
wrong source lists, signs, units and mismatched body epochs/frames before arithmetic.
The selected envelope is an empirical arithmetic check, not a rigorous bound.

For signed state differences independently subtract the exact saved operands in
Decimal and require their correctly rounded binary64 components to match saved
components exactly. For sensitivity compare B-minus-A, then oracle-minus-native
using the retained rounded intermediate vectors, rather than silently changing
the runner's floating-point expression tree. Decimal norm cross-checks admit at
most four binary64 ULPs for square-root/rounding differences; saved gate booleans
must separately equal a direct binary64 replay at the unchanged thresholds.
Record discrepancies and boundary-sensitive rounding; an arithmetic envelope
never enlarges a scientific pass threshold. Check native profile/native-oracle
0.01m/1e-5m/s, oracle profile0.001m/1e-6m/s and signed sensitivity0.02m/2e-5m/s.
Do not compare only norms or accept a caller's precomputed pass flag.

### Bind raw arrays, identities, calls and coverage

At native nodes read both the sample acceleration vector and raw dependent
history in force_order=(total,Sun,Moon[,Earth]); require equality. All retained
state/force history keys must match the exact1s/0.5s grid,301/601 entries, initial
state and successful completion; node samples must equal their raw entries.
At unsaved body epochs check finite raw fields, history/profile consistency and
source sums only: direct-force recomputation is limited to the seven body-table
nodes. Oracle arrays must contain the seven fixed offsets, zero initial correction,
matching reconstructed states and fixed profile labels. Reconstruct with separately
written arithmetic and explicit binary64 product/rounding semantics.

Recompute request order and attempt/return/completion ledgers from available call
and profile records. Enforce four native/four oracle, total RHS<=10000,
Python state reads=3*RHS+21<=30021, native guard reads5424 on complete evidence,
and0<=ordered call intervals<60s plus the recorded successful flush/time gate.
The saved flush flag is a historical assertion: no offline audit can remeasure
that already completed flush or establish a trustworthy clock from JSON alone.
Check per-oracle nfev/count increments and cumulative guards above frozen radii;
report that native internal SPICE reads and unsaved RHS trajectories cannot be
independently recounted. Do not assert continuous safety from sampled minima.

Require before/after identity equality, pinned version/build/profile metadata,
the original ordered13-kernel manifest and the required source-path inventory.
Rehash saved source paths confined to the checkout and declared module/native /
Conda metadata files within the pinned environment; reject missing or altered files
without loading them. Compare saved coefficient/callable hashes and shapes across
snapshots; do not claim to recover historical loaded objects from source hashes.
Kernel manifests have names/hashes, not retained absolute file paths: check their
exact equality to R1, without a new kernel-pool query or claiming fresh kernel-byte
or independent ephemeris verification. Current source/binary rehashes and saved
snapshot consistency are different claims and must be labelled separately.
Record the auditor's own source/evidence SHA256 and actual measured revision.

### Bounded preparation and later audit

Implement/test with hand-built analytic/Decimal fixtures and copied/mutated saved
schemas only; never call a real integrator to generate auditor fixtures. Cover
3D signs/cancellation, zero force, exact/adjacent gate boundaries, corrupted raw
arrays/forces/corrections/labels/identities/counters and partial/overrun evidence.
Run focused/full pytest, Ruff and strict OpenSpec before R5.2 completion. Preserve
all existing artifacts and keep the checkout frozen during the full suite.

The later offline audit gets a separate10s cooperative process/import/read/hash /
compute/serialization/flush budget, zero native calls and exclusive finite output.
An audit timeout or I/O failure cannot verify the study; preserve the diagnostic
without rerunning its trajectories. Preparation may fix ordinary parser/arithmetic
bugs with tests; reference failure requiring changed physical inputs/gates still
requires the user's decision and pausing automation under ADR0137.

## Consequences and revisit conditions

This closes the design ambiguity between checking saved arithmetic and replaying
physics. Implementation remains required before the one reference experiment.
Even passed audit verifies saved-node consistency, not every unsaved integration
stage, actual historical kernel memory, independent ephemeris truth, complete
forces, mission accuracy, escape/capture, finite burns or safety. Strict M3/task3.9
and all deferred milestones remain open. No retry or relaxed tolerance is authorized.

## Evidence and verification

[Static review](experiments/0143-offline-audit-design-checks.json) binds the five
reviewed source hashes and clean base. ADR0142 has56 explanatory node-force rows;
native validate_history retains total/source accelerations in each sampled state
and full raw histories; oracle integrate_corrections retains raw corrections /
offsets/nfev. ADR0141 identities include source, module/build/binary and coefficient
snapshots. Existing ADR0132 supplies the retained force-arithmetic envelope.

All264 tracked protected code/test/example/environment/legacy/experiment files
remain unchanged. New native imports/queries/propagations/reference executions:0.
This stage changes documentation only: full pytest/Ruff are not rerun on unchanged
code; reuse [5132 passing tests](experiments/0142-full-pytest.txt), measured at the
base revision with runner/tests untracked as recorded in ADR0142. Local links,
source/input digests, finite JSON, whitespace/diff and strict OpenSpec pass.
