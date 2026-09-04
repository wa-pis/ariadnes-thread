# Project Working Rules

## Mission and scope

- Build a ground-based engineering planner for Moon-to-Mars missions. Do not represent it as onboard or flight-qualified software.
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

- Use Python 3.11 and the pinned Conda environment in `environment.yml`.
- Prefer the standard library and existing dependencies. Add a dependency only when the active milestone needs it, then pin and verify it.
- Keep public APIs and CLI behavior backward compatible unless an accepted OpenSpec change explicitly revises them.
- Keep `moon_to_mars.py` byte-for-byte unchanged and never import it from `space_nav`.
- Keep changes scoped. Preserve unrelated user work and avoid speculative abstractions or future-milestone scaffolding.
- Parallelize only independent work; give agents non-overlapping ownership and review integrated results.

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
