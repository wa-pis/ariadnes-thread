# Current State

Updated: 2026-11-25. Keep under 60 lines; durable evidence in ADRs.

## Current preparation contract
[ADR0248](docs/adr/0248-design-coupled-synthetic-benchmark.md) completes F2 design:
private bounded two-node multiple shooting; six controls plus12translation-node
unknowns, mass/time derived. Manufactured uniform-gravity two finite TNW burns,
known-witness Decimal target and independent actual-command RK4 checker.
Explicit bounds/scales/TRF/DOP853, dimensional gates and finite shared300s budget.
No numerical evaluation, benchmark run or implementation; gates unverified.
Next F3: implement/qualify only this artificial benchmark and independent checker,
with focused and required frozen regression lanes, Ruff/review/strict OpenSpec.
No real archives/SPICE mission experiment, dependency or production-solver change.
[ADR0247](docs/adr/0247-formulate-coupled-moon-mars-problem.md) retains F0:
fixed orbital six-states/epochs/planes/phases, hardware and six finite-burn controls;
one full-force history. M2/excess vectors are seeds, not endpoint equalities.
Free dates/phases or orbit-membership targeting remain unadopted proposals.
Artificial success cannot establish F0 feasibility or physical error bounds.

## Goal and scheduler
One independently audited admissible analytical pair was the user-selected goal;
it remains unmet. No99% probability, physical closure or safety claim.
User resumed `ariadna-m3` on2026-11-25: ACTIVE every5minutes, samechat.
Proceed with authorized F3 preparation/artificial tests under ADR0248;
F1/F2 do not admit physical runs or revive consumed histories/R5.60.
Pause on required user choice/access/authorization, contract-changing failure,
or independently verified agreed success. Use pinned Conda and ponytail.

## Latest retained scientific result
[ADR0246](docs/adr/0246-record-bounded-retained-inconclusive.md): on clean33fea7c,
one0245 P6 returns complete inconclusive exit2/no-verified-witness.
Independent stdlib audit exit0 verifies13points/26slots, zero optimizer replay;
namespace0243-p3-retained consumed. Positive151.33118995827647deg proposal fails
mass floor:6157.712787309595m/s vs6117.706618414368m/s; negative objective guarded.
No continuous refusal/global optimum/physical impossibility proved.
Parent1.048381667s;312980B namespace; all caps/pins agree. No SPICE/integration/R5.60.

## Preserved verification and boundaries
[ADR0245](docs/adr/0245-qualify-retained-dispatch-lifecycle.md): aad842f qualified,
readiness33fea7c;7051portable/412live pass,42archive skips,7505local/CI IDs.
CI45358338765:7426pass,42archive+37platform skips; all37platform pass locally.
Runtime tests not repeated for F2 documentation; no fresh runtime-test claim.
[ADR0135](docs/adr/0135-fixed-orbit-boundary-contract.md)/
[ADR0205](docs/adr/0205-design-fixed-command-physical-join.md) retain all fixed
boundary, join/error-bound/readiness gates. No physical join or strictM3/task3.9.
No changed inputs/caps/tolerances/physics, new real run, M4–M6/ML/UI/publication
without accepted contract/authority. Preserve history and moon_to_mars.py;
work on dev, commit/push each checked stage to existing origin/dev.
