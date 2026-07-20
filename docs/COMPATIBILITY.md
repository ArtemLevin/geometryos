# GeometryOS Compatibility Policy

## Independent version domains

GeometryOS maintains three independent version domains:

| Domain | Current value in this phase | Meaning |
|---|---|---|
| Python package | `0.1.0` | Distribution version until the release PR |
| HTTP API | `v1` | Stable TutorBoard-facing HTTP contract |
| OpenAPI info | `1.0.0` | Version of the v1 HTTP schema |
| GIR schema | `0.2.0` | Mathematical data contract |

A change to one domain does not automatically change the others.

## HTTP API compatibility

Stable consumer routes use `/api/v1`. Unversioned routes remain temporary compatibility aliases, retain their pre-v1 JSON shapes and are excluded from OpenAPI.

Removing an unversioned alias requires a separately documented breaking change and confirmation that known consumers have migrated. New stable fields and constraints are added to v1 DTOs, not retrofitted into legacy response shapes.

## Canonical writer contract

Every current GeometryOS writer emits only GIR `0.2.0` with the field `schema_version`. Canonical output never contains the legacy field `version`.

The machine-readable contract is published as `schemas/gir-0.2.schema.json`. Consumers must pin this versioned artifact rather than assume that an unversioned schema path always describes the same contract.

## Legacy reader contract

The reader accepts exactly one legacy marker: `version: "0.1"`. It upgrades that marker to `schema_version: "0.2.0"` before Pydantic structural validation.

The compatibility layer does not repair objects, constraints, references, metadata or construction steps. A structurally or semantically invalid legacy scene remains invalid after its version marker is upgraded.

## Rejected GIR inputs

GeometryOS rejects:

- scenes without a version marker;
- scenes containing both `version` and `schema_version`;
- unknown canonical versions;
- unknown legacy versions;
- future versions that have not been explicitly implemented.

Unknown versions are never parsed as the current schema on a best-effort basis.

## Change classification

A GIR patch change may clarify documentation or validation without changing the accepted data shape. A backward-compatible minor change may add an optional field or a new explicitly supported union member. A major change removes, renames or changes the meaning or type of an existing field.

New object or constraint union variants may still be breaking for exhaustive generated clients. Consumer compatibility must therefore be evaluated before publishing them.

## Required GIR change procedure

Any GIR model change must update, in the same pull request:

1. Pydantic models;
2. the versioned JSON Schema artifact;
3. schema freshness tests;
4. canonical benchmark fixtures;
5. compatibility tests where applicable;
6. `docs/GIR_SPEC.md` and this policy;
7. TutorBoard consumer contracts once they exist.

## Removing GIR 0.1 support

Legacy GIR support may be removed only in a separately documented breaking change after all known persisted scenes and consumers have migrated. Until then, legacy support remains read-only: no current writer may produce GIR 0.1.

## Runtime failure compatibility

Stable `/api/v1` infrastructure failures use Problem Details with stable `code` and `request_id` fields. Successful payloads and expected domain results remain governed by the API v1 DTOs. Unversioned aliases preserve their existing JSON bodies, with the additive `X-Request-ID` response header.

Changing a Problem Details code, removing request correlation or changing a published HTTP status requires a documented API compatibility review.

## Operational probe compatibility

`/health` is the existing liveness contract and continues to return HTTP 200 with `{"status":"ok"}` whenever the process can serve HTTP.

`/ready` is an additive readiness contract. It returns the same strict JSON schema for HTTP 200 and 503, uses `status` values `ready` or `not_ready`, and reports named lifecycle, settings and executor checks. Readiness responses are non-cacheable and receive `X-Request-ID`.

Changing either probe path, the `200/503` semantics, the readiness response fields or the stable check names requires an operational compatibility review.

## Container integration contract

Until the release PR, the Docker image is an integration artifact rather than a published versioned release. The following deployment properties are nevertheless protected by review and CI:

- application port `8000`;
- non-root runtime UID/GID `10001:10001`;
- exec-form single-process Uvicorn command without reload;
- `/ready` Docker healthcheck;
- `SIGTERM` stop signal with a 20-second Uvicorn graceful timeout and 30-second Compose grace period;
- operation with a read-only root filesystem and tmpfs `/tmp`;
- loopback-only Compose host binding by default.

Weakening these properties or introducing a new required environment variable requires a documented deployment compatibility review and updated container smoke coverage.
