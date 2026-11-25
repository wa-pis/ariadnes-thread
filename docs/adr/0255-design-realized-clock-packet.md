# 0255 — Design a distinct bounded-realized-clock packet

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (private evidence contract only)
Implementation: not started; no native adapter, bound or executable profile adopted
Verification: independent scientific/source/scope review and documentary/strict checks
Scope / milestone: F9 / M3 preparation in the sole active change
Base revision: `193e7f2c28da62544ca6d8be3e38ea4d565d782a`, clean dev before design
Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-bound-realized-clock-evidence-without-changing-commands), [canonical contract](../../openspec/changes/refine-physical-trajectory/design.md#f9-bounded-realized-clock-packet-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves ADR0205/0250/0252/0254

## Context and constraints

[ADR0254](0254-record-native-event-transport-limits.md) records the pinned direct
API limitation without rejecting F0. [ADR0205](0205-design-fixed-command-physical-join.md)
already requires commanded/effective spans, both mass ledgers and justified
clock/mass/force contributions to endpoint allowances. The exact artificial F5
response cannot honestly stand in for those observations. F9 asks for the smallest
separate evidence/admission contract, without a calculation or experiment.

No command, event, source, kernel or trajectory is evaluated. No native import,
SPICE, test, implementation or new scientific bound is performed. Existing F7
local/CI evidence remains valid and is not rerun. All original fixed boundaries,
controls, hardware, models, physical/numerical gates and production caps persist.

## Options considered

- Relabel a close native time as F5's exact event: rejected; false identity.
- Use split Python exports or one float rounding cell as a complete native bound:
  rejected without a qualified conversion/normalization basis.
- Immediately implement a local-clock/full-force transform or another native
  campaign: deferred; complete absolute model mapping and error obligations remain.
- Define one fixed-shape packet under ADR0205, separating requests, native
  observations, justified enclosures and physical admission: selected.

## Decision and rationale

The linked design is canonical. One unreset three-arc path has four requested
chronological events, six native endpoint observations and four seven-state
nodes. It binds commands, fixed boundaries and scientific provenance. Actual
endpoint time, state AND mass cross each fresh-context handoff; independently
rounding the next start or merely reusing a JSON event ID cannot establish that.
A reverse traversal keeps physical RHS signs and requires its separately
qualified original-boundary/declared-mass anchor; no reverse profile is adopted.

Native Time observations and split Python export words remain distinct. A future
in-process reconstruction equality is useful producer-observed evidence for one
instance/runtime; the offline auditor cannot recreate original native identity
from JSON. No native enclosure is supplied by this decision. Unknown precision,
missing conversion basis and unsupported readback stay unavailable, never zero.

Signed epoch/span discrepancy intervals use the same actual event chain. Keep
requested and effective ledgers separately under the frozen binary64 mass-rate
word. Conservative lower mass bounds must establish the500kg floor before
rounding; matching tolerance never repairs a deficit. Actual returned mass is
checked and carried, not replaced. All native mass and continuous guard obligations
remain independent of four-node packet consistency.

Clock effects need justified transport through the full time-dependent force
model and existing endpoint allowances, including source/event branches. One
microsecond of time allowance alone establishes neither 1e-9kg of mass
agreement nor the position/velocity gates. Missing bounds are unavailable or
inconclusive; controller settings or empirical agreement are not certificates.
The Mars endpoint stays at its original target epoch/state; a reverse traversal
terminates at the original departure boundary. No numeric allowance is evaluated
or claimed by F9.

Structural validity, per-gate outcomes and physical admission are separate.
An evidence hash or caller-provided 'verified' flag cannot confer certification.
A complete diagnostic can pass its packet checks while physical admission stays
unavailable. Definite failure applies only to the fixed command, never a global
infeasibility result. A zero bound needs an actual justified identity and scope.

Future pure fabricated packet validation has a fixed4event/3arc/6observation/
4node shape,64KiB input,2MiB combined evidence/log output and15s inclusive
watchdog. Its scientific/native budget is zero. This does not authorize native
execution. Any separately admitted native synthetic follow-up retains F7's
existing6attempt/100000provider/60s limits; production73/76/228/300s is unchanged.
No generic backend, registry, public API or dependency is required by this design.

## Consequences and revisit conditions

F9 completes a data/admission contract, not physical readiness or a numerical
method. The next eligible ordinary preparation is a minimal pure checker on
fabricated intervals with an independent arithmetic oracle, under its explicit
zero-native scope; it may not accept physical certificates or actual native
observations as independently qualified. It must have its own completion checks
before code is described as qualified. No native adapter, actual readback,
mission search, consumed-study replay or R5.60 is admitted here.

Unqualified readback bounds, full-force seed, derivatives, safety/resource and
independent physical endpoint bounds remain open. Request the user's decision
only if concrete further work needs altered scientific contracts, dependencies,
commands, tolerances or unavailable access. Do not repeatedly request permission
for the already authorized reversible preparation or schedule diagnostic runs
merely to create activity.

## Evidence and verification

Read ADR0205/0250/0253/0254, the active requirements, existing F5 event/mass
checks and F7 native observation patterns. The source facts are already pinned in
[ADR0254's receipt](experiments/0254-design-verification.json); no native source
experiment or new runtime evidence is generated. Two independent read-only
reviews check scientific admission/handoff/mass/error semantics and the pinned
serialization/equality distinction. The new
[design-verification receipt](experiments/0255-design-verification.json) records
local links/anchors, protected historical bytes, CURRENT length, diff and strict
OpenSpec checks. No runtime tests are rerun for this documentary stage.
