# 0045 — Separate tolerance purposes before extending the coast

Date: 2026-09-14. Parent revision: `aed4474`. Task 3.9 remains open.

## Planning correction, not relaxed thresholds

Do not turn the short-control 0.001 m / 1e-6 m/s endpoint enclosure gates
into an unstated mission-wide absolute-error requirement. The active
physical-trajectory specification distinguishes the following quantities:

| Purpose | Existing values | Meaning |
| --- | --- | --- |
| Nominal integrator settings | Relative 1e-11; absolute 1e-3 m, 1e-6 m/s, 1e-9 kg | Adaptive numerical settings, not a global true-error guarantee |
| Adjacent arc continuity | 1e-6 s, 0.001 m, 1e-6 m/s, 1e-9 kg | Equality of the propagated handoff, not distance from ideal truth |
| Frozen-command nominal/tighter validation | 10 m, 1e-4 m/s, 1e-6 kg at common boundaries | Agreement of two integrations, not a rigorous true-state radius |
| Retained short full-force controls | 0.001 m, 1e-6 m/s | Conditional reference/native endpoint enclosure regressions; keep unchanged |
| Continuous collision protection | Non-intersection with eight pinned guard spheres, with all enclosure errors included | A geometric safety test, not a universal scalar velocity-accuracy gate |

Sources in the active spec: "Numerical error budget and scientific checks",
"Join exact arc boundaries", "Define every collision surface", and
"Qualify adaptive safety subdivision before selecting production limits".
The design's "Approved safety-limit investigation" explicitly assigns the
verified 0.001 m chord endpoint allowance to analytic controls only, with
full-force error budgets to be justified separately. Its later short-coast
controls remain valid regressions with their existing gates.

This distinction does NOT authorize replacing a rigorous radius by the
10 m nominal/tighter difference, dropping velocity error from force/domain
transport, or treating a failed short-control gate as passed. No production
acceptance rule, test threshold, force model or integration setting changes.

## What the current data actually limit

The retained four-arc chain ends after 0.125 s. Its latest cumulative
4000 m / 0.5 m/s domain is closed only over the qualified interval. Source
record coverage of the original one-second domain does not extend the
spacecraft/force-domain proof. The 283007.82847962243 m minimum conditional
clearance is a domain-to-guard margin for that interval, not future clearance
or a license to extrapolate it.

The fresh fourth-arc envelope has outgoing velocity radius
9.62662340905759e-7 m/s, leaving 3.73376590942409e-8 m/s below its private
1e-6 gate. As an ALGEBRAIC frozen-coefficient diagnostic only, suppose another
1/16 s step reused D=7.943095084820736e-6 m/s^2 and
J=1.1082532101285457e-4 m/s^3. Then D*h alone adds
4.96443442801296e-7 m/s, and J*h^2/2 alone adds
2.164557051032316e-7 m/s. Incoming plus either term exceeds the short-control
gate even with all other nonnegative envelope terms omitted. Exact Fraction
checks reproduce both inequalities from the saved fresh transport artifact.

These coefficients are NOT qualified on the next interval. This diagnostic
is neither a next-step error bound nor a lower bound on physical error. It
only shows why repeating the current envelope/gate without further analysis
cannot certify another equal step. Tightening only the constant anchor
channel would not resolve the unchanged rate-channel accounting. It does
not prove the mission or adaptive integration infeasible.

## Next bounded work

Derive a safety-specific geometric enclosure contract using the existing
position/velocity/source-error transport and all eight collision guards.
State precisely which enclosure must hold over an interval and how failure
stays unresolved. Keep the old short-control accuracy regressions and the
separate full-command numerical validation unchanged. First test the
contract with existing retained domains/analytic controls; no new native
arc or longer coast is justified by this audit. Any proposed production
acceptance/allocation change needs explicit review and user approval before
implementation. Do not replace the current limits until measured full-force
work supports it under the shared 300-second budget.

## Verification

Read-only spec/design/source/artifact audit and exact scalar accounting;
strict OpenSpec and whitespace checks pass. Documentation only: no runtime
code, fixture or numerical threshold changed, and the full suite was not
rerun. The parent revision retains 3201 passing tests. Task 3.9 remains open.
