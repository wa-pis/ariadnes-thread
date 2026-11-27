# 0287 — Identify the next owner handoff prerequisite

Date: 2026-11-27 (Europe/Samara)
Decision status: accepted (source readiness and next mapping scope only)
Implementation / verification: F18.17 source review complete; no new adapter or runtime qualification
Scope / milestone: M3, F18.17 / conditional F18.18 source preparation
Base revision: 13f53fb663c7614b9d662beeddb7799d9d076ef3
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture)
Supersedes / Superseded by: none; preserves [0286](0286-verify-single-completed-owner.md)

## Context and constraints

Question: does F18.16 establish state/mass carry between the original0267arcs;
if not, what is the smallest missing prerequisite? Review pinned source and saved
metadata only. Original0267fixture and0247F0boundaries/sixcontrols remain fixed;
there are no free scientific variables. The draft question contained a misleading
premise:0267never intended carry between its two independent directions.

## Options considered

- Connect0267forward output to its reverse start: rejected. This changes the
  fixed independent literal and weakens the independent own-start oracle.
- Repeat the existing artificial carry/full-owner checks: no new seam covered.
- Identify the original endpoint-to-handoff interface gap before writing an
  adapter: selected. Do not attempt a general ABI/lifetime/FP or physical proof.

## Decision and rationale

[0267](0267-design-actual-owner-endpoint-qualification.md)'s reverse arc deliberately
starts from its own literal. `_owner_endpoint_fixture.py:129–134,318–345` chooses
separate initial rows and creates a fresh body system. This is a readback/lifecycle
fixture, not a failed carry test. [0268](0268-qualify-artificial-owner-runner.md)
already qualifies its artificial full runner.0286 observes one forward endpoint;
it proves no second-arc handoff or remaining0267lifecycle cases.

The existing artificial bridge already carries prior response state and mass in
replay (`_coupled_bridge.py:445–470`); shooting instead uses independent nodes.
The actual research caller supplies current state/mass and checks its saved
initial row (`research_propagation.py:302–317,353–366`). Its completed reader
(`trajectory.py:1821–1890`) still uses exported float/native-Time history maps;
the synthetic native reader likewise exports a map (`_native_arc_conformance.py:192–232`).
These are source facts, not a newly observed numerical failure.

The precise missing prerequisite is a source-backed association of original-key
owner endpoint, processed seven-state metadata and completion with the existing
state/mass/event handoff. F18.18 may **only map this interface from retained
source/saved evidence**, list already established premises and identify the exact
unavailable premise before any adapter is adopted. Keep requested, represented
and observed epochs distinct; integer1000s success does not establish arbitrary
native-Time identity or physical TDB. Preserve upstream safety classification,
owned primitive snapshot/error behavior and source-owner association. Never
substitute exported maps, stale rows, mass resets or a caller schema as proof.

For a proposed handoff, all seven binary64 words and their endpoint association
must be preserved exactly. Existing exact-event admission and1e-6s label/residual
checks remain distinct. If a later analytic fixture is separately admitted, retain
its own-start independent Fraction(binary64) oracle and Euclidean position<=0.001m,
velocity<=1e-6m/s and scalar mass<=1e-9kg. No oracle or trajectory was evaluated now.

F18.18 is bounded to600s from first related reading through independent review,
2MiB new evidence, zero scientific/oracle/command/trajectory evaluations, tests,
scientific imports, native/SPICE/integration/mount/acquisition/builds. A short
source-anchored interface table or exact missing prerequisite is sufficient;
no new framework or duplicate artificial campaign. Implementation requires its
own explicit accepted contract; another native episode requires distinct choice
and fresh admission.0285once-only authority remains consumed.

## Consequences and revisit conditions

This corrects the draft premise without changing0267or scientific requirements.
Serial native-owner/lifecycle, production carry, prior arithmetic/full core ABI/FP,
full-force seed/derivatives/guards and physical endpoint bounds remain separate.
Full0267/F0/M3/99-percent/safety remain open. Stop the next mapping at a precise
unavailable premise rather than extending the research or inventing execution authority.

## Evidence and verification

[Result](experiments/0287-owner-handoff-readiness.json) and
[immutable source/readiness archive](experiments/0287-owner-handoff-readiness-evidence.zip)
retain the fixed scope,10root source pins/excerpts, independent review with10pins,
and actual closure observations. Independent source review passes; root source
files and directory fsync observed at281.532204s, closure-receipt directory fsync
at281.532454s, within600s. These source-only clocks exclude subsequent documentary
publication, which supplies no additional source/scientific qualification.

[Documentary verification](experiments/0287-doc-verification.json) records evidence
syntax/member pins, protected prior blobs, links/anchors, CURRENT length, diff and
strict OpenSpec. Runtime code/tests/CI/dependencies unchanged; pytest/Ruff/native
and prior successful campaigns were not repeated. No live resource/prefix scan
was repeated; preservation here is repository/source evidence only.
