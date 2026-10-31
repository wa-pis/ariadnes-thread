# 0126 — Propose independent verification of the actual reference coast

Date: 2026-10-31
Decision status: accepted for R2 priority by explicit user choice on2026-10-31; detailed contract proposed separately in [0127](0127-reference-coast-verification-contract.md).
Implementation: scope proposal only; no oracle, runner, native calls or UI change.
Scope / milestone: proposed R2 within the sole active M3 change; R1 remains complete.
Base revision: `b84b04e87fe453d0146c56f2052d0d9f2254781f`, clean before review.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/reference-coast-verification/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md).
Supersedes / Superseded by: none; follows [0125 delivery](0125-research-export-and-usable-path.md) and preserves [0117 priorities](0117-mission-first-demonstration-priority.md).

## Context and constraints

R1 delivers the actual input/display/verified JSON/OEM path. Its all-node OEM
checks measure serialization; R1.2 independently checks a synthetic ellipse.
Neither is independent numerical verification of the actual published reference
coast. The user requested continuation, without choosing a new scientific scope.
A priority question offers reference verification, saved-file reopening and UI
comparison. This record is the recommended proposal, not assumed acceptance of
new physical work or authorization to launch a study.

Bound this stage to inspecting current requirements and immutable local evidence,
then recording one proposed successor and its remaining readiness checks. No
external downloads, propagation, optimization, registration or dependency work.

## Options considered

- Reopen and inspect saved JSON/OEM: useful for interchange; defer behind the
  numerical credibility gap if the user accepts this priority.
- Improve candidate comparison in the UI: useful presentation; does not close
  that gap. The existing demonstrator already displays and exports candidates.
- Immediately resume D17/D18 or add forces: reject as an automatic continuation;
  it would change the physical problem before checking the current reference.
- Independently compare the retained reference coast at its actual121 epochs:
  recommended next scope. Reuse the completed product and preserve its fidelity.

## Decision and rationale

Propose R2, **actual-reference coast verification**, not a new full-mission
validation milestone. Keep original R1 completion and strict M3/task3.9 gates.

The authoritative input is unchanged ADR0119 JSON, SHA256
`3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0`,
first retained run, candidate `d0001-t0035`, all121 ordered SI/SSB/J2000 states at
their original numeric TDB epochs. Retained Sun GM is
`1.327124400420322e20 m^3/s^2`. No search, candidate selection, date change,
retargeting, new spacecraft propagation or replacement of saved states.

Readiness gap found: the artifact retains Moon/Mars endpoint states but **no Sun
track**. An independent Sun-relative coast cannot be reconstructed from those
SSB samples alone. A separately accepted contract must specify how to obtain,
freeze and audit the required Sun states using the same ordered hash-pinned
resources. An intended upper bound is121 exact-epoch Sun state reads, with no
new GM/planet queries, planner or production coast-adapter calls. This proposal
itself authorizes zero native reads and does not assert that readiness is passed.

R2.1 must freeze the exact Cartesian initial condition and its derivation from
the retained departure-body state/candidate and matching Sun state. Do not fit
orbital elements to later samples or use the saved final state to tune a solution.
An independent Cartesian-to-conic derivation and analytic time solve must handle
the actual initial phase/orientation; the synthetic periapsis-only R1.2 oracle
cannot be reused as proof without that extension and its own pure checks.
Unsupported conics or ill-conditioned inputs must stop, not select another case.

The intended comparison is the same Sun point-mass coast in Sun-relative J2000,
then re-add the exact matched Sun states and compare every saved SSB node. Sharing
a frozen ephemeris translation is acceptable input reuse, **not** independent
verification of the Sun ephemeris or absolute orientation. Preserve raw frame
translations, initial inputs, epochs, source/resources, both states, signed errors,
root/invariant diagnostics and failed/unavailable outcomes.

Start contract review from R1.2's numerical gates (1m position,1e-6m/s velocity,
exact TDB alignment and1e-12 relative energy/angular-momentum checks), without
adopting the tighter OEM wire thresholds as propagation criteria. R2.1 must
justify and freeze all gates, oracle domain/equations, independent pure fixtures,
resource admission, output identity and one shared wall-clock/call budget before
preparation or execution. No gate is changed or claimed passed by this proposal.

## Consequences and revisit conditions

This targets the trajectory users actually inspect, keeping the existing stack
and model. It validates only one ideal reference coast if it later passes; it
cannot qualify search optimality, arbitrary conics, real lunar escape, finite
burns, Mars capture, uncertainty, collision safety or M6. The existing scalar
mass/reserve and OEM checks remain distinct evidence. External mission replay,
new forces/optimizer controls, generic backends, ML and automation remain deferred.

Accept the priority and detailed contract before oracle preparation; separately
verify preparation and obtain an execution instruction before native work.
If another priority is chosen, keep this as a proposed backlog record rather
than silently treating it as accepted or rewriting R1 evidence.

## Evidence and verification

- Read-only JSON audit confirms the frozen digest, candidate,121 strictly ordered
  epochs, retained Sun GM, Moon/Mars endpoint-body records and missing Sun track.
- Strict OpenSpec, local links and scope/diff checks pass. All225 tracked
  runtime/test/scenario/environment/legacy/evidence files remain byte-identical
  to the measured base. CURRENT_STATE remains below60 lines.
- No runtime tests rerun: all runtime files remain byte-identical to `b84b04e`.
  Its4766-test/630.19s result remains previous implementation evidence, not a
  fresh physical-reference check. R2 remains unimplemented and unverified.
