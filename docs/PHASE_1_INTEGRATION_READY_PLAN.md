# GeometryOS Integration Ready — Phase 1 Development Plan

## 1. Purpose

The goal of Phase 1 is to bring GeometryOS to a stable **integration-ready** state and release an initial service version `0.2.0` that can be safely consumed by TutorBoard.

The target end-to-end contract is:

```text
text request
    ↓
draft GIR
    ↓
structural and semantic validation
    ↓
normalization
    ↓
canonical GIR 0.2
    ↓
SVG / TikZ
```

Phase 1 does **not** attempt to make GeometryOS a complete geometry platform. It should remain a small, deterministic, GIR-first geometry compiler and service.

## 2. Explicitly out of scope

The following features are deferred until after the first TutorBoard integration spike:

- general-purpose constraint solver;
- handwritten sketch recognition;
- OpenCV integration;
- 3D geometry and 3D GIR;
- production LLM provider;
- database and persistence;
- authentication and authorization;
- multi-user collaboration;
- frontend or visual editor;
- PDF rendering;
- Redis, Celery, event bus or workflow engine;
- Kubernetes and full platform observability.

The only runtime hardening required in this phase is what is necessary for predictable service integration: stable contracts, timeouts, structured errors, health/readiness endpoints, packaging and Docker execution.

---

# 3. Current baseline

GeometryOS already contains the main architectural building blocks:

- `gir_core` with Pydantic GIR models;
- semantic validation;
- normalization;
- a deterministic rule-based text-to-GIR adapter;
- canonical MVP layout;
- SVG and TikZ renderers;
- FastAPI endpoints;
- CLI commands;
- generated JSON Schema;
- benchmark suites;
- a common verification script;
- GitHub Actions CI.

The current public endpoints are:

```text
GET  /health
POST /generate
POST /validate-gir
POST /render/svg
POST /render/tikz
```

The current implementation is suitable as an MVP skeleton, but it still lacks the formal versioning, compatibility policy, stable API namespace, error model, readiness check, reproducible container image and TutorBoard-facing consumer contracts required for reliable integration.

---

# 4. Definition of Done for GeometryOS 0.2.0

Phase 1 is complete only when all of the following are true.

## 4.1. Geometry core

- A canonical GIR 0.2 specification is documented.
- Every canonical scene contains `schema_version`.
- Legacy GIR 0.1 input is accepted only through an explicit compatibility layer.
- Unknown schema versions are rejected predictably.
- AI adapters can only create draft GIR and cannot render directly.
- Renderers cannot invent, repair or silently reinterpret geometry.
- Semantic-invalid GIR is never rendered.
- Normalization is deterministic and idempotent for supported scenes.

## 4.2. Stable API

The following endpoints are available and documented:

```text
POST /api/v1/generate
POST /api/v1/validate-gir
POST /api/v1/render/svg
POST /api/v1/render/tikz
GET  /health
GET  /ready
```

Legacy unversioned endpoints remain temporarily available as deprecated aliases but are excluded from the TutorBoard consumer contract.

## 4.3. Reliability

- Request timeouts return HTTP `504`.
- Readiness failures return HTTP `503`.
- Unexpected internal errors return a stable HTTP `500` payload.
- Tracebacks, local paths and implementation details are never returned to clients.
- Every response carries `X-Request-ID`.
- Structured logs include request ID, operation, duration and error code.
- The Docker image runs as a non-root user.
- The container responds correctly to `SIGTERM`.

## 4.4. Published contracts

- `schemas/gir-0.2.schema.json` is committed and freshness-checked.
- `schemas/openapi.v1.json` is committed and freshness-checked.
- `make verify` passes from a clean checkout.
- CI executes the same verification path.
- TutorBoard consumer contract tests pass.
- A Docker container smoke test passes.
- Package, API and service versions are set to `0.2.0`.

---

# 5. Architectural invariants

The implementation must preserve these package boundaries:

```text
gir_ai
    produces draft GIR only

gir_core
    defines, validates and normalizes GIR

gir_application
    orchestrates use cases and the pipeline

gir_render
    renders already validated scenes

gir_api / gir_cli
    adapt external input to gir_application
```

Forbidden dependencies and flows:

```text
gir_core → FastAPI
gir_core → renderer
gir_core → Docker
gir_core → LLM SDK
gir_render → gir_ai
gir_render → geometry repair
gir_api → duplicated geometry pipeline
Text → AI → SVG
Text → AI → TikZ
API → render without semantic validation
```

Expected pipeline:

```text
input
  ↓
adapter / parser
  ↓
draft GIR
  ↓
semantic validation
  ↓
normalization
  ↓
semantic validation
  ↓
layout
  ↓
renderer
```

---

# 6. Delivery strategy

Phase 1 should be implemented as eight ordered pull requests:

```text
PR 1  Reproducible green baseline
  ↓
PR 2  GIR 0.2 schema and compatibility
  ↓
PR 3  Canonical application pipeline
  ↓
PR 4  Stable API v1
  ↓
PR 5  Timeouts, errors and request context
  ↓
PR 6  Health, readiness and Docker
  ↓
PR 7  OpenAPI and TutorBoard consumer contracts
  ↓
PR 8  Release GeometryOS 0.2.0
```

Each PR must keep `make verify` green. A PR that changes a public contract must update its tests, generated artifacts and documentation in the same change.

---

# PR 1 — Reproducible Green Baseline

**Suggested branch:** `integration/01-green-baseline`

## Goal

Prove that the current repository can be verified reproducibly from a clean checkout before adding new behavior.

## Required changes

### 1. Lock dependency installation

- Confirm that `uv.lock` is committed and current.
- Change CI installation to:

```bash
uv sync --frozen --dev
```

- Prevent CI from modifying the lock file.
- Add a separate package build smoke check.

### 2. Establish one canonical verification path

Use:

```bash
make verify
```

as the documented local and CI entrypoint.

The Makefile should still delegate to `scripts/verify.py`, which remains the single implementation of the verification sequence.

CI should run:

```yaml
- name: Verify
  run: make verify
```

### 3. Add wheel installation smoke testing

The project should be tested not only from source checkout but also as an installed distribution:

```bash
uv build
python -m venv .smoke-venv
.smoke-venv/bin/pip install dist/*.whl
.smoke-venv/bin/gir --help
.smoke-venv/bin/python -c "import gir_core, gir_api, gir_render"
```

On Windows, equivalent executable paths should be used in local instructions.

### 4. Make verification output explicit

`scripts/verify.py` should print named steps and stop immediately on failure:

```text
ruff: passed
format: passed
mypy: passed
pytest: passed
schema: passed
benchmarks: passed
cli benchmark: passed
cli schema: passed
```

### 5. Verify package imports

Include smoke tests for all public packages:

```text
gir_core
gir_ai
gir_render
gir_application   # after PR 3
gir_api
gir_cli
gir_benchmarks
```

## Main files

```text
.github/workflows/ci.yml
Makefile
scripts/verify.py
pyproject.toml
uv.lock
tests/test_verify_contract.py
README.md
```

## Verification

```bash
uv sync --frozen --dev
make verify
uv build
```

## Acceptance criteria

- A clean checkout passes `make verify`.
- CI uses the same verification entrypoint.
- A wheel builds successfully.
- The wheel installs in an empty environment.
- The installed CLI starts successfully.
- README, Makefile and CI document the same commands.

---

# PR 2 — GIR 0.2 Specification and Compatibility

**Suggested branch:** `integration/02-gir-schema-v02`

## Goal

Turn GIR into a formally versioned machine contract.

## Canonical GIR 0.2 shape

```json
{
  "schema_version": "0.2.0",
  "scene_type": "2d",
  "objects": [],
  "constraints": [],
  "construction_steps": [],
  "metadata": {}
}
```

## Version field decision

The canonical model must not contain both:

```json
{
  "version": "0.1",
  "schema_version": "0.2.0"
}
```

`schema_version` becomes the only source of truth.

The legacy field `version` is handled only by the compatibility adapter.

## Compatibility pipeline

```text
raw JSON payload
    ↓
detect schema version
    ↓
upgrade legacy payload if supported
    ↓
validate canonical GirScene 0.2
```

Required behavior:

| Input | Result |
|---|---|
| `schema_version: 0.2.0` | accepted |
| legacy `version: 0.1` | upgraded to 0.2 |
| no version | rejected |
| `schema_version: 0.3.0` | rejected as unsupported |
| unknown major version | rejected |

When legacy input is accepted, return a structured warning:

```json
{
  "code": "legacy_schema_version",
  "message": "GIR 0.1 was upgraded to GIR 0.2."
}
```

All API outputs must use canonical GIR 0.2 only.

## Version policy

Create `docs/COMPATIBILITY.md` and explicitly separate:

```text
GeometryOS service version: 0.2.0
API version: v1
GIR schema version: 0.2.0
```

Recommended GIR rules:

- patch: documentation and validation fixes that do not change accepted structure;
- minor: backward-compatible optional fields, object types or constraints;
- major: removals, renames or semantic changes.

## Required implementation

- Replace canonical `version` with `schema_version` in `GirScene`.
- Add `gir_core.compat` with version detection and upgrade functions.
- Generate `schemas/gir-0.2.schema.json`.
- Update all success benchmark fixtures to GIR 0.2.
- Keep at least one GIR 0.1 fixture specifically for compatibility tests.
- Add a stable unsupported-version error code.
- Document the migration contract.

## Main files

```text
src/gir_core/models/scene.py
src/gir_core/compat.py
src/gir_core/schema.py
schemas/gir-0.2.schema.json
docs/GIR_SPEC.md
docs/COMPATIBILITY.md
docs/adr/ADR-001-gir-versioning.md
benchmarks/**/*.gir.json
tests/test_schema_compatibility.py
tests/test_schema_export.py
```

## Required tests

```text
GIR 0.2 is accepted
GIR 0.1 is upgraded
missing version is rejected
unknown version is rejected
upgraded GIR 0.1 becomes semantic-valid GIR 0.2
serialized GIR contains schema_version
serialized GIR does not contain version
schema generation is deterministic
```

## Acceptance criteria

- All canonical fixtures use GIR 0.2.
- Legacy support is isolated in one compatibility layer.
- Unknown versions fail with a stable error.
- JSON Schema is generated from Pydantic models.
- Schema freshness is part of `make verify`.
- Compatibility rules are recorded in an ADR.

---

# PR 3 — Canonical Application Pipeline

**Suggested branch:** `integration/03-application-pipeline`

## Goal

Remove pipeline orchestration from FastAPI routes and CLI handlers. API and CLI must call one application layer.

## New package

```text
src/gir_application/
├── __init__.py
├── pipeline.py
├── commands.py
├── results.py
└── errors.py
```

## Required use cases

```python
generate_geometry(command: GenerateCommand) -> GenerateResult
validate_geometry(command: ValidateCommand) -> ValidateResult
render_geometry(command: RenderCommand) -> RenderResult
```

## Canonical generate pipeline

```text
1. Validate request command
2. Parse external input
3. Produce draft GIR
4. Validate draft GIR
5. Normalize GIR
6. Validate normalized GIR
7. Render requested formats
8. Return typed result
```

API and CLI must not duplicate these steps.

## Error hierarchy

```python
GeometryOSError
├── UnsupportedSchemaVersionError
├── StructuralValidationError
├── SemanticValidationError
├── NormalizationError
├── RenderError
└── PipelineTimeoutError
```

Expected user-domain results should remain normal typed results rather than exceptions:

```text
success
needs_clarification
error / unsupported construction
```

## Handling `mode`

The current public request accepts `strict` and `draft`, but draft behavior is not meaningfully implemented.

For API v1:

```text
mode = strict
```

Only strict mode should be public.

Draft mode may remain an internal Python or diagnostic CLI feature, but TutorBoard must never receive semantic-invalid draft GIR.

The API must not silently ignore `mode="draft"`.

## Required refactoring

- Move validation and normalization orchestration out of routes.
- Move renderer selection out of routes.
- Reuse the same application services in CLI commands.
- Keep `gir_core` independent from API/application delivery details.
- Ensure renderers receive only validated canonical scenes.

## Main files

```text
src/gir_application/*
src/gir_api/routes/generate.py
src/gir_api/routes/render.py
src/gir_api/routes/validate.py
src/gir_cli/main.py
pyproject.toml
tests/test_application_pipeline.py
```

## Required tests

- Adapter returns no GIR.
- Draft GIR fails semantic validation.
- Normalization changes a scene.
- Normalized GIR fails semantic validation.
- SVG renderer raises an error.
- TikZ renderer raises an error.
- No render format requested.
- Only SVG requested.
- Only TikZ requested.
- Unrequested renderer is never called.
- API and CLI produce equivalent core results.

## Acceptance criteria

- API and CLI use one application service.
- Validation/normalization orchestration exists in one place.
- Route handlers contain no geometry business logic.
- All previous benchmark contracts remain green.

---

# PR 4 — Stable API v1

**Suggested branch:** `integration/04-stable-api-v1`

## Goal

Create a stable HTTP contract for TutorBoard.

## New routes

```text
POST /api/v1/generate
POST /api/v1/validate-gir
POST /api/v1/render/svg
POST /api/v1/render/tikz
```

Legacy routes remain temporarily available as deprecated aliases:

```text
POST /generate
POST /validate-gir
POST /render/svg
POST /render/tikz
```

Legacy aliases should use:

```python
include_in_schema=False
```

They should be covered by regression tests but excluded from the TutorBoard OpenAPI contract.

## `/api/v1/generate`

### Request

```json
{
  "input_type": "text",
  "input": "Постройте треугольник ABC и проведите высоту AH к BC.",
  "output": ["svg"],
  "mode": "strict"
}
```

Validation rules:

- `input` must not be empty;
- input length is bounded by configuration;
- `output` contains no duplicates;
- only `svg` and `tikz` are accepted;
- only `strict` is public in API v1;
- all unknown fields are rejected.

### Success response

```json
{
  "status": "success",
  "confidence": 0.9,
  "schema_version": "0.2.0",
  "gir": {},
  "validation_report": {
    "is_valid": true,
    "issues": [],
    "warnings": []
  },
  "svg": "<svg>...</svg>",
  "tikz": null,
  "warnings": [],
  "ambiguities": [],
  "explanation": "Rule-based altitude case."
}
```

### Ambiguity response

HTTP status remains `200` because this is an expected domain result:

```json
{
  "status": "needs_clarification",
  "gir": null,
  "ambiguities": [
    {
      "code": "missing_angle",
      "message": "Не указан угол.",
      "options": ["angle_A", "angle_B", "angle_C"]
    }
  ]
}
```

### Unsupported construction response

HTTP status remains `200`:

```json
{
  "status": "error",
  "gir": null,
  "warnings": [
    {
      "code": "unsupported_construction",
      "message": "Construction is not supported."
    }
  ]
}
```

## `/api/v1/validate-gir`

Recommended response:

```json
{
  "schema_version": "0.2.0",
  "normalized_gir": {},
  "validation_report": {
    "is_valid": true,
    "issues": [],
    "warnings": []
  }
}
```

Behavior:

- structurally invalid payload → HTTP `422`;
- semantic-invalid payload → HTTP `200`, `is_valid: false`;
- unsupported schema version → HTTP `422`;
- valid legacy GIR 0.1 → HTTP `200`, canonical GIR 0.2 output.

## `/api/v1/render/svg`

```json
{
  "schema_version": "0.2.0",
  "media_type": "image/svg+xml",
  "content": "<svg>...</svg>"
}
```

## `/api/v1/render/tikz`

```json
{
  "schema_version": "0.2.0",
  "media_type": "text/x-tex",
  "content": "\\begin{tikzpicture}..."
}
```

## HTTP status matrix

| Situation | HTTP |
|---|---:|
| Success | 200 |
| Ambiguous text command | 200 |
| Unsupported text command | 200 |
| Invalid JSON/Pydantic payload | 422 |
| Semantic-invalid GIR sent to validate | 200 |
| Semantic-invalid GIR sent to render | 422 |
| Unsupported schema version | 422 |
| Request too large | 413 |
| Pipeline timeout | 504 |
| Service not ready | 503 |
| Unexpected internal error | 500 |

## Contract requirements

- Response status fields use `Literal` or enums, not unrestricted strings.
- All public Pydantic models use `extra="forbid"`.
- Operation IDs are explicitly assigned and tested.
- Nullability is explicit in OpenAPI.
- Examples are included for success, clarification and failure responses.

## Main files

```text
src/gir_api/main.py
src/gir_api/router.py
src/gir_api/models.py
src/gir_api/routes/generate.py
src/gir_api/routes/validate.py
src/gir_api/routes/render.py
docs/contracts/API_CONTRACT.md
tests/api/*
```

## Acceptance criteria

- API v1 routes are stable and tested.
- Legacy endpoints remain functional.
- Legacy endpoints do not appear in consumer OpenAPI.
- All public request and response models are strict.
- HTTP behavior is documented and enforced by tests.

---

# PR 5 — Timeouts, Internal Errors and Request Context

**Suggested branch:** `integration/05-api-resilience`

## Goal

Make all failures predictable for TutorBoard and prevent internal implementation details from leaking through FastAPI responses.

## Configuration

Introduce environment-backed settings outside `gir_core`:

```text
GEOMETRYOS_GENERATE_TIMEOUT_SECONDS
GEOMETRYOS_VALIDATE_TIMEOUT_SECONDS
GEOMETRYOS_RENDER_TIMEOUT_SECONDS
GEOMETRYOS_MAX_INPUT_CHARS
GEOMETRYOS_LOG_LEVEL
```

## Timeouts

Each application use case receives an explicit deadline:

```text
generate → generate timeout
validate → validate timeout
render   → render timeout
```

Timeout response:

```json
{
  "type": "about:blank",
  "title": "Geometry pipeline timeout",
  "status": 504,
  "code": "pipeline_timeout",
  "detail": "The operation exceeded its allowed execution time.",
  "request_id": "01J...",
  "retryable": true
}
```

## Problem Details error model

Unexpected internal error:

```json
{
  "type": "about:blank",
  "title": "Internal server error",
  "status": 500,
  "code": "internal_error",
  "detail": "The request could not be processed.",
  "request_id": "01J...",
  "retryable": false
}
```

Clients must never receive:

- Python traceback;
- local filesystem paths;
- package or module names;
- environment values;
- raw third-party exception text.

## Request ID middleware

The middleware should:

1. accept a valid incoming `X-Request-ID` when supplied by an internal gateway;
2. generate a request ID when absent;
3. add it to the response header;
4. include it in structured logs;
5. include it in all error responses.

## Structured logging fields

Minimum fields:

```text
timestamp
level
service
request_id
operation
duration_ms
http_status
schema_version
error_code
```

Full OpenTelemetry integration is not required in Phase 1.

## Required tests

- Slow adapter produces HTTP `504`.
- Slow renderer produces HTTP `504`.
- Unexpected exception produces HTTP `500`.
- Response body contains no traceback.
- Incoming request ID is preserved.
- Missing request ID is generated.
- Ambiguity remains HTTP `200`.
- Semantic validation failures do not become HTTP `500`.
- Unsupported schema version produces a stable `422` error.

## Acceptance criteria

- Every known failure has a stable machine-readable code.
- Unexpected errors use one safe Problem Details response.
- No expected domain result is misclassified as an internal server failure.

---

# PR 6 — Liveness, Readiness and Docker Image

**Suggested branch:** `integration/06-runtime-container`

## Goal

Make GeometryOS independently deployable and runnable as a stateless service.

## `/health`

Liveness must remain lightweight:

```json
{
  "status": "ok",
  "service": "geometryos",
  "version": "0.2.0"
}
```

It returns HTTP `200` when the process can serve HTTP requests.

It must not run validators, renderers or benchmark suites.

## `/ready`

Readiness should execute only cheap deterministic checks:

- application startup completed;
- GIR schema registry is available;
- canonical GIR 0.2 model is loadable;
- a small built-in sentinel scene passes semantic validation;
- the canonical layout and SVG renderer can process the sentinel scene.

Success:

```json
{
  "status": "ready",
  "checks": {
    "schema": "ok",
    "validator": "ok",
    "renderer": "ok"
  }
}
```

Failure:

```json
{
  "status": "not_ready",
  "checks": {
    "schema": "ok",
    "validator": "ok",
    "renderer": "failed"
  }
}
```

Failure returns HTTP `503`.

Readiness must not execute:

- pytest;
- benchmark suites;
- external LLM calls;
- Docker commands;
- full TikZ compilation.

## Docker image

Use a multi-stage Dockerfile.

### Build stage

- Python 3.12 slim;
- install `uv`;
- use locked dependencies;
- build the wheel.

### Runtime stage

- install only runtime dependencies and the built wheel;
- run as a non-root user;
- do not include compilers or dev tools;
- use `/tmp` as the only required writable location;
- set:

```text
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

Recommended command:

```dockerfile
CMD [
  "uvicorn",
  "gir_api.main:app",
  "--host", "0.0.0.0",
  "--port", "8000",
  "--no-access-log"
]
```

Access logging may be replaced by the structured request middleware.

## Docker healthcheck

```dockerfile
HEALTHCHECK CMD python -c \
  "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready')"
```

## New files

```text
Dockerfile
.dockerignore
compose.yaml
deploy/README.md
```

## CI jobs

```text
verify
package
docker-build
container-smoke
```

Container smoke sequence:

```bash
docker run -d --name geometryos-test -p 8000:8000 geometryos:test
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/ready
curl --fail -X POST http://localhost:8000/api/v1/generate ...
docker stop geometryos-test
```

## Acceptance criteria

- Docker image builds from a clean checkout.
- The image contains no dev dependency group.
- The process runs as non-root.
- `/health` and `/ready` behave as documented.
- Generate smoke test succeeds from inside the containerized service.
- Container shutdown completes without forced termination.

---

# PR 7 — Published OpenAPI and TutorBoard Consumer Contract

**Suggested branch:** `integration/07-openapi-consumer-contract`

## Goal

Make TutorBoard integration testable before building the full TutorBoard client.

## OpenAPI artifact

Add:

```text
scripts/export_openapi.py
schemas/openapi.v1.json
```

Commands:

```bash
uv run python scripts/export_openapi.py
uv run python scripts/export_openapi.py --check
```

The OpenAPI freshness check must be included in `make verify`.

## OpenAPI requirements

The committed schema must contain stable:

- service title;
- service version;
- API version;
- operation IDs;
- request schemas;
- response schemas;
- Problem Details schema;
- examples;
- documented HTTP statuses;
- media types;
- GIR schema version fields.

Recommended operation IDs:

```text
generateGeometry
validateGir
renderSvg
renderTikz
getHealth
getReadiness
```

## TutorBoard contract fixtures

Create:

```text
contracts/
└── tutorboard/
    └── v1/
        ├── README.md
        ├── generate-success.request.json
        ├── generate-success.response.json
        ├── generate-ambiguity.request.json
        ├── generate-ambiguity.response.json
        ├── validate-gir.request.json
        ├── validate-gir.response.json
        ├── render-svg.request.json
        └── render-svg.response.json
```

## Consumer contract tests

Create:

```text
tests/contracts/test_tutorboard_generate.py
tests/contracts/test_tutorboard_validate.py
tests/contracts/test_tutorboard_render.py
tests/contracts/test_openapi_contract.py
```

Tests must verify:

1. Endpoint exists.
2. Operation ID is stable.
3. Required fields remain required.
4. Field types do not change unexpectedly.
5. Response is compatible with a generated TypeScript client.
6. GIR 0.1 is upgraded to GIR 0.2.
7. Unknown schema version is rejected.
8. Ambiguity contains `code`, `message` and `options`.
9. SVG response declares `image/svg+xml`.
10. Internal errors conform to Problem Details.

## Breaking-change detection

At minimum, the OpenAPI check must fail when:

- an API v1 endpoint is removed;
- a required field is removed;
- a field type changes;
- an enum is narrowed;
- a success status code changes;
- a response schema disappears;
- an operation ID changes.

A custom subset/snapshot checker is sufficient for `0.2.0`. Pact or another external contract platform is not required yet.

## Acceptance criteria

- `schemas/openapi.v1.json` is deterministic.
- Stale OpenAPI fails CI.
- TutorBoard consumer tests pass.
- Legacy routes are excluded from consumer OpenAPI.
- A future TypeScript client can be generated using only `openapi.v1.json`.

---

# PR 8 — GeometryOS 0.2.0 Release Candidate

**Suggested branch:** `release/geometryos-0.2.0`

## Goal

Produce the first stable integration-ready release.

## Version updates

Update all version sources consistently:

```text
pyproject.toml
FastAPI application metadata
OpenAPI metadata
README.md
container labels
```

Target version:

```text
0.2.0
```

## Documentation

Create or finalize:

```text
CHANGELOG.md
docs/INTEGRATION_GUIDE.md
docs/ERROR_MODEL.md
docs/COMPATIBILITY.md
docs/DEPLOYMENT.md
```

## Integration guide contents

The guide must document:

- base URL;
- API v1 endpoints;
- GIR schema version;
- client timeout recommendations;
- retry policy;
- request ID behavior;
- handling `needs_clarification`;
- handling HTTP `504`;
- legacy GIR compatibility;
- curl examples;
- TutorBoard integration recommendations.

## Release workflow

```text
make verify
    ↓
build wheel
    ↓
install wheel smoke test
    ↓
build Docker image
    ↓
container smoke test
    ↓
publish generated schemas
    ↓
publish Docker image
    ↓
create Git tag v0.2.0
```

## Docker tags

```text
ghcr.io/artemlevin/geometryos:0.2.0
ghcr.io/artemlevin/geometryos:0.2
ghcr.io/artemlevin/geometryos:sha-<commit>
```

TutorBoard must use the immutable `0.2.0` tag rather than `latest`.

## Final verification

```bash
uv sync --frozen --dev
make verify
uv build
docker build -t geometryos:0.2.0 .
docker run ...
curl /health
curl /ready
curl /api/v1/generate
curl /api/v1/validate-gir
curl /api/v1/render/svg
curl /api/v1/render/tikz
```

## Acceptance criteria

- Tag `v0.2.0` points to a green CI commit.
- Published schemas match source code from the same commit.
- Docker image is built from the same commit.
- TutorBoard consumer contracts pass.
- No undocumented breaking change remains.

---

# 7. Complete test matrix

## 7.1. Unit tests

| Area | Required checks |
|---|---|
| Pydantic models | strict fields, discriminated unions, serialization |
| Compatibility | GIR 0.1 → GIR 0.2 |
| Semantic validator | missing refs, wrong types, duplicate IDs |
| Normalization | determinism and idempotency |
| Application pipeline | stage order and failure propagation |
| Error mapping | stable machine-readable codes |
| Readiness | each individual readiness check |

## 7.2. Important properties

Normalization idempotency:

```text
normalize(normalize(scene)) == normalize(scene)
```

Serialization round-trip:

```text
parse(serialize(scene)) == scene
```

Legacy compatibility:

```text
upgrade_0_1(payload) → valid GIR 0.2
```

## 7.3. API tests

Required scenarios:

```text
generate success
generate needs_clarification
generate unsupported
generate malformed
generate input too large
generate timeout

validate valid
validate semantic-invalid
validate structural-invalid
validate legacy GIR 0.1
validate unsupported schema version

render SVG valid
render SVG semantic-invalid
render SVG timeout

render TikZ valid
render TikZ semantic-invalid
render TikZ timeout

health success
ready success
ready failure

unexpected internal exception
request ID propagation
request ID generation
```

## 7.4. Contract tests

Contract tests must validate:

- field presence;
- required/optional status;
- field type;
- enum values;
- nullability;
- HTTP status;
- media type;
- schema version;
- backward compatibility behavior.

## 7.5. Container tests

- process runs as non-root;
- health endpoint works;
- readiness endpoint works;
- filesystem writes are not required outside `/tmp`;
- SIGTERM stops the process cleanly;
- API smoke tests pass;
- dev-only packages are absent.

---

# 8. Target `make verify` contract

By the end of Phase 1, `make verify` should run:

```text
1. ruff check
2. ruff format --check
3. mypy
4. pytest
5. GIR schema freshness check
6. OpenAPI freshness check
7. benchmark suites
8. CLI benchmark smoke
9. CLI schema smoke
10. wheel build
11. installed-package import smoke
```

Docker build and container smoke tests should remain a separate CI job because Docker may not be available in every local development environment.

Expected successful output:

```text
✓ ruff
✓ formatting
✓ mypy
✓ pytest
✓ GIR schema
✓ OpenAPI
✓ benchmarks
✓ CLI
✓ package build
✓ installation smoke

All GeometryOS verification checks passed.
```

---

# 9. Risks and mitigation

## 9.1. Expanding GIR too early

**Risk:** adding squares, circles, arbitrary polygons, 3D and advanced constraints before the integration boundary is stable.

**Mitigation:** GIR 0.2 stabilizes the current supported MVP surface. Feature expansion belongs to later versions driven by TutorBoard use cases.

## 9.2. Two competing version fields

**Risk:** keeping both `version` and `schema_version` in canonical GIR.

**Mitigation:** canonical GIR uses only `schema_version`; legacy `version` is handled exclusively by the compatibility adapter.

## 9.3. API and CLI divergence

**Risk:** different validation and normalization paths.

**Mitigation:** both delivery layers call `gir_application`.

## 9.4. Timeout response while CPU work continues

**Risk:** cancelling Python threads does not always stop CPU-bound work immediately.

**Mitigation for 0.2.0:** use bounded operations and documented deadlines. Process isolation can be added later when solver or LLM workloads become heavy.

## 9.5. Readiness becomes a benchmark suite

**Risk:** expensive readiness probes overload the service.

**Mitigation:** use only one small in-memory sentinel scene.

## 9.6. Accidental OpenAPI breaking changes

**Risk:** FastAPI model refactors silently change the consumer contract.

**Mitigation:** commit `openapi.v1.json`, check freshness and run breaking-change assertions.

---

# 10. Final milestone

TutorBoard development can begin immediately after GeometryOS 0.2.0 demonstrates the following reproducible scenario:

```text
clean GeometryOS Docker container
    +
published OpenAPI v1
    +
TutorBoard consumer contract tests
    +
successful request:
"Постройте треугольник ABC и проведите высоту AH к BC"
    ↓
valid GIR 0.2
    ↓
SVG
```

This milestone means GeometryOS is sufficiently stable for integration. It does not require a general solver, 3D engine or handwritten sketch recognition before TutorBoard work begins.
