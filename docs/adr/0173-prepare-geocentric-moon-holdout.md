# 0173 — Prepare the geocentric Moon holdout

Date: 2026-11-10 (Europe/Samara)
Decision status: accepted implementation of [ADR0172](0172-design-geocentric-moon-holdout.md).
Implementation: R5.26 complete; R5.27 not run.
Verification: synthetic capture and analysis, saved metadata and guarded regression.
Scope / milestone: M3 R5.26; private preparation of the 16-epoch source holdout.
Base revision: `60c865f74b765582d094cdd0a46f069d8be2aba1`, clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md),
[tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none.

## Context and constraints

[ADR0171](0171-frozen-coast-moon-screen-passes.md) passed conditionally on
the saved R5.24 rows. R5.26 prepares the missing Moon/Earth source check
under the unchanged ADR0172 limits. Only synthetic provider returns
and archived metadata are used for verification. The 16 missing live
states were not acquired and the frozen fields were not recomputed.

## Options considered

- Extend the production ephemeris provider or use the propagation
  runner: unnecessary for the sampled source question.
- Reuse the tested kernel, selector and ledger helpers in a private
  capture and validate the finalized evidence in a separate offline
  analysis: chosen, with no new dependency.

## Decision and rationale

The [loader](experiments/0173/ariadna_moon_holdout_inputs.py) pins the
16 exact `hi` words, their 21 mapped observations and 28 bound
evidence files. It checks the finalized R5.24 report and journal,
the retained references and both earlier archive bindings without
evaluating ephemeris records or fields.

The [collector](experiments/0173/ariadna_moon_holdout_capture.py) uses the
pinned kernel inventory on both sides of the capture. It verifies one
Moon segment selector before each Moon/Earth state call. The completed
sequence has 63 explicit operations, including setup and both inventory
snapshots. The separate verifier checks each archived call's arguments,
raw return, order, kernel/segment identity and timing.

The [offline analyzer](experiments/0173/ariadna_moon_holdout_analysis.py)
preserves the three independent classifications: exact SI parity against
the saved reference (1 mm and 1 µm/s), position bits against the proxy,
and a single rounded sum against archived Moon/SSB. Tests cover both
inclusive parity boundaries, a one-step proxy mismatch despite passing
parity and closure, and opposite signed zeros. A finite numerical miss
does not consume the remaining valid observations; an invalid operand
or deadline stops the check and records what is unavailable.

The [runner](experiments/0173/ariadna_moon_holdout_run.py) keeps phase
outputs exclusive, validates capture and receipt hashes before analysis,
rechecks the frozen identities and retains the raw journal on failure.
Synthetic tests cover malformed input, capture tampering, late returns,
watchdog expiry, the inclusive final flush deadline and rejection of a
second attempt. No actual live phase or runtime budget measurement was
made during preparation.

## Evidence and verification

- [Focused pytest](experiments/0173/pytest-focused.txt): 69 passed on
  synthetic data and saved metadata. No native queries.
- [Guarded regression](experiments/0173/pytest-guarded.txt): 5985 passed,
  407 skipped under the unchanged
  [SPICE guard](experiments/0170/pytest-no-spice-guard.py.txt).
  The [skip inventory](experiments/0173/pytest-guarded-skips.tsv) records
  exclusions. No unrestricted regression was run.
- The [verification manifest](experiments/0173-verification.json) pins
  tested and reused code, original inputs and test evidence. Ruff,
  strict OpenSpec, diff, links and hashes passed; 708 protected paths
  including previous evidence and `moon_to_mars.py` are unchanged.

## Consequences and revisit conditions

R5.27 still requires a separate execution instruction. The synthetic
success verifies the preparation, without establishing whether actual
Moon/Earth returns match the proxy. R5.24 remains conditional, R5.17
remains failed, and strict M3 and mission safety remain open. Automation
stays paused.
