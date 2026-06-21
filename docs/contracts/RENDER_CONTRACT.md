# Render Contract

## Purpose
Define the contract for Render Contract.

## Input
JSON-compatible data exchanged between GIR layers.

## Output
Validated data or a structured error/report.

## Invariants
- GIR is the source of truth.
- Layers do not bypass validation.
- Renderers never call AI.

## Failure modes
- Invalid schema.
- Missing references.
- Ambiguous user intent.

## Minimal JSON example
```json
{"version":"0.1","scene_type":"2d","objects":[],"constraints":[],"construction_steps":[]}
```
