from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.models.scene import GirScene
from gir_core.validation.semantic_validator import validate_scene


def scene() -> GirScene:
    result = text_to_gir("Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.")
    assert result.gir is not None
    return result.gir


def test_valid_scene_passes() -> None:
    assert validate_scene(scene()).is_valid


def test_missing_reference_detected() -> None:
    data = scene().model_dump()
    data["objects"] = [obj for obj in data["objects"] if obj["id"] != "H"]
    report = validate_scene(GirScene.model_validate(data))
    assert not report.is_valid
    assert any(issue.code == "missing_object_reference" for issue in report.issues)


def test_duplicate_object_id_detected() -> None:
    data = scene().model_dump()
    data["objects"].append(data["objects"][0])
    report = validate_scene(GirScene.model_validate(data))
    assert any(issue.code == "duplicate_object_id" for issue in report.issues)


def test_duplicate_constraint_id_detected() -> None:
    data = scene().model_dump()
    data["constraints"].append(data["constraints"][0])
    report = validate_scene(GirScene.model_validate(data))
    assert any(issue.code == "duplicate_constraint_id" for issue in report.issues)


def test_construction_step_missing_object_detected() -> None:
    data = scene().model_dump()
    data["construction_steps"][0]["objects"].append("ZZ")
    assert not validate_scene(GirScene.model_validate(data)).is_valid


def test_ray_start_and_through_must_be_points() -> None:
    data = scene().model_dump()
    data["objects"].append({"id": "r_bad", "type": "ray", "start": "BC", "through": "C"})
    report = validate_scene(GirScene.model_validate(data))
    assert not report.is_valid
    assert any(issue.path == "objects[7].start" for issue in report.issues)


def test_angle_points_must_be_points() -> None:
    data = scene().model_dump()
    data["objects"].append({"id": "angle_bad", "type": "angle", "points": ["A", "BC", "C"]})
    report = validate_scene(GirScene.model_validate(data))
    assert not report.is_valid
    assert any(issue.path == "objects[7].points" for issue in report.issues)


def test_label_target_must_exist() -> None:
    data = scene().model_dump()
    data["objects"].append(
        {"id": "label_bad", "type": "label", "text": "missing", "target": "ZZ"}
    )
    report = validate_scene(GirScene.model_validate(data))
    assert not report.is_valid
    assert any(issue.path == "objects[7].target" for issue in report.issues)


def test_belongs_to_point_must_be_point() -> None:
    data = scene().model_dump()
    data["constraints"][1]["point"] = "AH"
    report = validate_scene(GirScene.model_validate(data))
    assert not report.is_valid
    assert any(issue.path == "constraints[1].point" for issue in report.issues)


def test_altitude_endpoint_and_foot_must_be_points() -> None:
    data = scene().model_dump()
    data["constraints"][3]["from_point"] = "BC"
    data["constraints"][3]["foot"] = "AH"
    report = validate_scene(GirScene.model_validate(data))
    assert not report.is_valid
    assert any(issue.path == "constraints[3].from_point" for issue in report.issues)
    assert any(issue.path == "constraints[3].foot" for issue in report.issues)


def test_altitude_segment_must_be_segment() -> None:
    data = scene().model_dump()
    data["constraints"][3]["segment"] = "H"
    report = validate_scene(GirScene.model_validate(data))
    assert not report.is_valid
    assert any(issue.path == "constraints[3].segment" for issue in report.issues)


def test_median_midpoint_and_segment_types_are_checked() -> None:
    data = {
        "version": "0.1",
        "scene_type": "2d",
        "objects": [
            {"id": "A", "type": "point", "label": "A"},
            {"id": "B", "type": "point", "label": "B"},
            {"id": "C", "type": "point", "label": "C"},
            {"id": "BC", "type": "segment", "points": ["B", "C"]},
            {"id": "ABC", "type": "triangle", "vertices": ["A", "B", "C"]},
            {"id": "M", "type": "point", "label": "M"},
            {"id": "AM", "type": "segment", "points": ["A", "M"]},
        ],
        "constraints": [
            {
                "id": "c_median_bad",
                "type": "median",
                "from_point": "A",
                "to_object": "BC",
                "midpoint": "AM",
                "segment": "M",
            }
        ],
        "construction_steps": [],
    }
    report = validate_scene(GirScene.model_validate(data))
    assert not report.is_valid
    assert any(issue.path == "constraints[0].midpoint" for issue in report.issues)
    assert any(issue.path == "constraints[0].segment" for issue in report.issues)
