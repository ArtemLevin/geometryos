# GIR Specification 0.2

## Purpose

Geometry Intermediate Representation (GIR) is the canonical mathematical contract between parsers, validators, layout engines, renderers and external consumers such as TutorBoard. GIR describes what a construction means independently of screen coordinates and UI state.

## Canonical schema version

Every canonical scene must contain:

```json
{"schema_version":"0.2.0"}
```

`schema_version` is required and is serialized in every GIR 0.2 output. The legacy field `version` is not part of the GIR 0.2 schema.

## Scene structure

A scene contains:

- `schema_version`: exactly `0.2.0`;
- `scene_type`: currently exactly `2d`;
- `objects`: typed mathematical objects;
- `constraints`: typed semantic relationships;
- `construction_steps`: an ordered explanatory construction sequence;
- `metadata`: optional non-semantic producer metadata.

## Objects

The current object union includes points, segments, lines, rays, circles, triangles, angles and labels. Object identifiers are stable references used by constraints and construction steps.

## Constraints

The current constraint union includes membership, collinearity, non-collinearity, parallelism, perpendicularity, equal length, midpoint, intersection, altitude, median, angle bisector, circumcircle and incircle relationships.

## Structural validation

Pydantic validates required fields, discriminated unions, field types, forbidden extra fields and the exact GIR schema version before semantic validation runs.

Unknown, missing or conflicting schema versions are rejected. GeometryOS never attempts best-effort parsing of an unknown GIR version.

## Semantic validation

Semantic validation is structural and type-aware, but it is not a geometric solver. It checks, among other invariants:

- referenced objects and constraints exist;
- object and constraint ids are unique;
- point roles reference points;
- line-like roles reference segments, lines or rays as appropriate;
- segment endpoints, triangle vertices and angle points are distinct;
- altitude, median, midpoint, angle-bisector, circumcircle and incircle roles target compatible types;
- construction steps reference existing objects and constraints.

It does not prove global constructibility or solve arbitrary systems of geometric constraints.

## Normalization and rendering

Compatibility conversion completes before a `GirScene` exists. Normalization therefore receives canonical GIR 0.2 only. Renderers receive semantically valid canonical scenes and must not invent or repair geometry.

## GIR versus board state

GIR does not store TutorBoard presentation state such as camera position, zoom, selection, cursors, toolbar state, z-index, WebSocket state or collaboration metadata. Layout coordinates and visual interaction state belong to dedicated downstream models.

## Compatibility

GeometryOS temporarily reads legacy GIR 0.1 payloads containing `version: "0.1"`. The compatibility layer performs one transformation only: it replaces that top-level marker with `schema_version: "0.2.0"`. It does not add missing geometry, remove unknown fields or repair semantic errors.

All writers, API outputs, CLI-generated scenes and benchmark fixtures use GIR 0.2. See `docs/COMPATIBILITY.md` for the compatibility policy.
