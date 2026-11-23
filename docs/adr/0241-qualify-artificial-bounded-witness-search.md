# 0241 — Qualify bounded witness search on artificial inputs

Date: 2026-11-23 (Europe/Samara)
Decision status: accepted
Implementation: P3 components implemented; artificial qualification passes
Verification: 124 focused and 6961 full portable tests, Ruff and strict OpenSpec pass; live/CI not run under the user's no-SPICE constraint
Scope / milestone: artificial-only preparation within the active M3 change
Base revision: `5270f00c037de3118e5f4f0dd13bb677822e2c64` plus new sources bound in the [verification manifest](experiments/0241-verification.json)
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-use-bounded-scalar-search-only-to-propose-an-analytical-witness), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md)
Supersedes / Superseded by: none; implements [ADR0240](0240-choose-bounded-scalar-witness-search.md), without changing its scientific gates

## Context and constraints

The user authorized P3 implementation and artificial verification, explicitly
excluding saved real-data execution, SPICE and integration. The new command has
no retained mode. All existing mission records, production sources, dependencies,
workflow and `moon_to_mars.py` stay unchanged. Automation remains PAUSED.

The prescribed full live lane and current CI both load SPICE; they are not run.
The requested scope is delivered with portable checks, not relabelled full
scientific qualification. P3's full qualification and any retained execution stay
unavailable while that required lane is unverified. The commit explicitly skips
CI to preserve the user's prohibition, not to claim a passing workflow.

## Options considered

- Modify an old dyadic wrapper/guard or replay its producer/self-audit: rejected;
  this would change frozen history or hide repeated phase work.
- Add a general optimizer or runtime framework: rejected. Keep five private
  modules, existing pinned scientific helpers and an artificial-only command.
- Use the accepted scalar proposer with independently checked literal points:
  selected, preserving the split between point existence and mission readiness.

## Implementation and rationale

[Point adapter/auditor](experiments/0241-phase-points.py) keeps each arbitrary
binary64 phase as a hex word and exact degree ratio, both signed branches, original
six command words and both exact mass ledgers. Its separate audit uses the frozen
96-digit orbit/conic oracle and reader; it never calls producer point/conic code,
regenerates substitute command words or reruns the optimizer.

[Search](experiments/0241-bounded-search.py) first verifies all three refusing
anchors, then calls pinned bounded SciPy once per sign. Ordinary pair refusals
retain their finite costs. A guard/degenerate branch ends that scalar call;
unresolved data ends the attempt. Every duplicate/error/final check is precharged.
The [independent trace validator](experiments/0241-trace-audit.py) checks settings,
sign order, callback/result/final identity, counts and first-witness termination
without importing the proposer. Complete point witnesses or inconclusive results
are the only outcomes; no continuous refusal or optimum is certified.

[Invocation](experiments/0241-bounded-invocation.py) exposes only
`profile-producer OUTPUT`, `profile-audit OUTPUT`,
`artificial CONFIG CONFIG_SHA256 OUTPUT` and `audit CONFIG CONFIG_SHA256 OUTPUT`.
The parent/worker argument forms are tested through actual isolated cold processes.
Configuration, archive and producer paths must be external artificial paths before
opening. Four chained fabricated records pass the unchanged archive binder;
only three actual artificial anchor calculations build them. The other 357 rows
are explicitly metadata-only fixtures, not an old 360-point numerical replay.

[Runtime guard](experiments/0241-runtime.py) charges bootstrap/configuration,
archive/private/selected-solver-source reads including rereads, independently
bounds evidence, and authenticates the explicit installed-runtime allowlist before
solver import. The frozen [producer](experiments/0241-producer-runtime.json) and
[audit](experiments/0241-audit-runtime.json) profiles include interpreter, loaded
native dependency identities, host and observed import artifacts/volumes. No
package-tree inventory scan, additional dependency or warm-up is introduced.
The producer uses existing SciPy/NumPy; the numerical audit uses only stdlib.
Stdlib ctypes inspects OS loader metadata, never SPICE or a mission-force API.
Unreadable macOS shared-cache images are listed with host identity rather than
claimed content-hashed; this is a scoped local runtime qualification, not a general
native sandbox or portable/flight certification. Optional package and CPU-subprocess
probes are denied before execution, with library fallback and refusals recorded.

The original 129-phase/258-Mars-slot, separate startup-inclusive 30 s, 4 MiB
input and combined-evidence limits stay unchanged. Final readback is structural
only. A separate numerical audit checks every recorded point and original words.
The maximum-volume fixture uses a deliberately artificial 1 m Mars shape/guard,
keeping its absolute orbit radius unchanged, so both branches remain defined.
It still fails mass at every point. A labelled test-only driver forces all 129
point checks; this is a workload test, explicitly not a Brent search result.
Real Mars parameters and all scientific acceptance thresholds are untouched.

## Evidence and verification

The [tests](../../tests/test_bounded_witness_invocation.py) cover actual producer,
independent audit, full volume, source/runtime/phase/word/ledger tampering, guard
versus unresolved outcomes, missed witnesses, counters, deadlines, byte limits,
exclusive output and dispatcher forms. Point, search and trace tests are separate.
124 focused offline tests pass in 7.97 s; Ruff passes for `src`, `tests` and all
five new private modules. Independent reviews found and fixed trace, path,
pre-import identity and readback validation issues before qualification.

The manifest records the artificial witness, ordinary inconclusive search and
full-volume inconclusive/audit pair. Every process fits its unchanged input/time/
evidence limits and prohibited scientific-work counters remain zero. This is no
new retained result or evidence that the approximately 40.085 m/s gap is recoverable.
The full portable lane passes 6961 tests in 205.09 s, with 42 archival skips
and 412 live deselections; see the [test log](experiments/0241-offline-tests.log).
All 1327 Git-visible files, HEAD and working-tree status stayed identical throughout
that suite. Strict OpenSpec, local links/anchors and final whitespace/scope checks
pass. The workflow is explicitly skipped because it imports/loads SPICE; neither
the required live lane nor CI is claimed passing for this revision.

## Consequences and revisit conditions

Implementation and requested artificial tests do not accept an executable pair,
changed Mars target, physical join, reserve, safety or M3 completion. No saved
execution, original R5.60 or automation continuation is enabled. Complete required
regressions and review qualified immutable identities before any separately
instructed retained binding/execution. A failed or inconclusive future study must
stop under ADR0239/0240; it cannot expand the domain, budgets or tolerances.
