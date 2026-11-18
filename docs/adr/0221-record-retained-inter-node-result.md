# 0221 — Record the inconclusive retained inter-node check

- Date: 2026-11-18 (Europe/Samara).
- Decision status: accepted preservation of an inconclusive result; no verified continuous refusal or existence witness.
- Implementation: unchanged ADR0220 method; one retained execution and one separate saved audit completed.
- Scope: R5.59i, closed Mars true-anomaly interval [150°, 152°], candidate `d0001-t0035`, fixed ADR0218 surrogate and scientific gates.
- Measured revision: `1b47bd846f97f64e5239b022738459da994ca7bf`, initially clean `dev` synchronized with `origin/dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-check-the-continuous-neighborhood-of-the-best-saved-mars-phase), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559i-record-the-retained-inconclusive-result-2026-11-18), [task](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0215](0215-record-retained-phase-readback-failure.md), [ADR0217](0217-verify-the-saved-mars-phase-grid.md), [ADR0218](0218-design-inter-node-mars-phase-check.md), [ADR0220](0220-qualify-retained-inter-node-binding.md) and the [physical contract](0205-design-fixed-command-physical-join.md) keep their scopes.

## Context and constraints

The saved integer-degree grid admits no pair, with a 40.084654 m/s shortfall at its best sampled phase. It does not exclude a passing phase between samples. The user authorized one offline local study under the qualified ADR0218/0220 contract, a separate independent audit and preservation of either a verified witness, continuous refusal or inconclusive result. The exact four input hashes, fixed reference, two signed roots, tolerances, mass ledgers and bounded bisection procedure were unchanged.

## Options considered

- Execute the qualified bounded study and preserve its audited disposition: selected.
- Deepen, widen or repeat the computation after an unresolved result: outside this authorization and forbidden by the consumed-attempt contract.

## Decision and rationale

Preserve `inconclusive`. The producer and the separate saved-certificate audit agree. No eligible phase was found, but neither path certified an exclusion of both signs on any terminal cell. Completion of the procedure is distinct from a positive scientific answer or proof of impossibility.

The attempt is consumed. Do not silently increase depth, loosen a gate, change an input, repeat R5.59i or admit commands to R5.60. The next useful investigation is a separately scoped diagnosis of the saved positive-root enclosures before any proposed new experiment.

## Evidence and verification

The [execution observation](experiments/0221-execution.json) records the base revision, pinned inputs/methods, command arguments, externally measured timing, immutable artifacts and completion digest. The [producer report](experiments/0221-r559i/report.json), [receipt](experiments/0221-r559i/receipt.json) and [completion](experiments/0221-r559i/completion.json) bind the single attempt. The [separate audit output](experiments/0221-independent-audit.json) was captured from a fresh isolated `audit COMPLETION_SHA256` process; it reproduces the completion proof and verifies the receipt chain and local transcript with the pinned independent point/interval path. The externally captured completion SHA-256 remained `44a9bce0f042fe5e07b2237bc08e14a7eb9390449b6cc9c83f780f5b9b0735b6`.

| Observation | Result |
| --- | --- |
| Producer and independently audited status | `inconclusive`; witness null |
| Work per producer or replay | 126 cells, 252 signed bounds, 129 direct phases, 258 signed root/pair slots |
| Tree and terminal intervals | 62 splits; 64 unresolved depth-5 cells, each 1/32°, covering [150°, 152°] |
| Certified two-sign exclusion leaves | 0; unresolved leaves 64 |
| Recorded pre-write receipt / completion elapsed fields | 0.733259042 s / 2.017107583 s |
| Entire retained process, externally measured | 2.135583459 s through durable output/readback, below the shared 30 s cap |
| Separate audit process, externally measured | 1.383126208 s, below 30 s |
| Input per reader / four producer files | 1,065,958 bytes / 598,535 bytes |
| Producer files plus separate audit payload | 1,214,897 bytes, below 4 MiB |

All 126 recorded midpoint evaluations have no eligible pair and no unresolved point arithmetic: the negative root is rejected by its guard, and the built positive pair fails the commanded 500 kg floor. The three saved anchors were checked under the original parity gates. These finite samples are not a proof between points.

On every terminal cell the **producer-recorded** negative-root enclosure has reason `mass`, while the positive-root enclosure has no proven exclusion. This identifies the remaining limitation in the saved transcript: the approved depth/work resolution did not close the positive-root bound. It is not a wall-time, byte-cap or missing-coverage failure. The audit certifies no complete two-sign exclusion leaves; do not promote the producer's individual branch annotations to a full-interval result.

The isolated worker and independent audit allowed only the pinned files, method sources and standard library. Third-party scientific imports, SPICE/native-library loading and out-of-scope access were blocked. Counters report zero SPICE queries, kernel accesses, force evaluations, integrations, R5.59f replays and R5.60 attempts, with null commands. Launch stdout/stderr and audit stderr were empty. All 1,004 previously tracked file hashes were unchanged through the audit; the old R5.59f completion remains absent.

Source code and tests were unchanged. Reuse ADR0220's 9 focused and 6,495 guarded full passes/494 exclusions and Ruff result; pytest was not repeated. Artifact JSON/byte/hash and receipt checks, local links, diff and strict OpenSpec were checked for this evidence-only stage.

## Consequences and revisit conditions

The 40.085 m/s inter-node question remains unresolved for these exact inputs. The saved grid refusal in ADR0217 remains valid at its discrete samples, and ADR0215 remains incomplete and consumed. R5.59i is also consumed. A follow-up requires an explicitly reviewed change supported by the saved evidence; this record neither authorizes another attempt nor proposes relaxed scientific gates. Physical continuity, flight feasibility, M3 completion and R5.60 admission remain unestablished.
