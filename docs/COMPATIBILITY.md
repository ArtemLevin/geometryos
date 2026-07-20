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
