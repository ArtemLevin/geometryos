from gir_core.layout.simple_layout import create_simple_layout
from gir_core.models.layout import LayoutPoint, LayoutScene
from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene


def render_tikz(scene: GirScene) -> str:
    # Design note: public GirScene render entrypoints are a validation boundary for
    # library callers. Layout renderers stay pure and assume a prebuilt LayoutScene.
    report = validate_scene(scene)
    if not report.is_valid:
        raise ValueError(f"Cannot render semantic-invalid GIR: {report.model_dump()}")
    layout = create_simple_layout(scene)
    return render_tikz_layout(layout)


def render_tikz_layout(layout: LayoutScene) -> str:
    lines = [r"\begin{tikzpicture}"]
    for point in layout.points.values():
        x, y = _tikz_point(point, layout)
        lines.append(f"  \\coordinate ({point.id}) at ({x:g},{y:g});")
    for segment in layout.segments:
        style = "[dashed]" if segment.style == "dashed" else ""
        lines.append(f"  \\draw{style} ({segment.start})--({segment.end});")
    for label in layout.labels:
        lines.append(f"  \\node[above right] at ({label.target}) {{{label.text}}};")
    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)


def _tikz_point(point: LayoutPoint, layout: LayoutScene) -> tuple[float, float]:
    return point.x / 40, (layout.height - point.y) / 40
