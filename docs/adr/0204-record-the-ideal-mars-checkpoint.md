# 0204 — Record the ideal Mars checkpoint and model difference

- Date: 2026-11-15 (Europe/Samara)
- Decision status: accepted evidence under [ADR0202](0202-design-coepoch-mars-receiving-state.md).
- Implementation: R5.57 complete; the once-only attempt is consumed.
- Verification: one isolated retained-data run and independent readback arithmetic passed.
- Scope: one ideal checkpoint for `d0001-t0035`; no R4 physical join test.
- Measured revision: `2386f6e38f70530579f671e4d4687798a3793917`, clean synchronized `dev`.
- Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-design-an-independent-mars-receiving-state), [design result](../../openspec/changes/refine-physical-trajectory/design.md#r557-verify-the-ideal-coepoch-on-retained-data-2026-11-15), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
- Supersedes: none. [ADR0135](0135-fixed-orbit-boundary-contract.md) remains the physical interface contract.

## Context and constraints

[ADR0201](0201-authenticate-lunar-exit-record-receiving-gap.md)
authenticated the terminal R5.51 model B packet but found no
compatible incoming packet. [ADR0203](0203-prepare-coepoch-mars-worksheet.md)
qualified the frozen worksheet on artificial inputs. The user
authorized one run with the retained R5.51 and R1/R2 sources and
zero SPICE or numerical integration.

The epoch is **979014965.9635216 TDB s since J2000**
(binary64 `0x1.d2d4a9afb54adp+29`). It is the saved +16,000 s
coast endpoint from the R5.51 restart, distinct from the radial
marker and the actual burn interfaces.

## Options considered

- Reuse a neighboring ideal sample or interpolate between two: those
  records do not establish the Sun-only state at the exact epoch.
- Run the qualified two-endpoint analytic worksheet once with the
  coepoch Sun translation already in the archive: selected.
- Reverse-propagate a physical receiver from Mars: deferred under
  R5.58; no compatible command and full-force contract is ready.

## Decision and rationale

Record `ideal-reference-coepoch-computed`. The Sun-only forward
evaluation starts from the R2 departure seed; the reverse evaluation
starts from R1 node 120's pre-impulse spacecraft state. Both use the
same frozen R2 analytic equations and the matching archived Sun
state for all six SSB components. This compares two endpoint
constructions of the same ideal trajectory.

| Check | Retained result |
| --- | --- |
| Backward minus forward, Sun-relative and SSB/J2000 | 0.000130594198369 m and 2.22826201934e-11 m/s in both frames; passes 1 m and 1e-6 m/s. |
| Kepler root gates | 49 updates per path; worst bracket width 1.1157741397482823e-14 rad and worst root residual 1.5543122344752192e-15 rad; within 64 updates and 2e-14 rad. |
| Invariants | Maximum relative energy and angular momentum errors 9.62957399881166e-16 and 3.691254928507927e-16, both within 1e-12. |
| Ideal (backward path) minus archived model B, position components | (-4791890.275558, -32079300.904617, 40032943.059143) m; norm 51523589.63541422 m. |
| Ideal (backward path) minus archived model B, velocity components | (-468.456668480, -1747.149450375, 2122.765435679) m/s; norm 2788.927382902 m/s. |

The last two rows describe different trajectories at a common epoch
in SSB/J2000. Their magnitudes are not acceptance residuals or a
measurement of the effect of any one force. The ideal state has
no mass. The physical status remains `physical-join-not-established`,
with all four physical residuals `null`.

## Evidence and verification

- Preflight matched five prepared and five reused source hashes,
  seven compact inputs, both R5.51 phase chains, the one selected
  study member, the R5.54 originals and the R1/R2 lineage. The
  frozen worksheet verified the raw and gzip digests, 42,862 lines
  (16,777,139 raw / 5,176,745 gzip bytes), 1,903,681 compact input
  bytes, 20,353 archive metadata bytes and the two pinned rows.
  The Sun request/response and the archived ordered kernel
  inventory passed without opening a kernel.
- The single invocation exited 0 in **0.256854 s** including
  startup and finalization, within the 15 s limit. The parent receipt
  records 0.217305 s before its write. Peak child RSS
  was 73,809,920 bytes. No late marker was present.
  Two analytic paths used 98 root updates total. Scientific/native
  calls, kernel access, force callbacks, fitting and numerical
  propagations were all zero.
- Independent saved-value readback verified the attempt/report/receipt
  hash chain, both six-component Sun translations, the three signed
  difference vectors and norms, elapsed epoch offsets and the
  reported numerical gates. It did not solve the orbit again.
- The [verification manifest](experiments/0204-verification.json)
  binds the measured revision, authorization/preparation digests,
  and the original attempt, report and receipt (6,436
  bytes). The originals remain at `/Users/agrudin/dev/my/ariadna-evidence/R5.57` outside Git.
- Strict OpenSpec, changed local links, evidence and diff checks
  passed. Runtime code is unchanged; the 6,284 passed / 494 skipped
  guarded regression and Ruff are retained from ADR0203 and were
  not rerun.

## Consequences and revisit conditions

The receiving-data gap now has an exact-epoch **ideal** diagnostic.
A direct stitch of the two stored states would have a discontinuity.
Physical continuity, Mars arrival and capture, reserve, safety and
strict M3 completion remain unverified. R5.58 requires its own
full-model, command, mass and numerical contract.
No retry or further run is authorized by this evidence.
