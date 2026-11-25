# 0260 — Bound the Time construction/export domain

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (one narrow source-only review)
Implementation: no code or native adapter change
Verification: conditional domain/copy invariant independently reviewed; documentary/strict checks below
Scope / milestone: F14 / M3 preparation in the sole active change
Base revision: `f83f673be2799b428fa004868dca4cf6eed14994`
Related OpenSpec: [review contract](../../openspec/changes/refine-physical-trajectory/design.md#f14-narrow-pre-export-finite-domain-review-2026-11-25), [readback requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves F11–F13 and all physical gates

## Context and constraints

[ADR0259](0259-inspect-pinned-split-time-caster.md) establishes the inspected
generic double export route, conditional on actual selection and lawful native
inputs. Finite Python output cannot prove pre-export input safety. The next
useful question is narrower than another source collection or native fixture:
what can the already pinned Time construction/copy/export route establish?

## Options considered

- Treat a finite exported value or successful roundtrip as pre-export proof:
  rejected; these observations follow the conversion whose domain is at issue.
- Start a new native experiment or broad API review: deferred; a concrete source
  premise should be identified first without repeating existing work.
- One600s retained-source review of the named route: selected.

## Decision and rationale

Follow the canonical contract. Inspect only split/default construction, its
normalization, copy, component getters and existing pickle/caster dispatch.
Record explicit finite/input/integer-range and selection/FP premises separately
from source-derived preservation. A narrow supported conditional route must not
be generalized to arbitrary native integration keys. No new HTTP, implementation,
numerical/scientific evaluation, native import, SPICE, tests or integration.

## Consequences and revisit conditions

A successful argument adds a precise domain fact, not a qualified native exporter
or a physical command pair. A missing primitive remains explicit. No loosening
of F0 boundaries, clocks, mass ledgers, endpoint tolerances or budgets follows.
Ordinary reversible preparation remains authorized; pause only when a concrete
user/access/authorization or scientific-contract decision is actually needed.

## Evidence and verification

The scoped retained-source review ran03:35:17Z–03:38:45Z (208s<=600s),
including two independent reviews. All five inspected source hashes match the
exact package paths inventory already authenticated in ADR0258. The immutable
[source record](experiments/0260-source-review.json) retains paths, full SHA-256,
selected line bytes, pre-read contract hashes and the conditional argument.
This is installed-source evidence, not compiled-header/binary attestation.

| Route / premise | Source fact and consequence |
| --- | --- |
| Constant | Time34–37 declares3600; mathematicalConstants85–87 converts the integer to the requested floating type. Qualify that selected constant/FP route; no long-double mantissa is assumed. |
| Explicit split construction | Time68–72 stores caller h/r then normalizes. Caller must already supply valid C++int h and finite native0<=r<T. Python loading/argument identity remains separate. |
| Conditional no-op | Time1035–1042 tests r<0 or r>=T. Under the stated domain both tests are false: no modulo helper, integer conversion or hour update runs. This derives preservation from a precondition; it does not validate that precondition. |
| Copy | Time111–115 copies fields, resets auxiliary daysToAdd and invokes normalization again. It preserves the numeric pair in the same no-op domain; copying is not unconditionally bitwise or representation-preserving. |
| Getters and export | Time978–990 returns component fields; the existing binding229–238 makes a tuple and reconstructs through split construction. F13's conditional selected-caster/narrowing premises remain required. |
| Outside the domain | basicMathematicsFunctions77–83 calls integer-floor conversion and subtraction; utilities872–875 casts the quotient to int and may decrement it, followed by Time1041's signed-int addition. Separate finite/quotient/decrement/hour-range and FP premises are required. |

There is no native-finiteness guard in this reviewed path. Under ordinary NaN
comparison semantics, a NaN remainder can bypass both comparisons; infinities
or out-of-band finite values enter normalization. These are source/control-flow
arguments, not observed platform experiments. No universal normalization or
propagated-key safety is inferred from comments, finite Python output or a
successful post-export roundtrip. A rounded-to3600 export is still outside the
no-op reconstruction domain; signed-zero words must remain distinct evidence.

Clarification of [ADR0254](0254-record-native-event-transport-limits.md): its
phrase “finite normalized split storage” describes the intended representation,
not an unconditional checked invariant for every input or native key. This record
preserves the historical result while making its finite-domain premise explicit;
it does not supersede the stop-path finding or alter prior fixture results.

The precise remaining basis is domain validation/provenance of the ORIGINAL
native remainder before narrowing and before any normalizing copy. A native
const-reference finite/range predicate is a minimal conceptual primitive, not a
newly available or qualified API. Even such a predicate would only address the
current fields under lawful object/FP/source premises: it cannot retroactively
prove earlier propagation arithmetic was defined, establish original-key identity
from a JSON flag, or certify actual event/state/mass carry and physical gates.

[Documentary verification](experiments/0260-doc-verification.json) checks local
links/anchors, unchanged previous non-Markdown bytes, CURRENT/diff/strict and
source selections. No code, HTTP, runtime tests, native import, SPICE, numerical
trajectory evaluation or integration occurred. F0's inputs/gates remain fixed.
Next preparation may design one original-key pre-export admission path with
explicit source/lifecycle/prior-arithmetic obligations; no repeated collection,
generic checker or native/mission run is admitted by this source result.
