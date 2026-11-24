# 0251 — Qualify the artificial coupled coordinate bridge

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (private interface implementation only)
Implementation: complete private bridge and artificial tests; no native adapter or physical optimizer
Verification: 149 focused, 7289 portable and 412 live checks pass; frozen checkout, Ruff, independent review and documentation/strict checks complete
Scope / milestone: F5 / M3 artificial preparation in the sole active change
Base revision: `a89e322b75389088a67230812b54ed01dfec99cf` plus three new source/test files; exact measured hashes in the qualification/freeze evidence
Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-the-coupled-coordinate-bridge-before-native-adoption), [bridge contract](../../openspec/changes/refine-physical-trajectory/design.md#f4-private-coordinate-bridge-before-native-adoption-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; implements the artificial scope of [ADR0250](0250-design-coupled-coordinate-bridge.md)

## Context and constraints

ADR0250 separates coordinate/event/request qualification from native adoption.
The bridge must carry six physical controls, two auxiliary normalized nodes,
exact input-word event/mass meaning and an unreset replay without silently adding
physical freedom. This stage implements only that interface. F0 feasibility,
full-force propagation, a qualified native seed and independent physical error
bounds remain open.

## Options considered

- Transfer F3's optimizer into production or wrap the historical research
  executor: retain ADR0250's rejection; neither meets this narrow interface task.
- Implement one private evaluator with immutable packets and an injected
  fabricated arc callable: selected. No registry, generic propagation backend,
  public API/CLI or real-data loader is introduced.

## Decision and rationale

[The bridge](../../src/space_nav/_coupled_bridge.py) reconstructs node components
from exact Fractions of binary64 anchors/offsets, rounds once, and preserves the
anchor word for zero offsets. Raw signed defects remain SI values; separate
residual scaling uses 1000 m and 0.01 m/s.

Event packets preserve exact duration sums and fixed endpoint words separately
from rounded labels and signed conversion errors. Exact endpoint identity is
mandatory before the separate 1 microsecond label gate. The mass ledger freezes
the existing binary64 `F / float(g0*Isp)` word, using the project's g0 constant;
exact dry-mass comparison precedes conversion, admitting equality and rejecting
sub-ULP shortfalls. These checks validate bookkeeping, not native clock or mass
integration accuracy.

Shooting and unreset replay are explicit separate three-arc modes. Replay carries
actual returned state and mass rather than copying nodes or ledger masses.
Requests identify Moon-TNW departure, no-engine coast and Mars-TNW arrival.
Diagnostics bind the complete fixed-spec and canonical-control words. Context
and callable identity checks reject reuse; these establish fresh interface
objects, not isolation of a future native body system. Failed/partial/unsafe
returns and invalid clocks stop further producer work without retry.

The independent tests use fabricated rational/affine expectations and request
spies. Fixed physical increments test representability; no optimizer, Jacobian
accuracy or physical derivative step is qualified. Simulated slots remain
separate from actual native propagation counters.

## Consequences and revisit conditions

This supplies a tested private interface for later design work. It adds no
native adapter, physical optimizer or mission execution authority. The guarded
subprocess qualifies one fixed fabricated capacity fixture and its output; it
is not a general-purpose production launcher or isolation guarantee.

Before native adoption, retain ADR0250's missing seed, exact-time/realized-mass,
guard, full-force parity, derivative and independent endpoint-bound gates, plus
explicit reconciliation with the prescribed production corrector. Fraction
packets and cross-check success do not establish native accuracy, physical
closure or safety. Production's 73-control/76-evaluation/228-native-call/300 s
limits, fixed F0 boundaries/hardware/resources and historical evidence remain
unchanged. No consumed study or R5.60 is revived.

## Evidence and verification

Measured code is HEAD `a89e322` plus exactly three new files:
[bridge](../../src/space_nav/_coupled_bridge.py),
[independent artificial tests](../../tests/test_coupled_bridge.py) and
[capacity/watchdog tests](../../tests/test_coupled_bridge_limits.py).
Exact file hashes and retained measurements are bound in the
[qualification record](experiments/0251-qualification.json) and
[freeze verification](experiments/0251-freeze-verification.json).

Completed checks:

- [Focused results](experiments/0251-focused.xml): 149 passed in 0.37 s; Ruff
  and independent source/test review pass.
- Fixed full-volume fixture: 73 shooting controls plus three frozen replay
  diagnostics, 76 evaluations and 228 simulated arc slots; 64 KiB input and
  647 B output. Producer elapsed 0.038593334 s; external elapsed 0.043013209 s,
  within the inherited 10 s producer/15 s overall ceiling. Boundary/failure,
  byte-cap and finalization paths are separately exercised.
- [Portable results](experiments/0251-portable.xml): 7289 passed, 42 archival
  skips and 412 live deselections in 199.10 s.

- Required [live regression](experiments/0251-live.xml): 412 passed, 7331
  deselected in 578.91 s. The [complete log](experiments/0251-regression.log)
  and frozen manifest bind both lanes to the same 1421 unchanged files and
  unchanged Git status. Combined inventory is 7743 unique cases; all149 new
  cases pass, with no lane overlap and no failures/errors.
- Independent review, protected prior non-Markdown bytes, relative links/anchors,
  diff, CURRENT_STATE under60lines and strict OpenSpec pass. Required local
  qualification completes F5. Source-commit CI has not yet been observed; this
  record does not claim it has completed.

Zero SPICE/kernel/real-archive access, native propagations, numerical integrations
and optimizer calls applies to the **new artificial fixture**, not the whole
regression suite. Existing authorized live regression may separately use SPICE
and native resources. Artificial interface qualification does not qualify F0
reachability, a physical trajectory, certified error bounds or mission safety.
