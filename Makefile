.PHONY: help install install-dev lint format typecheck test verify clean docker-build docker-run

PY    ?= python3
PIP   ?= $(PY) -m pip
DOCKER ?= docker

help:
	@echo "Available targets:"
	@echo "  install      - install runtime dependencies"
	@echo "  install-dev  - editable install with dev extras"
	@echo "  lint         - run ruff (lint + format check)"
	@echo "  format       - auto-format with ruff"
	@echo "  typecheck    - run mypy on the package"
	@echo "  test         - run pytest with coverage"
	@echo "  verify       - lint + typecheck + test (used by CI / scripts/verify.sh)"
	@echo "  docker-build - build the convertxls Docker image"
	@echo "  docker-run   - run convertxls in a container (pass --args through)"
	@echo "  clean        - remove caches and build artifacts"

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -e ".[dev]"

lint:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

format:
	$(PY) -m ruff check --fix src tests
	$(PY) -m ruff format src tests

typecheck:
	$(PY) -m mypy src/convertxls

test:
	$(PY) -m pytest tests/unit -v

verify: lint typecheck test
	@echo "All checks passed."

docker-build:
	$(DOCKER) build -t convertxls .

docker-run:
	$(DOCKER) run --rm -v "$$PWD/legacy:/data" -v "$$PWD/out:/out" convertxls $(ARGS)

clean:
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +
