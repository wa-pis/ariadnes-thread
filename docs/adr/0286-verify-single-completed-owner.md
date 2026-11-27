# 0286 — Verify one synthetic completed owner

Date: 2026-11-27 (Europe/Samara)
Decision status: accepted
Implementation: F18.16 completed; independent saved-result review passed for this single synthetic owner only
Scope / milestone: M3, one forward completed-owner native conformance episode
Base revision: c9b8b565eb39281a6228d28112932398c31edf5d;1607tracked files/Git status frozen
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md)
Supersedes / Superseded by: none; executes the choice in [0285](0285-authorize-one-completed-owner.md) and preserves [0281](0281-design-single-completed-owner.md)/[0283](0283-map-completed-owner-controls.md)/[0284](0284-qualify-completed-owner-controls.md)

## Context and constraints

The user separately authorized one conditional F18.16. The completed producer,
independent auditor and eight controls plus external gate were already qualified
on artificial data. The remaining question was whether the real retained native
kernel could complete the original forward(True) synthetic arc, expose original
completion metadata and return its same-owner chronological-last endpoint.
This episode uses elapsed0–1000s, unchanged seven-state/RKDP87/binary64 literal
inputs, SSB/J2000 orientation and SI state units. It is not a mission ephemeris.

## Options considered

- Treat earlier artificial PASS as native admission: rejected by the existing
  contract. Fresh actual read-only admission and independent readback are required.
- Use the existing fixed controls with a narrow checked operator: selected. One
  retained image, no provisioning/acquisition, no retry or changed scientific gate.

## Decision and rationale

Accept the [result](experiments/0286-single-completed-owner-result.json) only for
one synthetic completed owner. The [immutable archive](experiments/0286-single-completed-owner-evidence.zip)
contains90members,727536expanded/256711compressed bytes: exact operator sources,
pre-invocation corrections,8case logs, original raw episode/postpacket records,
actual tool-return copies, canonical saved audit and independent reviews.
No native library, real resource payload or fabricated3.71MB fixture is archived;
the fixture generator/assertions are retained. The result's `qualified_controls`
field is the four-operator manifest pin; the exact eight runtime controls and
separate gate remain bound in the raw profile/decision and0284archive.

The minimal new operator was independently reviewed before one artificial
invocation:8/8cases,0errors/failures/skips, observed0.6320940828882158s<120s.
It exercises real prepare/reviewer/invoke logic on fabricated53source/10native/
11resource/25ledger/86history inputs, explicitly mocking Git/committed-authority,
OS mount and native dispatch. This does not qualify actual native authority.
Static findings were corrected before the first invocation and preserved: mixed
49absolute+4relative source keys, cleanup despite failed failure-receipt writing,
completed packet path, six READY counts, failure wording and fake subprocess guard.
Previous0284failures and unchanged57/212/8688campaigns were not repeated.

The actual original clock started before the new namespace write or ROmount.
Preparation returned at14.801022625062615s, independent actual review after file/
directory fsync at26.6109890001826s, and its separately observed tool-return record
at33.42616608319804s. The gate directly admitted once; native consumption was
49.032074083108455s<600s. Saved pending/PASS records were never used alone.
All53source/10native/11resource/25ledger/86historical identities and exact controls,
environment/private interpreter/fixture inputs were preserved, with0new acquisition.

The one native packet passed after its own final directory durability at
3.5246821250766516s<60s. Producer finalization was3.4584164996631444s<45s;
the original audit/finalization phases and all byte caps passed. It reported one
context/factory/integration-attempt/metadata/visitor,52acceleration callbacks and
native function evaluations[39], kept distinct. Ten markers total1752bytes.
Metadata confirms successful exact-condition termination, correct seven-state
IDs and SSB/J2000; the selected endpoint is hour0/remainder1000s. The independent
Fraction(binary64 literal0.1) polynomial accepted position norm<=0.001m, velocity
norm<=1e-6m/s and mass difference<=1e-9kg. SPICE queries/optimizer/real-archive
reads were0 according to the fixed probe counters.

After detach, one separate guarded stdlib-only canonical saved audit also passed:
0.07666412508115172s<10s,10markers, reportSHA
`389c34a2813686a6f229bf0640a604543a006428f77e049ab78700ad11ada029`.
It neither extends the original clock nor creates another native episode. The
independent saved envelope review accepted actual admission/consumption, counts,
outer finalization and preservation. Exact returned observations stay separate
from prefinal disk receipts and later housekeeping; no clock is reconstructed.

## Consequences and revisit conditions

F18.16 is complete within its fixed scope. Its namespace is consumed and must not
be cleared or resumed. Groups8313/8320 were recorded inactive, the image detached,
53/10/25/8pins and11ROresources passed postcheck, and71459operational paths plus
1607tracked files/status stayed unchanged. Final actual episode/postrecords total
232918bytes:231959structured and959logs, including the retained producer warnings.
No warning is assigned as a cause of earlier failures;0269counts/cause stayUNKNOWN.

Keep five-minute automation active for bounded source/saved readiness/design work
on the next original owner/coupled-adapter prerequisite. Fix the next question,
inputs, measurable gates and finite budget before implementation or another
experiment. A new native episode needs its own recorded choice and fresh admission;
this once-only authority has been consumed. Pause when user participation is
actually required, without asking again for ordinary reversible preparation.

This result does not establish the full0267two-arc/carry/lifetime/concurrency/
full-coreABI-FP/arithmetic contract, physical F0 reachability, force fidelity,
derivatives/guards/independent trajectory bounds, an admissible command pair,
99-percent probability, strictM3 or mission safety. M4–M6/ML/UI remain gated.

## Evidence and verification

Exact source/saved independent reviews,8new artificial cases, fresh actual
independent admission, single native episode and separate canonical audit passed.
Protected files, local links, JSON/AST/archive pins, diff and strict OpenSpec are
verified before commit. Original package/scientific source/old tests/CI/dependencies
and moon_to_mars.py are unchanged;0282's8688required passes/42archival skips/Ruff
were not repeated. Recorded native warnings are retained, not silently discarded.
