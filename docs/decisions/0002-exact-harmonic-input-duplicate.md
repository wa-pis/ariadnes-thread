# 0002 — Exact harmonic input duplication is observed

Date: 2026-09-13. Milestone: M3, task 3.9.

Status: accepted evidence supporting a local-reuse experiment; no optimization yet.

Follow-up to [0001](0001-inventory-runtime-investigation.md), not a replacement
of its deadline or qualification constraints.

## Question and method

Are repeated harmonic-error calls actually supplied with identical inputs?

Base revision: `d5cf251`; native inventory and production code match
`fd4dafd973d81a0c773112145d8da4ff3b16675d`. Unfinished midpoint tests and
OpenSpec edits remain in the working tree but are not part of this commit.
Use the pinned Conda `space-nav` environment and its existing SPICE resources.

The [diagnostic driver](experiments/0002-check-duplicates.py) wraps only the
test helper in a temporary process. It compares exact scalar representations
and array shapes, dtypes and bytes for every scientific argument, asserts the
same budget object and checks the original deadline. It evaluates unseen
inputs normally and deliberately raises before evaluating the first duplicate.
It does not cache or return a substituted scientific result.

Reproduce from the repository root:

```sh
conda run --no-capture-output -n space-nav python docs/decisions/experiments/0002-check-duplicates.py
```

Expected diagnostic outcome: exit 1 with `DIAGNOSTIC_STOP` and an observation
identifying the duplicate. A deadline or any other error is not that outcome.
This driver is an opt-in experiment, not a passing regression test.

## Observation

The [retained observation](../../tests/data/m3_harmonic_duplicate_observation.json)
records a stop in 72.32 s after two native arcs. Call 3 exactly matched call 1:
Moon degree-150 harmonic-error inputs, including the observed native terms.
The first uncached evaluation took 52.590835167095065 s. Call 2, the distinct
Mars degree-20 calculation, took 0.15060662501491606 s.

## Decision and limitations

Exact duplication is now empirically established for this pair. Proceed to a
test-local reuse implementation keyed by all dependencies; a global cache and
weaker arithmetic remain unnecessary. This evidence strengthens the hypothesis
in 0001 but is not a proof that all repeated calls match.

The duplicate was not recomputed: no repeated-result parity comparison or actual
speedup was measured. The inventory did not finish. Existing scientific gates,
the 300 s budget and all native controls must remain unchanged. Numerical model
and tolerance impact: none; only an instrumented experiment was run.

## Required next verification

WHEN reuse is implemented, THEN compare exact results against uncached evaluation,
verify misses when each dependency changes, prevent cached-result mutation, and
preserve validation and deadline checks. WHEN evaluating speed, THEN retain an
unprofiled complete-run result and native counts under the original limits, followed
by focused tests, full pytest, Ruff and strict OpenSpec before code completion.
Keep task 3.9 and the midpoint unit incomplete until their checks pass.
