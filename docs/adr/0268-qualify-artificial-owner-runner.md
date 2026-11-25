# 0268 — Qualify the artificial actual-owner runner

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (user explicitly authorized F18.2 implementation/tests)
Implementation / verification: complete for F18.2 artificial preparation; required regressions, independent review, Ruff and strict OpenSpec pass
Scope / milestone: F18.2 / M3 artificial preparation only
Base revision: `f1761404835498a64015d2b7f2e04e7aa1459ec2`; new files measured in the frozen working tree
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f182-artificial-owner-runner-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; retains ADR0267 and every consumed native episode

## Context and constraints

Implement [ADR0267](0267-design-actual-owner-endpoint-qualification.md)'s fixed
private fixture and independent auditor, verify artificial cases and required
portable/live regressions, commit/push. The user explicitly excludes F18.3.
New qualification uses injected owners and fake subprocesses only; no actual
private owner invocation, new native import packet, SPICE study, integration,
resource copies, builds, dependencies or changed physical inputs/gates.
Existing required live regression remains separately authorized.

## Options considered

- Extend/reuse the old F7 six-arc Budget and subprocess watcher unchanged:
  rejected for this new profile; six-attempt limits differ and the old watcher's
  error cleanup only kills a group while its direct leader is still alive.
  Do not alter historical pinned sources for this isolated preparation.
- Three small private modules with reused trajectory settings and import guards:
  selected. Keep the producer, independent rational auditor and bounded process
  controls separate; no public CLI, optimizer or dependency is introduced.

## Decision and rationale

[Producer](../../src/space_nav/_owner_endpoint_fixture.py) performs the eight
ordered calls, precharges3factories/2integrations/8visitors/100000acceleration
callbacks and preserves the first failure/partial counters. Injected mode is
explicit. Native imports are lazy and the future native path requires the exact
private kernel hash/context before factories. Read the private context from
`kernel.dynamics.simulator`, since the public star-import wrapper need not export
underscore attributes. No native branch was exercised in this qualification.

Reuse tighter coast RKDP87/coupled translation+mass construction. Independently
check actual typed settings map/initial words and successful exact termination.
State IDs now require exact source-backed whole labels and integer block indices,
not an arbitrary prefix with a matching body suffix. A bounded read-only source
substep resolved naming functions/Cowell/header concatenation in123.835s<=300s,
including an independent check; then the image was detached. This read no native
results and ran no imports, formulas, SPICE, compiler or payload acquisition.

[Auditor](../../src/space_nav/_owner_endpoint_audit.py) imports only stdlib,
recomputes each direction from its own literal binary64 start using Fraction,
checks exact initial words and unchanged squared Euclidean0.001m/1e-6m/s plus
scalar1e-9kg gates. It checks metadata, selectors, expected exceptions, retained
primitive words, limits/zero-work counts and actual sibling source digests without
importing the producer. Exported zero signs are retained; no native Time identity,
large/fractional epoch support or event carrier is inferred.

[Controller](../../src/space_nav/_owner_endpoint_run.py) validates bounded fixed
input before native imports, denies producer/scientific imports in the cold
auditor, uses exclusive namespaces and streams per-output/combined-log budgets.
It preserves partial failures and a durable prefinal receipt; returned post-fsync
observations are distinct and never rewrite that receipt. The cold supervised
parent and workers inherit one group; outer cleanup kills the entire group even
when its leader exits, before the supervisor's own recording. This also stops
live fake descendants when parent output/finalization I/O stalls.

The original60s inclusive45/10/5 phase limits remain fixed. Structured caps are
64KiB input,1MiB producer,512KiB audit and64KiB receipt, below2MiB including the
bounded outer input/observation/receipt. Parent logs63488B plus outer logs2048B
share64KiB. Direct component tests retain the64KiB local log cap. All deadlines
inherit one comparable clock; no launch after exhausted admission. An external
same-clock supervisor remains necessary to hard-bound opaque supervisor I/O;
the worker group is already stopped before its own final recording can stall.
A fixed serial worker/source profile is required; no arbitrary hostile-worker
containment, per-phase descendant quiescence or concurrency proof is claimed.

## Consequences and revisit conditions

No public API or operational native package changes. F18.2 prepares artificial
plumbing only. F18.3 still requires separately explicit authority and its complete
pinned runtime/source/resource/control preflight; no new execution profile is
sealed or consumed here. Existing5files/131662B,497045495B cumulative acquisition,
old clocks/closed ledgers, private kernel and historical failures remain intact.
F17/F17.1, actual serial native-owner outcomes, native carrier/carry/prior-Time
arithmetic, full core/source/ABI/FP, physical endpoint bounds and every F0/M3 gate
remain open. No admissible commands,99%probability or mission-safety result.

## Evidence and verification

The [qualification record](experiments/0268-qualification.json) and immutable
[raw evidence archive](experiments/0268-validation-evidence.zip) retain source
pins, read-only source receipts, separate code review, focused and full JUnit/logs,
freeze manifests, pinned environment metadata and the artificial cold packet.
Archive:33members,217598compressed bytes,3789231expanded bytes; SHA256
`c102a9037d8ed8ee16d1548ebad18681e3ba27106bbd84920c4a0268b1204371`.
This full validation archive is separate from the2MiB per-packet cap.

- Focused:194artificial cases pass in4.60s; these same194cases are included in
  the portable regression, not additional passes counted twice. Coverage includes
  exact metadata/word/gate tampering, full callback capacity, stream caps,
  inherited clocks, first failure, dead group leader and cold-parent
  fsync/live-descendant stalls.
- Required `make test`, unchanged pinned Conda environment:7724portable passed,
  42opt-in historical replay skips,413live deselected in the portable lane;
  413live passed,7766deselected in the live lane. Combined8137passed,0failures;
  lane case identities are disjoint. Existing live tests exercise their unchanged
  SPICE/TudatPy scope and do not execute the new private owner branch.
- All1525tracked/untracked files and Git status match before/after both lanes.
  Final documentation/evidence is added only after tests exit; runtime/test hashes
  match the frozen run. Ruff for all `src tests` passes, observed directly from
  the tool; no raw Ruff log is invented. Runtime tests are not repeated for the
  subsequent documentation-only edits.
- Independent connected-code review passes for the six new source/test files.
  Standalone artificial cold-parent/independent-audit qualification checks8calls
  and2saved analytic arcs in0.108096s after supervisor fsync. Its factory,
  integration and visitor counters are simulated logical slots; actual new
  private native factories/integrations/owner calls are all zero.
- [Final documentary verification](experiments/0268-doc-verification.json)
  records protected prior bytes, source/evidence hashes, working local links,
  anchors, final diff and strict OpenSpec checks, plus separate documentary review.

F18.2 alone is complete. F18.3 remains unchecked/unexecuted and requires separate
explicit authority; automation `ariadna-m3` remains PAUSED. No native-owner,
physical, command-feasibility,99%or mission-safety result follows.
