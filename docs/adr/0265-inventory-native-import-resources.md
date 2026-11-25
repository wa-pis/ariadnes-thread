# 0265 — Inventory the native import resources before another packet

Date: 2026-11-25 (Europe/Samara)
Decision status: accepted (user authorized this source-only inventory)
Implementation: source inventory complete; provisioning/native qualification not started
Scope / milestone: F17.2 / M3 isolated native-helper preparation
Base revision: `71d92362244b5953bd59431eaa2f3b44fd276b2b` (clean before preparation)
Related OpenSpec: [design](../../openspec/changes/refine-physical-trajectory/design.md#f172-complete-import-resource-inventory-2026-11-25), [tasks](../../openspec/changes/refine-physical-trajectory/tasks.md), [requirement](../../openspec/changes/refine-physical-trajectory/specs/research-trajectory-experiment/spec.md#requirement-keep-split-time-enclosures-conditional-on-the-conversion-basis)
Supersedes / Superseded by: none; preserve both prior import failures and the one build

## Context and constraints

[ADR0264](0264-qualify-original-row-fixture-packet.md) consumed the one resumed
packet at native import. The user accepted the proposal to first prepare a full
minimal list of resources, without further imports/builds/calculations. This
preparation does not authorize copying resources or another fixture packet.
The existing compiled artifact/runner and physical F0 gates remain unchanged.

## Options considered

- Add the next missing file and try importing again: rejected; it repeats an
  incomplete prerequisite check and consumes another native attempt.
- Copy the entire existing resource tree: rejected; the prior metadata proposal
  exceeds the unchanged2GiB acquisition ceiling and includes unused mission data.
- Trace eager initialization in the retained core, all81binding translation units
  and package import path, then pin only the complete source-derived minimal
  resource set: selected. Preserve any unresolved binary/runtime coverage premise.

## Decision and rationale

One source-review episode is bounded to900s including independent source review.
Mount the retained image read-only; inspect only retained sources/headers, binding
and package metadata. Hash at most32selected existing local payloads/16MiB;
hashes establish local identity, not upstream release authentication or data
adoption. No resource payload copies, HTTP, dependency change, compiler, module
import, native calls, SPICE, simulator construction, integration or fixture run.
Source-derived coverage and observed successful loading remain separate claims.

The deliverable is one pinned file/size/hash manifest with eager call chains,
explicit lazy exclusions/unknowns and an offline all-prerequisites provisioning
proposal. Do not run the installer or reset old clocks. Any later provisioning
profile and packet require their own explicit authority; automation stays PAUSED.

## Consequences and revisit conditions

This should remove file-by-file retries while retaining the small isolated build.
A source-derived list cannot establish source-to-binary equivalence or a passing
native import. Missing provenance or an additional loader-time dependency requires
an explicit inventory correction, never a hidden import retry. F17/F17.1 and all
owner/carry/prior-arithmetic/physical gates remain open.

## Evidence and verification

The [manifest](experiments/0265-import-resource-manifest.json) records the exact
local hashes, source call chains, exclusions and proposed offline sequence.
The [source archive](experiments/0265-import-resource-evidence.zip) retains27members/
1160711uncompressed bytes (133228compressed), SHA256
`f217d61f88fc4c2204cd642181ae2cdbfe27231fbd37737f3bf81f73cd001cc5`.
Source preparation including independent review ended at494.082s, within900s.
The final [documentary receipt](experiments/0265-doc-verification.json) records
links/anchors, protected history, diff and strict validation.

The reviewed helper-import source route has this five-file candidate minimum:

| Relative file under `HOME/.tudat/resource` | Bytes | Isolated state |
|---|---:|---|
| `quadrature/gaussianNodes.txt` | 36021 | Already present and pinned |
| `quadrature/gaussianWeights.txt` | 37106 | Already present and pinned |
| `station_locations/glo.sit` | 20865 | Missing; local bytes pinned only |
| `station_locations/glo.vel` | 17756 | Missing; local bytes pinned only |
| `station_locations/ns_codes.dat` | 19914 | Missing; local bytes pinned only |

Total131662bytes; only58535additional bytes would be needed. No payload was
copied. A future exact three-file provision would bring the preserved aggregate
acquisition from496986960 to497045495bytes, within the unchanged2GiB ceiling.
Use a new explicit precharge receipt carrying forward the old aggregate; never
reset the closed old ledger/build clock. Preflight the complete five-file set,
not one missing file per import. No whole-tree copy, installer or dependency is
needed for this proposed local fixture-only resource profile.

The two quadrature files are read by namespace-static node/weight constructors
in `gaussianQuadrature.h`. The three station files are read by namespace-static
maps in `defaultBodies.cpp`; three eager observation-binding defaults reuse those
maps. Independent source review found no concrete additional eager resource:
1054core source/header paths/14296818bytes were searched, all81binding units
were inspected/hashed, and seven relevant installed headers match retained source.
The minimal Python package initializer only declares its version; the frozen
runner imports the monolithic kernel directly.

A default time-converter factory would read six extra Earth-orientation files,
including `historicalDeltaT.txt`. That factory is registered by function pointer;
its former global converter is commented out. These files are excluded for this
helper-import route, along with call-time SPICE, atmosphere/space-weather,
gravity/deformation/VMF3 and approximate-planet datasets. This exclusion does not
apply to later model or trajectory calculations.

The preparation error was treating an installed resource package as a populated
runtime data directory. Its metadata lists11installer/header/config/test paths,
not payload data; its retained post-link script would fetch a full GitHub release
to `HOME/.tudat`, while `resource.h` resolves that HOME-based path. The script was
read, not executed. Existing local payload hashes do not authenticate upstream
v2.4contents or prove native-parser compatibility. The proposed profile explicitly
uses pinned existing local bytes for manufactured tests only.

The image was mounted read-only and detached after source capture. Source/kernel/
runner/helper pins and all81binding hashes matched; no new source/binary changes,
resource copies, native imports/tests/builds, HTTP, SPICE, simulator or integration.
Project runtime/test code is unchanged, so full pytest/Ruff/CI were not repeated.

This is a complete bounded source inventory of the reviewed eager route, **not**
a proof of every linked-binary access or an observed successful import. Precompiled
core/source equivalence, ABI/FP, native parsing/context/helper outcomes, owner/carry/
prior-arithmetic and physical F0 gates remain unresolved. F17.2 records documentary
completion only; F17/F17.1 remain unchecked, automation PAUSED. The exact proposed
three-file provisioning and any later eleven-call packet require explicit authority;
this inventory authorizes neither.
