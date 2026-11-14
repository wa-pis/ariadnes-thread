# 0185 — Independently check a 600 s model B coast

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted design; live execution requires separate authorization.
- Implementation: R5.38 design complete; R5.39 preparation pending.
- Verification: static evidence checks only; real R5.40 agreement unmeasured.
- Scope: restricted model B near the Moon, at the planned departure epoch.
- Base revision: `a5bc09ef57777adfc307ce5779b73f0c4c4d693b`, clean synchronized `dev`.
- Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-independently-check-the-longer-model-b-coast),
  [design](../../openspec/changes/refine-physical-trajectory/design.md#r538-design-the-600-s-model-b-check-2026-11-14)
  and [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none.

## Context and constraints

[R5.37](0184-earth-gravity-sensitivity-passes.md) passed the 300 s
tests for direct Sun/Moon/Earth gravity. Its signed Earth effect was
conditional on the saved A trajectory. It gives no evidence after
300 s. The starting six-state is the archived planned ignition
boundary: the spacecraft is still on its lunar parking orbit and
this experiment applies no thrust. No verified post-burn departure
state is implied by that label.

Question: if B starts from exactly that state and runs unpowered
for 600 s, do separately implemented integrators and a saved-data
audit still agree at the specified states and force samples,
including after 300 s?

## Options considered

- Reuse or extrapolate the 300 s result: cannot check new epochs on
  a dynamically evolved spacecraft path.
- Start from the saved 300 s state or use a post-burn boundary:
  the former inherits one solver's error, while the latter changes
  the experiment and needs an independently audited handoff.
- Double the span of B from the original state: selected. This
  preserves the seven earlier coepochs for a regression control
  and adds six coepochs under the same numerical limits.

## Decision and rationale

Use the same SI/SSB/J2000 and geometric TDB ephemerides, thirteen
kernels, GMs, physical radius guards and point gravity only. Compare
Tudat RK4 at 1 and 0.5 s with SciPy DOP853 normal and tighter, using
its separate force implementation, compensated epoch and measured
split Moon geometry. Each profile starts independently from the
same raw state. Compare at all thirteen nodes from 0 to 600 s in
50 s increments. Use the existing 0.01 m / 1e-5 m/s limits for
native convergence and the tighter cross-engine comparison and
0.001 m / 1e-6 m/s for DOP853 convergence. Check all four profiles
against their respective saved B prefix at their own profile limits.
The former DOP853 endpoint is now an interior output: require
numerical agreement, since step clipping can change the sampled bits.

Keep the force checks at every output and the original seven
initial RHS ordinals per adaptive profile. Add one deterministically
selected callback in each of the six 50 s intervals after 300 s.
Use the unchanged independent Type 2 and Fraction/Decimal evidence
checks. The two solvers share a physical model and kernel inputs;
the audit independently checks saved arithmetic and provenance
without rerunning a solver. This tests numerical agreement for B.
There is no model A propagation or extrapolation and no new B−A
measurement.

## Evidence and verification

The [static manifest](experiments/0185-design-inputs.json) binds
the original start, all R5.37 report and receipt bytes, preparation
manifest, inspected helper seams and retained record metadata.
The records already span the proposed end epoch,
978996055.2304223 TDB seconds from J2000. This establishes metadata
coverage; it does not verify live returns at the new epochs.
The archive, facts, links, diff and strict OpenSpec were checked.
No runtime tests, SPICE queries, kernel loads, record or force
evaluations, or trajectory calculations were performed.

R5.39 will prepare the private duration and sample handling and the
independent auditor on synthetic or metadata fixtures. R5.40 would
allow one study within 60 s and one independent offline audit
within 10 s, including finalization. Retain the two native and two
adaptive B solves and the 10,000 RHS and 1,000 trial ceilings.
R5.37 used 3,200 RHS and 263 trials in 6.6092 s (audit 1.8058 s).
That gives headroom for testing a doubled duration; it is not
a forecast or guarantee. The OpenSpec design specifies the exact
new counts and acceptance rules.

## Consequences and revisit conditions

A complete pass would verify sampled numerical agreement for a
600 s unpowered parking coast. It would not verify lunar escape,
the physical effects of omitted forces, continuous clearance,
a finite burn, the full transfer or strict M3. A real departure
coast needs a separately agreed post-burn boundary. An invalid
input, missing sample, gate or budget failure retains partial
evidence and stops; no retry, adjusted tolerance or shorter
substitution. No changes to previous studies or automation.
