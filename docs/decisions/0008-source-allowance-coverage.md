# 0008 — Audit source-position allowance coverage before force bridging

Date: 2026-09-14. Reviewed revision: `a2770e7`. M3 task3.9 remains open.
Status: accepted source audit, not an implemented force bridge.

## Question and evidence

Can a previously computed source-position allowance be used at the fresh
handoff? Follow [decision0007](0007-fresh-point-gravity-binding.md), using only
existing source, artifacts and captured output from its 2879-test run.
No new SPICE query, force evaluation or propagation was performed.

The relevant implementation is the reviewed revision of
[test_trajectory_spk.py](../../tests/test_trajectory_spk.py): construction of
`uniform_evaluation_bounds_m`, `chain_position_bounds_m`, `motion_samples`,
`fresh_affine_links` and `fresh_source_states`. The lower-bound helper in
[trajectory.py](../../src/space_nav/trajectory.py) requires proven input balls;
it does not supply them.

## Findings

1. Per-record evaluation allowances bound normalization plus series arithmetic
   over an extended record domain, not just a sampled epoch. Chain allowances
   sum maxima across required links and include centre addition and km-to-m
   conversion. Their L1 position error upper-bounds L2. They explicitly do NOT
   include arbitrary record-selection error or real ephemeris model uncertainty.
2. Candidate endpoints are checked inside unique guarded record cores. Their
   `motion_samples` error entries are exactly `chain_position_bounds_m`, not
   fitted residuals. Therefore the old anchor's numeric argument is not inherently
   an old-epoch-only bound; its provenance and core conditions matter.
3. Fresh source construction explicitly places the handoff and its following
   1/16 s inside the SAME guarded cores. Eleven links form eight chains. Sixteen
   comparisons reuse the existing native readbacks at offsets 1/16 and 1/8 s.
   They check L1 residual <= C*local_time^2/2 + chain_allowance. At the fresh
   anchor local_time is zero; the chain allowance is the relevant arithmetic term.
4. This supports conditional reuse of the chain arithmetic bound in those cores,
   not unrestricted transfer to another epoch or across a selection strip.
   Pinned kernel/reader assumptions and the established coverage must travel with it.

[Retained measured allowances](../../tests/data/m3_source_allowance_coverage.json)
are in metres, SSB/J2000. The fresh epoch is 978995455.2929223 TDB seconds since
J2000; the checked local source interval ends at 978995455.3554223 TDB s.
The values below are conditional arithmetic bounds, not statistical sigmas:

| Body / SPICE target | L1 allowance (m) |
| --- | ---: |
| Sun / 10 | 1.4595070471278306e-7 |
| Mercury / 1 | 4.3544796122872e-5 |
| Venus / 2 | 6.542382417808617e-5 |
| Earth / 399 | 6.0187747349184116e-5 |
| Moon / 301 | 8.934704095652991e-5 |
| Mars / 499 | 1.648618821045329e-4 |
| Jupiter / 599 | 4.281144922474497e-4 |
| Saturn / 699 | 7.284371515436439e-4 |

## Remaining binding and force obligations

The six new point vectors use ideal polynomial positions, while harmonic
vectors use stored source positions/matrices obtained from the fresh native
environment. A source bound on the audited SPICE readback does not, by itself,
bind every later consumer to that same readback. Preserve the existing fresh
readbacks and compare the relevant stored harmonic positions against them;
also verify exact epoch, frame, body mapping and kernel context. Do not add
new queries solely because the existing values were not retained.

For a nominal spacecraft position and a source position ball of radius epsilon,
a chord floor may be obtained by subtracting epsilon from a proved lower bound
on the nominal separation. Retain exact rational geometry and downward rounding;
reject a nonpositive floor as unresolved. Do not reuse an old radius floor or
claim this covers the spacecraft's incoming error ball without including it.

The existing point-force variation helper uses 2*GM*epsilon/d^3 only after d
bounds the entire chord. Harmonic fields require their verified spatial bound
and stored-matrix factors, not that point-force formula. Rotation/PCK error,
SRP, relativity, incoming state uncertainty and interval variation remain open.

## Selected next bounded implementation

Retain the already obtained fresh native source positions and the existing
chain allowances with explicit epoch/coverage binding. WHEN comparing them
with the exact source-polynomial anchors and stored harmonic positions, THEN
verify the appropriate allowance and exact readback/epoch/frame identity;
reject missing coverage or mismatched bodies. Keep the native query count fixed.
Qualify nonsingular chord floors independently before applying force bounds.
No new total-force certificate or trajectory extension follows.

Do not inflate epsilon from an observed mismatch: a mismatch is a failed binding
to investigate. Do not use empirical parity as a replacement for the conditional
arithmetic proof; it checks applicability to the intended consumer.

## Verification of the audit

Traced formulas and call arguments, compared retained values with the earlier
captured output, checked links/JSON and strict OpenSpec. No executable files or
scientific baseline changed. Full pytest was not rerun for this documentation;
the latest implementation result remains 2879 passed in 500.09 s.
