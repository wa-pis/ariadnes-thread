CONDA ?= conda
ENV ?= space-nav
RUN = $(CONDA) run --no-capture-output -n $(ENV)

.PHONY: setup lint test test-unit test-live test-archive check
setup:
	$(CONDA) env update -n $(ENV) --file environment.yml --prune
	$(RUN) uv pip install --no-deps --no-build-isolation --editable .

lint:
	$(RUN) ruff check src tests

test: test-unit test-live

test-unit:
	$(RUN) python -m pytest -q -ra --offline

test-live:
	$(RUN) python -m pytest -q -ra -m live

test-archive:
	$(RUN) python -m pytest -q -ra --run-archive -m archive

check: lint test
