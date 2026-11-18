# 0219 — Qualify the inter-node Mars phase check

- Date: 2026-11-18 (Europe/Samara)
- Decision status: accepted artificial qualification for R5.59h.
- Implementation: artificial-only bounded runner, interval certificate and saved verification. No retained entry point.
- Scope: [ADR0218](0218-design-inter-node-mars-phase-check.md), [150°, 152°], fabricated input only.
- Measured base: `7ef17a92692ac2eeeff8920d5637ffe24b3b0243` plus the file hashes in the [verification manifest](experiments/0219-verification.json).
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-check-the-continuous-neighborhood-of-the-best-saved-mars-phase), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559h-qualify-the-inter-node-mars-phase-check-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0217](0217-verify-the-saved-mars-phase-grid.md) and the [ADR0205 physical contract](0205-design-fixed-command-physical-join.md) retain their scope.

## Context and decision

A denser point sample can exhibit a passing phase, but cannot rule out a missed narrow window. We implemented separate checks for a point witness and for exclusion of both signed roots on closed cells. The [runner](experiments/0219-phase-study.py) uses the fixed dyadic bisection and exclusive, hash-linked evidence. It accepts only a separately pinned artificial source, supervises the 30 s budget through durable readback, and leaves commands null.

The [point worksheet](experiments/0219-phase-points.py) reuses the frozen binary64 and Decimal96 ellipse, conic and ledger calculations. It checks both signs, the same state, radius and impulse gates, exact event order and both exact 500 kg floors. A witness also has to meet the unrounded budget. The [interval kernel](experiments/0219-interval.py) uses directed Decimal96 operations, a rational π enclosure, bounded Taylor tails and explicit outward treatment of the historical rounded recurrence. The [cell checker](experiments/0219-phase-bounds.py) encloses each signed reversed conic and applies the exact commanded ledger to conservative lower bounds on its comparison durations. It uses the original 1e-6 s agreement gate plus a rounding envelope, not a different tolerance. Its exact mass exclusion is strict. Independent saved replay recomputes both signs with a separate interval norm expression and a mathematical trigonometric enclosure in addition to the rounded one, then checks gap-free coverage. Source identity, bounds, caps and saved evidence are authenticated separately from status.

## Evidence and verification

| Artificial case | Audited outcome | Cells / direct phases per path | Through saved readback |
| --- | --- | ---: | ---: |
| Narrow passing interval | Positive/positive at **151.5°**, 6,117.696618 m/s | 2 / 5 | 0.077731 s |
| Full local refusal | Both signs excluded on four closed half-degree cells covering **[150°, 152°]** | 6 / 5 | 0.164948 s |

In the passing case all three integer anchors fail the commanded floor. At 151.5° the pair comes in **0.010000 m/s below** the ideal budget; the commanded and epoch-effective final masses both exceed 500.001132 kg. This is an existence check, with no executable commands or claim of a unique optimum. In the refusal case the independently checked mass bounds exclude all eight terminal branch/cell combinations, with no gap or unresolved cell. The experiment admitted exactly **4,194,304 bytes** of artificial source, wrote 17,559 bytes of evidence and refused a one-byte source excess.

With pruning deliberately declined, the real arithmetic was exercised at the full work cap: each of producer and replay examined **126 cells**, **252 signed bounds** and **129 direct phases** in a combined **2.273908 s** in memory. It returned inconclusive with 64 unresolved leaves. The timed isolated cases above separately exercise durable output and receipt readback. The [tests](../../tests/test_inter_node_mars_phase.py) also cover a changing guard disposition, exact mass equality, coverage holes, independent disagreement, altered hashes and proof arithmetic, output reuse, byte caps and watchdog refusal. All **11 focused tests** passed in 3.32 s. The guarded full suite passed **6,486 tests** in 131.26 s, with **494 excluded native, live and retained-science cases**. Ruff and strict OpenSpec passed.

The manifest records both isolated dispositions, exact witness ledgers, the excluded cover, source and evidence hashes, work and timings. All measurements use fabricated inputs. No retained source was opened and no SPICE, kernel, force, integration, R5.59i or R5.60 execution took place.

## Consequences and revisit conditions

The test answers the interval question only for the two fabricated examples. The real 40.085 m/s shortfall is still unresolved between grid nodes. R5.59i would require its own binding to the reviewed retained records and separate authorization. An inconclusive proof must remain inconclusive; the retained interval, mass gates and physical contract cannot be widened by this runner.
