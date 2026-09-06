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
capabilities. CCSDS interchange and interchangeable numerical backends are goals,
not features delivered by this documentation update.

## Local Streamlit explorer

After installing the environment below, run from this repository:

```sh
conda run -n space-nav python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501, explicitly load the example, edit parameters, and
calculate. Select a candidate and move the time slider. Changing input clears
old results. The original example has an ideal propellant shortfall: this is
shown as a warning, not hidden by choosing another spacecraft.

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
