# 0133 — Retain the three-epoch gravity screening

Date: 2026-11-01
Decision status: accepted evidence interpretation under ADR0131; no new model contract.
Implementation: R3.3 complete; one native screening and independent offline arithmetic audit pass.
Scope / milestone: M3 research diagnostic only; strict M3 remains open.
Base revision: `bf674850a2014c79b01b1e1a91f0c55502b06e8f`; initially clean. The exclusive output was the only untracked file during the run, as retained in both identities.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/omitted-gravity-screening/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; executes [ADR0131](0131-screen-omitted-gravity-at-fixed-epochs.md) using [verified ADR0132 preparation](0132-gravity-screening-preparation.md).

## Context and constraints

R2 established numerical agreement only for the retained ideal Sun-only coast.
R3 asks for local Earth/Moon/Mars differential gravity at original nodes0,60,120.
It neither changes the candidate nor supplies physical lunar escape/Mars capture
states. The original body-centre endpoints remain invalid for their exterior fields.

## Options considered

- Treat passing arithmetic as physical trajectory qualification: rejected; the
  diagnostic samples three epochs and omits other forces and boundary dynamics.
- Preserve the local result, its expected absent endpoint terms and limited
  inference: selected. No repeat or enlarged scientific run is needed.

## Decision and rationale

Retain the single successful screening and independent offline audit. Earth GM
was read once as398600435468295.9m^3/s^2; seven exact-epoch state requests returned
in the prescribed order. Attempted/completed counts are7/7 states and1/1 GM.
Zero spacecraft propagations, integrations or searches occurred. The pre-flush
elapsed sample is0.9007711252197623s under the shared30s budget; the separate
post-flush gate passes. It is not an exact post-flush timestamp.

Original input digests, candidate/epochs/GM and ordered13-kernel manifest match;
initial/final source/runtime/build identities are equal. The spacecraft/Sun states
are retained inputs, not newly observed data. Acceleration values below are
Sun-relative direct-minus-indirect point-mass terms in J2000 axes and SI.

| Node | Body | Differential norm (m/s^2) | Ratio to local solar norm |
|---|---|---:|---:|
| 0 | Earth | 0.0024520189712057628 | 0.40198894618601994 |
| 0 | Moon | inadmissible | absent |
| 0 | Mars | 5.147211905531383e-10 | 8.438443233916826e-08 |
| 60 | Earth | 1.6271998735478957e-07 | 4.4184230907733644e-05 |
| 60 | Moon | 2.023114563111808e-09 | 5.493471482051443e-07 |
| 60 | Mars | 2.4567535629659262e-08 | 6.670954716386826e-06 |
| 120 | Earth | 1.6914870845443256e-08 | 5.465092871951312e-06 |
| 120 | Moon | 2.0718108574272123e-10 | 6.693896070750685e-08 |
| 120 | Mars | inadmissible | absent |

At node60, the vector sum is(1.2510853409577062e-07,
6.9740585606507e-08,-1.1135918575567695e-09)m/s^2; its norm is
1.4323803500172831e-07m/s^2, solar ratio3.8894191894737206e-05.
The sum of individual norms is1.8931063754756064e-07m/s^2, ratio
5.140453277232561e-05. Cancellation is visible and not used to hide individual terms.

Earth's local departure term is about40.2% of the local solar acceleration.
This quantifies one omitted term at that point; it does not yield an integrated
miss distance or establish the maximum perturbation along the coast. The much
smaller middle sample cannot qualify the departure or arrival neighborhoods.
Moon0/Mars120 distances remain0.00033742285747521945m/0.002428833056893391m,
inside the declared exclusion spheres. Their forces and endpoint totals are
absent, never zeroed. This is expected domain classification, not a failed run.

## Evidence and verification

- [Raw screening](experiments/0133-gravity-screen.json): all operands, signed
  direct/indirect/differential vectors, Decimal values, classifications, metadata,
  attempted/returned calls, identities and timings retained.
- [Offline audit](experiments/0133-gravity-offline-audit.json): passed, all9
  classifications checked (7 admitted terms,2 absent), zero native imports/queries;
  evidence and auditor SHA256 recorded. The audit was repeated offline to retain
  its machine-readable result; the native screening was not repeated.
- The maximum admitted differential component error against the independent
  80-digit Decimal calculation is1.7569710643036476e-19m/s^2, within each frozen
  max(1e-15m/s^2,1e-11*Decimal-vector-norm) gate. Direct/indirect gates also pass.
- Strict OpenSpec,132 local links, finite JSON/digests and diff checks pass;
  all237 previously tracked protected code/test/example/environment/legacy/
  historical-evidence files remain byte-for-byte unchanged.
  No code changed; the4936-test/Ruff preparation evidence atbf67485 is retained
  without rerunning unchanged runtime tests.

## Consequences and revisit conditions

R3's local question is answered. R1/R2 ideal validity is unchanged; the result
cannot establish full-force trajectory accuracy, finite-radius escape/capture,
finite burns, continuous safety, UI qualification or M3/task3.9/M6 completion.
Other planets, harmonics, SRP/shadows, relativity, thrust and uncertainties remain
unassessed by this diagnostic. The Decimal audit verifies arithmetic/provenance,
not independent truth of the shared ephemerides.

The next bounded step is a design review of existing finite-radius departure
and arrival/outer-transfer contracts, identifying the smallest independently
checkable follow-up before any propagation. This is not permission to change
candidate/initial data, restart D17/D18, add optimization or run another study.
Freeze any new question, states, reference, tolerances and budget in OpenSpec/ADR
first. Autonomous design review remains within the authorized M3 scope; pause
if it exposes a scientific-contract decision or action requiring the user.
