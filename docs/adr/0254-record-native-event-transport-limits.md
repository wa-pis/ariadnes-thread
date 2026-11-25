# 0254 — Preserve requested events across native transport limits

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (source limitation and preparation direction only)
Implementation: no code change, physical adapter or native execution adopted
Verification: pinned-source/design review; documentation/strict receipt below
Scope / milestone: F8 / M3 preparation in the sole active change
Base revision: `813f6e9f511a4b6a1fa22fab969e022c8e10603d`, clean dev before design
Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-separate-requested-events-from-native-transport), [design](../../openspec/changes/refine-physical-trajectory/design.md#f8-native-event-transport-limits-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves ADR0205/0250/0252 and their distinct scopes

## Context and constraints

Question: does the pinned native API provide the lossless event transport that
would let the artificial F5 exact-event interface consume arbitrary F0 burn
durations unchanged? Budget: at most ten minutes of installed-source review,
zero native imports, scientific evaluations, propagation, SPICE or test runs.
[ADR0253](0253-qualify-native-analytic-arc-conformance.md) qualifies six synthetic
integer-event arcs; it does not answer the general derived-event question.

Requested events remain exact input-word sums: t1=t0+tau_d and t2=tf−tau_a,
with masses derived from the unchanged binary64 rate and duration words.
An absolute label, native Time object, physical command and realized integration
span are different evidence. No current candidate sum is evaluated in this unit.

## Options considered

- Apply F7's representable-only path to all F0 events or call a nearby label exact:
  rejected. The inspected API does not provide that general guarantee.
- Use a custom stop, split Time constructor or local elapsed clock as a complete
  fix: not adopted. These do not by themselves qualify landing, complete-model
  absolute-time mapping or lossless transport over every required span.
- Preserve F5/F7's exact contract and prepare a separate bounded-realized-clock
  physical contract under the existing ADR0205 allowance: selected direction.
  No new implementation, dependency, numerical profile or experiment is selected.

## Decision and rationale

The [canonical design](../../openspec/changes/refine-physical-trajectory/design.md#f8-native-event-transport-limits-2026-11-25)
records the source trace. Installed TudatPy1.0.0 uses native Time, but time
termination stores and returns double. The exact-final-step branch rolls back
and computes a step toward that double stop value; it does not restore an
unrepresented requested Fraction. Stop checks reduce current time to double.
Custom termination settings accept double and the exact-custom branch explicitly
returns the state after condition violation; the binding's Time docstring is
not proof of a lossless custom-stop path.

Time has finite normalized split storage: integer hours plus a long-double
remainder. Its split constructor/arithmetic and native equality are useful,
but equality of constructed native values does not establish arbitrary rational
input identity. Python float conversion is a separate reduction. No claim about
a universal long-double mantissa or an observed platform error is inferred.

A local clock could help a restricted domain. It would still need a checked
absolute reconstruction for every time-dependent ephemeris, rotation, shadow,
guidance and force, and the coast span is another exact sum/difference. The
public custom-ephemeris callback is double-valued in time. No full-force clock
transformation or unsupported broad impossibility result is established here.

[ADR0205](0205-design-fixed-command-physical-join.md#inputs-events-and-declared-mass)
already requires commanded and effective-span mass ledgers, actual native event
representation and time-conversion mass/force effects inside justified endpoint
error allowances. A future distinct native packet may follow that existing
physical contract while preserving requested Fraction events and commands.
It must not fabricate F5's exact ArcResponse identity or relax F7's admission.

Before implementation, that distinct packet needs a complete bounded contract:
immutable requests, native/readback provenance and precision limits, signed
elapsed-span discrepancies, both dry-floor ledgers, propagated actual mass,
independent discrepancy/error-bound checks and finite work/time limits. Missing
justified bounds remain unavailable or inconclusive; controller tolerances,
close labels and cross-solver agreement cannot substitute for them. None of
those missing bounds is calculated or supplied by this record.

## Consequences and revisit conditions

The present direct path remains limited to events satisfying its exact
representability and observed-equality gates. This is an adapter limitation,
not observed native propagation failure, physical infeasibility or a changed
F0 target. No candidate, duration, kernel, hardware, force, phase, solver or cap
changes. Original join/target gates and ADR0205 error-bound obligations remain.

A documentation-only F9 may specify the separate realized-clock packet under
that pre-existing allowance, without adopting an implementation or scheduling a
native campaign. This ordinary reversible preparation needs no new user choice.
Pause if concrete design later requires changing the scientific contract,
dependencies, commands, tolerances or unavailable access. Do not generate another
experiment merely because the fixed F7 fixture passed. All full-force seed,
derivative/resource/safety and independent endpoint-bound gates remain open.

## Evidence and verification

The new [source/documentation receipt](experiments/0254-design-verification.json)
pins eight installed files, inspected line anchors and Conda build metadata;
shared hashes match the earlier ADR0252 source inventory. Source reading ran
from01:11:42Z through01:17:09Z within the declared ten-minute limit. Two
independent read-only reviews checked termination/last-step behavior and
Time/local-clock/physical-scope interpretation. The current source trace is a
read-only inspection, not a numerical experiment or a claim of complete API
impossibility. No native import, SPICE, oracle, command/trajectory evaluation or
runtime test was performed. The receipt additionally records local links,
anchors, protected bytes, CURRENT length, diff and strict OpenSpec checks.
