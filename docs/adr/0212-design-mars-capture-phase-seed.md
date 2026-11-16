# 0212 — Design a Mars capture-phase command seed

- Date: 2026-11-17 (Europe/Samara)
- Decision status: accepted research design; no new target admitted.
- Implementation: attribution checked on saved evidence; phase screen not implemented or run.
- Scope: separate phase study of reference transfer `d0001-t0035`.
- Measured base: `e68dd347dde358a8b27a36c225cb61a9c17cb88c`, synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-screen-a-separate-mars-capture-phase-seed-on-the-fixed-reference-ellipse), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559d-design-the-mars-capture-phase-screen-2026-11-17), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0211](0211-record-fixed-command-seed-refusal.md), [ADR0135](0135-fixed-orbit-boundary-contract.md) and [ADR0205](0205-design-fixed-command-physical-join.md) remain unchanged.

## Context and constraints

[The R5.59c report](experiments/0211-r559c/report.json) binds the
two radius-admissible local branches (positive/positive), but the pair failed
the commanded dry-mass floor. The costs are norms of velocity
differences before and after each ideal impulse:

| Leg | Before (m/s) | After (m/s) | Angle | Norm of impulse (m/s) | Difference of speeds (m/s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Moon departure | 1,633.504 | 3,362.289 | 59.012° | 2,884.055 | 1,728.785 |
| Mars capture | 6,120.692 | 4,266.267 | 114.162° | 8,777.253 | 1,854.426 |

At the fixed radii and energies,
`|v_after - v_before|² = (|v_after| - |v_before|)² + 2 |v_after| |v_before| (1 - cos θ)`.
The two speed gaps sum to 3,583.211 m/s, the collinear lower bound at
these points. The two vector norms sum to 11,661.307589 m/s.
On departure, 2,881.656 m/s of the impulse lies normal to the lunar
orbit plane. At the saved Mars periapsis, the incoming velocity has
-5,412.273 m/s radially outward and -2,505.266 m/s along the positive
target tangent. The capture must cancel inward motion and reverse
the along-orbit component. Mars accounts for 75.27% of total impulse.

With the remaining settings held fixed, the
[ideal rocket equation](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/ideal-rocket-equation/)
gives 6,117.706618 m/s from 2,000 kg down to 500 kg at 450 s Isp.
Keeping the verified lunar impulse leaves **3,233.652092 m/s** for
capture. Mars at the old phase exceeds the total budget by itself.
These numbers diagnose the local surrogate. They do not bound the
cost of all possible full-model trajectories.

## Options considered

- Vary the lunar phase alone: the retained Mars capture still
  exceeds even the entire ideal budget.
- Vary only Mars true anomaly at the fixed cutoff epoch: selected.
  This tests whether a more favorable approach on the same target
  orbit can cut the dominant vector cost.
- Free the target plane, turn the line of apsides, redesign the
  interplanetary connection or target finite burns end to end:
  changes more inputs and requires a different study. A heliocentric
  Lambert fit alone would not check local conics or mass admission.

## Decision and rationale

### Fixed operands and one new degree of freedom

R5.59d designs the trial; R5.59e qualifies implementation on
artificial archives; R5.59f is a separately authorized retained
screen. The retained input consists of ADR0211's four
[bound evidence files](experiments/0211-r559c). Authenticate their
external hashes from ADR0211 and the receipt chain. Retain candidate
identity, exact `t0/t*/tf` words, the lunar SSB and relative departure
state, and its independently audited positive root and impulse.
Keep the two signed R1 excess vectors, Mars SSB body state, orbit
elements other than true anomaly, both harmonic GMs and spherical
guards, initial/dry mass 2,000/500 kg, thrust 1,000 N and Isp 450 s.
Keep historical command exclusions. No fit to any R5.51/R5.57
spacecraft state, residual or past steering result is permitted.
The recorded positive lunar branch is an operand, not an admitted command.

The variable is Mars true anomaly, the
[angle from periapsis in the orbital plane](https://science.nasa.gov/learn/basics-of-space-flight/chapter5-1/#orbital-parameters-and-elements),
at the unchanged `arrival-cutoff` epoch. Changing it changes the
target position and velocity at that epoch. It requires a different
orbit phase datum under a separate research boundary identity; it
does not shift the epoch or model a wait along the old trajectory.
Preserve prograde motion, the binding eccentricity and the frozen
plane and apsides.

### Bounded search and verification

1. Generate exactly 360 samples `ν_k = 2π k / 360` for integers
   `0 <= k < 360`, with no refinement, restart or adaptive expansion.
   Retain grid index/rational turn and the binary64 angle word.
2. With Mars periapsis radius `r_p`, eccentricity `e` and harmonic
   `μ`, set `p = r_p (1 + e)` and `r = p/(1+e cos ν)`. Use
   perifocal `r(cos ν, sin ν, 0)` and
   `sqrt(μ/p)(-sin ν, e + cos ν, 0)` for position and velocity.
   Rotate with the frozen elements to J2000 and add both saved
   components of the Mars SSB state. The independent path forms
   radial and prograde transverse components with a separate
   high-precision evaluation of the grid angle and verifies energy,
   angular momentum and eccentricity vector. Use the existing
   0.001 m / 1e-6 m/s R4 state gates in both relative and SSB
   coordinates. Phase zero must also reproduce the saved endpoint,
   both radius decisions and the dry-floor refusal.
3. At each phase use the ADR0207 reversed Mars asymptote construction
   for both signed roots. Keep at most 720 Mars roots and 720
   phase/branch pairs per arithmetic path with the one lunar
   branch fixed. Verify signed physical arrival and full impulse
   vectors to 1e-6 m/s, minimum incoming-leg radius to 0.001 m
   and the strict 0.001 m exterior margin. The allowed
   capture conic leg checks the incoming past; it does not
   guarantee finite-thrust clearance.
4. Form candidate commands in the same pre-impulse TNW convention,
   using departure-then-arrival mass flow. Require exact binary64
   order `t0 < t1 < t* < t2 < tf`, both exact 500 kg ledgers, canonical command
   words and exclusions. Compare duration and mass estimates to
   1e-6 s / 1e-8 kg. The 3,233.652 m/s figure is explanatory; the
   exact checks decide. Only a common unique lowest-cost pair
   with more than 4e-6 m/s to the next eligible pair in both paths
   can yield a proposal. A verified empty grid yields
   `no-eligible-pair-on-grid`; disagreement, a tie or partial evidence
   yields an inconclusive or invalid result with null commands.
   A finite grid does not certify a continuous optimum or impossibility.
5. Run binary64 and an independent at-least-80-digit path under one
   30 s parent deadline through durable writes and independent saved
   readback. Limit archive input to 128 KiB, new evidence including
   receipts to 4 MiB, and charge every grid position and attempted
   root before work. Record all decisions and preserve the exclusive
   first complete or partial output. No SPICE, kernel access, force
   evaluation, trajectory integration, fitting or retry. Prove the
   workload and watchdog on full artificial inputs before approval
   of the single retained attempt.

A proposal binds its exact phase, exact target epoch and relative
and SSB SI/J2000 six-states, command words, source/model identities,
all decisions and exact mass ledgers. Artificial cases must cover
a zero-phase refusal with a known off-zero proposal, tilted-orbit
state reconstruction, Mars approach sign, guard and floor
boundaries, tie/ambiguity, tampering, all counts and caps.

## Evidence and verification

Verified the ADR0211 receipt chain and reconstructed the two norms
and ideal budget independently with 80-digit Decimal arithmetic;
the norm sum matched the archived pair within 1e-9 m/s. Calculated
angles and velocity projections only from saved vector components.
Checked local links, strict OpenSpec and a clean diff. No phase
sample, new target state or command was evaluated. No scientific
runtime changed, so runtime tests were not rerun.

## Consequences and revisit conditions

This screen can propose a cheaper local capture on the designated
ellipse; it cannot establish the heliocentric join, finite-burn
closure, reserve or mission safety. Any nonzero phase replaces the
full target state required by ADR0135/ADR0205. The original R5.60
remains unavailable. Adopting a phase-tagged proposal requires a
separate reviewed physical boundary contract, readiness and
execution authorization. A grid refusal ends this study without
loosening the gates; consider a different arrival geometry or
transfer design separately if needed.
