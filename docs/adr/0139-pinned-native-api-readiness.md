# 0139 — Verify pinned native construction before force tests

Date: 2026-11-01
Decision status: accepted preparation guidance under ADR0137; scientific contract unchanged.
Implementation: R5.2b API readiness inspected; native adapter, numeric parity and R5.2 remain incomplete.
Scope / milestone: M3 private preparation, synthetic settings only; no reference propagation.
Base revision: `b98a48bfcd58d15f87a41dfc8a55b587354453e9`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; follows [ADR0137](0137-short-coast-earth-gravity-contract.md) and [oracle preparation](0138-independent-short-coast-oracle.md).

## Context and constraints

The independent oracle is verified. Before implementing its native counterpart,
inspect the installed1.0.0 binding instead of assuming current online documentation
or inventing accessible model/profile fields. Bound this readiness unit to imports,
settings/body/model construction and API inspection, with no propagated arc,
mission-state query or kernel load. Each probe had a20s/30s process watchdog;
all returned in less than1s. Existing code, environment and all numerical gates
stay unchanged. Full native source/build identity remains a runner responsibility.

## Options considered

- Assume dictionaries preserve requested source order and expose force types:
  reject; observations below contradict those assumptions.
- Use a direct simulator derivative callback as the force oracle: not selected;
  the standalone path failed before returning a derivative.
- Use explicit native construction plus synthetic propagation/force telemetry
  tests in the next implementation unit: selected, still requiring verification.

## Decision and rationale

Use explicit `BodyListSettings("SSB", "J2000")` and empty body settings, central
fields with the frozen GMs, `direct_spice("SSB", "J2000", body_name)` and no
unspecified default body resources. The pinned direct-SPICE default orientation
is ECLIPJ2000: passing J2000 is essential. Its aberration flags are inspectable;
verify all three are false rather than infer geometric output from a label.
No SPICE state was queried in this unit.

The pinned binding provides `runge_kutta_fixed_step` with `CoefficientSets.rk_4`,
the explicit-time translational overload, Cowell and exact-final-time termination.
The future adapter must use these explicit settings, inspect their inputs and
retain every native history before post-call checks, as already required by
ADR0137. Constructor availability alone does not validate an executed profile.

Actual acceleration-map construction returned Sun/Moon/Earth in the order
Earth,Sun,Moon, although settings were inserted Sun,Moon,Earth. Check exact sets,
counts and source associations on this opaque native mapping; serialize a separate
canonical Sun,Moon,Earth inventory. Do not reject a valid mapping solely for its
returned order or confuse canonical reporting order with native summation order.
GMs read from the constructed native fields exactly matched all three inputs.

Each map value is an opaque `AccelerationModel` with no public Python attributes;
RK settings expose `initial_time`, not readable coefficients/step. Do not invent
readback values or report class names as verified force types. Next implement a
closed, explicit construction path, check exact map sources/counts and field GMs,
and test actual native accelerations/trajectories on independent analytic fixtures.
Pinned single-source and total acceleration dependent-variable settings exist;
their runtime behavior still needs verification. Source/count checks and requested
telemetry alone do not establish exhaustive force correctness. No inventory or
numerical gate is waived by this binding limitation; stop if evidence is insufficient.

## Consequences and revisit conditions

The ordinary simulator creation function defaults to immediate propagation. Every
readiness construction here used `simulate_dynamics_on_creation=False`. In the
next adapter, count an attempted native arc before any call that can propagate.
Use fresh matched body systems and preserve the four-arc reference limit.

The synthetic derivative call at epoch0, using a zero-position spacecraft and
constant axis-aligned sources, raised `RuntimeError: Error when updating environment,
input size is inconsistent 0 0 1`. No derivative returned, and no force comparison
or state history was obtained. Do not infer direct-field parity, convergence or
an integration failure from this setup error. Avoid this unverified callback path;
use bounded synthetic component tests of the normal propagation interface next.
This is not a failed R5 scientific run and does not authorize reference retries.

## Evidence and verification

- [Installed API docstrings](experiments/0139-installed-native-api.txt),
  [construction output](experiments/0139-synthetic-construction.txt) and
  [simulator/telemetry inspection](experiments/0139-native-inspection.txt).
- [Identity](experiments/0139-installed-identity.json): Conda tudatpy1.0.0,
  build py312h2196d89_3, osx-arm64; Python3.12.14. The wrapper-file hashes in this
  record are not complete native binary/build identity. The initial Python
  distribution-metadata lookup failed; existing Conda metadata provided identity
  without installing/replacing anything.
- [Readiness summary](experiments/0139-native-readiness.json) retains digests,
  counts and both failed setup attempts as exception summaries, not raw stderr.
  Two synthetic body/model systems were constructed; one simulator was created
  with simulation disabled and one derivative call failed. Zero native propagated
  arcs, zero mission ephemeris queries/kernel loads; no R5 reference experiment.
- Strict OpenSpec,149 local links, JSON/digests and documentation diff checks pass;
  all247 previously tracked protected files remain byte-identical to the base.
  The two raw API docstring transcripts intentionally retain trailing whitespace.
  The first staged all-file whitespace check flagged those13 lines; a shell
  sequence incorrectly continued to commit after that nonzero check. No evidence
  was rewritten. Subsequent checks passed normally for docs/JSON/construction
  output, and for the two raw transcripts with only end-of-line whitespace
  detection disabled. This exception applies only to preserved docstrings.
  Existing4990-test result is reused
  from ADR0138: no project runtime code/test/dependency changed and pytest was not rerun.

R5.2b completes only API readiness. Next implement and verify the native adapter,
then shared runner/extended identity and offline audit before R5.3. Full M3,
mission accuracy, finite burns, continuous safety and M4–M6 remain open/deferred.
