# Current State

Updated: 2026-11-25. Keep under60lines; durable evidence in ADRs.

## Current result
[ADR0265](docs/adr/0265-inventory-native-import-resources.md): complete bounded
source inventory of the helper-import route,494.082s including independent review.
Reviewed1054core source/header paths and all81binding units; no concrete omission
found from five eager files. Local hashes pinned,131662bytes total:
quadrature/gaussianNodes.txt + gaussianWeights.txt (already isolated),
station_locations/glo.sit + glo.vel + ns_codes.dat (missing,58535bytes combined).
[Manifest](docs/adr/experiments/0265-import-resource-manifest.json)/
[source ZIP](docs/adr/experiments/0265-import-resource-evidence.zip) retain call
chains,81binding hashes, package metadata, lazy exclusions and independent review.
Package installation does not populate HOME/.tudat/resource automatically here;
retained post-link download script was inspected, never executed.
Source-derived minimum is not proof of all binary accesses or successful loading.
Local payload hashes do not authenticate upstream2.4contents/native parsing.
No resource copies/imports/builds/HTTP/SPICE/simulator/integration occurred;
image was mounted read-only and detached. Project code/tests unchanged; no full
pytest/Ruff/CI repeated. F17.2 completes documentation, not native qualification.

## Next action and scheduler
ariadna-m3 remains PAUSED. User authorized the inventory only.
A complete offline provisioning preflight is now concrete in ADR0265/manifest:
verify all five exact local files, precharge58535additional bytes in a new record
carrying forward496986960old acquisition bytes, then stage only three station files
and verify the full isolated set. Projected497045495B stays below unchanged2GiB.
No whole resource-tree copy, installer/download, operational adoption or new build.
Explicit provisioning authority and a separate finite packet remain required;
no piecemeal import retries, changed caps or resetting old clocks.
[ADR0264](docs/adr/0264-qualify-original-row-fixture-packet.md) retains the consumed
packet: rc-6/missingglo.sit,0.294s process/0.341545s inclusive, no result/context/
visitor outcomes. Zero calls are source-order inference. Independent failure audit
passes; all71459operational paths matched at that stage. F17/F17.1 stay unchecked.
[ADR0263](docs/adr/0263-authorize-isolated-native-build.md) preserves the single
81-TU build422.086s and first failed import3.863s. Private variant04f7af4c… remains
in /private/tmp/ariadna-f17-0263 image, no operational-package adoption.

## Physical goal remains open
[ADR0247](docs/adr/0247-formulate-coupled-moon-mars-problem.md) retains fixed F0
states/epochs/planes/phases, hardware and six finite-burn controls.
No altered targets, admissible pair,99% probability, physical closure or safety claim.
Binary/source/ABI/FP, owner/concurrency, lawful prior arithmetic, carry/full-force
seed, derivatives/guards and independent endpoint bounds remain unqualified.
[ADR0246](docs/adr/0246-record-bounded-retained-inconclusive.md): P6 consumed,
13points audited/inconclusive/no witness; no historical-study replay.
No strictM3/task3.9, M4–M6/ML/UI/publication authorization.
Preserve history/moon_to_mars.py; dev only, commit/push checked stages to origin/dev.
