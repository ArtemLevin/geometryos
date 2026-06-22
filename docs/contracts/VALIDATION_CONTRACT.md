# Validation Contract

## Purpose
Define the contract for GIR structural semantic validation.
Validation verifies that a parsed `GirScene` is internally coherent enough for normalization and rendering without claiming to solve or prove geometry.

## Input
A Pydantic-validated `GirScene` containing:

- objects;
- constraints;
- construction steps;
- optional metadata.

## Output
A `ValidationReport` with:

- `is_valid` boolean;
- `issues` for blocking errors;
- `warnings` for non-blocking findings.

## Invariants
- GIR is the source of truth.
- Layers do not bypass validation.
- Renderers never call AI.
- Validators check references and expected target object types.
- Validators do not prove full geometric constructibility.

## Type compatibility rules
The semantic validator must reject existing objects used with the wrong constraint role:

- `belongs_to.point` must be `point`.
- `collinear.points` and `non_collinear.points` must be `point` objects.
- `parallel.objects` and `perpendicular.objects` must be line-like: `segment`, `line`, or `ray`.
- `equal_length.objects` must be `segment` objects in the MVP.
- `midpoint.point` must be `point`; `midpoint.object` must be line-like.
- `intersection.point` must be `point`; `intersection.objects` must be line-like.
- `altitude.from_point` and `altitude.foot` must be `point`; `altitude.segment` must be `segment`.
- `median.from_point` and `median.midpoint` must be `point`; `median.segment` must be `segment`.
- `angle_bisector.angle` must be `angle`; `angle_bisector.ray` must be `ray`.
- `circumcircle.triangle` and `incircle.triangle` must be `triangle`.
- `circumcircle.circle` and `incircle.circle` must be `circle`.

## Failure modes
- Invalid schema.
- Missing object or constraint references.
- Duplicate object or constraint ids.
- Existing references with incompatible object types.
- Ambiguous user intent before validation receives a GIR scene.

## Error codes
Expected validation issue codes include:

- `duplicate_object_id`
- `duplicate_constraint_id`
- `missing_object_reference`
- `missing_point_reference`
- `missing_constraint_reference`
- `invalid_constraint_target_type`

## Minimal JSON example
```json
{"version":"0.1","scene_type":"2d","objects":[],"constraints":[],"construction_steps":[]}
```
