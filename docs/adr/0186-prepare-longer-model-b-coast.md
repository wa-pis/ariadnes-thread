# 0186 — Prepare the independent 600 s model B check

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted under [ADR0185](0185-design-longer-model-b-coast.md).
- Implementation: R5.39 complete; R5.40 live study and audit pending.
- Verification: synthetic study, independent saved-data audit and guarded regression passed.
- Scope: restricted unpowered 600 s coast, no post-burn departure or model A calculation.
- Base revision: `2ff6c2a6600c3514ae731aeb97c7f62cbae05b6a`; tested source and fixture hashes are in the manifest.
- Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-independently-check-the-longer-model-b-coast)
  and [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

ADR0185 doubles the R5.37 interval while keeping the model, kernels,
raw initial condition and solver settings. The historical helpers'
300 s limits are part of their evidence. R5.39 prepares a new private
study and audit without evaluating retained real data beyond metadata
and without consuming the R5.40 attempt.

## Options considered

- Edit or retune the archived runner: invalidates frozen evidence
  and confounds an interval-only extension.
- Add private 600 s controls and reuse hash-checked duration-independent
  primitives: selected. This retains shared physical inputs but keeps
  native settings, adaptive force assembly and audit reconstruction
  separated without changing production packages.

## Decision and rationale

The [study](experiments/0186-long-b-study.py) schedules two native
RK4 profiles and two DOP853 profiles, reuses the checksummed B prefix,
selects new samples by callback ordinal and keeps signed residuals.
It stops on a failed gate and retains completed raw evidence.
The [audit](experiments/0186-long-b-audit.py) reads the saved report
and independently reconstructs motions, forces, trial membership,
profile and prefix comparisons, and ledgers. Neither the study
module nor any scientific package is imported by the auditor.
Trial counts are reconciled with the observed final step and the
subsequent DOP853 dense-output callbacks, which are not trial stages.

The [launcher](experiments/0186-long-b-launch.py) requires the tested
manifest and clean synchronized dev. The separately authorized study
and audit use exclusive attempt files, bounded child execution and
receipt binding. Its watchdog and corruption cases were tested with
a synthetic child boundary; it was not used to start either live phase.

## Evidence and verification

On synthetic inputs, actual DOP853 reached 600 s in both profiles.
Injected native histories checked the RK4 settings/returns, 601/1,201
states and all 5,412 guard reads. With the nonzero synthetic Earth
field, the tighter DOP853 endpoint agreed with an independent analytic
approximation to within 2e-6 m and 1e-8 m/s in the vertical component.
The independent audit verified all 67 comparisons (28 archived-prefix
equivalents), 52 source/force observations and 26 native telemetry
rows. It rejected corrupted residuals, callback membership, force,
counter, initial data and identity. Missing extension coverage,
prefix failure, timing and exclusive receipts have targeted checks.

The 24 focused tests passed. The guarded regression finished with
6,089 passed and 494 skipped. Three older R5.34 tests in
the first regression exceeded an import-time clock while waiting
behind unrelated tests. The final guard runs that file first and
leaves its controls and historical bytes unchanged.

The [manifest](experiments/0186-verification.json) records the counts,
run/test hashes and exact protected inputs. The [regression guard](experiments/0186/pytest-offline-guard.py.txt)
excluded actual SPICE access and known evaluations on retained real
operands. Strict OpenSpec, Ruff, linked files and frozen hashes passed.
No new SPICE queries, kernel loads, retained force or record evaluations,
or live propagation were performed.

## Consequences and revisit conditions

A synthetic pass makes the runner ready for the separately authorized
one-time R5.40 study and audit. Real convergence, force gates and
deadlines remain unmeasured. Stop on a scientific, identity or budget
failure and retain the evidence. No previous outcome, mission
accuracy, continuous safety or strict M3 acceptance is changed.
Automation remains paused.
