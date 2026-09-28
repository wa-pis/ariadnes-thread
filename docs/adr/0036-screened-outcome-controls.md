# 0036 — Verify the synthetic screening-to-reader boundary

Date: 2026-09-14. Parent revision: `7be82e8`. Task3.9 remains open.

## Bounded implementation

Add a test-local `_consume_screened_control` beside the existing arc outcome
tests. It accepts only explicit clear/unresolved screening labels, checks
the shared deadline before and after consumption, and delegates recognized
reasons or a clear/no-reason outcome to the existing reader. An unresolved
outcome without a reason checks native completion but returns no state and
never opens history. Native failure, including while unresolved, remains
fatal; uncertainty cannot mask it. The label is a synthetic test input,
not physical evidence or a production safety certificate.

Twelve clear/unresolved, reason/no-reason and success/failure combinations
exercise the real reader. Both history properties raise on forbidden
access; a spy verifies completed-state consumption happens only on the
clear/no-reason path. Established dry-mass/Moon-impact rejection survives
a clear label and bypasses unsafe history. An unresolved successful call
returns None without inventing a collision reason. Six missing/invalid
screening cases reject before native reads. One additional control retains
epoch validation and deadline checks before and after native-flag access.
No control/evaluation/arc counter is incremented by synthetic consumption.

## Test-development finding

The first focused run had one test-fixture failure: two independent deadline
cases reused a budget while resetting its fake monotonic clock backward.
The existing production clock guard correctly rejected this. Give the
second independent synthetic operation its own budget; do not reset an
expired real operation or weaken the clock guard. The corrected focused
module has 70 passing tests in0.15 s, including19 new cases.

## Final verification

Full pinned suite:3131 passed in503.39 s (native164.91, portable68.00),
unchanged thirteen/zero native arcs. Ruff, strict OpenSpec, whitespace
and legacy isolation checks pass. The retained conditional clearance
diagnostic reproduces unchanged excluding its elapsed-time field. No new
native call, production change, dependency, model, tolerance or limit.

## Limits and next step

No production function, public status or result contract changes. This
tests caller-side control flow, not real interval evidence binding, native
stage safety, finite-burn behavior, or physical subdivision performance.
The existing conditional 1/16 s clearance remains separate evidence.

Before physical composition, bind any clearance to the actual interval,
initial state/error, model/resources and available native outcome; an
arbitrary clear label must never authorize a physical result. Next inspect
how existing analytic subdivision passes child endpoints and rejection
outcomes so those bindings can be tested without new native runs. Retain
all incoming uncertainties and discarded-parent budget consumption.
Task3.9 remains open; no targeting or longer coast is enabled.
