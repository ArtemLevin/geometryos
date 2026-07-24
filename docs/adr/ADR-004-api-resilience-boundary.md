# ADR-004: API resilience boundary

## Status

Accepted for the GeometryOS integration-ready phase.

## Context

Stable API v1 introduced predictable paths and DTOs, but request correlation, deadlines, transport failures and logging were still implicit. Synchronous application functions were called directly by routes, and unexpected exceptions could expose framework-default behavior that was difficult for TutorBoard to correlate with server logs.

## Decision

Keep resilience policy in `gir_api` and leave `gir_application` synchronous and transport agnostic.

- create FastAPI applications through `create_app()` with validated environment-backed settings;
- run synchronous application calls in AnyIO worker threads;
- apply separate soft deadlines to generate, validate and render operations;
- attach or generate `X-Request-ID` through pure ASGI middleware and propagate it with `ContextVar`;
- return `application/problem+json` for v1 transport and infrastructure failures;
- preserve legacy JSON bodies and synchronous Python aliases;
- emit structured JSON completion and internal-error logs without request payloads or exception messages.

## Consequences

### Positive

- TutorBoard can correlate every failure with one request identifier;
- successful API v1 responses remain unchanged;
- timeout policy has one implementation;
- event-loop threads are not blocked by synchronous geometry work;
- v1 failures have stable codes and sanitized bodies;
- tests can inject settings and fake executors through the application factory;
- the mathematical core remains independent from FastAPI, AnyIO and environment configuration.

### Negative

- an expired worker-thread operation cannot be forcibly terminated and may finish later;
- v1 and legacy failure presenters remain different during migration;
- the API package gains settings, middleware, execution and logging modules;
- future side-effecting adapters must implement cooperative cancellation.

## Rejected alternatives

- placing deadlines in `gir_core` would couple mathematics to delivery policy;
- placing timeout logic independently in routes would duplicate behavior;
- converting the entire application layer to async would spread transport concerns through pure code;
- process pools would add serialization, startup and cross-platform complexity before profiling justifies them;
- Unix signals would not be portable to the supported Windows development environment;
- `BaseHTTPMiddleware` was rejected in favor of predictable `ContextVar` and response-header behavior in pure ASGI middleware;
- publishing tracebacks or exception messages to clients was rejected as an information leak;
- adding a structured-logging framework was unnecessary for the current event model.

## Follow-up

A later deployment PR may add readiness, process lifecycle handling and reverse-proxy body limits. Observability work may add metrics and distributed tracing while preserving the request ID and Problem Details contracts defined here.

## Browser contract extension

The resilience boundary also owns exact-origin CORS and the stable `service_unavailable` response. Request correlation remains the outer middleware so preflight and early CORS responses receive `X-Request-ID`; stable application operations are rejected before executor invocation whenever the local readiness snapshot is degraded.
