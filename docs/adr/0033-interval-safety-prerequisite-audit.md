# 0033 — Separate interval clearance from native trial handling

Date: 2026-09-14. Parent revision: `2532cd9`. Task3.9 remains open.

## Existing evidence and missing connection

`_check_conditional_full_force_coast_domains` already computes a uniform
relative distance floor for each of the eight bodies using the original
spacecraft position domain and source reach. Every floor is asserted
strictly greater than that body's guard radius from the pinned collision
resource. These are collision radii, not orbit-altitude or harmonic
normalization radii. That assertion alone is a property of a declared
domain, not evidence that a trajectory remains inside it.

Decision0032 separately rechecks conditional true-state domain inclusion
with the non-shrinking rounded incoming error radii over the fresh 1/16 s
interval. Combining those premises for the SAME interval, centres, source
coverage and resource gives conditional ideal-path clearance throughout
that interval. The final endpoint error tolerance is not the reason the
path is clear. Nor is a successful native completion flag.

No additional interpolation curve or collision model is needed to expose
this existing domain-based argument. The analytic adaptive test's chord
formula remains a separate control and must not be copied with its fixed
0.001 m endpoint allowance into a full-force mission.

## Native trial handling is a different obligation

`test_native_full_step_guard_can_miss_an_internal_crossing` demonstrates
a coast crossing missed even by sampled native stages. Its burn variant
can latch an observed rejection, but sampling/latching is not continuous
clearance. `test_native_distance_event_localization_requires_detection`
separately tests event localization; root finding does not detect a wholly
missed event by itself.

`_run_native_arc` returns explicitly unclassified output.
`_classify_environment_trial_state` classifies a single sample only.
`_read_trial_arc_outcome` requires its caller to establish between-step
safety before invoking the completed-state reader. None of these supplies
a production interval-screening policy automatically. Native internal or
rejected trial states can differ from the ideal path; the conditional
ideal-path argument must not be relabelled as safe native-stage evaluation.

## Next bounded implementation

In the existing fresh diagnostic, bind all eight original distance floors
and collision guard radii to the same source/PCK coverage and rounded
incoming-ball domain closure. Report each positive clearance margin with
downward rounding, assert its direction, retain the pinned collision
resource identity, and distinguish conditional ideal-coast clearance from
native-stage or mission safety. Preserve mass2000 kg, dry mass1000 kg and
thrust-off scope; no general finite-burn mass conclusion follows.

No new native query, propagation, coast extension or safe-result reader
is needed for that report. Preserve the existing endpoint control rather
than optimizing the weaker fresh one. After the report, audit the actual
interval-screening/native-rejection composition boundary before adding
any new native arcs. In a later composition, retain every incoming error,
discarded parent and rejected attempt in the shared budget; do not assume
an endpoint tolerance remains uniform across an entire mission.

## Verification scope

Read-only source audit of the full-force domain checks, native adaptive
and sampling controls, and trial-state/output readers. Documentation only;
strict OpenSpec and whitespace checks pass. No test or production code
changed, no native runs were added, and full pytest was not rerun. Latest
implementation evidence remains 3112 passed in500.78 s (native163.70,
portable66.70). No new numerical clearance certificate, task completion,
tolerance revision or production safety policy is claimed.
