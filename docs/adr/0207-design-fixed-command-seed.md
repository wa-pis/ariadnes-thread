# 0207 — Derive one fixed command seed from the R4 endpoints

- Date: 2026-11-16 (Europe/Samara)
- Decision status: accepted research design under [ADR0205](0205-design-fixed-command-physical-join.md).
- Implementation: R5.59a design complete; no worksheet, generated pair or live admission.
- Scope: one analytic seed proposal for `d0001-t0035`, before R5.60.
- Base revision: `6a71bff`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-derive-and-freeze-one-fixed-command-seed), [design](../../openspec/changes/refine-physical-trajectory/design.md#r559a-design-the-fixed-command-seed-2026-11-16), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0135](0135-fixed-orbit-boundary-contract.md) and ADR0205 keep their physical gates.

## Context and constraints

Can a fixed-radius, fixed-phase impulse construction supply one
independently checkable *proposal* for two finite burns? No accepted
two-burn command exists. The [old seed](0079-research-reference.md)
used scalar impulse budgets and projected excess-velocity directions;
its full-force trial missed by about 198 million km and 31.16 km/s.
The [central correction](0098-central-correction-does-not-improve.md)
and [two fractions](0101-central-fractions-do-not-improve.md) yielded
no selection. [D13](0104-lunar-reference-has-two-geometric-branches.md)
failed at the fixed lunar phase under a tangential, pericentre-only
constraint. [D17](0116-quadratic-steering-stagnates-at-bounds.md) used
shifted ignition and steering slopes and never provided a Mars command.

Keep the R4 endpoints, body-relative phases and exact ADR0205 epochs,
spacecraft, forces and resources. Do not use the archived R5.51
spacecraft state, the R5.57 checkpoint state or differences, or saved
physical misses/Jacobians as fitting operands. Only the already frozen
checkpoint epoch is needed from that lineage, for event ordering.

## Options considered

- Reuse the historical controls or retry a correction: reject; the
  retained results supply no admissible pair.
- Change the phase/date or start a full-force targeting campaign:
  changes the question or requires a separate scientific design.
- Invert the two local two-body asymptotes at the fixed points, allowing
  a radial component at the impulse: selected. It addresses a specific
  missing geometric constraint in the old seed and admits a finite,
  independently checkable set of branches. It may yield no proposal.

## Decision and rationale

### Pinned inputs

| Source | SHA-256 | Allowed role |
| --- | --- | --- |
| [0119](experiments/0119-m2-reference.json) | `3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0` | `runs[0].selected` departure and arrival excess vectors. Use the signed physical-time direction and magnitude, not M2 scalar impulses or centre states as spacecraft boundaries. |
| [0098](experiments/0098-central-correction-study.json) | `b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057` | Require exact parsed scenario and candidate equality to R1. `science.runs[0].run.boundaries[0]` and `target_state` are the fixed SI/SSB/J2000 endpoints; `science.runs[*].controls` are rejection history only. |
| [0136](experiments/0136-retained-boundary-audit.json) | `81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063` | The two audited `rows`: endpoint and body translation, exact relative six components, harmonic GM and independently reconstructed periodic-orbit boundary. |
| [0079](experiments/0079-research-reference.json) | `17f03d9557be6e439af5f1c388e1eb092f55236b3c2afc3de65006d5f639c235` | `science.seed_commands`: exclusion only, after mapping into the six-word R4 command order. |
| [0101](experiments/0101-central-damping-study.json) | `70bd01122433fea421d27b44edd9bc1f5324e834aa80f8979af4e2d3b6af9c07` | `science.runs[*].controls`: exclusion only. |
| [ADR0205](0205-design-fixed-command-physical-join.md) | `4ced4dab487bfe5a06ef70e9dd56341d78a35e8aa1ec759b0cd40a1ac2126b6d` | Epoch words, spacecraft, production identity and downstream physical contract. |

Verify the complete stored endpoint and body records, including exact
epoch labels and reference frames, against R4. Use ADR0136's
`retained_relative_exact` as the mathematical six-component input at
each body; cross-check the subtraction against the stored SSB operands
and the independently reconstructed R4 orbit under the existing
0.001 m / 1e-6 m/s boundary gates. The harmonic GM for each body is bound
as a constant of this local surrogate; this does not evaluate harmonics.
The radius used to construct an orbit is distinct from the exterior
screen, which uses the pinned conservative spherical maxima **1,737,400 m**
(Moon) and **3,396,190 m** (Mars).

### Closed-form geometry at each fixed point

At a relative position `r_vec`, set `r = ||r_vec||`, `n = r_vec/r`.
Let `w u` be the prescribed *future* excess vector, with unit `u` and
positive magnitude `w`. Set `c = n·u`, `s = ||n×u||` and
`b = (u-c n)/s`. Conservation of the eccentricity vector at the
finite point and at future infinity gives
`e = (v×h)/mu - n = (w u×h)/mu - u`, so transverse speed `v_t` and
radial speed `v_r` obey:

```text
v_t² - w s v_t - (mu/r)(1-c) = 0
v_r = w c + (mu/r) s/v_t
v = v_r n + v_t b
```

Use the two signed roots only, evaluating the second by the root
product to avoid cancellation and `1-c` from `||u-n||²/2`. Reject
non-finite/zero excess, `s <= 1e-8`, singular angular momentum/bases
or ambiguous arithmetic; do not invent an extra root or phase. For
each root reconstruct `h`, `e` and the physical future asymptote:
`u_check = -e_hat/||e|| + sqrt(1-1/||e||²)(h_hat×e_hat)` and
`w_check = sqrt(||v||² - 2mu/r)`. Check positive hyperbolic energy
and the signed vector, not just its norm. The minimum radius on the
chosen future leg is `r` if outward or at pericentre, otherwise
`||h||²/[mu(1+||e||)]`. Require that this leg stays more than 0.001 m
above its spherical guard and that both arithmetic paths agree on
the radial/guard classification. This screens a point-body conic,
not spacecraft clearance under thrust or the complete production force
model.

For Moon departure use R1's departure excess as written, with
`delta_v_d = v_hyperbola - v_parking`. At Mars solve the future
problem with **minus** the stored arrival excess (the stored value is
`v_transfer - v_Mars` in physical time). Negate the solved velocity
once to get the incoming state at the fixed point; use
`delta_v_a = v_target - v_incoming`. The exterior screen there applies
to the reverse-time leg, equivalent to the past of the incoming
physical conic. The calculation need not force either impulse to
be tangential. It does not join the two conics in space or time.

### From two impulses to one proposal

Project the full impulse vectors onto **pre-impulse** body-relative
TNW: lunar parking state and incoming Mars hyperbola, respectively.
Use the production T along velocity, W along `r×v`, N = W×T. Use
canonical azimuth `[-pi, pi)`, elevation `[-pi/2, pi/2]`, and reject
undefined impulse directions. This provides initial constant TNW
commands for the subsequent real burns. The Mars basis here is an
impulse proxy at the *cutoff point*, not a claim about the actual
ignition state at t2.

Use `c_e = g0·Isp` and `q = thrust/c_e`. For each impulse in
departure-then-arrival order, compute
`m_after = m_before exp(-||delta_v||/c_e)`,
`tau = (m_before - m_after)/q`. Start the second calculation at the
first's remaining mass; no re-use of the 2,000 kg start or a scalar
arrival allowance. Freeze the proposed binary64 words and verify
`t0 < t1 < t* < t2 < tf` plus both exact dry-mass ledgers under the
worksheet's binary64 clock as in ADR0205. The real native event
representation and its effective mass ledger still need qualification
at admission. Reject rather than clip a duration to the 500 kg floor
or repair a collapsed epoch. This stage makes no 550 kg reserve claim.

Use one binary64 construction and an independent at-least-80-digit
invariant reconstruction, including signed energy/asymptote, angular
momentum, periapsis, TNW vector and sequential rocket-equation checks.
For accepted roots require reconstructed excess and full impulse
vectors within **1e-6 m/s** Euclidean, minimum leg radius within
**0.001 m**, and durations and mass estimates within **1e-6 s /
1e-8 kg**. Synthetic fixtures must use known states/asymptotes with
both angular-momentum signs and physical approach reversal, plus
degenerate, guard, near-tie and dry-floor failures. These are worksheet
checks only. Two arithmetic paths do not bound omitted forces or the
impulse-to-finite-burn error.

At most two roots at each endpoint and four Cartesian pairs per
arithmetic path. Exclude any pair matching a retained failed command after comparison
in canonical R4 order, including signed-zero equivalence. Among the jointly admissible pairs select the unique minimum
of `||delta_v_d|| + ||delta_v_a||` (maximum ideal final mass);
both paths must agree and the gap to any runner-up must exceed
**4e-6 m/s** in both. If qualification/selection is ambiguous or no
pair remains, return `command-seed-unavailable` with reasons and
null commands. No alternate start, dates, phases, extra roots or retry.

### Stage and admission boundary

R5.59b is only preparation on synthetic metadata. A separate request
after it passes may authorize R5.59c, **one offline generation and
independent saved-evidence readback**. Use one 15 s shared parent
deadline through startup, arithmetic, durable finalization and
readback, six pins with at most 512 KiB total input and 128 KiB
output including receipts, and zero SPICE, kernel access, force
evaluation, trajectory integration, targeting or new transfer search.
Use exclusive output; count failed work and keep first partial
evidence if a cap fails. The five stored JSON files are 342,277 bytes
before the ADR pin, within the input cap; runtime is unmeasured.

A successful `analytic-command-proposal` binds the fixed boundaries,
production model *identifier*, inputs, method/source hashes, all root
decisions, ranking, exact six command words, mass ledgers, timing,
units and independent proof/readback. It is immutable and has no
launch authority. Keep it separate from the artificial R5.59 schema.
One later admission record may reference its hash and bind the real
environment/solver/resource identities, coverage and native events
without editing the proposal or tuning against a checkpoint. The
independent reference, propagated numerical error allowances,
instrumented work budgets, safety handling and separate authorization
of ADR0205 still gate R5.60. That attempt, if ever authorized, consumes
the unchanged words once; a miss cannot feed a correction loop.

## Consequences and revisit conditions

The method supplies a reproducible reason for a trial input and can
rule out its own surrogate, without inferring whether a physical
two-burn solution exists. Earth and solar perturbations near departure,
gravity-field and SRP effects, finite-burn rotation, coast connection
and capture are outside the impulse construction. Even a good local
analytic result need not make the full-force attempt scientifically
useful: the readiness review must explicitly accept that limitation
before requesting authorization. If no proposal qualifies, document
the limiting geometry, arithmetic or mass constraint and stop. Any
broader targeting or changed physical assumptions require a new design.

## Evidence and verification

Checked archive hashes and selectors, exact source scenario/candidate
equality, retained unsuccessful selections, prescribed velocity signs,
equations and existing constants. Local links, diff and strict OpenSpec
validated. No command, candidate trajectory or numerical state was
generated. No SPICE, kernel reads, force evaluations, integration or
R5.60; runtime files are unchanged and the runtime suite was not rerun.
