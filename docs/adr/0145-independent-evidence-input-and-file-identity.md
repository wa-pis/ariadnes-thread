# 0145 — Implement independent evidence input and file identity

Date: 2026-11-01
Decision status: accepted bounded preparation unit under ADR0143; scientific contract unchanged.
Implementation: R5.2g.2 file/input identity helpers implemented;39 new/128 focused and5223 full tests pass. Complete auditor remains partial.
Scope / milestone: M3 R5 saved-file preparation; zero native imports, body queries or propagation in the new unit.
Base revision: `ba738f332a13a7679d41ecbac6c2f4f6a7fefc8f`, initially clean; new helper/tests untracked during verification.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [arithmetic unit](0144-independent-saved-node-arithmetic.md) under [ADR0143](0143-independent-saved-evidence-audit-contract.md).

## Context and constraints

The remaining auditor must bind its input/runtime assertions to retained sources
without importing the numerical engines or accepting their input validator as its
own oracle. This unit completes that boundary independently. One final orchestration
unit remains: comparison/call/count ledgers, outcome/partial semantics, bounded
exclusive output and the complete private audit entry point. R5.2g/R5.2 remain open.
No code/environment/legacy/input/kernel change, new dependency or reference study.

## Options considered

- Import the prepared runtime identity provider: reject; loads scientific libraries
  and queries kernel inventory, violating the offline role.
- Trust recorded hashes or use Python equality for typed JSON values: reject;
  would miss current-file drift or boolean-versus-number substitutions.
- Stdlib-only frozen-file reconstruction, strict JSON and bounded streaming hashes:
  selected; read-only operations and explicit proof limitations.

## Decision and rationale

[Helper](experiments/0145-short-coast-evidence.py) imports only stdlib. It has no
CLI/audit_file/execute, no reference-verdict API and no scientific adapter import.
Existing prepared numerical/arithmetic helpers remain immutable; the future private
orchestrator composes these two separately hash-bound offline preparation units.
This preserves historical source identities instead of editing retained helpers.

Reject duplicate JSON keys at every object depth, nonfinite constants, exponent
overflow to infinity and non-object roots. Preserve explicit failed-value markers
as objects/strings and flags as booleans; they are not scientific numeric operands.
Canonical comparisons sort object keys but preserve JSON number/boolean and
integer/float distinctions. This is wire identity, not a unit/time transformation.

Independently hash-bind0119/0098/0133/0136 bytes, extract the unchanged scenario,
candidate, initial boundary, exact six-state/epoch and seven nodes, original ordered
kernels and SI/SSB/J2000 labels. The resulting wire bundle matches the existing
ADR0141 loader in a separate comparison test, without importing that loader in the
new helper. No native ephemeris or trajectory is acquired.

Saved snapshots must have the actual pinned field/source/import/module/build /
coefficient/callable inventories and versions. Require a40-digit Git revision,
string dirty-status entries, complete ordered13-kernel manifest, six immutable
prepared-source hashes and all four frozen input hashes. All declared checkout
sources are rehashed; source paths cannot escape the checkout. Declared native,
module and callable files must resolve within the pinned environment before any
read, including symlink resolution. Rehash declared files, bind callable source
paths/roles to their recorded modules, and verify five complete Conda records /
metadata digests/path roles against current JSON. Check copied coefficient shapes,
float64 labels and hash syntax, without executing code or recovering arrays.

Snapshot equality and current-byte checks are separate. The helper's result always
sets reference_study_verified=false and historical_loaded_memory_verified=false.
It verifies declared file bytes and saved metadata, not that the historical process
loaded every declared object, not all transitive libraries, distribution authenticity
or trusted execution. Coefficient/code object digests remain recorded assertions;
comparison between before/after snapshots is required by the later orchestrator.
Kernel manifests are compared to hash-bound R1, with no current kernel-byte/pool
read and no independent ephemeris-truth claim. Import paths are checked as paths;
source/native/module digest coverage is explicitly enumerated in the result.

All read/hash operations accept the future cooperative deadline callback; streaming
hashes check between1MiB chunks and before/after I/O, JSON checks bracket read and
parse. This is not a new standalone timer or a hard interrupt for blocked I/O.
The final auditor still must enforce ADR0143's separate10s process-inclusive budget,
finite exclusive output and rejected/partial/passed outcomes. Test-only alternate
checkout/prefix paths cannot authorize a reference verdict.

## Evidence and verification

[39 new tests](../../tests/test_r5_short_coast_evidence.py) use original immutable
JSON plus copied checkout files and unexecuted temporary module/native/Conda-file
fixtures. Fake file contents are never imported or represented as a verified
runtime. Cover malformed/duplicate/nonfinite JSON, typed identity distinctions,
frozen byte drift, exact prepared-loader wire parity, lazy fresh-process imports,
before-read/inter-chunk deadline failures, source/prepared-pin/module/native /
Conda/metadata-path/shape/callable/kernel/revision/import drift and path/symlink
escape. Snapshot comparison detects recorded in-memory coefficient digest drift
without claiming it recomputes the historical array.

Initial new-unit result:39 passed in0.52s. Final file+arithmetic+runner result:
128 passed in0.74s (39 new+52 arithmetic+37 runner). Ruff and strict OpenSpec pass.
No focused failure or scientific execution occurred.
[Full regression](experiments/0145-full-pytest.txt):5223 passed in650.56s, exit0.
[Checks](experiments/0145-file-preparation-checks.json) retain exact source/log
hashes and measured scope. Checkout status was byte-identical during the full
run; all269 protected tracked code/test/example/environment/legacy/experiment
files remain identical to the base. Ruff/strict OpenSpec, local links, finite JSON,
source/log digests and diff checks pass. No failed runtime test or scientific retry.
Full-suite native call totals were not instrumented; only the new39 tests are
asserted to acquire no native imports/body queries/propagations.

Prepared source SHA256:

- `docs/adr/experiments/0145-short-coast-evidence.py`: `426fe4e0abe9b9dfcf6380d09e86e8dbf5748f66875f74b26b45dceb6ba5da14`.

- `tests/test_r5_short_coast_evidence.py`: `23bfbdc158f3938a76388f9d04f1b341e1fa26aaf90cf40683428dc465ed6bd1`.

## Consequences and revisit conditions

Next implement the one remaining private orchestrator using the verified arithmetic
and file helpers; verify complete/partial/rejected ledgers, saved signed comparisons,
counts/times and exclusive10s output before full R5.2 review/reference use. No new
scientific propagation is authorized by this helper stage. A complete file audit
and empirical Earth-gravity sensitivity remain unmeasured. Mission accuracy,
finite burns, continuous safety, strict M3/task3.9 and deferred milestones remain
open. Ordinary preparation fixes need tests; changed scientific inputs/gates still
require the user decision and automation pause under ADR0137.
