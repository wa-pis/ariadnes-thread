# 0129 — Independent verification of the retained reference coast passes

Date: 2026-11-01
Decision status: accepted evidence under ADR0127; no new model or scientific gate.
Implementation: R2.3 single native comparison and independent offline audit complete.
Scope / milestone: R2 retained ideal reference coast within active M3.
Measured revision: `fa28e044011c9615c97b47b698d33bf5d903bec2`; clean before output reservation.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/reference-coast-verification/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; empirical result of [ADR0127](0127-reference-coast-verification-contract.md), using [ADR0128 preparation](0128-reference-coast-verifier-ready.md).

## Context and constraints

The user instructed continuation after verified R2.2 preparation. This authorized
one R2.3 comparison, not retries or a wider scientific study. The reference is the
unchanged ADR0119 run1/candidate d0001-t0035,121 SI/SSB/J2000 states, numeric TDB
epochs and original Sun GM1.327124400420322e20m^3/s^2.

The output file was exclusively reserved before native imports. Both retained
identity snapshots show only that new untracked output; production code,
preparation scripts/tests and all previously tracked files were unchanged.
No automation, planner, native spacecraft propagation or new mission data was used.

## Options considered

- Rerun the search or change numerical gates: rejected; that would change the question.
- Execute the frozen independent coast and then audit its evidence without native
  calls: selected, exactly once under the declared budget.
- Widen to finite burns or full-force dynamics: deferred; this result cannot close M3.

## Evidence and verification

[Raw evidence](experiments/0129-reference-coast.json), SHA256
`e2c5d077285fe0218d1c93f3000f319048006eb55477d680f83041f6c70ce9d7`.
[Retained offline audit](experiments/0129-reference-coast-audit.json) binds that
raw digest and the exact independently implemented auditor source hash.
The unchanged prepared runner was invoked once with `--execute` and this new
output path; no retry, altered input or tolerance was used.

- All121 Sun provider calls were attempted and returned, exactly once in retained
  epoch order. Zero native spacecraft propagations, extra-body/GM reads or search
  calls. Original ordered13-kernel manifest and all source/runtime/build identities
  match before/after. The only dirty path was the exclusively reserved output.
- Actual recovered domain: a178672353858.12955m, e0.17763402730689387;
  supported by the frozen ellipse domain. Seed uses retained Moon minus Sun0 and
  original departure excess velocity, not a propagated spacecraft sample.
- All121 nodes pass in both Sun-relative and re-added SSB frames. Maximum Euclidean
  position difference: **0.0021126122711470335m**, node11; velocity difference:
  **3.9825899625221015e-10m/s**, node11. Gates remain1m and1e-6m/s.
- Initial position difference0.00020977366767681153m; final0.00011341910360197835m.
  Zero-time adapter conversion roundoff is included, not fitted away.
- Saved-state maximum relative energy/vector-angular-momentum errors:
  9.62957399881166e-16 /5.716384911504403e-16. Independent-state maxima:
  1.1234502998613605e-15 /5.333451916812789e-16; all below1e-12.
- At most49 bisections per node; maximum bracket width1.1546319456101628e-14rad,
  residual1.2878587085651816e-14rad; frozen64-update/2e-14rad gates pass.
- Shared budget30s; elapsed sample before serialization1.1418960839509964s,
  final identity call ended at1.1416713749058545s. The unchanged runner's separate
  post-flush deadline gate also passed. Exact final post-flush elapsed is not
  recorded; the pre-serialization sample must not be presented as total run time.
- The stdlib-only independent auditor recalculated all121 nodes and returned
  `audit=passed`, `study_status=passed`, `reference_coast_verified=true`, with
  zero new native calls. Subsequent audit retention only repeated that offline
  calculation, not the native comparison.

Strict OpenSpec and diff checks pass;153 changed-document local links resolve,
228 previously tracked runtime/test/example/environment/legacy/evidence files
remain byte-identical to the measured base, and new JSON/digest/status checks pass.
CURRENT_STATE remains under60 lines. No runtime code
was changed, so runtime regression tests were not rerun; ADR0128's225 preparation
tests and ADR0125's4766 full tests remain historical results.

## Decision and rationale

Record **R2 complete for this retained ideal coast**: independent initial-phase
and elapsed-state arithmetic, original time/frame alignment, translations and
invariants meet the accepted contract at every saved node. The retained raw Sun
track now makes the comparison reproducible offline without new ephemeris reads.
Preserve both successful evidence artifacts and the original reference unchanged.

## Consequences and revisit conditions

Sun ephemerides remain shared authoritative inputs; their physical truth is not
independently tested. This is sampled agreement for one ideal Sun-point-mass coast,
not proof of continuous accuracy or validation of all search/Lambert cases, scalar
burn/mass dynamics, real lunar escape, finite burns, Mars capture, uncertainty or
mission safety. Strict M3/task3.9 and M6 remain open; UI qualification is unchanged.

No new physics, optimizer, ML, screening, UI or automation work follows automatically.
Choose the next user-visible priority separately. Revisit this verification if the
reference, force model, initial-state convention, provider, numerical code or
pinned scientific resources change; do not overwrite the retained evidence.
