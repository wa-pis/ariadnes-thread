# 0252 — Check native arcs against the existing analytic witness

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (F6 synthetic native-conformance contract only)
Implementation: not started; no native or physical solver adopted
Verification: source/design review and documentation checks passed; no numerical execution
Scope / milestone: F6 / M3 preparation in the sole active change
Base revision: `c8195e9f74587ed508e34056bbd95db9dac509cf`, clean dev before design
Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-check-native-arcs-on-the-existing-analytic-witness), [contract](../../openspec/changes/refine-physical-trajectory/design.md#f6-native-analytic-arc-conformance-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves ADR0250/0251 and all F0 gates

## Context and constraints

Question: can the pinned native translation/mass engine execute the already
specified synthetic burn/coast/burn witness in both directions, carry returned
states and masses, and expose the actual event times without hiding conversion?
This is the smallest next seam after [ADR0251](0251-qualify-coupled-coordinate-bridge.md).
It uses [ADR0248](0248-design-coupled-synthetic-benchmark.md)'s known uniform-field
witness, not another optimizer or a real-data experiment. F6 performs no numerical
oracle evaluation, native import/run, SPICE query or trajectory calculation.

Source inspection identifies a transport limitation, not an observed propagation
error: pinned TudatPy1.0.0 uses native `Time`, but its time-termination settings
store a double endpoint. A `Time` start does not establish arbitrary rational
endpoint support. The source inventory below is the installed-build evidence;
current online documentation is background, not proof of this pinned build.

## Options considered

- Connect the complete F5 bridge to the mission optimizer now: no qualified
  exact-event transport, complete full-force seed or independent endpoint bounds.
- Round physical durations to fit native labels: rejected; that changes commands
  and can disconnect the mass ledger from the realized span.
- Check one existing analytic witness with explicitly limited event transport:
  selected. This measures a native seam without changing physical requirements.

## Decision and rationale

The linked OpenSpec contract freezes one forward three-arc path and one reverse
three-arc path starting from ADR0248's exact-decimal100-digit final seven-state
rounded once per component to binary64, not the forward output or a chosen
alternative reference. Both carry actual
returned state AND mass, use explicit burn/coast mode through the last stage,
and compare every event against independent Decimal80/100 reference nodes.
The reverse path changes the integration direction only, not velocity, thrust,
TNW or the physical negative mass-rate RHS.

Admit a request only if every exact rational event equals its binary64 label
and the labels preserve ordering. Refuse unsupported transport before native
entry without classifying the physical command infeasible or rounding it.
Keep requested rational event, represented label, expected native Time, observed
native Time equality and Time-before-float residual separate. A one-microsecond
residual cannot manufacture F5's exact `ArcResponse.end_event` identity.
The offline auditor cannot reconstruct native equality from float labels; that
comparison remains explicitly producer-observed evidence. Native equality
failure leaves exact transport unqualified even if state errors
pass. The integer witness does not test F0's large/fractional event domain.

Reuse the low-level engine, seven-state settings and tighter RKDP87 profile from
[trajectory.py](../../src/space_nav/trajectory.py), with a fresh synthetic body/
engine set per arc and a direction-aware private endpoint reader. The existing
reader selects the maximum epoch and cannot read a reverse endpoint unchanged.
Use the uniform field on all arcs, not the full-force environment builder.
Native SSB/J2000 carrier names do not turn the synthetic frame or elapsed clock
into real ephemerides or TDB truth. Keep a distinct conformance packet instead
of relabelling the production F5 request/response contract.

The existing exact-decimal physical oracle stays unchanged. Separately compare
against an independent Decimal80/100 closed form built from exact binary64 F,
gravity and frozen mass-rate words, using F/b as the effective exhaust speed.
Retain constant-conversion differences and the Fraction mass ledger; never reset
native mass or substitute the oracle state. Both references retain the original
0.001m/1e-6m/s/1e-9kg gates. No claim that rounding differences vanish is made.

Freeze six native attempts including failures,100000 precharged uniform-gravity
provider entries,64KiB input,2MiB combined evidence/logs and a shared60s external
watchdog (producer45s, independent audit10s, finalization reserve5s). These are
predeclared engineering ceilings for one fixed fixture, not measured performance
or new production caps. Native reported function counts are post-run diagnostics;
provider entries are not all RHS evaluations. Production inner-work admission
and the original300s/73/76/228 ceilings remain unqualified and unchanged.

## Consequences and revisit conditions

F7 may implement and qualify this bounded synthetic native fixture under the
standing reversible preparation/test instruction, after F6 documentation checks.
Repetitions of the new fixed fixture remain synthetic conformance, not consumed
real-study replays. Existing required live/CI regression remains separately
authorized and may use SPICE/native resources. No mission run, SPICE acquisition, optimizer, arbitrary-node adoption,
F0 derivative qualification, full-force reverse qualification or certified error
bound follows. Stop at the first fixture failure without retuning inputs,
profile, tolerances or caps; preserve separate failed/unavailable outcomes.
Pause automation only when a concrete needed choice/access or contract change
requires the user, or the agreed independently audited physical goal is reached.

A later physical contract still needs the original fixed boundary and complete
safe seed, mandated six-control FD/lstsq method, actual inner-work enforcement,
complete force/resource guards, qualified reverse path and independent endpoint
error bounds under [ADR0205](0205-design-fixed-command-physical-join.md).
Successful interface/native tests alone cannot fill any of those prerequisites.

## Evidence and verification

Text-only source review used pinned Conda `space-nav`, TudatPy1.0.0 build
`py312h2196d89_3`; no dependency or production source changed. Installation-relative
paths/line locations are retained with hashes in the new
[design-verification receipt](experiments/0252-design-verification.json):
`include/tudatpy/scalarTypes.h:18`, time-termination header:83/289,
Time binding:179/242/268, propagation telemetry binding:644, custom-acceleration
binding:1080 and step validator:95. The source establishes API/storage structure;
callback exception behavior, equality and reverse execution still need tests.

The official [Time migration guide](https://py.api.tudat.space/en/latest/migration_guide.html)
explains the Time/float distinction. The [time-termination API](https://py.api.tudat.space/en/latest/dynamics/propagation_setup/propagator.html#tudatpy.dynamics.propagation_setup.propagator.time_termination)
documents float endpoints, step-direction bounds and possible minor final-condition
deviations; our strict observed-equality gate is deliberately not assumed to pass.
Two independent read-only reviews checked scientific scope and pinned APIs.
F6 documentation checks pass: eight Markdown files,557 local links/five anchors,
1126 prior non-Markdown files unchanged,52-line CURRENT_STATE, clean whitespace
and strict OpenSpec. The linked receipt preserves the pinned source hashes and
review boundaries. Runtime tests and scientific calculations were not rerun in
this design-only stage. F7 implementation/native qualification remains open.
