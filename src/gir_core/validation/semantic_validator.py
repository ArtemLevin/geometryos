from collections import Counter
from collections.abc import Iterable, Mapping

from gir_core.models.constraints import (
    AltitudeConstraint,
    AngleBisectorConstraint,
    BelongsToConstraint,
    CircumcircleConstraint,
    CollinearConstraint,
    EqualLengthConstraint,
    IncircleConstraint,
    IntersectionConstraint,
    MedianConstraint,
    MidpointConstraint,
    NonCollinearConstraint,
    ParallelConstraint,
    PerpendicularConstraint,
)
from gir_core.models.objects import (
    AngleObject,
    CircleObject,
    LabelObject,
    LineObject,
    RayObject,
    SegmentObject,
    TriangleObject,
)
from gir_core.models.scene import GirScene
from gir_core.models.validation import ValidationIssue, ValidationReport

_LINE_LIKE_TYPES = {"segment", "line", "ray"}


def validate_scene(scene: GirScene) -> ValidationReport:
    # Design note: this validator is intentionally structural and type-aware, not a
    # geometric solver. It catches dirty GIR references without pretending to prove
    # full mathematical constructibility.
    issues: list[ValidationIssue] = []
    object_ids = [obj.id for obj in scene.objects]
    constraint_ids = [constraint.id for constraint in scene.constraints]
    object_types = _object_type_map(scene)
    point_ids = {obj_id for obj_id, obj_type in object_types.items() if obj_type == "point"}
    object_id_set = set(object_ids)
    constraint_id_set = set(constraint_ids)

    _duplicates(object_ids, "duplicate_object_id", "object", issues)
    _duplicates(constraint_ids, "duplicate_constraint_id", "constraint", issues)

    for index, obj in enumerate(scene.objects):
        path = f"objects[{index}]"
        if isinstance(obj, TriangleObject):
            _require_points(obj.vertices, point_ids, f"{path}.vertices", issues)
            _require_distinct_refs(obj.vertices, f"{path}.vertices", issues)
        elif isinstance(obj, (SegmentObject, LineObject)):
            _require_points(obj.points, point_ids, f"{path}.points", issues)
            _require_distinct_refs(obj.points, f"{path}.points", issues)
        elif isinstance(obj, RayObject):
            _require_point(obj.start, point_ids, f"{path}.start", issues)
            _require_point(obj.through, point_ids, f"{path}.through", issues)
            _require_distinct_refs((obj.start, obj.through), path, issues)
        elif isinstance(obj, AngleObject):
            _require_points(obj.points, point_ids, f"{path}.points", issues)
            _require_distinct_refs(obj.points, f"{path}.points", issues)
        elif isinstance(obj, LabelObject):
            _require_object(obj.target, object_id_set, f"{path}.target", issues)
        elif isinstance(obj, CircleObject):
            _require_point(obj.center, point_ids, f"{path}.center", issues)
            if obj.radius_point is not None:
                _require_point(obj.radius_point, point_ids, f"{path}.radius_point", issues)

    for index, constraint in enumerate(scene.constraints):
        path = f"constraints[{index}]"
        if isinstance(constraint, BelongsToConstraint):
            _require_constraint_target_type(
                constraint.id, constraint.point, object_types, {"point"}, f"{path}.point", issues
            )
            _require_object(constraint.object, object_id_set, f"{path}.object", issues)
        elif isinstance(constraint, (CollinearConstraint, NonCollinearConstraint)):
            _require_constraint_target_types(
                constraint.id, constraint.points, object_types, {"point"}, f"{path}.points", issues
            )
            _require_distinct_refs(constraint.points, f"{path}.points", issues)
        elif isinstance(constraint, (PerpendicularConstraint, ParallelConstraint)):
            _require_constraint_target_types(
                constraint.id,
                constraint.objects,
                object_types,
                _LINE_LIKE_TYPES,
                f"{path}.objects",
                issues,
            )
        elif isinstance(constraint, EqualLengthConstraint):
            _require_constraint_target_types(
                constraint.id,
                constraint.objects,
                object_types,
                {"segment"},
                f"{path}.objects",
                issues,
            )
        elif isinstance(constraint, MidpointConstraint):
            _require_constraint_target_type(
                constraint.id, constraint.point, object_types, {"point"}, f"{path}.point", issues
            )
            _require_constraint_target_type(
                constraint.id,
                constraint.object,
                object_types,
                _LINE_LIKE_TYPES,
                f"{path}.object",
                issues,
            )
        elif isinstance(constraint, IntersectionConstraint):
            _require_constraint_target_type(
                constraint.id, constraint.point, object_types, {"point"}, f"{path}.point", issues
            )
            _require_constraint_target_types(
                constraint.id,
                constraint.objects,
                object_types,
                _LINE_LIKE_TYPES,
                f"{path}.objects",
                issues,
            )
        elif isinstance(constraint, AltitudeConstraint):
            _require_constraint_target_type(
                constraint.id,
                constraint.from_point,
                object_types,
                {"point"},
                f"{path}.from_point",
                issues,
            )
            _require_constraint_target_type(
                constraint.id,
                constraint.to_object,
                object_types,
                _LINE_LIKE_TYPES,
                f"{path}.to_object",
                issues,
            )
            _require_constraint_target_type(
                constraint.id, constraint.foot, object_types, {"point"}, f"{path}.foot", issues
            )
            _require_constraint_target_type(
                constraint.id,
                constraint.segment,
                object_types,
                {"segment"},
                f"{path}.segment",
                issues,
            )
        elif isinstance(constraint, MedianConstraint):
            _require_constraint_target_type(
                constraint.id,
                constraint.from_point,
                object_types,
                {"point"},
                f"{path}.from_point",
                issues,
            )
            _require_constraint_target_type(
                constraint.id,
                constraint.to_object,
                object_types,
                {"segment"},
                f"{path}.to_object",
                issues,
            )
            _require_constraint_target_type(
                constraint.id,
                constraint.midpoint,
                object_types,
                {"point"},
                f"{path}.midpoint",
                issues,
            )
            _require_constraint_target_type(
                constraint.id,
                constraint.segment,
                object_types,
                {"segment"},
                f"{path}.segment",
                issues,
            )
        elif isinstance(constraint, AngleBisectorConstraint):
            _require_constraint_target_type(
                constraint.id, constraint.angle, object_types, {"angle"}, f"{path}.angle", issues
            )
            _require_constraint_target_type(
                constraint.id, constraint.ray, object_types, {"ray"}, f"{path}.ray", issues
            )
        elif isinstance(constraint, (CircumcircleConstraint, IncircleConstraint)):
            _require_constraint_target_type(
                constraint.id,
                constraint.triangle,
                object_types,
                {"triangle"},
                f"{path}.triangle",
                issues,
            )
            _require_constraint_target_type(
                constraint.id, constraint.circle, object_types, {"circle"}, f"{path}.circle", issues
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
                        message=(
                            f"Construction step references missing constraint '{constraint_id}'."
                        ),
                        path=f"construction_steps[{index}].constraints",
                    )
                )

    return ValidationReport(is_valid=not issues, issues=issues)


def _object_type_map(scene: GirScene) -> dict[str, str]:
    return {obj.id: obj.type for obj in scene.objects}


def _require_constraint_target_type(
    constraint_id: str,
    ref: str,
    object_types: Mapping[str, str],
    allowed_types: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    actual_type = object_types.get(ref)
    if actual_type is None:
        issues.append(
            ValidationIssue(
                code="missing_object_reference",
                message=f"Constraint '{constraint_id}' references missing object '{ref}'.",
                path=path,
            )
        )
        return
    if actual_type not in allowed_types:
        expected = sorted(allowed_types)
        issues.append(
            ValidationIssue(
                code="invalid_constraint_target_type",
                message=(
                    f"Constraint '{constraint_id}' expects '{ref}' to reference one of "
                    f"{expected}, got '{actual_type}'."
                ),
                path=path,
            )
        )


def _require_constraint_target_types(
    constraint_id: str,
    refs: Iterable[str],
    object_types: Mapping[str, str],
    allowed_types: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    for ref in refs:
        _require_constraint_target_type(
            constraint_id, ref, object_types, allowed_types, path, issues
        )


def _duplicates(values: list[str], code: str, kind: str, issues: list[ValidationIssue]) -> None:
    for value, count in Counter(values).items():
        if count > 1:
            issues.append(ValidationIssue(code=code, message=f"Duplicate {kind} id '{value}'."))


def _require_distinct_refs(
    refs: Iterable[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    ref_list = list(refs)
    if len(set(ref_list)) != len(ref_list):
        issues.append(
            ValidationIssue(
                code="duplicate_role_reference",
                message="Object or constraint role references must be distinct.",
                path=path,
            )
        )


def _require_point(ref: str, point_ids: set[str], path: str, issues: list[ValidationIssue]) -> None:
    if ref not in point_ids:
        issues.append(
            ValidationIssue(
                code="missing_point_reference",
                message=f"Missing point '{ref}'.",
                path=path,
            )
        )


def _require_segment(
    ref: str,
    segment_ids: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if ref not in segment_ids:
        issues.append(
            ValidationIssue(
                code="missing_segment_reference",
                message=f"Missing segment '{ref}'.",
                path=path,
            )
        )


def _require_points(
    refs: Iterable[str],
    point_ids: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    for ref in refs:
        _require_point(ref, point_ids, path, issues)


def _require_object(
    ref: str,
    object_ids: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if ref not in object_ids:
        issues.append(
            ValidationIssue(
                code="missing_object_reference",
                message=f"Missing object '{ref}'.",
                path=path,
            )
        )


def _require_objects(
    refs: Iterable[str],
    object_ids: set[str],
    path: str,
    issues: list[ValidationIssue],
) -> None:
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
