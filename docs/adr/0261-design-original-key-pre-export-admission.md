# 0261 — Design original-key pre-export admission

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (bounded source/design review only)
Implementation: no code, native build or dependency change
Verification:298s source/design review and two independent reviews; documentary/strict checks below; native implementation awaits user choice
Scope / milestone: F15 / M3 preparation in the sole active change
Base revision: `df44803a4e658d398077266a281c74b1d5a99708`
Related OpenSpec: [admission design](../../openspec/changes/refine-physical-trajectory/design.md#f15-original-key-pre-export-admission-design-2026-11-25), [readback requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves F14's conditional domain and physical gates

## Context and constraints

[ADR0260](0260-bound-time-construction-export-domain.md) isolates the missing
basis: original native-key domain/provenance before copying and narrowing. Its
conditional no-op construction/copy invariant does not validate arbitrary keys.
The next useful step is one concrete admission path, not another generic checker.

## Options considered

- Reconstruct after Python export or trust a bool/JSON declaration: rejected;
  this cannot establish the required pre-copy/pre-narrowing provenance.
- Reuse an existing original-key native reference/guard if the named source path
  supplies it: preferred, subject to pinned route/lifecycle/qualification evidence.
- Specify a minimal new native primitive if that point is absent: design only;
  no new build/dependency or scientific-contract change is adopted automatically.

## Decision and rationale

Review the F7 call path and its direct installed history bindings within600s,
without HTTP, code/native execution, scientific evaluations or integration.
Record current availability and one precise proposed interface with independent
future verification obligations. A source gap must stay a gap. Pause only for a
concrete needed user decision rather than issuing another diagnostic successor.

## Consequences and revisit conditions

Original key/state/mass association, lifetime and lawful prior arithmetic remain
separate from finite current fields. A successful design is not an implemented
native exporter, exact carry, physical clock bound or command-pair witness.
F0 inputs/model/tolerances and all production budgets remain unchanged. Any
necessary new native build/dependency or scientific-contract choice is presented
to the user before implementation; ordinary reversible preparation is authorized.

## Evidence and verification

The review03:47:06Z–03:52:04Z took298s<=600s, including independent source/
scope reviews. Seven source records retain full hashes/selected line bytes in
[the source/design evidence](experiments/0261-source-design.json). Six installed
records match the exact package paths inventory; the project reader matches the
base revision. No binary or active STL-converter attestation follows.

| Named route | Source observation / availability |
| --- | --- |
| F7 Python reader | `_native_arc_conformance.py`200 obtains Python history,203 sorts it,205 narrows labels;179–188 performs post-export equality/subtraction. No original-field native admission precedes history export. |
| Direct simulator property | expose_simulator140–149 binds the const-map-reference accessor in dynamicsSimulator1143–1146. It returns the native map without an original-row finite/range guard: a concrete C++ interception point, not a proven Python key-reference route. |
| Similarly named results property | expose_propagation535–539 calls propagationResults222–227's templated conversion. utilities915–923 iterates pairs by value and casts/inserts Time keys into a new map; Time copying can normalize before any Python check. |
| Conversion/hash boundary | The binding includes pybind11/stl.h; its exact active converter/ownership policy is not established by retained sources. Time117–125 hashes through remainder arithmetic/integer conversion, so the new guard must precede Python mapping/hash export too. No exact uninspected STL order is claimed. |

The named existing path does not supply the needed admission guarantee. This is
not a claim that every library API is impossible or that F7's retained synthetic
integer-event evidence failed. Source/lawful-object/prior-arithmetic premises and
actual compiled FP remain separate unresolved obligations.

### Minimal proposed native seam

Conceptual interface only: `visit_original_endpoint(owner, selector)` returns an
admitted native event and its readback evidence. It is not an existing Python API.

1. Keep the completed native owner alive and prevent mutation during the call.
   Select the chronological endpoint by const iteration of the ORIGINAL native
   map; bind its `const Time&` and associated seven-state row together. Do not
   copy keys/maps, reconstruct, hash, normalize, narrow or export a Python map.
2. Read r in its native type and require qualified native finiteness and0<=r<T,
   with valid h and selected T/FP semantics. Reject before any unsafe operation;
   do not repair/normalize an inadmissible key. A current-field check cannot
   retroactively certify earlier propagation/normalization arithmetic.
3. Only after admission export exact h, the original narrowed y word and the
   associated state/mass words. Preserve signed zero/rounded3600 and F11's
   conditional neighbour enclosure; do not reconstruct a native event from y.
   Actual later carry needs its own lifetime-safe native event carrier and
   cross-context qualification; no dangling borrowed reference may escape.
4. Bind source/build, owner/arc/row/command/model identities and guard ordering
   to independently checked evidence. A bool/JSON declaration cannot certify
   its own original-key provenance, prior arithmetic or physical admission.

Future verification is finite: guard-before-copy/hash/narrow instrumentation;
scalar native-domain boundaries/nonfinites without unsafe Time construction;
original row/state/mass and direction binding; owner expiry/mutation/context
rejection; signed words/rounded3600/finite-neighbour semantics; and unavailable
prior-arithmetic/compiled-FP/carry/error-bound cases. A chosen build/profile must
fix its compile/runtime/native/byte/watchdog limits before execution. No limits
or native attempts are expanded by this design and no experiment is scheduled.

### Required user choice and scheduler

Implementing that seam introduces a native build/interface choice: a small
visitor within a rebuilt TudatPy binding, or a separately compatible native
extension. Neither build route, ABI/dependency profile nor modified pinned
package is adopted here. Moving checks in the existing Python reader cannot
supply the missing pre-export guard. Scope this as one native adapter, preserving
Python/Conda, the physical model, F0 inputs and every scientific tolerance.

Per the linked F15 contract, `ariadna-m3` is PAUSED pending the user's decision
whether to authorize this native-adapter preparation/qualification. That is the
concrete needed choice, not another request for already authorized source work.
No native build, dependency install, mission search or contract relaxation occurs
while waiting. After approval, select and bound one build approach before code.

[Documentary verification](experiments/0261-doc-verification.json) checks links,
source selections/hashes, protected history/CURRENT/diff/strict. No code, HTTP,
runtime tests, native import, SPICE, scientific evaluation or integration ran.
The [final documentary receipt](experiments/0261-final-doc-verification.json)
clarifies one summary label: its “int64 conversion” means the source's
`long long` conversion, with no exact-width assumption. Selected source bytes and
both earlier receipts remain unchanged. All prior evidence remains intact; the
original command-pair goal is still open.
