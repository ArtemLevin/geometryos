# GeometryOS Application Pipeline

## Purpose

`gir_application` is the transport-agnostic orchestration boundary between GeometryOS delivery adapters and the mathematical/rendering packages.

```text
HTTP API ─┐
          ├── gir_application ── gir_ai
CLI ──────┘                    ├─ gir_core
Future TutorBoard adapter ─────└─ gir_render
```

API routes and CLI commands translate their input into application commands. They do not assemble validation, normalization and rendering stages themselves.

## Canonical flow

Generation uses one ordered pipeline:

```text
text adapter
→ draft GIR
→ semantic validation
→ normalization
→ semantic validation
→ requested renderers
→ typed result
```

Rendering an existing GIR starts at the first semantic validation stage. Validation-only operations deliberately do not normalize the input.

## Short-circuit rules

- `needs_clarification` and adapter errors without GIR do not invoke validation, normalization or rendering;
- semantic-invalid draft GIR is not normalized;
- semantic-invalid normalized GIR is not rendered;
- a renderer is called only when its output format was requested;
- each requested renderer is called at most once;
- renderers receive only normalized GIR that passed both validation gates.

## Public application functions

```python
from gir_application import GenerateGeometryCommand, OutputFormat, generate_geometry

result = generate_geometry(
    GenerateGeometryCommand(
        input_type="text",
        input="Постройте треугольник ABC",
        outputs=frozenset({OutputFormat.SVG}),
    )
)
```

The supported entry points are:

- `generate_geometry()`;
- `validate_geometry()`;
- `prepare_geometry()`;
- `render_geometry()`.

`prepare_geometry()` is public for trusted internal integrations that need canonical validated GIR without rendering.

## Contracts versus transports

Application commands and results do not contain HTTP status codes, `HTTPException`, Typer exit codes or request objects. Transport adapters remain responsible for:

- HTTP request and response DTOs;
- mapping invalid render requests to HTTP 422;
- CLI stdout, stderr and exit codes;
- future timeout and error-response mapping.

## Dependency ports

`GeometryPipelineDependencies` contains callable ports for the text adapter, semantic validator, normalizer and renderers. The production wiring uses the current rule-based adapter and SVG/TikZ implementations. Unit tests replace individual stages with deterministic fakes without a dependency-injection framework.

## Adding a renderer

A new renderer requires:

1. a new `OutputFormat` member;
2. a typed field in `RenderedArtifacts`;
3. a renderer port in `GeometryPipelineDependencies`;
4. dispatch in `_render_artifacts()`;
5. application tests proving validation gates and one-call dispatch;
6. transport mapping in API/CLI when exposed publicly.

A renderer must never validate, normalize or repair GIR by itself.

## Adding an adapter

A new parser or AI adapter may produce draft GIR and adapter metadata. It must be wired through an application port and must not call renderers. All produced GIR continues through the same validation and normalization gates.
