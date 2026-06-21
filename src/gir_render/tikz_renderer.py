from gir_core.models.objects import PointObject, SegmentObject, TriangleObject
from gir_core.models.scene import GirScene

TIKZ_COORDS: dict[str, tuple[float, float]] = {
    "A": (0, 3),
    "B": (-2, 0),
    "C": (3, 0),
    "H": (0, 0),
    "M": (0.5, 0),
}


def render_tikz(scene: GirScene) -> str:
    lines = [r"\begin{tikzpicture}"]
    for obj in scene.objects:
        if isinstance(obj, PointObject) and obj.id in TIKZ_COORDS:
            x, y = TIKZ_COORDS[obj.id]
            lines.append(f"  \\coordinate ({obj.id}) at ({x:g},{y:g});")
    for obj in scene.objects:
        if isinstance(obj, TriangleObject) and all(v in TIKZ_COORDS for v in obj.vertices):
            a, b, c = obj.vertices
            lines.append(f"  \\draw ({a})--({b})--({c})--cycle;")
        elif isinstance(obj, SegmentObject) and all(point in TIKZ_COORDS for point in obj.points):
            a, b = obj.points
            lines.append(f"  \\draw[blue] ({a})--({b});")
    for obj in scene.objects:
        if isinstance(obj, PointObject) and obj.id in TIKZ_COORDS:
            lines.append(f"  \\node[above right] at ({obj.id}) {{{obj.label or obj.id}}};")
    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)
