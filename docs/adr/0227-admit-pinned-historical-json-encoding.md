# 0227 — Admit the pinned historical audit JSON encoding

- Date: 2026-11-20 (Europe/Samara).
- Decision status: accepted compatibility repair explicitly requested by the user after ADR0226; retained numerical execution remains deferred.
- Implementation: complete for R5.59o. Artificial qualification and read-only real metadata preflight pass; no new retained numerical run.
- Scope / milestone: R5.59o, M3 archive-adapter repair only.
- Base revision: `b613ee4c17203ae3b0029fc877895c266bdb7353`, clean synchronized `dev` before repair.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-admit-hash-pinned-historical-json-encodings-without-rewriting-evidence), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559o-historical-json-compatibility-repair-2026-11-20), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. ADR0224's mathematical/resource contract, ADR0225's qualified historical adapter and [ADR0226](0226-record-retained-trace-input-rejection.md)'s consumed first dispatch remain immutable.

## Context and constraints

The ninth pinned archive uses valid sorted JSON with default spaces after separators. The qualified ADR0225 adapter admitted compact or indented serialization only, so its first retained dispatch stopped before scientific work. The raw hash was correct. The user requested fixing this compatibility defect and artificial qualification, without repeating the retained numerical diagnostic.

## Options considered

- Rewrite the saved audit or edit the historical adapter: rejected; immutable evidence and recorded source identities must remain usable.
- Accept arbitrary parseable JSON in every role: rejected; it would broaden the encoding boundary beyond the observed compatibility need.
- Preserve a versioned adapter with a small input-decoding change: selected. The orchestration is retained verbatim outside that change, making its scientific and resource behavior reviewable against the original.

## Decision and rationale

Create [the versioned adapter](experiments/0227-retained-trace.py) from the unchanged historical adapter. Authenticate raw bytes against the existing role pin before decoding. Keep the two established exact serializations and additionally admit sorted default-spaced JSON followed by one newline for `study_audit` only. Reject duplicate keys at any nesting depth, non-object roots, nonfinite constants/overflow, malformed JSON and unapproved whitespace. Keep new output evidence compact; never rewrite or normalize old files on disk.

All mathematical modules, contract pins, selected cells/points, mass/parity rules, output scope and inherited clocks/work/byte limits stay unchanged. Preserve the prior adapter and first failed dispatch byte-for-byte. Qualify fabricated archives with the nine observed encoding profiles and rechained raw identities; show the original adapter still rejects the previously failing shape. Verify the complete artificial matrix and separate audit plus failure boundaries. A read-only preflight may inspect the original nine hashes, encodings and downstream metadata/selected-row identities without calling scientific functions. It is not a retained observation run.

## Consequences and revisit conditions

This repair addresses archive admission only. Successful metadata preflight or artificial matrix tests do not establish real internal widths, an eligible command pair or physical continuity. Automation stays PAUSED. A new retained numerical invocation requires a separate explicit instruction and a first-attempt record under the qualified version; the consumed ADR0226 dispatch is not erased or reset.

## Evidence and verification

[The 18 focused tests](../../tests/test_retained_json_compat.py) pass in 3.59 s. Both full-volume artificial witness/refusal profiles reproduce all nine historical encoding roles: seven compact, the indented grid audit and the default-spaced study audit. Raw receipt/source pins are rechained for those fabricated archives; historical files are not repinned. Each artificial profile verifies the old adapter's exact rejection and the new 24-trace/24-control matrix, 48 bounds, zero new points, 12 producer mass calls and a separate saved-only audit with zero bounds/six mass calls. All 16 applicable quantities per trace are checked and new output remains compact. Fabricated unselected rows and old audit rows are format fixtures rather than historical scientific replays.

Regression cases reject a semantically equal reencoding at the raw SHA gate before parsing; default spacing in other roles; nested and top-level duplicate keys; NaN/Infinity/overflow; malformed/invalid UTF-8; scalar/array roots; unsorted keys and missing/extra whitespace. Both prior compact/indent forms remain admitted for every role.

The [read-only metadata preflight](experiments/0227-qualification/metadata-preflight.json) accepts the original nine pinned files and passes the later receipt/source/reference/selected-row checks that ADR0226 never reached. The exact reference and rows 62/94/125 are unchanged, with three already saved point records loaded. Authenticated inventory is **2,504,838 bytes** under 4 MiB. Elapsed time **4.065886292 s** includes a call-profile guard that refuses scientific-artifact calls outside the metadata decoder functions; it is not propagation or representative numerical-dispatch timing. Budget counters for bounds/points/events/mass are all zero. `_methods`, numerical producer/auditor and all scientific helpers were not called, and neither retained output path was created. The [guarded driver text](experiments/0227-qualification/metadata-preflight-driver.txt) records this separate metadata-only check.

The complete guarded suite passes **6,578 tests in 159.76 s**, with 494 explicit native/live-UI/prohibited retained exclusions. Ruff, strict OpenSpec, local links, finite JSON, immutable source/input/legacy hashes and staged diff pass. Checkout bytes/status remain frozen for the full suite. [The manifest](experiments/0227-verification.json), [full log](experiments/0227-qualification/full-tests.txt) and [skip inventory](experiments/0227-qualification/skipped-tests.txt) preserve exact checks and sources; native qualification is not claimed.

AST comparison confirms every preexisting top-level node other than `_inputs` is unchanged; restoring only its decoder statements produces the original `_inputs` AST. The sole new function is `_record`. All historical mathematical sources, contract and prior adapter/evidence remain byte-for-byte unchanged. Independent read-only review confirms the same limited delta. No retained numerical dispatcher or retained saved-only auditor was invoked; no SPICE, integration, old scientific audit or R5.60 ran. Automation remains PAUSED pending the next execution decision.
