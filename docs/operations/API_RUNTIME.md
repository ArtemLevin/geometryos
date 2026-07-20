# GeometryOS API Runtime

## Purpose

The stable HTTP API is wrapped by a transport-only resilience boundary. Request correlation, deadlines, Problem Details and logging live in `gir_api`; the mathematical core and application pipeline remain synchronous and transport agnostic.

## Configuration

GeometryOS reads the following environment variables at application startup:

| Variable | Default | Valid range |
|---|---:|---:|
| `GEOMETRYOS_GENERATE_TIMEOUT_SECONDS` | `15` | `> 0`, up to `300` |
| `GEOMETRYOS_VALIDATE_TIMEOUT_SECONDS` | `5` | `> 0`, up to `60` |
| `GEOMETRYOS_RENDER_TIMEOUT_SECONDS` | `10` | `> 0`, up to `120` |
| `GEOMETRYOS_MAX_INPUT_CHARS` | `20000` | `1..20000` |
| `GEOMETRYOS_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

Invalid values fail fast while the FastAPI application is created.

PowerShell example:

```powershell
$env:GEOMETRYOS_GENERATE_TIMEOUT_SECONDS = "20"
$env:GEOMETRYOS_RENDER_TIMEOUT_SECONDS = "10"
$env:GEOMETRYOS_LOG_LEVEL = "INFO"
uv run uvicorn gir_api.main:app --reload
```

## Request correlation

Every HTTP response contains `X-Request-ID`. A caller-provided value is reused only when it matches `^[A-Za-z0-9._-]{1,128}$`; otherwise GeometryOS generates a UUID. The same identifier appears in v1 Problem Details and structured server logs.

The header is additive across health, stable v1, legacy compatibility and error responses; it does not alter existing JSON success bodies.

Request and operation identifiers are stored in `ContextVar` instances and reset after every request. Parallel requests therefore retain isolated context.

## Problem Details

Infrastructure and transport failures under `/api/v1` use `application/problem+json` with this stable shape:

```json
{
  "type": "urn:geometryos:problem:operation-timeout",
  "title": "Operation timed out",
  "status": 504,
  "detail": "The generate operation exceeded its configured time limit.",
  "instance": "/api/v1/generate",
  "code": "operation_timeout",
  "request_id": "6dbf7b27-b7bd-4ee5-8ac0-5e350b861169",
  "errors": []
}
```

Current stable failure codes include:

- `request_validation_failed`;
- `semantic_validation_failed`;
- `input_too_large`;
- `operation_timeout`;
- `not_found`;
- `method_not_allowed`;
- `internal_error`.

Unexpected errors never expose exception messages, tracebacks, request bodies, local paths, GIR payloads or rendered content. Legacy endpoints retain their pre-v1 JSON error shapes.

## Deadlines

HTTP handlers invoke synchronous application functions through AnyIO worker threads. Separate soft deadlines apply to generation, validation and rendering. When a deadline expires, the API stops waiting and returns HTTP `504`.

Python cannot safely terminate a running worker thread. The abandoned synchronous operation may therefore finish after the response has been sent. This is safe for the current deterministic, side-effect-free pipeline. Future network or LLM adapters must observe deadlines cooperatively and cancel their own external calls.

## Input limits

The public v1 DTO accepts at most 20,000 characters. `GEOMETRYOS_MAX_INPUT_CHARS` may impose a stricter operational limit:

- input above the public schema limit is rejected as request validation with HTTP `422`;
- input within the public schema but above the configured operational limit returns HTTP `413`.

The operational limit counts Unicode code points after Pydantic whitespace normalization. It is not a raw HTTP body byte limit; reverse-proxy body limits belong to the deployment layer.

## Structured logging

The `geometryos.api` logger emits one JSON `request_completed` event per request. Fields include:

- timestamp and level;
- request ID;
- operation;
- method and path;
- status code;
- duration in milliseconds;
- stable error code when applicable.

Internal exceptions produce a separate `internal_error` event with the exception type. At `DEBUG`, sanitized stack-frame metadata may be included, but exception messages and request data remain excluded.

## Deferred production controls

This runtime layer does not add readiness checks, containers, process lifecycle management, reverse-proxy limits, authentication, rate limiting, Prometheus or OpenTelemetry. Those concerns remain separate from the stable API resilience contract.
