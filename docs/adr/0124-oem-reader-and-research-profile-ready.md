# 0124 — Verify the independent reader and research exchange profile

Date: 2026-10-31
Decision status: accepted (user requested preparation and explicitly approved the unregistered research-originator exception).
Implementation: private reader/fixtures verified; R1.3 readiness complete at research scope. Production writer/UI not implemented.
Scope / milestone: R1.3b; not R1.4 delivery or formal CCSDS conformity.
Base revision: `c09742ccbb2d293d9e70d530bb46a9dc6473be05`, clean before preparation.
Related OpenSpec: [profile requirements](../../openspec/changes/refine-physical-trajectory/specs/traceable-trajectory-result/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes: [0123 draft profile](0123-traceable-result-and-oem-profile.md); preserve its original research/limitations, inputs and prior evidence.

## Context and constraints

The draft left source corrections, originator identity and reader acceptance open.
This preparation resolves them without building the exporter, loading scientific
libraries, querying SPICE or propagating another trajectory. The user explicitly
approved `ORIGINATOR=ARIADNA` with an unregistered-originator/no-full-conformance
notice. That permission does not register the project or authorize another
agency's identity. Full M3/M6 qualification remains outside R1.

## Options considered

- Wait for SANA registration or impersonate a registered originator: no;
  registration is not authorized, and another agency is not our producer.
- Continue with the unavailable corrected source or silently retain the old one:
  reject; follow the official catalogue link to inspect the corrected document.
- Adopt a hash-pinned corrected baseline with one explicit research exception,
  then verify a private independent reader before writer code: selected.

## Decision and rationale

### Sources and frame admission

Use **CCSDS 502.0-B-3, April 2023, corrected file `502x0b3e2tc11.pdf`**,
3,776,940 bytes, SHA256
`9165f11d6111c05f9428a2870c9e218ac659af9951324ebe1c6105223efbcd7b`.
[Official catalogue](https://ccsds.org/publications/allpubs/entry/3073/) links the
[inspected PDF](https://ccsds.org/wp-content/uploads/gravity_forms/5-448e85c647331d9cbaf66c096458bdd5/2026/10/502x0b3e2tc11.pdf?gv-iframe=true).
Inspect OEM section5 and syntax/time/units sections7.4–7.8; retain version3.0,
the six-component node representation and the declared numeric gates. The
document-control page identifies EC2 November2025/Cor.1 September2026, while
catalogue prose says June2026. Pin **content hash**, not an invented reconciliation
of inconsistent publication dates. This is not a review of all 224 pages/all ODM.

The earlier inspected EC1 file is 2,346,017 bytes, SHA256
`97d1687b4a461ffdf965b9b65923820cc6aa9d1d1c4d4df77a598a53d4a49d81`.
Both PDFs were fetched from official URLs and hashed in memory. No PDF is vendored;
future verification must match the recorded bytes/hash, not trust an unchanged URL.

Correct a draft mistake: the actual R1.1 kernel manifest contains **INPOP19a**, not
a DE4xx planetary kernel. The [IMCCE INPOP19a release description](https://ftp.imcce.fr/pub/ephem/planets/inpop19a/)
documents ICRF axes and the TDB SPICE product. The local planetary SPK hash
`01f095b148ef1e5aad6f95213c188ca5b0d8a58901d19a95b0c11082b1d3a0c6`
matches the immutable ADR0119 manifest; no new native query was made.
Admit that **complete, ordered hash-bound R1.1 kernel manifest** and its INPOP19a
frame convention for the reference, not an unverified DE-only allowlist or
arbitrary kernel labelled J2000. Preserve SSB coordinates and numeric values.
Unknown/changed provenance and actual EME2000/rotating/heliocentric states still
fail; this is a documented frame-identity decision, not a fitted rotation or
new absolute orientation-accuracy claim. No historical source/result is changed.

### One explicit experimental deviation and an exact subset

The responsible producer is ARIADNA. The user-approved deviation is **unregistered
ORIGINATOR**: this is a research OEM-shaped exchange profile, not full CCSDS
conformity or a certification. All other selected unit/time/state rules remain.
The private reader validates that notice, not SANA membership. Mandatory lines
are version first, followed in order by these comments:

```
COMMENT PROFILE ariadna-oem-kvn-v1
COMMENT RESEARCH_ONLY NOT_FOR_OPERATIONAL_NAVIGATION
COMMENT ORIGINATOR_UNREGISTERED NO_FULL_CCSDS_CONFORMANCE
COMMENT QUALIFICATION <ideal-model-feasible|unqualified>
COMMENT RESULT_ID <64 lowercase hexadecimal digits>
```

Then ordered header fields CREATION_DATE (Gregorian UTC, six fractional digits,
Z), ORIGINATOR=ARIADNA and MESSAGE_ID equal to the result ID. Metadata order is
OBJECT_NAME/OBJECT_ID=UNKNOWN, CENTER_NAME=SOLAR SYSTEM BARYCENTER, REF_FRAME=ICRF,
TIME_SYSTEM=TDB, START_TIME, STOP_TIME, within META_START/META_STOP.
Keep the other ADR0123 rules: one segment, six values/node in km/km/s, TDB tags
without Z, no extra sections/units/interpolation recommendations. Each line uses
single spaces, no blanks/tabs/CR/non-ASCII, maximum1024 bytes, file<=2,000,000 bytes;
2–1001 strictly ordered nodes (121 for the reference), exact encoded bounds.
These limits are the local strict subset, not general CCSDS limits.

Clarify identity binding before production code: `result_id` is SHA256 of the
canonical finite scientific payload, including actual states, candidate, model,
normalized-input identity, resource/source identity, reserve and scientific status.
Exclude result_id itself and execution/exchange envelopes; no self/cyclic hash.
Thus different retained scientific states cannot silently share a result ID.
The decoder verifies both comment/header binding **and** externally supplied
expected ID/qualification; parsing must not promote unqualified physics.

### Verified independent decoder and acceptance procedure

Freeze [reader](experiments/0124-oem-reader.py) ID `r1-oem-audit-v1`, SHA256
`a531dec0b774f29a78b02a2b65c7418bd27919bacbcf8f2893372c9b80541247`.
It uses only stdlib Decimal/calendar arithmetic and reads file **bytes**. No
production/writer helpers, Tudat, NumPy or resource loading. It is a private audit,
not a runtime dependency, operational importer or third-party interoperability test.

[Asymmetric fixture](../../tests/fixtures/r1_oem/asymmetric.oem) and
[expected SI table](../../tests/fixtures/r1_oem/expected-si.json) are hand authored,
not propagated trajectories or writer output. The separate
[leap-day fixture](../../tests/fixtures/r1_oem/leap-day.oem) covers the calendar
boundary. Tests include negative/zero/day/leap-year anchors, lower-side rounding
ties/carry acceptance, inclusive time/position/velocity thresholds, Euclidean
norms, count/shape/finite/binding errors and malformed/unsupported/injected files.
The reader does not round epochs itself: correctness of the future writer's
half-even rounding, resource admission and JSON identities remains R1.4 work.

Future acceptance: take the independently retained expected SI/TDB table and
result ID/status; pass emitted bytes to `verify`, then retain reader/hash/file
identity and maxima. Require <=1microsecond, <=1mm Euclidean position and
<=1e-9m/s Euclidean velocity at **every** node. Wrong1000x units and swapped axes
may parse but fail comparison; false UTC labels require comparison to expected
TDB values. A parser cannot detect arbitrary truthful-looking false metadata.
The retained ADR0119 121-state table is readable offline and remains immutable;
no OEM is generated from it until separately instructed R1.4 implementation.

## Consequences and revisit conditions

R1.3 is ready for this expressly limited research path. Next is a separately
instructed R1.4 implementation, with focused/full regressions and actual
input/display/export/independent decoding acceptance. No writer/UI/source physics,
API, environment or old artifact changed here. Registration, external consumer
requirements, changed resources/frames or broader OEM support require review;
never quietly remove the experimental notice. All earlier ideal-model and
finite-burn/M3/M6/safety limitations stay in force; automation remains paused.

## Evidence and verification

- [88 focused native-free tests](../../tests/test_r1_oem_reader.py) pass; hand
  fixture/expected vectors and leap-day decode exactly, and injected corruptions
  fail the declared checks. Test module SHA256
  `1e6df59fe6f72a8ee101a30a69b3563828e2d0ce376b9aaef6f173b495e2c836`.
- Import guards and an AST allowlist enforce reader independence. The prepared
  R1.2 native-free tests are also rerun; these mocks are not new physical evidence.
- Ruff, strict OpenSpec, local links, artifact syntax, scope/diff and immutable
  source/environment/history/legacy checks pass. Source PDFs are version-bound
  above; the installed INPOP SPK was read/hashed, not loaded as a native kernel.
- Full native regression suite **not rerun** for this scoped private evidence
  preparation; no production implementation completion is claimed. The full suite
  remains mandatory before R1.4 production completion. No generated real-trajectory
  OEM round-trip, third-party parser, new propagation or general certification
  is claimed by these synthetic wire fixtures or the 88 test count.
