# 0094 — Reuse the research composer for central-column diagnostics

Date: 2026-10-04
Decision status: accepted (implementation approach for approved D10).
Implementation: complete and verified; live D10.3 study pending.
Scope / milestone: M3 research D10.2; no live D10 experiment yet.
Base revision: `88b8afc` plus this implementation and tests.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [0093](0093-central-column-study-proposal.md).

## Context and constraints

The approved D10 contract requires thirteen nominal evaluations, exact
seed-based signed probes and replay gates before assembling central columns.
Existing D7–D9 orchestration already supplies the authoritative scenario,
resource/target/settings binding, native composer, sampled guards and evidence
lifecycle. A new optimizer, force model or public API is out of scope.

## Options considered

- Duplicate the native pipeline in another driver: rejected; it would duplicate
  resource and failure handling already covered by regressions.
- Add a mutually exclusive private mode with separate arithmetic and budget:
  selected; preserve old mode limits and reuse the existing native pipeline.

## Decision and rationale

Add `--column-references D7 D9` to the private targeting experiment module.
The first reference is pinned 0086, the second pinned 0092; positional 0079
remains mandatory. Check all identities, the finite rank-six retained direction
and nonzero predicted norm before environment preparation. Historical D7 and
D9 source hashes remain separately labelled from current implementation hashes.

Use one D10-local 13/13/39 budget and shared 300-second cooperative clock.
Control attempts precede analytic validation. The baseline is checked against
all three references. Each positive probe replays its retained D7 boundaries
before its negative partner starts. All perturbations start from the original
seed with a fixed target and nominal settings in fresh matched environments.
Keep explicit column/sign/increment metadata even when command validation or
propagation fails. An already-closed seed does not skip this diagnostic.

The small standard-library arithmetic module stores complete central/forward/
even column pairs incrementally. Assemble a whole-matrix directional comparison
only after all six pairs. Compensated sums retain cancellation-sensitive
contributions. Record column and directional identity defects rather than
pretending floating-point identities are exact physical bounds. Compare the
central prediction against both retained D9 nominal slopes with the fixed
retained directional norm and <=0.10 exploratory criterion. Zero central norm
and nonfinite ratios have explicit unavailable reasons; nonfinite vectors abort.
No correction solve, rank computation, selection or tighter run is introduced.

## Consequences and revisit conditions

D7–D9 behavior and public CLI remain unchanged. A diagnostic pass is not column
accuracy, cross-profile qualification, mission closure, safety or strict M3
completion. Native D10.3 remains a separate single-run stage after all tests.
No new dependency, automatic retry, production setting change or automation
restart is permitted. Further probes or optimization require a scoped decision
based on the resulting evidence, including failure or timeout.

## Evidence and verification

246 focused checks pass in 3.66 s, including D7–D9 and native composer regressions.
Independent linear/quadratic oracles verify control order/units, known even bias,
central/forward identities, compensated cancellation, exact threshold acceptance
and failure, zero direction/denominator, nonfinite ratios/vectors and shape errors.
Manufactured orchestration verifies thirteen independent commands, fixed target,
nominal-only settings, fresh environments, all baseline and positive replays,
reference/resource mismatches, control/evaluation/arc limits, shared deadlines,
analytic/native/event failures, retained earlier pairs, exclusive finite output
and absence of solve/selection. These are not physical mission observations.

Full suite: 3,856 tests pass in 578.59 s. Ruff, strict OpenSpec, private CLI help,
local documentation links, diff and immutable legacy checksum checks pass.
Independent reconstruction of the retained D7 positive columns agrees within
1e-7 absolute scaled units; mirrored negative inputs in that check are synthetic,
not new native observations. All three pinned artifact hashes remain unchanged.
No live D10 run has occurred; physical consistency is not claimed by these tests.
