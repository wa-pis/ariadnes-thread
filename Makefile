CONDA ?= conda
ENV ?= space-nav
RUN = $(CONDA) run --no-capture-output -n $(ENV)

.PHONY: setup lint test check
setup:
	$(CONDA) env update -n $(ENV) --file environment.yml --prune
	$(RUN) uv pip install --no-deps --no-build-isolation --editable .

lint:
	$(RUN) ruff check src tests

test:
	$(RUN) python -m pytest -q

check: lint test
