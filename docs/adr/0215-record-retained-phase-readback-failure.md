# 0215 — Record the retained Mars phase readback failure

- Date: 2026-11-18 (Europe/Samara)
- Decision status: accepted partial evidence; the single R5.59f attempt is consumed.
- Scope: candidate `d0001-t0035`, fixed ADR0211 archive and the 360 Mars true anomalies from [ADR0212](0212-design-mars-capture-phase-seed.md).
- Measured revision: `3e75c15e6f86ef39022f7da408e6f3291b205ac6`, clean `dev` synchronized with `origin/dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#scenario-bind-the-retained-phase-screen-to-adr0211-evidence), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559f-record-the-retained-phase-readback-failure-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0205](0205-design-fixed-command-physical-join.md) and [ADR0211](0211-record-fixed-command-seed-refusal.md) retain their scopes.

## Context and constraints

[ADR0214](0214-qualify-retained-phase-binding.md) qualified the offline binding on artificial archives. The user authorized one invocation on the original four ADR0211 records. A scientific disposition requires a timely completion witness and successful saved-evidence audit. The invocation was `conda run --no-capture-output -n space-nav python -I -S -B docs/adr/experiments/0214-phase-binding.py retained`.

## Evidence and verification

The process returned **3** without a completion witness. The saved report contains all **360** indexed phase rows, **720** signed Mars root slots and **408** pair records. It records `no-eligible-pair-on-grid`, all 408 pairs rejected by the commanded dry floor, and null commands. Its lowest recorded pair is at **151°**, **6,157.791 m/s**, about **40.084 m/s** above the ideal dry-mass budget. These are observations from the **unaudited scientific report**. No phase proposal or verified grid refusal was established.

The separate [partial readback](experiments/0215-partial-audit.json), restricted to the newly saved evidence, pinned methods and the standard library, verified the attempt–report–receipt hash chain, frozen scientific operand digest, ordered grid inventory and zero authority. It independently reproduced the first failure without running the screen or reopening ADR0211. At phase 0°, the first velocity component in `independent_relative_si` is the exact decimal zero `0E-569`. The unchanged reader applies `abs(Decimal(value).adjusted()) <= 400` before the state comparison, so it rejects the exponent of a numerical zero. This was the only such encoding in the 2,160 saved independent state components. The audit stopped there without validating the remaining state, root and pair decisions.

| Evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| [attempt.json](experiments/0215-r559f/attempt.json) | 1,508 | `ac1d02f445ebed82ac5b4f728193ea8533890188ed2422117523db50d087bf0a` |
| [report.json](experiments/0215-r559f/report.json) | 1,059,325 | `323c2c71e17168a46e9dd5280015a3fecb0865016b9b6954dcb051de4def1800` |
| [receipt.json](experiments/0215-r559f/receipt.json) | 1,727 | `395d20ab4771b9a9e4743e038e5c50338d12b8d890018befc3879bf3de21a18b` |

The invocation opened each of the four pinned records once (13,363 of 131,072 allowed bytes). It saved 1,062,560 of 4,194,304 allowed bytes and reached the receipt in 0.318469 s under the shared 30 s limit. This elapsed value is through the receipt only; no completion was issued. The separate partial readback took 0.023090 s. SPICE queries, kernel accesses, force evaluations, integrations and R5.60 attempts were all zero. Strict OpenSpec, local links, saved evidence hashes and diff checks passed. Runtime code was unchanged in this stage; the full test suite was not rerun.

## Decision and consequences

Preserve the three original files byte for byte, with the separate partial audit. Do not complete, repair or retry the original invocation. R5.59f scientific disposition remains unverified; the original R5.60 remains unavailable. A separately reviewed saved-only check could handle canonical numerical zero without loosening any nonzero bound, then determine whether the existing grid can be verified without a new scan. That check does not retroactively complete this invocation or authorize a physical test.
