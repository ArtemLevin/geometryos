# GeometryOS Error Model

GeometryOS separates expected geometry-domain outcomes from HTTP/transport failures.

## Domain outcomes

`POST /api/v1/generate` returns HTTP `200` for all expected domain outcomes:

| Status | Meaning | Client action |
|---|---|---|
| `success` | GIR and requested artifacts were produced | consume result |
| `needs_clarification` | request is ambiguous | ask the user to choose or clarify |
| `error` | construction is unsupported or cannot be produced | show structured warning; do not retry unchanged input |

These outcomes are discriminated by the response `status` field. They are not Problem Details.

## HTTP failures

Failures under `/api/v1` use media type:

```text
application/problem+json
```

Canonical shape:

```json
{
  "type": "urn:geometryos:problem:operation-timeout",
  "title": "Operation timed out",
  "status": 504,
  "detail": "The generate operation exceeded its configured time limit.",
  "instance": "/api/v1/generate",
  "code": "operation_timeout",
  "request_id": "request-id",
  "errors": []
}
```

Stable fields for client logic are `status`, `code`, `request_id` and structured `errors`. Human-readable `title` and `detail` may improve without changing the contract.

## Error matrix

| Code/state | HTTP | Automatic retry |
|---|---:|---|
| `input_too_large` | 413 | no |
| `request_validation_failed` | 422 | no |
| `semantic_validation_failed` | 422 | no |
| `not_found` | 404 | no |
| `method_not_allowed` | 405 | no |
| `operation_timeout` | 504 | limited |
| `internal_error` | 500 | limited |
| readiness `not_ready` | 503 | yes, with backoff |

Readiness `503` uses `ReadinessResponse`, not Problem Details.

## Validation errors

`errors` entries contain:

```text
code
message
location
```

`location` is a list of object keys and array indices identifying the rejected field. Clients should display a safe summary and may map locations to form fields.

## Internal errors

Unexpected exceptions are sanitized. Responses never expose:

- Python tracebacks;
- local filesystem paths;
- environment values;
- raw third-party exception messages;
- prompt, GIR, SVG or TikZ content.

Use `request_id` to correlate the client-visible failure with structured service logs.

## Timeout semantics

Timeouts are operation-specific and currently implemented as soft deadlines around synchronous worker threads. GeometryOS can return HTTP `504` while a worker that already started may finish later. Operations in `0.2.0` are side-effect-free, which allows a bounded client retry policy.

## Retry guidance

For retryable cases:

1. use exponential backoff with jitter;
2. cap attempts;
3. preserve correlation lineage;
4. stop retrying when a definitive domain or validation response is received;
5. avoid concurrent duplicate retries for the same user action.
