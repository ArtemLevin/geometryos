# GeometryOS 0.2.0 Integration Guide

## Version matrix

| Contract | Version |
|---|---|
| GeometryOS service/distribution | `0.2.0` |
| HTTP API | `v1` / `1.0.0` |
| GIR schema | `0.2.0` |
| TutorBoard contract | `tutorboard/v1` |

The service version, API version and GIR schema version are independent contracts. Do not infer one from another.

## Deployment

For local or TutorBoard-side deployment:

```bash
docker compose up --build --detach
```

The default Compose binding is loopback-only:

```text
http://127.0.0.1:8000
```

For immutable deployments prefer the published digest:

```text
ghcr.io/artemlevin/geometryos@sha256:<digest>
```

The SemVer tag is:

```text
ghcr.io/artemlevin/geometryos:0.2.0
```

## Health probes

```text
GET /health
GET /ready
```

`/health` is process liveness. `/ready` returns `200` only after startup and while required runtime components are available; otherwise it returns `503` with the same readiness response shape.

## API endpoints

```text
POST /api/v1/generate
POST /api/v1/validate-gir
POST /api/v1/render/svg
POST /api/v1/render/tikz
```

The complete machine contract is `schemas/openapi.v1.json`. Executable examples are under `contracts/tutorboard/v1`.

## Generate

```json
{
  "input_type": "text",
  "input": "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
  "output": ["svg"],
  "mode": "strict"
}
```

A successful response has `status="success"`, canonical GIR `0.2.0`, a validation report and requested render artifacts.

### Clarification

`status="needs_clarification"` is an expected domain result and remains HTTP `200`. TutorBoard should show the supplied ambiguity message/options and submit a new explicit request. It should not retry the same payload automatically.

### Unsupported construction

`status="error"` with warning code `unsupported_construction` is also an expected HTTP `200` domain result. It is not a transport failure.

## Validate GIR

`POST /api/v1/validate-gir` accepts canonical GIR `0.2.0` and supported legacy GIR `0.1`. Legacy input is upgraded and returned as canonical GIR `0.2.0`.

- structurally invalid payload: HTTP `422`;
- semantic-invalid GIR: HTTP `200` with `is_valid=false`;
- unknown schema version: HTTP `422`.

## Render

SVG response:

```json
{
  "schema_version": "0.2.0",
  "media_type": "image/svg+xml",
  "content": "<svg>...</svg>"
}
```

TikZ response uses `media_type="text/x-tex"`. Semantic-invalid GIR is rejected with HTTP `422`; renderers never receive invalid scenes.

## Request correlation

TutorBoard may send:

```text
X-Request-ID: <safe internal correlation id>
```

GeometryOS echoes a valid identifier or generates one. Preserve the response header and the `request_id` in Problem Details when logging integration failures.

## Client timeout recommendations

| Operation | Server default | Recommended client deadline |
|---|---:|---:|
| Generate | 15 s | 20–25 s |
| Validate | 5 s | 8–10 s |
| Render | 10 s | 15 s |

Server timeouts are soft for a synchronous worker already executing. A client timeout should close its wait but must not assume the underlying worker stopped immediately.

## Retry policy

Limited retry with exponential backoff is appropriate for:

- connection failure before receiving a response;
- readiness HTTP `503`;
- operation timeout HTTP `504`;
- selected sanitized HTTP `500` failures while operations remain side-effect-free.

Do not automatically retry:

- HTTP `413`;
- HTTP `422`;
- `needs_clarification`;
- domain `status="error"`.

Always bound attempts and preserve the same request correlation lineage.

## Problem Details

API failures use `application/problem+json` with:

```text
type, title, status, detail, instance, code, request_id, errors
```

See `docs/ERROR_MODEL.md`. Never parse human-readable `detail` as a stable programmatic value; branch on HTTP status and `code`.

## Client generation

Generate TypeScript types from the committed OpenAPI artifact:

```bash
npm ci --prefix contracts/tutorboard/typescript
npm run --prefix contracts/tutorboard/typescript generate
npm run --prefix contracts/tutorboard/typescript typecheck
```

The generated source is intentionally not committed. TutorBoard should generate its own client using the immutable OpenAPI artifact attached to the release.

## Known limitations

- construction coverage is bounded and rule-based;
- there is no external LLM provider in `0.2.0`;
- authentication and TLS termination must be provided by the surrounding platform;
- the first published image target is `linux/amd64`.
