# 0067 — Subdivision reduces rate cost, not every error cost

Date: 2026-09-15. Parent revision: `9c0fd72`. M3 task 3.9 stays open.
Status: exact manufactured composition plus hypothetical budget sensitivity.

## Decision and analytic control

Reuse `_coast_error_envelope` to compose equal reference pieces without
resetting incoming position/velocity errors. First isolate the accounting
with Lx=Lv=0, a common local defect D+J*tau and repeated endpoint residual
bounds rp and rv. For total horizon H, N pieces and h=H/N, exact composition is

`V_N = v0 + D*H + J*H^2/(2*N) + N*rv`,
`P_N = p0 + H*v0 + D*H^2/2 + J*H^3*(3*N-1)/(12*N^2)`
`      + N*rp + rv*H*(N-1)/2`.

The velocity residual affects subsequent position too; its contribution is
not just N times a position residual. These formulas assume equal pieces and
common nonnegative bounds. They do not establish domains or uniform D/J for
a physical mission. Positive state-feedback terms require separate treatment.

Sixty independent manufactured cases use smooth truth acceleration
`sign*(D+J*t)` and piecewise reference acceleration `sign*J*t_start`.
Exact signed reference endpoint perturbations represent rp/rv. At every
join, compare the existing envelope recursion, the closed form and separately
integrated truth/reference states. Cover both signs, 1/2/4/8/16/32 pieces,
nonzero incoming errors, isolated constant/rate/residual channels and mixtures.
The endpoint perturbations are arithmetic test controls, not physical jumps
of a spacecraft or empirical characterizations of a native integrator.

Thus the rate term improves as 1/N, but a common constant defect still costs
D*H and repeated velocity residuals cost N*rv. Subdivision is not uniformly
beneficial. Any measured per-piece cost must also count rejected/parent work.

## Hypothetical fourth-endpoint sensitivity

Use the retained H=0.125 s and full incoming error pair. As a deliberately
unqualified sensitivity parameter, assume the last local-translation rate
8.265836017855932e-5 m/s^3 were a common J on every future piece. It has NOT
been proved for those new references. Set every other defect, feedback and
new residual to zero before computing the remaining allowances.

| Analytic pieces | Optimistic velocity accounting (m/s) | Fits both private gates with all other costs zero? |
| ---: | ---: | --- |
| 1 | 1.6084307798007537e-6 | No |
| 2 | 1.2855465603532565e-6 | No |
| 4 | 1.1241044506295077e-6 | No |
| 8 | 1.0433833957676334e-6 | No |
| 16 | 1.0030228683366964e-6 | No |
| 32 | 9.828426046212276e-7 | Yes, under these optimistic assumptions only |

For 32 pieces, remaining velocity room is about 1.7157395378772315e-8 m/s.
It must pay the COUPLED cost `D*H + 32*rv`, plus omitted channels. The separate
intercepts are D<=approximately 1.3725916303017852e-7 m/s^2 with rv=0, OR
rv<=approximately 5.361686055866348e-10 m/s per piece with D=0. They cannot
both be spent in full. The separate position-only rp intercept is about
2.6573925091289252e-5 m per piece when D=rv=0. Negative intercepts in the
retained table mean the baseline already fails, not negative usable budgets.
All reported intercepts are approximate diagnostics, not accepted allocations.

These are reference-piece counts, not added native arcs. We have not selected
32 pieces, obtained their states, certified their anchors/residuals, or shown
that a composed physical run fits 300 s. No scientific tolerance changes.

## Verification and next step

All 61 new analytic/sensitivity tests passed in 0.10 s. Each sensitivity row
also matches exact repeated calls of the existing transport helper. Separate
replay: 61 passed in 0.10 s. Both runs and the full-suite report match
`tests/data/m3_fourth_hypothetical_subdivision_allowances.json` exactly.
Full suite: 3343 passed in 463.66 s (native inventory 143.05 s, portable
46.58 s). All 19 prior native, 6 prior portable and 5 prior retained-input
scientific reports match the parent run after excluding timers only.
Inventory arc counts remain 13/0; harmonic reuse remains 14 requests,
4 misses and 10 hits. Ruff, strict OpenSpec validation, whitespace checks
and the unchanged legacy SHA-256 passed. Suite time covers separate tests,
not one mission's shared 300 s budget. No production, UI or dependency changes.

Before choosing subdivision, compare its repeated anchor/residual accuracy
and cost demands with a richer reference that captures more force variation.
Prioritize bounded low-cost evaluation controls for candidate anchor/derivative
methods; do not rerun a known over-budget exact high-degree evaluation or add
native pieces without a viable numerical/error argument. Any eventual
composition must establish per-piece domains, rates, all residual charges,
cumulative errors and the shared runtime budget. No targeting is enabled.
