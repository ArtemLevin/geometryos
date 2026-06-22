from gir_core.models.layout import LayoutLabel, LayoutPoint, LayoutScene, LayoutSegment
from gir_core.models.objects import LabelObject, PointObject, SegmentObject, TriangleObject
from gir_core.models.scene import GirScene

# Design note: fixed MVP coordinates live in the layout layer, not renderers. This
# preserves the GirScene -> LayoutScene -> Render boundary while postponing a real
# solver/layout engine until there are enough benchmark cases to justify one.
_FIXED_POINTS: dict[str, tuple[float, float]] = {
    "A": (120, 40),
    "B": (40, 180),
    "C": (240, 180),
    "H": (120, 180),
    "M": (140, 180),
}


def create_simple_layout(scene: GirScene) -> LayoutScene:
    points = _layout_points(scene)
    segments = _layout_segments(scene, points)
    labels = _layout_labels(scene, points)
    return LayoutScene(points=points, segments=segments, labels=labels)


def _layout_points(scene: GirScene) -> dict[str, LayoutPoint]:
    points: dict[str, LayoutPoint] = {}
    for obj in scene.objects:
        if isinstance(obj, PointObject) and obj.id in _FIXED_POINTS:
            x, y = _FIXED_POINTS[obj.id]
            points[obj.id] = LayoutPoint(id=obj.id, x=x, y=y, label=obj.label or obj.id)
    return points


def _layout_segments(scene: GirScene, points: dict[str, LayoutPoint]) -> list[LayoutSegment]:
    segments: list[LayoutSegment] = []
    seen: set[tuple[str, str, str]] = set()

    def add_segment(segment_id: str, start: str, end: str) -> None:
        key = (segment_id, start, end)
        if start in points and end in points and key not in seen:
            segments.append(LayoutSegment(id=segment_id, start=start, end=end))
            seen.add(key)

    for obj in scene.objects:
        if isinstance(obj, TriangleObject):
            a, b, c = obj.vertices
            add_segment(f"{obj.id}_edge_{a}{b}", a, b)
            add_segment(f"{obj.id}_edge_{b}{c}", b, c)
            add_segment(f"{obj.id}_edge_{c}{a}", c, a)
        elif isinstance(obj, SegmentObject):
            start, end = obj.points
            add_segment(obj.id, start, end)
    return segments


def _layout_labels(scene: GirScene, points: dict[str, LayoutPoint]) -> list[LayoutLabel]:
    labels = [
        LayoutLabel(id=f"label_{point.id}", target=point.id, text=point.label or point.id)
        for point in points.values()
    ]
    for obj in scene.objects:
        if isinstance(obj, LabelObject) and obj.target in points:
            labels.append(LayoutLabel(id=obj.id, target=obj.target, text=obj.text))
    return labels
