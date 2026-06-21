SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

UV ?= uv
PYTHON ?= python
UV_RUN := $(UV) run
BENCHMARK_GIR ?= benchmarks/text_to_gir/altitude/altitude_001.expected.gir.json
HOST ?= 127.0.0.1
PORT ?= 8000

.PHONY: help sync install test lint format format-check typecheck schema benchmarks check api \
	validate render-svg render-tikz cli-benchmark cli-export-schema clean py-compile

help: ## Show available Make targets.
	@awk 'BEGIN {FS = ":.*##"; printf "GIR developer commands:\n\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

sync: ## Install runtime and dev dependencies with uv.
	$(UV) sync --dev

install: sync ## Alias for sync.

test: ## Run the pytest suite.
	$(UV_RUN) pytest

lint: ## Run ruff lint checks.
	$(UV_RUN) ruff check .

format: ## Format Python code with ruff.
	$(UV_RUN) ruff format .

format-check: ## Check Python formatting without modifying files.
	$(UV_RUN) ruff format --check .

typecheck: ## Run mypy over src/.
	$(UV_RUN) mypy src

schema: ## Export GIR JSON Schema to schemas/gir.schema.json.
	$(UV_RUN) $(PYTHON) scripts/export_schema.py

benchmarks: ## Run text-to-GIR benchmark checks.
	$(UV_RUN) $(PYTHON) scripts/run_benchmarks.py

check: test lint format-check typecheck schema benchmarks ## Run all required verification checks.

api: ## Start the FastAPI development server.
	$(UV_RUN) uvicorn gir_api.main:app --reload --host $(HOST) --port $(PORT)

validate: ## Validate BENCHMARK_GIR or another GIR path: make validate BENCHMARK_GIR=path.gir.json.
	$(UV_RUN) gir validate $(BENCHMARK_GIR)

render-svg: ## Render BENCHMARK_GIR as SVG via CLI.
	$(UV_RUN) gir render-svg $(BENCHMARK_GIR)

render-tikz: ## Render BENCHMARK_GIR as TikZ via CLI.
	$(UV_RUN) gir render-tikz $(BENCHMARK_GIR)

cli-benchmark: ## Run benchmarks through the installed CLI entrypoint.
	$(UV_RUN) gir benchmark

cli-export-schema: ## Export schema through the installed CLI entrypoint.
	$(UV_RUN) gir export-schema

py-compile: ## Syntax-check Python files without importing third-party dependencies.
	$(PYTHON) -m py_compile $$(find src scripts tests -name '*.py' -not -path '*/.venv/*')

clean: ## Remove local caches, build outputs, coverage artifacts and virtualenv.
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov build dist *.egg-info .venv
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
