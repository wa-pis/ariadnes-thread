# 0192 — Bracket the retained 3,000 km lunar range event

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted within the [ADR0191](0191-design-retained-lunar-range-event.md) diagnostic contract.
- Implementation: R5.45 complete.
- Verification: synthetic checks and one bounded offline readback passed.
- Scope: the retained candidate `d0001-t0035` unpowered model B coast.
- Base revision: `9423a8e6fa559a98d6271955512c7da882ed2caa` with new private worksheet and tests, whose exact hashes are in the manifest.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-check-a-retained-lunar-range-event), [result](../../openspec/changes/refine-physical-trajectory/design.md#r545-retained-lunar-range-result-2026-11-14), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[ADR0190](0190-post-cutoff-coast-outbound-at-samples.md) verified the
600 s post-cutoff coast at fixed epochs. This worksheet checks one
range crossing inside that archive using signed raw operands. It
retains the same exact cutoff, constant mass, reference frame,
units, source inputs and numerical comparison gates. The marker is
fixed at 3,000,000 m from the lunar centre, chosen retrospectively
as a check that the evidence path works.

## Options considered

- Report an interpolated crossing time: would require a separate
  interpolation and event-time accuracy contract.
- Compare sign brackets directly on the two archived engine grids:
  selected. The finer native histories tighten their own brackets
  without fabricating finer adaptive-solver samples.

## Decision and rationale

Accept the sampled brackets from both engines. The worksheet verified
52 coepoch rows and 1,802 native mesh rows, excluding the preflight Moon
entry from each mesh. Both exact dyadic and Decimal paths agree on all
range and radial signs; binary64/Decimal metrics pass the established
direction arithmetic gates. Every grid supplies one strict below-to-above
pair with positive radial motion at the endpoints. The original R5.43
coepoch numerical gates also pass on the reconstructed operands.

| Archived grid | Bracket, seconds after cutoff |
| --- | ---: |
| All four profiles at 50 s coepochs | 200–250 |
| RK4, 1 s mesh | 209–210 |
| RK4, 0.5 s mesh | 209–209.5 |

The two native brackets overlap at **209–209.5 s**. This is an
overlap of sampled brackets; the DOP853 evidence has the coarser
200–250 s bracket. The signs imply at least one crossing for each
represented continuous model trajectory; they do not identify an
exact crossing epoch or prove it is the first physical crossing.

## Evidence and verification

The [manifest](experiments/0192/manifest.json), [signed endpoints](experiments/0192/evidence.json),
[attempt](experiments/0192/attempt.json) and [receipt](experiments/0192/receipt.json)
bind the result, hashes, counts and timing. The once-only saved-data
run finalized in 0.337292 s of 10 s, with zero native calls, kernel
loads, scientific package imports, record evaluations or spacecraft
integrations. No earlier artefact was modified.

24 focused tests passed, including exact equality, inward and
multiple candidates, bracket disagreement, stale source or receipt,
and a late finalization. The full run with the
[R5.42 native guard](experiments/0189/pytest-offline-guard.py.txt)
reported 6,165 passed, 494 skipped. Ruff, strict OpenSpec, link, checksum and
frozen-checkout checks passed.

## Consequences and revisit conditions

The retained archive can verify a finite-radius diagnostic event
without another trajectory run. The 18,374 km comparison marker,
continuity between samples, full-force mission accuracy, escape and
the actual burn interfaces remain unverified. A farther-range study
needs a covered fixed horizon, independent verification and a
separate runtime budget and authorization.
