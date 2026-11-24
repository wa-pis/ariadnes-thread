# 0248 — Check coupled shooting on an analytic finite-burn problem

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (F2 method and artificial-benchmark contract only)
Implementation: not started; no benchmark executed or scientific result obtained
Scope / milestone: private M3 preparation; no change to the production F0 solver
Base revision: `ea5ee6b3c24b976126425ff85a68c2449b138f73`, clean `dev` before design
Related OpenSpec: [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-coupled-shooting-on-an-analytic-finite-burn-benchmark), [design](../../openspec/changes/refine-physical-trajectory/design.md#f2-minimal-coupled-method-and-artificial-benchmark-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; elaborates [ADR0247](0247-formulate-coupled-moon-mars-problem.md)

## Context and constraints

Question: can a small, bounded coupled-shooting implementation recover a feasible
two-burn command from a perturbed seed, with an independent trajectory check?
Completion requires a fully specified test before implementation; this F2 stage
performs source review and documentation only. Research is bounded to the current
formulation, inspected local helpers and the four primary references below; no
search of real archives, scientific imports, numerical evaluation or propagation.

Existing TNW helpers and mass checks in [trajectory.py](../../src/space_nav/trajectory.py)
can support the candidate side. The historical D16 corrector in
[bounded_local_targeting.py](../../src/space_nav/bounded_local_targeting.py) binds a
different local steering problem; the native three-arc composition in
[research_propagation.py](../../src/space_nav/research_propagation.py) binds a full
mission environment. Neither is a generic coupled F0 solver to replay or refactor.
The existing closed-form/quadrature thrust-oracle cases in
[native-burn](../../tests/test_native_burn.py) and
[local-targeting](../../tests/test_local_targeting.py) tests use negligible gravity.
R1.2 verifies an unpowered coast. None alone verifies this recovery test.

## Options considered

- Another scalar phase method: retains the surrogate restriction and does not
  check coupled position/velocity continuity; do not repeat it.
- Start immediately with full-force F0 targeting: no qualified coupled method,
  known-safe seed or independent full-force error bounds; defer.
- A zero-gravity manufactured target: simple but omits an intended finite-burn
  interaction. A central-gravity finite-burn target would lose this simple exact
  oracle. Select a clearly labelled uniform-field manufactured problem instead.
- A private two-node multiple-shooting test using installed SciPy and existing
  pure guidance helpers: selected, without a generic backend or new dependency.

## Decision and rationale

### Fixed synthetic problem and exact witness

This is NOT a Moon/Mars force model, real orbit or ephemeris fallback. Use a fixed
synthetic body at the coordinate origin, `SYNTHETIC_INERTIAL` Cartesian axes,
SI units and elapsed seconds since the test start; do not label these as real
SSB/J2000 states or TDB epochs. No collision/safe-orbit claim is made.

| Parameter | Explicit fixture value |
| --- | --- |
| Initial position / velocity | (10000000,0,0) m / (0,1000,0) m/s |
| Initial / dry mass | 2000 / 500 kg |
| Maximum thrust / Isp / g0 | 1000 N / 450 s / 9.80665 m/s^2 |
| Uniform gravitational acceleration | (0,0.1,0) m/s^2, unchanged on all arcs |
| Start / final elapsed time | 0 / 10000 s |
| Known witness q*=(a_d,e_d,tau_d,a_a,e_a,tau_a) | (0,0,1000,0,0,1000), radians and seconds |
| Solver control seed | (0.02,-0.01,900,-0.02,0.01,1100), radians and seconds |

Both burns use dynamically rebuilt TNW about the synthetic fixed origin. At q*
the velocity remains on +Y, angular momentum points +Z and TNW is +Y/-X/+Z;
only this witness admits the fixed-axis closed form. Perturbed commands must
recompute the basis from each current state, never reuse the witness axes.
The future fixture check must show |g|*(tf-t0)>=0.5*|v0| and consumed witness
mass>=0.1*m0, so gravity and mass change are not negligible relative to the test.
The table supplies proposed artificial inputs, not calculated terminal numbers.

The independent stdlib oracle uses Decimal at 80 and 100 digits on exact decimal
fixture inputs. Let b=F/(g0*Isp), ve=g0*Isp, d the arc duration and mi its initial
mass. For a witness burn with mf=mi-b*d, compute simultaneously from BEFORE-arc
position/velocity:

```text
L = ln(mi/mf)
B = ve * (d - mf/b * L)
r_after = r_before + v_before*d + g*d*d/2 + (0,B,0)
v_after = v_before + g*d + (0,ve*L,0)
m_after = mf
```

Coast uses the same gravity, r_after=r_before+v_before*d+g*d*d/2,
v_after=v_before+g*d and unchanged mass. Compose burn/coast/burn sequentially,
including the mass entering burn two, to construct the target and witness nodes
at t1*=1000 and t2*=9000 s. Do not update velocity before using v_before for
position. The two precision paths must agree within 1e-9 m, 1e-12 m/s and
1e-15 kg before a target is admitted. This known witness is not the solver seed.

### Minimal transcription and pinned numerical method

Unknowns: six physical controls q and two six-component translation nodes z1/z2,
18 total. Each propagated arc start is still a seven-state: append its derived
mass m1=m0-b*tau_d or m2=m1. Derive node epochs t1=tau_d and t2=tf-tau_a.
Mass/time equalities are eliminated analytically, not independently adjustable.
Integrate three arcs and concatenate signed translation defects:
Phi_d(y0)-z1, Phi_c(z1,m1)-z2, Phi_a(z2,m2)-target. Scale each position component
by 1000 m and each velocity component by 0.01 m/s, retaining raw defects as well.
18 equations/unknowns do not prove rank, uniqueness or convergence.

Use `scipy.optimize.least_squares` with method='trf', jac='2-point',
tr_solver='exact', loss='linear', ftol=xtol=gtol=1e-12, diff_step=None,
max_nfev=20, verbose=0 and sequential workers=None. Use already pinned SciPy
1.17.1/NumPy 1.26.4; 1.17.0 API documentation is background, not a runtime change.
Set control bounds to [-0.1,0.1] rad for each angle and [500,1500] s for each
duration. Bound each node within its witness node +/-1000000 m per position
component and +/-500 m/s per velocity component. Use x_scale=(0.1,0.1,100,
0.1,0.1,100) for q, then (1000,1000,1000,1,1,1) for each node.
Initialize z1/z2 from witness nodes plus respectively
(1000,-1000,500,1,-1,0.5) and (-1000,1000,-500,-1,1,-0.5), in m and m/s.
The initial raw defects must fail at least one final qualification gate.

The candidate integrates the seven-state with solve_ivp/DOP853, rtol=1e-12,
atol=(1e-6,1e-6,1e-6,1e-10,1e-10,1e-10,1e-10), first_step=1 s and
max_step=100 s. Request each exact arc endpoint, require success/finite output
and endpoint epoch within 1e-6 s. Give each arc an explicit burn/coast mode:
its final RHS evaluation still uses that arc's mode, then switch between arcs.
Do not select thrust mode using an ambiguous global-time endpoint comparison.
Reject invalid/nonfinite epochs, mass, state or degenerate TNW and stop this
benchmark without penalties, backward stencils, seed substitution or restarts.

### Independent verification and dimensioned gates

First compare candidate witness propagation against the admitted analytic nodes.
Then solve from the perturbed seed. Repropagate the returned command from the
original initial state through all burns/coast without replacing states by nodes.
A separate stdlib auditor independently implements cross products, TNW, RHS and
classical fixed-step RK4; it imports neither SciPy nor candidate guidance/flow.
It performs witness and recovered-command forward replays, each with 4096 and
8192 equal steps PER ARC. Mass at every RK stage comes from its independently
computed linear ledger at that stage time; avoid accumulated mass-step rounding.
The candidate must separately compare its integrated mass with that ledger.

Check all four event epochs and seven-state values. Use Euclidean position and
velocity norms and absolute mass/time differences, not component cancellation:

| Check | Required bound |
| --- | --- |
| Candidate/RK4 witness versus Decimal analytic nodes | 0.001 m / 1e-6 m/s / 1e-9 kg; epochs 1e-6 s |
| Each recovered shooting translation defect | 0.001 m / 1e-6 m/s; separately verify mass/time continuity to 1e-9 kg / 1e-6 s |
| Unreset recovered final state versus target | 0.1 m / 1e-5 m/s, in both candidate and independent tighter RK4 path |
| Candidate versus tighter RK4, and the two RK4 meshes, at each event | 0.001 m / 1e-6 m/s / 1e-9 kg; epochs 1e-6 s |
| Domain/accounting | Canonical bounded controls, positive ordered spans, every stage m>=500 kg and matching derived terminal mass; no fixed terminal-mass equality |

The auditor must integrate the ACTUAL recovered command; nominal-witness parity
cannot validate a different steering command. Mesh/profile agreement is a
numerical diagnostic, not a certified global error enclosure. This artificial
qualification does not satisfy ADR0205's physical error-bound or M3 safety gates.
No requirement that recovered controls equal q* is imposed; uniqueness is unknown.

### Finite work and stop policy

| Budget | Fixed artificial-only ceiling |
| --- | --- |
| Overall elapsed time | One shared 300 s inclusive of startup, calculation, audit and durable report; producer finishes by parent start+210 s, separate auditor <=60 s and finishes by start+270 s, reserve the remaining 30 s for finalization. No clock resets. |
| Producer work | <=400 residual callback entries, INCLUDING numerical Jacobian calls; <=1206 synthetic arc attempts (3 per residual +3 witness +3 unreset validation), <=1000000 RHS attempts. Charge before work, including failed/rejected work. |
| Auditor work | Four three-arc replays x four RK stages, 4096/8192 steps/arc for witness/recovered: 294912 planned RHS, hard cap300000; <=12 synthetic arcs. |
| Data/output | <=64 KiB explicit fixture/config, <=2 MiB total new result/audit/log evidence, no all-RHS trace; finite values and source/runtime/settings/counter provenance. |
| Native/scientific access | Zero SPICE/kernel/real-archive reads or native propagations; no R5.60 or F0 mission run. |

max_nfev excludes numerical Jacobian calls; it cannot enforce the callback cap.
Keep explicit independent counters/deadline checks inside residuals/RHS and at
stage boundaries, with a bounded parent watchdog and finalization reserve; reuse
existing process utilities if suitable, without another generic framework.
These are synthetic work units, not an increase of production's 73 controls,
76 evaluations, 228 native calls or 300 s limits. A failed gate/budget yields
explicit failed/inconclusive artificial qualification, never a best-effort pass.
Do not retune seed, meshes, tolerances or budgets to obtain success automatically.

## Consequences and revisit conditions

F3 may implement this small private benchmark and its independent checker under
the user's resumed preparation/artificial-test authority. Verify focused cases,
both frozen required regression lanes, Ruff/review/strict OpenSpec and retain
new evidence before claiming qualification. Exercise endpoint-mode errors,
wrong gravity/mass/TNW, perturbed versus copied-node recovery, node resets,
nonfinite/domain failures, all budget boundaries and independent-audit tampering.
Artificial regression repetitions after relevant code changes are legitimate;
they do not revive any consumed retained scientific study or permit lucky retries.

No full-force F0 implementation or real-data run follows automatically. The
benchmark can expose transcription failures cheaply; success cannot establish
F0 reachability, a safe seed, force fidelity or the missing physical error bounds.
Review production method/qualification gaps explicitly before another contract.
No field/window/phase/hardware/kernel/tolerance changes; keep automation active
for authorized preparation, pausing whenever the next step requires the user.

## Evidence and verification

Inspected the local helpers/tests without imports or execution. Primary sources:
[NASA preliminary-survey workflow](https://trajbrowser.arc.nasa.gov/user_guide.php),
[AAS16-272 multiple shooting](https://ntrs.nasa.gov/api/citations/20160001644/downloads/20160001644.pdf),
[SciPy least_squares API](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.least_squares.html)
and [solve_ivp API](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.integrate.solve_ivp.html).
They support the selected transcription/API, not this fixture's unmeasured result.
The NASA examples are not the same finite-burn synthetic model.
Separate read-only reviews checked reuse limits, analytic witness conditions,
node elimination, endpoint mode, independent recovered-command checking and costs.
Verification passes: strict OpenSpec; 536 local links/four anchors across eight
changed Markdown files; one new requirement/five WHEN-THEN scenarios; source facts,
diff and CURRENT_STATE under60lines. All1081 tracked non-Markdown files, including
code/legacy/retained evidence, remain byte-for-byte unchanged. No runtime tests or
scientific calculations were performed in F2; numerical gates remain unverified.
