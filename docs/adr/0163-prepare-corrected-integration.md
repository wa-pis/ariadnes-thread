# 0163 — Prepare corrected integration and independent audit

Date: 2026-11-09
Decision status: accepted implementation of the unchanged ADR0162 contract.
Implementation: R5.16 complete after the verification recorded below; R5.17 not executed.
Scientific verification: analytic/injected preparation checks pass; real-input convergence and numerical agreement remain unmeasured.
Scope / milestone: M3 R5.16, private A-only integration preparation.
Base revision: `0c8d7b660ceae7a00d53fc0a160d0ead419a2362`, initially clean `dev`, equal to `origin/dev`; new files were uncommitted during verification.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [ADR0162](0162-corrected-real-integration-contract.md), preserving all historical experiments and gates.

## Context and constraints

The user requested implementation, tests, commit and push for R5.16. This does
not authorize the R5.17 real-input experiment. Preparation must exercise genuine
correction dynamics and independently reconstruct saved arithmetic without
repeating R5.3, manufacturing mission corrections or relaxing its tolerances.

The current stage keeps production APIs, environment/dependencies,13-kernel
selection, physical initial data, GMs, time/frame/unit conventions and the
immutable educational model unchanged. Automation remains PAUSED. The missing
historical0148 final identity remains missing; new checks cannot repair it.

## Options considered

- Modify the old oracle or moving probe in place: reject; would change protected
  evidence and obscure the distinction between manufactured and solved q/w.
- Add a production integration/API or replace the ephemeris provider: defer;
  neither is needed for this bounded verification.
- Five private helpers with existing pinned pure arithmetic/identity utilities:
  selected; keeps the candidate, independent reference and saved-data audit
  separate while retaining the approved scope and dependencies.

## Decision and implementation

| Prepared helper | Responsibility |
|---|---|
| [Inputs](experiments/0163-corrected-inputs.py) | Hash-bound metadata, exact initial state/coepochs,301/601 native grids, three covering Type2 records, original13-kernel/GM/guard metadata; no polynomial evaluation. |
| [Integrator](experiments/0163-corrected-integrator.py) | Genuine q'=w,w'=A, TwoSum time, split relative assembly, original normal/tighter DOP853 profiles, guards, shared counters and raw trial/RHS retention. |
| [Reference](experiments/0163-corrected-reference.py) | Actual-q/w Fraction bounds, independent source/polynomial/Decimal force checks, all-body preflight and original source-inclusive gates. |
| [Study](experiments/0163-corrected-study.py) | Future once-only execution, tested-byte binding, live unchanged SPICE wrapper, identity/setup/metadata counters, node reuse, comparisons, selected observations and exclusive finite output/receipts. |
| [Audit](experiments/0163-corrected-audit.py) | Stdlib-only reconstruction of every recorded RHS/output, trials, caps/ledgers, sampled high-precision checks, trajectory comparisons, provenance and partial/finalization outcomes. |

Each helper has a corresponding `tests/test_corrected_*.py` module. The new
loaders execute the checked source bytes; the candidate does not call the old
manufactured correction constructor. The auditor imports neither the candidate
force/assembly nor its controller; a shared pinned pure independent reference
is not a second ephemeris or a second force-reference implementation.

The observer brackets the pinned12-stage trial through an instance callback
wrapper, leaving SciPy's controller/stage arithmetic untouched. It records an
attempt before its first stage, including an unavailable-decision descriptor
if an RHS/guard/deadline error prevents the estimator from returning. Initial
and dense-output callbacks consume RHS/state budgets but are not fabricated
trial stages. Both profiles have exact observed-versus-vanilla t/y/nfev parity
on an artificial circular orbit; controller/coefficient identities match the
retained pinned SciPy source. This is preparation evidence only.

All runtime geometries guard Sun/Moon/Earth before either A force. The future
study reuses one21-call body table, checks14 saved native node states with42
separations and performs normal then tighter with fail-stop. It preserves raw
native returns/solver arrays before post-call checks and never retries a failed
profile. Checked source bytes are the executed bytes, including prebinding the
integrator before import. Inputs/protected bytes, helpers, preparation manifest
and tested sources are checked before/after; current identity cannot complete0148.

The original seven-node0.01m/1e-5m/s native and0.001m/1e-6m/s oracle-profile
gates remain. High-precision qualification is limited to28 predetermined
observations (seven outputs plus first seven completed RHS per profile), with
84 body checks/56 included-source rows/448 Decimal fields/28 A totals. Nonzero
low time in a selected RHS is required per profile. All-RHS binary64 replay is
separate from this sampled source/force qualification; original source floors
remain in the overall force gate without subtraction or allowances.

Future caps remain shared60s/10000 attempted RHS/30021 live state requests/
1000 trial descriptors/20028 binary64 fields; the separate saved-data audit has
its own inclusive10s and zero native/scientific queries or solves. Setup and
metadata APIs have separate counters;30021 is not a total native-call count.
External pre-child timestamps include startup. Exclusive attempt/output/receipt
files and late-finalization downgrades preserve failed prefixes. Injected tests
cannot produce a scientific-verification verdict, even when their checks pass.

## Evidence and verification

The [verification manifest](experiments/0163-verification.json) binds all ten
new helper/test hashes and382 protected historical artifacts/files, including
0162's verification record. The source contract ADR0162 is also unchanged.
The [test receipt](experiments/0163-test-receipt.json) and
[frozen checkout](experiments/0163-checkout-freeze.json) retain the exact base,
commands, byte identities and checkout stability throughout the full suite.

- 301 focused tests pass in17.15s across the five new test modules.
- 6182 full-suite tests pass in672.14s with unchanged checkout bytes/status throughout.
- [Full pytest log](experiments/0163-full-pytest.txt) and
 [Ruff log](experiments/0163-ruff.txt) are retained; Ruff and strict OpenSpec pass.
- Independent fixtures cover3D circular dynamics/nonzero q/w, exact TwoSum/sign/
 source/SI/profile/coepoch/GM/kernel/hash mutations, rounding/ties/subnormals/
 cancellation, force/precision boundaries, every cap and late-return/partial/
 exclusive-output/finalization path.
- An end-to-end artificial circular study passes all28 observations and a separate
 independent saved-data auditor. A deliberately biased artificial source by0.1mm
 passes state parity but fails the unchanged force gate; the independent auditor
 confirms the saved negative result as partial, without downstream fabrication.
- [Metadata-only preflight](experiments/0163-input-preflight.json) validates the
 saved inputs/protected bindings without new polynomial/state/force evaluation,
 scientific imports, kernel setup, propagation or an R5.17 attempt.

The full regression suite includes the existing native component tests. Newly
added tests use artificial sources or read-only retained metadata; they do not
qualify the future real mission solve. No retained R5.17 study/audit, new mission
search, B sensitivity experiment or automation resumption occurred.

## Consequences and revisit conditions

R5.16 preparation is complete; a separately authorized R5.17 may use exactly the
tested helper bytes and frozen inputs/gates/caps. Real convergence, runtime/audit
budget feasibility and native/oracle agreement are still unknown. Any failure
must be retained without replay/tuning and reviewed under a new contract before
changing its assumptions or limits.

No historical R5.3 causality, independent astronomical truth, omitted-force
sensitivity, continuous safety, finite-burn/full-mission feasibility or strict
M3 completion is established. M4-M6/ML/search/UI qualification remain deferred.
