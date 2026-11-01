# 0152 — Validate compensated time and relative assembly on the synthetic fixture

Date: 2026-11-01
Decision status: accepted under the user's instruction to check the compensation candidate.
Implementation: private candidate,34 focused/5319 full tests and one retained synthetic demonstration complete.
Scientific status: combined compensation verified on the10s constant-velocity fixture only; no real-SPICE/R5 fix claim.
Scope / milestone: M3 R5 numerical preparation, synthetic constant-velocity source only.
Base revision: `f3931346746b5245bb5400e85a2bda99dbb901b6`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [ADR0151](0151-frozen-stage-error-attribution.md), preserves all previous reference/helper/evidence files.

## Context and constraints

The frozen-stage analysis shows timestamp noise alone raises the first synthetic
error norm above1. It does not show how a corrected adaptive solve behaves. The
user authorized checking the next candidate. Preserve the original10s translating
one-body initial state, epoch, constants, normal settings and analytic/force gates.
Keep production/R5 adapters and stack unchanged. No real-body query or R5 replay.

## Options considered

- Change tolerances, raise caps or rerun the failed R5: reject.
- Evaluate the body at precise local time directly: reject for this test; bypasses
  the scalar binary64 source epoch boundary being investigated.
- Reconstruct exact source coordinates from its internal linear model: reject as
  an adapter fix; plain binary64 provider positions have already lost those bits.
- Rephase the returned source using its velocity and compensated relative assembly:
  selected for this constant-velocity synthetic validation, not yet real SPICE use.

## Decision and fixed synthetic contract

Use an error-free binary64 TwoSum(t0,s) pair hi+lo, where hi=float(t0+s) and
lo=exact(t0+s)-hi, the opposite sign to the old logged clock residual. Evaluate
the synthetic provider at hi: B_hat[j]=fsum(B0[j],V[j]*(hi-t0)), returning plain
binary64 positions and constant V. Do not expose/recover provider internals across
this boundary. Assemble the separation directly as
fsum(B_hat[j],-x0[j],-v0[j]*s,-q[j],V[j]*lo), then the unchanged point field.
This changes timestamp treatment AND geometry assembly; call it a combined
compensated-time/relative-assembly candidate. It retains the provider's absolute
position rounding floor. Ordinary binary64 arithmetic drives integration; Decimal
is used only for independent checks and inherited diagnostic references.

The new private0152 helper SHALL hash-check and load an isolated immutable0150
helper, replacing only that instance's private field binding and restoring it in
finally. Reuse its controller, original rtol1e-12/atol(1e-7m x3,1e-10m/s x3),
first_step1s/max_step5s, trial/RHS/analytic tracing. External mode is compensated;
legacy internal mode is only adapter plumbing. Retain raw epoch residual,
applied low-time correction, rounded provider state, relative separation, actual
force and correction state. Partial adapter calls can outnumber inherited RHS
records; retain both, reconciling equality only after complete success.

Before retained execution verify exact TwoSum identity with independent Decimal
at fractional/integer/tie/sub-ULP/neighbor times, correction sign and wrong-sign
mutation, invalid/nonfinite/singular inputs, pinned immutable-source isolation,
independent Decimal force at returned geometry and local relative reference with
the original envelope, solver analytic gates and exact candidate traced/vanilla
final t/q/nfev parity, partial cap/deadline and fresh/exclusive/finite output.
The body-position floor means no1e-14m/s^2 relative-field or exact37-RHS parity
claim. Run focused/full pytest, Ruff, strict OpenSpec, links/hashes/diff/protected
files. Freeze checkout mutations during full pytest. Tests use separate bounded
fixtures; they do not repeat the retained demonstration or R5 experiment.

Only then execute one fresh10s candidate, with<=3000 completed RHS,<=300 retained
trial rows and a shared10s cooperative process/import/read/compute/JSON/flush
budget. Compare against retained0150 baselines without reintegrating them.
Required scientific checks: finish10s, every retained force satisfies the original
max(1e-15m/s^2,1e-11*reference magnitude) envelope, every accepted endpoint passes
1e-6m/1e-8m/s analytic gates, and the common final endpoint differs from retained
relative control by<=1e-6m/1e-8m/s. Separately predeclare first attempted trial
accepted and>=10x fewer RHS than2413 (integer RHS<=241) as behavioral/efficiency
targets; never confuse them with accuracy gates or tune after a negative result.
Retain finite exclusive partial evidence on cap/error, no automatic retry or
changed budget/profile/gate. A separate stdlib-only saved-data audit may check
all retained candidate rows under5s, at most6000 Decimal field evaluations, no
source query/integration/import of scientific libraries, with its own exclusive
finite evidence. This validates recorded operands/gates without another solve. Report source/runtime/baseline identities and all
available failures. Keep automationPAUSED.

## Consequences and revisit conditions

Passing would validate the combined candidate only for the linear synthetic
fixture, and show an actual corrected solve rather than frozen-stage attribution.
It would not identify historical R5 rejection history, authorize a real-state fix
or validate Earth sensitivity, complete forces, full mission accuracy or safety.
Real ephemerides require a separate velocity/position-consistency and Taylor-
remainder/error contract, compensated-coordinate checks and native-call budget.
No package API, production propagation or mission input changes here.

## Evidence and verification

The [private helper](experiments/0152-compensated-time-diagnostic.py) loads the
hash-pinned immutable0150 controller in isolated instances. [34 focused tests](experiments/0152-focused-pytest.txt)
pass in1.01s; [5319 full tests](experiments/0152-full-pytest.txt) pass in664.28s.
Checkout status is unchanged throughout the full run. Ruff and strict OpenSpec
pass. [Verification](experiments/0152-verification.json) binds tested new-source
hashes, baseline identity, raw logs and304 previously tracked protected files,
all unchanged fromf393134. Application/environment/legacy and prior experiment
sources remain unchanged; full tests include existing native coverage, while new
candidate tests and demonstration perform no SPICE/Tudat operations.

Independent review caught and preparation fixed two retention errors before full
verification: an exception after assigning passed now resets the report to partial;
post-return adapter reconciliation failure retains the returned case/geometry and
marks it failed. Captured-engine tests check actual field-binding restoration.
Arithmetic tests include200-digit exact TwoSum sums at fractional/tie/sub-ULP/
neighbor times, opposite-sign mutation,80/100-digit independent geometry/relative
fields, a3D correction, source-floor retention and immutable-source hash rejection.
Candidate observed/vanilla final t/q/nfev match exactly in the deterministic test.

One [exact invocation](experiments/0152-compensated-invocation.txt) produces the
[raw candidate trace](experiments/0152-compensated-trace.json) and
[output](experiments/0152-compensated-output.txt). It finishes10s in
0.3457699166610837s before flush, with finalization passed:61 completed RHS,
61 returned geometry records,5 accepted trials and0 rejected. Baselines are read
from saved0150, not re-integrated. Zero SPICE queries/Tudat propagations/R5 replays.

| Metric | Saved rounded-time baseline | New combined candidate |
| --- | ---: | ---: |
| Completed RHS | 2413 | 61 |
| Accepted / rejected trials | 137 /64 | 5 /0 |
| First trial error norm | 15.7339437463 | 0.0105768519 |
| All retained force gates | fail | pass |
| All accepted analytic gates | pass | pass |

RHS reduction2413/61=39.557377049180324 exceeds the predeclared10x target;
first-trial acceptance and RHS<=241 both pass. These are efficiency/behavior
observations, not an accuracy improvement factor or wall-clock speedup claim.
Maximum accepted analytic errors are7.994318246131494e-11m and
3.230265769342626e-11m/s, below the unchanged1e-6m/1e-8m/s gates. The common
final endpoint differs from the saved relative control by6.899486159856413e-12m
and2.027702143530707e-11m/s. These tiny discrepancies describe a synthetic
numerical check, not achievable knowledge of a real spacecraft state.

A separate [stdlib-only saved-data invocation](experiments/0152-saved-audit-invocation.txt)
[passes](experiments/0152-saved-audit.json) in0.024034792091697454s before flush,
finalization passed:61 paired RHS/geometry rows,122 fields at100 Decimal digits,
all exact two-part epochs/correction signs/provider positions/relative separations,
force envelopes, five norm/accepted-state checks and final-control/efficiency
arithmetic. Its [output](experiments/0152-saved-audit-output.txt) is retained.
It confirms source-position rounding is actually present; maximum relative field
discrepancy5.854916557400376e-12m/s^2 remains inside the original envelope.
A separate read-only review independently confirms these operands and outcomes.
A logged h=5.000000000000001s follows floating t_new-t recomputation; the pinned
max_step setting remains5s. This is an arithmetic detail, not a relaxed setting.

No tolerance/profile/input/cap tuning or candidate retry occurred. Retained output,
tests, hashes, local links, finite JSON, diff and strict OpenSpec pass. Automation
remainsPAUSED; real-state physics/source changes and historical R5 causality
remain unverified. Next contract should check compensated rephasing error and
position/velocity consistency against real ephemerides under a finite native
sampling budget before any new real-state integration.
