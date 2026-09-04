# Space Nav

Ground-based Moon-to-Mars mission-planning and navigation prototype.

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
