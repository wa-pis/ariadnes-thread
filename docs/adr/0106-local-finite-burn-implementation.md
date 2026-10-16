# 0106 — Implement the bounded local finite-burn diagnostic

Date: 2026-10-16
Decision status: accepted
Implementation: complete; focused/native and full regression verification pass.
Scope / milestone: M3 research D14.2, not the D14.3 reference study.
Base revision: `d084f13`; implementation and tests are part of this commit.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; implements [0105](0105-local-finite-burn-contract.md).

## Context and constraints

The accepted local contract needs native integration without changing the
existing interplanetary propagator, public interfaces, dependency pins or
historical evidence. No retained-reference propagation is part of this stage.

## Options considered

- Reuse the full-force three-arc environment: rejected; wrong model and budget
  for the explicitly isolated two-arc local problem.
- Tudat generic custom-state integration: tried in implementation tests; the
  pinned build reports inconsistent custom-dynamics input before integration.
  Do not update native dependencies or hide this failure with a conic fallback.
- Use the existing coupled translation/mass pattern: selected; qualified by
  analytic native tests and compatible with the pinned environment.

## Decision and rationale

Add only private [local_burn.py](../../src/space_nav/local_burn.py) and its
[tests](../../tests/test_local_burn.py). Verify the immutable 0104 file hash,
reconstruct the full free-phase reference through D13, compare all fields and
explicitly bind its first branch. Reject candidate/reference/phase/state/mass
changes before native work. Convert the retained launch-window UTC values with
SPICE and check actual ignition, not just the virtual epoch.

Construct the oriented circular ignition state, vector-impulse unit direction,
centered duration and outgoing target analytically. Check conic invariants and
independently integrate the area law with 4096-panel Simpson quadrature to
verify time of flight within 0.001 s. Tests additionally use 128-point Gaussian
quadrature, eccentricity-vector reconstruction, Rodrigues rotation and 50-digit
Decimal mass accounting rather than comparing an implementation to itself.

Use Tudat's Moon-central translational and mass propagators. The native body
container has SSB/J2000 labels and an explicitly fixed zero-position point Moon;
the integrated state is Moon-relative J2000. This is an isolated two-body model,
not a claim about the Moon's actual SSB trajectory or fabricated replacement
ephemerides. Only the date conversion reads SPICE. Native relative integration
seconds start at ignition; the command records their absolute TDB epoch mapping.
Fresh bodies per arc initialize mass from the exact handoff, not the original
spacecraft mass. Point gravity is native; custom thrust uses the propagated mass
and a fixed J2000 direction, with constant burn mass flow and zero coast flow.

Both arc types use the same explicitly pinned local profiles:

| Setting | Nominal | Tighter |
|---|---:|---:|
| Coefficients | RKF 7/8 | RKDP 8/7 |
| Relative tolerance | 1e-11 | 1e-13 |
| Position absolute tolerance, m | 1e-3 | 1e-5 |
| Velocity absolute tolerance, m/s | 1e-6 | 1e-8 |
| Mass absolute tolerance, kg | 1e-9 | 1e-11 |
| Initial step, s | 1 | 0.25 |
| Minimum step, s | 1e-6 | 1e-8 |
| Maximum step, s | 10 | 2 |

Reject steps below the minimum and nonfinite step requests. Exact time
termination is enabled. Guards run on thrust-callback derivative stages and saved
states, including coast stages; this still does not certify continuous safety.
Validate successful native completion, exact history endpoints/initial state,
finite states, lunar radius, dry mass, unchanged coast mass and analytic burn
mass within 1e-6 kg before accepting an arc.

Reuse the existing cooperative deadline through a private four-arc ordered
budget; no retry after an incomplete arc. The 300-second clock starts before
reference/kernel preparation and is checked during native callbacks and history
reading. This cannot preempt a blocked native call; late output is rejected.
The fixed command receives nominal then tighter burn/coast pairs even on a
completed miss. Failure skips later work. Return finite diagnostic evidence with
separate closure/agreement/outcome, raw residuals, command, integration profiles,
resource/source hashes, runtime versions, counts and elapsed time. The caller
must retain a new artifact; this module never overwrites evidence files.

## Consequences and revisit conditions

No exported API, CLI, UI, dependency, production force model or optimizer changes.
The point-Moon test is intentionally not high-fidelity mission validation.
Do not interpret passing synthetic tests as a successful finite burn on the
retained branch. D14.3 remains unchecked and needs its own immutable report/ADR;
no live reference-case study ran here. Strict M3/task 3.9 remain open, and
automation remains paused. A later steering solve or perturbation/outer matching
requires a separately reconciled contract, not retries of this command.

## Evidence and verification

182 focused tests pass in 1.90 s, including 116 new D14 tests plus D13 and
research-propagation regression tests. Native checks cover a full circular orbit
plus 100 s (position <=0.001 m and velocity <=1e-6 m/s against the analytic
solution) and a near-zero-gravity variable-mass burn against the rocket equation
followed by exact-mass coast, for both profiles. These are synthetic integrator
qualifications, not the retained reference study. Injected tests cover all four
failure positions, skipped results, cutoff mass, invalid history, actual callback
deadline/impact, profile and closure/agreement thresholds, and nonfinite residuals.
Full regression: 4,112 tests pass in 598.94 s. Ruff, strict OpenSpec, local links,
diff checks and unchanged reference/legacy SHA256 pass. D14.2 is complete;
D14.3 remains pending. The full suite ran on the final runtime/test files;
subsequent edits only record verification in documentation.
