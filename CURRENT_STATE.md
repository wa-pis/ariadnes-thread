# Current State

Updated: 2026-11-27. Keep under60lines; durable evidence in ADRs.

## Current result
[ADR0275](docs/adr/0275-record-failed-never-run-setup.md) retains the once-only
F18.9 failure. Permission CONSUMED, setup UNQUALIFIED, no retry. Import/context
checks reached; four617Bmarkers stop at factory-enter. Childexit2 reports missing
Tudat resource earth_orientation/eopc04_14_IAU2000.62-now.txt, confirmed absent.
No factory-return/visitor/complete/report/counter snapshot. Actual native partial
counts UNKNOWN; no explicit integration or visitor reached. Observed6.641288042s
<60s45/10/5; independent saved-only audit PASS_ACCOUNTED_FAILURE, full success REJECT.
Admission443.030s/consumption450.258s on original600s clock;12079structured/213logB.
All49source/test/10native/5resource/25old-ledger pins and71459operational paths
unchanged; groups gone, image detached, acquisition0. Initial temporary setup/
collector findings and corrected artificial checks preserved. Runtime code unchanged.
[Result](docs/adr/experiments/0275-never-run-setup-result.json).

## Next action and scheduler
ariadna-m3 PAUSED at terminal result, before a new user decision.
Propose source/saved-only inventory of all model-setup resource dependencies.
No new inventory/provision/download/native run authorized yet; do not replay
F18.9/F18.3/F18.6/0266 or supplement resources/change profile automatically.
[ADR0274](docs/adr/0274-qualify-artificial-owner-setup.md): artificial F18.8 qualified,
215new cases in8063portable+413live passes/42unchanged archival skips, Ruff/review/
strict PASS. Successful runtime tests not repeated on unchanged code for0275.
Same warning in0269 and0272 does not establish historical cause/counts.

## Physical goal remains open
[ADR0247](docs/adr/0247-formulate-coupled-moon-mars-problem.md): fixed F0 states,
epochs/planes/phases, hardware and six finite-burn controls.
F17/F17.1/F18.3/F18.9, completed-owner/carry/concurrency/core-source ABI-FP/prior
arithmetic/full-force seed/derivatives/guards/endpoint bounds remain open.
No admissible pair,99%probability, physical closure or safety claim.
No strictM3/task3.9,M4–M6/ML/UI/publication authority or historical study replay.
Preserve history/moon_to_mars.py; dev only, commit/push checked stages origin/dev.
