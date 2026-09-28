# 0086 — One full correction step increases the target miss

Date: 2026-09-28. Measured revision: `6061cd8`, clean before the experiment.
Status: completed bounded study, negative targeting outcome; not a feasible
mission, numerical accuracy certificate or continuous-safety acceptance.
[Retained JSON](experiments/0086-targeting-study.json) contains exact source,
reference, runtime/kernel/resource identity and all completed run evidence.

## Procedure

49 focused tests passed in 0.31 s before one live invocation:

```sh
conda run --no-capture-output -n space-nav python -m space_nav.targeting_experiment examples/m3_feasible_mission.toml docs/adr/experiments/0079-research-reference.json docs/adr/experiments/0086-targeting-study.json
```

No code, seed, force model, integrator setting or tolerance changed. Each run
used a fresh resource-matched environment, the fixed departure/arrival epochs,
and the existing sampled guards. Eight nominal runs completed: baseline, six
ordered forward probes and one trial. All 24 attempted native arcs completed;
eight control attempts/evaluations, zero retries, no recorded rejection.
Elapsed shared-budget time was 19.105812750 s, below 300 s. The cooperative
deadline cannot preempt a native call. Tudat emitted its existing deprecation
warning for `mass_rate.custom`; no calculation failure was reported.

## Observations

All four baseline boundaries reproduce the retained nominal reference exactly
in position, velocity and mass; epoch and seed checks also passed.

| Quantity | Baseline | One corrected trial |
|---|---:|---:|
| Position miss (m) | 197851062193.60904 | 245008762296.3577 |
| Velocity miss (m/s) | 31160.14668810916 | 40593.268629890255 |
| Scaled residual score | 197875598.18874988 | 245042387.63237208 |
| Endpoint closure | false | false |

Trial/baseline score ratio is 1.238365871666: the score increased by about
23.84%, so the prescribed improvement test failed. Position and velocity miss
both increased; neither endpoint gate (1000 m, 0.01 m/s) came close to passing.

The empirical scaled Jacobian has numerical rank six at rcond=1e-12. Its largest
and smallest singular values are 356346658.4833949 and 45225.41167939399 (ratio
about 7879.35). This is a solve diagnostic, not evidence that the derivatives
are accurate or that a full nonlinear update will improve the trajectory.

The capped update, in departure then arrival (azimuth rad, elevation rad,
duration s) order, was:

```text
(0.024366137324887543, -0.13508417238295242, -600.0,
 0.12789125794475317,   0.05698073441300194, -50.607786569360435)
```

The departure duration change reaches the specified trust-scale cap. Full signed
probe residual changes and Jacobian are retained in JSON. They are empirical
finite differences; the earlier D6 coast study is not a derivative noise bound.

Outcome is `not-improving`. In accordance with the specification, no tighter
trial ran: numerical agreement and tighter comparison are null, not false or
silently assumed. Exit zero means the bounded diagnostic completed, not that
targeting succeeded. Continuous safety remains explicitly unverified.

## Decision and limits

Do not select this trial, call the seed corrected, increase the budget, or run
another iteration automatically. The experiment establishes that this one
alpha=1 update fails the improvement rule, not that the mission is impossible
or that all six-control targeting must fail. Local linearization error is a
possible explanation, not a diagnosed cause; numerical derivative uncertainty
also remains unresolved. Changing SPICE or loosening gates is not justified.

A possible next bounded question is whether smaller fractions of this same
direction improve the residual, using an explicitly agreed damping study.
Specify its inputs, comparison control, fractions, stop rules and budget before
any new native runs. No such study was run or authorized by this record.
Strict M3/task 3.9, full target closure and safety remain open.

## Verification

Independent retained-data checks confirm finite JSON, exact source hashes,
run ordering, counters, signed residuals/probe changes, Euclidean miss norms,
score ratio and absence of a tighter run. No second mission invocation was used.
Full suite: 3,704 passed in 596.59 s. Ruff, strict OpenSpec, whitespace and
unchanged legacy SHA-256 pass. Runtime code is unchanged in this evidence
commit. D7 is complete as a bounded experiment with a negative targeting result,
not a successful correction or strict-M3 acceptance.
