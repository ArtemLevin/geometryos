SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

UV ?= uv
PYTHON ?= python
UV_RUN := $(UV) run
BENCHMARK_GIR ?= benchmarks/text_to_gir/altitude/altitude_001.expected.gir.json
HOST ?= 127.0.0.1
PORT ?= 8000
IMAGE ?= geometryos
IMAGE_TAG ?= local
CONTAINER_IMAGE := $(IMAGE):$(IMAGE_TAG)
PROJECT_VERSION := $(shell $(PYTHON) scripts/print_version.py)
RELEASE_TAG ?= v$(PROJECT_VERSION)
BUILD_REVISION ?= $(shell git rev-parse HEAD 2>/dev/null || echo local)
BUILD_VERSION ?= $(PROJECT_VERSION)

.PHONY: help sync install lock lock-upgrade test lint format format-check typecheck schema schema-check \
	openapi openapi-check consumer-contract consumer-typescript benchmarks verify package-smoke \
	verify-all check api api-prod validate render-svg render-tikz cli-benchmark cli-export-schema \
	cli-schema-check container-build container-smoke compose-config compose-up compose-down \
	compose-logs version version-check release-manifest release-manifest-check dependency-audit \
	release-build release-smoke release-check release-all clean py-compile

help: ## Show available Make targets.
	@awk 'BEGIN {FS = ":.*##"; printf "GIR developer commands:\n\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

sync: ## Install locked runtime and dev dependencies with uv.
	$(UV) sync --frozen --dev

install: sync ## Alias for sync.

lock: ## Resolve dependencies and update uv.lock intentionally.
	$(UV) lock

lock-upgrade: ## Upgrade dependency versions recorded in uv.lock.
	$(UV) lock --upgrade

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

schema: ## Export GIR JSON Schema to schemas/gir-0.2.schema.json.
	$(UV_RUN) $(PYTHON) scripts/export_schema.py

schema-check: ## Check that committed GIR JSON Schema is up to date.
	$(UV_RUN) $(PYTHON) scripts/export_schema.py --check

openapi: ## Export the canonical OpenAPI v1 artifact.
	$(UV_RUN) $(PYTHON) scripts/export_openapi.py

openapi-check: ## Check that committed OpenAPI v1 is up to date.
	$(UV_RUN) $(PYTHON) scripts/export_openapi.py --check

consumer-contract: ## Run TutorBoard Python consumer contract tests.
	$(UV_RUN) pytest tests/contracts

consumer-typescript: ## Generate and type-check TutorBoard TypeScript contract types.
	npm ci --prefix contracts/tutorboard/typescript
	npm run --prefix contracts/tutorboard/typescript generate
	npm run --prefix contracts/tutorboard/typescript typecheck

benchmarks: ## Run all benchmark suites.
	$(UV_RUN) $(PYTHON) scripts/run_benchmarks.py

verify: ## Run the canonical source verification gate.
	$(UV_RUN) $(PYTHON) scripts/verify.py

package-smoke: ## Build and test the wheel in an isolated environment.
	$(UV_RUN) $(PYTHON) scripts/package_smoke.py

verify-all: verify package-smoke ## Run source and distribution verification.

check: test lint format-check typecheck schema-check openapi-check benchmarks ## Run individual source checks.

api: ## Start the FastAPI development server with reload.
	$(UV_RUN) uvicorn gir_api.main:app --reload --host $(HOST) --port $(PORT)

api-prod: ## Start the production-style single-process Uvicorn server.
	$(UV_RUN) uvicorn gir_api.main:app --host 0.0.0.0 --port $(PORT) --no-access-log --timeout-graceful-shutdown 20

validate: ## Validate BENCHMARK_GIR or another GIR path: make validate BENCHMARK_GIR=path.gir.json.
	$(UV_RUN) gir validate $(BENCHMARK_GIR)

render-svg: ## Render BENCHMARK_GIR as SVG via CLI.
	$(UV_RUN) gir render-svg $(BENCHMARK_GIR)

render-tikz: ## Render BENCHMARK_GIR as TikZ via CLI.
	$(UV_RUN) gir render-tikz $(BENCHMARK_GIR)

cli-benchmark: ## Run benchmarks through the installed CLI entrypoint.
	$(UV_RUN) gir benchmark --root .

cli-export-schema: ## Export schema through the installed CLI entrypoint.
	$(UV_RUN) gir export-schema --output schemas/gir-0.2.schema.json

cli-schema-check: ## Check schema through the installed CLI entrypoint.
	$(UV_RUN) gir export-schema --check --output schemas/gir-0.2.schema.json

container-build: ## Build the hardened GeometryOS container image.
	docker build --tag $(CONTAINER_IMAGE) --build-arg BUILD_REVISION=$(BUILD_REVISION) --build-arg BUILD_VERSION=$(BUILD_VERSION) .

container-smoke: ## Build and run the complete hardened container smoke test.
	$(UV_RUN) $(PYTHON) scripts/container_smoke.py --image $(CONTAINER_IMAGE) --revision $(BUILD_REVISION) --version $(BUILD_VERSION)

compose-config: ## Validate the Docker Compose deployment definition.
	docker compose config --quiet

compose-up: ## Build and start GeometryOS through Docker Compose.
	docker compose up --build --detach

compose-down: ## Stop Compose services and remove orphan containers.
	docker compose down --remove-orphans

compose-logs: ## Follow GeometryOS Compose logs.
	docker compose logs --follow geometryos

version: ## Print the canonical GeometryOS service version.
	@$(PYTHON) scripts/print_version.py

version-check: ## Check all release-version sources for consistency.
	$(UV_RUN) $(PYTHON) scripts/check_release_version.py

release-manifest: ## Export release/manifest.json.
	$(UV_RUN) $(PYTHON) scripts/export_release_manifest.py

release-manifest-check: ## Check that release/manifest.json is current.
	$(UV_RUN) $(PYTHON) scripts/export_release_manifest.py --check

dependency-audit: ## Audit the frozen runtime dependency graph.
	$(UV_RUN) $(PYTHON) scripts/audit_runtime_dependencies.py

release-build: ## Build the validated release bundle under dist/release/.
	$(UV_RUN) $(PYTHON) scripts/build_release.py

release-smoke: ## Validate the complete release bundle.
	$(UV_RUN) $(PYTHON) scripts/release_smoke.py

release-check: verify package-smoke consumer-contract consumer-typescript container-smoke version-check release-manifest-check ## Run every pre-release gate without publishing.

release-all: release-check dependency-audit release-build release-smoke ## Build and verify the complete release candidate.

py-compile: ## Syntax-check Python files without importing third-party dependencies.
	$(PYTHON) -m py_compile $$(find src scripts tests -name '*.py' -not -path '*/.venv/*')

clean: ## Remove local caches, build outputs, coverage artifacts and virtualenv.
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov build dist *.egg-info .venv .smoke-venv
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
