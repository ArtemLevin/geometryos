# Render Contract

## Purpose
Define the rendering boundary for GeometryOS outputs.
Renderers are deterministic sinks: they draw already validated geometry and never
interpret user text, call AI, or repair invalid mathematics.

## Input
Public `GirScene` render entrypoints accept semantic-valid GIR only. They must
run semantic validation before layout so direct library callers cannot bypass the
validation gate.

Low-level layout renderers accept `LayoutScene` and assume the caller already
built a valid layout from a validated scene.

## Output
Renderers return deterministic text output:

- SVG renderer returns an SVG string.
- TikZ renderer returns a TikZ picture string.

## Invariants
- GIR is the source of truth.
- Renderers never call AI.
- Renderers do not invent missing objects or fix invalid geometry.
- Semantic-invalid `GirScene` input is rejected before layout/render.
- `LayoutScene` render functions only serialize the provided layout.

## Failure modes
- Pydantic schema parsing can fail before a renderer is called.
- Semantic validation failure rejects public `GirScene` render calls.
- Invalid or inconsistent `LayoutScene` may fail during layout serialization.

## Minimal example
```python
from gir_core.validation.semantic_validator import validate_scene
from gir_render.svg_renderer import render_svg

report = validate_scene(scene)
assert report.is_valid
svg = render_svg(scene)
```
