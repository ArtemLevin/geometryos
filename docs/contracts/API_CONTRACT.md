# GeometryOS HTTP API v1 Contract

## Purpose

The stable TutorBoard-facing contract is exposed under `/api/v1`. GeometryOS remains a GIR-first compiler: HTTP handlers delegate to `gir_application`, and only canonical validated GIR reaches renderers.

## Version domains

| Domain | Value |
|---|---|
| HTTP API | `v1` |
| OpenAPI info version | `1.0.0` |
| GIR schema | `0.2.0` |
| Python package | `0.1.0` until the release PR |

These versions evolve independently.

## Stable endpoints

```text
POST /api/v1/generate
POST /api/v1/validate-gir
POST /api/v1/render/svg
POST /api/v1/render/tikz
GET  /health
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
geometryos_v1_generate
geometryos_v1_validate_gir
geometryos_v1_render_svg
geometryos_v1_render_tikz
```

Operation IDs are explicit and stable so future TutorBoard clients can be generated predictably.

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

Timeouts, request-size middleware, readiness failures, request IDs and stable internal-error payloads are intentionally deferred to the resilience PR.

## Legacy aliases

```text
POST /generate
POST /validate-gir
POST /render/svg
POST /render/tikz
```

Legacy aliases preserve their pre-v1 request and response JSON shapes, including `mode: "draft"` and string warnings. They are hidden from OpenAPI and may be removed only in a separately documented breaking change after TutorBoard migration.
