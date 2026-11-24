# 0250 — Qualify a coordinate bridge before physical solver adoption

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (private bridge and artificial-verification contract only)
Implementation: not started; no physical optimizer or native adapter adopted
Verification: design/source review only; artificial and native qualification remain separate
Scope / milestone: F4 / M3 preparation in the sole active change
Base revision: `5af711d8cdea0c68f08af4742bc8b131dd7c5f18`, clean dev before design
Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-the-coupled-coordinate-bridge-before-native-adoption), [bridge contract](../../openspec/changes/refine-physical-trajectory/design.md#f4-private-coordinate-bridge-before-native-adoption-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; narrows the F4 work unit without replacing any physical solver or gate

Later implementation: [ADR0251](0251-qualify-coupled-coordinate-bridge.md) records
subsequent artificial F5 qualification; the original F4 result below remains design-only.

## Context and constraints

[ADR0249](0249-qualify-coupled-artificial-shooting.md) qualifies recovery on a
manufactured problem, not arbitrary-node native full-force propagation. The next
question is whether the same transcription can carry large-coordinate states,
exact event meaning, derived mass and explicit arc modes without introducing
physical freedom or hidden resets. Answer this small interface question first.

The earlier F4 task promised a complete F0 method/verification contract. That is
premature: native time conversion, seed, derivatives, safe arbitrary-node arcs
and independent full-force endpoint-error bounds remain unqualified. Transparently
narrow F4 to this bridge contract; do not report a physical solver profile ready.
The production six-control forward-FD/lstsq corrector, eight iterations and
73-control/76-evaluation/228-native-call/300-second ceilings stay binding.

## Options considered

- Transfer F3's 18-variable TRF/default finite differences directly into production:
  not selected; the production algorithm is different, and normalized offsets do
  not themselves prevent perturbations disappearing at large absolute anchors.
- Wrap the complete historical research executor: not selected; it chains previous
  endpoints, limits execution to one command/two profiles, and rejects equality
  at dry mass. It cannot serve as an arbitrary-node evaluator unchanged.
- Qualify one private coordinate/event/arc-request bridge using fabricated data
  and an injected arc function: selected. Reuse low-level helpers only at their
  verified boundaries; defer native/optimizer adoption rather than invent it.

## Decision and rationale

The linked OpenSpec design is the canonical detailed contract. F5 may implement
one private evaluator and tests, with six physical controls and two normalized
translation-node offsets, exact rational event packets, the unchanged binary64
mass-rate word, explicit burn/coast requests, independent mass/time checks and
an explicit separate unreset replay mode. Exact rational event identity is checked
before rounded-label tolerance; node reconstruction uses exact accumulation and
one rounding, and simulated slots remain separate from zero actual native calls.
No generic backend, public API, search or real-data loader
is needed. Its injected flow is labelled artificial, not a substitute ephemeris.

An important reviewed risk is the mismatch between exact commanded duration and
an absolute epoch rounded to binary64. Existing arc construction reduces its
start epoch to float, while the mass-domain guard uses the duration words.
Preserve exact sums and conversion errors in the bridge; this is a precision
policy to test, not an observed native failure or a fix for the native clock.
In particular, freeze the current binary64 `F / float(g0*Isp)` result before
forming the exact mass ledger; decimal recomputation would change the input.

[SciPy's official API](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.least_squares.html)
distinguishes trust-region variable scaling, relative difference steps and the
function-count limit that excludes numerical-Jacobian calls. Our inference is
that explicit physical perturbation/representability tests and real callback
counters are needed; this source does not validate any F0 derivative step.
No optimizer or Jacobian is implemented in F5.

## Consequences and revisit conditions

F5 closure means interface/coordinate qualification only. Full-force inventory,
original fixed orbital states/epochs/planes/phases, hardware, six controls,
join/target/safety/resource/model/error-bound gates and consumed studies remain
unchanged. No boundary or budget change needs user approval at this stage because
none is adopted. Ordinary reversible artificial preparation is authorized by the
resumed automation; it does not admit a real run.

A subsequent native method contract must reconcile the mandated production
corrector explicitly, bind a complete seed, qualify exact-event consumption and
realized mass, establish derivatives and enforceable inner work caps, and meet
[ADR0205](0205-design-fixed-command-physical-join.md)'s independent force/reverse/
endpoint-bound prerequisites. No default diagnostic campaign or automatic
successor experiment is scheduled here. If a physical constraint, gate or cap
must change, pause automation for the concrete user decision. Unknown full-force
feasibility and missing error bounds are not cured by packet or CI success.

## Evidence and verification

Read existing ADR0247/0248/0249, ADR0135/0205, active requirements and the existing
helper interfaces. Two independent read-only reviews checked scope/reuse and the
precision proposal, including the binary64 mass-rate pin. No scientific import,
real archive evaluation, kernel access, SPICE query, force evaluation,
integration, optimizer call or artificial run occurred in F4. Runtime tests are
not rerun for this documentation-only unit; source-bound local/CI evidence remains
in ADR0249. Verification passes: strict OpenSpec,544 local links/five anchors across eight
Markdown files, one new requirement/four WHEN-THEN scenarios, separate scope and
precision reviews, diff and CURRENT_STATE under60lines. All1110 tracked
non-Markdown files, including code, legacy and retained evidence, remain
byte-for-byte unchanged. F4 design is complete; artificial F5 remains unchecked.
