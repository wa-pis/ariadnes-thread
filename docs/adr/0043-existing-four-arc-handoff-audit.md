# 0043 — Audit the existing four-arc handoff

Date: 2026-09-14. Parent revision: `8ec15b9`. Task 3.9 remains open.

## Correct the unit of discussion

The recent phrase "two-interval handoff" means a preceding composite
prefix plus the next arc, not two independent native arcs covering the
whole retained control. The existing Mars path has FOUR accepted nominal
arcs. Starting at 978995455.2304223 TDB seconds since J2000, their durations
are 1/64, 1/64, 1/32 and 1/16 s, totaling 1/8 s. The newly retained fresh
endpoint/SPK/force contexts describe the fourth arc, starting at
978995455.2929223 and ending at 978995455.3554223.

The source code already labels these outputs two-, three- and four-segment
bounds. This audit corrects the planning shorthand, not the algorithm.

## Trace and observed numerical continuity

`short_handoff` takes the first nominal native endpoint with the degree-map
reference bound plus its native residual exactly once. The initial zero
error here defines an exact synthetic control state, not a measured-state
uncertainty claim. `two_segment_handoff` then takes nominal adjacent result
index zero; `three_segment_handoff` takes nominal doubled result index zero.
The longer/fresh control consumes that third endpoint. Tighter diagnostic
results are not silently substituted into the accepted nominal chain.

| Accepted arc | Duration, s | Cumulative duration, s | Reported position bound, m | Reported velocity bound, m/s |
| --- | ---: | ---: | ---: | ---: |
| Initial short | 0.015625 | 0.015625 | 4.089581664258794e-5 | 1.5322522880991422e-8 |
| Adjacent | 0.015625 | 0.03125 | 7.684027797138391e-5 | 5.87273990686923e-8 |
| Doubled | 0.03125 | 0.0625 | 1.0529778787867129e-4 | 2.3227467748483292e-7 |
| Longer, old shifted reference | 0.0625 | 0.125 | 1.4951220569742958e-4 | 9.436498377495054e-7 |

Read-only replay of the retained Decision0042 full-suite output confirms
all three report-level incoming error pairs equal the preceding reported
outgoing pair, adjacent start/end epochs join exactly, all conditional
prerequisites and both endpoint gates pass, and the duration totals exactly
1/8 s. The fresh endpoint artifact's incoming pair equals the doubled
output, not zero. These checks inspect existing results; no propagation
was run for this audit.

Internally the handoff carries exact Fractions; the diagnostic pairs round
outward. Native initial-state construction round-trips each stored component
back to the same Fraction and checks the actual history's initial state.
The fresh transport independently rounds incoming radii outward and checks
they do not shrink. Each continuation closes its own cumulative domain;
it does not copy the smaller preceding domain's force bounds.

The fresh cubic is a second reference for the SAME fourth nominal native
arc, not a fifth propagation. Its slightly larger outgoing bounds remain
1.4951281615784107e-4 m and 9.62662340905759e-7 m/s. Preserve the tighter
old shifted-reference result. Four accepted nominal arcs also do not mean
four total charged arcs: the complete inventory includes thirteen native
arcs, counting independent/tighter diagnostics as before.

## Concrete remaining gap and next step

The live code connects the three native handoffs, but the new standalone
endpoint artifact retains only the fourth arc. The previous prefix reports
retain error magnitudes without all native input/output vectors in one
lineage record. A saved last-arc context therefore does not independently
demonstrate the entire accepted prefix's state continuity.

Next retain four compact lineage rows from the EXISTING accepted nominal
histories, with epochs, initial/final seven-states and exact incoming/
outgoing error radii. Check all three state/epoch joins and non-reset error
handoffs in the same probe, distinguish four accepted rows from thirteen
charged inventory arcs, and link the last row to the already retained
endpoint. Reuse the existing paths; add no new propagation or public
certificate framework. WHEN a predecessor state/epoch/error is changed
independently, THEN the lineage check must reject; WHEN unchanged, THEN
all three joins must reproduce. This is a next-step criterion, not a
completed test in this audit.

This does not authorize a longer coast: the largest closed cumulative
domain is still 0.125 s. Native-stage/finite-burn safety and mission-scale
subdivision counts/runtime remain open. A short conditional endpoint
bound is not a global independent tighter-integrator validation.

## Verification

Documentation-only source/result audit and exact report-level assertions.
Strict OpenSpec and whitespace checks pass. No code, data fixture, force,
tolerance or budget changed; the full suite was not rerun. The unchanged
parent revision has 3183 passing tests. Task 3.9 remains open.
