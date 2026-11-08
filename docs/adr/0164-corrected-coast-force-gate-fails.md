# 0164 — Corrected coast completes but source-inclusive force gate fails

Date: 2026-11-09 (Europe/Samara)
Decision status: accepted bounded execution and preservation of negative evidence; scientific acceptance failed.
Implementation: unchanged R5.16 helpers reused; no runtime, test or dependency changes.
Scientific verification: partial; both solves and sampled trajectory comparisons complete, required Moon overall force gate fails.
Scope / milestone: M3 R5.17, corrected real-input300s A coast under ADR0162.
Base revision: `e3d07ed19b1cca06484947087a1dc83d637141c7`, initially clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [ADR0162](0162-corrected-real-integration-contract.md) after [ADR0163](0163-prepare-corrected-integration.md), preserving all historical results.

## Context and constraints

The user separately authorized one R5.17 execution, result verification and
ADR/OpenSpec/commit/push. No competing Ariadna study/test/audit process or0164
evidence existed. The exact tested source hashes, initial r0/v0/t0,300s interval,
seven50s output nodes, Sun/Moon A force order and GMs, Earth guards, live geometric
SPICE provider,13 ordered kernels, solver profiles and all gates/caps stayed fixed.
No native spacecraft propagation, GM acquisition, optimizer or B-force run was made.

The question is whether the combined numerical candidate can complete and pass
the original sampled numerical gates. It does not ask whether a Moon-to-Mars
mission is feasible. Retained native histories have the explicit missing0148
final identity; no new process can repair it.

## Options considered

- Execute the accepted contract once, then audit the complete saved bytes:
  selected using the verified R5.16 implementation.
- Tune the force tolerance, subtract the source discrepancy, change ephemerides
  or repeat after failure: excluded by ADR0162; retain the failure instead.

## Execution and measurements

The [exact parent invocation](experiments/0164-corrected-invocation.txt) verifies
the preparation manifest SHA256
`518eea292547b4bfc4a379e3e8a2ce63632d49fcdef2761d504d09a34d485844`
and all ten tested helper/test hashes. The [baseline](experiments/0164-baseline.json)
binds640 tracked files; their bytes and clean Git status stayed unchanged across
both processes. One fresh pinned Conda Python process ran the study with `-I -B`;
one separate fresh stdlib-only process ran the audit with `-I -S -B`.
Each received its own unchanged external parent monotonic timestamp immediately
before child creation. The60s/10s scientific budgets include startup, imports,
identity checks, all computation and final flush/receipt checks. Parent65s/15s
watchdogs did not fire and did not extend scientific deadlines. No retries.

| Measurement | Study | Separate saved-data audit |
|---|---:|---:|
| Outcome / finalization | failed / passed | partial / passed |
| External process time, s | 2.7041840832680464 | 1.6426147911697626 |
| Before-flush elapsed, s | 1.7794972080737352 | 1.5797519581392407 |
| Receipt elapsed, s | 2.4967775833792984 | 1.6232542912475765 |
| RHS attempted/completed | 5132/5132 | 5132/5132 inspected |
| Trial descriptors attempted/completed | 424/424 | 424/424 inspected |
| Binary64 source fields attempted/completed | 10292/10292 | 10292/10292 rebuilt |
| Selected three-body checks | 42/42 | 42/42 rebuilt |
| Selected source rows attempted/completed | 28/27 | 28/27 rebuilt |
| Decimal source fields attempted/completed | 224/224 | 224/224 rebuilt |
| Sampled A totals attempted/completed | 13/13 | 13/13 rebuilt |

Both solver attempts return success at local300s with all seven outputs. Normal
uses790 RHS/64 accepted/zero rejected trials. Tighter uses4342 RHS/341 accepted/
19 rejected trials. All5132 RHS complete;15417 live state requests include the
shared21-call node table. All42 native-node guards pass. There is one initial
kernel setup and one identity snapshot containing15 explicitly counted metadata
API calls; final identity is unavailable because validation stops earlier.
These counts are not an exact count of hidden transitive native/FFI calls.

All21 trajectory comparisons pass. Maxima across the seven nodes are:

| Comparison | Position error, m | Velocity error, m/s | Required limits, m / m/s |
|---|---:|---:|---:|
| Saved native h1/h0.5 | 0.0001930101110942614 | 3.438942231775422e-8 | 0.01 / 1e-5 |
| Saved native h0.5/corrected tighter | 0.0001632761730883232 | 2.730216742863825e-8 | 0.01 / 1e-5 |
| Corrected normal/tighter | 0 | 3.494491245742145e-9 | 0.001 / 1e-6 |

The zero exported position difference is equality of rounded Cartesian outputs,
not equality of internal q operands or proof of zero physical error.

## Earliest checked failure and interpretation

After both solves and all trajectory comparisons, the predetermined high-precision
validation fails on normal profile RHS ordinal6 at local0.25s, hi=978995455.4804223
TDB seconds since J2000 and lo=0. This is the first required failure in validation
order, not the first continuous-time divergence. Thirteen observations complete;
the fourteenth retains a partial assessment. Tighter-profile sampled source/force
qualification and the failing sample's A total are unavailable; no backfill.

Moon's overall force error at100 digits is
`1.581286302871407357984508839058774664557205075828021519665815603211344227625280611391024376664081192e-11 m/s^2`,
against the unchanged envelope
`1.452234547810967980740932995477535882860544531723828405816975326618336532251078509508182963346807723e-11 m/s^2`.
The ratio is1.0888642645604087:8.8864% above the envelope. The80-digit classification
is identical. Returned-geometry error3.7108634870920695e-17m/s^2 passes; source-state
parity, component/domain guards, precision convergence and signed telescoping pass.
The saved Moon position discrepancy is1.6645034321071922e-5m, velocity discrepancy
1.4696601137466275e-12m/s. Source-state parity passing does not imply force passing.

The saved signed attribution is dominated by the source discrepancy: native-source
contribution components are approximately(1.01314e-11,1.12820e-11,-4.48494e-12)m/s^2,
relative assembly is about1.31e-16m/s^2 and field evaluation about3.71e-17m/s^2.
At this sample lo=0 and the saved rephasing/drift contribution is zero. This
localizes the failed gate within the saved decomposition; it does not establish
the underlying cause of live SPICE versus retained-polynomial source differences,
a uniform source-error bound or historical R5.3 causality. No source-floor
subtraction or new allowance is applied. The deferred check did not stop an
earlier integration stage; it rejected later qualification of already saved solves.

## Decision, consequences and revisit conditions

Retain this as a consumed once-only execution and independently audited negative
result. The auditor confirms all-RHS arithmetic and the available sampled prefix,
returns partial with scientific_verified=false, and makes zero scientific imports,
native calls, queries, kernel loads or new propagations. Finalizations pass;
there is no deadline/count failure. Only the initial runtime identity is available.
Full ADR0162 scientific acceptance and R5.17's scientific checkbox remain open.
Do not retry or tune this contract. A read-only diagnosis of the exact saved
source discrepancy is the next useful question before proposing any separately
justified contract; no new scientific experiment is authorized by this record.

R5.3, Earth-force sensitivity, unsampled source selection/trajectory accuracy,
continuous safety, full-force/finite-burn mission feasibility and strict M3 remain
open. M4-M6, ML, new search and UI qualification remain deferred. Automation
ariadna-m3 stays PAUSED; production/dependencies and moon_to_mars.py are unchanged.

## Evidence and verification

The [complete study](experiments/0164-corrected-study.json.gz) and
[separate audit](experiments/0164-corrected-audit.json.gz) are lossless gzip copies
of the exact original UTF-8 bytes, without removed operands, flags or provenance.
The audit ran on the original JSON, whose SHA256 is
`ddebc41daa32141a57c3e9d9d1addb216a20864a0d68a32a78102dfb15781b82`.
Uncompressed originals stay outside Git; the archives are the retained copy.

- [Study receipt](experiments/0164-study-receipt.json), [audit receipt](experiments/0164-audit-receipt.json), [study attempt](experiments/0164-study-attempt.json).
- [Study parent attempt](experiments/0164-study-parent-attempt.json), [receipt](experiments/0164-study-parent-receipt.json); [audit parent attempt](experiments/0164-audit-parent-attempt.json), [receipt](experiments/0164-audit-parent-receipt.json).
- [Saved-data summary](experiments/0164-result-summary.json), [assertion-based summary analysis](experiments/0164-saved-summary-analysis.txt), [verification manifest](experiments/0164-verification.json).

Reuse ADR0163's301 focused/6182 full passing tests and Ruff on exactly unchanged
code/test bytes. Runtime tests and Ruff are not rerun for this evidence/docs
stage. Verify finite duplicate-free JSON, exact archive round trips, receipt/
marker/invocation/source/protected identities, available counts/flags/gates,
local links, diff and strict OpenSpec. Saved-result review does not repeat a
study, audit, force field or reference calculation.
