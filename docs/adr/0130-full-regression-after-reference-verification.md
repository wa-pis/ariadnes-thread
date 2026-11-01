# 0130 — Full regression after reference verification passes

Date: 2026-11-01
Decision status: accepted verification evidence; no architectural or scientific contract change.
Implementation: full integrated regression complete; no runtime changes or new trajectory study.
Scope / milestone: verification of the current research demonstrator and R2 preparation within active M3.
Measured revision: `7b222534ee88d81daea579699652d89e84b9b2ac`; clean before verification.
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md), [R2 requirements](../../openspec/changes/refine-physical-trajectory/specs/reference-coast-verification/spec.md).
Supersedes / Superseded by: none; supplements [ADR0128 preparation](0128-reference-coast-verifier-ready.md) and [ADR0129 result](0129-reference-coast-verification-passes.md) without replacing their evidence.

## Context and constraints

The user requested continued verification. R2.2 had225 combined native-free
preparation checks, but the last full regression preceded its86 new tests.
R2.3 had independently verified the actual retained ideal coast. Repeating that
successful experiment would not test integration or increase model fidelity.

The next bounded verification action was therefore one complete existing pytest
suite at the unchanged checkout, plus lint, strict OpenSpec and immutable-file
checks. Its640.24s duration is a regression-suite duration, distinct from the
frozen30s R2 native-study budget; no R2 experiment was retried or expanded.

## Options considered

- Repeat only the small focused suite: rejected; it would leave integration open.
- Repeat R2 or automatically add more forces/optimizer controls: rejected; neither
  is necessary to check compatibility, and physical studies need their own scope.
- Run the complete existing regression suite once, preserve the exact result and
  current source identities: selected under the user's verification instruction.

## Evidence and verification

[Machine-readable summary](experiments/0130-full-regression.json) retains the
command, measured revision, Python executable/version, exact pytest summary,
reported duration and relevant source/evidence SHA256 identities. Summary SHA256:
`4a8591b36b768bec5dd60e520002fd6544d64f56f1d2e0d2216048574506fb93`. It is a summary
of the observed terminal result, not a saved full terminal transcript.

- Command: pinned Conda Python `-m pytest -q`, with repository pytest configuration.
- Exit code0: **4852 passed in640.24s (0:10:40)**; no failures or skips reported.
  This integrates ADR0125's4766-test baseline plus86 R2 preparation tests.
- Ruff over `src`, `tests` and both new private R2 experiment scripts passes.
- Strict `openspec validate refine-physical-trajectory --strict` passes.
- All230 previously tracked protected runtime/test/example/environment/legacy/
  experiment files remain byte-identical to the measured revision; original R2
  raw/audit hashes and all three prepared R2 file identities are preserved.
- Existing native regression tests were included. Native query counts were not
  instrumented, so this record does not claim a zero-native run. No separate
  reference-coast CLI study was launched; ADR0129's retained result was not rewritten.

All129 changed-document local links resolve; JSON/digest and diff checks pass.
CURRENT_STATE has59 lines, within its under60-line rule. No dependencies, code, tests or scientific tolerances
were changed to obtain the result. Automation remains paused.

## Decision and rationale

Record the integrated regression as passing at the measured revision. Keep the
successful R2 result and its exact original evidence; the new full-suite result
adds compatibility evidence, not a new physical validation claim.

## Consequences and revisit conditions

The project now has both an independently checked retained ideal coast and a
fresh full regression including its new verifier tests. This does not verify
shared planetary ephemeris truth, continuous safety, finite burns, real lunar
escape, Mars capture, uncertainty or the effects of omitted forces. Strict M3/
task3.9 and M6 stay open, with UI qualification unchanged.

Any next increase in physical fidelity needs a named question, frozen inputs,
force model, independent reference, tolerances and bounded execution scope.
No automatic D17/D18 replay, new optimizer, ML, object screening, UI change or
native experiment follows from this record. Rerun regression after relevant
implementation changes, rather than repeatedly testing the same unchanged code.
