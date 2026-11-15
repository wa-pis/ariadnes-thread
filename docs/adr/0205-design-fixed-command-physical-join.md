# 0205 — Design the fixed-command physical checkpoint test

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted research test contract; execution unavailable.
- Implementation: R5.58 design complete. No eligible command pair, qualified endpoint error bounds or instrumented execution budget is available.
- Scope: one existing candidate, one fixed comparison epoch, unchanged R4/M3 full model.
- Base revision: `f292fd60a2855c7ba143a5c7397542e322d9bbf6`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-test-one-fixed-command-pair-at-the-physical-checkpoint), [design](../../openspec/changes/refine-physical-trajectory/design.md#r558-design-the-fixed-command-physical-checkpoint-test-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. This specifies the physical readiness path of [ADR0202](0202-design-coepoch-mars-receiving-state.md) under [ADR0135](0135-fixed-orbit-boundary-contract.md).

## Context and constraints

Can one independently justified finite-burn command pair connect the
fixed lunar and Mars orbit states in the same production force model?
Test where the two arcs meet at the exact R5.51 checkpoint, and check
the Mars target separately. [ADR0204](0204-record-the-ideal-mars-checkpoint.md)
compares an ideal conic with archived model B; neither is a physical
operand for this experiment. The comparison epoch stays fixed.

The available archive does not supply an eligible two-burn pair.
[ADR0079](0079-research-reference.md) completed full-model arcs with a
seed derived from ideal impulses; it missed by about 1.98e11 m and
31,160 m/s and the profiles disagreed. [ADR0098](0098-central-correction-does-not-improve.md)
selected no correction; the [0101 fractions](experiments/0101-central-damping-study.json)
also remained unselected. [ADR0116](0116-quadratic-steering-stagnates-at-bounds.md)
has a local lunar burn and no accepted Mars arrival command. These
are informative negative results, not defaults to rerun. An admissible
new proposal need not already demonstrate target closure; it must be
justified and frozen before this experiment, with a provenance that
does not use the R5.51 spacecraft state or the R5.57 deltas to force a
match.

## Options considered

- Stitch model B to R5.57 or use an impulse as the Mars burn: it changes
  dynamics or event meaning and cannot answer the physical question.
- Start both arms at the same checkpoint state or tune controls during
  the comparison: this would impose agreement or turn the test into a
  search.
- Freeze one command pair and independently start at each orbit:
  selected. A miss applies to that one pair; it does not rule out other
  command pairs.

## Decision and rationale

### Inputs, events and declared mass

Bind the exact stored states, frame/units, phases, and scenario and
candidate equality through [R1](experiments/0119-m2-reference.json),
[0098](experiments/0098-central-correction-study.json) and the
[R4 arithmetic audit](experiments/0136-retained-boundary-audit.json).
The design pins the following retained evidence (SHA-256). The R5.57
record supplies checkpoint provenance without supplying an endpoint.

| Source | SHA-256 |
| --- | --- |
| [0119-m2-reference.json](experiments/0119-m2-reference.json) | `3606bb0a2af29a693a4c5192d88dcffd96a20a81b2d84771e916fbcdda7af8c0` |
| [0098-central-correction-study.json](experiments/0098-central-correction-study.json) | `b5b13613698aa9054477cb820af06f1ec32fe7909c7159f65566e562bd2f5057` |
| [0136-retained-boundary-audit.json](experiments/0136-retained-boundary-audit.json) | `81d78ecf6e4e80b55e9d909f929a879b2e392667387ec2569632aa99a6b41063` |
| [0204-record-the-ideal-mars-checkpoint.md](0204-record-the-ideal-mars-checkpoint.md) | `8365729fdf6c5480178edd0d719e74c9e022bc3ec1db275e1b2035a19e386ed6` |

The notation below denotes TDB seconds since J2000; the state uses SI,
SSB origin and J2000 orientation.

| Event | Frozen origin and meaning |
| --- | --- |
| t0 = 978995455.2304223 (`0x1.d2d247f9d7e7ap+29`) | 0098 `science.runs[0].run.boundaries[0]`, configured lunar orbit at departure ignition. |
| t1 | Departure cutoff, from t0 + departure duration under the frozen command and time convention. |
| t* = 979014965.9635216 (`0x1.d2d4a9afb54adp+29`) | R5.51 terminal epoch, comparison inside the coast; no thrust or phase change here. |
| t2 | Arrival ignition, from tf − arrival duration under the same convention. |
| tf = 1004169273.4122404 (`0x1.ded341cb4c44bp+29`) | 0098 `science.runs[0].run.target_state`, desired Mars orbit at arrival cutoff. |

The admission packet shall contain one canonical finite, nonboolean
tuple `(a_d, e_d, tau_d, a_a, e_a, tau_a)` in radians and seconds,
source and selection rationale, exact binary64 words, and digests of
both orbit states, resources and study settings. Use azimuth in
[-pi, pi), elevation in [-pi/2, pi/2], positive durations, and
t0 < t1 < t* < t2 < tf. Reject noncanonical input or collapsed epochs
before any work; never pick new phases, retime, normalize a different
command after freezing, or invoke targeting. Command values and
resulting intermediate times and masses remain absent until one
eligible immutable packet exists.

Use the fixed 2,000 kg initial mass, 500 kg dry mass, 1,000 N maximum
thrust, 450 s Isp, 9.80665 m/s^2 g0, 20 m^2 radiation area and 1.3
reflectivity coefficient. Let `q = thrust/(g0 * Isp)` in kg/s under
the production rate convention. The ledger is
`m1 = m2 = m0 - q*tau_d`, `mf = m2 - q*tau_a`. Check the dry floor
with exact rational arithmetic on the frozen binary64 rate and
durations, before rounding mass. Carry the declared mass into SRP and
propagate it as the seventh state; compare each propagated burn and
coast with its own ledger and retain the actual values. A separate
reserve claim would require at least 550 kg and its own evidence.

Freeze the actual native event representation and verify its elapsed
burn spans, not just displayed absolute epoch labels. Retain both
commanded and effective-span mass ledgers, reject dry deficit in either,
and include any time-conversion mass discrepancy and resulting force
effect in the endpoint error allowance. No silent rounding, duration
repair, mass overwrite or shared checkpoint mass injection. Agreement
against this common declared ledger verifies mass bookkeeping, not
independently measured propellant.

### Two endpoints in one force model

Bind the [production force and resource spec](../../openspec/changes/refine-physical-trajectory/specs/physical-trajectory-refinement/spec.md#requirement-declared-gravitational-dynamics):
`ssb-j2000-nbody-gggrx1200-200x200-jgmro120d-120x120-cannonball-srp-schwarzschild-direct-spice-v2`.
Use unchanged Sun/Mercury/Venus/Earth/Jupiter/Saturn point fields,
Moon 200x200 and Mars 120x120 harmonics with the declared GMs, hashes
and orientation frames, cannonball SRP with Moon/Earth/Mars shadows
and current mass, and Sun Schwarzschild with PPN beta=gamma=1.
Each path uses the same ordered direct geometric SPICE inventory
and selection semantics. Before admission, bind resource and solver
identities and qualified coverage for all target/center links and
rotations over the closed interval, including boundary/guard queries.
Do not smooth record or shadow transitions or approximate missing
coverage, silently change models or double count the harmonic degree
zero. Handle every relevant discontinuity in the numerical allowance.

Use fixed-body-relative TNW during both burns and the physical
`dm/dt = -q`; the reverse solver steps in decreasing physical time
without negating the RHS, thrust vector or stored velocity. Mass
therefore increases on the reverse burn. Set thrust and mass rate to
zero on the coast. The schedule is:

| Path | Exact stop order |
| --- | --- |
| Receiver, start independently from the desired Mars state and declared mf | tf → t2 (reverse arrival burn) → t* (reverse coast). Write and hash both solver receiver packets before any outgoing integration or residual calculation. |
| Outgoing and full forward check, start from the configured lunar state and m0 | t0 → t1 (departure burn) → t* (coast) → t2 (same coast) → tf (arrival burn). Continue at t* with the complete forward solver state and unchanged time, mass, model and command, without inserting the receiver or an impulse. |

The checkpoint coast split is an exact stop for sampling, not an R4
burn interface. Check assembly separately at t1 and t2; identical
handoffs alone are not independent evidence. Check target closure
in Mars-relative coordinates at tf from the unreset forward result.

### Numerical decision rule

Use the production tighter RKDP87 as the primary path and a separately
implemented DOP853 stepper and event/readback adapter as reference,
subject to qualification for decreasing time and the complete force
inventory. Before a retained run, pin both solver versions, settings,
precision policies and new source hashes. Validate the assembled RHS
against independently configured component and total force checks
under the existing M3 limits at fixed near-Moon, cruise and near-Mars
controls. Identical source resources are shared inputs; this is not
independent ephemeris truth. Existing forward-only wrappers and
short model B tests do not qualify reverse production work.

Require justified nonnegative endpoint error bounds for each compared
quantity from each path. A candidate approach is an interval enclosure
of local defects and force, clock and state-rounding errors, transported
over the complete path with bounded sensitivity through each
subinterval, including source branches and event boundaries. A
certified enclosure or equivalent independently checked method is
required to make a decisive numerical claim. Step-controller
tolerances, cross-solver spread and round trips are diagnostics rather
than error bounds. Missing bounds remain unresolved; M3's existing
10 m / 1e-4 m/s / 1e-6 kg profile limits do not imply R4 accuracy.
Check native epochs before reduction to floating-point labels. Near
1e9 s, a binary64 epoch ULP is about 119 ns; with about 30 km/s SSB
speed, that can shift a position by about 3.6 mm. Include conversion,
clock and coordinate assembly in the bounds.

Report signed incoming-minus-outgoing time, three position, three
velocity and mass components. For each observed absolute difference
or Euclidean norm d, use an outward-rounded interval
`[max(0,d-E), d+E]` with `E` the sum of applicable endpoint and
comparison error bounds. The R4 limits are **1e-6 s, 0.001 m,
1e-6 m/s and 1e-9 kg**; the separate forward target limits are
**1000 m and 0.01 m/s**, with target-coordinate conversion uncertainty
included if not exact. Pass a quantity only if its entire interval
is within its unchanged limit; fail if its lower edge is above the
limit; otherwise mark it numerically inconclusive. If no compatible
pair exists, leave physical residuals null. If only bounds are
missing, retain measured residuals as diagnostics and mark the
affected verdict inconclusive. Both solver paths must support the same
verdict; disagreements are inconclusive. Record join and target statuses
separately; one cannot compensate for the other. An invalid,
incomplete, resource-limited or unsafe/unresolved path cannot
certify a physical match.

### Bounded preparation and future execution envelope

| Limit | Requirement before any retained run |
| --- | --- |
| Offline synthetic readiness only | 15 s through durable finalization per fixture, 2 MiB compact inputs, 128 KiB output, zero kernel access, SPICE, force evaluation or integration; synthetic metadata and fake counters only. |
| Model run | At most one separately authorized attempt, one frozen pair, two solver paths, at most 12 attempted propagation segments in total (six per solver); zero fit/search calls, retries and automatic replays. Bound a single 300 s monotonic parent deadline from startup through receipt finalization, with at least 15 s reserved for finalization. Count before work, including failed launches and rejected steps; do not restart the clock. |
| Work and report ceilings | At most 1,000,000 RHS attempts and 32,000,000 provider state/rotation attempts combined across both solvers and all checks, and at most 64 MiB of new evidence bytes including receipts. Instrument the inner native work, or prove and charge a conservative worst-case count before each opaque call. Missing telemetry or an unenforceable cap makes readiness unavailable. |
| Independent saved-evidence verification | One separate native-free audit, at most 30 s through finalization, 64 MiB of run evidence and 128 KiB of audit output. Check identities, counters, endpoints, ledgers, bound certificates, intervals and first failure; no rerun. |

The 300 s ceiling preserves the existing production time limit; 12
segments are a much narrower study allocation than M3's public 228
native-call ceiling. The RHS ceiling is a stop limit, with headroom
over the historical scale of thousands of accepted coast steps times
multistage solves across both approaches. The provider ceiling is a
separate aggregate stop limit for resource use, not a measured
calls-per-step factor or allowance for opaque work. Evidence retains
bounded endpoint/guard summaries and error certificates, not an
unbounded all-RHS trace. From [ADR0083](0083-coast-step-study.md), the
forward tighter/capped profiles took 30.626 s for three coasts and
saved up to 5,036 intervals; that is neither a bound for this setup
nor evidence that a validated millimetre enclosure can fit. ADR0079
also saw 1,751.287 m profile disagreement at cutoff. No estimated
runtime or synthetic pass authorizes the physical run. An isolated worker and parent watchdog must stop new work by 285 s
and leave the parent able to finalize first evidence by 300 s, even
if a native call stalls. Qualify that path with a synthetic stall. Require
lower or equal caps, comparable timing evidence, coverage
and independently justified numerical bounds before separate
execution authorization. No limit rises on failure.

The next offline preparation must exercise valid metadata and known
pass/fail/straddling intervals, missing coverage or budget proof,
wrong epochs or source models, unqualified reverse semantics,
command substitution, mass rounding at the dry floor, counter
boundaries including rejected work, late finalization and hash
tampering. Record exact input, command, environment, solver and
output hashes on any future attempt; write new exclusive artifacts
and keep the first safe partial evidence on failure.

## Consequences and revisit conditions

R5.58 completes design only. Physical execution is unavailable:
no eligible frozen command pair, complete reverse/full-force
qualification with endpoint bounds, or enforceable timing and
telemetry evidence has been established. Readiness checks may be
prepared next on artificial metadata, without implying launch
approval. A future pass applies to one command under the pinned
model; strict M3, arrival/capture qualification, continuous safety,
and reserves remain separate.

## Evidence and verification

Verified the retained scenario, command-candidate history, endpoint
and checkpoint words, source digests, existing forces and scientific
gates, local links, diff and strict OpenSpec. No SPICE, kernel reads,
force evaluations, trajectory states, integration or optimization
performed. Runtime files did not change and the runtime suite was
not rerun.
