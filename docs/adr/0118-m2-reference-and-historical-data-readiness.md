# 0118 — Specify the M2 reference before a historical comparison

Date: 2026-10-30
Decision status: accepted (user approved the contract and bounded verification on 2026-10-30).
Implementation: source/readiness audit complete; bounded R1.1 execution subsequently passed in [ADR 0119](0119-positive-ideal-m2-reference.md). Acceptance alone closes no scientific gate.
Scope / milestone: R1 preparation within the sole active M3 change; no M3 qualification.
Base revision: `ab9f2f5b14adcba59980cb783ba86b92e18e9511`, clean before the original planning stage. Its preceding push failed; the planning stage was subsequently pushed successfully as `5c7012c`. Execution provenance is separate in ADR 0119.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; elaborates [0117](0117-mission-first-demonstration-priority.md), preserving its order and gates.

## Context and constraints

The user asked about public historical missions and then asked to continue.
An archive can supply a useful empirical trajectory, but not necessarily the
complete force, mass and thrust model needed for an independent numerical oracle.
Do not turn source discovery into an automatic mission replay or a substitute
for the positive-reserve reference required by R1.1.

The existing M2 mass flag checks only final mass against dry mass. The current
examples and earlier experiments are immutable baselines, not already qualified
R1 references. Keep their names, bytes, targets and results unchanged.

## Options considered

- Replay GRAIL immediately and treat agreement as R1.2: reject. Force/version,
  maneuver-free interval and reference uncertainty are not yet reconciled.
- Replace Moon-to-Mars with a historical mission: defer; it would change the
  user-visible problem rather than verify the existing approximation.
- Specify a distinct M2 reference with an explicit reserve, and audit historical
  data separately: selected; the user subsequently accepted the contract. Reuse the existing
  planner and sampler; no new production dynamics engine or dependency.

## Decision and rationale

### R1.1 accepted problem and explicit inputs

User outcome: choose an approximate Moon-to-Mars transfer, understand its time,
ideal delta-v and propellant trade-off, and inspect a reproducible sampled coast.
Use model `sun-centered-zero-revolution-patched-conic-v1`: Sun-point-mass coast,
zero-revolution prograde Lambert solution and scalar instantaneous escape/capture
estimates. Body-centre endpoints are search approximations, not actual parking
orbit departure or Mars insertion states. Orbit-plane angles, finite thrust,
perturbations, SRP, maneuver errors and tracking do not constrain this M2 path;
retain and disclose its existing ignored-field manifest. No operational claim.

The new reference identity is `r1-m2-reserve-reference`, not D17 or a
reclassification of the old M3 fixture. After contract acceptance, create a
distinct scenario by copying every explicit TOML value from
[the existing hypothetical input](../../examples/m3_feasible_mission.toml), SHA256
`2c3b2a140d6e6ea00c2173caab5c51b1c4be87a112d2dec28a40cd1e2a0a9b42`.
It is not a GRAIL/MSL spacecraft model. Its fixed values include:

| Quantity | Fixed value and meaning |
|---|---|
| Departure window, UTC | 2031-01-01T00:00:00Z through 2031-12-31T00:00:00Z; explicit hypothetical search window, not an observed launch or optimized default |
| Flight time | 180–320 days, each day 86400 s; grid coordinates determine each candidate's actual arrival epoch |
| Local orbit sizes | Moon circular altitude 100 km; Mars periapsis/apoapsis altitudes 300/10000 km; used only in scalar M2 impulse estimates |
| Spacecraft | Initial 2000 kg, dry 500 kg, Isp 450 s; all remaining explicit values/orientations/tracking settings copied unchanged, even when unused by M2 |
| Grid | Budget 2000: existing 44×45 grid, 1980 attempts per complete search, not a promise to find 2000 solutions |

Fix **50 kg reserve before any new fixture/candidate selection**. This is a
hypothetical allocation for aggregate additional ideal delta-v up to 100 m/s,
at constant Isp 450 s, mass never above 2000 kg, no staging or mass additions.
The conservative required propellant is
`2000 * (1 - exp(-100 / (9.80665 * 450))) = 44.811085412142 kg < 50 kg`.
The main accounting already includes the two scalar M2 escape/capture estimates;
the 50 kg is held back afterwards, not consumed twice. This is not a scheduled
TCM, a finite-burn budget, or coverage of quantified navigation uncertainty.

A positive reference must satisfy `final_mass_kg >= 550.0` with no tolerance
admitting a reserve deficit. Independently recompute sequential ideal mass with
50-digit Decimal arithmetic; difference from reported mass must be <=1e-9 kg.
Among reserve-qualified entries in the returned Pareto front, choose the minimum
tuple `(total_delta_v_m_s, flight_time_s, departure_epoch_tdb_s, candidate_id)`.
Freeze that identity for replay; no hand-picked retained candidate. If none
qualifies, stop with a failed reference gate, not changed masses, dates or reserve.

### Bounded verification contract

After acceptance and a separate execution instruction, allow exactly two
identical complete planner calls and two 121-state sampler calls: at most 3960
Lambert grid attempts and 242 two-body samples. Use one shared 300 s wall-clock
acceptance budget including scientific/resource setup, with checks before and
after every top-level call; stop before any further call after exhaustion.
Existing native calls are not preemptible by that cooperative deadline. An
overrun is failure with the actual elapsed time, never a claimed bounded success.
No extra retry, grid expansion, optimization or network resource fallback.

Record actual normalized inputs, scenario/source/resource hashes, resolved SPICE
GMs, versions, grid counters, selected identity, mass/reserve, sampled states and
errors. Both runs must have identical scientific payloads; wall-clock timing is
reported separately. Require finite SI/SSB/J2000 states at TDB epochs, matching
Moon/Mars centre endpoints and their specified excess velocities within existing
100 m / 0.001 m/s M2 sampler gates. These are internal consistency tolerances,
not estimates of real mission accuracy. Resource/input/selection mismatch,
missing positive candidate, numerical failure or overrun stops the gate.

R1.2 still needs a separately accepted same-force oracle contract. A small coast
through existing `explorer.propagate_two_body` can be checked by independent
conic arithmetic without calling Tudat for the oracle; existing circular checks
are component evidence, not a newly completed benchmark. R1.1 repeatability and
historical agreement do not establish this independence or finite-burn accuracy.

### Historical source audit, checked 2026-10-30

| Candidate | Confirmed public metadata | Current readiness |
|---|---|---|
| MSL cruise | [SPK directory](https://naif.jpl.nasa.gov/pub/naif/pds/data/msl-m-spice-6-v1.0/mslsp_1000/data/spk/) lists `msl_cruise_v1.bsp` at about 618K; [SPK documentation](https://naif.jpl.nasa.gov/pub/naif/pds/data/msl-m-spice-6-v1.0/mslsp_1000/data/spk/spkinfo.txt) identifies reconstructed NAV cruise data and DE425/MAR085 companion ephemerides. [Dataset catalogue](https://naif.jpl.nasa.gov/pub/naif/pds/data/msl-m-spice-6-v1.0/mslsp_1000/catalog/spiceds.cat) leaves cruise reconstruction uncertainty TBD. | Preferred small candidate for a later empirical coast comparison, not selected as an oracle. The label could not be retrieved in this audit; binary segment coverage/comments and a maneuver-free interval remain unverified. |
| GRAIL science | [SPK directory](https://naif.jpl.nasa.gov/pub/naif/pds/data/grail-l-spice-6-v1.0/grlsp_1000/data/spk/) lists primary-science v02 at about 400M. Its [specific label](https://naif.jpl.nasa.gov/pub/naif/pds/data/grail-l-spice-6-v1.0/grlsp_1000/data/spk/grail_120301_120529_sci_v02.lbl) names gravity model 900c9a and coverage labels 2012-03-01T00:00:00 through 2012-05-30T00:00:00. | Defer as first small case. Do not infer precise binary segment coverage, body IDs or time-scale semantics from filenames/labels alone. |

The [GRAIL dataset catalogue](https://naif.jpl.nasa.gov/pub/naif/pds/data/grail-l-spice-6-v1.0/grlsp_1000/catalog/spiceds.cat)
describes a 420b8a science gravity field and metre-level absolute orbit accuracy,
whereas the specific v02 label names 900c9a. Do not transfer the generic accuracy
claim to v02 without reconciliation. NAV products may mix reconstructed and
predicted segments. The [archive SIS](https://pds-geosciences.wustl.edu/grail/grail-l-lgrs-3-cdr-v1/grail_0101/document/archsis.htm)
lists mass, thruster-activation and tracking products; their presence does not
prove complete calibrated thrust history for an arbitrary coast interval.

Before any historical comparison, independently fix the exact product URLs,
versions/hashes, inspected binary segment body/centre/frame/coverage, time scale,
companion kernels/load order, event evidence for a continuous maneuver-free arc,
force omissions, sampling epochs, comparison tolerances and execution limits.
Unknown uncertainty remains unavailable, not zero. Report empirical residuals
separately from same-model numerical error; neither is a positive fuel reference.
No kernels were downloaded or loaded and no historical arc was selected here.

## Consequences and revisit conditions

This supplies a concrete contract, not evidence that its candidate passes.
The user accepted it and separately authorized its execution on 2026-10-30.
If its checks fail, retain the failure and explicitly
review the problem; do not silently adjust inputs or reinterpret an old success.
Accept a same-force R1.2 contract before that benchmark, then follow R1.3/R1.4.
Historical replay cannot bypass this sequence or validate finite thrust, the
real parking/arrival planes, navigation uncertainty or a lunar-to-Mars mission.
No API/UI/exporter, dependency, automation or strict M3/task 3.9 gate changes.

## Evidence and verification — original planning stage

The source audit read official metadata only. Local read-only checks verified the
input SHA256, explicit values and 44×45 grid arithmetic. Independent 60-digit
Decimal and binary64 calculations agree within 1e-9 kg for the contingency bound.
Documentation checks include strict OpenSpec, local links, whitespace and scope
review; code/tests/environment/examples/legacy and old evidence remain unchanged.
Runtime tests and native scientific calculations were not rerun in the original
planning stage. No positive fixture, independent benchmark or mission validation
was claimed there. Execution evidence is recorded separately, without rewriting
those original observations.
