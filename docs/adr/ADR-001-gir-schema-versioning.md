# ADR-001: GIR schema versioning

- Status: Accepted
- Date: 2026-07-20

## Context

GIR 0.1 used an unconstrained `version: str` field. Any string could pass structural parsing, the field did not define a compatibility policy, and internal writers, API, CLI and benchmark fixtures all treated the label as informal metadata. TutorBoard integration requires a deterministic machine contract and predictable rejection of unknown versions.

## Decision

GIR 0.2 uses a required `schema_version` field with the exact value `0.2.0`. The canonical Pydantic model and generated JSON Schema contain no `version` field.

A single compatibility boundary accepts legacy `version: "0.1"` and converts only that top-level marker to `schema_version: "0.2.0"`. Missing, conflicting and unsupported versions are rejected with stable Pydantic error types.

Package, HTTP API and GIR schema versions remain independent.

## Alternatives considered

- Keep `version: str`: rejected because it does not enforce a contract.
- Use a numeric version: rejected because numeric JSON values lose semantic-version precision.
- Use `0.2` instead of `0.2.0`: rejected in favor of an explicit semantic-version format.
- Keep both fields in the canonical model: rejected because it creates two sources of truth.
- Reject all GIR 0.1 immediately: rejected because existing fixtures and potential saved scenes need a bounded migration window.
- Accept unknown minor versions optimistically: rejected because field meaning and union variants may change.

## Consequences

Positive consequences:

- every canonical scene is self-identifying;
- JSON Schema can be pinned by consumers;
- API, CLI and direct Python parsing share one compatibility path;
- future migration warnings can reuse compatibility metadata;
- unknown future schemas fail safely.

Costs:

- all current fixtures and writers must migrate;
- the versioned schema artifact must be regenerated on model changes;
- legacy support must remain tested until explicitly removed.

## Migration

All current writers and benchmark fixtures move to GIR 0.2. One legacy altitude fixture remains under `tests/fixtures/gir/v0_1` solely to verify compatibility. The old unversioned schema artifact is replaced by `schemas/gir-0.2.schema.json`.
