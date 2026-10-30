# 0122 — Independent elliptic coast comparison passes

Date: 2026-10-30
Decision status: accepted (user separately authorized the single ADR 0120 study).
Implementation: R1.2c evidence complete; all 17 pairs and offline audit pass.
Scope / milestone: R1.2 synthetic coast-component gate only.
Base revision: `35ae8a324ab38fa8da8bf74f5bfe775df78e338a`, clean before execution.
Related OpenSpec: [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md).
Supersedes / Superseded by: none; executes [0120](0120-independent-elliptic-coast-benchmark.md) after [0121 preparation](0121-elliptic-benchmark-preparation.md).

## Context and constraints

The accepted contract requires an independent analytic comparison before result
export design. User authorization permits one 17-call/shared30s study, not retries,
retuning or native regression launches. Production and the prepared runner remain
unchanged. The exclusive output reservation is the only dirty path recorded by
the before/after execution provenance; later audit/documentation edits are not
misrepresented as measured production changes.

## Options considered

- Repeat or tighten a passing study: reject; outside the authorized budget and
  unnecessary for the predeclared gate.
- Retain the single result and independently audit its arithmetic offline:
  selected. This provides inspectable evidence without new native computations.

## Decision and rationale

Close R1.2/R1.2c at their declared component scope. The one execution made exactly
17 attempted/completed adapter calls in epoch order and finished in
**0.5558036253787577 s**, including imports, identity checks and oracle work.
All 17 finite six-state pairs satisfy exact epoch/elapsed alignment, root bounds,
state agreement and energy/vector-angular-momentum conservation gates.

| Measured maximum | Observed | Frozen gate |
|---|---:|---:|
| Position difference | 0.0015983353934112736 m | 1 m |
| Velocity difference | 3.66733086796617e-10 m/s | 1e-6 m/s |
| Relative energy/angular-momentum error, both paths | 1.3437667093460488e-15 | 1e-12 |

These are empirical binary64 numerical differences, not bounds on real-world
trajectory accuracy. The independent stdlib bisection oracle does not use Tudat
states or conversions. A separate offline Newton solve cross-checks its retained
roots; analytic states, differences and conservation errors are recalculated.
The offline energy sum uses `fsum`, allowing <=2e-15 absolute difference in
reported relative errors for summation roundoff; the original 1e-12 physics gate
is unchanged and checked independently. No production tolerance is relaxed.

## Consequences and revisit conditions

Proceed next to R1.3 **profile design**, not exporter implementation. The evidence
checks one inclined eccentric Sun-centred/J2000-oriented ellipse over one period.
It does not validate the full R1.1 trajectory, SSB translation, arbitrary conics,
Lambert targeting, burns, navigation uncertainty, UTC conversion or mission safety.
Mass evolution/error remains not-modelled/null, not zero. No new SPICE request,
kernel load, search, historical replay or additional native propagation was made.
Strict M3/task 3.9, M6 and finite-burn gates remain open; automation stays paused.
A changed adapter/environment/problem requires reviewed new evidence rather than
rewriting this result. No public API, UI, dependencies or examples changed.

## Evidence and verification

- Immutable [raw result](experiments/0122-elliptic-coast.json), SHA256
  `2274cc0453f8da0c637f1172f25a92637a92f1650809cf49a97a31829cbae247`.
  Includes every raw state/root/difference, attempted/completed counts, call
  timings and identical before/after provenance. Prepared runner and adapter
  hashes match ADR 0121/0120 respectively.
- Python 3.12.14, TudatPy 1.0.0 build `py312h2196d89_3`, NumPy 1.26.4;
  actual source/import paths and native binary hashes are retained. GM is the
  unchanged hash-bound R1.1 SPICE value, not a fresh gravitational measurement.
- [Offline audit](experiments/0122-check-elliptic-coast.py) passes without importing
  native scientific modules: frozen inputs, 17 rounded epochs, call order/budget,
  roots, analytic states, differences/invariants and file/binary identities.
- Ruff, strict OpenSpec, local links, clean diff and immutable history/legacy
  checks pass. The existing 51 native-free preparation tests are rerun separately;
  they test guards, not additional real propagations.
- Full runtime regression suite **not rerun**: it contains native launches outside
  this bounded evidence stage. No production code changed. Full regressions remain
  mandatory at subsequent production/R1.4 implementation completion.
