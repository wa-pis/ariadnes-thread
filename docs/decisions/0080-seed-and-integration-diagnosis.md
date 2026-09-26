# 0080 — Separate seed geometry from integration disagreement

Date: 2026-09-26. Revision inspected: `0138db9`, clean working tree.
Status: accepted diagnostic observations; no model or specification-gate change.
Scope: read-only analysis of [Decision 0079](0079-research-reference.md) and its
[stored evidence](experiments/0079-research-reference.json). Zero native launches.

## Findings

The M2 evaluator solves a Sun-centred Lambert problem between body centres and
uses a scalar periapsis escape/capture cost. It does not solve the finite-burn
connection from the configured lunar orbit to the required outgoing asymptote.
The prescribed M3 seed projects the outgoing excess-velocity direction into
ignition TNW, then holds those TNW components during thrust; the inertial
direction rotates with the current relative state. It is an optimizer seed,
not an already targeted trajectory. D4 deliberately runs without that optimizer.

An independent two-body instantaneous-impulse diagnostic exposes the mismatch:
the initial circular speed is 1633.504135 m/s; departure delta-v is 1728.785076
m/s, but its seeded direction is 60.952617 degrees from the initial velocity.
Using `v_after² = v_c² + delta_v² + 2*v_c*delta_v*cos(angle)` and
`v_infinity² = v_after² - 2*mu/r` gives 1750.036944 m/s, not the required
2443.013963 m/s. Applying that scalar delta-v tangentially gives 2443.013963 m/s
in this diagnostic. This does **not** establish the correct asymptote direction,
prove the requested orbit geometry is feasible or prescribe a tangential fix.

The actual departure burn lasts 2860.733099 s, about 40.48% of the initial
unperturbed circular period (7067.459726 s). The instantaneous diagnostic is
therefore not a prediction of the actual finite-burn exit state. It demonstrates
why scalar M2 fuel feasibility does not imply finite-burn target closure; it
does not quantitatively explain the entire 198-million-km miss.

The separate numerical-comparison failure is localized only to an interval:
departure cutoff differs by 0.012751 m / 0.000008626 m/s (both pass), while
arrival ignition differs by 1751.032853 m / 0.000313458 m/s (both fail).
The coast lasts 25168910.786164 s. Its two inputs already differ slightly;
stored boundary data cannot distinguish amplified initial error from different
coast integration error. Neither profile is an independent truth reference.
The initial states and targets match exactly; recorded mass flow agrees with
constant-thrust analytic depletion within 5e-11 kg for both profiles.

The integrator controls SSB Cartesian components. Relative position scale
`1e-11 * max(abs(position))` is about 1.28–1.31 m at the stored boundaries,
not the listed 0.001 m absolute setting alone. This is a diagnostic scale,
**not** an inferred global error bound or proof of the disagreement's cause.
Do not blame SPICE, loosen gates or replace settings on this evidence alone.

## Reproduce the geometry diagnostic

Run from the repository root using the pinned Python environment. This reads
retained JSON and performs standard-library arithmetic; no ephemeris queries,
trajectory propagation, output writes or modified physical constants.

```python
import json
import math
from pathlib import Path

s = json.loads(Path(
    "docs/decisions/experiments/0079-research-reference.json"
).read_text())["science"]
moon = next(x for x in s["provenance"]["environment"]["harmonic_fields"]
            if x["body"] == "Moon")
mu = moon["gravitational_parameter_m3_s2"]
r = (moon["orbit_shape_radius_m"]
     + s["scenario"]["departure_orbit"]["periapsis_altitude_m"])
c = s["provenance"]["candidate"]
dv = c["departure_delta_v_m_s"]
v_c = math.sqrt(mu / r)
cosine = s["nominal"]["burns"][0]["direction_tnw"][0]
seed_excess = math.sqrt(v_c**2 + dv**2 + 2*v_c*dv*cosine - 2*mu/r)
required_excess = math.hypot(*c["departure_v_infinity_m_s"])
assert math.isclose(seed_excess, 1750.0369441614744, abs_tol=1e-6, rel_tol=0)
assert math.isclose(required_excess, 2443.0139632236283, abs_tol=1e-6, rel_tol=0)
assert abs(seed_excess - required_excess) > 690
print(seed_excess, required_excess)
```

## Decision and next scope

Preserve the prescribed seed and all tolerances. Changing the seed unilaterally
would violate the current targeting contract, which explicitly prescribes it.
Do not add an optimizer to the research-only path under the name of a bug fix.

Next proposed bounded step: complete D4.5 with one identical-input replay under
the existing 300-second/six-arc cap and a new evidence filename. Compare science
fields excluding wall time. Reproducing disagreement is a valid repeatability
result, not numerical acceptance. Then scope a separate controlled coast study
using identical starting states to isolate inherited versus integration errors;
its budget and acceptance criteria must be agreed before native runs.
Targeting/seed redesign is separate and needs an explicit scope decision.

Verification: stored-data arithmetic and code inspection only. No runtime code
changed; full test suite was not rerun. D4.5, strict M3 and safety remain open.
