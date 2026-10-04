# 0100 — Reuse damping for the retained central direction

Date: 2026-10-04
Decision status: accepted.
Implementation / verification: D12.2 complete; no live D12 study in this stage.
Scope / milestone: M3 research D12.2, no production targeting.
Base revision: `40f8396`, pushed before implementation.
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
Supersedes / Superseded by: none; implements [0099](0099-central-direction-damping-contract.md).

## Context and constraints

D12 has the same two-fraction schedule and budget as D8, but a different retained
direction and evidence contract. D11's negative full-step result supplies that
direction; no new solve or derivative probes are authorized.

## Options considered

- Copy the damping loop or build a general optimizer: rejected; duplicates
  existing scheduling, dynamics and stop semantics without a new requirement.
- Reuse D8's loop/budget with a D11-specific input verifier: selected; preserves
  old entrypoints and scientific gates while bounding the new research mode.

## Decision and rationale

Add the private mutually exclusive `--central-damping-reference` option.
Existing modes remain unchanged. The verifier checks pinned 0079/0098 identity,
completed D11 runs, reconstructed raw residuals/improvement, cap and SI unit
conversion, recorded prediction and the retained linear equation. SVD checks
the matrix's singular values/rank but does not solve for a new step. Algebraic
roundoff checks use rtol=1e-10 and atol=1e-7 in dimensionless scaled quantities;
these are serialization/algebra checks, not relaxed physical replay gates.

Reuse the existing independent seed-based half/quarter commands, alpha-dependent
decrease/closure rule, fresh environments, canonical/analytic/native guards,
first selection and frozen tighter repeat. Record a D12 tighter status so an
unavailable agreement cannot be confused with non-improvement. No fallback
after tighter failure or disagreement. Current/historical source hashes remain
separate. One 300-second clock and existing 3/4/12 limits apply; no dependency,
public API, UI, force model or production setting change.

## Consequences and revisit conditions

This enables one approved experiment, not an improved or qualified mission.
Any negative result remains useful evidence; do not automatically shrink steps
again or start iterative research. Strict M3/task 3.9 stay open, automation paused.
Revisit only after the separately retained D12.3 study is independently checked.

## Evidence and verification

287 focused D7–D12/composer tests pass in 3.19 s. New cases check independent
commands/thresholds, both selection branches, no improvement, frozen tighter
failures and disagreement, no fallback, identities/algebra/raw residuals,
nonfinite rejection, closed baseline, analytic rejections, shared deadline and
exclusive finite output. Tests prohibit both `solve` and `lstsq` during import
and correction helpers throughout D12 orchestration. Existing native guards and
all earlier research regressions are reused. Ruff, strict OpenSpec, diff and
unchanged legacy checksum pass. Full suite: 3,947 tests pass in 609.93 s.
The next step is the single approved D12.3 study; no native study in this stage.
