# 0259 — Inspect the pinned split-Time caster source

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (one bounded source continuation only)
Implementation: no production code or native adapter change
Verification: one source capture completed; independent source review corroborates the limited route; documentary/strict checks below
Scope / milestone: F13 / M3 preparation in the sole active change
Base revision: `ebf24bd86acf9dffef31a7d2d7950a3535839f1d`
Related OpenSpec: [source contract](../../openspec/changes/refine-physical-trajectory/design.md#f13-bounded-pinned-source-continuation-2026-11-25), [conditional readback requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves ADR0258's partial result and all physical gates

## Context and constraints

[ADR0258](0258-lookup-exact-split-time-build-source.md) recovered exactpy312
recipe/Git declarations but its interactive controller failed on EOF. Repeating
the package acquisition is unnecessary. The saved records identify one TudatPy
checkout and pybind11 version; inspecting their primary sources is the smallest
remaining step toward understanding F11's conditional readback premise.

## Options considered

- Refetch/replay the old controller or substitute current sources: rejected;
  identity is already known and the historical failure must remain unchanged.
- Rebuild/install or start another native fixture: deferred; neither is needed
  to establish what the pinned source declares.
- One fixed noninteractive source continuation with finite limits: selected.

## Decision and rationale

Follow the canonical source contract before any request: root TudatPy CMake,
one exact tag resolution (optionally one annotated-tag dereference), then two
immutable pybind11 headers. Use at most6responses/600s with60s-per-response,
256KiB-per-body and separate2MiB raw/decoded/retained ledgers. Reject redirects,
compression and unsupported tag chains; retain partials without hidden retry.
No archive members, package refetch, downloaded execution or scientific work.

The official tag's resolved commit identifies inspected upstream bytes only.
A recipe or CMake selection path cannot attest the include files/macros actually
compiled into the installed extension. Keep those facts separate from lawful
native-domain/readback and physical qualification. The original target, hardware,
commands, tolerances and resource gates remain unchanged and unevaluated.

## Consequences and revisit conditions

A successful lookup may close a source-level fact; it cannot close actual event
carry, effective FP behaviour, finite-domain proof or mass/force/endpoint gates.
Keep actual readback unavailable when any premise is missing. A missing source
is a precise gap, not a scientific failure or permission to replace its version.
Continue ordinary reversible preparation only; pause for a concrete needed user
choice/access/authorization or scientific-contract change. No generic checker or
native/mission experiment follows automatically.

## Evidence and verification

The fixed contract preceded one noninteractive session. FiveHTTP200 responses
include exactly one annotated-tag dereference; raw and decoded bodies total
215077bytes. Original durable session records total230134bytes. The separate
parent return observes2.620360417s after their finalization, exit0. Earlier child
and outer-record timestamps remain explicitly pre-fsync. No retry, package
refetch, redirect, compression or downloaded execution occurred.

The official `v3.0.1` tag resolves through annotated object
`e86205cb2ba070755d582856430c0f83c0af6694` to inspected commit
`f5fbe867d2d26e4a0a9177a51f6e568868ad3dc8`. Its saved API record says unsigned;
this is observed source resolution, not signature or historical-build attestation.
The pinned [TudatPy root CMake](https://github.com/tudat-team/tudatpy/blob/2300d7fe3d7db4db9a78dd4a9a4a713f614da22d/CMakeLists.txt#L520)
selects config-mode pybind11 and include variables at lines520–522, without
retaining their actual effective values. The pinned generic
[caster source](https://github.com/pybind/pybind11/blob/f5fbe867d2d26e4a0a9177a51f6e568868ad3dc8/include/pybind11/cast.h#L229)
uses a double intermediary for floating types, reads Python doubles and assigns
them to T (235/253–255/306); its export narrows directly to double before the
CPython float constructor (310–314). Tuple creation dispatches the selected
argument casters before inserting Python objects (1892–1910). The pinned
[float wrapper](https://github.com/pybind/pybind11/blob/f5fbe867d2d26e4a0a9177a51f6e568868ad3dc8/include/pybind11/pytypes.h#L1906)
also uses double-valued CPython APIs (1906–1925).

Independent saved-byte/source review corroborates that conditional route. These
sources close what the inspected generic version implements; they do not prove
that this exact template/configuration generated the installed binary, its
complete FP behaviour or a lawful finite native input domain. F11's mathematical
enclosure therefore remains conditional and actual readback unavailable. No
mantissa, half-ULP, singleton, exact carry or physical certificate follows.

The immutable [source ZIP](experiments/0259-pinned-source-lookup.zip) contains all
five bodies, request/response records, bounded anchor summaries and distinct
parent evidence. [Lookup verification](experiments/0259-lookup-verification.json)
pins every retained member and source SHA. [Documentary verification](experiments/0259-doc-verification.json)
checks links/protected history/CURRENT/diff/strict. Historical0258 records and
its unchecked incomplete task remain unchanged. Runtime tests were not rerun;
no production code, native import, SPICE or scientific evaluation changed.

Next preparation should bound the pre-export finite/range invariant for a narrow
Time construction/copy/export route using retained sources only, identifying any
missing primitive before implementation or experiments. This is a concrete
remaining premise, not another broad API review. Do not repeat this lookup or
create another generic checker or native/mission campaign by default.
