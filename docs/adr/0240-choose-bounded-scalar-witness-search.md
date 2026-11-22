# 0240 — Choose bounded scalar search for an analytical witness

Date: 2026-11-22 (Europe/Samara)
Decision status: accepted
Implementation: method design complete; implementation and qualification not started
Verification: documentation only; no new numerical result
Scope / milestone: local analytical command admissibility within the active M3 change
Base revision: `32887ecd8a37c69a1149fbb490c3a026c55c27c4`, clean `dev` before this stage
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-use-bounded-scalar-search-only-to-propose-an-analytical-witness), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md)
Supersedes / Superseded by: none; completes the method choice required by [ADR0239](0239-stop-diagnostics-at-a-feasibility-decision.md), preserving its stop policy

## Context and constraints

The next useful result is an independently checked admissible point, rather than
another diagnosis of interval width. The retained grid fails the dry floor and
the continuous question remains unresolved; see [ADR0217](0217-verify-the-saved-mars-phase-grid.md)
and [ADR0221](0221-record-retained-inter-node-result.md). We have no new evidence
that the approximately 40.085 m/s shortfall can be recovered between grid nodes.

Keep candidate `d0001-t0035`, the closed Mars true-anomaly domain [150°, 152°],
fixed positive lunar branch, both Mars signs, original epochs and every remaining
[ADR0218](0218-design-inter-node-mars-phase-check.md) input and point gate.
This decision concerns the impulsive surrogate, not full-force trajectory closure.

## Options considered

- Root bisection or `brentq`: requires a continuous scalar residual with an
  established sign-changing bracket; no admitted bracket is available. See the
  [SciPy root-solver contract](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.brentq.html).
- More grid/interval subdivision: repeats the consumed route or needs another
  proof change; not selected. A new derivative/interval proof may support refusal,
  but adds machinery unnecessary for checking an individual candidate.
- Bounded Brent scalar minimization using existing SciPy: selected as the smallest
  derivative-free witness proposer. It avoids the unresolved interval bounds and
  checks arbitrary off-grid points directly, without promising a global minimum.

## Decision and rationale

### One scalar, two fixed signs

For each Mars sign separately minimize
`J_sign(theta_deg) = norm(fixed_lunar_impulse) + norm(mars_impulse_sign(theta_deg))`
in m/s. Do not optimize the switching minimum of the two signs or introduce new
controls. Use the pinned Conda SciPy 1.17.1 / NumPy 1.26.4, with the explicit call:

```python
minimize_scalar(objective, method="bounded", bounds=(150.0, 152.0),
                options={"xatol": 1e-5, "maxiter": 62, "disp": 0})
```

This is the bounded minimization variant of Brent, not `brentq` or unbounded
`method="brent"`; see [SciPy's method contract](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.minimize_scalar.html)
and [option definitions](https://docs.scipy.org/doc/scipy-1.17.0/reference/optimize.minimize_scalar-bounded.html).
`xatol` is a search stopping setting in degrees, not a physical tolerance or a
certified phase-error bound. No unimodality or continuity across guards is assumed.

First authenticate and compare all three saved anchors 150°, 151°, 152°,
including both signed inventories and original pair refusals, before any search.
These frozen anchors are parity gates only: the preserved comparator requires no
eligible anchor. Changing a saved refusal into a witness is an invalid anchor
mismatch. Only after all comparisons pass, search positive followed by negative,
at most once per sign. At every proposed phase inspect both
signed point checks before returning the active sign's cost. Stop at the first
independently passing point of either sign; no rank gap, optimum or optimizer
success is required.
Retain finite analytical costs for ordinary pair rejections (mass, event order or
historical exclusion); those refusals still prevent admission. In particular,
removing mass-rejected costs would prevent searching toward the dry floor.
The scalar objective never admits a pair.

If the active sign is definitively guard-rejected or agreed degenerate, record that disposition
and terminate only that scalar search as `objective-unavailable`; continue the
other sign if still applicable. Do not supply infinity, NaN, a penalty, fabricated
commands, a replacement bracket or a restart. A rejected other sign does not abort
the active search. Both sign slots must still be present with explicit dispositions.
Unresolved classification, missing inventory, nonfinite arithmetic, anchor mismatch
or independent disagreement terminates the attempt invalid/inconclusive.

### Preserve exact points and literal commands

The immutable [0219 point wrapper](experiments/0219-phase-points.py) accepts only
the old denominator-at-most-64 grid and strips `command_words` from its report.
Use a new minimal versioned adapter; do not edit or call that wrapper unchanged.
Preserve each proposed binary64 phase as its canonical hex word and exact integer
ratio in degrees, with value-preserving conversion of the solver's scalar.
Reject booleans, nonfinite values and out-of-domain phases. Never snap to the grid.
Keep the existing binary64 angle operation order `math.tau * theta_deg / 360`;
the independent pinned 96-digit orbit/conic path reconstructs the exact degree
ratio with its own trigonometry. Record the angle word and both frame states.

Every witness must pass all ADR0218/0212 relative and SSB/J2000 state gates
(0.001 m, 1e-6 m/s), signed-asymptote/impulse and incoming-leg guard gates,
duration agreement (1e-6 s), mass agreement (1e-8 kg), canonical pre-impulse TNW,
arrival reversal, event ordering, historical exclusions, unrounded ideal budget
and both exact commanded/effective 500 kg mass ledgers. Preserve the original six
binary64 command words and their phase/sign/endpoint binding. The separate audit
must check those literal commands independently; newly rounded oracle commands
must not replace them. An unresolved second root prevents point admission.

### Count the whole attempt and verify the recorded points

Use the same four scientific inputs and exact SHA-256 values in the `PINS` map of
[0220-phase-invocation.py](experiments/0220-phase-invocation.py) at the base revision:
ADR0215 attempt/report/receipt and ADR0217 saved-grid audit. Preserve their chain
and operand identity. Reuse the frozen core, oracle, reader, orbit, screen and
anchor contracts/pins there; no 360-point replay or old producer/auditor dispatch.
Before any saved execution, freeze the new adapter, proposer, independent auditor,
wrapper/solver source and installed dependency version/build identities after
qualification; absent or changed identities leave execution unavailable.

| Charged work | Ceiling per arithmetic path |
| --- | --- |
| Saved anchors | 3 phases |
| Objective callback attempts | 62 per sign, 124 total |
| Final checks | 2 phases, only already-recorded `result.x` from completed searches |
| All direct phases | 129; at most 258 Mars signed-root slots and 258 pair slots |
| Interval cells / signed bounds | 0 / 0; no subdivision tree |

Precharge every attempt, including duplicates, rejected points and final checks;
cache use cannot conceal charged work. Each direct phase includes the inherited
fixed-lunar validation and both Mars slots. The producer's binary64 and independent
paths and the separate auditor each have explicit counters within these caps.
The audit checks only recorded phases/commands, never reruns the optimizer, and
has no implicit new probes. Producer durable readback is structural/hash-only:
reusing the old self-audit would hide repeated phase work.

Keep 30 s import/startup-inclusive through durable producer finalization/readback,
a separate 30 s audit, 4 MiB pinned input per reader and 4 MiB combined new evidence.
Charge all four archives, private/scientific source, bootstrap/config/profile
metadata and selected wrapper/solver-source authentication bytes to the 4 MiB
input ceiling, including rereads. Installed interpreter and NumPy/SciPy import
artifacts are runtime, not additional scientific inputs: permit only an exact
path/build/digest allowlist with its total loaded/read volume measured and frozen
during qualification. No general package/directory scan or other runtime exception
is allowed; all runtime loading/authentication remains inside the same 30 s.
This explicit runtime permission changes the new process profile, not archive,
private-source or evidence limits. Until its full allowlist/volume is qualified,
execution is unavailable. Qualification must demonstrate all ceilings rather than
omit load/finalization costs; failure cannot raise a cap. Use a fresh exclusive
output identity for the first complete/partial attempt.

The new producer needs an explicit pinned SciPy/NumPy runtime profile: the old
stdlib-only import guard cannot admit this method. Do not weaken that historical
guard or claim zero native-library loads. The independent audit remains stdlib-only;
SPICE/kernel access, force evaluations, integration, old study dispatch and R5.60
stay forbidden. No new dependency, environment change or warm-up outside the clock.

### Terminal conclusions and preparation gate

Only `verified-analytical-witness` or `inconclusive/invalid` is available here.
No witness, optimizer success/failure, local stationarity or an above-budget minimum
cannot establish continuous refusal. This method emits no refusal certificate.
After either terminal result stop; no automatic diagnostics, restart or widened search.
A witness remains existence only: no executable command selection, adopted changed
Mars target, physical readiness, reserve, safety or M3 completion. Original R5.60
stays closed under ADR0205/0207 and automation remains PAUSED.

A separate implementation instruction must first qualify fabricated full-volume
inputs: arbitrary-ratio off-grid witnesses; endpoint witnesses in the isolated
point verifier only, outside the frozen anchor-comparison flow; anchor-refusal
drift; all-mass-failing and
multimodal missed-witness cases that stay inconclusive; guard/search abort versus
unresolved failure; exact-zero/equality/rounding and literal-word tampering;
anchor/sign/source drift; all 129 phases with duplicate/precharge/final-slot caps;
input/output/deadline/finalization failures; and an independent audit that never
calls the optimizer. Verify actual command shapes/profile identities, focused tests,
both frozen required regression lanes, Ruff and strict OpenSpec. Artificial success
is not a retained result. A saved execution needs another explicit instruction.

## Consequences and revisit conditions

This chooses a small direct route to existence and deliberately gives up a local
refusal proof. The method can miss an admissible point or stop at a guard; an
inconclusive outcome is useful only with that limitation stated. No probability
of success or recovery of the shortfall is asserted. A required negative proof or
failed qualification needs an explicit reviewed decision, not another default chain.

## Evidence and verification

Source/document inspection only: no scientific imports, numerical evaluations,
experiments, SPICE or integration. Checked the pinned API/options against SciPy
1.17 documentation and the installed solver source without importing it. The
phase-grid restriction, stripped commands and old runtime/readback behavior were
read from the cited source. Independent reviews pass after clarifying frozen-anchor
precedence and the runtime/source byte partition. All 508 local links/anchors,
document facts, whitespace, documentation-only scope and strict OpenSpec pass;
CURRENT_STATE remains under 60 lines. Runtime sources/tests/dependencies and
historical evidence are unchanged. No local pytest/Ruff or scientific qualification
was rerun for this documentation-only stage.
