# 0242 — Complete P3 regression qualification without a retained search

Date: 2026-11-24 (Europe/Samara; initial runs began on 2026-11-23)
Decision status: accepted
Implementation: minimal runtime/test repairs complete; P3 qualification remains open pending repaired CI
Verification: 412 live tests passed before repair; 151 focused and 6964 repaired portable tests pass; repaired CI pending
Scope / milestone: P3 regression qualification within the active M3 change
Base revision: `4f5cbb3fb2cd2a162fb1ba62d39f8e7294af1e45`; repaired sources bound in [preparation evidence](experiments/0242-preparation.json)
Related OpenSpec: [requirements](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-use-bounded-scalar-search-only-to-propose-an-analytical-witness), [design](../../openspec/changes/refine-physical-trajectory/design.md), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [roadmap](../../openspec/ROADMAP.md)
Supersedes / Superseded by: none; completes the verification deferred by [ADR0241](0241-qualify-artificial-bounded-witness-search.md), preserving ADR0240's method and gates

## Context and constraints

The user separately authorized the existing live TudatPy/SPICE regression and CI,
without a new P3 search on saved real inputs. Existing live tests include ordinary
native propagation and small SPICE transfer searches; these are regression tests,
not a new P3 mission experiment. Automation stays PAUSED and R5.60 stays closed.

All 412 local live tests passed in 635.88 s on clean `4f5cbb3`; all 1328 Git-visible
files, HEAD and status stayed unchanged during that run. The first manually
triggered [CI run](https://github.com/wa-pis/ariadnes-thread/actions/runs/45252415905)
passed setup, lint and actual standard-kernel loading/CLI smoke, then failed the
portable lane: 6935 passed, 6 failed, 19 errors, 42 archival and 1 platform skip.
Its live step did not execute. The [failure inventory](experiments/0242-ci-initial-failure.json)
preserves that outcome; it is not retried unchanged or labelled a passing run.

## Options considered

- Rerun unchanged, skip failing checks or raise budgets: rejected; both failures
  have reproducible lifecycle/path causes rather than a scientific tolerance issue.
- Duplicate the private adapter stack: unnecessary before completed qualification.
- Repair the exact metadata registration and artificial clock injection: selected.
  Preserve historical scientific sources and existing evidence byte-for-byte.

## Decision and rationale

The Linux loader inventory registered literal `/proc/self/maps`, but the guard
canonicalizes every open to `/proc/<current PID>/maps`. Resolve that fixed constant
before registering/opening it. This grants no prefix, PID wildcard, caller path or
additional native permission. Keep the 512 KiB metadata read, explicit byte charge,
4 MiB aggregate input limit, runtime allowlist and startup-inclusive deadline.
Portable synthetic alias tests check canonical reads, unrelated files/writes and
both metadata/input caps, including the explicit metadata-byte charge.

The six corrected-study failures came from collection-time `PROCESS_START` being
older than its shared 60 s budget before injected artificial calls began.
Inject constant clocks into those test-only study/audit calls, as in existing
fixture practice. Simulate a 120 s-old import in the fixture; preserve advancing
clock/deadline tests and historical `0163` implementation/limits unchanged.
The independent clock review reproduced the six failures before repair; all
24 affected tests then passed normally and with delayed study/auditor imports.

The in-place repair is limited to unfinished P3 runtime implementation and tests.
Original `0241` JSON, profiles, logs and scientific helpers are immutable history
bound to `4f5cbb3`; they do not authenticate the changed runtime source. New
[producer](experiments/0242-producer-runtime.json) and [audit](experiments/0242-audit-runtime.json)
profiles record the repaired source identity. No scientific formula, dependency,
kernel, tolerance, command/mass gate, workflow or production API changes.

## Evidence and verification

[Focused tests](experiments/0242-focused-tests.log): 151 passed in 11.05 s, covering
127 P3 cases and 24 artificial corrected-study cases. The [local live log](experiments/0242-live-tests.log)
records the pre-repair 412 passes; it is not relabelled a repaired-revision run.
The [repaired portable lane](experiments/0242-portable-tests.log) passes 6964 tests
in 209.59 s, with 42 archival skips and 412 live deselections. All 1335 Git-visible
files, HEAD and status stayed unchanged throughout. Its case inventory and the
pre-repair live inventory are disjoint and cover 7418 cases (7376 passes and
42 archival skips). Selected live tests, production and historical scientific
sources are byte-identical across this repair; that live result is reused only
for those unchanged paths. Independent review, Ruff and strict OpenSpec pass.
Repaired-current-source CI must still pass both lanes before checking P3 complete.

## Consequences and revisit conditions

This closes preparation only after its required regressions succeed. It does not
produce a real analytical witness, continuous refusal, executable pair, adopted
Mars target, physical join, M3 completion or safety claim. The command still has
no retained entrypoint. Any saved binding/execution needs a separate instruction
and reviewed immutable identities; no automatic successor or wider search is enabled.
