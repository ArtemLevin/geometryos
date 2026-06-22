import pytest

from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.models.scene import GirScene
from gir_render.svg_renderer import render_svg


def _altitude_scene() -> GirScene:
    scene = text_to_gir(
        "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."
    ).gir
    assert scene is not None
    return scene


def test_render_svg_triangle() -> None:
    svg = render_svg(_altitude_scene())
    assert isinstance(svg, str)
    assert "<svg" in svg and "</svg>" in svg
    assert "A" in svg and "B" in svg and "C" in svg


def test_render_svg_rejects_semantic_invalid_gir() -> None:
    data = _altitude_scene().model_dump()
    data["constraints"][3]["segment"] = "H"

    with pytest.raises(ValueError, match="semantic-invalid GIR"):
        render_svg(GirScene.model_validate(data))
