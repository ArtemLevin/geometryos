# GeometryOS Compatibility Policy

## Independent version domains

GeometryOS maintains three independent version domains:

| Domain | Current value in this phase | Meaning |
|---|---|---|
| Python package | `0.1.0` | Distribution version |
| HTTP API | unversioned | Current delivery routes |
| GIR schema | `0.2.0` | Mathematical data contract |

A change to one domain does not automatically change the others.

## Canonical writer contract

Every current GeometryOS writer emits only GIR `0.2.0` with the field `schema_version`. Canonical output never contains the legacy field `version`.

## Legacy reader contract

The reader accepts exactly one legacy marker: `version: "0.1"`. It upgrades that marker to `schema_version: "0.2.0"` before Pydantic structural validation.

The compatibility layer does not repair objects, constraints, references, metadata or construction steps. A structurally or semantically invalid legacy scene remains invalid after its version marker is upgraded.

## Rejected inputs

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

## Required change procedure

Any GIR model change must update, in the same pull request:

1. Pydantic models;
2. the versioned JSON Schema artifact;
3. schema freshness tests;
4. canonical benchmark fixtures;
5. compatibility tests where applicable;
6. `docs/GIR_SPEC.md` and this policy;
7. future TutorBoard consumer contracts once they exist.

## Removing GIR 0.1 support

Legacy support may be removed only in a separately documented breaking change after all known persisted scenes and consumers have migrated. Until then, legacy support remains read-only: no current writer may produce GIR 0.1.
