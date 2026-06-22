from html import escape

from gir_core.layout.simple_layout import create_simple_layout
from gir_core.models.layout import LayoutScene
from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene


def render_svg(scene: GirScene) -> str:
    # Design note: public GirScene render entrypoints are a validation boundary for
    # library callers. Layout renderers stay pure and assume a prebuilt LayoutScene.
    report = validate_scene(scene)
    if not report.is_valid:
        raise ValueError(f"Cannot render semantic-invalid GIR: {report.model_dump()}")
    layout = create_simple_layout(scene)
    return render_svg_layout(layout)


def render_svg_layout(layout: LayoutScene) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{layout.width:g}" '
        f'height="{layout.height:g}" viewBox="0 0 {layout.width:g} {layout.height:g}">'
    ]
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    for segment in layout.segments:
        start = layout.points[segment.start]
        end = layout.points[segment.end]
        dash = ' stroke-dasharray="4 4"' if segment.style == "dashed" else ""
        parts.append(
            f'<line x1="{start.x:g}" y1="{start.y:g}" x2="{end.x:g}" y2="{end.y:g}" '
            f'stroke="#2563eb" stroke-width="2"{dash}/>'
        )
    for point in layout.points.values():
        parts.append(f'<circle cx="{point.x:g}" cy="{point.y:g}" r="3" fill="black"/>')
    for label in layout.labels:
        target = layout.points[label.target]
        parts.append(
            f'<text x="{target.x + label.dx:g}" y="{target.y + label.dy:g}" font-size="14">'
            f"{escape(label.text)}</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts)
