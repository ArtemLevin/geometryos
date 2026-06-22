from gir_core.layout.simple_layout import create_simple_layout
from gir_core.models.layout import LayoutPoint, LayoutScene
from gir_core.models.scene import GirScene


def render_tikz(scene: GirScene) -> str:
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
