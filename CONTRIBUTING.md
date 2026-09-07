# Contributing

Read `AGENTS.md` and `openspec/ROADMAP.md` before changing behavior. This is a
ground-based engineering prototype, not flight-qualified software.

## Environment and checks

Conda is authoritative for Python and all scientific/native dependencies.
Install Miniforge, then follow the environment setup in `README.md`.
`environment.yml` pins direct dependencies; it is not a complete platform-specific
lock file. Do not generate a competing uv or pip dependency lock.

Run `make setup` to create or refresh the environment and editable installation.
Run `make check` before committing; it runs Ruff and the complete pytest suite.
Override `CONDA` or `ENV` when necessary, for example `make CONDA=/path/to/conda check`.
Without Make, use:

```sh
conda run -n space-nav ruff check src tests
conda run -n space-nav python -m pytest -q
```

For focused development, pass a test path to pytest. A focused run does not
replace the complete suite. CI installs the same environment on Ubuntu, checks
real TudatPy/SPICE kernel loading and the installed CLI, then runs all tests.
Investigate skipped scientific tests: a missing dependency is not evidence that
a numerical contract passes. CI retains the JUnit report and the resolved Conda package list for 14 days.

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
