# Contributing

Read `AGENTS.md` and `openspec/ROADMAP.md` before changing behavior. This is a
ground-based engineering prototype, not flight-qualified software.

## Environment and checks

Conda is authoritative for Python and all scientific/native dependencies.
Install Miniforge, then follow the environment setup in `README.md`.
`environment.yml` pins direct dependencies; it is not a complete platform-specific
lock file. Do not generate a competing uv or pip dependency lock.

Run `make setup` to create or refresh the environment and editable installation.
Run `make check` before committing. It runs Ruff and both required regression
lanes, using the same pytest options as CI:

```sh
make test-unit     # portable tests, including saved-data arithmetic; no live native access
make test-live     # existing TudatPy/SPICE and native-resource regression
make test-archive  # opt-in exact replay in its historical environment and checkout
```

Override `CONDA` or `ENV` when necessary, for example `make CONDA=/path/to/conda check`.
Without Make, use the pinned environment:

```sh
conda run -n space-nav ruff check src tests
conda run -n space-nav python -m pytest -q -ra --offline
conda run -n space-nav python -m pytest -q -ra -m live
```

The two required lanes together cover all non-archive tests. Plain `pytest -q`
applies no live exclusion and skips `archive` checks by default; existing
platform/dependency skips still apply. Archive
checks authenticate historical machine/build and protected-checkout identities or
require exact old floating-point replay. Use `--run-archive -m archive` in the
matching historical environment and checkout; this maintenance checkout is not
claimed to satisfy those old identities.
They must not be relabeled as passing on another operating system or silently
weakened to make a build green. Portable saved-data validators remain in the
required suite; reading a historical file alone does not make a test archival.

`live` marks existing tests that need TudatPy/SPICE, CSPICE or native resources.
`--offline` excludes them before execution and fails unexpected in-process native
imports/loads instead of silently skipping unclassified tests. This guard is not
a sandbox for arbitrary isolated Python child processes; classify subprocess tests
explicitly. The maintained test policy replaces archival ad-hoc skip scripts.

For focused development, pass a test path to pytest. A focused run does not replace
the required lanes. Test exclusivity on temporary paths and use injected clocks
for artificial deadline checks; repository output history and test order must not
determine whether ordinary regression passes. CI installs the pinned environment
on Ubuntu, checks real TudatPy/SPICE kernel loading and the installed CLI, and runs
both required lanes. It retains separate JUnit reports and the resolved Conda
package list for 14 days. A skipped archive test is not a verified scientific result.

Ruff checks syntax, undefined names, unused imports, and related basic errors.
EditorConfig establishes whitespace conventions. Keep formatting changes limited
to touched code; `moon_to_mars.py` is excluded and must remain byte-for-byte intact.
Static type checking and automatic whole-repository formatting are not enforced.

## Changes and review

Use `dev` unless the user specifies another branch. Make small Conventional
Commits (for example `ci: run the pinned scientific test suite`). Do not push
without explicit authorization. Submit a pull request with the problem, behavior,
and actual verification results; use the repository PR template.

Behavior changes follow the active OpenSpec milestone. Keep at most one active
change and run `openspec validate <change> --strict` before marking it complete.
Repository tooling and documentation changes do not advance scientific milestones
or complete their tasks. Do not modify scientific baselines, tolerances, kernels,
or constants merely to get a green check.

Dependency upgrades must update compatible pins together and run the scientific
parity tests. Explain any numerical impact. Dependabot proposes GitHub Actions
updates weekly; maintain Conda and build-tool pins manually. Actions are pinned
to commit SHAs and CI has read-only repository permissions.

## Maintainer settings

After CI has run successfully on GitHub, configure a branch ruleset for `main`
requiring pull requests and the `Python quality and scientific tests` status check,
blocking force pushes and branch deletion. Require an independent review when
another maintainer is available. These server-side settings are not installed by
committing this repository configuration.
