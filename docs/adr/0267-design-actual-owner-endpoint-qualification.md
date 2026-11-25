# 0267 — Design actual-owner endpoint qualification

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (source-backed design only)
Implementation: not started; no new runner, native call or integration
Scope / milestone: F18.1 / M3 preparation in the sole active change
Base revision: `4a6f5d8275d8f53e1e0eaa7d2c7c4c6c9d717509`, clean dev
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f18-actual-owner-endpoint-qualification-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves F17's results and unresolved obligations

## Context and constraints

[ADR0266](0266-verify-provisioned-native-fixture.md) passes manufactured map/scalar
checks, not a simulation owner's method. The user's “делаем дальше” authorizes
this bounded preparation, not another native packet. Resolve the actual factory,
processed-row and lifetime route before implementing a fixture. Source/design
review, including independent review, is limited to900s; no imports, tests,
scientific/oracle evaluations, HTTP, payload copies, build, SPICE or integration.

## Options considered

- Repeat the eleven manufactured cases: no new owner evidence; rejected.
- Run the full six-arc F7 witness or a physical mission: unnecessary for this
  readback question, with wider force/carry obligations; deferred.
- Reuse F7's uniform-field translation/mass settings on two minimal coast arcs:
  selected. A polynomial reference isolates the owner seam without engines,
  ephemerides, search, node resets or a new native build.

## Decision and rationale

### Reachable source route

The private binding already exposes
`SingleArcSimulator._ariadna_original_endpoint(forward, schema)`. The factory
`create_dynamics_simulator(bodies, single_arc_settings, simulate_dynamics_on_creation)`
constructs `SingleArcDynamicsSimulator<double, tudat::Time>`. The method belongs
to the **simulator**, not `propagation_results`. It holds a shared owner, obtains
its shared single-arc results, checks performed/not-cleared and accesses the
original const map. The shared helper selects chronological min/max by const
iterator, validates the original remainder before narrowing, verifies seven
finite row values, then snapshots native fields/words before Python allocation.
No new accessor, compilation or operational installation is needed.

Source references and full hashes are in the [source/design archive](experiments/0267-owner-readback-design-evidence.zip).
Key anchors: patched simulator binding136–150; factory54–69; dynamicsSimulator
783–800/1124–1151; propagationResults156–182/371–380; results binding785–808;
project `_native_arc_conformance.py`233–291 and `trajectory.py`1689–1751.
Four relevant retained native headers match installed counterparts byte-for-byte.
These are source facts, not proof of the linked binary's complete ABI/FP basis.

### Fixed proposed analytic fixture

| Item | Frozen value / rule |
| --- | --- |
| Carrier | SSB/J2000-named native settings, explicitly labelled SYNTHETIC_INERTIAL / elapsed seconds; not physical TDB or ephemerides |
| Bodies | One empty Spacecraft, constant mass2000kg; no Moon/Mars bodies, kernels, gravity files, atmosphere, rotation, engine or radiation |
| RHS | Custom acceleration `(0, float(0.1), 0)` m/s², custom mass rate0kg/s; reuse F7's coupled translation/mass builder |
| Forward | elapsed0→1000s; literal SI row `(10000000,0,0,0,1000,0,2000)` |
| Reverse | elapsed1000→0s; independent literal SI row `(10000000,1050000,0,0,1100,0,2000)`; do not start from forward output |
| Integrator | Existing tighter coast RKDP87: relative1e-13; absolute position1e-5m, velocity1e-8m/s, mass1e-11kg; initial step+75/-75s, min1e-5s, max21600s; exact final condition, no minor-step termination |
| Result retention | Explicit `clear_numerical_solution=False`, `set_integrated_result=False`; record actual success and time-condition termination separately from performed marker |
| Row meaning | Independently establish processed-state metadata: indices0–5 Cartesian translation of Spacecraft relative toSSB, index6 Spacecraft mass; declared schema is not its own proof |

Both integration directions retain the same acceleration and mass-rate RHS.
The `forward` argument selects max/min stored epoch; it does not infer propagation
direction. Bind requested start/stop, signed step and row role externally.

The independent stdlib auditor uses exact rational values of each direction's
**own literal binary64** initial row, acceleration word and signed elapsed span:
`r=r0+v0*dt+a*dt²/2`, `v=v0+a*dt`, `m=m0`. It must not import the producer,
TudatPy or accept a producer-supplied reference. No values of this formula are
evaluated in this design stage. Require exact initial-row words, finite seven
values and terminal Euclidean position<=0.001m, velocity<=1e-6m/s, mass<=1e-9kg;
compare exact rational squared norms to squared gates. These retain F7's gates.
Do not reset native mass or reuse the forward output as the reverse oracle.

For each selected epoch expect hour0 and remainder numerically0 or1000; retain
actual binary64 hex/bits, including either zero sign. Numeric agreement at these
integer epochs is not native Time identity, arbitrary fractional/large-epoch
support, an event carrier or a proof of lawful prior arithmetic.

### Eight frozen visitor calls and lifecycle boundary

1. A never-run owner (`simulate_dynamics_on_creation=False`): RuntimeError
   `completed original results unavailable`.
2. Forward completed owner, `forward=False`: original start row.
3. Same owner, `forward=True`: original terminal row.
4. Same owner, schema `invalid`: ValueError
   `explicit Cartesian position/velocity/mass schema required`.
5. Retain its bound method and results alias, delete the original simulator
   variable and collect Python garbage, then call retained method(True): exactly
   the same terminal tuple/words. This checks retained-self ownership, not expiry.
6. Call the retained results alias's `clear_data()`, then retained method(True):
   RuntimeError `completed original results unavailable`.
7. Reverse completed owner, `forward=False`: its terminal/min-epoch row.
8. Same reverse owner, `forward=True`: its initial/max-epoch row.

Use the exact valid schema `cartesian-position-m_velocity-m-s_mass-kg` in every
other call. Retain arc/owner roles, actual processed IDs/vector length, native
context, settings and all outcomes in the packet. Previously returned primitive
tuples must remain word-for-word unchanged after clear/release; no borrowed
native row reference escapes. Do not export a Python state-history map for this
qualification. No public `solution_is_cleared` property is assumed.

Single-threaded, no uncontrolled native operations or callback mutation during
readback is an explicit premise. These tests do not establish owner destruction
timing, expiration rejection, arbitrary mutation, mixed-context safety or concurrent
synchronization. Performed alone is not successful completion. Any unsupported
metadata/completion/lifecycle premise leaves qualification unavailable.

### Future preparation and once-only execution

F18.2 may implement a **private** runner, independent auditor and injected tests
for the literal contract and failure limits, without executing this native packet.
Verify argument/order/schema/word/metadata failures, initial/terminal/direction
errors, retained-alias/clearing cases, oracle tampering and all counters/deadlines/
byte/watchdog boundaries, including full-size artificial data. At implementation
completion run the required frozen portable/live regression lanes, Ruff,
independent review and strict OpenSpec. Ordinary existing live regression does
not authorize the new private-owner packet. Pin exact runner/auditor/profile bytes.

F18.3 needs separately explicit authority after those prerequisites. Proposed
one fresh isolated packet: at most3factory attempts (one never-run plus two
simulated),2analytic integration attempts including failures,8visitor calls and
100000 **uniform-acceleration callback** entries precharged before work. This is
not a bound on mass-rate callbacks or all native RHS; retain native reported
function counts separately. Stop at first unexpected outcome; preserve partials,
consume the packet without retry/extra cases or retuning inputs/gates/caps.

Require <=600s same-interpreter comparable-clock preflight, independent control/
admission review before launch, source/kernel/resource pins and no pending work.
One external60s inclusive watchdog covers import, producer<=45s, independent
audit<=10s and5s finalization reserve through fsynced result/receipt. Input64KiB,
log64KiB, aggregate structured evidence2MiB; qualified process-group and streaming
byte controls apply. These are proposed engineering ceilings, not measured
performance. Missing prerequisites stop before native entry. New attempts require
new authority; old build clocks/closed ledgers and all old failures stay intact.

Reuse the exact isolated private image/kernel and five131662B local resource
files. No acquisition, rebuild, installer, dependency or operational-prefix change;
preserve8GiB scratch/2GiB cumulative acquisition and497045495B carried balance.
Check operational prefix/history after any authorized future execution. Eager
import resources were observed sufficient for the prior helper packet, not proven
for this new route; no automatic file supplementation or import-probing retry.
The historical F17 zero-propagation packet is not expanded by this distinct
unexecuted two-analytic-arc proposal. Automation remains PAUSED.

## Consequences and revisit conditions

Success would qualify only this private actual-owner serial readback fixture.
Parent F17 remains unchecked until its complete original obligations are met;
historical failed F17.1 cannot become a pass. Concurrency/native mutation, prior
Time arithmetic, carrier/carry, full precompiled-core/source/ABI/FP basis, full-force
seed/derivatives/guards and independent physical endpoint bounds remain separate.
No admissible command pair,99%probability, mission safety, physical F0 or M3 closure.
Stop for a concrete dependency/source/scientific-contract decision; do not grow
another optimizer or diagnostic campaign from this fixture.

## Evidence and verification

The [source/design result](experiments/0267-owner-readback-design.json) records
finite timing, exact pins, both source reviews, exclusions and read-only detach.
The source/design review completed in549.657s<=900s, including both independent
reviews and the final draft. The image was mounted read-only, its unchanged
source/runner/kernel hashes verified, then detached. No new full operational-prefix
scan was made; ADR0266 retains the most recent actual full comparison.
The source/design archive retains11members, original selected excerpts and reviews.
Both review-summary corrections are explicit: F7 was already seven-state coupled,
and the preserved position/velocity gates are Euclidean rather than componentwise.
[Documentary verification](experiments/0267-doc-verification.json) records protected
history, links/anchors, CURRENT length, diff and strict validation. Runtime code
and tests are unchanged; pytest/Ruff/CI and all native packets were not rerun.
