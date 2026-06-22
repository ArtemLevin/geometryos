# GIR — Geometry Intermediate Representation

GIR is a Python-first geometry compiler skeleton. Text is converted into draft GIR, validated, normalized, laid out later, and rendered to SVG or TikZ. The LLM is never the source of truth: GIR is.

## Architecture
`gir_core` contains pure Pydantic models, normalization and semantic validation. It has no FastAPI, renderer, database, Docker, frontend, OpenAI or Ollama dependency. `gir_ai` creates draft GIR only. `gir_render` draws already-valid GIR. `gir_api` and `gir_cli` expose the same pipeline.

## Setup and checks
```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/export_schema.py
uv run python scripts/export_schema.py --check
uv run python scripts/run_benchmarks.py
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
gir benchmark
gir export-schema
```

## Continuous Integration

CI runs on `push` and `pull_request` using GitHub Actions. For the same local verification path, run:

```bash
make verify
# or
uv run python scripts/verify.py
```

## MVP
The MVP includes strict GIR models, structural validation, schema export, rule-based altitude/median/ambiguous text adapter, SVG/TikZ renderers and benchmarks. It does not include a solver, real LLM integration, PDF, frontend, auth, DB, Docker, OpenCV, SymPy or multi-user features.
