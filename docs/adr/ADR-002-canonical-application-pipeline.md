# ADR-002: Canonical application pipeline

## Status

Accepted for the GeometryOS integration-ready phase.

## Context

Before this decision, `/generate`, `/render/*` and CLI render commands each assembled parts of the sequence `validate → normalize → validate → render`. This duplicated policy across delivery adapters and made future TutorBoard integration, timeout handling and error mapping likely to diverge.

## Decision

Introduce a transport-agnostic `gir_application` package with typed commands, results and callable dependency ports. The package owns the canonical orchestration sequence and exposes `generate_geometry`, `validate_geometry`, `prepare_geometry` and `render_geometry`.

FastAPI routes and Typer commands become thin adapters. They retain responsibility for HTTP status codes, response DTOs, terminal output and process exit codes.

## Consequences

### Positive

- validation and rendering policy has one implementation;
- API, CLI and future TutorBoard integrations receive consistent behavior;
- every stage can be tested independently;
- renderer invocation is guaranteed to happen only after both validation gates;
- later timeout, tracing and structured error work has one application boundary;
- no dependency-injection framework or new runtime package is required.

### Negative

- GeometryOS gains another package and a small mapping layer;
- application contracts overlap structurally with current HTTP DTOs;
- adding a new output format requires updating typed application artifacts.

## Rejected alternatives

- keeping orchestration inside API routes would leave CLI and TutorBoard behavior duplicated;
- moving orchestration into `gir_core` would make the pure mathematical core depend on adapters and renderers;
- allowing renderers to validate or repair scenes would make rendering a source of mathematical policy;
- placing a shared helper in `gir_api` would keep CLI coupled to an HTTP package;
- adding a dependency-injection framework would be disproportionate to the current synchronous MVP.
