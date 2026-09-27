# 0082 — Coast disagreement persists with an identical initial state

Date: 2026-09-27. Base revision: `76b8f87` plus the new D5 adapter and tests.
Status: diagnostic evidence, not accuracy, target closure or safety acceptance.
The [machine-readable report](experiments/0082-identical-start-coast.json)
records exact Python source hashes, the pinned Decision 0079 artifact digest,
normalized input, runtime/kernel/model resources, settings and initial state.

## Procedure

Run once after 157 focused checks passed, with no retry, changed force model,
new tolerance or command optimization:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.coast_diagnostic examples/m3_feasible_mission.toml docs/decisions/experiments/0079-research-reference.json docs/decisions/experiments/0082-identical-start-coast.json
```

Both profiles start with the retained nominal departure-cutoff state and mass,
and end at the same arrival-ignition epoch. Each uses a fresh full-force native
environment, existing coupled-state/integrator/force/completion adapters and no
thrust. Sampled checks reuse the existing physical classifier and preserve D4
dry-mass equality, event precedence, exact native initial history and constant
coast mass requirements. The driver rejects changed reference/scenario/candidate/
runtime/kernel/environment/settings identities and stops after the first failure.
Output creation is exclusive: prior evidence cannot be overwritten.

## Observations

- Two native arcs attempted and completed, no retry; 7.619343375 s of the shared
  300-second cooperative budget. This deadline does not preempt native calls.
- Nominal/tighter checked-state counts: 631 / 3107, including repeat evaluations.
- Nominal restart drift is exactly zero in stored position, velocity and mass.
- Same-input profile difference: 115.669948207 m, 0.000020400481302 m/s, zero kg.
  Position fails the unchanged 10 m gate; velocity and mass pass their gates.
- New tighter minus old tighter: 1866.692492747 m, 0.000333854360420 m/s and
  4.547473509e-13 kg. This includes changed-start and restart/numerical effects;
  it is not an exact physical sensitivity estimate.
- Earlier full-profile arrival-ignition separation: 1751.032852526 m.
  The contributions are signed vectors, not additive distances. Stored vectors
  satisfy the decomposition in the design exactly in the comparison arithmetic.
- Exit code zero means this diagnostic completed, not numerical agreement.
  Continuous safety is false/unverified; no mission target was corrected.

## Interpretation and next decision

The identical-input experiment rules out initial-state differences as the sole
explanation of the original profile disagreement: the isolated coast still
differs by 115.67 m. The nominal zero-drift control supports comparability of the
restart on this run. The larger change under the tighter profile when replacing
its initial state also shows that the small departure-cutoff difference matters.
Do not subtract 115.67 m from 1751.03 m to estimate a physical error budget.

Neither profile is ground truth. These observations do not identify which
integrator is more accurate, establish a global error bound, or explain the
full 198-million-km target miss. The prescribed seed's geometry limitation from
Decision 0080 remains separate. No production settings are changed here.

Next proposed step is a separately bounded convergence study from this same
cutoff, with diagnostic-only integration settings agreed before native runs.
No additional profiles, native experiments, optimizer or retargeting have run.
Strict M3 and task 3.9 remain open; the OpenSpec change must not be archived.

## Verification

157 focused checks passed in 2.32 s, including a real native nearly force-free
coast oracle for both profiles (position 1e-6 m, velocity 1e-9 m/s, exact constant
mass), reference/resource mismatch, failures without endpoints, dry mass,
collision precedence, deadline, two-launch accounting and output preservation.
The oracle is a toy, not mission accuracy evidence. Source/reference hashes and
signed-vector decomposition were checked independently from retained JSON;
no live repeat was used. Full suite: 3,631 passed in 595.03 s. Ruff, strict
OpenSpec, whitespace and unchanged legacy SHA-256 pass. D5 is complete as a
diagnostic slice; position agreement and strict M3 remain unqualified.
