from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.validation.semantic_validator import validate_scene


def test_text_to_gir_triangle_only_success() -> None:
    result = text_to_gir("Постройте треугольник ABC.")

    assert result.status == "success"
    assert result.gir is not None
    assert validate_scene(result.gir).is_valid
    assert {obj.id for obj in result.gir.objects} >= {"A", "B", "C", "AB", "BC", "CA", "ABC"}


def test_text_to_gir_midpoint_success() -> None:
    result = text_to_gir("Постройте треугольник ABC. Отметьте середину M стороны BC.")

    assert result.status == "success"
    assert result.gir is not None
    assert any(obj.id == "M" for obj in result.gir.objects)
    assert any(constraint.type == "midpoint" for constraint in result.gir.constraints)
    assert validate_scene(result.gir).is_valid


def test_text_to_gir_angle_bisector_success() -> None:
    result = text_to_gir("Постройте треугольник ABC. Проведите биссектрису угла A.")

    assert result.status == "success"
    assert result.gir is not None
    assert any(obj.id == "angle_BAC" and obj.type == "angle" for obj in result.gir.objects)
    assert any(obj.id == "bisector_A" and obj.type == "ray" for obj in result.gir.objects)
    assert any(constraint.type == "angle_bisector" for constraint in result.gir.constraints)
    assert validate_scene(result.gir).is_valid


def test_text_to_gir_ambiguous_bisector_needs_clarification() -> None:
    result = text_to_gir("Постройте треугольник ABC. Проведите биссектрису.")

    assert result.status == "needs_clarification"
    assert result.gir is None
    assert result.ambiguities
    assert result.ambiguities[0].code == "missing_angle"


def test_text_to_gir_unsupported_square_error() -> None:
    result = text_to_gir("Постройте квадрат ABCD.")

    assert result.status == "error"
    assert result.gir is None


def test_text_to_gir_triangle_with_unsupported_circle_text_stays_error() -> None:
    result = text_to_gir("Постройте треугольник ABC. Проведите окружность через A.")

    assert result.status == "error"
    assert result.gir is None


def test_all_successful_adapter_scenes_emit_canonical_gir_0_2() -> None:
    prompts = [
        "Постройте треугольник ABC.",
        "Постройте треугольник ABC. Отметьте середину M стороны BC.",
        "Постройте треугольник ABC. Проведите медиану из вершины A к стороне BC.",
        "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
        "Постройте треугольник ABC. Проведите биссектрису угла A.",
    ]

    for prompt in prompts:
        result = text_to_gir(prompt)
        assert result.status == "success"
        assert result.gir is not None
        assert result.gir.schema_version == "0.2.0"
        assert "version" not in result.gir.model_dump()
