# 0218 — Design the inter-node Mars phase check

- Date: 2026-11-18 (Europe/Samara)
- Decision status: accepted research design for R5.59g; no new target admitted.
- Implementation and verification: design only; no analytic evaluation or retained execution.
- Scope: the closed Mars true-anomaly interval [150°, 152°] for `d0001-t0035`, under the same local impulsive surrogate as R5.59f.
- Design base: `555ecf5465b66ae1c3e8e5e7cdbca0c123c7da7a`, clean synchronized `dev`.
- Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-check-the-continuous-neighborhood-of-the-best-saved-mars-phase), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559g-design-the-inter-node-mars-phase-check-2026-11-18), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0217](0217-verify-the-saved-mars-phase-grid.md), [ADR0215](0215-record-retained-phase-readback-failure.md) and the [ADR0205 physical contract](0205-design-fixed-command-physical-join.md) retain their scopes.

## Context and constraints

[ADR0217](0217-verify-the-saved-mars-phase-grid.md) verified that the cheapest **built pair on the integer-degree grid** was positive/positive at 151°, costing 6,157.791272 m/s against an ideal budget of 6,117.706618 m/s. The gap is about 40.085 m/s. The saved evidence excludes those samples; it supplies no lower bound between them. In particular, a root rejected at both ends of a cell can still matter inside it.

The question is whether **any** off-grid phase in the two adjacent cells [150°, 151°] and [151°, 152°] yields an eligible pair under the same surrogate and exact dry-floor checks. An improvement smaller than the shortfall does not answer yes. This local question neither searches the rest of the ellipse nor retargets the physical transfer.

## Options considered

- Interpolate the saved costs or fit a parabola around 151°: useful for a guess, but it cannot exclude a narrow minimum or a branch/guard change.
- Sample a finer fixed grid or optimize each apparent minimum: can find a witness, but failure to find one leaves gaps.
- Use bisection with conservative interval bounds and an independently checked point witness: selected. This can prove a local refusal or exhibit one eligible point within a fixed budget; an unresolved region stays unresolved.

## Decision

### Frozen inputs and point checks

Before a future authorized run, bind the exact SHA-256 of the [ADR0217 audit](experiments/0217-saved-grid-audit.json) and the three immutable ADR0215 records, verify their evidence chain and frozen operand digest, and pin the implemented verifier. Use only these four saved files as scientific inputs. Preserve the candidate, exact epoch words, positive lunar branch and impulse, signed R1 excess vectors, Mars body translation, orbit plane, apsides, eccentricity, GMs, spherical guards, spacecraft, mass and historical exclusions. Only Mars true anomaly at the original arrival-cutoff epoch varies. The design uses no trajectory residuals, new body states or SPICE kernels.

Start from the two adjacent closed cells and keep endpoints as exact dyadic degree fractions. Process shallower cells first, lower angle first, with bisection at the exact midpoint. Cover **both** signed Mars roots; preserve the physical-time arrival reversal of [ADR0207](0207-design-fixed-command-seed.md). Re-evaluate exactly the three saved anchors before refinement, under the same point budget. Require agreement with the saved states, signed root dispositions, available costs and pair refusals within their original gates. The saved node data do not determine an interval bound.

A new midpoint can establish existence only if the binary64 construction and independent at-least-80-digit path agree under ADR0212: SI state in Mars-relative and SSB/J2000 frames within 0.001 m and 1e-6 m/s; unchanged signed-asymptote and impulse gates; incoming-leg radius within 0.001 m and strictly more than 0.001 m above the guard; durations within 1e-6 s and masses within 1e-8 kg. Require canonical pre-impulse TNW words, exact event ordering, both exact 500 kg mass ledgers and historical exclusions. Require the point's total analytic impulse to be at or below the unrounded ideal budget in both paths as well. Report the exact phase, sign, costs and ledger evidence for a passing witness; it shows existence, does not select a unique optimum and supplies no adopted or executable commands.

### Whole-cell exclusion

Use outward enclosures of the existing ellipse and reversed-conic formulas, with an enclosing value of π, trigonometric remainder bounds and outward square-root, exponential and rounding enclosures. Nearest-rounded evaluations at the interval endpoints are not enclosures. For each closed cell and each sign, try to prove that the entire leg is rejected by an existing geometry gate or that its commanded mass must fail. A guard exclusion requires a conservative upper bound on minimum incoming-leg radius at or below the original guard threshold, including rounding. If radial sign changes, enclose both radius cases or subdivide. A root denominator, asymptote alignment or branch boundary that cannot be bounded cannot justify pruning. Use no inferred root monotonicity or smoothness from integer samples.

For mass exclusion, the ideal 6,117.706618 m/s figure alone does not certify the rounded command ledger. Use outward lower bounds `L_d, L_a` on each independent comparison duration **after** its conversion to binary64, including finite-precision error in the oracle. Let `E` be the next binary64 value above the existing 1e-6 s comparison threshold, a conservative envelope for rounding of the difference, not a changed acceptance tolerance. Any passing branch needs commanded duration at least `max(0,L_i-E)` for each burn. With the exact rational value of the frozen binary64 mass-flow rate `q`, exclusion follows only when the resulting lower bound on `q*(td+ta)` is **strictly greater** than the exact 1,500 kg available above the floor. Equality, uncertain arithmetic or overlap with a gate is unresolved. An independent verifier must check these claims from authenticated primitives and recorded enclosures with outward bounds of its own; rerunning a floating-point optimizer or trusting logged endpoint samples cannot certify a refusal.

### Outcomes, limits and authorization

- **Eligible off-grid witness:** at least one proposed phase satisfies all point gates. Record its evidence without claiming a continuous unique optimum or handing commands to R5.60.
- **No eligible pair on the local interval:** verified intervals cover the two closed cells without holes and exclude both signed roots for every phase, including every shared boundary.
- **Inconclusive or invalid:** any remaining branch/cell, mismatched anchors, unauditable coverage, exhausted budget, failed authentication or arithmetic disagreement. Preserve partial evidence and do not report a local refusal.

Charge before work. Cap depth at 5 from each original 1° cell, 126 examined cells, 252 branch-cell enclosures per path, and 129 direct phase evaluations per path (3 saved anchors plus at most 126 midpoints), each with at most two Mars roots and two pairs. The independent verifier is subject to the same work caps. Cap the combined producer, durable output and readback at 30 s; charge at most 4 MiB of pinned source input per reader and 4 MiB of new evidence including receipts. Use fixed exclusive output for the first complete or partial result. Do not expand the interval or retry within this contract.

Future qualification on artificial inputs must check a narrow passing off-grid witness between failing nodes, a complete two-sign refusal, a possible root/guard transition, a numerical or mass equality boundary where exclusion must remain unproved, cover holes, tampering, and full workload/cap refusal. Run focused tests, guarded full pytest, Ruff and strict OpenSpec before any retained invocation. After that, a separate authorization is required for at most one offline local audit with the retained inputs.

## Evidence and verification

The design uses the published ADR0217 figures and existing code contracts. Only documentation, links, strict OpenSpec and scope checks were performed. No node, midpoint, conic, command, interval bound, SPICE query, force evaluation, propagation or R5.60 was run. Runtime code and archived evidence were untouched.

## Consequences and revisit conditions

An interval exclusion only answers the local question on [150°, 152°] for the fixed model; a witness only supports an analytic point on that ellipse. Either result leaves the original R5.59f invocation incomplete and consumed, and R5.60 unavailable. A positive witness changes the full Mars target state and would need separate boundary review and physical readiness before it can be used. An inconclusive result calls for a reviewed proof change or a separately scoped study, with no automatic retries or tolerance relaxation.
