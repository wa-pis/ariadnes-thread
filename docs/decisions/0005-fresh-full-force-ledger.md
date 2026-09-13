# 0005 — Fresh-handoff full-force evidence ledger

Date: 2026-09-13. Reviewed revision: `ecd9b22`. M3 task3.9 remains open.
Status: accepted evidence inventory, not a new calculation or certificate.

## Reference and provenance

Candidate `d0001-t0035`, epoch 978995455.2929223 TDB seconds since J2000,
SSB origin, J2000 orientation. The old anchor is 978995455.2304223 TDB s;
the prospective local interval ends at 978995455.3554223 TDB s.
An instantaneous value does not bound that entire interval.

The [snapshot](../../tests/data/m3_fresh_harmonic_replay.json) binds the nominal
state, mass 2000 kg, stored harmonic matrices and resources of `direct-spice-v2`.
Its SHA256 is `e401d88cbdd0110ac6c0357612b0053a34f87f8953856ac3372360e5ea3dca99`.
These are synthetic diagnostic states, not an operational mission.

Code references below mean the reviewed revision of
[test_trajectory_spk.py](../../tests/test_trajectory_spk.py), primarily
`_check_conditional_full_force_coast_domains`. Existing captured output from the
2823-test run in [decision0004](0004-separate-harmonic-tail.md) was inspected
read-only. No new SPICE query or propagation was performed.

## Force ledger

All acceleration values/errors use m/s^2. Missing means not yet independently
assembled and verified at the fresh reference, not that no reusable formula exists.

| Component | Same-epoch evidence | Missing obligation |
| --- | --- | --- |
| Mars gravity, configured degree120 | Degree100 prefix plus higher-degree tail; L2 midpoint bound 7.82777879292353e-6, decision0004 | Source/PCK and incoming state-ball effects; not full degree120 arithmetic evaluation. |
| Moon gravity, configured degree200 | Fresh degree20 prefix plus higher-degree tail; component intervals in `fresh_harmonic_vector_enclosure`, tail L2 <= 2.7021574876745438e-120 | Scalar midpoint/error, source/PCK and state-ball effects. Tail alone excludes prefix rounding. |
| Sun point gravity | Fresh ideal source polynomial position; old point-force error oracle | Fresh acceleration vector/error assembly. |
| Mercury point gravity | Same source-reanchoring evidence | Fresh acceleration vector/error assembly. |
| Venus point gravity | Same source-reanchoring evidence | Fresh acceleration vector/error assembly. |
| Earth point gravity | Same source-reanchoring evidence | Fresh acceleration vector/error assembly. |
| Jupiter point gravity | Same source-reanchoring evidence | Fresh acceleration vector/error assembly. |
| Saturn point gravity | Same source-reanchoring evidence | Fresh acceleration vector/error assembly. |
| Solar radiation pressure | Old-anchor `_fully_lit_srp_anchor_error_bound_m_s2`, source-position variation and shadow checks | Independent fresh vector/error and rebound illumination/domain premises. Old full illumination cannot simply be copied. |
| Sun Schwarzschild correction | Old-anchor `_schwarzschild_anchor_error_bound_m_s2` and source-state variation | Fresh vector/error, Sun position/velocity uncertainty binding. Position-polynomial derivatives are not automatically the stored velocities used by this model. |
| Thrust | Examined arc explicitly has `thrust_enabled=False`; zero mass derivative checked | Explicit coast zero, not a missing-force default; no finite-burn qualification. |

Moon/Mars harmonic fields already include their degree-zero gravity. Do not add
their point gravity again. This coast has eight gravity sources plus SRP and
relativity, not ten gravity sources.

## Cross-cutting premises

| Premise | Available evidence | Remaining boundary |
| --- | --- | --- |
| Source motion | `fresh_source_affine_control`: eleven guarded links, eight chains, exact rebasing and sixteen reused position comparisons | Chain arithmetic bounds may be reused only with demonstrated coverage/binding. Reanchoring is not a source-induced force error bound; old epoch-specific floors cannot be copied blindly. |
| Rotation/PCK | Pinned resources, fresh stored matrices, old `_pck_matrix_error_bound` and rotation-rate machinery | Rebind ideal angles/matrix error and its force effect at the fresh epoch. Hashes do not bound angular error. |
| Incoming uncertainty | Conditional handoff position <= 0.00010529778787867129 m, velocity <= 2.3227467748483292e-7 m/s | Preserve these radii; nominal snapshot does not reset uncertainty. Sensitivities must cover state balls and reference chords. |
| Native total | Fresh observed acceleration (-3.147750890395473, 0.002978796195723602, -0.005506764365930771) m/s^2 | Observation, not independent enclosure. Fresh component assembly/rounding bound missing; subtracting Mars from the total does not qualify the other forces. |
| Ideal monopole jerk | Eight source intervals; L1 midpoint error <= 3.7770127063258504e-20 m/s^3 through `fresh_mars_monopole_jerk` | Not acceleration or full-force jerk; excludes higher harmonics, other forces, source arithmetic and state-ball effects. L1 bounds L2, not conversely. |
| Defect and domain | Old shifted-reference certificates and verified transport formulas | Fresh complete acceleration/variation bound and closed domain needed. Endpoint agreement is insufficient. |
| Integration/stage safety | Conditional endpoints and unchanged native counts | No full-mission or internal-stage safety certificate; finite-burn/collision tasks stay open. |

These numerical premises concern the pinned mathematical model and ephemeris
representation, not newly proven real-world model/observational uncertainty.
No total bound is reported: unknown entries are not zero.

## Selected next proof

Expose signed point-gravity component intervals from the existing
`_point_gravity_anchor_error_bound_m_s2` arithmetic. Its current result is an L1
error around an observation, not a vector reference. Keep its comparison API
by reducing the same intervals. Reuse the guarded square-root helper.

WHEN given exact rational relative coordinates and positive finite GM, THEN
verify signed/zero components, rational and irrational radius controls,
singularity/invalid input rejection and exact old error-reduction parity.
Qualify the pure helper first; then bind the six existing fresh source
polynomials without new queries or silent binary64 rounding. Bridges between
ideal polynomial and stored harmonic geometry remain separate obligations.

This addresses six explicit gaps with existing arithmetic. Repeating degree100,
raising to degree120, subtracting from a native total or extending the coast
would not establish those independent acceleration components.

## Verification

Checked source enumeration, epoch bindings, helper inputs and qualifiers against
code and captured outputs; checked links and strict OpenSpec validation.
No executable files, scientific constants or baselines changed. Full pytest was
not rerun for this documentary step; latest implementation verification remains
2823 passed in 475.24 s. Detailed historical observations remain in active tasks
and the reproducible inventory; this record is a scoped inventory, not a raw log.
