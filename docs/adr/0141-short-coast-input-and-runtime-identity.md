# 0141 — Bind R5 inputs and extend the runtime identity

Date: 2026-11-01
Decision status: accepted preparation unit under ADR0137; scientific contract unchanged.
Implementation: R5.2d input/identity helpers and44 tests implemented;130 focused and5095 full tests, Ruff and strict OpenSpec pass.
Scope / milestone: M3 private data/provenance preparation, no R5 execution.
Base revision: `31edb278d9c0bf18f09aafe144bec239d1218069`, initially clean; new helper/tests untracked during verification.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [ADR0137](0137-short-coast-earth-gravity-contract.md), [oracle](0138-independent-short-coast-oracle.md) and [native adapter](0140-native-short-coast-adapter.md).

## Context and constraints

The remaining shared runner must bind frozen data and record actual imported
solver/coefficient/build identities before interpreting engine agreement. Complete
this bounded reusable portion first, rather than duplicating R2 provenance code
inside a large unverified runner. This unit does not run either propagation engine,
query body states, calculate forces, change inputs or implement the offline audit.
No new dependency, public API, production code or scientific gate changes.

## Options considered

- Rely on version labels alone: reject; loaded files, aliases and coefficient
  tables can differ while labels remain the same.
- Duplicate the complete existing native/kernel identity code: reject.
- Reuse hash-pinned R2 input/identity utilities, extending them only for R5's
  physical boundary and SciPy/NumPy solver provenance: selected.

## Decision and rationale

[Helper](experiments/0141-short-coast-inputs.py) loads immutable R2 utilities only
after checking their prepared digest. Module import and frozen-input loading
require stdlib only. Before native imports, load exactly ADR0137's four JSON
records by SHA256 and verify prepared oracle/native source hashes. Validate the
retained R1 reference using existing code, complete scenario/candidate equality
with0098, passed R3/R4 prerequisite/finalization status and R4's input digests.

Keep the original departure-ignition boundary unchanged: check label, SSB/J2000,
exact TDB/UTC and six-state against ADR0137, including finite nonboolean numbers.
Return original complete scenario/candidate/boundary data, SI/time/frame labels,
seven exact nodes and original ordered13-kernel manifest. The state is read from
the record, not rebuilt from an orbit or assigned as a scenario default. A loader
hash failure stops before parsing that record. This validates configured inputs;
it does not turn the historical failed physical trajectory into a valid mission.

Reuse the existing native identity: pinned versions, checkout imports, Tudat
binary/Conda/resource metadata, source digests, Git revision/dirty status and
kernel manifest. Add actual NumPy/SciPy/SpiceyPy module-file paths and hashes,
NumPy compiled core/linalg binaries, source files for solve_ivp/RK/DOP853 tables,
and complete existing Conda build metadata/digests for NumPy/SciPy/SpiceyPy.
All added imported files must resolve inside the active Conda prefix; actual
module versions must match the pinned identities. Additional runner/auditor files
can be included explicitly, only inside the checkout. The runner will still have
to compare initial/final snapshots and the original ordered kernel manifest.

Check solve_ivp alias binding and DOP853 registry/class binding; enforce stage
count12, extended16, interpolation power7 and method/error-estimator orders8/7.
Record six finite float64 coefficient tables' shapes and value-byte hashes and
check loaded class slices, including dense-output stages, against those tables.
Record Python code/source identities for solve_ivp, rk_step and selected DOP853
step/error/dense-output functions. Bytecode hashes use the installed Python's
marshal format and are local-runtime provenance, not a portable standard.

These snapshots establish reproducibility operands and detect recorded drift;
they are not a security attestation of an initially trusted distribution, proof
of every loaded Python object's identity or all transitive native shared-library
contents. Package-build metadata and the explicitly listed compiled modules are
retained; no complete runtime-memory or system-library inventory is claimed.
Cooperative checks occur around acquisition. Shared60s accounting, finalization,
call ordering/counts and exclusive partial-evidence serialization remain runner work.

## Evidence and verification

[44 tests](../../tests/test_r5_short_coast_inputs.py) cover exact real frozen data,
no scientific imports during loading, all four data/source hash guards, complete
scenario/candidate/prerequisite/boundary/frame/epoch/state drift, boolean rejection,
and deadline-before-import behavior. A real before/after identity pair is stable
and its kernel manifest matches R1 exactly. Other tests inject actual module
version/path, solver alias/registry, class/table/shape/type/domain/order and build
metadata changes, check coefficient-value drift in snapshots and source scope.
Existing R2 utility tests verify reused behavior without replaying R2's study.

Initial new checks:42 passed in1.43s. Ruff found one unused test import, removed.
Inspection of the installed RK source supplied explicit C/A dense-stage slices
before checking them; no numerical experiment or tolerance change occurred.
After adding shape/order coverage, final focused result is130 passed in2.14s:
44 new and86 existing R2 tests. Ruff passes. The new real identity test performs
metadata/kernel inventory acquisition only, no body-state query or propagation;
initial pool setup may load the existing pinned kernels, subsequent snapshots
reuse the loaded pool. Existing full-suite native counts are not instrumented.

Full regression passed5095 tests in661.07s, exit0. Git status was byte-identical
before/after; all256 previously tracked protected code/test/example/environment/
legacy/experiment files match the base byte-for-byte. See the
[actual full log](experiments/0141-full-pytest.txt) and
[check summary](experiments/0141-input-identity-preparation-checks.json) for exact
source/log digests and native scope. Strict OpenSpec and Ruff pass. Final prose
updates leave verified runtime sources unchanged; pytest is not repeated for
documentation-only edits. No R5 reference study has been launched.

Prepared SHA256:

- `docs/adr/experiments/0141-short-coast-inputs.py`: `4457d9094afe3e8b674a46704b6789fdd724469cb8e1efe5cc054ce39d34c37c`.

- `tests/test_r5_short_coast_inputs.py`: `998d9f09c84c24a242584dd45c4e00f8d8c4b857d9a3b5052567aed9c182a5cc`.

## Consequences and revisit conditions

R5.2 remains incomplete. Next implement bounded orchestration/evidence handling
using these helpers and the verified adapters, then an independent zero-native
offline audit and associated tests before the single R5.3. No native R5 solve,
new candidate/control, optimizer, UI qualification or full-mission claim. Numerical
agreement, model sensitivity and continuous safety remain separate; strict M3 /
task3.9 and M4–M6 gates are not closed by provenance checks.
