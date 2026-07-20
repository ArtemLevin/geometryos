# ADR-003: Stable HTTP API v1

## Status

Accepted for the GeometryOS integration-ready phase.

## Context

GeometryOS originally exposed only unversioned FastAPI routes. After the canonical application pipeline was introduced, transport handlers became thin enough to support a stable consumer contract without duplicating geometry policy. TutorBoard needs predictable paths, operation IDs, strict DTOs and generated-client-friendly response types.

## Decision

Expose the stable API under `/api/v1` with separate strict request and response models. Keep the existing unversioned routes as hidden compatibility aliases.

The v1 generation response is a discriminated union over the domain status. Ambiguity and unsupported constructions remain HTTP 200 because they are expected domain outcomes rather than transport failures. Validation returns HTTP 200 for semantic-invalid GIR and rendering returns HTTP 422 for semantic-invalid GIR.

Legacy aliases use the same application services but retain their old JSON shapes. They are excluded from OpenAPI.

## Consequences

### Positive

- TutorBoard can pin a stable namespace and operation IDs;
- generated clients can narrow generation responses by status;
- request constraints are visible in OpenAPI;
- legacy users are not broken immediately;
- no geometry orchestration is duplicated;
- GIR, package and API versions remain independent.

### Negative

- v1 and legacy require separate transport DTOs and presenters;
- compatibility aliases increase route-level test coverage;
- warning strings must be mapped to stable public warning codes.

## Rejected alternatives

- unversioned routes provide no explicit compatibility boundary;
- header or query-parameter versioning is less visible to human and generated clients;
- removing legacy routes immediately would break existing callers;
- sharing one DTO between v1 and legacy would prevent stronger v1 constraints;
- publishing a committed OpenAPI artifact now would mix this contract PR with the later TutorBoard consumer-contract PR.

## Follow-up

The next resilience PR adds timeouts, request context and stable internal-error responses. A later contract PR commits and freshness-checks the OpenAPI artifact.
