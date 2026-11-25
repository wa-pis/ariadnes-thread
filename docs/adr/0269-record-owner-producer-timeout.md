# 0269 — Record the bounded actual-owner producer timeout

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (user explicitly authorized exactly one F18.3 attempt)
Implementation / verification: one packet consumed; producer deadline failure; independent failure accounting PASS; native-owner/numerical qualification unavailable
Scope / milestone: F18.3 / M3 synthetic serial-owner qualification only
Base revision: `a6e89e3da46c4a05525f3cd72ef21347f0d0e5bf`, clean dev before preflight; runtime/tests unchanged
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f183-consumed-producer-timeout-2026-11-25), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md)
Supersedes / Superseded by: none; preserves ADR0267/0268 and all consumed episodes

## Context and constraints

The user explicitly requested one [ADR0267](0267-design-actual-owner-endpoint-qualification.md)
packet after kernel/resource/limit admission, independent saved-result audit,
ADR/OpenSpec and commit/push. [ADR0268](0268-qualify-artificial-owner-runner.md)
already qualified the private producer/auditor/controller and required regressions.
No retry, new data, build, dependencies, changed inputs/gates/limits, SPICE study
or physical trajectory is authorized. Automation remains PAUSED.

## Options considered

- Reuse the qualified private controller with a fixed source-bootstrap/PGID shim
  and externally supervised caller: selected, after artificial success/timeout
  and live/dead-leader cleanup checks plus independent admission/control review.
- Repeat or extend the native attempt after timeout: excluded. Preserve the
  consumed failure and unknown counters; a further bounded plan needs separate
  authority.

## Decision and rationale

Mount the retained image read-only. Verify the exact private kernel04f7af4c…,
10old native/source/control pins, five131662B resources,10old clocks/ledgers and
all9qualified runtime/test/reused source hashes. Both71459-path operational
prefix inventories match the original baseline. No acquisitions or provisioning;
aggregate497045495B and the original closed ledgers remain unchanged. Resource
pins establish local identity; upstream2.4content authentication remains unknown.

Seal the fixed profile and external orchestration. A private interpreter uses
only explicit repo/src bootstrap and isolated retained HOME/resources; sandbox
rules deny network, operational-prefix reads and writes outside the exclusive
output directory. The private entry records its own and the cold parent's
process groups before project/native imports. The caller inherits one60s clock,
bounds launcher communication and always kills launcher and recorded native
groups, including dead leaders. Qualified controller code and45/10/5 phases remain
unchanged. This assumes responsive OS clock/kill/filesystem; no arbitrary-hostile
worker/OS-failure or concurrency proof is claimed.

The same pinned operational Python3.12 clock measures positive preflight
517.983354s admission,526.427893s caller start and526.507489s consumed marker,
all below600s. Independent static admission and controls reviews precede launch.
The exclusive marker consumes one fixed3factory/2analytic-arc/8visitor/
100000acceleration-callback profile; those are caps and intended calls, not
observed native counts. Callback caps are not a count of all native RHS.

## Consequences and revisit conditions

The producer exceeds its original45s cutoff. Final caller observation after
finalization fsync is45.035706542s, within60s; all processes are cleaned up.
The producer output is empty, parent mode is null, completed-worker list is empty
and no numerical-audit file exists. Actual factory/integration/visitor/callback
counts and endpoint/lifecycle outcomes are **unknown**, not zero. The independent
numerical auditor was not launched: there are no saved endpoint words to audit.
Independent saved-only failure/control accounting passes; it does not substitute
for numerical qualification.

The only stderr is64bytes of OpenMP warning179 about a `/tmp` file. It does not
identify where or why the producer stalled. No import-versus-simulation diagnosis,
causal conclusion, new probe, increased limit or retry follows from this warning.
F18.3 remains unchecked. F17/F17.1, actual-owner, concurrency, native carrier/carry,
prior arithmetic, core/source/ABI/FP and every physicalF0/M3 gate remain open.
No admissible commands,99%probability or mission-safety result is claimed.
The next choice is a separately bounded diagnosis plan from retained facts;
execution authority for this packet is exhausted.

## Evidence and verification

[Result](experiments/0269-owner-timeout-result.json) and
[immutable evidence archive](experiments/0269-owner-timeout-evidence.zip) retain
profiles/pins, artificial orchestration checks, both prelaunch reviews, raw partial
outputs, distinct persisted-prefinal and returned post-fsync observations,
independent failure/control audits, both preservation inventories, process cleanup
and read-only detach receipts. Archive: 44members/90627expanded bytes/42339compressed bytes, SHA256 `c3c8cf46964ae93b9816074919d0c0f5e25083aa08ab85fe9724fb666240ed45`.
The validation archive is separate from per-packet budgets; no limit is expanded.
Packet plus caller/tool structured evidence7485B<2MiB; combined logs64B<64KiB.

All10old timers/ledgers,10native pins and five resource files match after the
packet; both71459operational paths/1646916124regular bytes match before/after.
Recorded groups contain no processes; read-only image detached and preserved.
Runtime/tests remain byte-for-byte at the verified base; pytest/Ruff/CI were not
repeated for this evidence-only stage. Reuse0268's194focused cases included in
7724portable+413live passes/42opt-in archival skips and full Ruff. Artificial
external-control checks and independent reviews are retained separately; no
additional scientific/native qualification is inferred from them.
[Final documentary verification](experiments/0269-doc-verification.json) records
prior project-byte preservation, links/anchors, hashes/syntax, diff and strict
OpenSpec checks plus final independent documentary review.
