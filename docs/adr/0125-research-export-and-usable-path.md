# 0125 — Deliver one traceable research display and export path

Date: 2026-10-31
Decision status: accepted (user explicitly instructed R1.4 implementation).
Implementation: complete at research-demonstrator scope; focused/full verification passes.
Scope / milestone: R1.4 research demonstrator, not M3 closure or flight navigation.
Base revision: `bd9f3f28636c350b0f67bfdb93f25e077a675b3c`; source/UI/tests uncommitted during verification.
Related OpenSpec: [exchange contract](../../openspec/changes/refine-physical-trajectory/specs/traceable-trajectory-result/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements accepted [0124](0124-oem-reader-and-research-profile-ready.md), retaining historical evidence unchanged.

## Context and constraints

R1.1 supplies a positive ideal M2 coast, R1.2 a synthetic independent physical
benchmark, and R1.3 an accepted, limited research profile and a frozen decoder.
The user now requests the existing input → calculation → display → paired export
path. Use the existing M2 search and sampler, without new physics, tuning,
trajectory studies, dependencies, or automation. Original M3/task3.9 and M6 gates
remain open. File-conversion success cannot establish physical mission feasibility.

## Options considered

- Load the private decoder from repository documentation at runtime: rejected;
  package installation would not carry that path, and mutable dynamic imports
  would obscure the frozen verification identity.
- Add a generic OEM library/backend or rewrite the independent verifier: rejected;
  unnecessary for this exact profile and risks sharing writer conversion code.
- Package an exact byte-identical copy of the frozen independent decoder, and
  verify its hash before publication: selected. Keep the original artifact frozen.

## Decision and rationale

[research_export.py](../../src/space_nav/research_export.py) consumes completed,
ordered SI/SSB/J2000 states, selected candidate/search, actual normalized scenario,
endpoint body states, measured search time, selection policy and provenance.
It never propagates, loads resources or queries SPICE. It validates source/runtime
availability, the complete ordered ADR0119 kernel hash allowlist, frame/time/model,
search completion, sample epochs, endpoint agreement and independent Decimal
rocket accounting within 1e-9 kg. A fixed 50 kg reserve is explicit research
qualification, separate from M2's existing dry-mass feasibility flag.

Canonical sorted compact finite UTF-8 JSON binds the scientific payload, including
actual states and statuses, into a SHA256 result ID. The OEM MESSAGE_ID/comments
bind that ID; JSON retains the OEM digest, decoder identity and maximum residuals.
Creation UTC and measured search elapsed time belong only to the execution/exchange
envelopes. The exporter source hash is retained separately; the scientific source
identity describes the actual calculation, including when retained historical
states are decoded offline. Repeated export of the same request has identical bytes.

Epochs use integer microseconds from the TDB J2000 noon anchor, half-even rounding
and calendar carry. Components divide exact binary64 values by1000 using Decimal
and emit normalized16-digit scientific notation. Reject out-of-range calendars,
nonfinite values, formatted duplicate epochs and unsupported semantics. No UTC
conversion, coordinate rotation, resampling, interpolation or maneuver commands.

[_oem_audit.py](../../src/space_nav/_oem_audit.py) is a byte-identical packaged copy
of ADR0124's private verifier, SHA256
`a531dec0b774f29a78b02a2b65c7418bd27919bacbcf8f2893372c9b80541247`.
The writer uses none of its conversion/formatting helpers. The decoder reconstructs
file bytes independently, binds external result ID/qualification and checks **all**
nodes at <=1microsecond, <=1mm Euclidean position and <=1e-9m/s Euclidean velocity.
Reader/source/hash or decode failure returns no bundle; no partial downloads.
This local independent implementation is not third-party interoperability approval.

[explorer_ui.py](../../src/space_nav/explorer_ui.py) offers an explicit positive
**С резервом 50 кг** example alongside the unchanged original shortfall example.
It retains the same search, Pareto selection, plot and121-node sampler. Only after
verification does it publish paired immutable JSON/OEM bytes. It preserves
`unqualified` coast status even when exchange passes and shows the approved
unregistered-originator/no-full-CCSDS-conformance notice.

Input/recalculation/error changes clear search/sample/export state; candidate
changes clear selected sample/export state, and empty filters clear downloads.
Generation guards reject late search/sample/export results. Sort/slider changes
preserve a matching selected result. Source and complete actual kernel hashes are
rechecked before display/publication; changes require recalculation. This costs
resource I/O even on view reruns, but does not rerun search or resample. Calculation
and exchange failures retain their stage/message and available provenance. Search
provenance requires a readable checkout; missing identity fails without fabrication.

## Consequences and revisit conditions

One usable repository-based research path with existing dependencies and CLI/API
behavior preserved. The explicit narrow kernel admission can reject changed
installations; review provenance before widening it. Source/kernel hash checks
can add UI latency. Broader installed-wheel provenance, external consumers,
additional frames/profiles, SANA registration or performance-driven inventory
caching require review; never silently change the frozen verifier or reuse its
identity after editing it. Legacy model, environment, existing evidence and all
strict scientific tolerances remain unchanged. Automation stays paused.

## Evidence and verification

- [39 new tests](../../tests/test_research_export.py) plus existing explorer,
  sampler and frozen-reader coverage: **151 focused tests passed in67.28s**.
  Tests exercise offline retained121-node serialization, canonical identity,
  creation-time independence, frame/resource/source rejection, epoch rounding,
  mass/endpoint checks, decoder failure, real Streamlit positive/unqualified paths,
  changing inputs/candidate/resources/model, sort/slider retention, empty filters,
  late results and persistent error diagnostics.
- Offline ADR0119 reference: result ID
  `916903bbf703a10968358ed14c33a8f9bf98f39215d93564c0d4ed991d0f50c5`;
  JSON59008bytes / OEM20355bytes for the fixed test request. All121 nodes pass:
  max epoch4.90570068359375e-7s, position6.506174973706631e-5m,
  velocity6.690771978291971e-12m/s. Independent final mass
  887.96646404096114166633065999155148821690285642750446kg;
  mass error2.78425e-14kg, propellant error1.41530e-13kg, reserve margin337.966464kg.
  These are serialization/accounting observations, not new propagation accuracy.
- UI tests execute the existing native M2 calculation and sampler, not a new
  scientific study or D17 retry. Historical0119 JSON and original reader are unchanged.
- Full pinned regression suite: **4766 passed in630.19s (10min30s)** after
  the test-isolation correction below. Full `src/tests` Ruff and strict OpenSpec
  pass; local links, source hashes, scope/diff and220 immutable tracked scientific,
  environment, legacy and evidence files pass. The original verifier is byte-identical
  to its packaged copy. No runtime code changed after this final regression run.
- Local Streamlit server started on127.0.0.1:8501; its health endpoint returns
  HTTP200/ok. AppTest verifies actual UI behavior; no external browser/consumer
  compatibility or visual screenshot audit is claimed.
- No external OEM consumer, general CCSDS conformity, continuous/coast safety,
  finite-burn escape/capture or full-mission independent verification is claimed.

### Regression-order diagnosis

The initial full run was interrupted after5 failures/3059 passes in199.19s to
inspect its already-failed UI acceptance. A separate reproducer (CLI → real
SPICE parity → positive UI) failed1 test/17 passed in5.60s. The strict reference
inventory correctly refused the changed pool: the old real-parity test forcibly
reset Python initialization flags after earlier tests had already loaded native
kernels, then loaded them again. Remove that forced reset from the real test and
assert an already-loaded pool keeps its count; retain its original state/time
parity tolerances. This is test isolation, not a relaxed production allowlist,
changed SPICE initialization policy or accepted resource-baseline drift.
After this correction the reproducing CLI/ephemeris/new-export sequence passes
**56 tests in22.66s**; the complete fresh4766-test run above also passes.

### Measured source identities

- `src/space_nav/research_export.py` SHA256 `4c4001539f4169de7e32c833ded8eb5fc9a9e22e007e86391b6a73d117470eb2`.
- `src/space_nav/explorer_ui.py` SHA256 `14da24cdb5802ebcb3cc775a31ef0b6da1af229a6aa887e7946258095906eb0b`.
- `tests/test_research_export.py` SHA256 `b2c137ac4d5c73f8d1cf027e0f3e87ceb75c1327c220097fb898748dd35b2423`.
- `tests/test_ephemeris.py` SHA256 `9a4f5a6d87f7429323287187e5257702c85bbfe79da07bf562ea0925e76a0f6f`.
