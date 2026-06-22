from html import escape

from gir_core.models.objects import PointObject, SegmentObject, TriangleObject
from gir_core.models.scene import GirScene

# Design note: hard-coded coordinates are acceptable only for the skeleton renderer.
# They make the first vertical slice executable while preserving the rule that
# mathematical meaning comes from GIR, not from renderer-side geometry inference.
SVG_COORDS: dict[str, tuple[int, int]] = {
    "A": (120, 40),
    "B": (40, 180),
    "C": (240, 180),
    "H": (120, 180),
    "M": (140, 180),
}


def render_svg(scene: GirScene) -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="280" height="220" viewBox="0 0 280 220">'
    ]
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    for obj in scene.objects:
        if isinstance(obj, TriangleObject) and all(v in SVG_COORDS for v in obj.vertices):
            coords = " ".join(f"{SVG_COORDS[v][0]},{SVG_COORDS[v][1]}" for v in obj.vertices)
            parts.append(
                f'<polygon points="{coords}" fill="none" stroke="black" stroke-width="2"/>'
            )
        elif isinstance(obj, SegmentObject) and all(point in SVG_COORDS for point in obj.points):
            (x1, y1), (x2, y2) = (SVG_COORDS[obj.points[0]], SVG_COORDS[obj.points[1]])
            parts.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#2563eb" stroke-width="2"/>'
            )
    for obj in scene.objects:
        if isinstance(obj, PointObject) and obj.id in SVG_COORDS:
            x, y = SVG_COORDS[obj.id]
            label = escape(obj.label or obj.id)
            parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="black"/>')
            parts.append(f'<text x="{x + 6}" y="{y - 6}" font-size="14">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts)
