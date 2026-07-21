# GeometryOS HTTP API v1 Contract

## Purpose

The stable TutorBoard-facing contract is exposed under `/api/v1`. GeometryOS remains a GIR-first compiler: HTTP handlers delegate to `gir_application`, and only canonical validated GIR reaches renderers.

## Contract sources

The integration contract is published through four synchronized sources, in this order:

1. FastAPI and Pydantic runtime definitions;
2. generated and freshness-checked `schemas/openapi.v1.json`;
3. executable fixtures under `contracts/tutorboard/v1`;
4. this human-readable document.

`schemas/openapi.v1.json` and the JSON fixtures are generated artifacts and must not be edited manually. `make verify` fails when either artifact set is stale. Pull-request CI additionally checks the candidate OpenAPI against the base branch for backward compatibility.

## Version domains

| Domain | Value |
|---|---|
| HTTP API | `v1` |
| OpenAPI info version | `1.0.0` |
| GIR schema | `0.2.0` |
| TutorBoard contract | `tutorboard/v1` |
| GeometryOS service/package | `0.2.0` |

These versions evolve independently. OpenAPI additionally publishes `x-geometryos-service-version: 0.2.0`; changing the service version does not rename API v1 or alter GIR `0.2.0`.

## Stable endpoints

```text
POST /api/v1/generate
POST /api/v1/validate-gir
POST /api/v1/render/svg
POST /api/v1/render/tikz
GET  /health
GET  /ready
```

Unversioned routes remain temporary compatibility aliases. They are operational but excluded from OpenAPI and are not part of the TutorBoard consumer contract.

## Generate

`POST /api/v1/generate` accepts text input, zero or more unique render formats and public mode `strict`.

```json
{
  "input_type": "text",
  "input": "Постройте треугольник ABC и проведите высоту AH к BC.",
  "output": ["svg"],
  "mode": "strict"
}
```

Contract constraints:

- input is trimmed and must contain 1–20,000 characters;
- outputs are limited to unique `svg` and `tikz` entries;
- v1 accepts only `strict`;
- unknown fields are rejected.

The response is a discriminated union over `status`: `success`, `needs_clarification` or `error`. Expected domain ambiguity and unsupported constructions return HTTP 200. Every v1 generation response includes top-level `schema_version: "0.2.0"`.

Warnings are structured as `{code, message}`. Current stable codes are:

- `unsupported_construction`;
- `draft_gir_invalid`;
- `normalized_gir_invalid`;
- `adapter_warning`.

## Validate GIR

`POST /api/v1/validate-gir` accepts canonical GIR 0.2 and the explicitly supported legacy GIR 0.1 reader format.

A structurally valid request returns:

```json
{
  "schema_version": "0.2.0",
  "canonical_gir": {},
  "validation_report": {
    "is_valid": true,
    "issues": [],
    "warnings": []
  }
}
```

`canonical_gir` means that the version marker has been canonicalized to GIR 0.2. The validation endpoint does not promise geometric normalization.

Semantic-invalid GIR returns HTTP 200 with `is_valid: false`. Structural-invalid GIR and unsupported schema versions return HTTP 422.

## Render

SVG response:

```json
{
  "schema_version": "0.2.0",
  "media_type": "image/svg+xml",
  "content": "<svg>...</svg>"
}
```

TikZ response:

```json
{
  "schema_version": "0.2.0",
  "media_type": "text/x-tex",
  "content": "\\begin{tikzpicture}..."
}
```

Semantic-invalid and structural-invalid render input returns HTTP 422.

## Operation IDs

```text
geometryos_health
geometryos_ready
geometryos_v1_generate
geometryos_v1_validate_gir
geometryos_v1_render_svg
geometryos_v1_render_tikz
```

Operation IDs are explicit and stable so TutorBoard clients can be generated predictably. Renaming an operation ID is a breaking API v1 change.

## HTTP status matrix

| Situation | HTTP |
|---|---:|
| Success | 200 |
| Ambiguous text command | 200 |
| Unsupported construction | 200 |
| Semantic-invalid GIR sent to validate | 200 |
| Invalid request or structural GIR | 422 |
| Semantic-invalid GIR sent to render | 422 |
| Unsupported GIR schema version | 422 |
| Service process alive and application ready | 200 |
| Service process alive but application not ready | 503 |

## Operational probes

`GET /health` is the liveness contract. It returns HTTP 200 with exactly:

```json
{"status": "ok"}
```

Liveness indicates that the process and event loop can answer HTTP. It intentionally remains successful while readiness is stopping or degraded.

`GET /ready` is the readiness contract. It returns HTTP 200 only after FastAPI startup and while the lifecycle, validated settings and application executor checks pass:

```json
{
  "status": "ready",
  "checks": [
    {"name": "lifecycle", "status": "pass"},
    {"name": "settings", "status": "pass"},
    {"name": "executor", "status": "pass"}
  ]
}
```

During startup, shutdown, lifecycle failure or missing runtime state, it returns HTTP 503 with the same schema and `status: "not_ready"`. Readiness responses carry `Cache-Control: no-store`. Both probes receive the additive `X-Request-ID` header.

Readiness is side-effect-free: it does not execute generation, validation, normalization or rendering and does not contact external systems.

## Legacy aliases

```text
POST /generate
POST /validate-gir
POST /render/svg
POST /render/tikz
```

Legacy aliases preserve their pre-v1 request and response JSON shapes, including `mode: "draft"` and string warnings. They are hidden from OpenAPI and may be removed only in a separately documented breaking change after TutorBoard migration.

## Runtime resilience

Every HTTP response carries `X-Request-ID`. Valid caller-provided identifiers are echoed; invalid or missing values are replaced with a generated UUID.

Infrastructure failures under `/api/v1` use `application/problem+json`. The stable runtime status matrix adds:

| Situation | HTTP | Code |
|---|---:|---|
| Configured operational input limit exceeded | 413 | `input_too_large` |
| Request or structural GIR validation failed | 422 | `request_validation_failed` |
| Semantic-invalid GIR sent to render | 422 | `semantic_validation_failed` |
| Operation deadline exceeded | 504 | `operation_timeout` |
| Unexpected internal failure | 500 | `internal_error` |

Successful and domain-result response DTOs remain unchanged. Legacy aliases retain their pre-v1 JSON bodies. Timeouts are soft: the API stops waiting, while an abandoned side-effect-free worker thread may finish later. See `docs/operations/API_RUNTIME.md`.

## Consumer generation and updates

Generate and verify the machine contracts with:

```bash
uv run python scripts/export_openapi.py
uv run python scripts/export_openapi.py --check
uv run python scripts/export_tutorboard_contracts.py
uv run python scripts/export_tutorboard_contracts.py --check
make consumer-contract
make consumer-typescript
```

Generated TypeScript source is intentionally not committed. The committed OpenAPI artifact, exact npm lock, generated-type compilation smoke, and executable JSON fixtures form the reproducible TutorBoard contract.
