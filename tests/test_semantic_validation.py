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
    data = scene().model_dump(); data["objects"].append(data["objects"][0])
    assert any(i.code == "duplicate_object_id" for i in validate_scene(GirScene.model_validate(data)).issues)


def test_duplicate_constraint_id_detected() -> None:
    data = scene().model_dump(); data["constraints"].append(data["constraints"][0])
    assert any(i.code == "duplicate_constraint_id" for i in validate_scene(GirScene.model_validate(data)).issues)


def test_construction_step_missing_object_detected() -> None:
    data = scene().model_dump(); data["construction_steps"][0]["objects"].append("ZZ")
    assert not validate_scene(GirScene.model_validate(data)).is_valid
