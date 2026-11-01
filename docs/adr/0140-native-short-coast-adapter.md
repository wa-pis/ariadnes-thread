# 0140 — Prepare a native restricted-force RK4 adapter

Date: 2026-11-01
Decision status: accepted preparation unit under ADR0137/0139; reference contract unchanged.
Implementation: R5.2c native adapter and61 tests implemented;115 focused and5051 full tests, Ruff and strict OpenSpec pass.
Scope / milestone: private M3 component preparation, not an R5 reference experiment.
Base revision: `9b18ec0683ac323137b241f9b7a2e7d1220f0223`, initially clean; new adapter/tests untracked during checks.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [API readiness](0139-pinned-native-api-readiness.md), [oracle](0138-independent-short-coast-oracle.md) and [frozen contract](0137-short-coast-earth-gravity-contract.md).

## Context and constraints

Complete the native half before the shared runner and offline audit. Preserve
all frozen reference inputs, profiles and gates. The adapter must not reuse the
independent oracle's dynamics or pretend the full M3 production model is reduced.
This preparation unit uses analytic fixtures instead of the R5 initial state.
Its four real synthetic arcs per test-file invocation each use a15s cooperative
component deadline; these are separate tests, not the future reference budget.
No new dependency, production code, candidate, control or environment change.

## Options considered

- Reuse the Sun-only/full-M3 propagator with a substituted label: reject.
- Depend on the previously failed standalone derivative callback: reject.
- Explicit private construction and normal simulator propagation, with actual
  per-source and total acceleration telemetry: selected and component-tested.

## Decision and rationale

[Native adapter](experiments/0140-short-coast-native.py) imports only stdlib at
module load. Low-level construction supports analytic fixture ephemeris settings;
only the R5-facing wrapper creates the fixed A/B environments and300s profiles.
Every wrapper call constructs fresh SSB/J2000 direct-SPICE bodies, central fields
with frozen GMs and a2000kg spacecraft with no gravity or mass dynamics. It checks
geometric aberration flags and assigns only the selected point-mass accelerations.
The explicit native constructor is separate from all oracle force/propagation code.

Actual maps are checked by source set and count, native field GMs at1e-15 relative
and frame; no invented force-type readback. Dependent-variable construction asks
for each selected point force and the total, retaining their canonical output
order independently of opaque map order. Total versus source sum must agree
within1e-12m/s^2 Euclidean norm. This telemetry consistency check is additional
to the unchanged ADR0137 state/sensitivity gates; it cannot prove absence of
unrepresented physics or physical adequacy. A later saved-node audit still must
compare the native operands/forces with independently recomputed direct fields.

The normal native propagation interface uses explicit Cowell, classical RK4 h1s
or h0.5s, exact final-time termination and no minor-step termination. The adapter
checks every saved step/count, exact initial state and requested node membership,
completion within1e-6s, finite state/force arrays and retained-state guards. No
native history interpolation or guard on every internal RK stage is claimed.

One shared context caps attempted native calls at4 before simulator creation;
returned and successfully validated arcs are counted separately. Raw state/force
histories are retained before after-call deadline and validation checks. A dedicated
exception carries them on failure. Guard ephemeris reads have separate attempted /
returned counters and retain the last returned raw state before the deadline check;
they are not counted as the independent oracle's30021 reads. The future runner
must normalize finite raw native arrays when preserving exclusive partial JSON.
It still owns shared60s timing, engine ordering, four-oracle limits, resource /
build/source identity, complete input binding, comparison and evidence finalization.

## Evidence and verification

[Tests](../../tests/test_r5_short_coast_native.py) include:

- One1s no-force line with exactly representable weighted increments; final state
  and zero acceleration compare bitwise. The first fixture used velocities2/3/4,
  where native RK4 returned1.9999999999999998 instead of2. The bitwise expectation
  was inappropriate for those increments. Changing only the synthetic velocities
  to3/6/12 retains the exact gate; no reference data or numerical gate changed.
- Two300s circular fixtures at h1/h0.5, mu1e12m^3/s^2 and radius1e7m, compare
  seven nodes to closed form within1e-6m/1e-8m/s and actual total/single-source
  acceleration within1e-12m/s^2. These are not mission trajectories.
- One1s three-source axis fixture at h0.5 compares native total and individual
  accelerations with independent Decimal80 arithmetic within1e-14m/s^2 per
  component. The off-origin Sun term distinguishes direct SSB forcing from an
  erroneous indirect-origin subtraction.
- At epoch0, both constructed A/B direct ephemerides for Sun/Moon/Earth match
  direct Tudat/SPICE NONE states within0.001m/1e-6m/s, with exact native GMs.
  Twelve actual body-state reads per invocation of that test, no reference state.
- Lazy imports; no shared force implementation; malformed/finite/boolean/frame /
  source/count/GM/profile/epoch/sample/initial/force-total rejection; all three
  exclusion spheres including omitted Earth's guard; guard/body-state retention,
  missing/failed native output, cap and after-call deadline/error paths. Injected
  fake outputs are not counted as native propagated arcs.

First focused iteration:1 failed/43 passed in0.81s due only to the exact-line
fixture expectation above. Initial Ruff found24 style errors; formatting the new
files fixed those without changing physics. Intermediate98 checks passed in1.69s.
Final native+oracle focused check:115 passed in2.02s; new native tests61, prior
oracle tests54. New native test file ran three times during focused preparation,
four synthetic native arcs each time; the later full run adds four. Other full-suite
native calls are not instrumented and must not be inferred from this count.

Full regression passed5051 tests in650.86s, exit0. Git status was byte-identical
before/after; all252 previously tracked protected code/test/example/environment/
legacy/experiment files remain byte-identical to the base. See the
[actual full log](experiments/0140-full-pytest.txt) and
[check summary](experiments/0140-native-preparation-checks.json) for digests and
actual component/native scope. Strict OpenSpec and Ruff pass. Final documentation
updates do not alter verified runtime code/tests; full pytest is not repeated for
prose-only changes. No R5 reference has been run.

Prepared SHA256:

- `docs/adr/experiments/0140-short-coast-native.py`: `8bc888d6e1c638251d8379d6d4c896393b5cd76fb71e85c65c7faf9aab9294e2`.

- `tests/test_r5_short_coast_native.py`: `47f91ce5d5ccb9133f6c6df5933b382b1a05fe436ee5995c9cb4523b48d8ab9b`.

## Consequences and revisit conditions

This unit does not complete R5.2. Next build the shared runner with extended
native/SciPy/NumPy/build/resource identity and separate offline audit, then verify
all preparation before the one R5.3 reference. The wrapper has no execution CLI
and does not load/download kernels. Keep same-model numerical agreement distinct
from restricted model sensitivity, full mission accuracy and continuous safety.
M3/task3.9 and finite-burn/escape/capture/mission gates remain open; M4–M6 deferred.
