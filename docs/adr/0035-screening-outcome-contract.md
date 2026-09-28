# 0035 — Keep unresolved screening out of completed-state consumption

Date: 2026-09-14. Parent revision: `01b3850`. Task3.9 remains open.

## Call-site audit

All current external calls to `_read_trial_arc_outcome` are tests; there
is no production caller in `src`. The only source-module call from that
function to `_read_completed_arc_state` occurs when `safety_rejection` is
None. Its docstring explicitly requires independently established safety:
None means no supplied rejection reason, not proof of interval clearance.
This is an integration prerequisite, not evidence of an exposed production
unsafe-result bug.

The reader already preserves native failure, gives recognized safety
rejections precedence over final-epoch/history checks, and rejects invalid
reasons before native reads. Its unit tests guard these properties with
history accessors that raise. The native sampling test confirms an observed
burn rejection can stop early; the adaptive analytic test returns an endpoint
only for clear screening and None for impact/unresolved outcomes.

Decision0034 adds conditional ideal-coast clearance for one bound interval.
It must not become a global Boolean authorizing arbitrary native outputs,
different epochs, burns, resources or internal trial states.

## Required caller-side distinction

| Evidence/outcome | Completed-state consumption |
| --- | --- |
| Recognized rejection reason | Existing rejection reader; no unsafe history exposure; native failure remains fatal |
| Unresolved interval or missing applicable evidence | No safe endpoint; do not convert to None and call the completed-state reader |
| Explicit applicable clearance, no rejection, completed native call | Reader may validate epoch/state/mass; clearance alone does not bypass these checks |
| Expired deadline or work limit | Existing failure, no completed result; preserve all attempted-call counts |

An unresolved interval is not a confirmed impact and must not fabricate a
body-specific rejection count. A later clear screen must not erase an
already established rejection reason. These rules preserve the current
public statuses; no new public unresolved status is proposed here.

## Next bounded check

Add a small test-local composition control beside the existing outcome
tests, using synthetic simulator objects and an explicit screening outcome.
Make forbidden history reads fail immediately. Verify unresolved yields no
state and invokes no completed-state reader; recognized rejection preserves
the existing no-history path; explicit clearance still undergoes native
completion and epoch checks. Invalid or absent screening evidence must not
default to clearance. Keep this an analytic caller-contract test, not a
production safety policy or proof about real native stages.

Do not add a production certificate class, generic dispatcher, new reason
code or native run just to express this small check. Future physical
composition must bind evidence to its own interval/state/error/resource
context and retain all uncertainty and budget consumption before advancing.
Do not reuse the analytic adaptive fixture's fixed endpoint error for
physical arcs. Production integration and representative full-force
subdivision/time measurements remain prerequisites to task3.9 completion.

## Verification scope

Read-only audit of every source/test reader call, existing outcome tests,
analytic screen results and the active safety scenarios. Documentation
only: strict OpenSpec and whitespace checks pass. No full-suite rerun,
new numerical evidence, native calls or production changes. Latest full
suite remains3112 passed in502.97 s (native164.95, portable68.35).
