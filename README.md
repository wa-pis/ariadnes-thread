# Ariadna — Open Space Navigation Platform

Ariadna is being developed as an open, extensible ground-based space-navigation
platform: an open specification, a reference implementation, and interoperability
tests. Moon-to-Mars mission planning is the first reference use case, not the
limit of the product's intended scope.

The current implementation is an engineering prototype, not onboard or
flight-qualified software, an adopted industry standard, or a certified CCSDS
implementation. Python, TudatPy, and SPICE remain the implementation stack;
`space_nav` and `space-nav` retain their existing names and interfaces.

See the [product vision](openspec/VISION.md) for the contract and interoperability
direction, and the [roadmap](openspec/ROADMAP.md) for implemented versus planned
capabilities. A narrow research OEM exchange is available in the local explorer;
general CCSDS interoperability and interchangeable numerical backends remain goals.

## Local Streamlit explorer

After installing the environment below, run from this repository:

```sh
conda run -n space-nav python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501, explicitly load the example, edit parameters, and
calculate. Select a candidate and move the time slider. Changing input clears
old results. The original example has an ideal propellant shortfall: this is
shown as a warning, not hidden by choosing another spacecraft.

For the positive research example, choose **С резервом 50 кг**, click
**Загрузить пример**, then **Рассчитать перелёт**. After selecting a candidate,
use **Скачать результат JSON** and **Скачать траекторию OEM** below the plot.
JSON binds the actual normalized inputs, selected coast, scientific limitations,
50 kg reserve accounting, source/kernel provenance and OEM hash. The OEM carries
the same 121 coast nodes in km/km/s with TDB calendar tags. Every node must pass
an independently implemented decoder before either download appears. Its gates
are 1 microsecond / 1 mm / 1e-9 m/s for serialization only, not trajectory accuracy.

The profile explicitly uses unregistered `ORIGINATOR=ARIADNA`; it is research-only
and claims no full CCSDS conformity or operational safety. A coast that lacks the
reserve remains `unqualified` even if its file decoding passes. Unsupported
resources/frames or failed exchange checks disable downloads and retain diagnostics.
Actual input, candidate, source or resource changes invalidate corresponding
cached results/downloads; slider/sort edits preserve a still-matching candidate.
Resource/source revalidation may read and hash kernels again; it does not rerun
search or propagate new trajectory samples. The first export path is repository
based: missing checkout/source provenance disables export rather than inventing it.

The main controls expose a 1–10000 candidate budget (default 2000) and the actual date/duration
grid. Sort the returned Pareto front by fuel, flight time or delta-v; optionally
filter by ideal fuel feasibility. These view preferences do not repeat search.
An empty filter retains the search provenance and can be cleared. The trajectory
control displays elapsed 86400-second days rather than sample indices.

Every input has Russian help with units, constraints and M2 usage. Results have
an additional glossary. Small-body/debris screening is explicitly not performed;
displayed planetary tracks do not establish gravitational inclusion or safety.

Expand **О расчёте** after calculating to inspect the M2 model, runtime/resource
versions, loaded SPICE kernel metadata, search counts and normalized SI inputs.
These describe the completed search, including your edits, not the original
example file. Editing inputs or a calculation failure clears this snapshot;
moving the slider or selecting another candidate reuses it without another search.

The plot is a Sun-relative J2000 XY projection, not an ecliptic view. M2 uses a
two-body transfer and ideal endpoint impulses; it does not resolve escape,
capture, or engine firing durations. The app lists ignored parameters. This
local research UI is not flight-qualified. Do not expose the server publicly.
Streamlit is an additional presentation boundary; the CLI remains unchanged.
High-fidelity M3 is deferred, and scheduled implementation remains paused.

## Development environment

TudatPy is distributed through Conda, so Conda owns Python and the native and
scientific dependencies. `uv` installs the local Python package inside that
environment:

```sh
conda env create --file environment.yml
conda run -n space-nav uv pip install --no-deps --no-build-isolation --editable .
```

For an existing environment, replace the first command with:

```sh
conda env update -n space-nav --file environment.yml --prune
```

Run the complete test suite with:

```sh
conda run -n space-nav python -m pytest -q
```

Do not use `uv lock`, `uv sync`, `uv run`, or `uv venv` in this repository:
they cannot describe the Conda-only TudatPy and native dependency graph.

## Quality checks

```sh
make check
```

This runs Ruff and the complete test suite in `space-nav`. `make setup` refreshes
the Conda environment and editable install. GitHub Actions runs the same checks,
including a real TudatPy/SPICE runtime preflight, on pull requests and pushes to
`main` and `dev`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for review, dependency updates, and maintainer
settings, and [AGENTS.md](AGENTS.md) for scientific and implementation contracts.
