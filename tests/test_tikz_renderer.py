import pytest

from gir_ai.text_to_gir.adapter import text_to_gir
from gir_core.models.scene import GirScene
from gir_render.tikz_renderer import render_tikz


def _altitude_scene() -> GirScene:
    scene = text_to_gir(
        "Постройте треугольник ABC. Проведите высоту из вершины A к стороне BC."
    ).gir
    assert scene is not None
    return scene


def test_render_tikz_triangle() -> None:
    tikz = render_tikz(_altitude_scene())
    assert isinstance(tikz, str)
    assert "\\begin{tikzpicture}" in tikz
    assert "\\end{tikzpicture}" in tikz
    assert "\\coordinate (A)" in tikz


def test_render_tikz_rejects_semantic_invalid_gir() -> None:
    data = _altitude_scene().model_dump()
    data["constraints"][3]["segment"] = "H"

    with pytest.raises(ValueError, match="semantic-invalid GIR"):
        render_tikz(GirScene.model_validate(data))
