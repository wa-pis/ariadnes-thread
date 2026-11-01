# 0136 — Retained physical endpoints pass independent arithmetic

Date: 2026-11-01
Decision status: accepted evidence interpretation under ADR0135; no new mission model.
Implementation: R4.3 offline endpoint audit complete and passed once.
Scope / milestone: M3 boundary arithmetic only; no achieved transfer or safety claim.
Base revision: `186c20b0fac7d0acb636448b52fa196067c92fad`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [ADR0135](0135-fixed-orbit-boundary-contract.md), preserves R1–R3 and D13–D17 evidence.

## Context and constraints

The fixed configured orbital endpoints can be reused only if their arithmetic
matches the original states, phases, harmonic GMs and exact R1 body epochs.
This check isolates that question; it neither selects controls nor propagates
the spacecraft. Candidate/scenario equality alone would not prove conversion.

## Options considered

- Construct another phase/branch or replay local targeting: unnecessary and not
  authorized by the endpoint contract.
- Audit the two retained states with the two specified independent orbital
  expressions and fixed original translations: selected and completed.

## Decision and rationale

The single fresh offline process passed both endpoints in0.014713209122419357s
before evidence flush, under the shared10s budget. The finalization gate passes;
no exact post-flush timestamp is claimed. Scientific imports, native reads and
spacecraft propagations are zero. No mission initial/target input was changed.

The original0119/0098 digests and complete scenario/candidate equality pass.
Stored body/epoch/frame/label checks pass. Binary64 plane rotation/vis-viva and
80-digit Decimal p-based periapsis arithmetic independently reproduce the saved
relative and SSB states at the frozen gates0.001m/1e-6m/s. Decimal uses exact
stored binary angles/eccentricity and a separate Taylor trig implementation;
no polar-angle rounding or eccentricity substitution occurred.

| Endpoint | Method | Position residual norm (m) | Velocity residual norm (m/s) |
|---|---|---:|---:|
| Lunar ignition | binary64 | 0 | 2.484017812455876e-13 |
| Lunar ignition | Decimal80 | 0 | 2.857644125562129e-13 |
| Mars target cutoff | binary64 | 4.656612873077393e-10 | 1.438037388729017e-12 |
| Mars target cutoff | Decimal80 | 4.339306691747424e-10 | 1.0064403121775914e-12 |

Relative and SSB comparison norms agree because both use the same retained
translation in exact Decimal arithmetic; these are two coordinate presentations,
not independent ephemeris checks. Position agreement of80/100-digit oracles is
zero at both endpoints; velocity differences are2.0572628736215755e-77m/s and
3.849287426211678e-77m/s, below1e-12m/1e-15m/s convergence gates.

## Evidence and verification

[The exclusive audit record](experiments/0136-retained-boundary-audit.json),
SHA256 `81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063`,
retains original input digests, exact endpoint/body/orbit records, constants,
80/100-digit oracle vectors, both methods' signed relative/SSB residuals and norms,
zero-native counters and timing/finalization status. Its embedded reproduction
worksheet and SHA256 retain the exact arithmetic used; it is not a new package
module or reusable runtime implementation. The worksheet passed syntax and Ruff
checks, with E402 explicitly exempted to start the budget before remaining stdlib
imports; analytic zero-angle trig assertions passed in the audit. No native or
scientific runtime was started and no numerical retry occurred.

Finite JSON, embedded-source/input/evidence digests, numeric gate values,
137 local links, diff and strict OpenSpec pass; all240 previously tracked protected
code/test/example/environment/legacy/evidence files remain byte-for-byte unchanged. Production code, tests, dependencies, examples, legacy model and historical
evidence are unchanged; the unrelated full suite is not rerun. ADR0132 retains
4936 passing tests; this numerical worksheet is evidence, not a runtime change.

## Consequences and revisit conditions

R4's fixed-endpoint arithmetic question is answered. The initial/target records
are valid descriptions of configured task boundaries at their stated fidelity;
no connecting trajectory, capture maneuver, achieved reserve, interior handoff,
independent dynamics or continuous safety has been demonstrated. Strict M3/task3.9
and M6 remain open; no old failed experiment is repaired by this result.

The next bounded design step can specify a short-coast omitted-force comparison
from the now-audited retained initial state, first inspecting existing numerical /
independent-engine adapters and tests for reuse. It must name two force models,
an independent same-model reference, exact interval, numerical gates and a finite
native/time budget before any implementation or execution. Report integrated
model sensitivity separately from numerical error, full-arc accuracy or safety.
No new candidate, orbit phase, mission control, optimizer or dependency is selected
here; pause if the next contract needs an action or choice outside authorization.
