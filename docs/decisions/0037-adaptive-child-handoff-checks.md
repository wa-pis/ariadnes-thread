# 0037 — Verify child state lineage in existing adaptive controls

Date: 2026-09-14. Parent revision: `a6b82c0`. Task3.9 remains open.

## Bounded change

Instrument the existing seven analytic adaptive controls without changing
their force model, subdivision algorithm, native calls or classification.
Copy each native input before propagation and assert it is unchanged.
Record completed native-call input epochs/states, then require the record
count to match the existing native counter, including discarded parents.
The original root state must remain unchanged on normal and limit exits.

For every completed right-subtree invocation, compare its first recorded
native input against the accepted left endpoint and exact child interval.
Require the left endpoint to remain unchanged and prevent returning the
discarded parent's endpoint object. A non-clear left outcome carries no
state; a right result carries a state only if its outcome is clear.
All original analytic position/velocity/mass and limit checks remain.

## Coverage and limits

The existing normal-case diagnostics expose the actual exercised branches:

| Case | Native calls | Discarded parents | Completed child-handoff checks |
| --- | ---: | ---: | ---: |
| Straight impact | 5 | 4 | 0 |
| Straight clear | 1 | 0 | 0 |
| Curved impact | 2 | 1 | 0 |
| Curved clear | 1 | 0 | 0 |
| Tangent, unresolved | 8 | 6 | 1 |

Both call-limit and deadline controls retain exactly two native calls and
no terminal state. Thus these seven cases use21 calls per complete test
invocation, including rejected/discarded attempts; focused and full-suite
runs are separate invocations, not work hidden inside one shared budget.

The tangent control exercises a real accepted-left to right-subtree
transfer but ultimately remains unresolved. The two clear cases need no
subdivision, so they do NOT verify a successful multi-leaf return path.
Keep that coverage limitation explicit. The test-only fixed0.001 m error
is still checked against known analytic motion and is not transferable to
arbitrary physical arcs. No native-stage or mission safety follows.

## Verification

All seven focused controls pass in3.12 s. Full pinned suite:3131 passed
in505.61 s (native inventory166.13, portable68.94). Focused and full
lineage diagnostics agree excluding timings; earlier adaptive statuses,
native counts and analytic error observations are unchanged. The retained
physical conditional-clearance diagnostic also reproduces excluding time.
Ruff, strict OpenSpec, whitespace and legacy isolation pass. No production,
dependency, force-model, tolerance or budget-limit change. The full-force
inventory still uses thirteen/zero native arcs, separate from the analytic
adaptive calls listed above.

## Next bounded check

Exercise successful two-child completion and a blocked left child with
deterministic synthetic endpoints that distinguish the parent, left and
right results, without another native propagation. Check that the chosen
endpoint and screening context follow the actual child lineage before
proposing physical composition or larger native limits. Do not infer this
missing branch from the unresolved tangent control or two unsplit clears.
