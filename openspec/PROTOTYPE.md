# Prototype first

User-approved priority change, 2026-09-07. Deliver a small, visible research
experience before continuing the high-fidelity engineering roadmap.

## First usable result

One local screen: explicit mission inputs, a transfer view with a time slider,
and a compact summary of flight time, ideal delta-v, and propellant budget.
Moon-to-Mars remains the only supported route initially. Reuse the working M2
search and real SPICE data; do not rebuild the solver or migrate the stack.
Load the existing example only through an explicit user action, not hidden
launch-date or spacecraft defaults.

The view should let a user choose a candidate and explore the approximate
spacecraft position and velocity over time. Label any 2D projection, reference
frame, units, and time scale. Sampling must follow the declared M2 trajectory
model; a decorative curve is not computed trajectory evidence.

M2 burns are instantaneous estimates at transfer endpoints, not resolved engine
firings or an executable lunar departure/Martian capture. Display this clearly.
Do not fake finite-burn durations, tracking accuracy, or successful insertion.

## Small delivery sequence and checks

1. Revise the single open OpenSpec change for this priority; preserve unfinished
   M3 requirements as deferred reference. Verify strict validation and ensure
   no old M3 task is marked complete merely because scope changed.
2. Show one real reference search and candidate summary. Verify displayed
   values match the existing M2 result, including its fuel-budget rejection.
3. Add trajectory sampling and the time slider. Verify endpoint agreement and
   sampled position/velocity against an independent two-body check with explicit
   SI tolerances defined in the revised spec before implementation.
4. Allow editing dates and spacecraft inputs and rerunning. Verify invalid
   input has field-level errors, successful reruns replace previous results,
   and failed reruns never present stale results as current.

First acceptance walkthrough: explicitly load the example, run the search,
choose a candidate, move the time slider, edit an input, and rerun without
editing a file or using the terminal. Keep the approximation warning visible.
Preserve the existing test suite and add only checks needed for these behaviors.

## Not needed for this prototype

High-degree gravity refinement, finite-burn targeting, orbit determination,
automatic course corrections, Monte Carlo, GMAT comparison, CCSDS exporters,
plugin frameworks, hosted deployment, accounts, and new mission routes.
Preserve existing code; do not delete it to simplify the prototype.

Success means the user can understand and explore the idea. It does not mean
flight readiness or validated high-fidelity feasibility. Review the next
priority after this walkthrough, not after completing all deferred milestones.
