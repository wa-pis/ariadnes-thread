# 0233 — Record the corrected saved-lineage readback

Date: 2026-11-21 (Europe/Samara)
Decision status: accepted
Execution / verification: complete; one retained readback and one independent audit pass
Scope / milestone: M3, R5.59u, newly authorized saved-only execution through qualified0232
Measured revision: clean `b8b241325938b4491476098fe72505a15b041858`, synchronized `dev`/`origin/dev`
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves [ADR0231](0231-record-saved-lineage-result.md)'s consumed failure and [ADR0232](0232-qualify-lineage-command-dispatch.md)'s artificial qualification

## Context and constraints

The user explicitly authorized one `retained` and one independent `audit` through
unchanged0232 on the saved data, with no SPICE, integration or R5.60. This is a
distinct authorization after qualified repair, recorded as R5.59u; historical
R5.59s remains failed, consumed and unchecked. Immutable0232 emits raw stage
`R5.59s` for the retained profile; preserve that label without reinterpreting the
old failure. No artificial bootstrap, profile injection or numerical-source edit
is used. The [authorization](experiments/0233-saved-dispatch/authorization.json)
records the exact user instruction, clean base,13 raw pins, source inventory and
the unchanged [ADR0229 contract](0229-design-saved-lineage-diagnosis.md).

## Options considered

- Repeat the historical0230 invocation: rejected; its failed attempt is consumed.
- Read back with newly qualified0232 under the new explicit instruction: selected.
- Replay the scientific experiment or change operands/formulas: rejected; outside scope.

## Decision and rationale

Run the pinned Conda Python3.12.14 executable with `-I -S -B` and unmodified
`0232-saved-lineage.py retained` exactly once. Only after successful durable
completion, hash its raw `completion.json` and invoke the same script with
`audit COMPLETION_SHA256` exactly once. Preserve exclusive fixed outputs and
first evidence on any failure; no retry or cleanup/replacement by the recorder.
The external recorder writes authorization/logs outside the checkout, then copies
them into the journal after both commands finish. The producer itself writes the
four fixed result files, and the auditor writes the separate fixed audit file.

## Evidence and verification

Independent preflight confirmed13 immutable raw input pins, qualified source/test
hashes, the contract and absent fixed outputs. Both raw commands returned0 without
timeout. External durations: producer0.265408750 s, auditor0.217269209 s;
dispatcher durations0.251725875/0.204067625 s. Both share their respective parent
clock with the isolated worker and enforce30 s through durable finalization.
The raw [dispatch summary](experiments/0233-saved-dispatch/dispatch-summary.json)
and [producer](experiments/0233-saved-dispatch/producer.stdout)/[audit transcripts](experiments/0233-saved-dispatch/auditor.stdout)
preserve exact commands, completion pin and zero prohibited-work ledgers.

The [report](experiments/0229-saved-lineage-result/report.json) and separately
implemented [audit](experiments/0229-saved-lineage-audit.json) agree:

- 24 retained rows,1248 event visits and648 descriptors:432 checkpoints plus216
  cell/singleton comparison records;528 alias links and36 norm-pair slots.
- All432 checkpoints are observed,216 comparisons matched and528 aliases matched.
- All36 norm slots are `input-confounded`:12 impulse-squared,12 radius-squared
  and12 angular-momentum-squared pairs. No same-operand local comparison is admitted.
- Complete source inventory3,887,171 bytes/process, below4,194,304; producer555,778
  bytes plus752-byte audit totals556,530, below1,048,576 with65,536 audit reserve.
- Every new point/root/interval/norm/mass/trace/native/kernel/SPICE/force/integration/
  old-audit-replay/R5.60 counter is0. Only allowed saved endpoint arithmetic,
  descriptive widths, aliases and local-comparison dispositions are evaluated.

The new completion SHA256 is
`822626c615b0c41646d89d25ecf0e2f0ccb5a50f488339134bfcd02e99470756`;
the audit binds it and the produced analysis digest
`062cdcadc72acbd31421e7f0788f5bfaec918587f64a3a189296b7301952d6eb`.
Source and all original evidence bytes are unchanged. The [result summary](experiments/0233-saved-dispatch/result-summary.json)
retains measured identities, counts and dispositions.

An additional independent read-only review verified the hash chain, exact saved
operand/alias pointers, all36 confounded classifications, counters and caps without
replaying either command or any scientific evaluator. Project checks are in the
[verification manifest](experiments/0233-verification.json). No implementation or
test code changed: reuse ADR0232's87 focused/6665 guarded full passes with494 explicit
exclusions, Ruff and strict OpenSpec qualification; pytest/Ruff are not rerun.
This stage requires source/input/evidence hashes, finite JSON, links, scoped diff
and fresh strict OpenSpec validation.

## Interpretation, consequences and revisit conditions

Status `lineage-qualified-attribution-unresolved` is independently verified.
Here `input-confounded` means the saved operands differ between implementations;
their outputs cannot isolate the local implementation response. It does not prove
that the methods agree, that changing the norm is irrelevant, or that its effect
dominates final width. All three semantic roles are affected. Cell/singleton width
differences remain descriptive, not dependency-loss or rounding-error bounds.
Decimal96 context equality remains conditional source/provenance information,
not an observed runtime snapshot. No final-width cause, continuous refusal,
new eligible command pair, physical join, mission safety or strict M3 completion
is established; `commands=null`, `physical-join-not-established` remain explicit.

The two newly authorized commands are consumed and will not be repeated. Original
R5.59s remains unchecked; new R5.59u is complete. Automation remains PAUSED. Any
attempt to obtain matched operands, change the method or execute further studies
needs a separately specified and authorized scope; no such calculation is added here.
