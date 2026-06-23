from math import hypot

from gir_core.models.constraints import (
    AltitudeConstraint,
    AngleBisectorConstraint,
    MedianConstraint,
    MidpointConstraint,
)
from gir_core.models.layout import LayoutLabel, LayoutPoint, LayoutScene, LayoutSegment
from gir_core.models.objects import (
    AngleObject,
    GirObject,
    LabelObject,
    PointObject,
    RayObject,
    SegmentObject,
    TriangleObject,
)
from gir_core.models.scene import GirScene

_CANONICAL_TRIANGLE_POINTS: tuple[tuple[float, float], ...] = (
    (120, 40),
    (40, 180),
    (240, 180),
)
_ANGLE_BISECTOR_RAY_LENGTH = 90


def create_simple_layout(scene: GirScene) -> LayoutScene:
    objects = _objects_by_id(scene)
    points = _layout_points(scene, objects)
    _resolve_midpoints(scene, objects, points)
    _resolve_altitudes(scene, objects, points)
    _resolve_medians(scene, objects, points)
    _resolve_angle_bisectors(scene, objects, points)
    segments = _layout_segments(scene, points)
    labels = _layout_labels(scene, points)
    return LayoutScene(points=points, segments=segments, labels=labels)


def _objects_by_id(scene: GirScene) -> dict[str, GirObject]:
    return {obj.id: obj for obj in scene.objects}


def _layout_points(scene: GirScene, objects: dict[str, GirObject]) -> dict[str, LayoutPoint]:
    points: dict[str, LayoutPoint] = {}
    triangle = _primary_triangle(scene)
    if triangle is not None:
        # geometryos: canonical MVP layout assumes one primary triangle scene.
        # ceiling: replace when benchmarks include multiple interacting triangles.
        # trigger: first benchmark with more than one TriangleObject.
        for point_id, (x, y) in zip(triangle.vertices, _CANONICAL_TRIANGLE_POINTS, strict=True):
            point = objects.get(point_id)
            if isinstance(point, PointObject):
                points[point_id] = LayoutPoint(id=point_id, x=x, y=y, label=point.label or point_id)

    for obj in scene.objects:
        if isinstance(obj, PointObject) and obj.id in points:
            points[obj.id] = points[obj.id].model_copy(update={"label": obj.label or obj.id})
    return points


def _primary_triangle(scene: GirScene) -> TriangleObject | None:
    return next((obj for obj in scene.objects if isinstance(obj, TriangleObject)), None)


def _resolve_midpoints(
    scene: GirScene,
    objects: dict[str, GirObject],
    points: dict[str, LayoutPoint],
) -> None:
    for constraint in scene.constraints:
        if isinstance(constraint, MidpointConstraint):
            _place_segment_midpoint(constraint.point, constraint.object, objects, points)


def _resolve_altitudes(
    scene: GirScene,
    objects: dict[str, GirObject],
    points: dict[str, LayoutPoint],
) -> None:
    for constraint in scene.constraints:
        if not isinstance(constraint, AltitudeConstraint):
            continue
        base = objects.get(constraint.to_object)
        if not isinstance(base, SegmentObject) or constraint.from_point not in points:
            continue
        start, end = base.points
        if start not in points or end not in points:
            continue
        x, y = _project_point_to_line(points[constraint.from_point], points[start], points[end])
        _place_point(constraint.foot, objects, points, x, y)


def _resolve_medians(
    scene: GirScene,
    objects: dict[str, GirObject],
    points: dict[str, LayoutPoint],
) -> None:
    for constraint in scene.constraints:
        if isinstance(constraint, MedianConstraint) and constraint.midpoint not in points:
            _place_segment_midpoint(constraint.midpoint, constraint.to_object, objects, points)


def _resolve_angle_bisectors(
    scene: GirScene,
    objects: dict[str, GirObject],
    points: dict[str, LayoutPoint],
) -> None:
    for constraint in scene.constraints:
        if not isinstance(constraint, AngleBisectorConstraint):
            continue
        angle = objects.get(constraint.angle)
        ray = objects.get(constraint.ray)
        if not isinstance(angle, AngleObject) or not isinstance(ray, RayObject):
            continue
        first, vertex, third = angle.points
        if vertex not in points or first not in points or third not in points:
            continue
        if ray.through in points:
            continue
        direction = _angle_bisector_direction(points[vertex], points[first], points[third])
        if direction is None:
            continue
        x = points[vertex].x + direction[0] * _ANGLE_BISECTOR_RAY_LENGTH
        y = points[vertex].y + direction[1] * _ANGLE_BISECTOR_RAY_LENGTH
        _place_point(ray.through, objects, points, x, y)


def _place_segment_midpoint(
    point_id: str,
    segment_id: str,
    objects: dict[str, GirObject],
    points: dict[str, LayoutPoint],
) -> None:
    segment = objects.get(segment_id)
    if not isinstance(segment, SegmentObject):
        return
    start, end = segment.points
    if start not in points or end not in points:
        return
    x, y = _midpoint(points[start], points[end])
    _place_point(point_id, objects, points, x, y)


def _place_point(
    point_id: str,
    objects: dict[str, GirObject],
    points: dict[str, LayoutPoint],
    x: float,
    y: float,
) -> None:
    obj = objects.get(point_id)
    if isinstance(obj, PointObject):
        points[point_id] = LayoutPoint(id=point_id, x=x, y=y, label=obj.label or obj.id)


def _midpoint(a: LayoutPoint, b: LayoutPoint) -> tuple[float, float]:
    return ((a.x + b.x) / 2, (a.y + b.y) / 2)


def _project_point_to_line(
    point: LayoutPoint,
    line_start: LayoutPoint,
    line_end: LayoutPoint,
) -> tuple[float, float]:
    dx = line_end.x - line_start.x
    dy = line_end.y - line_start.y
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        return line_start.x, line_start.y

    t = ((point.x - line_start.x) * dx + (point.y - line_start.y) * dy) / length_squared
    return line_start.x + t * dx, line_start.y + t * dy


def _angle_bisector_direction(
    vertex: LayoutPoint,
    first: LayoutPoint,
    third: LayoutPoint,
) -> tuple[float, float] | None:
    first_unit = _unit_vector(first.x - vertex.x, first.y - vertex.y)
    third_unit = _unit_vector(third.x - vertex.x, third.y - vertex.y)
    if first_unit is None or third_unit is None:
        return None

    # geometryos: angle bisector layout uses fixed ray length and no collision avoidance.
    # ceiling: replace when render benchmarks include overlapping labels or multiple angle rays.
    # trigger: first visual benchmark requiring collision-aware layout.
    dx = first_unit[0] + third_unit[0]
    dy = first_unit[1] + third_unit[1]
    return _unit_vector(dx, dy)


def _unit_vector(dx: float, dy: float) -> tuple[float, float] | None:
    length = hypot(dx, dy)
    if length == 0:
        return None
    return dx / length, dy / length


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
        elif isinstance(obj, RayObject):
            add_segment(obj.id, obj.start, obj.through)
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
