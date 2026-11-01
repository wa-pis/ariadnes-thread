# 0149 — Inspect oracle time and coordinate conditioning

Date: 2026-11-01
Decision status: accepted saved-data diagnosis under the user request to check now; no reference replay or profile change.
Implementation: static/independent reviews and seven bounded arithmetic probes complete; root cause remains unproven, no reference replay.
Scope / milestone: M3 R5 failure diagnosis, zero scientific imports/body queries/solves.
Base revision: `dfe3c70e5bb5ed2014cc3c2755e39a21bc6e03d0`, initially clean.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; diagnoses the [retained failure](0148-short-coast-oracle-rhs-limit.md) without replacing its contract or evidence.

## Context and constraints

The user requested an immediate check of the10000-RHS failure. Inspect existing
source and retained operands without a second reference run. Bound the scalar
arithmetic audit to5s and seven synthetic elapsed-time probes, using stdlib only,
with zero state acquisition, integration, native/scientific imports or environment
changes. Quantify binary64 spacing and phase residuals, source-displacement scales
and local point-force conditioning. The probes are arithmetic examples, not new
mission samples, measured force errors or an inferred trajectory. Preserve exact
input/source identities, elapsed budget, finite output and unavailable conclusions.

## Options considered

- Repeat the same solve, increase the cap or loosen tolerances: reject; does not
  diagnose the cause and changes the frozen experiment.
- Declare a root cause from the cap alone: reject; the failed solve retained no
  accepted/rejected-step history or normalized error trace.
- Review counters/configuration and quantify saved-input precision asymmetry:
  selected; can reveal a concrete mechanism without consuming another run.

## Findings, evidence and verification

The oracle's counter is consistent: one RHS callback adds one RHS count and
three body-state reads. Retained30021=21+3*10000 is correct, not a triple count.
The correction equations, DOP853 selection, normal/tighter parameter forwarding
and model order show no obvious wiring error. This review does not prove all
possible bugs absent. Two independent read-only reviews reached the same precision
finding without native work, edits or test reruns.

### Confirmed precision asymmetry

[Oracle line161](experiments/0138-short-coast-oracle.py) reconstructs spacecraft
position from accurate local elapsed time s, while line162 queries the bodies
at rounded binary64 t0+s. At saved t0=978995455.2304223s, absolute-time spacing
is1.1920928955078125e-7s, approximately119.209ns. The saved Moon SSB speed is
31246.224457m/s: one time ULP corresponds to3.724840mm of source motion;
half-ULP rounding corresponds to a1.862420mm local motion scale. These are
conditioning scales using saved velocity, not observed ephemeris errors.

Absolute spacecraft position spacing is7.629/15.259/7.629micrometres along x/y/z.
The normal local correction-position atol is0.1micrometre. Correction variables
improve the solver's error scale but reconstruction for force evaluation still
rounds onto the much coarser absolute coordinate grid. The local Moon point-force
Jacobian spectral norm is2mu/r^3 at separation1837400m. Applying it to the
half-time-ULP motion scale gives a first-order worst-direction scale
2.944019620354976e-9m/s^2. This is not a measured acceleration error, a rigorous
trajectory-error bound or a DOP853 rejection prediction.

[Seven stdlib scalar probes](experiments/0149-conditioning-audit.json) completed
in0.03053345810621977s before flush, with the post-flush5s check passing.
For synthetic s=0.1,0.2,1/3 and48.605s, the exact Decimal residual
float(t0+s)-t0-s is nonzero; integer s=1,50,300 gives zero. A synthetic local
perturbation d -> d+v_moon*residual, evaluated in100-digit Decimal at the saved
initial geometry, changes the point force by approximately0.9–2.3e-9m/s^2 for
the four nonzero examples. This explicitly demonstrates arithmetic sensitivity;
it does not assert that those s values, linear body motion or perturbed force
occurred in the failed solve. All seven retained comparison nodes use integer
50s offsets, so their clean timestamp arithmetic alone cannot detect this issue
at arbitrary internal stage times.

### What the solver evidence does and does not show

The pinned installed SciPy source (hash/path in the receipt) scales local errors
as atol+rtol*max(abs(q),abs(q_new)) at rk.py146 and retries with smaller h after
an error-norm rejection. DOP853's E5/E3 estimator is at lines520–528; its trial
uses12 RHS calls and dense interpolation adds more. Thus10000 RHS is not10000
accepted time steps. Do not compare an acceleration perturbation directly with
a position/velocity tolerance or predict a step length from h*noise alone.
Actual weights, h, correction scales and error estimates are required.

Existing closed-form solver tests use epoch0 with a smooth origin-centred body;
the real SPICE boundary test checks a single epoch0. They do not jointly exercise
moving bodies, a large absolute epoch, SSB coordinate magnitudes and adaptive
stepping. The failed solve raises before solve_ivp returns, so its intermediate
accepted/rejected steps and normalized error components were not captured.
The last saved body-query time48.605s cannot establish completed integration
coverage: an internal trial or dense interpolation can query earlier times.

The precision asymmetry is confirmed; its causal role in exhausting the10000
RHS cap remains a strong hypothesis. The available evidence cannot distinguish
how many attempts were rejected, how far accepted integration reached, which
components dominated the error norm or whether another mechanism contributed.

### Verification and retained scope

[Invocation](experiments/0149-conditioning-invocation.txt) and
[output](experiments/0149-conditioning-output.txt) retain the actual arithmetic
check. The receipt binds the failed study and inspected oracle/runner/test and
installed SciPy source hashes. Assertions check the119ns spacing, half-ULP
rounding envelope, nonzero fractional/zero selected integer residuals, count
identity, finite JSON, deadline and absence of scientific modules. No SPICE,
body query, integration, new mission sample or reference replay occurred.
All287 protected tracked files remain identical to the base. Runtime, tests and
environment are unchanged; reuse5255 full tests/Ruff from ADR0146 rather than
repeat them. Source/artifact digests, local links, diff, finite JSON and strict
OpenSpec pass. Automation remainsPAUSED; this user instruction authorized the
read-only diagnosis, not restarting the failed experiment or its schedule.

## Consequences and revisit conditions

No physics, kernel, candidate, profile, gate or runtime/test code changes.
The next proposed contract should begin with a synthetic moving-body fixture
at realistic absolute epoch/coordinate magnitudes and record trial h, accepted /
rejected counts, component error/scale and exact body-time rounding residuals.
Any instrumented solve must have explicit finite work/time limits and its own
scope; the failed R5 reference must not be replayed as an undocumented probe.
Only after such diagnosis should a stable relative-coordinate/time treatment
be designed and independently checked. Do not blindly raise the cap, weaken
scientific gates or substitute interpolated ephemerides. Any instrumented solve
or revised reference experiment still needs a separate bounded contract.
A conditioning diagnosis cannot establish actual oracle rejection counts, exact
root cause, Earth-force sensitivity, independent numerical agreement or mission
accuracy/safety. Preserve the5255-test result on unchanged code; do not repeat it
for documentation or arithmetic inspection.
