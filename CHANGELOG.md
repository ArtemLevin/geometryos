# Changelog

All notable changes to GeometryOS are documented in this file.

The project follows Semantic Versioning for the GeometryOS service and Python distribution. HTTP API, GIR schema and TutorBoard consumer contracts are versioned independently.

## [Unreleased]

## [0.2.0] - 2026-07-21

### Added

- Formal GIR `0.2.0` machine contract with strict Pydantic models and a committed JSON Schema.
- Canonical application pipeline shared by the HTTP API and CLI.
- Stable HTTP API v1 for generation, validation and SVG/TikZ rendering.
- Machine-readable Problem Details, request correlation and operation-specific timeouts.
- Liveness and readiness probes.
- Hardened multi-stage Docker image and Docker Compose deployment.
- Deterministic OpenAPI v1 artifact and backward-compatibility checks.
- Executable TutorBoard v1 consumer fixtures and TypeScript generation smoke tests.
- Reproducible wheel, source distribution, release manifest, checksums and CycloneDX SBOM.
- Tag-driven GitHub Release and GHCR publication workflow.

### Changed

- GeometryOS is now packaged as an independently deployable GIR-first service.
- Legacy GIR `0.1` input is upgraded to canonical GIR `0.2.0` output.
- The package description now reflects the integration-ready geometry compiler service rather than a skeleton.

### Security

- Runtime containers execute as a non-root user with a read-only root filesystem.
- Container privileges are minimized through capability removal and restricted runtime settings.
- Internal exceptions are sanitized before being returned to clients.
- Release candidates include locked dependency auditing, SHA-256 checksums and provenance-ready artifacts.
- Versioned container images are published without a mutable `latest` tag.

### Known limitations

- Natural-language construction coverage remains intentionally bounded and rule-based.
- No external LLM provider is included in this release.
- HTTP operation timeouts are soft for already-running synchronous worker threads.
- Authentication, TLS termination, rate limiting and distributed observability are outside this release.
- The published container target is `linux/amd64`.
