# 0200 — Prepare the retained lunar-to-Mars interface audit

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted within [ADR0199](0199-design-retained-lunar-to-mars-interface-check.md).
- Implementation: R5.53 complete; R5.54 unexecuted.
- Verification: artificial full-volume audit, focused checks and guarded regression passed.
- Scope: offline audit of the archived model B departure packet and retained receiving references.
- Base revision: `bc447146c689f81f778ed3f1e2fc7c6bd5148863`, exact prepared sources pinned in the verification manifest.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-check-retained-lunar-to-mars-interface-readiness), [design](../../openspec/changes/refine-physical-trajectory/design.md#r553-prepare-the-retained-lunar-to-mars-interface-audit-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

ADR0199 fixes the tighter RK4 terminal coepoch, five archive members,
the 121 ideal epochs, the receiving-side reports and a 15 s shared
deadline. The archived R5.51 result remains unchanged. This stage
prepares the audit and qualifies its limits using artificial inputs.

## Options considered

- Re-run the full R5.51 audit or expand the archive: unnecessary for
  the pinned endpoint and outside the selected offline workload.
- Use identifiers and checksums alone: insufficient to check the
  endpoint's state words, relative direction or the receiving inventory.
- Authenticate selected members and replay only the endpoint
  arithmetic and epoch inventory: selected.

## Decision and rationale

The private stdlib worksheet validates the recorded manifest and
receipt chains, authenticates one bounded shard at a time, counts
all lines and decodes just the pinned rows. It verifies the
spacecraft, epoch and mass words and checks the common and mesh
direction signs using exact rational arithmetic and independent
Decimal80 radius and radial speed. The receiving inventory uses
stored epochs and explicit eligibility reasons. A missing compatible
receiver can coexist with a verified source; continuity residuals
remain null. Invalid evidence cannot certify the source.

The isolated child rejects scientific imports, SPICE loads and
kernel-file accesses. The launcher reserves an exclusive result
directory, enforces the shared deadline and binds the report to
its attempt and parent receipt; a failed or late receipt cannot
certify the result. Synthetic mode accepts only a marked fixture
tree. Retained mode needs the pinned design, exact prepared source
bytes, clean synchronized `dev`, a fixed unused result directory
and separate R5.54 authorization bound to the revision and digests.

## Evidence and verification

The full-volume artificial archive has **218,972 lines in five
shards**, each exactly 16 MiB raw. It used 83,886,080 raw bytes and
26,110,834 gzip payload bytes (99.6% of the
compressed cap). Distinct synthetic records fill non-selected rows;
the selected rows and 121 ideal epochs exercise the actual audit.
The complete launch and finalization took **0.297 s of 15 s**
with 108.0 MiB child peak RSS and 10,130
bytes of attempt, report and receipt. Fixture generation and
separate result readback are outside the launch timing. The
receipt-bound report authenticates the artificial source, finds no
exact ideal coepoch or compatible receiving state and carries four
null continuity residuals. It establishes no result for real data.

The fixture, attempt, report and receipt remain at
`/Users/agrudin/dev/my/ariadna-evidence/R5.53-verified` outside Git. The
[verification manifest](experiments/0200-verification.json) binds
their digests, workload, timing and the tested sources.

All 30 focused tests passed, including corrupted or missing
inputs, invalid or duplicate selectors, bitwise and metric
disagreement, a coeval but ineligible target, source/receiving
status separation, hard resource caps, timeouts, receipt tampering
and exclusive output. The [offline guard](experiments/0189/pytest-offline-guard.py.txt)
full suite had 6,247 passed, 494 skipped in 131.43 s;
Ruff, strict OpenSpec, local links and diff passed.

## Consequences and revisit conditions

The implementation is ready for one separately requested R5.54
audit on frozen data. No R5.54 attempt, SPICE query, force calculation
or trajectory propagation was performed. The artificial evidence
does not authenticate the real outgoing state or establish
continuity to Mars. The original mission gates are unchanged.
