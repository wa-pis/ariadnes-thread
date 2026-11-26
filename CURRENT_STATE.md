# Current State

Updated: 2026-11-27. Keep under60lines; durable evidence in ADRs.

## Current result
[ADR0278](docs/adr/0278-qualify-artificial-provision-admission.md): F18.12 temporary
fixed-six provision/admission qualified artificially:94/94, no failures/errors/skips,
observed post-fsync1.142126958s<120s. Full newfakevolume3578887B/exact11fakefiles;
20982B invocation evidence;171660B expanded archive+7515B result<2MiB.
Independent code/reuse review PASS; initial proof/durability findings fixed before
qualification, retained. Four runtime controls byte-identical; three outer paths
namespace-only. No package/test/dependency change; prior8476passes/Ruff retained.
[Result](docs/adr/experiments/0278-artificial-provision-admission-result.json).

## Next action and scheduler
ariadna-m3 ACTIVE every5minutes; user requested continued tests2026-11-27.
Next: separately record concrete F18.13 execution/admission decision and prepare
minimal final outer gate binding observed admission return to once-only dispatch.
F18.12 disk candidates stay pending, never authorize launch alone. Nativepositive/
actualROidentity/final livegate unexercised; no actual provision/native admission.
[ADR0277](docs/adr/0277-design-supplemented-setup-test.md): exact6localfiles, exclusive
precharge/no-replace publication, exact11file/ROremount/fresh600s preflight;
unchanged env/code/kernel/60s45-10-5 caps. Real execution needs independent admission.
No realresourcepayload reads/copies/mount/native/SPICE/integration in F18.12.
[ADR0276](docs/adr/0276-inventory-fixed-setup-resources.md): six source-visible local
files3578887B absent image; local identity/source reasoning only, no runtime proof.
[ADR0275](docs/adr/0275-record-failed-never-run-setup.md): F18.9 CONSUMED/UNQUALIFIED,
4markers/factory-enter/childexit2/missingEOP,6.641288042s<60, partialcounts UNKNOWN;
failure accounting audited/fullsuccess REJECT. No replay or0269cause claim.
Image remains unmounted. Old evidence/moon_to_mars.py unchanged.

## Physical goal remains open
[ADR0247](docs/adr/0247-formulate-coupled-moon-mars-problem.md): fixed F0 states,
epochs/planes/phases, hardware and six finite-burn controls.
F17/F17.1/F18.3/F18.9/completed-owner/carry/concurrency/core-source ABI-FP/prior
arithmetic/full-force seed/derivatives/guards/endpoint bounds remain open.
No admissible pair,99%probability, physical closure or safety claim.
No strictM3/task3.9,M4–M6/ML/UI/publication authority or historical study replay.
Preserve history; dev only, commit/push checked stages origin/dev.
