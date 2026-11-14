# 0182 — Design the 300 s Earth-gravity comparison

- Date: 2026-11-14 (Europe/Samara)
- Decision status: accepted design. This record does not authorize live execution.
- Implementation: R5.35 design complete; R5.36 preparation pending.
- Scientific verification: pending the separately authorized R5.37 study and audit.
- Scope: M3 restricted Earth point-mass sensitivity on the same 300 s unpowered arc.
- Base revision: `5605354639db34ab516d1523f3516a78501613cb`, clean `dev`, equal to `origin/dev`.
- Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md#requirement-compare-earth-gravity-against-the-retained-a-coast),
  [design](../../openspec/changes/refine-physical-trajectory/design.md#r535-design-the-earth-gravity-comparison-2026-11-14),
  [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes / Superseded by: none. [R5.3](0148-short-coast-oracle-rhs-limit.md) and
  [R5.17](0164-corrected-coast-force-gate-fails.md) remain failed.

## Context and constraints

[R5.34](0181-split-moon-coast-recheck-passes.md) verified model A
(Sun and Moon direct point gravity) at its prescribed nodes and samples.
Earth was already queried and guarded, and served as the centre for one
Moon position leg. No Earth acceleration was added to the spacecraft.
The question from [ADR0137](0137-short-coast-earth-gravity-contract.md)
is how much the trajectory at those same epochs changes when that one
acceleration is included and the body ephemerides are held fixed.

## Options considered

- Evaluate Earth gravity along saved A and infer a displacement from it:
  useful as a local force diagnostic, but it omits trajectory feedback
  as the changed spacecraft state moves through all three fields.
- Recompute A and B: would repeat already checked A work and widen
  this stage. A fresh fully attested native A reference would require a
  separate contract if the conditional evidence proves insufficient.
- Reuse saved A and integrate B in both existing numerical engines:
  selected. Compare signed differences in both engines so a solver or
  model wiring discrepancy cannot pass by producing a similar norm.

## Decision and rationale

Fix the original R1/0098 identity and initial six-state, t0
978995455.2304223 TDB s since J2000, 300 s duration and seven nodes
t0 + 50*j s (j = 0..6). SI, inertial SSB/J2000, moving geometric
NONE ephemerides, GMs, radii and omitted forces remain unchanged.
There is no burn, phase change or terminal retargeting. B adds direct
Earth point-mass acceleration with GM 398600435468295.9 m³/s²;
there is no indirect-origin term. Earth, Moon and Sun tracks stay
prescribed. B's difference from A includes the response to the changed
path through the Sun and Moon fields.

Use the saved A RK4 h1/h0.5 nodes from R5.3 and A DOP853 normal/tighter
nodes from R5.34; no A solve or interpolation. Bind the exact report
bytes, attempt and receipt chains, profile controls and common
scientific identities. The original native A final identity remains
unavailable and makes the cross-engine inference conditional.

After offline preparation and separate execution authorization, run
only B: two native Tudat RK4 arcs (1 and 0.5 s) through the existing
private adapter, then two DOP853 profiles with the R5.34 settings,
compensated motion and split Moon force. At every RHS, use the same four
source routes and the existing Earth guard geometry to also evaluate
Earth's force, appending it to Sun and Moon in the component sum. Keep
models and engines separate. Reuse the existing reference records only
for checks; adaptive B epochs and spacecraft states must come from B.

Require the three original seven-node B comparisons and the original
signed sensitivity comparison:

| Seven nodes in each comparison | Position norm limit (m) | Velocity norm limit (m/s) |
| --- | ---: | ---: |
| B native h1 vs. h0.5 | 0.01 | 1e-5 |
| B native h0.5 vs. DOP853 tighter | 0.01 | 1e-5 |
| B DOP853 normal vs. tighter | 0.001 | 1e-6 |
| B-minus-A in DOP853 tighter vs. B-minus-A in native h0.5 | 0.02 | 2e-5 |

Retain both signed B-minus-A state vectors and their vector discrepancy,
plus position and velocity norms, at all seven epochs. The initial
difference must be zero in both engines. The endpoint is the primary
reported effect, accompanied by the six preceding nodes. A small or
zero effect is a valid result; distinguish effects within the comparison
scale from effects above it, by position and velocity separately, with
no formal uncertainty or significance claim.

## Evidence and verification

The [input manifest](experiments/0182-design-inputs.json) pins the
R5.34 reports and receipt set, R5.3 native A data, original contract
anchors, reference records and the source seams inspected in this design.
Static checks bind the archived receipts, common starting state, seven
nodes, profiles and the retained Type 2 record coverage. R5.35 ran no
SPICE, force calculation, ephemeris polynomial or trajectory.
Local links, immutable inputs, diff and strict OpenSpec are checked.
Runtime tests were not rerun for this documentation stage.

R5.36 must verify the private paths with synthetic or metadata fixtures
and no live SPICE or archived-trajectory propagation. R5.37 would use
one study within 60 s including finalization, and one independent
saved-data audit within 10 s. Both phases must pass. The [design](../../openspec/changes/refine-physical-trajectory/design.md#r535-design-the-earth-gravity-comparison-2026-11-14)
specifies the exact sampling, force/reference gates, caps and failure
behavior. These are ceilings, not runtime measurements for B.

## Consequences and revisit conditions

The result would measure Earth-force sensitivity for this specific
pair of models and this 300 s arc, conditional on the retained A
reference. Captured native telemetry and the independent replay check
recorded points and operands. They do not qualify unsampled ephemeris
fidelity, internal native RK stages, continuous safety, the full
transfer or M3. Missing coverage, numerical disagreement, identity
drift or budget failure stops execution with partial evidence and
unavailable work recorded. No automatic retry, tolerance or input
change. No production code or dependency changes; automation stays
paused.
