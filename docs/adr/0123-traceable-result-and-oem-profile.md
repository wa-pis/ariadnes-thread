# 0123 — Design a traceable result and narrow OEM profile

Date: 2026-10-30
Decision status: superseded by [0124](0124-oem-reader-and-research-profile-ready.md); original draft and unresolved checks below preserved.
Implementation: specification draft only; no exporter, reader or fixtures implemented.
Scope / milestone: R1.3a; parent R1.3 remains open pending readiness checks.
Base revision: `0af58d0b33c89c35f4dcb9cfb4271dc43702b488`, clean before this stage.
Related OpenSpec: [result/profile requirements](../../openspec/changes/refine-physical-trajectory/specs/traceable-trajectory-result/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes: none. Superseded by [0124](0124-oem-reader-and-research-profile-ready.md); elaborates [0117](0117-mission-first-demonstration-priority.md) after [0122](0122-independent-elliptic-coast-passes.md).

## Context and constraints

R1.1 has a positive ideal M2 reference; R1.2 checks one synthetic coast component.
Neither establishes full-mission validity or export compatibility. Existing
`sample_transfer` already returns SI/SSB/J2000 states at numeric TDB epochs and
checks its arrival against M2. Reuse these states, without a new propagation
engine or resampling during export. Their UTC labels are not authoritative TDB
serialization inputs. The first/last states are outbound/inbound **coast** states,
not parking-orbit states before departure or after capture.

Bounded research in this stage: inspect existing boundaries and official OEM
syntax/time/frame rules; stop after selecting a draft and explicit readiness
gates. No native calculations, installations, external registration or new study.

## Options considered

- JSON only: easiest, but does not deliver the agreed trajectory-exchange path.
- Generic backend/export framework, multiple formats, or Java/Orekit runtime:
  defer; disproportionate to one sampled ideal coast.
- One normalized JSON result plus one narrow OEM file, with a separately written
  stdlib verification reader: proposed. Avoid new dependencies. This is local
  independent decoding evidence, **not** third-party interoperability certification.

## Decision and rationale

### Two linked artifacts, not a new orbit standard

Propose `ariadna-result-v1` JSON and `ariadna-oem-kvn-v1`. JSON retains normalized
actual inputs, selected candidate, model/omissions, canonical states, accounting,
separate statuses, source/resources and exchange provenance. OEM carries only the
same coast six-states and exchange metadata. Link them by a stable result ID in
`MESSAGE_ID` and the OEM SHA256 in JSON; do not embed a cyclic self-hash.

Use the existing model ID `sun-centered-zero-revolution-patched-conic-v1`.
Declare 121 samples for the positive reference. No interpolation, reoptimization,
new resource query or propagation during serialization. Do not put rocket-accounting
mass, covariance, safety flags, accelerations or maneuver commands into OEM.

Canonical input identity is SHA256 of UTF-8 JSON of the fully validated normalized
scenario, recursively string-key sorted, compact separators, `ensure_ascii=False`,
`allow_nan=False`, with explicit normalized UTC input strings and SI numeric
values from the scenario contract. Include ignored-but-supplied M2 fields; do not
hash raw TOML or depend on dictionary insertion order. Retain serialization/version
rules. Distinguish input ID from result ID: candidate full data, sample count,
model and actual resource/source identity also belong to the result identity.
Identical scientific payloads have identical IDs; elapsed time/export creation
timestamps belong to a separate execution/exchange envelope, not science identity.

### Exact draft wire profile

Pin the inspected **CCSDS 502.0-B-3, April 2023, Editorial Change 1, May 2023**,
official file `502x0b3e1.pdf`; OEM version **3.0**, KVN, ASCII, LF, final newline.
No XML, compression, accelerations, covariance, extra segments or user-defined
keywords. This pins a baseline, **not the latest corrected edition**. The catalogue
search surfaced a later Cor.1/e2 document, but its full text could not be fetched;
no claim that later corrections are incorporated or irrelevant is permitted.
R1.3b must inspect/reconcile it or explicitly review retention of the older
baseline before acceptance. Freeze document bytes/hash in that readiness record.

Header: version first, then research/profile/paired-result comments immediately
after it, explicit UTC `CREATION_DATE`, `ORIGINATOR`, `MESSAGE_ID`. Creation time
is a recorded export request value, never a launch default; repeated export of
the same request has identical bytes. It does not change result identity.
The originator must identify the actual responsible producer. B-3 table 5-2
requires a SANA organization value; **no registered Ariadna identity is verified**.
Readiness must resolve that identity or explicitly propose a labelled experimental
deviation for user review. Never substitute JPL/ESA/another agency or assert full
CCSDS conformity from parser acceptance. No registration request is authorized.

One metadata block: `OBJECT_NAME=UNKNOWN`, `OBJECT_ID=UNKNOWN` for the hypothetical
unregistered spacecraft; retain its descriptive scenario ID in JSON/comments.
`CENTER_NAME=SOLAR SYSTEM BARYCENTER`, `REF_FRAME=ICRF`, `TIME_SYSTEM=TDB`,
`START_TIME`/`STOP_TIME` equal the first/last encoded epochs. Omit
`REF_FRAME_EPOCH`, usable-time overrides and interpolation recommendations.
Promise accuracy only at the supplied nodes; do not imply continuous/interpolated
accuracy or safety over the 121-point coast.

Our SPICE J2000-to-ICRF identity mapping is conditional on the known DE4xx-compatible
kernel provenance documented by NAIF; it is not a universal EME2000-to-ICRF identity.
Freeze the admitted resource hashes and label that basis. Unknown provenance,
heliocentric input, EME2000/ITRF axes or another time scale must fail, not be renamed.
No coordinate rotation or SSB-to-Sun shift occurs at this export boundary.

Each data line has a TDB Gregorian calendar tag without `Z` and six values in
km/km/s. Convert SI by dividing each component by 1000; output normalized uppercase
scientific notation with **16 significant decimal digits** (`.15E`), not arbitrary
17-digit float representations. No units suffixes. TDB calendar labels are a
representation of seconds from `2000-01-01T12:00:00` **TDB**, not UTC conversion:
use integer days/seconds and decimal fractional seconds, six fractional digits,
round-half-even with carry. Admit calendar years 1900–2100 inclusive; reject
overflow, invalid dates, second=60, and duplicate epochs after formatting.
Never use `epoch_utc`, Unix timestamps or a `Z` suffix to serialize these epochs.

### Separate scientific and exchange statuses

Keep calculation (`passed`, `failed`, `unavailable`), reserve accounting
(`passed`, `failed`, `not-evaluated`), qualification (`ideal-model-feasible` or
`unqualified`), and exchange (`not-checked`, `passed`, `failed`, `unavailable`)
distinct. An OEM parsing pass cannot promote any scientific status. On failure,
retain error stage/message and provenance; no download of stale/partial states.
Only completed finite, ordered, admitted-frame states from the current result
can be exported; an unqualified but numerically completed research coast must
remain explicitly unqualified in both the paired result and mandatory comments.
The positive reference must pass its unchanged 50kg reserve and ideal accounting
gates. Absent covariance/tracking/safety values are null with not-modelled status.

UI must invalidate result, selected/sample caches, pending export bytes and
download controls immediately on any actual-input change, failed calculation,
new calculation start, resource/model change, or candidate change affecting the
selected result. Candidate changes may preserve the search but not the old coast
or export. Late results are published only if their captured input/result key
still matches current controls. Reuse the existing invalidation path, not a new
background job system. Sort/filter-only changes preserve a still-selected result.

### Verification without a second producer sharing the same bug

Select separately implemented reader `r1-oem-audit-v1` in a private verification
script, stdlib `Decimal` and calendar arithmetic only, no imports from writer,
its formatting/conversion helpers or Tudat. Its implementation/hash is frozen
before exporter work. It parses **file bytes**, validates this strict subset and
reconstructs SI/TDB values, not values passed around in writer memory.
It is not an operational importer/general CCSDS validator. Shared requirements
and constants are necessary; shared serialization algorithms are forbidden.

At every node require Euclidean differences <=0.001m and <=1e-9m/s, reconstructed
epoch error <=1e-6s, exact count/order/frame/centre/time tokens and matching
metadata bounds. These are wire-conversion tolerances, not propagation accuracy.
Use hand-authored asymmetric/mixed-sign Cartesian fixtures with a separately
declared expected SI table and TDB anchors at zero/negative/day/leap-year/carry
boundaries, plus offline reconstruction of the retained 121-state R1.1 payload.
Reject duplicate/missing metadata, malformed/extra fields, unsupported versions/
sections/units/frames/time, nonfinite values, unordered/duplicate times, partial
files, metadata-bound mismatch and header/comment injection. Include deliberately
1000x, swapped-axis and UTC-labelled-as-TDB corruptions checked against expected
physical data: syntax alone cannot discover false metadata or wrong-unit numbers.

## Consequences and revisit conditions

One inspectable result and one conservative wire subset keep the existing stack.
No claim of all-OEM support, a new adopted standard, flight readiness, continuous
accuracy, full-transfer independent validation or M3/M6 closure. A real external
consumer, new frame/time/model or originator/corrigendum resolution requires a
reviewed profile version, not silent extension. R1.3 remains open until its
metadata/corrections and independent-reader/fixture checks are verified. R1.4
still needs a separate implementation instruction and full regression checks.

## Evidence and verification

Inspected existing sampler, UI invalidation/provenance boundaries and previous R1
requirements without executing native code. Official sources inspected 2026-10-30:

- [CCSDS B-3 EC1](https://ccsds.org/Pubs/502x0b3e1.pdf), document-control page v,
  tables 5-2/5-3, sections 5.2.4, 7.5, 7.7.2, 7.8: edition, field structure and units.
- [NAIF frames](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/frames.html#ICRF%20vs%20J2000): conditional J2000/ICRF mapping for compatible kernels.
- [SANA organizations](https://sanaregistry.org/r/organizations/): organization
  registry inspected, not proof of an Ariadna assignment or authority to use one.
- [CCSDS catalogue](https://ccsds.org/publications/newbooks/): later-correction
  search result; full corrected text unavailable in this bounded check.

Strict OpenSpec, local links, scope/diff and immutable-history checks apply to
this documentation stage. No runtime tests, reader/writer acceptance, source-PDF
hash, third-party parser, new trajectory or scientific result is claimed here.
