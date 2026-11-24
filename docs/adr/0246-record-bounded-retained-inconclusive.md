# 0246 — Record the bounded retained inconclusive result and stop

Date: 2026-11-24 (Europe/Samara)
Decision status: accepted
Implementation: one fixed P6 execution and separate audit complete; attempt consumed
Verification: complete inconclusive producer, verified independent point audit; strict/local evidence checks pass; selected witness goal not achieved
Scope / milestone: one ADR0243 retained analytical attempt within M3; no physical propagation
Base revision: `33fea7c8b9c2414ff16dda2ec28ecf298a13293e`, clean `dev` at launch
Qualified code: `aad842f4332cc23c89fa47d06ecbaa4f04077064`; CI45358338765
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-use-bounded-scalar-search-only-to-propose-an-analytical-witness), [design](../../openspec/changes/refine-physical-trajectory/design.md#p4-one-retained-bounded-attempt-2026-11-24), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md)
Supersedes / Superseded by: none; records the one consumed execution authorized by ADR0243/0244 after ADR0245 qualification

## Context and constraints

The user selected one admissible analytical command pair on fixed saved real
inputs with independent audit as the measurable goal. No99%probability or physical
trajectory agreement is inferred. [ADR0245](0245-qualify-retained-dispatch-lifecycle.md)
completed the full P5 qualification, exact local/CI inventory and immutable
readiness before this launch. The source and closure commits were pushed to
`origin/dev`; checkout was clean. [ADR0243](0243-design-one-retained-bounded-attempt.md)
and [ADR0244](0244-start-bounded-autonomous-preparation.md) supply the unchanged
once-only contract and conditional standing execution authority.

Question: does the fixed bounded proposer find a pair that passes every original
independent point/literal-command/guard/mass gate on these saved inputs? Keep
candidate d0001-t0035, four original raw pins, reference/epoch words, positive Moon
branch and both Mars signs on[150°,152°]. Retain129phase/258signed-slot limits per
arithmetic path,30s producer and separate30s audit,4MiB cumulative source/input
per reader, exact0242 runtime/read caps and4MiB aggregate new evidence. No SPICE,
new state acquisition, force evaluation, integration, interval proof or R5.60.

## Options considered

- Relabel optimizer success or independent audit success as an admitted pair:
  rejected; admission is decided by the unchanged physical-command gates.
- Retry, enlarge the budget, change inputs or start another diagnostic after no
  witness: rejected by the one-shot stop policy; these need a new user decision.
- Preserve the complete bounded outcome and independent audit, state its limited
  scientific meaning, then pause automation: selected.

## Decision and rationale

Run the qualified no-argument0245 `retained` command exactly once. It reserved the
fixed [namespace](experiments/0243-p3-retained/invocation.json), dispatched one cold
producer and, after its complete authenticated exit2, one separate stdlib audit.
There was no retry, worker-only invocation, optimizer replay or late evidence edit.

The [producer](experiments/0243-p3-retained/producer/report.json) completed with
`inconclusive/invalid`, disposition `inconclusive`, reason `no-verified-witness`,
and no witness. The [independent audit](experiments/0243-p3-retained/audit/report.json)
verified all13 recorded points, their dispositions/counters and no eligible pair;
its status is `recorded-point-audit-verified`, optimizer calls0. Its raw completion
binding matches the exact producer completion. The parent returned the expected
analytical-inconclusive exit2, not a partial/invalid process failure.

The positive-sign minimizer completed8callbacks and proposed151.33118995827647°
(exact word `0x1.2ea991baef1f4p+7`). The final point reports6157.712787309595m/s
against the original6117.706618414368m/s ideal budget; the pair fails
`commanded-dry-floor`. Independent reported totals/budget and literal-command
checks agree; this does not satisfy the unchanged500kg mass floors. The negative
sign stops at its first guarded objective, with no candidate proposal. These are
recorded finite observations: Brent's completion and a guarded sample do not
prove global optimality, absence of a pair elsewhere, or continuous refusal.

The selected admissible-pair goal remains unmet. P6's execution-and-audit task is
complete, and its namespace consumes the authorization. Automation `ariadna-m3`
was immediately set to PAUSED on this terminal outcome. No scientific successor,
repeat or contract change is authorized by this result record.

## Consequences and revisit conditions

The result establishes neither an executable pair nor a physical Moon-to-Mars
join, strict M3 closure, mission safety or success probability. A changed Mars
phase does not adopt a new target or open the original R5.60. Any next research
contract requires the user's scientific choice; keep all earlier failures,
qualified sources and this result immutable. Do not automatically expand the
search or loosen mass/guard/command/state tolerances to obtain success.

## Evidence and verification

The immutable [result summary](experiments/0246-retained-result.json) binds all
nine raw namespace files, the qualified source/binding/readiness, four inputs,
resource counters and operational stdout/stderr. Full parent elapsed time is
1.048381667s: producer stage0.875374083s, independent audit stage0.173006333s.
Worker final completions report0.847333083s and0.165655625s; both parent stage
clocks include authentication/readback and remain below their separate30s caps.
Work is13phases/26root+pair slots per path:3anchors,8positive/1negative objective
callbacks,1final and zero blocked attempts. Audit performs no optimization.

Namespace evidence is312,980B, below4MiB including bounded terminal telemetry.
Charged source/readback is2,464,002B producer,1,884,640B auditor and813,170B parent,
each below4MiB. Runtime reads213,095,921/38,953,165B remain below the unchanged
340,344,044/71,719,216B caps. Raw chains, counters, source/runtime pins, zero
prohibited-work flags and all1,069 pre-existing non-Markdown files are checked.
Conda's generic stderr line reports the expected nonzero exit2; it is not evidence
of a worker crash or failed independent audit.

A separate read-only evidence review checks the raw chain/receipt bindings,
source/readiness/protected-file identities and bounded result interpretation;
it does not rerun any numerical audit or optimizer. Local links, finite JSON,
hashes, whitespace and strict OpenSpec are checked for this recording. Runtime
code is unchanged, so successful P5 regression/CI checks are reused without new
pytest, SPICE or scientific reruns. P5 qualification remains separate from this
negative analytical result; no percentage is derived from passed tests.
