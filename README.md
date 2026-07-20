# GIR — Geometry Intermediate Representation

GIR is a Python-first geometry compiler skeleton. Text is converted into draft GIR, validated, normalized, laid out through the canonical MVP layout, and rendered to SVG or TikZ. The LLM is never the source of truth: GIR is.

## Architecture

`gir_core` contains pure Pydantic models, normalization and semantic validation. It has no FastAPI, renderer, database, Docker, frontend, OpenAI or Ollama dependency. `gir_ai` creates draft GIR only. `gir_render` draws already-valid GIR. `gir_application` owns the canonical orchestration pipeline, while `gir_api` and `gir_cli` are transport adapters over that application layer.

## Canonical application pipeline

GeometryOS exposes one transport-agnostic workflow:

```text
text → draft GIR → validate → normalize → validate → SVG/TikZ
```

The supported Python entry points are `generate_geometry`, `validate_geometry`, `prepare_geometry` and `render_geometry`. API routes and CLI commands do not assemble the geometry pipeline themselves. See `docs/APPLICATION_PIPELINE.md` and `docs/adr/ADR-002-canonical-application-pipeline.md`.

## Stable HTTP API v1

The TutorBoard-facing contract is exposed under `/api/v1`:

```text
POST /api/v1/generate
POST /api/v1/validate-gir
POST /api/v1/render/svg
POST /api/v1/render/tikz
GET  /health
GET  /ready
```

Unversioned POST routes remain temporary compatibility aliases and are excluded from OpenAPI. Start the development API with `make api`, then call:

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "text",
    "input": "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
    "output": ["svg"],
    "mode": "strict"
  }'
```

See `docs/contracts/API_CONTRACT.md` and `docs/adr/ADR-003-stable-http-api-v1.md`.

API resilience adds `X-Request-ID`, operation-specific soft timeouts, sanitized `application/problem+json` failures and structured JSON request logs. Runtime settings use the `GEOMETRYOS_*` environment variables documented in `docs/operations/API_RUNTIME.md`; the architectural decision is recorded in `docs/adr/ADR-004-api-resilience-boundary.md`.

## Requirements

- Python 3.11 is the canonical local and CI verification version.
- `uv` is required for dependency management and command execution.
- GNU Make is recommended, but direct Python commands are documented for Windows environments without Make.
- Docker Engine and Docker Compose v2 are required for container verification and deployment.

The project commits `.python-version` and `uv.lock`. Normal installation and CI must use the locked dependency graph.

## Quick start

```bash
uv sync --frozen --dev
make verify
make package-smoke
```

Run the complete source and distribution gate with:

```bash
make verify-all
```

### Windows fallback without Make

```powershell
uv sync --frozen --dev
uv run python scripts/verify.py
uv run python scripts/package_smoke.py
```

## Verification

`make verify` is the canonical source verification entrypoint used locally and in CI. It delegates to `scripts/verify.py` and runs:

- `ruff check`;
- `ruff format --check`;
- `mypy`;
- `pytest`, including API, CLI and source import smoke tests;
- GIR schema freshness checks;
- benchmark suites;
- CLI benchmark and schema smoke checks.

The verifier is fail-fast, always executes from the repository root, and prints an explicit `PASS` or `FAIL` result for every executed step.

Individual checks remain available:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/export_schema.py --output schemas/gir-0.2.schema.json
uv run python scripts/export_schema.py --check --output schemas/gir-0.2.schema.json
uv run python scripts/run_benchmarks.py
uv run gir benchmark --root .
uv run gir export-schema --check --output schemas/gir-0.2.schema.json
uv run python scripts/verify.py
```

## Distribution smoke test

Source-tree tests do not prove that the built wheel contains every public package. Run:

```bash
make package-smoke
```

The package smoke test:

1. builds one wheel in a temporary directory;
2. creates an isolated Python 3.11 virtual environment;
3. installs only the generated wheel and its runtime dependencies;
4. runs `uv pip check`;
5. imports all public packages from the installed distribution;
6. verifies installed package metadata;
7. starts the installed `gir --help` console entrypoint.

Temporary artifacts are removed automatically.

## Container deployment

Build and verify the hardened deployment image:

```bash
make container-build
make container-smoke
```

Start the loopback-only Compose deployment:

```bash
make compose-up
```

Operational endpoints:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/ready
http://127.0.0.1:8000/docs
```

`/health` is liveness; `/ready` returns `200` only after FastAPI startup and while the runtime settings and application executor remain available. The image runs as UID/GID `10001:10001`, supports a read-only root filesystem, drops all Linux capabilities and uses `/ready` for Docker health.

See `docs/operations/DEPLOYMENT.md` and `docs/adr/ADR-005-container-runtime-and-readiness.md`.

## Dependency workflow

Install the committed dependency graph without modifying it:

```bash
uv sync --frozen --dev
```

Intentionally resolve the current dependency constraints:

```bash
make lock
make verify-all
```

Intentionally upgrade dependency versions:

```bash
make lock-upgrade
uv sync --frozen --dev
make verify-all
```

Any `uv.lock` change must be reviewed as a dependency graph change. CI uses frozen installation and fails rather than silently rewriting the lock file.

## Makefile shortcuts

```bash
make help
make sync
make lock
make lock-upgrade
make test
make verify
make package-smoke
make verify-all
make schema-check
make api
make api-prod
make container-build
make container-smoke
make compose-config
make compose-up
make compose-down
make validate BENCHMARK_GIR=benchmarks/text_to_gir/altitude/altitude_001.expected.gir.json
```

## API ambiguity response

Ambiguous requests are first-class domain responses, not server errors. For example:

```json
{
  "status": "needs_clarification",
  "confidence": 0.4,
  "schema_version": "0.2.0",
  "gir": null,
  "validation_report": null,
  "svg": null,
  "tikz": null,
  "warnings": [],
  "ambiguities": [
    {
      "code": "missing_angle",
      "message": "Не указано, биссектрису какого угла нужно построить.",
      "options": ["angle_A", "angle_B", "angle_C"]
    }
  ],
  "explanation": "Bisector request lacks angle target."
}
```

## CLI

```bash
gir validate benchmarks/text_to_gir/altitude/altitude_001.expected.gir.json
gir render-svg benchmarks/text_to_gir/altitude/altitude_001.expected.gir.json
gir render-tikz benchmarks/text_to_gir/altitude/altitude_001.expected.gir.json
gir benchmark --root .
gir benchmark --benchmarks-dir benchmarks/text_to_gir
gir export-schema --output schemas/gir-0.2.schema.json
gir export-schema --check --output schemas/gir-0.2.schema.json
```

By default, `gir benchmark` uses the current working directory as the project root.

## Development API

```bash
make api
```

Equivalent direct command:

```bash
uv run uvicorn gir_api.main:app --reload
```

Production-style local process without reload:

```bash
make api-prod
```

## Continuous integration

GitHub Actions runs three gated jobs on pushes and pull requests:

- `verify` installs dependencies from `uv.lock` and runs `make verify`;
- `package-smoke` independently builds and installs the wheel with `make package-smoke`;
- `container-smoke` runs after both jobs, validates Compose, builds the hardened image and checks runtime security, probes, stable API behavior and graceful shutdown.

All jobs use Python 3.11, frozen dependency installation, read-only repository permissions and explicit timeouts. Pull-request CI builds but does not publish container images.

## MVP

The MVP includes strict GIR models, semantic validation, schema export/check, a deterministic rule-based adapter for triangle/altitude/median/midpoint/angle-bisector cases, a canonical application pipeline, canonical single-triangle layout, SVG/TikZ renderers, stable API v1, readiness/liveness probes, a hardened container deployment, CLI contracts and text/render benchmarks. It does not include a general solver, real LLM integration, PDF, frontend, auth, DB, OpenCV, SymPy or multi-user features.
