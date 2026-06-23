# GIR — Geometry Intermediate Representation

GIR is a Python-first geometry compiler skeleton. Text is converted into draft GIR, validated, normalized, laid out through the canonical MVP layout, and rendered to SVG or TikZ. The LLM is never the source of truth: GIR is.

## Architecture
`gir_core` contains pure Pydantic models, normalization and semantic validation. It has no FastAPI, renderer, database, Docker, frontend, OpenAI or Ollama dependency. `gir_ai` creates draft GIR only. `gir_render` draws already-valid GIR. `gir_api` and `gir_cli` expose the same pipeline.

## Setup and checks
```bash
uv sync --dev
uv run python scripts/verify.py
```

## Verification

Run the full local gate before opening a PR:

```bash
uv sync --dev
uv run python scripts/verify.py
```

or:

```bash
make verify
```

The verification gate runs:

- `ruff check`;
- `ruff format --check`;
- `mypy`;
- `pytest` including API, CLI and import smoke tests;
- GIR schema freshness check;
- benchmark suites;
- CLI benchmark and schema smoke checks.

Individual checks remain available:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run python scripts/export_schema.py --output schemas/gir.schema.json
uv run python scripts/export_schema.py --check --output schemas/gir.schema.json
uv run python scripts/run_benchmarks.py
uv run gir benchmark --root .
uv run gir export-schema --check --output schemas/gir.schema.json
uv run python scripts/verify.py
uv run uvicorn gir_api.main:app --reload
```


## Makefile shortcuts
```bash
make help
make sync
make check
make verify
make schema-check
make api
make validate BENCHMARK_GIR=benchmarks/text_to_gir/altitude/altitude_001.expected.gir.json
```

## API ambiguity response

Ambiguous requests are first-class domain responses, not server errors. For example:

```json
{
  "status": "needs_clarification",
  "confidence": 0.4,
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
gir export-schema --output schemas/gir.schema.json
gir export-schema --check --output schemas/gir.schema.json
```

By default, `gir benchmark` uses the current working directory as the project root.

## Continuous Integration

CI runs on `push` and `pull_request` using GitHub Actions. For the same local verification path, run:

```bash
make verify
# or
uv run python scripts/verify.py
```

## MVP
The MVP includes strict GIR models, semantic validation, schema export/check, a deterministic rule-based adapter for triangle/altitude/median/midpoint/angle-bisector MVP cases, canonical single-triangle layout, SVG/TikZ renderers, API/CLI contracts and text/render benchmarks. It does not include a general solver, real LLM integration, PDF, frontend, auth, DB, Docker, OpenCV, SymPy or multi-user features.
