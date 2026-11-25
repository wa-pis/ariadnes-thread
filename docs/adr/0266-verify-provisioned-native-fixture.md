# 0266 — Verify the provisioned native fixture once

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (user explicitly authorized three files and one fixed packet)
Implementation: exact provision, one manufactured native packet and independent audit pass
Scope / milestone: F17.3 / M3 manufactured native-helper qualification only
Base revision: `9dc1387b302a4000c2661b81183d6966a1a7492c` (clean before preparation)
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f173-provisioned-native-packet-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis)
Supersedes / Superseded by: none; preserve the build, both failed packets and source inventory

## Context and constraints

[ADR0265](0265-inventory-native-import-resources.md) pins the source-derived five
file minimum and a complete offline provisioning proposal. The user's next “да”
answers the concrete offer to prepare three missing station files and run one
fixed eleven-check packet. This authorizes that foreground action without
resuming the scheduler or adopting resources for a physical mission.

## Options considered

- Add files incrementally and probe imports: rejected; preserve the full frozen
  prerequisite set and the two earlier failures.
- Provision the three exact local files, verify all five, then execute one frozen
  manufactured packet: selected under the explicit instruction.

## Decision and rationale

Use a fresh <=600s preflight clock before native launch. Verify the unchanged
source/runner/kernel/helper, all five exact local payload identities and isolated
HOME, old clocks/ledgers, absence of the new output and unchanged scratch limit.
Precharge58535bytes in a new immutable record carrying forward496986960bytes,
then atomically complete the three-file station directory. New aggregate497045495
is below the unchanged2GiB ceiling. No installer/download/dependency change.
Use the exact local research-only payload profile; upstream2.4content authenticity
and parser compatibility are not inferred from package/version labels.

Reuse the qualified0264 controller/launcher/auditor, changing only new episode
paths/tag/output metadata. Require independent admission/control review **before**
launch. No new control algorithm or fake-test campaign. One exclusive packet
marker starts the standalone60s inclusive clock before controller/native import;
retain5s finalization reserve,64KiB parameters/64KiB logs/2MiB structured evidence,
exactly11external fixture calls and zero simulator/trajectory calls. Do not reset
old clocks or add another build/import attempt. Stop on drift, timeout or failure.

The unchanged two accepted/nine refused cases check scalar words, row/state/mass
association, signed zero, exported binary64 neighbours and compiled53/53/8 context. The
unchanged independent stdlib auditor checks saved literal outcomes without
repeating native calls; separate outer receipts retain fsynced inclusive time.
Preserve full or partial failure safely, then ADR/OpenSpec/CURRENT, appropriate
checks, one commit/push. Scheduler remains PAUSED.

## Consequences and revisit conditions

Even eleven passing checks qualify only manufactured map/helper plumbing under
this private binary/profile. Production owner lifecycle/mutation/concurrency,
lawful prior arithmetic, native carry, full source/core/ABI/FP proof and physical
F0 gates remain open. This does not adopt the kernel in operational space-nav or
establish a command pair,99%probability, mission safety or M3 completion.
Any failure consumes this packet without automatic retry/added data/changed caps.

## Evidence and verification

[Result](experiments/0266-native-fixture-result.json) and
[evidence archive](experiments/0266-native-fixture-evidence.zip) retain the native
packet, exact profiles/control deltas, precharge/admission/finalization, one
independent audit and preservation receipts. The archive contains27members/
74195uncompressed bytes (30873compressed), SHA256
`0ab6379d3ac65fbed79fda28db7d74152dfd4c9495c09bad9e9b6644d51b39d7`.
The final [documentary receipt](experiments/0266-doc-verification.json) records
protected project history/links/anchors/diff and strict validation.

- The three exact station files were staged and directory-renamed atomically;
  all five isolated files/131662bytes matched pinned local hashes. Precharge
  58535bytes carries the old496986960 forward to497045495, below2GiB, without
  altering the old closed ledger. Source/runner/kernel/helper/timer pins match.
- Both independent admission and static control reviews preceded the native
  marker. One review initially used an incomparable monotonic clock; that receipt
  and its static-only correction are retained. The parent separately measured
  nonnegative206.308s preflight (marker-based206.345s), within600s, and executed
  the launcher with the exact same host interpreter/clock. No timer reset.
- Exactly one packet returned0:4.858s process,4.908064s inclusive and4.908203s
  observed after stage fsync, within60s. Parameters2429B/packet9479B/log222B
  satisfy64KiB/2MiB/64KiB. Packet SHA256
  `38f3ec22c27b5f3fd6c9dbd6f4b92eeb83ef94fead02f9f0dca2f1991b6997d7`.
- The compiled context was actually observed as long-double digits53, double
  digits53 and long-double size8bytes. Forward/reverse rows match literal hour,
  state/mass words, signed negative zero and exported binary64 neighbours. All nine
  expected domain/schema/history/row-size/nonfinite-state refusals match. Scalar
  domain refusals exercise the shared predicate before Time construction; these
  are not malformed propagated native histories. No event-time reconstruction
  or native carry qualification is inferred from exported binary64 neighbours.
- The unchanged independent offline auditor ran exactly once (exit0), checking
  all11inputs/outcomes:2accepted/9expected refusals, exact bits/hex/association,
  pinned identities and recorded11visitor calls/0simulators/0trajectories.
  Counter claims are source/runner/outcome-bound, not independent native-process
  instrumentation. Its frozen artificial checks were reused, not rerun.
- The native log retains OpenMP warning179 about setting a temporary-file size.
  Isolation was not relaxed; these serial manufactured outcomes do not qualify
  threading/performance. The warning did not change the recorded case results.
- After the packet all71459operational paths/1646916124regular bytes match the
  original full manifest (11.501s check); isolated resource hashes and old four
  clock/ledger/profile pins match independently. Image detached, build preserved.

The old controller/launcher adaptation changes only episode paths/tag/output
metadata; qualified guard logic is unchanged. The old auditor is unchanged.
No new build/install/HTTP/SPICE query/simulator/integration, native retry or
operational-package adoption occurred. Project runtime/test code is unchanged;
full pytest/Ruff/CI were not repeated for this finite qualification evidence.

F17.3 completes only the manufactured helper/scalar packet under the private
binary/local-data profile. Historical failed F17.1 stays unchecked and preserved;
parent F17 is not closed because its production-owner route was not exercised.
Owner lifecycle/mutation/concurrency, prior arithmetic/carry, full ABI/FP/core-source
basis and all physical F0/command-pair/M3 obligations remain open. Automation stays
PAUSED; this consumed foreground packet authorizes no further native study.
