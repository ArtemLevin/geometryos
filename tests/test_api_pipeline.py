import pytest
from fastapi import HTTPException

from gir_ai.text_to_gir.adapter import text_to_gir
from gir_api.routes.generate import GenerateRequest, generate
from gir_api.routes.render import render_svg_endpoint
from gir_core.models.scene import GirScene


def test_generate_validates_normalizes_and_renders_requested_outputs() -> None:
    response = generate(
        GenerateRequest(
            input_type="text",
            input="Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.",
            output=["svg", "tikz"],
            mode="strict",
        )
    )

    assert response.status == "success"
    assert response.validation_report is not None
    assert response.validation_report.is_valid
    assert response.gir is not None
    assert response.svg is not None and "<svg" in response.svg
    assert response.tikz is not None and "\\begin{tikzpicture}" in response.tikz


def test_render_endpoint_rejects_semantic_invalid_gir() -> None:
    result = text_to_gir("Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC.")
    assert result.gir is not None
    data = result.gir.model_dump()
    data["constraints"][3]["segment"] = "H"

    with pytest.raises(HTTPException) as exc_info:
        render_svg_endpoint(GirScene.model_validate(data))

    assert exc_info.value.status_code == 422
