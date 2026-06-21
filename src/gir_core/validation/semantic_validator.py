from collections import Counter
from typing import Iterable

from gir_core.models.constraints import (
    AltitudeConstraint,
    BelongsToConstraint,
    MedianConstraint,
    ParallelConstraint,
    PerpendicularConstraint,
)
from gir_core.models.objects import CircleObject, LineObject, SegmentObject, TriangleObject
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationIssue, ValidationReport


def validate_scene(scene: GirScene) -> ValidationReport:
    issues: list[ValidationIssue] = []
    object_ids = [obj.id for obj in scene.objects]
    constraint_ids = [constraint.id for constraint in scene.constraints]
    point_ids = {obj.id for obj in scene.objects if obj.type == "point"}
    object_id_set = set(object_ids)
    constraint_id_set = set(constraint_ids)

    _duplicates(object_ids, "duplicate_object_id", "object", issues)
    _duplicates(constraint_ids, "duplicate_constraint_id", "constraint", issues)

    for index, obj in enumerate(scene.objects):
        path = f"objects[{index}]"
        if isinstance(obj, TriangleObject):
            _require_points(obj.vertices, point_ids, f"{path}.vertices", issues)
        elif isinstance(obj, SegmentObject | LineObject):
            _require_points(obj.points, point_ids, f"{path}.points", issues)
        elif isinstance(obj, CircleObject):
            _require_point(obj.center, point_ids, f"{path}.center", issues)
            if obj.radius_point is not None:
                _require_point(obj.radius_point, point_ids, f"{path}.radius_point", issues)

    for index, constraint in enumerate(scene.constraints):
        path = f"constraints[{index}]"
        if isinstance(constraint, BelongsToConstraint):
            _require_object(constraint.point, object_id_set, f"{path}.point", issues)
            _require_object(constraint.object, object_id_set, f"{path}.object", issues)
        elif isinstance(constraint, PerpendicularConstraint | ParallelConstraint):
            _require_objects(constraint.objects, object_id_set, f"{path}.objects", issues)
        elif isinstance(constraint, AltitudeConstraint):
            _require_objects(
                [constraint.from_point, constraint.to_object, constraint.foot, constraint.segment],
                object_id_set,
                path,
                issues,
            )
        elif isinstance(constraint, MedianConstraint):
            _require_objects(
                [constraint.from_point, constraint.to_object, constraint.midpoint, constraint.segment],
                object_id_set,
                path,
                issues,
            )
        else:
            for ref in _generic_constraint_refs(constraint):
                _require_object(ref, object_id_set, path, issues)

    for index, step in enumerate(scene.construction_steps):
        for obj_id in step.objects:
            _require_object(obj_id, object_id_set, f"construction_steps[{index}].objects", issues)
        for constraint_id in step.constraints:
            if constraint_id not in constraint_id_set:
                issues.append(
                    ValidationIssue(
                        code="missing_constraint_reference",
                        message=f"Construction step references missing constraint '{constraint_id}'.",
                        path=f"construction_steps[{index}].constraints",
                    )
                )

    return ValidationReport(is_valid=not issues, issues=issues)


def _duplicates(values: list[str], code: str, kind: str, issues: list[ValidationIssue]) -> None:
    for value, count in Counter(values).items():
        if count > 1:
            issues.append(ValidationIssue(code=code, message=f"Duplicate {kind} id '{value}'."))


def _require_point(ref: str, point_ids: set[str], path: str, issues: list[ValidationIssue]) -> None:
    if ref not in point_ids:
        issues.append(ValidationIssue(code="missing_point_reference", message=f"Missing point '{ref}'.", path=path))


def _require_points(refs: Iterable[str], point_ids: set[str], path: str, issues: list[ValidationIssue]) -> None:
    for ref in refs:
        _require_point(ref, point_ids, path, issues)


def _require_object(ref: str, object_ids: set[str], path: str, issues: list[ValidationIssue]) -> None:
    if ref not in object_ids:
        issues.append(ValidationIssue(code="missing_object_reference", message=f"Missing object '{ref}'.", path=path))


def _require_objects(refs: Iterable[str], object_ids: set[str], path: str, issues: list[ValidationIssue]) -> None:
    for ref in refs:
        _require_object(ref, object_ids, path, issues)


def _generic_constraint_refs(constraint: object) -> list[str]:
    data = constraint.model_dump()  # type: ignore[attr-defined]
    refs: list[str] = []
    for key, value in data.items():
        if key in {"id", "type", "reason"}:
            continue
        if isinstance(value, str):
            refs.append(value)
        elif isinstance(value, list | tuple):
            refs.extend(item for item in value if isinstance(item, str))
    return refs
