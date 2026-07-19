.PHONY: help install install-dev install-all lint format typecheck arch test test-unit coverage check clean

help:
	@echo "Install"
	@echo "  install           runtime dependencies only (no dev group, no extras)"
	@echo "  install-dev       runtime + dev group"
	@echo "  install-all       everything: dev group + every adapter extra"
	@echo ""
	@echo "Verify"
	@echo "  lint              ruff check + format check"
	@echo "  format            ruff format (writes) + ruff --fix"
	@echo "  typecheck         mypy (strict)"
	@echo "  arch              import-linter: the layer dependency rule"
	@echo "  test-unit         offline unit suite"
	@echo "  coverage          unit suite, domain+application gated"
	@echo "  check             lint + typecheck + arch + test-unit"

# --- Install -----------------------------------------------------------------

install:
	uv sync --no-dev

install-dev:
	uv sync

install-all:
	uv sync --all-extras

# --- Verify ------------------------------------------------------------------

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src tests

arch:
	uv run lint-imports

test:
	uv run pytest

test-unit:
	uv run pytest -m unit

coverage:
	uv run pytest -m unit \
		--cov=src/app/domain \
		--cov=src/app/application \
		--cov-report=term-missing \
		--cov-fail-under=90

check: lint typecheck arch test-unit

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
