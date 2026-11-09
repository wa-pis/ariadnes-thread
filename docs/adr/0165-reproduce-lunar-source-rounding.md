# 0165 — Reproduce saved lunar position with staged rounding

Date: 2026-11-09 (Europe/Samara)
Decision status: accepted saved-data diagnosis; no provider change accepted.
Implementation: unchanged; private offline evidence only.
Scientific verification: staged rounding reproduces the sampled position; R5.17 scientific acceptance still fails.
Scope / milestone: M3 R5.18, saved R5.17 Moon source discrepancy.
Base revision: `edec79c49a5c258617aa95a262ca67570272c56a`, initially clean `dev`, equal to `origin/dev`.
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/short-coast-sensitivity/spec.md), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md).
Supersedes / Superseded by: none; diagnoses [ADR0164](0164-corrected-coast-force-gate-fails.md) without altering its failure or [ADR0162](0162-corrected-real-integration-contract.md).

## Context and constraints

Both 300 s A solves and all 21 trajectory comparisons passed in R5.17. The
required Moon overall force gate failed at normal RHS ordinal 6 (local 0.25 s,
hi=978995455.4804223 TDB seconds from J2000, lo=0, J2000/SSB). Returned-geometry
force, source-state parity and other assessed arithmetic gates passed. The
diagnosis asks whether the saved discrepancy already exists in the raw km
return, and whether rounded Earth and geocentric Moon terms can reproduce it.

Use the existing 14 assessed observations (13 distinct source epochs), with
the archived exact Type 2 positions at hi, saved km and SI returns, and the
recorded failure geometry/reference. The [NAIF SPK description](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/spk.html)
defines Type 2 positions by Chebyshev coefficients; the retained Earth and
Moon record identities and centre links come from ADR0162 and the study bytes.
There is no new polynomial evaluation, SPICE access, orbit propagation, study
or audit replay. The bounded saved-data check uses rational position arithmetic
and four static diagnostic geometries at 80 and 100 digits (eight fields), with
a 5 s parent watchdog. No gates, inputs, kernels or model change.

## Options considered

- Attribute the entire residual to SI conversion: check exact scaling against
  the saved km and SI values rather than assume an incorrect conversion.
- Compare a single rounded barycentric coordinate with a staged centre sum:
  selected on the same retained operands, independently of solver behaviour.
- Query the native geocentric state now or rerun the coast: deferred; neither
  is needed to distinguish these arithmetic effects in the saved sample.

## Decision and measurements

At the failed sample, signed position differences are in micrometres:

| Difference | x | y | z | Norm |
|---|---:|---:|---:|---:|
| Exact scaling of the saved km return minus exact Type 2 | −6.168947 | +11.294044 | −3.234931 | 13.269367 |
| Saved SI minus exact scaling of the saved km return | −0.238419 | +2.980232 | −2.443790 | 3.861443 |
| Saved SI minus exact Type 2 | −6.407366 | +14.274276 | −5.678721 | 16.645034 |

The two signed vectors sum exactly to the retained source discrepancy; their
norms do not add. All three SI components are correctly rounded binary64 products
of the saved km components by 1000. Relative to one direct rounding of the exact
barycentric Moon position to km, saved raw x/y are −1/+1 binary64 steps away and
z matches. Thus the first difference already exists before SI conversion.

For each saved epoch form the exact geocentric term by subtracting the exact
Earth position from the exact Moon position. Convert this difference to km and
round once; add it to the saved Earth km vector, with one rounding of the sum.
This reproduces **42/42 raw Moon position components bit for bit**. Directly
rounding the exact barycentric Moon position reproduces 31/42. All 42 saved Earth
components match direct rounding, so using the observed Earth vector and using
that rounded exact Earth vector are indistinguishable here. At the failed row,
Earth rounding, geocentric rounding and rounding of the sum have norms of
7.831773, 0.028286 and 5.665313 µm respectively, and telescope exactly to the
13.269367 µm discrepancy before SI conversion. This is a sufficient arithmetic
model for the sampled position, not a trace of intermediate native SPICE values.

Four counterfactuals hold the failed row's spacecraft position, epoch, Moon GM
and original force envelope fixed. They evaluate the exact geometry perturbed
only by the hypothetical source representation. Both Decimal precisions agree
within relative 1e-60 for each error. The measured R5.17 candidate is shown for
context; its overall error includes assembly and field arithmetic as well.

| Source representation at the saved row | Error, m/s² | Ratio to original envelope |
|---|---:|---:|
| Measured R5.17 overall, saved | 1.5812863e-11 | 1.088864 |
| Saved barycentric km, exact scaling to SI | 1.3465871e-11 | 0.927252 |
| Direct rounding to barycentric km, then rounded SI | 4.9473485e-12 | 0.340671 |
| Direct rounding of the exact source to SI | 2.5915362e-12 | 0.178452 |
| Retain rounded Earth and model geocentric terms without rounding the sum or SI | 7.3485098e-12 | 0.506014 |

The correct SI rounding contributes to crossing this strict boundary in the saved
geometry. The retained raw km discrepancy already
uses about 93% of the envelope in the exact-scaling diagnostic. Neither claim
assumes a bad km-to-m conversion. These substitutions do not show that a revised
provider or full solve would pass; the hypothetically precise source is built
from the same retained model and is not an independent ephemeris.

## Consequences and revisit conditions

Preserve the negative R5.17 verdict. One-step km mismatches also occur in passing
observations. This sample proves neither a uniform source-error bound nor the
native routine's exact rounding sequence, segment-selection parity outside the
assessed epochs, historical R5.3 causality, Earth sensitivity or mission safety.
The recorded ordinal failure is not a monotone time crossing.

If pursued next, specify one bounded source-only probe that observes Earth/SSB
and Moon/Earth separately under the same kernel identity and tests compensated
assembly on the failed epoch and fixed controls before considering a new coast.
This record does not authorize that query, change the tolerance, or reopen the
once-only study. R5.17 scientific acceptance and strict M3 remain open;
automation ariadna-m3 remains PAUSED.

## Evidence and verification

The [analysis invocation](experiments/0165-saved-source-analysis.txt) checks the
uncompressed original study and audit digests and uses only the standard library.
The [result](experiments/0165-saved-source-analysis.json) retains every control,
exact signed decomposition, force ratios and scope. It completes in about 0.17 s
before writing evidence, within the 5 s watchdog. The [verification manifest](experiments/0165-verification.json)
records archive/test hashes, protected bytes, JSON/link checks, diff and strict
OpenSpec validation. The verified 6182-test/Ruff baseline is reused; runtime
tests and Ruff are not rerun on unchanged code.
