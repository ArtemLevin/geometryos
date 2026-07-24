# ADR-006: Published OpenAPI and TutorBoard consumer contract

## Context

GeometryOS already exposes a stable API v1, but runtime `/openapi.json` alone is not a reviewable or versioned integration artifact. TutorBoard needs a contract that can be consumed and tested without starting the service.

## Decision

- Runtime FastAPI/Pydantic definitions remain the source of generation.
- `schemas/openapi.v1.json` is a deterministic committed artifact and must never be edited manually.
- `make verify` checks OpenAPI and TutorBoard fixture freshness.
- Pull-request CI compares the candidate artifact with the base branch and blocks detected breaking changes.
- `contracts/tutorboard/v1` contains executable, versioned request/response fixtures.
- TypeScript types are generated temporarily with pinned tooling and compiled, but generated files are not committed.
- Existing operation IDs remain stable; legacy unversioned routes remain excluded.
- HTTP API, GIR schema, package, and consumer-contract versions remain independent.

## Consequences

API changes become visible as generated artifact diffs, stale contracts fail CI, and TutorBoard can generate a client from one file. CI gains a Node-based consumer job and contract fixtures must be intentionally regenerated when behavior changes.

## Rejected alternatives

Runtime-only OpenAPI, handwritten OpenAPI, committed generated TypeScript clients, immediate Pact adoption, reading repository fixtures from runtime code, renaming operation IDs, and coupling package version to API version were rejected.

## Correlation headers and availability

The published OpenAPI includes the optional `X-Request-ID` request parameter, response header declarations for every status, and the stable `503` Problem Details outcome. The compatibility checker treats removal or narrowing of these headers as breaking and newly declared response statuses as review-required additions.
