# 0117 — Put a useful demonstration before more local targeting

Date: 2026-10-29
Decision status: accepted (user-approved priority and planning gates).
Implementation: planning complete; R1.1–R1.4 specifications/implementation and scientific verification remain open.
Scope / milestone: near-term research demonstration within the sole active M3 change; not M3 completion.
Base revision: `866e593f5648de1e26b5d39982c1d54bcf7424e7`, clean before this documentation stage.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [proposal](../../openspec/changes/refine-physical-trajectory/proposal.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md).
Supersedes / Superseded by: none; sets the next priority after [0116](0116-quadratic-steering-stagnates-at-bounds.md), without replacing historical decisions, results or scientific gates.

## Context and constraints

The delivered explorer computes and displays an explicitly simplified M2
transfer. Recent D14–D17 work instead investigates one private local lunar
departure. D17 improves its residual but does not close its fixed target;
provisional post-arrival mass effectively equals dry mass. Even local closure
would not validate the omitted outer transfer, perturbations or Mars capture.

An exact fixed-epoch reproduction of an impulsive hyperbola is a useful test,
not yet a justified mission boundary condition for a finite-thrust departure.
More control coefficients or passing component tests alone do not establish
that this is the right next problem. The long-term platform vision remains
valid, but trajectory design, measurement-based navigation and data interchange
are separate capabilities and need not be delivered together.

## Options considered

- Immediately extend the D17 solver, seed or budget: rejected as the default
  next step; first justify the mission problem, feasibility and user benefit.
- Rewrite Python/TudatPy/SPICE or create a general backend framework: rejected;
  the retained study did not exhaust its runtime budget, and no demonstrated
  stack limitation justifies migration.
- Deliver one explicitly scoped, reproducible research demonstration with an
  independently checked calculation and exportable result: selected. Reuse the
  existing explorer and numerical tools instead of adding another private path.

## Decision and rationale

The near-term product is a research trajectory demonstrator, not operational
navigation. Keep the open-platform vision and Python/TudatPy/SPICE/Streamlit.
Use the delivered M2 path as the starting point; explicitly select the first
demonstration's model fidelity in R1.1, rather than implying finite-burn support.
An M2-level demonstration may succeed only at that stated approximation.

R1 replaces automatic successor planning with four ordered gates:

1. **R1.1 — Problem and positive reference.** Define a user-visible outcome,
   initial/final conditions and the physical reason for each constrained state
   component/epoch. Distinguish mission requirements from an impulsive reference.
   Before fixture selection, declare a numerical positive reserve in kg, its
   maneuver coverage, all explicit physical inputs, model omissions, numerical
   tolerances and bounded verification budget. A fixture becomes positive only
   after passing the declared checks at its named fidelity, not by renaming the
   old case or lowering a tolerance. Keep historical unclosed cases unchanged;
   they are not proofs of global infeasibility.
2. **R1.2 — Independent small benchmark.** Compare one frozen calculation with
   an independently implemented analytic reference or another numerical engine,
   using identical initial state, epochs, forces and any thrust/mass commands.
   State the reference, versions, numeric SI tolerances and execution limits
   before running. If finite burns are claimed, include non-negligible gravity
   and finite thrust. Two profiles of the same adapter or two separately
   optimized trajectories are not this independent check. A failure stops for
   diagnosis; it does not trigger extra optimizer complexity or silent retries.
3. **R1.3 — Result and interchange profile.** Specify the minimal normalized
   input/result contract, status semantics, model/provenance and UI invalidation.
   Select the exact CCSDS OEM edition/corrections, encoding, supported metadata,
   frames/time scales, conversion tolerances and independent reader before
   implementing export. Retain physics qualification and format compatibility as
   separate results. No generic plugin layer or competing orbit standard.
4. **R1.4 — One usable path.** After those gates and a separate implementation
   instruction, deliver input → calculation → display → export → independent
   decoding for the positive reference, with rejection/stale-result tests and
   focused/full regression. A new feature must improve this named path; another
   private study or additional test count alone is not product completion.

The early small benchmark is an explicit scheduling exception to the old blanket
deferral of independent-engine comparison. It is not M6's full-mission comparison,
Monte Carlo campaign or a continuous-safety certificate. Full strict M3 criteria,
including task 3.9, remain unchanged and open; R1 completion cannot archive M3.

## Consequences and revisit conditions

No D18, repeated D17 run, new seed/chart/budget, parameter relaxation or automation
restart follows this decision. New physical problems must receive their own
explicit scope without rewriting old artifacts. Preserve the original reference,
all retained JSON and `moon_to_mars.py`. No new dependency, public API, exporter,
runtime behavior or scientific result is introduced by this planning commit.

Detailed benchmark/profile values are intentionally still unselected. Accept the
corresponding detailed contracts and limits before separately instructed code or
native work; observed verification gates close only after their checks run.
If an independent reference/tool is unavailable, label that gate
unverified rather than substituting another run of the same implementation.
M4 estimation, M5 TCMs, M6 full-mission validation, ML and catalogue screening
remain deferred. Compact current status links retained history rather than
promoting every old experimental instruction to an active next step.

## Evidence and verification

The user approved the critical review and requested this OpenSpec record.
[0116](0116-quadratic-steering-stagnates-at-bounds.md) provides the measured
negative result; [the demonstration audit](../demo-audit.md) records the usable
M2 path, and [the vision](../../openspec/VISION.md) already separates interchange
from numerical engines. This stage adds no propagation or feasibility evidence.
Strict OpenSpec validation, independent scope-consistency review, local links,
whitespace and immutable/source/environment checks pass. Runtime tests are not
rerun because only documentation changes; no implementation checkbox is closed.
