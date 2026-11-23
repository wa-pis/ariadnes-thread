# 0242 — Complete P3 regression qualification without a retained search

Date: 2026-11-24 (Europe/Samara; initial runs began on 2026-11-23)
Decision status: accepted
Implementation: minimal runtime/test repairs complete; P3 qualification remains open pending repaired CI
Verification: 412 live tests passed before repair; first repair passes 151 focused/6964 portable; latest repair passes 152 focused/6965 portable; current-source CI pending
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

## Follow-up — executable native mappings only

The [second CI](https://github.com/wa-pis/ariadnes-thread/actions/runs/45256674267)
on clean `390edfc` passes 6960 portable tests, with only three actual artificial
producer cases failing before a report exists; 42 archival and 1 platform skip,
zero setup errors. Its live lane does not execute. The clock/canonical-path
failures no longer occur. Preserve its [failure inventory](experiments/0242-ci-second-failure.json).
That invocation version did not expose the exact rejected filename; a specific
locale filename is therefore not claimed as observed.

Source review and a synthetic maps fixture identify a separate defect: Linux
maps includes readonly data as well as executable library segments. Treating all
mapped files as native libraries can produce a profile that its next worker
rejects before output creation. Restrict native image entries to executable
mappings; preserve full raw-map charging, exact current-process access, root/type/
hash checks and every time/byte cap. The fixture keeps executable Python/_hashlib
and excludes readonly stdlib, locale and unrelated data rows.

Bound early worker diagnostics to 1024 characters plus newline; the parent relays
only the last 4096 captured stderr bytes after decoding. These are operational
errors, not a new numerical evidence channel or permission. Fault tests now
require the specific expected rejection and distinguish early invalid scope/native
images from complete invalid scientific reports; any unrelated abort cannot pass.
The [latest focused log](experiments/0242-linux-focused-tests.log) records 152 passes
in 11.78 s. Independent review finds no blocking issue.

The [new binding record](experiments/0242-linux-profile-repair.json) freezes changed
runtime/invocation/test source identities. Installed-runtime tables are exactly
identical to the already retained producer/audit tables, so reuse those tables
without copying or changing historical records; their old top-level source maps
remain historical. The [latest full portable lane](experiments/0242-linux-portable-tests.log)
passes 6965 tests in 208.60 s (42 archival skips, 412 live deselections), on a
frozen 1339-file checkout. Ruff, independent review and strict OpenSpec pass.
Current-source CI remains pending; P3 is not checked complete yet.

## Consequences and revisit conditions

This closes preparation only after its required regressions succeed. It does not
produce a real analytical witness, continuous refusal, executable pair, adopted
Mars target, physical join, M3 completion or safety claim. The command still has
no retained entrypoint. Any saved binding/execution needs a separate instruction
and reviewed immutable identities; no automatic successor or wider search is enabled.
