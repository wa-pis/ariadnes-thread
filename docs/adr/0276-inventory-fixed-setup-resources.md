# 0276 — Inventory fixed model-setup resources

Date: 2026-11-27 (Europe/Samara; raw UTC records begin on November26)
Decision status: accepted for bounded source/saved-only preparation
Implementation / verification: F18.10 scoped source inventory complete; independent source review PASS; no runtime qualification
Scope / milestone: M3 setup diagnostic preparation after consumed F18.9
Base revision: `2e831190a35cee5b0c3fee55f3352f24d7de0f70`, dev
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f1810-fixed-setup-resource-inventory-2026-11-27), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-qualify-actual-owner-readback-on-a-fixed-analytic-fixture)
Supersedes / Superseded by: none; preserves0275failure and consumed authority

## Context and constraints

The user resumes automation and continued checks after [ADR0275](0275-record-failed-never-run-setup.md).
The next useful check is a source/saved-only inventory for the fixed
`_native_factory('never-run', False)` path. The former five import resources did
not establish setup coverage. Preserve functions, inputs, settings, image,
kernels and old native600s preflight/60s45-10-5 profile. No new native attempt,
resource supplementation, download, integration or SPICE query belongs to this
inventory. The separate900s source clock includes independent review and detach.

## Options considered

- Repeat failed setup or add only its reported file immediately: rejected;
  this would neither identify the source path nor establish remaining resources.
- Trace the fixed path and required readers using existing local sources/payloads:
  selected; record unknown branches rather than claiming runtime completeness.
- Inventory all Tudat features or write another generic harness: outside scope.

## Decision and rationale

The missing EOP failure is **consistent with an eager import-side converter**,
not specifically body creation. Installed Python source follows
`dynamics -> environment_setup.gravity_field.sbdb_wrapper -> data.processTrk234
-> converters.radioBase`. The class attribute `RadioBase.time_scale_converter`
calls `default_time_scale_converter()` while the module is imported, before the
fixed factory reaches its empty Spacecraft body statements. Source anchors show
the binding's default EOPReader, default UT1 short-period correction files and
unconditional historicalDeltaT reader. This explains a viable source path, not
an observed native stack or a proven cause of the older0269failure.

The retained callgraph has44 exact source/hash/line anchors and40 edges.
The independently verified extra payloads are:

| Relative to earth_orientation/ | Bytes | Local SHA256 |
|---|---:|---|
| `eopc04_14_IAU2000.62-now.txt` | 3572052 | `cc838b27572e89ff6d36ee7cbeb6a8f104f1f8e59ddf769e8c93e6515276cd32` |
| `historicalDeltaT.txt` | 3627 | `4a2d068df1cdb5f39ac0e7efa04aafeea5be585afd1c9e2e4380cf8872e1f78e` |
| `utcLibrationAmplitudes.txt` | 120 | `43e945689ae30f7200d87df1adba1571d912671679ecd06ef27603c147f4bca7` |
| `utcLibrationFundamentalArgumentMultipliers.txt` | 319 | `901564789b3e7478d856dd9c0f37644d41810e8ef288039b59e7d52bf038c9c5` |
| `utcOceanTidesAmplitudes.txt` | 1136 | `e5a638ccddc614670804ee85d60e3c0a541ce40ad4758a71af5ce680aa615829` |
| `utcOceanTidesFundamentalArgumentMultipliers.txt` | 1633 | `eb2ae730afe18e42b75f201f087057e13a99d632f0217fbef9d520084ac3c863` |

All six are absent from the admitted image and available in the existing local
Tudat resource directory: **3,578,887B**. No payload is copied. The other seven
of13local Earth-orientation candidates are not selected by this inspected
converter route, which does not establish they are globally unused by Tudat.
Two Gaussian tables and three station maps remain the five earlier admitted
kernel-load static resources. `RadioBase.stationDict` calls a literal DSN
coordinate map and adds no file read through that call.

The fixed empty-body settings do not request standard Earth rotation, physical
ephemeris/gravity/atmosphere or thrust models. SimulatorFalse guards integration,
but constructor preparation happens before that guard; partial callback/native
counts in0275remain UNKNOWN. Lazy callback bodies and alternative polar-motion
readers are distinguished from the eager converter route. The inspected leap-
second wrapper calls compiled SOFA iauDat; no external .tls reader is established
for this route. These source statements do not prove linked-binary equivalence,
all third-party/transitive import effects or complete runtime resource closure.
Local hashes establish byte identity, not upstream authentication, parser validity,
data coverage or sufficiency for successful setup. No claim all six were read
in the failed0275attempt is made.

## Preparation and verification

Independent source review PASS at508.945825s. Read-only image detach completed
at557.625779s on the original900s source clock. An initial default-sandbox detach
was denied at538.356984s; its receipt is preserved. The authorized filesystem
escalation detached on the same clock, with no native/scientific retry.
All49source/test,10native,5resource and25old-ledger pins match. All71459protected
operational-prefix paths/1646916124regular-file bytes match their baseline.
No competing relevant process was found. New acquisition, resource copies,
provisions, project/runtime imports, tests, native calls, SPICE queries,
integrations, builds and dependency changes are each0.

Runtime code/tests/dependencies are unchanged. Successful [ADR0274](0274-qualify-artificial-owner-setup.md)
8063portable+413live passes/42unchanged archival skips and Ruff are retained,
without rerunning the same regression for this source/documentation stage.
Links, evidence syntax/digests, prior blobs, diff and strict OpenSpec are checked
separately in the final documentary receipt.

## Consequences and revisit conditions

Automation `ariadna-m3` is ACTIVE every5minutes under the user's resumed continued-
checks instruction. The next useful ordinary preparation is a concrete distinct
six-file supplementation/setup-test contract, reusing the qualified controls and
auditor, before any provisioning or new native observation. The archived proposal
pins exactly6files and unchanged limits: projected carried acquisition500624382B
under2GiB,11totalresourcefiles/3710549B. It is a proposal, not a provision or a run.
The new contract must identify isolated writes/readback, old data preservation,
one new observation identity and stop-on-first-failure behavior. Do not repeat
a successful full suite or create another harness without a changed behavior.
Pause only when actual access/data/action or a scientific-contract choice needs
the user; routine reversible preparation does not itself require confirmation.

F18.9 remains consumed/unqualified and is not replayed or relabeled successful.
F17/F17.1/F18.3, completed-owner/carry/concurrency/ABI-FP/prior arithmetic and
physicalF0/M3/99-percent/safety gates remain open. This source result establishes
neither an admissible command pair nor a flight-safety or physical accuracy claim.

## Evidence and verification

[Result](experiments/0276-setup-resource-inventory-result.json) and
[immutable raw evidence](experiments/0276-setup-resource-inventory-evidence.zip)
retain the original clock, local inventory, source callgraph/anchors, independent
review, proposed six-file list, operational preservation, both filesystem detach
receipts and ACTIVE scheduler readback. The raw archive contains12members.
[Final documentary verification](experiments/0276-doc-verification.json) records
local links/anchors, protected prior blobs, artifact identities, independent
review and strict validation. No new runtime or scientific result is claimed.
