# 0161 — Controlled moving-coordinate arithmetic passes

Date: 2026-11-08
Decision status: accepted bounded execution of the unchanged ADR0159 contract.
Implementation: frozen R5.13 helpers reused; no runtime, test or dependency changes.
Scientific verification: all required controlled-arithmetic gates and separate saved-data audit pass; physical trajectory validity remains unverified.
Scope / milestone: M3 R5.14, prescribed moving-coordinate probe on retained real-source ephemeris operands.
Base revision: `3776f0523be964a643bebe8f53576efedf0bc9ff`, initially clean `dev` and equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [ADR0159](0159-moving-coordinate-assembly-contract.md) after [ADR0160](0160-prepare-moving-coordinate-check.md), preserving historical evidence and gates.

## Context and constraints

The user explicitly authorized R5.14 execution, result verification, ADR/OpenSpec
updates and commit/push. No prior0161 evidence or active study/audit process was
present. The retained inputs, exact initial six-state and seven epochs, INPOP19a
polynomial words, GMs, manufactured q/w, field formulas, domains, gates and caps
were frozen by ADR0159 and the verified R5.13 implementation. No integration,
failed R5.3 replay or changed fixture/tolerance/budget was authorized here.

Real data here means retained real body-state/polynomial operands. The spacecraft
q/w remain explicitly prescribed controlled inputs; they are not observed or
propagated flight corrections. Only elapsed zero is coepoch with a saved0148
native spacecraft state. The independent arithmetic reference shares the saved
source model; it is not independent astronomical truth.

## Options considered

- Repeat the fixed-position0158 check: would not exercise moving drift/q/w.
- Execute the accepted moving probe once, followed by a separate fresh audit:
  selected after binding the exact tested bytes and clean base revision.
- Expand into propagation or change operands/caps: outside this contract; defer
  to a separately specified scientific question.

## Decision and execution

The [recorded invocation](experiments/0161-moving-invocation.txt) binds the
ADR0160 manifest SHA256
`dbc5f6a31dc143f5936cb5ad209d0a21f2f1daa312a4ea44d330c5ff0a9edd50`
and all eight tested source/test hashes before launching either child. The
[baseline](experiments/0161-baseline.json) additionally binds370 existing files.
Receipts report354 for the prior manifest's protected map;370 includes its16
prepared source/test/artifact additions. Both counts describe distinct scopes.

One study and one saved-data audit each ran in a separate fresh pinned Conda
Python3.12.14 process with `-I -S -B`, default adapters/clocks and an unchanged
parent monotonic timestamp captured immediately before child creation. Each
retained its own inclusive10s budget through imports, reads, hashing, computation,
serialization, flush and post-flush check. The15s parent watchdog was only an
emergency process bound, not a relaxed scientific deadline; actual external
process times were below10s. Exclusive attempt markers, outputs and receipts
prevent an interrupted call from being silently repeated. Neither was retried.

| Saved result | Study | Separate audit |
|---|---:|---:|
| Status / finalization | passed / passed | passed / passed |
| Total external process time, s | 0.6299941670149565 | 0.5738388746976852 |
| Before-flush elapsed, s | 0.5127556249499321 | 0.5535072088241577 |
| Six-state assemblies, attempted/completed | 7/7 | 7/7 |
| Source rows, attempted/completed | 21/21 | 21/21 |
| Decimal fields, attempted/completed | 168/168 | 168/168 |
| Binary64 fields, attempted/completed | 63/63 | 63/63 |
| A/B model totals, attempted/completed | 14/14 | 14/14 |

Both ordered ledgers contain546 events and match. All42 motion/source/model
assessments pass. Source and helper identities match before/after, the audit
binds the exact uncompressed study SHA256
`21e71646bd5aafec0e78616ce1a00275de0b33e216ca73dbacca4db1109c20b2`,
and its `scientific_verified=true` qualifies only this controlled arithmetic
contract. Neither process made a scientific-library import, native call, kernel
load, GM acquisition, spacecraft propagation or optimizer call.

## Measurements and interpretation

All105 motion-component flags,63 relative-sum flags,63 source-rephasing product
flags,147 source-domain flags and140 required force flags across80/100 digits
pass. All35 precision assessments/classifications and70 signed telescope checks
pass. Elapsed-zero state and compensated source/model vectors reproduce0158
exactly; original source discrepancies remain in overall agreement without
subtraction or additional allowance.

The largest overall force error/envelope ratio is0.6287902030942953 for Moon
at elapsed5.960464477539063e-8s:9.131508562250725e-12m/s^2 versus
1.452234547757631e-11m/s^2. The largest returned-geometry ratio is
3.204205723684148e-5 for Sun at zero:1.954490448253912e-18m/s^2 versus
6.099765797829824e-14m/s^2. These are sampled arithmetic errors, not bounds on
astronomical uncertainty or future trajectory position error.

The drift-product component reaches exactly its inclusive half-ulp bound at
elapsed8.940696716308594e-8s (component1); ties-even passes. Maximum ratios to
the predefined component envelopes are0.5373475185439736 for q quantization,
0.4110946186117530 for exported position and0.3624153137207031 for velocity.
All w quantization errors are zero. The empirical one-ulp sum criterion passes
on this pinned build; this is not a universal fsum theorem.

At100 digits, flattened-craft controls pass all21 source and14 model overall
gates. Omitting q fails7 of21 source and6 of14 model gates; the other control
comparisons pass. Classifications are stable at80 digits. Control failures are
diagnostic, not required-study failures. Passing flattened controls means this
sample does not establish universal superiority or necessity of compensation;
no such conclusion is claimed. The independent synthetic cancellation coverage
and these real-source sampled results address different evidence boundaries.

## Consequences and revisit conditions

R5.14 completes its controlled arithmetic question. It does not establish the
physical correctness or uncertainty of q/w, a corrected integrator, historical
R5.3 causality, an independent ephemeris, Earth-force trajectory sensitivity,
continuous safety, full-force/finite-burn feasibility, strict M3/task3.9 or mission
safety. R5.3 remains failed; M3 remains open and automation remains PAUSED.

A corrected integration requires a separate bounded contract before any new
solve. Preserve these results, successful0155/0158 evidence, failed0148 evidence,
all old kernels/inputs/gates and `moon_to_mars.py`. No additional search, optimizer,
new force model or automatic continuation is authorized by this result.

## Evidence and verification

Retain the complete study and audit as lossless gzip archives of the exact
original UTF-8 bytes; verification records both compressed and uncompressed
SHA256 identities. No fields, raw operands, duplicate provenance snapshots or
failures are removed or reserialized. The original uncompressed files remain
outside the repository; the archives are the retained copy. The separate audit
ran on the exact original JSON before archival, not on a shortened report.

All370 earlier protected files and eight tested source/test hashes remain
unchanged. Reuse ADR0160's251 focused/5881 full passing tests and Ruff on those
same bytes; runtime tests and Ruff were not rerun for this evidence/documentation
stage. New evidence is checked for finite duplicate-free JSON, archive/receipt /
marker/invocation/source identities, counts, flags, budgets, links, diff and strict
OpenSpec. No study, audit or field evaluation is repeated during saved-data review.

- [Complete study (gzip)](experiments/0161-moving-study.json.gz), [separate audit (gzip)](experiments/0161-moving-audit.json.gz)
- [Study receipt](experiments/0161-study-receipt.json), [audit receipt](experiments/0161-audit-receipt.json)
- [Study attempt](experiments/0161-study-attempt.json), [audit attempt](experiments/0161-audit-attempt.json)
- [Saved-result summary](experiments/0161-result-summary.json), [summary analysis](experiments/0161-saved-summary-analysis.txt)
- [Verification and protected-file identities](experiments/0161-verification.json)
