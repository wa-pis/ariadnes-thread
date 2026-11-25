# 0257 — Design a conditional split-Time readback enclosure

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (conditional source-level design only)
Implementation: not started; no native exporter, physical bound or executable profile adopted
Verification: independent source/scientific review; documentary/strict receipt below
Scope / milestone: F11 / M3 preparation in the sole active change
Base revision: `d670ff04bc2b989d9200fcdbb19591638c6ee6e6`, clean dev before design
Related OpenSpec: [canonical design](../../openspec/changes/refine-physical-trajectory/design.md#f11-conditional-split-time-readback-enclosure-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves ADR0205/0254/0255/0256

## Context and constraints

[ADR0256](0256-qualify-fabricated-clock-packet.md) completes the fabricated checker
and its CI verification, not actual native readback. The concrete next blocker
is the missing justified conversion basis from stored native Time components to
Python evidence. We ask only whether a conservative symbolic enclosure can
avoid assuming nearest half-ULP rounding or a particular long-double mantissa.

The canonical design fixes the question, inputs/model/reference, unchanged gates,
completion criterion and600s source-review budget. No native imports, SPICE,
runtime tests, candidate/trajectory/oracle evaluations or integrations occur.
The original F0 data, six controls, hardware and73/76/228/300s stay unchanged.

## Options considered

- Assume exported words are exact or use a half-ULP cell: rejected; current
  source/provenance does not establish either claim.
- Adopt a different clock, native shim, dependency or a new diagnostic campaign:
  deferred; not needed to isolate this source-level obligation.
- Use the conditional adjacent-binary64 envelope while making missing caster,
  lawful-domain and build evidence explicit: selected. No code is needed yet.

## Decision and rationale

The linked canonical section is authoritative. Under its explicit conversion
premises, stored r lies between the two neighbours of exported y, so exact
integer-hour plus rational-neighbour arithmetic encloses the stored epoch.
This follows by cases from the C++ floating-conversion rule, with no numerical
candidate or artificial experiment. It does not infer the premises from finite
exported words, a caller verification flag or a producer roundtrip observation.

The installed getter/pickle path and CPython storage declarations are pinned.
The exact py312 extracted-cache path is absent; generic long-double caster
headers were not found in the inspected installed paths. A different Python-ABI
recipe cannot establish this binary's route. Thus the conditional derivation is
accepted, while the actual installed readback basis remains unavailable.

Source/scientific review also prevents unjustified clipping to a normalized
remainder range: comments do not establish that invariant for every floating
operation. Retain h/y as exported, including signed zero or a rounded3600.
Roundtrip failure rejects exact serialization, not necessarily a separately
justified conservative interval. No F5 exact ArcResponse is fabricated.

## Consequences and revisit conditions

This replaces an unbounded precision question with one concrete missing fact:
pin the exact extension caster/build route and supported lawful finite domain.
A bounded metadata/source lookup may prepare that fact without installing or
changing dependencies. Neither this decision nor a matching source hash proves
actual native identity, transport, endpoint accuracy or physical admission.

Keep unavailable if those premises cannot be established. A native experiment
or alternate implementation needs its own complete accepted scope before work;
there is no automatic synthetic diagnostic successor. Full-force clock effects,
actual carry, mass/floor/matching, derivatives/guards and independent physical
endpoint bounds remain separate. Ask the user only for a concrete required
contract/access/dependency decision; ordinary reversible preparation is authorized.

## Evidence and verification

Two independent read-only reviews check the conversion argument, exact source
anchors, missing provenance, normalization caveat and unchanged F0/physical gates.
The [design/source receipt](experiments/0257-design-verification.json) pins inspected
files and the review window; shared Time/binding/Conda hashes match ADR0254.
It records links/anchors, protected bytes, CURRENT length, diff and strict
OpenSpec. A separate [final documentary receipt](experiments/0257-final-doc-verification.json)
binds the final bounded-search wording clarification and final Markdown hashes;
the initial source/design receipt is retained unchanged. No runtime tests or new scientific work are performed. This is a
conditional proof/design result, not a native precision qualification or witness.
