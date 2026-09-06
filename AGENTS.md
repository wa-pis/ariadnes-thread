# Project Working Rules

## Mission and scope

- Build Ariadna, an open, extensible ground-based space-navigation platform with an open specification, reference implementation, and interoperability tests. Moon-to-Mars is the first reference use case; see `openspec/VISION.md`. Do not represent it as onboard or flight-qualified software, an adopted industry standard, or a certified CCSDS implementation.
- Follow the linear milestones in `openspec/ROADMAP.md`. Keep at most one active OpenSpec change and do not implement later-milestone behavior early.
- Explicit user instructions override this file. Otherwise, make reasonable reversible assumptions and continue until the active task is complete.

## Scientific contract

- Use SI internally, TDB seconds since J2000, SSB origin, and J2000 orientation.
- Label units, time scale, origin, and orientation wherever state data crosses a public boundary.
- Use TudatPy/SPICE as the authoritative source for ephemerides and gravitational parameters. Missing kernels, unsupported bodies, or uncovered epochs must fail clearly; never fabricate circular-orbit or stale-data fallbacks.
- Require launch-window dates and spacecraft physical parameters explicitly. Do not add hidden scientific defaults.
- Preserve deterministic outputs for fixed scenarios and pinned dependencies. Treat changes to kernels, constants, tolerances, reference values, or scientific baselines as reviewable changes and explain their numerical impact.

## OpenSpec workflow

- Write OpenSpec artifacts in English using the standard `proposal.md -> specs -> design.md -> tasks.md` workflow.
- Every requirement must include at least one measurable `WHEN`/`THEN` scenario. Every implementation task must name its verification.
- Fully specify and implement only the current roadmap milestone.
- Before implementation completion, run focused checks, the complete test suite, and `openspec validate <change> --strict`.
- Before archival, sync delta specs to main specs, rerun strict validation, archive the change, and update `openspec/ROADMAP.md`.

## Implementation

- Prefer the standard library and existing dependencies. Add a dependency only when the active milestone needs it, then pin and verify it.
- Keep Conda authoritative for Python and all native or scientific dependencies. Use the Conda-installed `uv` only for editable installs or pure-Python package operations inside the active environment; do not use `uv lock`, `uv sync`, `uv run`, or `uv venv` in this repository because they cannot reproduce Conda-only TudatPy.
- Install or refresh the editable package with `conda run -n space-nav uv pip install --no-deps --no-build-isolation --editable .` after environment creation or package-metadata changes.
- Keep public APIs and CLI behavior backward compatible unless an accepted OpenSpec change explicitly revises them.
- Keep `moon_to_mars.py` byte-for-byte unchanged and never import it from `space_nav`.
- Keep changes scoped. Preserve unrelated user work and avoid speculative abstractions or future-milestone scaffolding.
- Parallelize only independent work; give agents non-overlapping ownership and review integrated results.

## Python code requirements

- Target Python 3.12.14 and the pinned Conda environment in `environment.yml`; keep production modules under `src/space_nav` and tests under `tests/test_*.py`.
- Follow PEP 8 and the existing naming and import style. Do not reformat unrelated code. Give public APIs concise docstrings that state scientific conventions where relevant.
- Give every new or changed function, method, and dataclass field explicit type annotations. Use `Any` only at untyped input, serialization, or third-party boundaries, validate it immediately, and keep each `# type: ignore[...]` narrow and justified.
- Model public scientific values as immutable `@dataclass(frozen=True, slots=True)` records. Enforce invariants at construction, reject booleans where numbers are expected, and reject NaN or infinity before computation or serialization.
- Encode physical units in scientific names, such as `*_m`, `*_m_s`, `*_kg`, `*_rad`, and `*_tdb_s`. Convert once at input boundaries and never silently mix units, frames, origins, orientations, or time scales.
- Keep domain modules free of printing and process exits; only `cli.py` renders output and maps expected user errors to exit codes. Raise project-specific errors with field, body, epoch, or candidate context and chain the original exception.
- Catch broad `Exception` only directly around untyped TudatPy/SPICE boundaries that must be translated into domain errors. Never use a bare `except` or silently substitute scientific data.
- Keep TudatPy/SPICE imports and kernel loading lazy so `import space_nav`, CLI help, and scenario validation remain lightweight and deterministic.
- Make results reproducible for identical normalized inputs and the pinned environment: use stable ordering and identifiers, explicit seeds, and injectable clocks or scientific adapters only when tests require them.
- Every behavioral change requires pytest coverage for its success path and relevant boundary or error path. Every new scientific formula or adapter requires an independent oracle, analytic invariant, or direct TudatPy/SPICE parity test with an explicit tolerance and physical units; never loosen a tolerance only to make a test pass.

## Verification

- Run focused tests while iterating and `conda run -n space-nav python -m pytest -q` before completing implementation work.
- Use real SPICE/TudatPy parity checks for scientific boundaries and pure injected tests for deterministic error paths.
- Do not mark an OpenSpec task complete until its stated check passes.
- Report numerical tolerances, scientific limitations, test results, and any unverified assumptions.

## Git

- Work on `dev` unless the user specifies another branch.
- Use small logical Conventional Commits. Commit completed units after checks pass.
- Never commit secrets, caches, virtual environments, editable-install metadata, or generated build artifacts.
- Do not push, rewrite history, delete branches, or change remotes unless the user explicitly asks.
- Leave the working tree clean at handoff, or clearly identify remaining user-owned changes.
