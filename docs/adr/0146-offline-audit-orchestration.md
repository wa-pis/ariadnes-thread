# 0146 — Complete offline audit orchestration preparation

Date: 2026-11-01
Decision status: accepted bounded implementation under ADR0143; scientific gates unchanged.
Implementation: R5.2g.3 implemented;32 new/160 focused and5255 full tests pass. Final R5.2 preparation review remains open.
Scope / milestone: M3 R5 saved-evidence audit preparation; no reference propagation.
Base revision: `bf71dd62a01faecd8f957b233e024777e5b3524a`, initially clean; new helper/tests untracked during checks.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; completes orchestration described in [ADR0143](0143-independent-saved-evidence-audit-contract.md), composing [0144](0144-independent-saved-node-arithmetic.md) and [0145](0145-independent-evidence-input-and-file-identity.md).

## Context and constraints

Arithmetic and file-identity helpers are independently tested but cannot alone
validate complete study evidence. The final private orchestrator must connect their
checks, stop invalid downstream evidence and distinguish complete, partial and
rejected outcomes. This is the last implementation unit before the aggregate R5.2
review. Neither this record nor its fixture tests authorize an unreviewed R5.3 run.
No production, environment, input, kernel, dependency or earlier helper change.

## Options considered

- Import runner validators or scientific adapters: reject; would share the logic
  being checked and violate the zero-native offline boundary.
- Rewrite the retained0144/0145 files into one script: reject; changes immutable
  prepared identities and duplicates verification work.
- Compose two exact hash-bound stdlib helpers in one private entry point:
  selected; preserves their evidence and avoids a general validation framework.

## Decision and rationale

[0146-audit-short-coast.py](experiments/0146-audit-short-coast.py) supplies
read-only audit_file(path) and exclusive execute(input_path, output_path), using
only stdlib and the two pinned offline helpers. ADR0143's original0144 entry-point
filename is realized by this composition;0144 remains the immutable arithmetic
core. No public API, CLI, UI or propagation implementation changes.

Validate restricted physical labels, exact frozen input bundle, ordered seven-node
body operands, model/source inventories, all eight native/oracle raw profiles,
56 node-force rows,14 numerical comparisons and seven signed-model rows. Reuse
independent Decimal arithmetic, exact saved component differences, raw-array parity
and unchanged scientific gate replay. Compare signed B-minus-A and then
oracle-minus-native with the retained rounded intermediates. False gates are
allowed only on the final available row of a declared failed study; B requires
all four A profiles and all seven passed A numerical rows.

Reconcile the32 ordered complete call records with saved profile/body returns,
four native/four oracle limits, per-oracle nfev and cumulative before/after counts,
RHS<=10000, Python body reads=3*RHS+21<=30021 and5424 saved-state native guard
reads on complete evidence. Check finite ordered recorded times below60s and
cumulative saved minima above frozen body radii. These remain saved assertions:
unsaved native reads/RHS states and historical timing cannot be replayed offline.

Require current-file identity checks plus initial/final snapshot equality for a
complete reference audit. An injected clock never grants study_verified=true;
injected-test source evidence is rejected at the file boundary. Relabelling toy
fixtures as reference still fails independently reconstructed frozen inputs.
The pure fixture checker always returns study_verified=false. A partial failed
study retains available arithmetic and false gates; invalid failed-profile operands
are labelled unavailable, never promoted. Inconsistent evidence is rejected.

Capture process start before remaining imports; enforce the separate cooperative
10s budget across reads, hashes, arithmetic, output and flush. Require a fresh
process without scientific modules for reference use. Save finite JSON to a newly
reserved output only. A late flush overrun revokes success, preserves a first error
and rewrites only that newly owned output. I/O errors propagate; there is no crash
recovery guarantee or hard interruption of blocked I/O. Record own/helper/evidence
hashes and actual Git revision, without importing evidence-specified code.

## Evidence and verification

[32 new tests](../../tests/test_r5_short_coast_offline.py) use static hand-built
arrays and malformed/partial JSON, never a reference trajectory or integrator.
They cover complete fixture wiring, three-dimensional signed sensitivity, wrong
signs with equal norms, force/raw-array corruption, labels, gates, count/return /
call-order/timing drift, cumulative minima and nfev reconciliation. Declared failed
numerical/profile cases retain partial diagnostics and prohibit downstream B.
File checks cover forged reference labels, bad JSON, missing paths, expired clocks,
helper drift, invalid snapshots, finite diagnostics, write failures and late flush.
A real fresh subprocess executes only a failed-setup fixture, verifies no scientific
modules and proves exclusive output leaves existing bytes untouched.

Focused results:32 passed in0.35s; all four offline/runner units160 passed in1.05s.
[Full regression](experiments/0146-full-pytest.txt):5255 passed in647.52s, exit0.
Ruff and strict OpenSpec pass. [Check manifest](experiments/0146-offline-preparation-checks.json)
retains exact source/log hashes and scope. Git status was byte-identical throughout
the full run; all273 tracked protected code/test/example/environment/legacy /
experiment files match the base. Local links, finite JSON, digests and diff pass.
No failed focused/full run or scientific retry occurred in this stage. New tests
import/query/propagate no native science; full-suite native totals are uninstrumented.
A complete reference-file verdict has not been exercised and is not claimed.

Prepared source SHA256:

- `docs/adr/experiments/0146-audit-short-coast.py`: `074886270d1a602dd9f7ffddb02f5e43bf75af77a72bde06fdd0057d1b23ee92`.

- `tests/test_r5_short_coast_offline.py`: `cbaaa9586448bf225ac54cb040d5eeed1298fe5b8c907cd7793c5666e0c1d9f1`.

## Consequences and revisit conditions

The private auditor is implemented and fixture-tested. Review all R5.2 units,
entry-point/source identities, actual native test coverage and run prerequisites
before closing R5.2/R5.2g and attempting the once-only R5.3 contract. No more audit
implementation split is planned. Ordinary preparation defects may be fixed with
checks; changed scientific inputs/gates or failed reference science still require
the user's decision and automation pause. No Earth-force sensitivity result,
whole-mission accuracy, escape/capture, finite burn, continuous safety or strict
M3/task3.9 closure follows from these tests. Deferred milestones remain deferred.
